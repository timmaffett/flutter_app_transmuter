"""App Store Connect operations for brandtool: App IDs, capabilities, apps, certs.

All functions take an AscClient (or any object with .get/.post) so tests can fake it.
"""
import datetime

IDENTIFIERS_URL = 'https://developer.apple.com/account/resources/identifiers/list'
APPS_URL = 'https://appstoreconnect.apple.com/apps'
AGREEMENTS_URL = 'https://appstoreconnect.apple.com/agreements'


def find_app(client, bundle_id):
    apps = client.get('/apps', params={'filter[bundleId]': bundle_id})
    for app in apps:
        if app.get('attributes', {}).get('bundleId') == bundle_id:
            return app
    return None


def find_bundle_id(client, bundle_id):
    # The API's filter[identifier] is a substring match - require exact equality.
    resources = client.get('/bundleIds', params={'filter[identifier]': bundle_id})
    for res in resources:
        if res.get('attributes', {}).get('identifier') == bundle_id:
            return res
    return None


def register_bundle_id(client, bundle_id, name):
    body = {'data': {'type': 'bundleIds', 'attributes': {
        'identifier': bundle_id, 'name': name, 'platform': 'IOS'}}}
    return client.post('/bundleIds', body).get('data', {})


def list_capability_types(client, bundle_id_resource):
    caps = client.get(f"/bundleIds/{bundle_id_resource['id']}/bundleIdCapabilities")
    return {c.get('attributes', {}).get('capabilityType') for c in caps}


# Capabilities the API refuses to enable without a configuration. Sign In with
# Apple demands a consent choice (portal: "Enable as a primary App ID" vs group
# with another App ID); every brand is a standalone app, so primary is correct.
CAPABILITY_SETTINGS = {
    'APPLE_ID_AUTH': [{'key': 'APPLE_ID_AUTH_APP_CONSENT',
                       'options': [{'key': 'PRIMARY_APP_CONSENT'}]}],
}


def enable_capability(client, bundle_id_resource, capability_type):
    attributes = {'capabilityType': capability_type}
    if capability_type in CAPABILITY_SETTINGS:
        attributes['settings'] = CAPABILITY_SETTINGS[capability_type]
    body = {'data': {'type': 'bundleIdCapabilities',
                     'attributes': attributes,
                     'relationships': {'bundleId': {'data': {
                         'type': 'bundleIds', 'id': bundle_id_resource['id']}}}}}
    client.post('/bundleIdCapabilities', body)


def enable_capabilities(client, bundle_id_resource, capability_types):
    """Enable each capability; one failing does not block the rest.
    Raises RuntimeError at the end listing every capability that failed."""
    failures = []
    for cap in capability_types:
        try:
            enable_capability(client, bundle_id_resource, cap)
        except Exception as e:
            failures.append(f'{cap}: {e}')
    if failures:
        raise RuntimeError('; '.join(failures))


def missing_capabilities(client, bundle_id_resource, required):
    have = list_capability_types(client, bundle_id_resource)
    return [c for c in required if c not in have]


def seed_id(bundle_id_resource):
    return bundle_id_resource.get('attributes', {}).get('seedId', '')


def seed_matches_team(bundle_id_resource, team_id):
    return seed_id(bundle_id_resource) == team_id


def expiring_certificates(client, days=90):
    """(name, certificateType, yyyy-mm-dd, days_left) for certs expiring within
    `days`; days_left is negative for already-expired certs. Soonest first."""
    now = datetime.datetime.now(datetime.timezone.utc)
    soon = []
    for cert in client.get('/certificates'):
        attrs = cert.get('attributes', {})
        exp = attrs.get('expirationDate')
        if not exp:
            continue
        exp_dt = datetime.datetime.fromisoformat(exp.replace('Z', '+00:00'))
        days_left = (exp_dt - now).days
        if days_left <= days:
            soon.append((attrs.get('name', '?'), attrs.get('certificateType', '?'),
                         exp[:10], days_left))
    return sorted(soon, key=lambda c: c[3])


def verify_key(client):
    """add-asc-key live check: (distinct team seedIds, count of visible bundle ids)."""
    resources = client.get('/bundleIds')
    seeds = {seed_id(r) for r in resources if seed_id(r)}
    return seeds, len(resources)
