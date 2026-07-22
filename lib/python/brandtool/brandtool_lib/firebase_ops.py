"""Firebase / Google Cloud project operations.

Ported from bin/createBrandGoogleCloudAndFirebase.py (the proven legacy script).
All functions take googleapiclient service objects so they can be faked in tests.
"""
import base64
import json
import os
import time

FCM_ADMIN_ID = 'firebase-messaging-admin'
FCM_ADMIN_ROLE = 'roles/firebasecloudmessaging.admin'  # "Firebase Cloud Messaging API Admin"


def wait_for_operation(service, operation_name, poll_seconds=4):
    while True:
        result = service.operations().get(name=operation_name).execute()
        if result.get('done'):
            if 'error' in result:
                if result['error'].get('code') == 409:
                    return result
                raise RuntimeError(f'Operation failed: {result["error"]}')
            return result
        time.sleep(poll_seconds)


def get_android_app(firebase, project_id, package_name):
    apps = firebase.projects().androidApps().list(parent=f'projects/{project_id}').execute()
    for app in apps.get('apps', []):
        if app['packageName'] == package_name:
            return app['appId']
    return None


def get_ios_app_full(firebase, project_id, bundle_id):
    """The full iOS app resource dict (appId, teamId, appStoreId, ...) or None."""
    apps = firebase.projects().iosApps().list(parent=f'projects/{project_id}').execute()
    for app in apps.get('apps', []):
        if app['bundleId'] == bundle_id:
            return app
    return None


def get_ios_app(firebase, project_id, bundle_id):
    app = get_ios_app_full(firebase, project_id, bundle_id)
    return app['appId'] if app else None


def patch_ios_app(firebase, project_id, app_id, fields):
    """Patch mutable iOS app fields (teamId, appStoreId, displayName)."""
    firebase.projects().iosApps().patch(
        name=f'projects/{project_id}/iosApps/{app_id}',
        updateMask=','.join(sorted(fields)), body=fields).execute()


def list_sha_hashes(firebase, project_id, app_id):
    parent = f'projects/{project_id}/androidApps/{app_id}'
    existing = firebase.projects().androidApps().sha().list(parent=parent).execute()
    return {c['shaHash'].lower() for c in existing.get('certificates', [])}


def add_sha(firebase, project_id, app_id, sha_hash, cert_type):
    parent = f'projects/{project_id}/androidApps/{app_id}'
    firebase.projects().androidApps().sha().create(
        parent=parent, body={'shaHash': sha_hash, 'certType': cert_type}).execute()


def create_project(crm, project_id, display_name, parent=None):
    body = {'projectId': project_id, 'displayName': display_name}
    if parent:
        body['parent'] = parent
    op = crm.projects().create(body=body).execute()
    return wait_for_operation(crm, op['name'])


def get_project_number(crm, project_id):
    proj = crm.projects().get(name=f'projects/{project_id}').execute()
    return proj['name'].split('/')[1]


def grant_role(crm, project_id, member, role):
    policy = crm.projects().getIamPolicy(resource=f'projects/{project_id}').execute()
    policy.setdefault('bindings', []).append({'role': role, 'members': [member]})
    crm.projects().setIamPolicy(resource=f'projects/{project_id}',
                                body={'policy': policy}).execute()


def get_billing_account(billing, project_id):
    info = billing.projects().getBillingInfo(name=f'projects/{project_id}').execute()
    return info.get('billingAccountName', '')


def link_billing(billing, project_id, billing_account_id):
    billing.projects().updateBillingInfo(
        name=f'projects/{project_id}',
        body={'billingAccountName': f'billingAccounts/{billing_account_id}'}).execute()


def list_enabled_apis(usage, project_id):
    enabled, page_token = set(), None
    while True:
        resp = usage.services().list(parent=f'projects/{project_id}',
                                     filter='state:ENABLED', pageSize=200,
                                     pageToken=page_token).execute()
        for svc in resp.get('services', []):
            enabled.add(svc['name'].split('/')[-1])
        page_token = resp.get('nextPageToken')
        if not page_token:
            return enabled


def enable_apis(usage, project_id, apis):
    op = usage.services().batchEnable(parent=f'projects/{project_id}',
                                      body={'serviceIds': list(apis)}).execute()
    wait_for_operation(usage, op['name'])


def add_firebase(firebase, project_id):
    try:
        op = firebase.projects().addFirebase(project=f'projects/{project_id}').execute()
        wait_for_operation(firebase, op['name'])
    except Exception as e:
        if '409' not in str(e):
            raise


def create_android_app(firebase, project_id, display_name, package_name):
    op = firebase.projects().androidApps().create(
        parent=f'projects/{project_id}',
        body={'displayName': display_name[:40].strip(), 'packageName': package_name}).execute()
    res = wait_for_operation(firebase, op['name'])
    return (res.get('response', {}).get('appId')
            or get_android_app(firebase, project_id, package_name))


def create_ios_app(firebase, project_id, display_name, bundle_id,
                   team_id=None, app_store_id=None):
    import re as _re
    # same 40-char cap as create_android_app so both apps carry the same name
    body = {'displayName': display_name[:40].strip(), 'bundleId': bundle_id}
    # invalid/placeholder values 400 the whole request - skip them with a note
    if team_id and _re.fullmatch(r'[A-Z0-9]{10}', team_id):
        body['teamId'] = team_id
    elif team_id:
        print(f'  skipping teamId {team_id!r} (not a 10-char Apple Team ID - '
              'set DEVELOPMENT_TEAM later; audit --fix patches it)')
    if app_store_id and str(app_store_id).isdigit():
        body['appStoreId'] = str(app_store_id)
    elif app_store_id:
        print(f'  skipping appStoreId {app_store_id!r} (not numeric - audit --fix '
              'records it once the App Store record exists)')
    op = firebase.projects().iosApps().create(
        parent=f'projects/{project_id}', body=body).execute()
    res = wait_for_operation(firebase, op['name'])
    return (res.get('response', {}).get('appId')
            or get_ios_app(firebase, project_id, bundle_id))


def download_android_config(firebase, project_id, app_id, dest_dir):
    conf = firebase.projects().androidApps().getConfig(
        name=f'projects/{project_id}/androidApps/{app_id}/config').execute()
    content = base64.b64decode(conf['configFileContents']).decode('utf-8')
    with open(os.path.join(dest_dir, 'google-services.json'), 'w') as f:
        f.write(content)
    return content


def download_ios_config(firebase, project_id, app_id, dest_dir):
    conf = firebase.projects().iosApps().getConfig(
        name=f'projects/{project_id}/iosApps/{app_id}/config').execute()
    content = base64.b64decode(conf['configFileContents']).decode('utf-8')
    with open(os.path.join(dest_dir, 'GoogleService-Info.plist'), 'w') as f:
        f.write(content)
    return content


def service_account_exists(iam, project_id, email):
    try:
        iam.projects().serviceAccounts().get(
            name=f'projects/{project_id}/serviceAccounts/{email}').execute()
        return True
    except Exception:
        return False


def fcm_admin_members(crm, project_id):
    """Service-account emails holding the FCM Admin role on the project."""
    policy = crm.projects().getIamPolicy(resource=f'projects/{project_id}').execute()
    emails = set()
    for binding in policy.get('bindings', []):
        if binding.get('role') == FCM_ADMIN_ROLE:
            for member in binding.get('members', []):
                if member.startswith('serviceAccount:'):
                    emails.add(member[len('serviceAccount:'):])
    return sorted(emails)


def ensure_fcm_admin(iam, crm, project_id, brand_dir, sa_email=None):
    """Ensure an FCM messaging SA + key file exist; returns the key filename.

    sa_email: use an existing (possibly custom-named, pre-tooling) service account
    instead of the standard firebase-messaging-admin - it must already exist.
    """
    email = sa_email or f'{FCM_ADMIN_ID}@{project_id}.iam.gserviceaccount.com'
    if not service_account_exists(iam, project_id, email):
        if sa_email:
            raise RuntimeError(f'{email} does not exist in project {project_id} '
                               '(fcmServiceAccount in transmute.json is wrong?)')
        iam.projects().serviceAccounts().create(
            name=f'projects/{project_id}',
            body={'accountId': FCM_ADMIN_ID,
                  'serviceAccount': {'displayName': 'Firebase Messaging Admin'}}).execute()
        grant_role(crm, project_id, f'serviceAccount:{email}', 'roles/editor')
    key_op = iam.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{email}',
        body={'privateKeyType': 'TYPE_GOOGLE_CREDENTIALS_FILE'}).execute()
    key_data = json.loads(base64.b64decode(key_op['privateKeyData']).decode('utf-8'))
    filename = f"{project_id}-{key_op['name'].split('/')[-1][:12]}.json"
    with open(os.path.join(brand_dir, filename), 'w') as f:
        json.dump(key_data, f, indent=2)
    return filename
