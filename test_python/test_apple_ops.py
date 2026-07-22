from brandtool_lib import apple_ops


class FakeAscClient:
    """get() keyed by path; params ignored."""

    def __init__(self, gets=None):
        self.gets = gets or {}
        self.posted = []

    def get(self, path, params=None):
        return self.gets.get(path, [])

    def post(self, path, body):
        self.posted.append((path, body))
        return {'data': {'id': 'created-id',
                         'attributes': body['data']['attributes']}}


BUNDLE = {'id': 'B1', 'attributes': {'identifier': 'com.demo.ios', 'seedId': 'TEAM123456'}}


def test_find_bundle_id_requires_exact_match():
    client = FakeAscClient({'/bundleIds': [
        {'id': 'B0', 'attributes': {'identifier': 'com.demo.ios.extra'}}, BUNDLE]})
    assert apple_ops.find_bundle_id(client, 'com.demo.ios')['id'] == 'B1'
    assert apple_ops.find_bundle_id(client, 'com.other') is None


def test_register_bundle_id_posts_ios_platform():
    client = FakeAscClient()
    res = apple_ops.register_bundle_id(client, 'com.demo.ios', 'Demo App')
    path, body = client.posted[0]
    assert path == '/bundleIds'
    assert body['data']['attributes'] == {
        'identifier': 'com.demo.ios', 'name': 'Demo App', 'platform': 'IOS'}
    assert res['id'] == 'created-id'


def test_capabilities_listing_and_missing():
    client = FakeAscClient({'/bundleIds/B1/bundleIdCapabilities': [
        {'attributes': {'capabilityType': 'PUSH_NOTIFICATIONS'}}]})
    assert apple_ops.list_capability_types(client, BUNDLE) == {'PUSH_NOTIFICATIONS'}
    assert apple_ops.missing_capabilities(
        client, BUNDLE, ['PUSH_NOTIFICATIONS', 'APPLE_ID_AUTH']) == ['APPLE_ID_AUTH']


def test_enable_capability_posts_relationship():
    client = FakeAscClient()
    apple_ops.enable_capability(client, BUNDLE, 'ASSOCIATED_DOMAINS')
    path, body = client.posted[0]
    assert path == '/bundleIdCapabilities'
    assert body['data']['attributes'] == {'capabilityType': 'ASSOCIATED_DOMAINS'}
    assert body['data']['relationships']['bundleId']['data'] == {
        'type': 'bundleIds', 'id': 'B1'}


def test_enable_capability_apple_id_auth_sends_primary_consent():
    # Bare APPLE_ID_AUTH is rejected by the API with 409 ENTITY_ERROR
    # "Please select at least one configuration for Sign In with Apple."
    client = FakeAscClient()
    apple_ops.enable_capability(client, BUNDLE, 'APPLE_ID_AUTH')
    _, body = client.posted[0]
    attrs = body['data']['attributes']
    assert attrs['capabilityType'] == 'APPLE_ID_AUTH'
    assert attrs['settings'] == [{'key': 'APPLE_ID_AUTH_APP_CONSENT',
                                  'options': [{'key': 'PRIMARY_APP_CONSENT'}]}]


def test_enable_capabilities_continues_past_failure():
    class FailFirstClient(FakeAscClient):
        def post(self, path, body):
            if body['data']['attributes']['capabilityType'] == 'APPLE_ID_AUTH':
                raise RuntimeError('409 ENTITY_ERROR')
            return super().post(path, body)

    client = FailFirstClient()
    try:
        apple_ops.enable_capabilities(
            client, BUNDLE, ['APPLE_ID_AUTH', 'ASSOCIATED_DOMAINS', 'WALLET'])
        assert False, 'expected RuntimeError'
    except RuntimeError as e:
        assert 'APPLE_ID_AUTH' in str(e) and '409' in str(e)
    posted_caps = [b['data']['attributes']['capabilityType'] for _, b in client.posted]
    assert posted_caps == ['ASSOCIATED_DOMAINS', 'WALLET']


def test_seed_helpers():
    assert apple_ops.seed_id(BUNDLE) == 'TEAM123456'
    assert apple_ops.seed_matches_team(BUNDLE, 'TEAM123456')
    assert not apple_ops.seed_matches_team(BUNDLE, 'OTHER')


def test_expiring_certificates_window():
    import datetime
    soon = (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=10)).isoformat().replace('+00:00', 'Z')
    far = (datetime.datetime.now(datetime.timezone.utc)
           + datetime.timedelta(days=400)).isoformat().replace('+00:00', 'Z')
    client = FakeAscClient({'/certificates': [
        {'attributes': {'name': 'Dist', 'certificateType': 'IOS_DISTRIBUTION',
                        'expirationDate': soon}},
        {'attributes': {'name': 'Dev', 'certificateType': 'DEVELOPMENT',
                        'expirationDate': far}}]})
    result = apple_ops.expiring_certificates(client, days=90)
    assert len(result) == 1 and result[0][0] == 'Dist'
    assert 0 <= result[0][3] <= 10   # days_left included


def test_expiring_certificates_flags_expired_and_sorts_soonest_first():
    import datetime
    past = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=5)).isoformat().replace('+00:00', 'Z')
    soon = (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=20)).isoformat().replace('+00:00', 'Z')
    client = FakeAscClient({'/certificates': [
        {'attributes': {'name': 'Dev', 'certificateType': 'DEVELOPMENT',
                        'expirationDate': soon}},
        {'attributes': {'name': 'Dead', 'certificateType': 'IOS_DISTRIBUTION',
                        'expirationDate': past}}]})
    result = apple_ops.expiring_certificates(client, days=60)
    assert [c[0] for c in result] == ['Dead', 'Dev']   # soonest (expired) first
    assert result[0][3] < 0 and result[1][3] > 0


def test_verify_key():
    client = FakeAscClient({'/bundleIds': [BUNDLE,
        {'id': 'B2', 'attributes': {'identifier': 'x', 'seedId': 'TEAM123456'}}]})
    seeds, count = apple_ops.verify_key(client)
    assert seeds == {'TEAM123456'} and count == 2


def test_find_app_exact_match():
    client = FakeAscClient({'/apps': [
        {'id': 'A1', 'attributes': {'bundleId': 'com.demo.ios'}}]})
    assert apple_ops.find_app(client, 'com.demo.ios')['id'] == 'A1'
    assert apple_ops.find_app(client, 'com.none') is None
