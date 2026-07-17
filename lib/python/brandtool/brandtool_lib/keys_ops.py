"""Google Cloud API-key inspection and creation (apikeys v2)."""
import os
import re

from .firebase_ops import wait_for_operation

# Legacy Places API + Places API (New). NOTE: 'places-new-backend.googleapis.com'
# is NOT a real service (SERVICE_CONFIG_NOT_FOUND) - the new API is places.googleapis.com.
PLACES_SERVICES = ['places-backend.googleapis.com', 'places.googleapis.com']
MAPS_ANDROID_SERVICE = 'maps-android-backend.googleapis.com'
MAPS_IOS_SERVICE = 'maps-ios-backend.googleapis.com'

# Per-transmute-field key purpose: the display name for keys the tool creates,
# the API service(s) the key is locked to, and the display-name tokens that
# recognize an existing key serving this purpose (matches both manually created
# legacy names and old tool names; Firebase's auto-created keys contain no
# 'maps'/'places' token, so they are never picked up). No brand prefix in the
# names: the project already identifies the brand, and displayName is capped at
# MAX_DISPLAY_NAME_LEN characters.
KEY_PURPOSES = {
    'androidGoogleMapsSDKApiKey': {
        'name': 'Android Loyalty App Google Maps SDK API Key',
        'tokens': ('android', 'maps'), 'services': [MAPS_ANDROID_SERVICE]},
    'iosGoogleMapsSDKApiKey': {
        'name': 'iOS Loyalty App Google Maps SDK API Key',
        'tokens': ('ios', 'maps'), 'services': [MAPS_IOS_SERVICE]},
    'serverGooglePlacesAPIKey': {
        'name': 'Loyalty App Google Places API Key for netPark Server',
        'tokens': ('places',), 'services': PLACES_SERVICES},
}

MAX_DISPLAY_NAME_LEN = 63   # API Keys v2 displayName hard limit


def key_display_name(field, data, brand_dir=None):
    name = KEY_PURPOSES[field]['name']
    if field == 'serverGooglePlacesAPIKey':
        # suffix the netPark location number(s) so the key is traceable to the
        # server admin page(s) (https://np1.netpark.us/netPark/<locationId>/)
        source = os.path.basename(os.path.normpath(
            brand_dir or data.get('brand_source_directory') or ''))
        ids = re.findall(r'\d+', source)
        if ids:
            name += ' ' + ' '.join(ids)
            if len(name) > MAX_DISPLAY_NAME_LEN:
                # many-location brands (fine has 4 ids): drop the prefix to fit
                name = name.replace('Loyalty App ', '', 1)
    return name


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


def places_restriction_ok(key):
    return api_targets_ok(key, PLACES_SERVICES)


def android_restrictions_body(fingerprints_sha1, package_name):
    return {'androidKeyRestrictions': {'allowedApplications': [
        {'sha1Fingerprint': fp, 'packageName': package_name} for fp in fingerprints_sha1]},
        'apiTargets': [{'service': MAPS_ANDROID_SERVICE}]}


def ios_restrictions_body(bundle_id):
    return {'iosKeyRestrictions': {'allowedBundleIds': [bundle_id]},
            'apiTargets': [{'service': MAPS_IOS_SERVICE}]}


def places_restrictions_body():
    return {'apiTargets': [{'service': s} for s in PLACES_SERVICES]}


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
