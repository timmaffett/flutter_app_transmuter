import textwrap

from brandtool_lib import config as cfgmod

YAML = textwrap.dedent('''
    project:
      brands_root: my_brands
      brand_config: transmute.json
      starter_brand_dir: TEMPLATE
      customer_id_pattern: '\d+'
    google:
      quota_project: qp-1
      billing_account: 0000-1111
      admin_grantee: admin@example.com
      automation_service_account: sa@qp-1.iam.gserviceaccount.com
      required_apis: [firebase.googleapis.com]
      signing_certs:
        debug_sha1: "AA:BB"
        release_sha1: "CC:DD"
        release_sha256: "EE:FF"
      play:
        credentials_file: play.json
    api_keys:
      - field: androidGoogleMapsSDKApiKey
        name: "Android Key"
        restriction: android
        services: [maps-android-backend.googleapis.com]
        match_tokens: [android, maps]
      - field: serverKey
        name: "Server Key {customerIds}"
        restriction: api_only
        services: [places.googleapis.com]
        match_tokens: [places]
        name_overflow_strip: "Server "
        server_copy:
          note: "our server uses this key"
          url_template: "https://admin.example.com/{customerId}/"
          settings_path: "Settings -> Keys"
    fcm:
      server_copy:
        url_template: "https://admin.example.com/{customerId}/"
        settings_path: "Settings -> Push"
    apple:
      required_capabilities: [PUSH_NOTIFICATIONS]
      apns_backup_dir: apnsBackup
      organization_name: Example Corp
''')


def test_load_provisioning_config_maps_to_legacy_shape(tmp_path, monkeypatch):
    (tmp_path / 'transmute_provisioning.yaml').write_text(YAML)
    monkeypatch.setattr(cfgmod, 'PROJECT_ROOT', str(tmp_path))
    cfg = cfgmod.load_provisioning_config()
    assert cfg['billingAccountId'] == '0000-1111'
    assert cfg['quotaProject'] == 'qp-1'
    assert cfg['netparkAdminGrantee'] == 'admin@example.com'
    assert cfg['requiredApis'] == ['firebase.googleapis.com']
    assert cfg['debugSha1'] == 'AA:BB' and cfg['releaseSha256'] == 'EE:FF'
    assert cfg['iosRequiredCapabilities'] == ['PUSH_NOTIFICATIONS']
    assert cfg['play'] == {'credentialsFile': 'play.json'}
    assert cfg['apnsBackupDir'] == 'apnsBackup'
    assert cfg['customerIdPattern'] == '\d+'
    assert cfg['organizationName'] == 'Example Corp'
    assert cfg['fcmServerCopy']['settings_path'] == 'Settings -> Push'
    purposes = cfg['apiKeyPurposes']
    assert purposes[0]['field'] == 'androidGoogleMapsSDKApiKey'
    assert purposes[1]['server_copy']['note'] == 'our server uses this key'
    # brands root follows the project: section
    assert cfgmod.BRANDS_ROOT.endswith('my_brands')


def test_missing_yaml_raises_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, 'PROJECT_ROOT', str(tmp_path))
    try:
        cfgmod.load_provisioning_config()
        assert False, 'expected SystemExit'
    except SystemExit as e:
        assert 'transmute_provisioning.yaml' in str(e)
        assert 'provision init' in str(e)


def test_project_root_env_controls_paths(tmp_path, monkeypatch):
    monkeypatch.setenv('TRANSMUTER_PROJECT_ROOT', str(tmp_path))
    assert cfgmod.compute_project_root() == str(tmp_path)
