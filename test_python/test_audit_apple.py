import json
import os

from brandtool_lib import audit
from brandtool_lib.report import OK, ISSUE, ERROR, SKIP, INFO, BrandReport


def make_brand(tmp_path, asc_fields=True, with_apns=True, name='apple_brand'):
    root = tmp_path / 'branded_loyalty'
    root.mkdir(exist_ok=True)
    d = root / name
    d.mkdir()
    data = {'packageName': 'com.demo.app', 'iosBundleIdentifier': 'com.demo.ios',
            'appName': 'Demo', 'DEVELOPMENT_TEAM': 'TEAM123456', 'appStoreId': 'A1'}
    if asc_fields:
        data.update({'ascApiKeyId': 'TESTKEY123', 'ascApiIssuerId': 'issuer-uuid',
                     'ascApiKeyFile': 'AuthKey_ASC_TESTKEY123.p8'})
        (d / 'AuthKey_ASC_TESTKEY123.p8').write_text('key')
    if with_apns:
        data['apnsKeyId'] = 'APNS999999'
        (d / 'AuthKey_APNS999999.p8').write_text('apns')
        backup = tmp_path / 'appleAPNPushKey'
        backup.mkdir(exist_ok=True)
        (backup / 'AuthKey_APNS999999.p8').write_text('apns')
    (d / 'transmute.json').write_text(json.dumps(data))
    return str(d), data


CFG = {'iosRequiredCapabilities': ['PUSH_NOTIFICATIONS', 'APPLE_ID_AUTH']}


class FakeAscClient:
    def __init__(self, bundle=None, apps=None, caps=None, certs=None):
        self.bundle = bundle
        self.apps = apps or []
        self.caps = caps or []
        self.certs = certs or []
        self.posted = []

    def get(self, path, params=None):
        if path == '/bundleIds':
            return [self.bundle] if self.bundle else []
        if path.endswith('/bundleIdCapabilities'):
            return self.caps
        if path == '/apps':
            return self.apps
        if path == '/certificates':
            return self.certs
        return []

    def post(self, path, body):
        self.posted.append((path, body))
        return {'data': {'id': 'new'}}


BUNDLE = {'id': 'B1', 'attributes': {'identifier': 'com.demo.ios', 'seedId': 'TEAM123456'}}
APP = {'id': 'A1', 'attributes': {'bundleId': 'com.demo.ios'}}
CAPS = [{'attributes': {'capabilityType': 'PUSH_NOTIFICATIONS'}},
        {'attributes': {'capabilityType': 'APPLE_ID_AUTH'}}]


def checks_by_name(r):
    return {c.name: c for c in r.checks}


def test_missing_credentials_flags_every_api_check(tmp_path):
    d, data = make_brand(tmp_path, asc_fields=False)
    r = BrandReport('apple_brand')
    audit._audit_apple(r, CFG, d, data, client=None)
    checks = checks_by_name(r)
    for name in audit.APPLE_API_CHECKS:
        assert checks[name].status == ISSUE, name
        assert 'MISSING APPLE APP MANAGER API KEY' in checks[name].detail
        assert checks[name].flash
    # local checks still run without credentials
    assert checks['APNs key file'].status == OK
    assert 'App Store Connect' not in checks  # old single-skip line is gone


def test_healthy_apple_brand(tmp_path):
    d, data = make_brand(tmp_path)
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=BUNDLE, apps=[APP], caps=CAPS)
    audit._audit_apple(r, CFG, d, data, client=client)
    assert [c.name for c in r.issues] == []
    checks = checks_by_name(r)
    assert checks['Bundle ID registered'].status == OK
    assert checks['Bundle ID team'].status == OK
    assert checks['App ID capabilities'].status == OK
    assert checks['ASC app record'].status == OK
    assert checks['APNs key file'].status == OK
    assert checks['APNs key in Firebase'].status == INFO


def test_missing_capability_is_fixable(tmp_path):
    d, data = make_brand(tmp_path)
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=BUNDLE, apps=[APP], caps=CAPS[:1])
    audit._audit_apple(r, CFG, d, data, client=client)
    cap = checks_by_name(r)['App ID capabilities']
    assert cap.status == ISSUE and 'APPLE_ID_AUTH' in cap.detail and cap.fix
    cap.fix()
    assert client.posted and client.posted[0][0] == '/bundleIdCapabilities'


def test_unregistered_bundle_id_fixable_and_missing_app_record(tmp_path):
    d, data = make_brand(tmp_path, with_apns=False)
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=None, apps=[])
    audit._audit_apple(r, CFG, d, data, client=client)
    checks = checks_by_name(r)
    assert checks['Bundle ID registered'].status == ISSUE and checks['Bundle ID registered'].fix
    assert checks['ASC app record'].status == ISSUE and checks['ASC app record'].fix is None
    assert checks['APNs key file'].status == ISSUE


def test_apns_key_id_recording_is_fixable(tmp_path):
    d, data = make_brand(tmp_path)
    del data['apnsKeyId']
    tj = os.path.join(d, 'transmute.json')
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=BUNDLE, apps=[APP], caps=CAPS)
    audit._audit_apple(r, CFG, d, data, client=client)
    check = [c for c in r.checks if c.name == 'APNs key file'][0]
    assert check.status == ISSUE and check.fix is not None
    assert 'APNS999999' in check.detail
    check.fix()
    with open(tj) as f:
        assert json.loads(f.read())['apnsKeyId'] == 'APNS999999'


def test_apns_missing_backup_is_fixable(tmp_path):
    import os as _os
    d, data = make_brand(tmp_path)
    _os.remove(str(tmp_path / 'appleAPNPushKey' / 'AuthKey_APNS999999.p8'))
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=BUNDLE, apps=[APP], caps=CAPS)
    audit._audit_apple(r, CFG, d, data, client=client)
    check = [c for c in r.checks if c.name == 'APNs key file'][0]
    assert check.status == ISSUE and 'backup' in check.detail and check.fix
    check.fix()
    assert (tmp_path / 'appleAPNPushKey' / 'AuthKey_APNS999999.p8').exists()


def test_apns_unclaimed_candidates_listed(tmp_path):
    d, data = make_brand(tmp_path, with_apns=False)
    apns = tmp_path / 'appleAPNPushKey'
    apns.mkdir(exist_ok=True)
    (apns / 'AuthKey_ZZ99887766.p8').write_text('k')
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=BUNDLE, apps=[APP], caps=CAPS)
    audit._audit_apple(r, CFG, d, data, client=client)
    check = [c for c in r.checks if c.name == 'APNs key file'][0]
    assert check.status == ISSUE and 'ZZ99887766' in check.detail


def test_app_store_id_recorded_from_asc_when_missing(tmp_path):
    import os as _os
    d, data = make_brand(tmp_path)
    del data['appStoreId']
    tj = _os.path.join(d, 'transmute.json')
    with open(tj, 'w') as f:
        f.write(json.dumps(data))
    r = BrandReport('apple_brand')
    client = FakeAscClient(bundle=BUNDLE, apps=[APP], caps=CAPS)
    audit._audit_apple(r, CFG, d, data, client=client)
    check = checks_by_name(r)['appStoreId recorded']
    assert check.status == ISSUE and check.fix
    assert 'A1' in check.detail
    check.fix()
    with open(tj) as f:
        assert json.loads(f.read())['appStoreId'] == 'A1'


class RaisingClient:
    def __init__(self, exc):
        self.exc = exc

    def get(self, path, params=None):
        raise self.exc

    def post(self, path, body):
        raise self.exc


def test_account_holder_blocking_error_is_classified(tmp_path):
    from brandtool_lib.asc_api import AscPermissionError
    d, data = make_brand(tmp_path)
    exc = AscPermissionError(
        'API key role is insufficient (403): '
        'FORBIDDEN.REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED: This request requires an '
        'in-effect agreement that has not been signed or has expired.')
    r = BrandReport('apple_brand')
    audit._audit_apple(r, CFG, d, data, client=RaisingClient(exc))
    check = checks_by_name(r)['Apple account status']
    assert check.status == ISSUE and check.flash
    assert 'ACCOUNT HOLDER' in check.detail
    assert 'REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED' in check.detail


def test_plain_auth_error_stays_asc_authentication(tmp_path):
    from brandtool_lib.asc_api import AscAuthError
    d, data = make_brand(tmp_path)
    exc = AscAuthError('App Store Connect rejected the API key (401): NOT_AUTHORIZED: bad key')
    r = BrandReport('apple_brand')
    audit._audit_apple(r, CFG, d, data, client=RaisingClient(exc))
    checks = checks_by_name(r)
    assert checks['ASC authentication'].status == ERROR
    assert 'Apple account status' not in checks


def test_asc_client_for_brand_reasons(tmp_path):
    d, data = make_brand(tmp_path, asc_fields=False, name='b1')
    client, reason = audit.asc_client_for_brand(d, data)
    assert client is None and 'add-asc-key' in reason
    d2, data2 = make_brand(tmp_path, asc_fields=True, name='b2')
    data2['ascApiKeyFile'] = 'missing.p8'
    client, reason = audit.asc_client_for_brand(d2, data2)
    assert client is None and 'missing.p8' in reason


AGREEMENT_403 = ('Apple account blocked pending Account Holder action (403): '
                 'FORBIDDEN.REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED: This request requires '
                 'an in-effect agreement that has not been signed or has expired.')


def test_needs_account_holder_signals():
    from brandtool_lib import asc_api
    assert asc_api.needs_account_holder(AGREEMENT_403)
    assert asc_api.needs_account_holder('the membership has expired')
    assert not asc_api.needs_account_holder(
        'API key role is insufficient (403): FORBIDDEN: no access to this resource')


def test_perm_error_message_distinguishes_agreements():
    from brandtool_lib import asc_api
    blocked = asc_api.perm_error_message(
        'FORBIDDEN.REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED: sign it')
    assert 'Account Holder' in blocked and 'role is insufficient' not in blocked
    plain = asc_api.perm_error_message('FORBIDDEN: no access')
    assert 'role is insufficient' in plain


def test_agreements_status_classification(tmp_path):
    from brandtool_lib.asc_api import AscPermissionError
    d_ok, _ = make_brand(tmp_path, name='brand_ok')
    d_blocked, _ = make_brand(tmp_path, name='brand_blocked')
    d_nokey, _ = make_brand(tmp_path, asc_fields=False, name='brand_nokey')
    # record an Account Holder contact on the blocked brand
    blocked_data = json.loads((tmp_path / 'branded_loyalty/brand_blocked/transmute.json').read_text())
    blocked_data.update(appleAccountHolderName='Jane Holder',
                        appleAccountHolderEmail='jane@client.com')
    (tmp_path / 'branded_loyalty/brand_blocked/transmute.json').write_text(json.dumps(blocked_data))

    clients = {'brand_ok': (FakeAscClient(bundle=BUNDLE), None),
               'brand_blocked': (RaisingClient(AscPermissionError(AGREEMENT_403)), None),
               'brand_nokey': (None, 'credentials not configured (run: ...)')}

    def factory(brand_dir, data):
        return clients[os.path.basename(brand_dir)]

    results = audit.agreements_status([d_ok, d_blocked, d_nokey], client_factory=factory)
    by = {r['brand']: r for r in results}
    assert by['brand_ok']['status'] == 'OK'
    assert by['brand_blocked']['status'] == 'ACTION NEEDED'
    assert 'REQUIRED_AGREEMENTS' in by['brand_blocked']['detail']
    assert by['brand_blocked']['holder_name'] == 'Jane Holder'
    assert by['brand_blocked']['holder_email'] == 'jane@client.com'
    assert by['brand_nokey']['status'] == 'NO KEY'


def test_agreements_status_other_errors_are_errors(tmp_path):
    from brandtool_lib.asc_api import AscAuthError
    d, _ = make_brand(tmp_path, name='brand_badkey')
    exc = AscAuthError('App Store Connect rejected the API key (401): NOT_AUTHORIZED')
    results = audit.agreements_status(
        [d], client_factory=lambda bd, data: (RaisingClient(exc), None))
    assert results[0]['status'] == 'ERROR' and '401' in results[0]['detail']


def test_certs_status_classification(tmp_path):
    import datetime
    d_ok, _ = make_brand(tmp_path, name='certs_ok')
    d_exp, _ = make_brand(tmp_path, name='certs_expiring')
    d_nokey, _ = make_brand(tmp_path, asc_fields=False, name='certs_nokey')

    soon = (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=9)).isoformat().replace('+00:00', 'Z')
    expiring_client = FakeAscClient(bundle=BUNDLE)
    expiring_client.certs = [
        {'attributes': {'name': 'Tim Dev', 'certificateType': 'DEVELOPMENT',
                        'expirationDate': soon}}]
    clients = {'certs_ok': (FakeAscClient(bundle=BUNDLE), None),
               'certs_expiring': (expiring_client, None),
               'certs_nokey': (None, 'credentials not configured')}

    results = audit.certs_status(
        [d_ok, d_exp, d_nokey], days=60,
        client_factory=lambda bd, data: clients[os.path.basename(bd)])
    by = {r['brand']: r for r in results}
    assert by['certs_ok']['status'] == 'OK'
    assert by['certs_nokey']['status'] == 'NO KEY'
    exp = by['certs_expiring']
    assert exp['status'] == 'EXPIRING'
    assert exp['certs'][0][0] == 'Tim Dev' and exp['certs'][0][3] <= 9
