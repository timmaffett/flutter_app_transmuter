"""Google Cloud API-key inspection and creation (apikeys v2)."""
import os
import re

from .firebase_ops import wait_for_operation

# Key purposes come from transmute_provisioning.yaml's api_keys: list. Each
# purpose dict: field (transmute.json entry), name (displayName template,
# may contain {customerIds}/{customerId}), label (audit report label),
# restriction (android | ios | api_only), services (API targets),
# match_tokens (adopt-by-name), optional name_overflow_strip + server_copy.

MAX_DISPLAY_NAME_LEN = 63   # API Keys v2 displayName hard limit


def key_display_name(purpose, data, brand_dir=None, customer_id_pattern=r'\d+'):
    """Render the purpose's displayName template. Customer ids (netPark:
    "location ids") come from the brand dir name; if the rendered name blows
    the 63-char cap, the configured name_overflow_strip prefix is dropped."""
    name = purpose['name']
    if '{customerIds}' in name or '{customerId}' in name:
        source = os.path.basename(os.path.normpath(
            brand_dir or data.get('brand_source_directory') or ''))
        ids = re.findall(customer_id_pattern, source)
        name = (name.replace('{customerIds}', ' '.join(ids))
                    .replace('{customerId}', ids[0] if ids else '')).strip()
        if len(name) > MAX_DISPLAY_NAME_LEN and purpose.get('name_overflow_strip'):
            name = name.replace(purpose['name_overflow_strip'], '', 1)
    return name


def purpose_for_field(cfg, field):
    for p in cfg.get('apiKeyPurposes', []):
        if p['field'] == field:
            return p
    return None


def list_keys(apikeys, project_id):
    parent = f'projects/{project_id}/locations/global'
    keys, page_token = [], None
    while True:
        resp = apikeys.projects().locations().keys().list(
            parent=parent, pageSize=300, pageToken=page_token).execute()
        keys.extend(resp.get('keys', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            return keys


def key_string(apikeys, key_name):
    return apikeys.projects().locations().keys().getKeyString(
        name=key_name).execute()['keyString']


def find_key_by_string(apikeys, project_id, wanted_key_string):
    for key in list_keys(apikeys, project_id):
        if key_string(apikeys, key['name']) == wanted_key_string:
            return key
    return None


def android_restriction_missing(key, fingerprints_sha1, package_name):
    """Cleaned SHA-1s (lowercase, no colons) not allowed for package_name by this key."""
    allowed = {(a.get('sha1Fingerprint', '').lower(), a.get('packageName'))
               for a in key.get('restrictions', {})
               .get('androidKeyRestrictions', {}).get('allowedApplications', [])}
    return [fp for fp in fingerprints_sha1 if (fp.lower(), package_name) not in allowed]


def ios_restriction_ok(key, bundle_id):
    return bundle_id in key.get('restrictions', {}).get(
        'iosKeyRestrictions', {}).get('allowedBundleIds', [])


def api_targets(key):
    """The set of API services this key is restricted to (empty = ALL APIs)."""
    return {t.get('service') for t in key.get('restrictions', {}).get('apiTargets', [])}


def api_targets_ok(key, services):
    return set(services) <= api_targets(key)


def android_restrictions_body(fingerprints_sha1, package_name, services):
    return {'androidKeyRestrictions': {'allowedApplications': [
        {'sha1Fingerprint': fp, 'packageName': package_name} for fp in fingerprints_sha1]},
        'apiTargets': [{'service': s} for s in services]}


def ios_restrictions_body(bundle_id, services):
    return {'iosKeyRestrictions': {'allowedBundleIds': [bundle_id]},
            'apiTargets': [{'service': s} for s in services]}


def api_only_restrictions_body(services):
    return {'apiTargets': [{'service': s} for s in services]}


def update_restrictions(apikeys, key, restrictions):
    op = apikeys.projects().locations().keys().patch(
        name=key['name'], updateMask='restrictions',
        body={'restrictions': restrictions}).execute()
    wait_for_operation(apikeys, op['name'])


def find_keys_by_tokens(apikeys, project_id, tokens):
    """Keys whose display name contains ALL tokens (case-insensitive)."""
    tokens = [t.lower() for t in tokens]
    return [k for k in list_keys(apikeys, project_id)
            if all(t in (k.get('displayName') or '').lower() for t in tokens)]


def restriction_removals(key, new_restrictions):
    """Human-readable list of currently-allowed entries that a wholesale
    restrictions PATCH (update_restrictions/adopt_key) would REMOVE - builds or
    servers still using them lose access the moment the patch lands."""
    removed = []
    cur = key.get('restrictions', {})
    cur_apps = {(a.get('sha1Fingerprint', '').lower(), a.get('packageName'))
                for a in cur.get('androidKeyRestrictions', {})
                .get('allowedApplications', [])}
    new_apps = {(a.get('sha1Fingerprint', '').lower(), a.get('packageName'))
                for a in new_restrictions.get('androidKeyRestrictions', {})
                .get('allowedApplications', [])}
    removed += [f'Android {pkg} (cert {fp[:12]}...)'
                for fp, pkg in sorted(cur_apps - new_apps) if pkg]
    cur_bundles = set(cur.get('iosKeyRestrictions', {}).get('allowedBundleIds', []))
    new_bundles = set(new_restrictions.get('iosKeyRestrictions', {})
                      .get('allowedBundleIds', []))
    removed += [f'iOS bundle id {b}' for b in sorted(cur_bundles - new_bundles)]
    new_targets = {t.get('service') for t in new_restrictions.get('apiTargets', [])}
    removed += [f'API target {s}' for s in sorted(api_targets(key) - new_targets) if s]
    return removed


def adopt_key(apikeys, key, restrictions):
    """Reuse an existing key for a brand purpose: OVERWRITE its restrictions with
    the desired app restriction + API target(s), then return its key string."""
    update_restrictions(apikeys, key, restrictions)
    return key_string(apikeys, key['name'])


def ensure_key(apikeys, project_id, display_name, restrictions, tokens=()):
    """Non-interactive provisioning: adopt the first key whose display name
    matches the purpose tokens (its restrictions get corrected), else create a
    new restricted key named display_name. Returns (key_string, action)."""
    matches = find_keys_by_tokens(apikeys, project_id, tokens) if tokens else []
    if matches:
        return adopt_key(apikeys, matches[0], restrictions), 'reused'
    return create_key(apikeys, project_id, display_name, restrictions), 'created'


def create_key(apikeys, project_id, display_name, restrictions):
    if len(display_name) > MAX_DISPLAY_NAME_LEN:
        raise ValueError(f'API key display name is {len(display_name)} chars; Google '
                         f'caps displayName at {MAX_DISPLAY_NAME_LEN}: "{display_name}"')
    op = apikeys.projects().locations().keys().create(
        parent=f'projects/{project_id}/locations/global',
        body={'displayName': display_name, 'restrictions': restrictions}).execute()
    res = wait_for_operation(apikeys, op['name'])
    return res['response']['keyString']
