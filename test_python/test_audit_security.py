"""Security audit section: IAM least-privilege / unexpected-SA / forbidden-API
checks. Born from a real incident: a messaging SA key holding project Editor
leaked and was used to enable Compute Engine and create a probe SA."""
import json
import os

from brandtool_lib import audit
from brandtool_lib import firebase_ops as fb
from brandtool_lib.report import ERROR, INFO, ISSUE, OK, SKIP, BrandReport
from fakes import FakeResource

PROJECT = 'demo-proj'
FCM_SA = f'firebase-messaging-admin@{PROJECT}.iam.gserviceaccount.com'
ADMINSDK_SA = f'firebase-adminsdk-fbsvc@{PROJECT}.iam.gserviceaccount.com'
COMPUTE_SA = '111222333-compute@developer.gserviceaccount.com'
GOOGLE_AGENT = 'service-111222333@gcp-sa-firebase.iam.gserviceaccount.com'

SEC = {
    'fcmSaAllowedRoles': ['roles/firebasecloudmessaging.admin'],
    'forbiddenSaRoles': ['roles/owner', 'roles/editor'],
    'privilegedSaAllowlist': [],
    'expectedServiceAccounts': [],
    'forbiddenApis': ['compute.googleapis.com'],
    'maxKeyAgeDays': 0,
}


def cfg_with(**overrides):
    sec = {**SEC, **overrides.pop('sec', {})}
    return {'security': sec, 'automationServiceAccount': '', **overrides}


def sec_services(bindings=None, accounts=None, keys_by_email=None,
                 enabled_apis=('firebase.googleapis.com',), set_policy_log=None,
                 disabled_apis_log=None):
    keys_by_email = keys_by_email or {}

    def set_iam_policy(resource=None, body=None):
        if set_policy_log is not None:
            set_policy_log.append(body['policy'])
        return {}

    def disable(name=None, body=None):
        if disabled_apis_log is not None:
            disabled_apis_log.append(name.split('/')[-1])
        return {'name': 'op-disable', 'done': True}

    def list_keys(name=None, keyTypes=None):
        email = name.split('/')[-1]
        return {'keys': keys_by_email.get(email, [])}

    iam = FakeResource(projects=FakeResource(serviceAccounts=FakeResource(
        get=lambda name: {'email': 'x'},
        list=lambda **kw: {'accounts': accounts or []},
        keys=FakeResource(list=list_keys),
    )))
    crm = FakeResource(projects=FakeResource(
        getIamPolicy=lambda resource: {'bindings': bindings or []},
        setIamPolicy=set_iam_policy,
    ))
    usage = FakeResource(
        services=FakeResource(
            list=lambda **kw: {'services': [
                {'name': f'projects/1/services/{a}'} for a in enabled_apis]},
            disable=disable),
        operations=FakeResource(get=lambda name: {'done': True}))
    return {'iam': iam, 'crm': crm, 'usage': usage}


def run_security(services, cfg=None, data=None, brand_dir='.'):
    r = BrandReport('demo_brand')
    audit._audit_security(r, services, cfg or cfg_with(), data or
                          {'fcmServiceAccount': FCM_SA}, brand_dir, PROJECT)
    return {c.name: c for c in r.checks}


# ---------------------------------------------------------------- check 1

def test_fcm_sa_holding_editor_is_flagged_and_fix_revokes_only_excess():
    log = []
    services = sec_services(bindings=[
        {'role': 'roles/firebasecloudmessaging.admin', 'members': [f'serviceAccount:{FCM_SA}']},
        {'role': 'roles/editor', 'members': [f'serviceAccount:{FCM_SA}', 'user:someone@x.com']},
    ], accounts=[{'email': FCM_SA}], set_policy_log=log)
    checks = run_security(services)
    c = checks['FCM SA least privilege']
    assert c.status == ISSUE and c.fix
    assert 'roles/editor' in c.detail
    c.fix()
    assert len(log) == 1
    editor = [b for b in log[0]['bindings'] if b['role'] == 'roles/editor']
    assert editor and f'serviceAccount:{FCM_SA}' not in editor[0]['members']
    assert 'user:someone@x.com' in editor[0]['members']  # other members untouched
    fcm = [b for b in log[0]['bindings'] if b['role'] == 'roles/firebasecloudmessaging.admin']
    assert fcm and f'serviceAccount:{FCM_SA}' in fcm[0]['members']  # allowed role kept


def test_fcm_sa_with_only_allowed_role_is_ok():
    services = sec_services(bindings=[
        {'role': 'roles/firebasecloudmessaging.admin', 'members': [f'serviceAccount:{FCM_SA}']},
    ], accounts=[{'email': FCM_SA}])
    assert run_security(services)['FCM SA least privilege'].status == OK


def test_fcm_sa_with_no_roles_is_info_not_ok():
    services = sec_services(bindings=[], accounts=[{'email': FCM_SA}])
    assert run_security(services)['FCM SA least privilege'].status == INFO


# ---------------------------------------------------------------- check 2

def test_privileged_sweep_flags_project_sa_but_skips_google_agents_and_allowlist():
    rogue = f'rogue@{PROJECT}.iam.gserviceaccount.com'
    allowed = f'automation@{PROJECT}.iam.gserviceaccount.com'
    services = sec_services(bindings=[
        {'role': 'roles/editor', 'members': [
            f'serviceAccount:{rogue}',
            f'serviceAccount:{GOOGLE_AGENT}',          # Google-managed: by design
            f'serviceAccount:{allowed}',               # allowlisted
            f'serviceAccount:111222333@cloudservices.gserviceaccount.com']},
    ], accounts=[{'email': FCM_SA}])
    checks = run_security(services, cfg=cfg_with(sec={'privilegedSaAllowlist': [allowed]}))
    c = checks['privileged service accounts']
    assert c.status == ISSUE
    assert rogue in c.detail
    assert GOOGLE_AGENT not in c.detail
    assert allowed not in c.detail
    assert 'cloudservices' not in c.detail


def test_privileged_sweep_flags_default_compute_sa_holding_editor():
    services = sec_services(bindings=[
        {'role': 'roles/editor', 'members': [f'serviceAccount:{COMPUTE_SA}']},
    ], accounts=[{'email': FCM_SA}])
    c = run_security(services)['privileged service accounts']
    assert c.status == ISSUE and COMPUTE_SA in c.detail


def test_privileged_sweep_ok_when_clean():
    services = sec_services(bindings=[
        {'role': 'roles/firebasecloudmessaging.admin', 'members': [f'serviceAccount:{FCM_SA}']},
        {'role': 'roles/editor', 'members': [f'serviceAccount:{GOOGLE_AGENT}']},
    ], accounts=[{'email': FCM_SA}])
    assert run_security(services)['privileged service accounts'].status == OK


# ---------------------------------------------------------------- check 3

def test_unexpected_service_account_flagged():
    services = sec_services(accounts=[
        {'email': FCM_SA}, {'email': ADMINSDK_SA},
        {'email': f'test-acc@{PROJECT}.iam.gserviceaccount.com'},
    ])
    c = run_security(services)['unexpected service accounts']
    assert c.status == ISSUE and 'test-acc@' in c.detail


def test_expected_and_adminsdk_accounts_are_recognized():
    extra = f'ci-deploy@{PROJECT}.iam.gserviceaccount.com'
    services = sec_services(accounts=[
        {'email': FCM_SA}, {'email': ADMINSDK_SA}, {'email': extra}])
    checks = run_security(services, cfg=cfg_with(sec={'expectedServiceAccounts': [extra]}))
    assert checks['unexpected service accounts'].status == OK


def test_default_compute_sa_presence_is_info_not_unexpected():
    services = sec_services(accounts=[{'email': FCM_SA}, {'email': COMPUTE_SA}])
    checks = run_security(services)
    assert checks['unexpected service accounts'].status == ISSUE or \
        checks['unexpected service accounts'].status == OK
    # present-but-known default SA reported as INFO, not lumped with unknowns
    assert checks['unexpected service accounts'].status == OK
    assert checks['default service accounts'].status == INFO
    assert COMPUTE_SA in checks['default service accounts'].detail


# ---------------------------------------------------------------- check 4

def test_forbidden_api_enabled_is_flagged_and_fix_disables():
    disabled = []
    services = sec_services(enabled_apis=('firebase.googleapis.com',
                                          'compute.googleapis.com'),
                            accounts=[{'email': FCM_SA}],
                            disabled_apis_log=disabled)
    c = run_security(services)['forbidden APIs']
    assert c.status == ISSUE and 'compute.googleapis.com' in c.detail and c.fix
    c.fix()
    assert disabled == ['compute.googleapis.com']


def test_forbidden_api_not_enabled_is_ok():
    services = sec_services(accounts=[{'email': FCM_SA}])
    assert run_security(services)['forbidden APIs'].status == OK


# ---------------------------------------------------------------- check 5

def test_user_managed_key_on_non_fcm_sa_is_flagged():
    services = sec_services(
        accounts=[{'email': FCM_SA}, {'email': ADMINSDK_SA}],
        keys_by_email={
            FCM_SA: [{'name': 'k1', 'validAfterTime': '2026-01-01T00:00:00Z'}],
            ADMINSDK_SA: [{'name': 'k2', 'validAfterTime': '2026-01-01T00:00:00Z'}],
        })
    c = run_security(services)['SA key hygiene']
    assert c.status == ISSUE and ADMINSDK_SA in c.detail


def test_multiple_keys_on_fcm_sa_is_flagged():
    services = sec_services(
        accounts=[{'email': FCM_SA}],
        keys_by_email={FCM_SA: [
            {'name': 'k1', 'validAfterTime': '2026-01-01T00:00:00Z'},
            {'name': 'k2', 'validAfterTime': '2026-02-01T00:00:00Z'}]})
    c = run_security(services)['SA key hygiene']
    assert c.status == ISSUE and '2' in c.detail


def test_stale_key_flagged_when_max_age_configured():
    services = sec_services(
        accounts=[{'email': FCM_SA}],
        keys_by_email={FCM_SA: [{'name': 'k1', 'validAfterTime': '2020-01-01T00:00:00Z'}]})
    c = run_security(services, cfg=cfg_with(sec={'maxKeyAgeDays': 365}))['SA key hygiene']
    assert c.status == ISSUE and 'older than' in c.detail


def test_key_hygiene_ok_with_single_fresh_fcm_key():
    services = sec_services(
        accounts=[{'email': FCM_SA}],
        keys_by_email={FCM_SA: [{'name': 'k1', 'validAfterTime': '2026-01-01T00:00:00Z'}]})
    assert run_security(services)['SA key hygiene'].status == OK


# ---------------------------------------------------------------- wiring

def test_security_section_skipped_without_crm():
    services = sec_services(accounts=[{'email': FCM_SA}])
    services['crm'] = None
    checks = run_security(services)
    assert checks['FCM SA least privilege'].status == SKIP
    # non-IAM checks still run
    assert 'forbidden APIs' in checks and 'unexpected service accounts' in checks


def test_fcm_sa_inferred_from_key_file_when_unrecorded(tmp_path):
    keyfile = tmp_path / 'sa.json'
    custom = f'custom-push@{PROJECT}.iam.gserviceaccount.com'
    keyfile.write_text(json.dumps({'client_email': custom}))
    services = sec_services(bindings=[
        {'role': 'roles/editor', 'members': [f'serviceAccount:{custom}']},
    ], accounts=[{'email': custom}])
    checks = run_security(services, data={'messagingServiceAccountKeyFile': 'sa.json'},
                          brand_dir=str(tmp_path))
    c = checks['FCM SA least privilege']
    assert c.status == ISSUE and custom in c.detail


# ---------------------------------------------------------------- config

def test_security_config_defaults_when_section_absent(tmp_path, monkeypatch):
    from brandtool_lib import config as cfgmod
    p = tmp_path / 'transmute_provisioning.yaml'
    p.write_text('project:\n  brands_root: brands\ngoogle:\n  billing_account: B\n')
    cfg = cfgmod.load_provisioning_config(str(p))
    sec = cfg['security']
    assert sec['fcmSaAllowedRoles'] == ['roles/firebasecloudmessaging.admin']
    assert sec['forbiddenSaRoles'] == ['roles/owner', 'roles/editor']
    assert sec['forbiddenApis'] == ['compute.googleapis.com']
    assert sec['maxKeyAgeDays'] == 0


def test_security_config_opt_out(tmp_path):
    from brandtool_lib import config as cfgmod
    p = tmp_path / 'transmute_provisioning.yaml'
    p.write_text('project:\n  brands_root: brands\nsecurity:\n  enabled: false\n')
    assert cfgmod.load_provisioning_config(str(p))['security'] is None


def test_security_config_custom_values(tmp_path):
    from brandtool_lib import config as cfgmod
    p = tmp_path / 'transmute_provisioning.yaml'
    p.write_text(
        'project:\n  brands_root: brands\n'
        'security:\n'
        '  forbidden_apis: [compute.googleapis.com, run.googleapis.com]\n'
        '  privileged_sa_allowlist: [auto@p.iam.gserviceaccount.com]\n'
        '  max_key_age_days: 400\n')
    sec = cfgmod.load_provisioning_config(str(p))['security']
    assert sec['forbiddenApis'] == ['compute.googleapis.com', 'run.googleapis.com']
    assert sec['privilegedSaAllowlist'] == ['auto@p.iam.gserviceaccount.com']
    assert sec['maxKeyAgeDays'] == 400
