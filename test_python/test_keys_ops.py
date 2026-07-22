from brandtool_lib import keys_ops


def android_key(pairs):
    return {'name': 'k', 'restrictions': {'androidKeyRestrictions': {'allowedApplications': [
        {'sha1Fingerprint': fp, 'packageName': pkg} for fp, pkg in pairs]}}}


def test_android_restriction_missing_is_case_insensitive():
    key = android_key([('14AE72', 'com.a'), ('2266DB', 'com.a')])
    assert keys_ops.android_restriction_missing(key, ['14ae72', '2266db'], 'com.a') == []
    assert keys_ops.android_restriction_missing(key, ['14ae72', 'ffffff'], 'com.a') == ['ffffff']
    assert keys_ops.android_restriction_missing(key, ['14ae72'], 'com.OTHER') == ['14ae72']


def test_android_restriction_missing_handles_unrestricted_key():
    assert keys_ops.android_restriction_missing({'name': 'k'}, ['aa'], 'com.a') == ['aa']


def test_ios_and_places_checks():
    ios = {'restrictions': {'iosKeyRestrictions': {'allowedBundleIds': ['com.a']}}}
    assert keys_ops.ios_restriction_ok(ios, 'com.a')
    assert not keys_ops.ios_restriction_ok(ios, 'com.b')
    places = {'restrictions': {'apiTargets': [
        {'service': 'places-backend.googleapis.com'},
        {'service': 'places.googleapis.com'}]}}
    both = ['places-backend.googleapis.com', 'places.googleapis.com']
    assert keys_ops.api_targets_ok(places, both)
    assert not keys_ops.api_targets_ok({'restrictions': {}}, both)


def test_restriction_bodies():
    body = keys_ops.android_restrictions_body(['aa', 'bb'], 'com.a', ['svc-a'])
    assert body['androidKeyRestrictions']['allowedApplications'] == [
        {'sha1Fingerprint': 'aa', 'packageName': 'com.a'},
        {'sha1Fingerprint': 'bb', 'packageName': 'com.a'}]
    assert body['apiTargets'] == [{'service': 'svc-a'}]
    ios = keys_ops.ios_restrictions_body('com.a', ['svc-i'])
    assert ios['iosKeyRestrictions'] == {'allowedBundleIds': ['com.a']}
    assert ios['apiTargets'] == [{'service': 'svc-i'}]
    assert keys_ops.api_only_restrictions_body(['a', 'b']) == {'apiTargets': [
        {'service': 'a'}, {'service': 'b'}]}


def test_api_targets_ok():
    key = {'restrictions': {'apiTargets': [
        {'service': 'maps-android-backend.googleapis.com'}]}}
    assert keys_ops.api_targets_ok(key, ['maps-android-backend.googleapis.com'])
    assert not keys_ops.api_targets_ok(key, ['maps-ios-backend.googleapis.com'])
    assert not keys_ops.api_targets_ok({'restrictions': {}},
                                       ['maps-android-backend.googleapis.com'])


ANDROID_P = {'field': 'androidGoogleMapsSDKApiKey',
             'name': 'Android Loyalty App Google Maps SDK API Key',
             'restriction': 'android',
             'services': ['maps-android-backend.googleapis.com'],
             'match_tokens': ['android', 'maps']}
SERVER_P = {'field': 'serverGooglePlacesAPIKey',
            'name': 'Loyalty App Google Places API Key for netPark Server {customerIds}',
            'restriction': 'api_only',
            'services': ['places-backend.googleapis.com', 'places.googleapis.com'],
            'match_tokens': ['places'],
            'name_overflow_strip': 'Loyalty App '}


def test_key_display_name_from_purpose():
    assert keys_ops.key_display_name(ANDROID_P, {}) ==         'Android Loyalty App Google Maps SDK API Key'
    assert keys_ops.key_display_name(
        SERVER_P, {}, 'branded_loyalty/ftmyers_2195') ==         'Loyalty App Google Places API Key for netPark Server 2195'
    # no ids anywhere -> template placeholder collapses cleanly
    assert keys_ops.key_display_name(SERVER_P, {}) ==         'Loyalty App Google Places API Key for netPark Server'


def test_customer_ids_overflow_strips_configured_prefix():
    data = {'brand_source_directory': 'branded_loyalty/fine_335_1535_2185_2190'}
    name = keys_ops.key_display_name(SERVER_P, data)
    assert name == 'Google Places API Key for netPark Server 335 1535 2185 2190'
    assert len(name) <= keys_ops.MAX_DISPLAY_NAME_LEN


def test_purpose_for_field():
    cfg = {'apiKeyPurposes': [ANDROID_P, SERVER_P]}
    assert keys_ops.purpose_for_field(cfg, 'serverGooglePlacesAPIKey') is SERVER_P
    assert keys_ops.purpose_for_field(cfg, 'nope') is None


def test_create_key_rejects_overlong_display_name():
    try:
        keys_ops.create_key(None, 'proj', 'x' * 64, {})
        assert False, 'expected ValueError'
    except ValueError as e:
        assert '63' in str(e)


def test_ensure_key_adopts_by_tokens_else_creates():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fakes import FakeResource

    created, patched = [], []

    def fake_create(parent, body):
        created.append((parent, body))
        return {'name': 'op1'}

    def fake_patch(name, updateMask, body):
        patched.append((name, updateMask, body))
        return {'name': 'op2'}

    def make_apikeys(existing_keys):
        keys = FakeResource(
            list=lambda **kw: {'keys': existing_keys},
            getKeyString=lambda name: {'keyString': f'AIza-string-of-{name}'},
            create=fake_create, patch=fake_patch)
        return FakeResource(
            projects=FakeResource(locations=FakeResource(keys=keys)),
            operations=FakeResource(get=lambda name: {
                'done': True, 'response': {'keyString': 'AIza-fresh-key'}}))

    # adopt: the manually-named legacy key matches the android+maps tokens;
    # its restrictions are forcibly corrected
    legacy = {'name': 'k1', 'displayName': 'FtMyers Loyalty Android Google Maps SDK API'}
    apikeys = make_apikeys([legacy])
    result, action = keys_ops.ensure_key(apikeys, 'proj', 'New Name', {'r': 1},
                                         tokens=('android', 'maps'))
    assert (result, action) == ('AIza-string-of-k1', 'reused')
    assert created == []
    assert patched == [('k1', 'restrictions', {'restrictions': {'r': 1}})]

    # Firebase auto-created keys do NOT match ('android' without 'maps') -> create
    auto = {'name': 'k2', 'displayName': 'Android key (auto created by Firebase)'}
    apikeys = make_apikeys([auto])
    result, action = keys_ops.ensure_key(apikeys, 'proj', 'Demo iOS Maps Key', {'r': 2},
                                         tokens=('android', 'maps'))
    assert (result, action) == ('AIza-fresh-key', 'created')
    assert created[0][0] == 'projects/proj/locations/global'
    assert created[0][1]['displayName'] == 'Demo iOS Maps Key'


def test_restriction_removals_lists_dropped_entries():
    # a key currently allowing the OLD package + an extra API target
    key = {'restrictions': {
        'androidKeyRestrictions': {'allowedApplications': [
            {'sha1Fingerprint': '14AE72AAAA', 'packageName': 'com.old.app'},
            {'sha1Fingerprint': '14ae72aaaa', 'packageName': 'com.new.app'}]},
        'apiTargets': [{'service': 'maps-android-backend.googleapis.com'},
                       {'service': 'geocoding-backend.googleapis.com'}]}}
    new = keys_ops.android_restrictions_body(['14ae72aaaa'], 'com.new.app',
                                             ['maps-android-backend.googleapis.com'])
    removed = keys_ops.restriction_removals(key, new)
    assert removed == ['Android com.old.app (cert 14ae72aaaa...)',
                       'API target geocoding-backend.googleapis.com']
    # nothing removed when the new body is a superset
    same = keys_ops.android_restrictions_body(['14ae72aaaa'], 'com.new.app',
                                              ['maps-android-backend.googleapis.com'])
    key2 = {'restrictions': same}
    assert keys_ops.restriction_removals(key2, same) == []


def test_restriction_removals_ios_bundles():
    key = {'restrictions': {'iosKeyRestrictions': {
        'allowedBundleIds': ['com.old.bundle', 'com.new.bundle']}}}
    new = keys_ops.ios_restrictions_body('com.new.bundle',
                                         ['maps-ios-backend.googleapis.com'])
    removed = keys_ops.restriction_removals(key, new)
    assert 'iOS bundle id com.old.bundle' in removed
    assert not any('com.new.bundle' in r for r in removed)
