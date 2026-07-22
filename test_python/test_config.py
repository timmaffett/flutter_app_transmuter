import json
import os

from brandtool_lib import config


def make_brand(tmp_path, name, transmute, google_services_project=None):
    d = tmp_path / name
    d.mkdir()
    (d / 'transmute.json').write_text(json.dumps(transmute))
    if google_services_project:
        (d / 'google-services.json').write_text(
            json.dumps({'project_info': {'project_id': google_services_project}}))
    return str(d)


CFG = {'debugSha1': '14:AE:72', 'releaseSha1': '22:66:DB', 'releaseSha256': '16:52:87'}


def test_placeholder_fields_detects_starter_values():
    data = {'firebaseProjectId': 'PLACE_PROJECT_ID_HERE',
            'packageName': 'MAKE_PACKAGE_NAME_HERE:us.netpark.app.loyalty_demo',
            'firebaseProjectNumber': '###################',
            'appName': 'Real App'}
    assert config.placeholder_fields(data) == [
        'firebaseProjectId', 'firebaseProjectNumber', 'packageName']


def test_missing_required_fields():
    assert config.missing_required_fields({'packageName': 'x'}) == [
        'iosBundleIdentifier', 'appName']


def test_brand_fingerprints_dedupes_and_always_includes_release(tmp_path):
    data = {'AndroidSHA-1Fingerprint': '14:AE:72',
            'Additional-AndroidSHA-1Fingerprint': '22:66:db'}
    fps = config.brand_fingerprints(data, CFG)
    assert fps == [('14ae72', 'SHA_1'), ('2266db', 'SHA_1'), ('165287', 'SHA_256')]


def test_brand_project_id_prefers_google_services(tmp_path):
    d = make_brand(tmp_path, 'b1', {'firebaseProjectId': 'from-transmute'}, 'from-gs')
    assert config.brand_project_id(d, config.load_transmute(d)) == 'from-gs'


def test_brand_project_id_ignores_placeholder(tmp_path):
    d = make_brand(tmp_path, 'b2', {'firebaseProjectId': 'PLACE_PROJECT_ID_HERE'})
    assert config.brand_project_id(d, config.load_transmute(d)) is None


def test_find_brand_dirs_skips_starter_and_missing_google_services(tmp_path):
    make_brand(tmp_path, 'STARTER_BRAND_DIR', {}, 'x')
    make_brand(tmp_path, 'real', {}, 'x')
    make_brand(tmp_path, 'no_gs', {})
    dirs = config.find_brand_dirs(brands_root=str(tmp_path))
    assert [os.path.basename(d) for d in dirs] == ['real']
    dirs = config.find_brand_dirs(require_google_services=False, brands_root=str(tmp_path))
    assert [os.path.basename(d) for d in dirs] == ['no_gs', 'real']


def test_save_transmute_round_trips(tmp_path):
    d = make_brand(tmp_path, 'b3', {'a': 1})
    data = config.load_transmute(d)
    data['b'] = 2
    config.save_transmute(d, data)
    assert config.load_transmute(d) == {'a': 1, 'b': 2}


def test_missing_inferable_fields():
    cfg = {'debugSha1': '14:AE:72', 'releaseSha1': '22:66:DB', 'releaseSha256': '16:52:87',
           'billingAccountId': 'BILL-1'}
    assert config.missing_inferable_fields({}, cfg) == [
        'AndroidSHA-1Fingerprint', 'Additional-AndroidSHA-1Fingerprint', 'billingAccountId']
    complete = {'AndroidSHA-1Fingerprint': '14:AE:72',
                'Additional-AndroidSHA-1Fingerprint': '22:66:db',
                'billingAccountId': 'BILL-1'}
    assert config.missing_inferable_fields(complete, cfg) == []
    assert config.inferable_defaults(cfg)['billingAccountId'] == 'BILL-1'


def test_active_brand_dir_and_is_active(tmp_path, monkeypatch):
    from brandtool_lib import config as cfgmod
    monkeypatch.setattr(cfgmod, 'REPO_ROOT', str(tmp_path))
    # no root transmute.json -> unknown
    assert cfgmod.active_brand_dir() is None
    assert not cfgmod.is_active_brand('branded_loyalty/parkngo_440')
    import json
    (tmp_path / 'transmute.json').write_text(json.dumps(
        {'brand_source_directory': 'branded_loyalty/parkngo_440'}))
    assert cfgmod.active_brand_dir() == 'branded_loyalty/parkngo_440'
    # separator/case-insensitive match
    assert cfgmod.is_active_brand(r'branded_loyalty\parkngo_440')
    assert cfgmod.is_active_brand('branded_loyalty/PARKNGO_440')
    assert not cfgmod.is_active_brand('branded_loyalty/mke_smartpark_1495')


def test_real_value_filters_placeholders():
    from brandtool_lib import config as cfgmod
    data = {'DEVELOPMENT_TEAM': 'PLACE_TEAM_ID_HERE:BW25647WCD',
            'appStoreId': '#####', 'packageName': 'com.real.app', 'empty': ''}
    assert cfgmod.real_value(data, 'DEVELOPMENT_TEAM') == ''
    assert cfgmod.real_value(data, 'appStoreId') == ''
    assert cfgmod.real_value(data, 'packageName') == 'com.real.app'
    assert cfgmod.real_value(data, 'empty') == ''
    assert cfgmod.real_value(data, 'absent') == ''
