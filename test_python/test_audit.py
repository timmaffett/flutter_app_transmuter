import json
import os

from brandtool_lib import audit
from brandtool_lib.report import OK, ISSUE, SKIP
from fakes import FakeResource


def make_brand(tmp_path, project_id='demo-proj', app_id='1:1:android:aaa',
               ios_app_id='1:1:ios:bbb'):
    root = tmp_path / 'branded_loyalty'
    root.mkdir(exist_ok=True)
    d = root / 'demo_brand'
    d.mkdir()
    (d / 'AuthKey_APNS999999.p8').write_text('apns')
    backup = tmp_path / 'appleAPNPushKey'
    backup.mkdir(exist_ok=True)
    (backup / 'AuthKey_APNS999999.p8').write_text('apns')
    (d / 'transmute.json').write_text(json.dumps({
        'packageName': 'com.demo.app', 'iosBundleIdentifier': 'com.demo.ios',
        'appName': 'Demo', 'billingAccountId': 'BILL-1',
        'firebaseProjectId': project_id,
        'firebaseProjectName': 'Demo Display Name',
        'apnsKeyId': 'APNS999999',
        'DEVELOPMENT_TEAM': 'TEAM123456',
        'appStoreId': '6446444444',
        'fcmServiceAccount': 'firebase-messaging-admin@demo-proj.iam.gserviceaccount.com',
        'apnsUploadedForIosAppId': '1:1:ios:bbb',
        'androidGoogleMapsSDKApiKey': 'AIza-android', 'iosGoogleMapsSDKApiKey': 'AIza-ios',
        'serverGooglePlacesAPIKey': 'AIza-places',
        'messagingServiceAccountKeyFile': 'sa.json',
        'AndroidSHA-1Fingerprint': '14:AE:72',
        'Additional-AndroidSHA-1Fingerprint': '22:66:DB'}))
    (d / 'google-services.json').write_text(json.dumps({
        'project_info': {'project_id': project_id, 'project_number': '111222333'},
        'client': [{'client_info': {'mobilesdk_app_id': app_id}}]}))
    (d / 'GoogleService-Info.plist').write_text(f'<plist>{ios_app_id}</plist>')
    (d / 'firebase_options.dart').write_text(f'// {app_id} {ios_app_id}')
    (d / 'sa.json').write_text('{}')
    return str(d)


CFG = {'billingAccountId': 'BILL-1', 'requiredApis': ['firebase.googleapis.com'],
       'debugSha1': '14:AE:72', 'releaseSha1': '22:66:DB', 'releaseSha256': '16:52:87'}


def healthy_services():
    key_by_name = {
        'k-android': {'name': 'k-android', 'displayName': 'Android Maps',
                      'restrictions': {'androidKeyRestrictions': {
                          'allowedApplications': [
                              {'sha1Fingerprint': '14AE72', 'packageName': 'com.demo.app'},
                              {'sha1Fingerprint': '2266DB', 'packageName': 'com.demo.app'}]},
                          'apiTargets': [{'service': 'maps-android-backend.googleapis.com'}]}},
        'k-ios': {'name': 'k-ios', 'displayName': 'iOS Maps',
                  'restrictions': {'iosKeyRestrictions': {
                      'allowedBundleIds': ['com.demo.ios']},
                      'apiTargets': [{'service': 'maps-ios-backend.googleapis.com'}]}},
        'k-places': {'name': 'k-places', 'displayName': 'Server Places',
                     'restrictions': {'apiTargets': [
                         {'service': 'places-backend.googleapis.com'},
                         {'service': 'places.googleapis.com'}]}},
    }
    strings = {'k-android': 'AIza-android', 'k-ios': 'AIza-ios', 'k-places': 'AIza-places'}
    sha = FakeResource(list=lambda parent: {'certificates': [
        {'shaHash': '14AE72'}, {'shaHash': '2266DB'}, {'shaHash': '165287'}]})
    android = FakeResource(
        list=lambda parent: {'apps': [{'packageName': 'com.demo.app', 'appId': '1:1:android:aaa'}]},
        sha=sha)
    ios = FakeResource(list=lambda parent: {'apps': [
        {'bundleId': 'com.demo.ios', 'appId': '1:1:ios:bbb',
         'teamId': 'TEAM123456', 'appStoreId': '6446444444'}]})
    return {
        'firebase': FakeResource(projects=FakeResource(androidApps=android, iosApps=ios)),
        'billing': FakeResource(projects=FakeResource(
            getBillingInfo=lambda name: {'billingAccountName': 'billingAccounts/BILL-1'})),
        'usage': FakeResource(services=FakeResource(
            list=lambda **kw: {'services': [{'name': 'projects/1/services/firebase.googleapis.com'}]})),
        'apikeys': FakeResource(
            projects=FakeResource(locations=FakeResource(keys=FakeResource(
                list=lambda **kw: {'keys': list(key_by_name.values())},
                getKeyString=lambda name: {'keyString': strings[name]},
                patch=lambda name, updateMask, body: {'name': 'op-patch'}))),
            operations=FakeResource(get=lambda name: {'done': True, 'response': {}})),
        'iam': FakeResource(projects=FakeResource(serviceAccounts=FakeResource(
            get=lambda name: {'email': 'x'}))),
        'crm': FakeResource(projects=FakeResource(
            get=lambda name: {'name': 'projects/111222333',
                              'displayName': 'Demo Display Name'})),
    }


def test_healthy_brand_all_ok(tmp_path):
    r = audit.audit_brand(healthy_services(), CFG, make_brand(tmp_path))
    # This fixture has no ASC credentials, so the Apple API checks are (by design)
    # loudly flagged as missing; everything else must be clean.
    problems = [(c.name, c.status, c.detail) for c in r.issues
                if 'MISSING APPLE APP MANAGER API KEY' not in c.detail]
    assert problems == []
    apple_missing = [c for c in r.issues if 'MISSING APPLE APP MANAGER API KEY' in c.detail]
    assert len(apple_missing) == len(audit.APPLE_API_CHECKS)
    play_checks = [c for c in r.checks if c.name == 'Play Store app']
    assert play_checks and play_checks[0].status == SKIP


def test_missing_fingerprint_is_fixable_issue(tmp_path):
    services = healthy_services()
    sha_empty = FakeResource(list=lambda parent: {'certificates': []},
                             create=lambda parent, body: {})
    android = FakeResource(
        list=lambda parent: {'apps': [{'packageName': 'com.demo.app', 'appId': '1:1:android:aaa'}]},
        sha=sha_empty)
    ios = FakeResource(list=lambda parent: {'apps': [
        {'bundleId': 'com.demo.ios', 'appId': '1:1:ios:bbb'}]})
    services['firebase'] = FakeResource(projects=FakeResource(androidApps=android, iosApps=ios))
    r = audit.audit_brand(services, CFG, make_brand(tmp_path))
    fp = [c for c in r.checks if c.name == 'cert fingerprints'][0]
    assert fp.status == ISSUE and fp.fix is not None and fp.console_url


def test_maps_key_restriction_issue_names_the_missing_cert(tmp_path):
    services = healthy_services()
    # Android Maps key that only allows the debug cert (the legacy-script bug).
    key_by_name = {
        'k-android': {'name': 'k-android', 'restrictions': {'androidKeyRestrictions': {
            'allowedApplications': [
                {'sha1Fingerprint': '14AE72', 'packageName': 'com.demo.app'}]}}},
        'k-ios': {'name': 'k-ios', 'restrictions': {'iosKeyRestrictions': {
            'allowedBundleIds': ['com.demo.ios']}}},
        'k-places': {'name': 'k-places', 'restrictions': {'apiTargets': [
            {'service': 'places-backend.googleapis.com'},
            {'service': 'places.googleapis.com'}]}},
    }
    strings = {'k-android': 'AIza-android', 'k-ios': 'AIza-ios', 'k-places': 'AIza-places'}
    services['apikeys'] = FakeResource(projects=FakeResource(locations=FakeResource(
        keys=FakeResource(
            list=lambda **kw: {'keys': list(key_by_name.values())},
            getKeyString=lambda name: {'keyString': strings[name]}))))
    r = audit.audit_brand(services, CFG, make_brand(tmp_path))
    check = [c for c in r.checks if c.name == 'Android Maps key restriction'][0]
    assert check.status == ISSUE
    assert 'missing app signing fingerprint' in check.detail
    assert '2266db' in check.detail and 'release signing cert' in check.detail
    assert 'com.demo.app' in check.detail


def test_firebase_options_stale_names_brand_dir_in_switch_command(tmp_path):
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'firebase_options.dart'), 'w') as f:
        f.write('// no live ids in here')
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'firebase_options.dart in sync'][0]
    assert check.status == ISSUE
    assert f'transmute --switch {d}' in check.detail
    assert 'transmute --update' in check.detail


def test_firebase_options_stale_commands_colored_cornflower(tmp_path):
    from brandtool_lib import report
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'firebase_options.dart'), 'w') as f:
        f.write('// stale')
    try:
        report.set_color(True)
        r = audit.audit_brand(healthy_services(), CFG, d)
    finally:
        report.set_color(None)
    check = [c for c in r.checks if c.name == 'firebase_options.dart in sync'][0]
    assert '\x1b[38;5;111mtransmute --switch' in check.detail


def test_firebase_project_id_recording_is_fixable(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['firebaseProjectId']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'firebaseProjectId recorded'][0]
    assert check.status == ISSUE and check.fix is not None
    assert 'demo-proj' in check.detail
    check.fix()
    with open(tj) as f:
        data = json.loads(f.read())
    assert data['firebaseProjectId'] == 'demo-proj'
    assert data['firebaseProjectNumber'] == '111222333'


def test_firebase_project_id_mismatch_is_reported(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    data['firebaseProjectId'] = 'some-other-project'
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'firebaseProjectId recorded'][0]
    assert check.status == ISSUE and check.fix is None
    assert 'some-other-project' in check.detail and 'demo-proj' in check.detail


def test_firebase_project_name_recording_is_fixable(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['firebaseProjectName']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'firebaseProjectName recorded'][0]
    assert check.status == ISSUE and check.fix is not None
    assert 'Demo Display Name' in check.detail
    check.fix()
    with open(tj) as f:
        assert json.loads(f.read())['firebaseProjectName'] == 'Demo Display Name'


def test_firebase_project_name_difference_is_info(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    data['firebaseProjectName'] = 'Old Cased Name'
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'firebaseProjectName recorded'][0]
    assert check.status == 'info' and 'Demo Display Name' in check.detail
    assert check not in r.issues


def _services_with_ios(ios_app_dict, patch_calls=None):
    services = healthy_services()
    def patch(name, updateMask, body):
        if patch_calls is not None:
            patch_calls.append((updateMask, body))
        return {}
    ios = FakeResource(list=lambda parent: {'apps': [ios_app_dict]}, patch=patch)
    android = FakeResource(
        list=lambda parent: {'apps': [{'packageName': 'com.demo.app', 'appId': '1:1:android:aaa'}]},
        sha=FakeResource(list=lambda parent: {'certificates': [
            {'shaHash': '14AE72'}, {'shaHash': '2266DB'}, {'shaHash': '165287'}]}))
    services['firebase'] = FakeResource(projects=FakeResource(androidApps=android, iosApps=ios))
    return services


def test_ios_team_id_missing_is_fixable(tmp_path):
    patches = []
    services = _services_with_ios(
        {'bundleId': 'com.demo.ios', 'appId': '1:1:ios:bbb', 'appStoreId': '6446444444'},
        patches)
    r = audit.audit_brand(services, CFG, make_brand(tmp_path))
    check = [c for c in r.checks if c.name == 'Firebase iOS Team ID'][0]
    assert check.status == ISSUE and check.fix
    assert 'TEAM123456' in check.detail
    check.fix()
    assert patches[0] == ('teamId', {'teamId': 'TEAM123456'})


def test_ios_app_store_id_missing_in_firebase_is_fixable(tmp_path):
    patches = []
    services = _services_with_ios(
        {'bundleId': 'com.demo.ios', 'appId': '1:1:ios:bbb', 'teamId': 'TEAM123456'},
        patches)
    r = audit.audit_brand(services, CFG, make_brand(tmp_path))
    check = [c for c in r.checks if c.name == 'Firebase iOS App Store ID'][0]
    assert check.status == ISSUE and check.fix
    check.fix()
    assert patches[0] == ('appStoreId', {'appStoreId': '6446444444'})


def test_ios_app_store_id_recorded_from_firebase_when_transmute_lacks_it(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['appStoreId']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    services = _services_with_ios(
        {'bundleId': 'com.demo.ios', 'appId': '1:1:ios:bbb',
         'teamId': 'TEAM123456', 'appStoreId': '6446444444'})
    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'Firebase iOS App Store ID'][0]
    assert check.status == ISSUE and check.fix
    check.fix()
    with open(tj) as f:
        assert json.loads(f.read())['appStoreId'] == '6446444444'


def test_fcm_custom_sa_detected_via_iam_role(tmp_path):
    # The MKE scenario: custom-named push SA holds the FCM Admin role; no
    # fcmServiceAccount recorded, no key file at all.
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['fcmServiceAccount']
    del data['messagingServiceAccountKeyFile']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    services = healthy_services()
    services['crm'] = FakeResource(projects=FakeResource(
        get=lambda name: {'name': 'projects/111222333', 'displayName': 'Demo Display Name'},
        getIamPolicy=lambda resource: {'bindings': [
            {'role': 'roles/firebasecloudmessaging.admin',
             'members': ['serviceAccount:custom-push-notif@demo-proj.iam.gserviceaccount.com']}]}))
    r = audit.audit_brand(services, CFG, d)
    sa = [c for c in r.checks if c.name == 'FCM admin service account'][0]
    assert sa.status == ISSUE and sa.fix
    assert 'custom-push-notif@demo-proj.iam.gserviceaccount.com' in sa.detail
    assert 'Firebase Cloud Messaging API Admin' in sa.detail
    sa.fix()
    with open(tj) as f:
        assert json.loads(f.read())['fcmServiceAccount'] == \
            'custom-push-notif@demo-proj.iam.gserviceaccount.com'
    key = [c for c in r.checks if c.name == 'FCM admin key file'][0]
    assert key.status == ISSUE and key.fix  # mintable for the detected SA


def test_fcm_sa_inferred_from_key_file_client_email(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['fcmServiceAccount']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    with open(os.path.join(d, 'sa.json'), 'w') as f:
        f.write(json.dumps({'client_email': 'legacy-push@demo-proj.iam.gserviceaccount.com'}))
    r = audit.audit_brand(healthy_services(), CFG, d)
    sa = [c for c in r.checks if c.name == 'FCM admin service account'][0]
    assert sa.status == ISSUE and sa.fix and 'legacy-push@' in sa.detail
    sa.fix()
    with open(tj) as f:
        assert json.loads(f.read())['fcmServiceAccount'] == \
            'legacy-push@demo-proj.iam.gserviceaccount.com'


def test_fcm_key_file_account_mismatch_reported(tmp_path):
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'sa.json'), 'w') as f:
        f.write(json.dumps({'client_email': 'other@demo-proj.iam.gserviceaccount.com'}))
    r = audit.audit_brand(healthy_services(), CFG, d)
    mismatch = [c for c in r.checks if c.name == 'FCM key file account'][0]
    assert mismatch.status == ISSUE
    assert 'other@demo-proj' in mismatch.detail


def test_netpark_admin_urls_from_brand_name():
    assert audit._netpark_admin_urls('mke_smartpark_1495') == \
        ['https://np1.netpark.us/netPark/1495/']
    assert audit._netpark_admin_urls('fine_335_1535_2185_2190') == [
        'https://np1.netpark.us/netPark/335/', 'https://np1.netpark.us/netPark/1535/',
        'https://np1.netpark.us/netPark/2185/', 'https://np1.netpark.us/netPark/2190/']
    assert audit._netpark_admin_urls('netpark_demo_Loyalty') == \
        ['https://np1.netpark.us/netPark/<locationId>/']


def test_fcm_key_fix_paste_existing_json(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['fcmServiceAccount']
    del data['messagingServiceAccountKeyFile']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    key_json = json.dumps({
        'type': 'service_account', 'project_id': 'demo-proj',
        'private_key_id': '49714c1598f338a7fa6243f41b8a4296758bd551',
        'private_key': '-----BEGIN PRIVATE KEY-----X-----END PRIVATE KEY-----',
        'client_email': 'custom-push@demo-proj.iam.gserviceaccount.com'}, indent=2)
    answers = iter(['p'] + key_json.split('\n'))
    out = []
    audit.fcm_key_interactive_fix(
        healthy_services(), d, 'demo-proj', data,
        'custom-push@demo-proj.iam.gserviceaccount.com',
        input_fn=lambda _='': next(answers), print_fn=out.append)
    dest = os.path.join(d, 'demo-proj-49714c1598f3.json')
    assert os.path.exists(dest)
    with open(tj) as f:
        updated = json.loads(f.read())
    assert updated['messagingServiceAccountKeyFile'] == 'demo-proj-49714c1598f3.json'
    assert updated['fcmServiceAccount'] == 'custom-push@demo-proj.iam.gserviceaccount.com'
    assert any('nothing to upload' in str(ln) for ln in out)


def test_fcm_key_fix_paste_html_entity_encoded_json(tmp_path):
    # the netPark server admin page serves the stored JSON with HTML entities
    # (&quot; for every double quote) - the paste flow must decode it
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['fcmServiceAccount']
    del data['messagingServiceAccountKeyFile']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    key_json = json.dumps({
        'type': 'service_account', 'project_id': 'demo-proj',
        'private_key_id': 'e464e7b67161233fa8bdda77c96f73c29a688b9e',
        'private_key': '-----BEGIN PRIVATE KEY-----\\nX\\n-----END PRIVATE KEY-----\\n',
        'client_email': 'custom-push@demo-proj.iam.gserviceaccount.com'}, indent=2)
    encoded = key_json.replace('"', '&quot;')
    answers = iter(['p'] + encoded.split('\n'))
    out = []
    audit.fcm_key_interactive_fix(
        healthy_services(), d, 'demo-proj', data,
        'custom-push@demo-proj.iam.gserviceaccount.com',
        input_fn=lambda _='': next(answers), print_fn=out.append)
    dest = os.path.join(d, 'demo-proj-e464e7b67161.json')
    assert os.path.exists(dest)
    with open(dest) as f:
        saved = json.load(f)
    assert saved['client_email'] == 'custom-push@demo-proj.iam.gserviceaccount.com'
    assert '&quot;' not in open(dest).read()
    assert any('HTML' in str(ln) for ln in out)


def test_fcm_key_fix_paste_rejects_wrong_project_then_cancel(tmp_path):
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'transmute.json')) as f:
        data = json.loads(f.read())
    wrong = json.dumps({'type': 'service_account', 'project_id': 'OTHER-proj',
                        'private_key_id': 'x', 'client_email': 'a@b'})
    answers = iter(['p'] + wrong.split('\n') + ['c'])
    out = []
    import pytest
    with pytest.raises(RuntimeError):
        audit.fcm_key_interactive_fix(
            healthy_services(), d, 'demo-proj', data, 'a@b',
            input_fn=lambda _='': next(answers), print_fn=out.append)
    assert any('OTHER-proj' in str(ln) for ln in out)


def test_fcm_key_fix_mint_prints_json_and_server_warning(tmp_path):
    import base64
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'transmute.json')) as f:
        data = json.loads(f.read())
    minted = {'type': 'service_account', 'project_id': 'demo-proj',
              'client_email': data['fcmServiceAccount']}
    key_payload = base64.b64encode(json.dumps(minted).encode()).decode()
    services = healthy_services()
    services['iam'] = FakeResource(projects=FakeResource(serviceAccounts=FakeResource(
        get=lambda name: {'email': 'x'},
        keys=FakeResource(create=lambda name, body: {
            'name': 'projects/p/serviceAccounts/x/keys/abcdef123456',
            'privateKeyData': key_payload}))))
    answers = iter(['m'])
    out = []
    audit.fcm_key_interactive_fix(
        services, d, 'demo-proj', data, data['fcmServiceAccount'],
        input_fn=lambda _='': next(answers), print_fn=out.append)
    text = '\n'.join(str(ln) for ln in out)
    assert 'ACTION REQUIRED' in text
    assert 'np1.netpark.us' in text
    assert 'Firebase Cloud Messaging Service Account JSON File' in text
    assert '"client_email"' in text  # the JSON is printed for copy/paste


def test_missing_inferable_field_is_fixable(tmp_path):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.loads(f.read())
    del data['Additional-AndroidSHA-1Fingerprint']
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'transmute.json inferable fields'][0]
    assert check.status == ISSUE and check.fix is not None
    check.fix()
    with open(tj) as f:
        data = json.loads(f.read())
    assert data['Additional-AndroidSHA-1Fingerprint'] == '22:66:DB'


def test_maps_key_not_found_message_and_fix(tmp_path):
    services = healthy_services()
    d = make_brand(tmp_path)
    # transmute records a key string that exists in some OTHER (legacy) project
    with open(os.path.join(d, 'transmute.json')) as f:
        data = json.load(f)
    data['androidGoogleMapsSDKApiKey'] = 'AIzaSyLEGACY-from-old-cloud-project-XYZW'
    with open(os.path.join(d, 'transmute.json'), 'w') as f:
        json.dump(data, f)

    from fakes import FakeResource
    key_by_name = {
        'k-ios': {'name': 'k-ios', 'displayName': 'iOS Maps',
                  'restrictions': {'iosKeyRestrictions': {'allowedBundleIds': ['com.demo.ios']}}},
        'k-places': {'name': 'k-places', 'displayName': 'Server Places',
                     'restrictions': {'apiTargets': [
                         {'service': 'places-backend.googleapis.com'},
                         {'service': 'places.googleapis.com'}]}},
    }
    strings = {'k-ios': 'AIza-ios', 'k-places': 'AIza-places'}
    created = []

    def fake_create(parent, body):
        created.append((parent, body))
        return {'name': 'op1'}

    services['apikeys'] = FakeResource(
        projects=FakeResource(locations=FakeResource(keys=FakeResource(
            list=lambda **kw: {'keys': list(key_by_name.values())},
            getKeyString=lambda name: {'keyString': strings[name]},
            create=fake_create))),
        operations=FakeResource(get=lambda name: {
            'done': True, 'response': {'keyString': 'AIza-newly-created'}}))

    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'Android Maps key'][0]
    assert check.status == ISSUE
    # names the transmute field, part of the key string, and the project it's absent from
    assert 'androidGoogleMapsSDKApiKey' in check.detail
    assert 'AIzaSyLEGACY' in check.detail
    assert 'demo-proj' in check.detail
    assert check.fix is not None and check.console_url

    check.fix()  # no android-looking key exists in the fixture -> creates one
    assert created and created[0][0] == 'projects/demo-proj/locations/global'
    assert created[0][1]['displayName'] == 'Android Loyalty App Google Maps SDK API Key'
    assert created[0][1]['restrictions']['apiTargets'] == [
        {'service': 'maps-android-backend.googleapis.com'}]
    with open(os.path.join(d, 'transmute.json')) as f:
        assert json.load(f)['androidGoogleMapsSDKApiKey'] == 'AIza-newly-created'


def test_empty_key_field_is_fixable_too(tmp_path):
    services = healthy_services()
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'transmute.json')) as f:
        data = json.load(f)
    data['serverGooglePlacesAPIKey'] = ''
    with open(os.path.join(d, 'transmute.json'), 'w') as f:
        json.dump(data, f)
    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'Places server key'][0]
    assert check.status == ISSUE and check.fix is not None
    assert 'Loyalty App Google Places API Key for netPark Server' in check.detail
    assert 'demo-proj' in check.detail
    check.fix()  # fixture HAS a places-looking key; non-interactive -> reuse it
    with open(os.path.join(d, 'transmute.json')) as f:
        assert json.load(f)['serverGooglePlacesAPIKey'] == 'AIza-places'


def test_key_fix_can_create_new_even_when_candidates_exist(tmp_path, monkeypatch):
    services = healthy_services()
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'transmute.json')) as f:
        data = json.load(f)
    data['serverGooglePlacesAPIKey'] = ''
    with open(os.path.join(d, 'transmute.json'), 'w') as f:
        json.dump(data, f)
    created = []

    def fake_create(parent, body):
        created.append((parent, body))
        return {'name': 'op1'}

    services['apikeys'] = FakeResource(
        projects=FakeResource(locations=FakeResource(keys=FakeResource(
            list=lambda **kw: {'keys': [
                {'name': 'k-places', 'displayName': 'Server Places'}]},
            getKeyString=lambda name: {'keyString': 'AIza-old-places'},
            create=fake_create))),
        operations=FakeResource(get=lambda name: {
            'done': True, 'response': {'keyString': 'AIza-brand-new'}}))
    monkeypatch.setattr('builtins.input', lambda prompt='': 'n')
    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'Places server key'][0]
    check.fix()  # user answers [N]ew -> creates despite the reusable candidate
    assert created and created[0][1]['displayName'] == \
        'Loyalty App Google Places API Key for netPark Server'
    with open(os.path.join(d, 'transmute.json')) as f:
        assert json.load(f)['serverGooglePlacesAPIKey'] == 'AIza-brand-new'


def test_places_server_update_notice_contents():
    lines = []
    audit.places_server_update_notice('branded_loyalty/ftmyers_2195',
                                      'AIza-brand-new-key', print_fn=lines.append)
    text = '\n'.join(lines)
    assert 'ACTION REQUIRED' in text and 'netPark SERVER' in text
    assert 'https://np1.netpark.us/netPark/2195/' in text
    assert "Maintenance -> App/Website Settings -> General" in text
    assert "'Loyalty App Google Places API Key'" in text
    assert 'AIza-brand-new-key' in text
    assert 'do NOT delete' in text


def test_apns_missing_key_fix_claims_unclaimed_backup(tmp_path, monkeypatch):
    from brandtool_lib.report import BrandReport
    d = make_brand(tmp_path)
    # brand has no APNs key file and no recorded id; an unclaimed backup exists
    os.remove(os.path.join(d, 'AuthKey_APNS999999.p8'))
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.load(f)
    del data['apnsKeyId']
    with open(tj, 'w') as f:
        json.dump(data, f)

    r = BrandReport('demo_brand')
    r.project_id = 'demo-proj'
    audit._audit_apns_key(r, d, data)
    check = [c for c in r.checks if c.name == 'APNs key file'][0]
    assert check.status == ISSUE and check.fix is not None
    # the per-app Cloud Messaging URL is present for the user to go look
    assert 'demo-proj/settings/cloudmessaging/ios:com.demo.ios' in check.console_url
    assert 'APNS999999' in check.detail  # the unclaimed candidate is named

    monkeypatch.setattr('builtins.input', lambda prompt='': 'APNS999999')
    check.fix()
    with open(tj) as f:
        assert json.load(f)['apnsKeyId'] == 'APNS999999'
    assert os.path.exists(os.path.join(d, 'AuthKey_APNS999999.p8'))


def test_apns_missing_key_fix_records_id_without_backup(tmp_path, monkeypatch, capsys):
    from brandtool_lib.report import BrandReport
    d = make_brand(tmp_path)
    os.remove(os.path.join(d, 'AuthKey_APNS999999.p8'))
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.load(f)
    del data['apnsKeyId']
    with open(tj, 'w') as f:
        json.dump(data, f)

    r = BrandReport('demo_brand')
    r.project_id = 'demo-proj'
    audit._audit_apns_key(r, d, data)
    check = [c for c in r.checks if c.name == 'APNs key file'][0]
    # user reads a key id from Firebase that has no local backup file
    monkeypatch.setattr('builtins.input', lambda prompt='': 'ZZ11223344')
    check.fix()
    out = capsys.readouterr().out
    with open(tj) as f:
        assert json.load(f)['apnsKeyId'] == 'ZZ11223344'
    assert not os.path.exists(os.path.join(d, 'AuthKey_ZZ11223344.p8'))
    assert 'locate the .p8' in out


def test_places_restriction_issue_names_key_current_and_missing_targets(tmp_path):
    # newark's case: the Places key allows only the legacy places-backend API
    services = healthy_services()
    key_by_name = {
        'k-places': {'name': 'k-places', 'displayName': 'Places API',
                     'restrictions': {'apiTargets': [
                         {'service': 'places-backend.googleapis.com'}]}},
    }
    services['apikeys'] = FakeResource(projects=FakeResource(locations=FakeResource(
        keys=FakeResource(
            list=lambda **kw: {'keys': list(key_by_name.values())},
            getKeyString=lambda name: {'keyString': 'AIza-places'}))))
    d = make_brand(tmp_path)
    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'Places server key restriction'][0]
    assert check.status == ISSUE
    assert '"Places API"' in check.detail                      # the key's name
    assert 'currently allows places-backend.googleapis.com' in check.detail
    assert 'missing places.googleapis.com' in check.detail
    assert check.fix is not None


def test_missing_firebase_apps_are_fixable(tmp_path, monkeypatch):
    services = healthy_services()
    # neither the new package nor the new bundle id has a Firebase app yet
    android = FakeResource(list=lambda parent: {'apps': []})
    ios = FakeResource(list=lambda parent: {'apps': []})
    services['firebase'] = FakeResource(projects=FakeResource(androidApps=android,
                                                              iosApps=ios))
    d = make_brand(tmp_path)
    r = audit.audit_brand(services, CFG, d)
    checks = {c.name: c for c in r.checks}
    a, i = checks['Firebase Android app'], checks['Firebase iOS app']
    assert a.status == ISSUE and a.fix is not None and '[F]ix creates it' in a.detail
    assert i.status == ISSUE and i.fix is not None and '[F]ix creates it' in i.detail

    calls = []
    monkeypatch.setattr(audit.fb, 'create_android_app',
                        lambda fbase, pid, name, pkg: calls.append(('android', pid, pkg))
                        or 'new-android-id')
    monkeypatch.setattr(audit.fb, 'add_sha',
                        lambda fbase, pid, app, h, t: calls.append(('sha', h, t)))
    monkeypatch.setattr(audit.fb, 'download_android_config',
                        lambda fbase, pid, app, bdir: calls.append(('gsjson', app, bdir)))
    monkeypatch.setattr(audit.fb, 'create_ios_app',
                        lambda fbase, pid, name, bid, team_id=None, app_store_id=None:
                        calls.append(('ios', bid, team_id, app_store_id)) or 'new-ios-id')
    monkeypatch.setattr(audit.fb, 'download_ios_config',
                        lambda fbase, pid, app, bdir: calls.append(('plist', app, bdir)))
    a.fix()
    i.fix()
    kinds = [c[0] for c in calls]
    assert kinds.count('android') == 1 and kinds.count('ios') == 1
    assert kinds.count('sha') == 3          # debug SHA1 + release SHA1 + SHA256
    assert ('gsjson', 'new-android-id', d) in calls
    assert ('plist', 'new-ios-id', d) in calls
    ios_call = [c for c in calls if c[0] == 'ios'][0]
    assert ios_call[2] == 'TEAM123456' and ios_call[3] == '6446444444'


def test_restriction_fix_warns_about_removed_entries(tmp_path):
    # parkngo's case: the key still allows the OLD package; patching to the new
    # package must warn that old-package builds lose access
    services = healthy_services()
    key_by_name = {
        'k-android': {'name': 'k-android', 'displayName': 'Android Maps',
                      'restrictions': {'androidKeyRestrictions': {
                          'allowedApplications': [
                              {'sha1Fingerprint': '14AE72', 'packageName': 'com.OLD.app'},
                              {'sha1Fingerprint': '2266DB', 'packageName': 'com.OLD.app'}]},
                          'apiTargets': [{'service': 'maps-android-backend.googleapis.com'}]}},
    }
    services['apikeys'] = FakeResource(projects=FakeResource(locations=FakeResource(
        keys=FakeResource(
            list=lambda **kw: {'keys': list(key_by_name.values())},
            getKeyString=lambda name: {'keyString': 'AIza-android'}))))
    d = make_brand(tmp_path)
    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'Android Maps key restriction'][0]
    assert check.status == ISSUE
    assert 'WARNING' in check.detail and 'LOSE access' in check.detail
    assert 'com.OLD.app' in check.detail


def test_firebase_options_advice_skips_switch_when_brand_is_active(tmp_path, monkeypatch):
    d = make_brand(tmp_path)
    with open(os.path.join(d, 'firebase_options.dart'), 'w') as f:
        f.write('// no live ids in here')
    monkeypatch.setattr(audit.cfgmod, 'is_active_brand', lambda bd: True)
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'firebase_options.dart in sync'][0]
    assert 'already the ACTIVE brand' in check.detail
    assert '--switch' not in check.detail
    assert 'flutterfire configure' in check.detail


def test_root_transmute_sync_check(tmp_path, monkeypatch):
    d = make_brand(tmp_path)
    monkeypatch.setattr(audit.cfgmod, 'is_active_brand', lambda bd: True)
    monkeypatch.setattr(audit.cfgmod, 'REPO_ROOT', str(tmp_path))

    # in sync: root copy identical to the brand dir copy
    with open(os.path.join(d, 'transmute.json')) as f:
        brand_data = json.load(f)
    root = tmp_path / 'transmute.json'
    root.write_text(json.dumps(brand_data))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'root transmute.json sync'][0]
    assert check.status == OK and 'reads ONLY the brand dir' in check.detail

    # differing: root has an edited field and is NEWER
    brand_data['appName'] = 'Edited In Working Tree'
    root.write_text(json.dumps(brand_data))
    old = os.path.getmtime(os.path.join(d, 'transmute.json')) - 3600
    os.utime(os.path.join(d, 'transmute.json'), (old, old))
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'root transmute.json sync'][0]
    assert check.status == ISSUE and check.flash
    assert 'You must resolve the differences' in check.detail
    assert 'appName' in check.detail and 'Edited In Working Tree' in check.detail
    assert 'ROOT (working tree) is NEWER' in check.detail
    assert 'transmute --update' in check.detail

    # differing but BRAND DIR newer (normal after audit fixes): calm reminder, no flash
    now = os.path.getmtime(str(root)) + 3600
    os.utime(os.path.join(d, 'transmute.json'), (now, now))
    from brandtool_lib.report import INFO
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'root transmute.json sync'][0]
    assert check.status == INFO and not check.flash
    assert 'REMEMBER to run transmute --switch' in check.detail
    assert 'BRAND DIRECTORY' in check.detail


def test_root_transmute_sync_absent_for_inactive_brand(tmp_path, monkeypatch):
    d = make_brand(tmp_path)
    monkeypatch.setattr(audit.cfgmod, 'is_active_brand', lambda bd: False)
    r = audit.audit_brand(healthy_services(), CFG, d)
    assert not any(c.name == 'root transmute.json sync' for c in r.checks)


def test_apns_firebase_upload_unconfirmed_is_flagged_and_confirmable(tmp_path, monkeypatch):
    d = make_brand(tmp_path)
    tj = os.path.join(d, 'transmute.json')
    with open(tj) as f:
        data = json.load(f)
    del data['apnsUploadedForIosAppId']   # e.g. freshly re-created iOS app
    with open(tj, 'w') as f:
        json.dump(data, f)
    r = audit.audit_brand(healthy_services(), CFG, d)
    check = [c for c in r.checks if c.name == 'APNs key in Firebase'][0]
    assert check.status == ISSUE and check.flash and check.fix is not None
    assert '1:1:ios:bbb' in check.detail
    assert 'settings/cloudmessaging/ios:com.demo.ios' in check.console_url

    monkeypatch.setattr('builtins.input', lambda prompt='': 'y')
    check.fix()
    with open(tj) as f:
        assert json.load(f)['apnsUploadedForIosAppId'] == '1:1:ios:bbb'


def test_apns_firebase_upload_stale_after_app_recreation(tmp_path):
    d = make_brand(tmp_path)   # confirmed for 1:1:ios:bbb
    services = healthy_services()
    # live iOS app has a NEW app id (bundle id change -> app re-created)
    ios = FakeResource(list=lambda parent: {'apps': [
        {'bundleId': 'com.demo.ios', 'appId': '1:1:ios:NEW',
         'teamId': 'TEAM123456', 'appStoreId': '6446444444'}]})
    android = FakeResource(
        list=lambda parent: {'apps': [{'packageName': 'com.demo.app',
                                       'appId': '1:1:android:aaa'}]},
        sha=FakeResource(list=lambda parent: {'certificates': [
            {'shaHash': '14AE72'}, {'shaHash': '2266DB'}, {'shaHash': '165287'}]}))
    services['firebase'] = FakeResource(projects=FakeResource(androidApps=android,
                                                              iosApps=ios))
    r = audit.audit_brand(services, CFG, d)
    check = [c for c in r.checks if c.name == 'APNs key in Firebase'][0]
    assert check.status == ISSUE
    assert 'was confirmed for previous iOS app' in check.detail
    assert '1:1:ios:bbb' in check.detail and '1:1:ios:NEW' in check.detail


def test_apns_firebase_upload_confirmed_is_ok(tmp_path):
    r = audit.audit_brand(healthy_services(), CFG, make_brand(tmp_path))
    check = [c for c in r.checks if c.name == 'APNs key in Firebase'][0]
    assert check.status == OK and 'upload confirmed' in check.detail
