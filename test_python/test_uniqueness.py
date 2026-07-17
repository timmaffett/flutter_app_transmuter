import json

from brandtool_lib import uniqueness


def make_brand(root, name, transmute, gs_project=None):
    d = root / name
    d.mkdir(parents=True)
    (d / 'transmute.json').write_text(json.dumps(transmute))
    if gs_project:
        (d / 'google-services.json').write_text(
            json.dumps({'project_info': {'project_id': gs_project}}))
    return str(d)


def test_detects_duplicated_values_and_ignores_placeholders(tmp_path):
    a = make_brand(tmp_path, 'brand_a',
                   {'packageName': 'com.same.app', 'androidGoogleMapsSDKApiKey': 'AIza-dup',
                    'iosGoogleMapsSDKApiKey': 'AIza-unique-1',
                    'DEVELOPMENT_TEAM': 'PLACE_TEAM_ID_HERE:X'})
    b = make_brand(tmp_path, 'brand_b',
                   {'packageName': 'com.same.app', 'androidGoogleMapsSDKApiKey': 'AIza-dup',
                    'iosGoogleMapsSDKApiKey': 'AIza-unique-2',
                    'DEVELOPMENT_TEAM': 'PLACE_TEAM_ID_HERE:X'})
    dups = uniqueness.find_duplicates([a, b])
    assert dups['packageName'] == {'com.same.app': ['brand_a', 'brand_b']}
    assert dups['androidGoogleMapsSDKApiKey'] == {'AIza-dup': ['brand_a', 'brand_b']}
    assert 'iosGoogleMapsSDKApiKey' not in dups
    assert 'DEVELOPMENT_TEAM' not in dups  # placeholders ignored


def test_detects_google_services_project_collision(tmp_path):
    a = make_brand(tmp_path, 'brand_a', {}, gs_project='same-proj')
    b = make_brand(tmp_path, 'brand_b', {}, gs_project='same-proj')
    dups = uniqueness.find_duplicates([a, b])
    assert dups['google-services project_id'] == {'same-proj': ['brand_a', 'brand_b']}


def test_render_report_lists_brands_and_is_empty_when_clean(tmp_path):
    a = make_brand(tmp_path, 'brand_a', {'packageName': 'com.a'})
    b = make_brand(tmp_path, 'brand_b', {'packageName': 'com.b'})
    assert uniqueness.render_duplicates(uniqueness.find_duplicates([a, b])) == ''
    c = make_brand(tmp_path, 'brand_c', {'packageName': 'com.a'})
    text = uniqueness.render_duplicates(uniqueness.find_duplicates([a, b, c]))
    assert 'packageName' in text and 'brand_a' in text and 'brand_c' in text
    assert 'com.a' in text and 'DUPLICATE' in text
