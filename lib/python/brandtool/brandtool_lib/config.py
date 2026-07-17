"""Shared configuration loading for the provisioning engine: the project-level
transmute_provisioning.yaml plus per-brand transmute.json files. The engine runs
from inside the flutter_app_transmuter pub package, so the target project's
location comes from the TRANSMUTER_PROJECT_ROOT env var (set by the Dart
driver) or the current working directory - never from this file's own path."""
import json
import os
import re

import yaml


def compute_project_root():
    return os.environ.get('TRANSMUTER_PROJECT_ROOT') or os.getcwd()


PROJECT_ROOT = compute_project_root()
REPO_ROOT = PROJECT_ROOT     # legacy name, used throughout the engine
PROVISIONING_FILE = 'transmute_provisioning.yaml'
_PROJECT_DEFAULTS = {'brands_root': 'branded_loyalty',
                     'brand_config': 'transmute.json',
                     'starter_brand_dir': 'STARTER_BRAND_DIR',
                     'customer_id_pattern': r'\d+'}
BRANDS_ROOT = os.path.join(REPO_ROOT, _PROJECT_DEFAULTS['brands_root'])

# Values left over from starter-brand templates ("PLACE_..._HERE", "#####").
PLACEHOLDER_RE = re.compile(r'_HERE|^#+$')

REQUIRED_TRANSMUTE_FIELDS = ['packageName', 'iosBundleIdentifier', 'appName']


def load_provisioning_config(path=None):
    """Read transmute_provisioning.yaml and return the legacy cfg-dict shape the
    engine consumes, plus the generalized sections (apiKeyPurposes, server
    copies, Apple settings). Also points BRANDS_ROOT at the project: section."""
    global BRANDS_ROOT
    p = path or os.path.join(PROJECT_ROOT, PROVISIONING_FILE)
    if not os.path.exists(p):
        raise SystemExit(
            f'{PROVISIONING_FILE} not found in {os.path.dirname(p) or PROJECT_ROOT} - '
            'the provisioning commands are configured per-project. Create one '
            'with: transmute provision init')
    with open(p, encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}
    proj = {**_PROJECT_DEFAULTS, **(raw.get('project') or {})}
    BRANDS_ROOT = os.path.join(PROJECT_ROOT, proj['brands_root'])
    g = raw.get('google') or {}
    certs = g.get('signing_certs') or {}
    play = g.get('play') or {}
    apple = raw.get('apple') or {}
    return {
        'billingAccountId': g.get('billing_account', ''),
        'quotaProject': g.get('quota_project', ''),
        'netparkAdminGrantee': g.get('admin_grantee', ''),
        'automationServiceAccount': g.get('automation_service_account', ''),
        'requiredApis': g.get('required_apis') or [],
        'debugSha1': certs.get('debug_sha1', ''),
        'releaseSha1': certs.get('release_sha1', ''),
        'releaseSha256': certs.get('release_sha256', ''),
        'play': ({'credentialsFile': play.get('credentials_file', '')}
                 if play else {}),
        'iosRequiredCapabilities': apple.get('required_capabilities') or [],
        'apiKeyPurposes': raw.get('api_keys') or [],
        'fcmServerCopy': (raw.get('fcm') or {}).get('server_copy'),
        'apnsBackupDir': apple.get('apns_backup_dir', 'appleAPNPushKey'),
        'accessRequestEmailTemplate': apple.get('access_request_email_template'),
        'organizationName': apple.get('organization_name', 'our team'),
        'customerIdPattern': proj['customer_id_pattern'],
        'brandConfigName': proj['brand_config'],
        'starterBrandDir': proj['starter_brand_dir'],
    }


# Legacy alias so brandtool.py's get_context keeps one call site.
def load_tool_config(path=None):
    return load_provisioning_config(path)


def load_transmute(brand_dir):
    with open(os.path.join(brand_dir, 'transmute.json')) as f:
        return json.load(f)


def active_brand_dir():
    """The brand currently transmuted into the working tree, from the repo-root
    transmute.json's brand_source_directory; None when undeterminable."""
    try:
        with open(os.path.join(REPO_ROOT, 'transmute.json')) as f:
            return json.load(f).get('brand_source_directory') or None
    except Exception:
        return None


def is_active_brand(brand_dir):
    active = active_brand_dir()
    return bool(active) and (os.path.normpath(active).lower()
                             == os.path.normpath(brand_dir).lower())


def save_transmute(brand_dir, data):
    with open(os.path.join(brand_dir, 'transmute.json'), 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def placeholder_fields(data):
    return sorted(k for k, v in data.items()
                  if isinstance(v, str) and PLACEHOLDER_RE.search(v))


def missing_required_fields(data):
    return [k for k in REQUIRED_TRANSMUTE_FIELDS if not data.get(k)]


def clean_fp(fp):
    return fp.replace(':', '').replace(' ', '').lower()


def brand_fingerprints(data, cfg):
    """All (cleaned shaHash, certType) pairs the brand's Firebase Android app should have."""
    wanted = []
    for k, v in data.items():
        if 'AndroidSHA-1Fingerprint' in k and v:
            wanted.append((clean_fp(v), 'SHA_1'))
    wanted.append((clean_fp(cfg['debugSha1']), 'SHA_1'))
    wanted.append((clean_fp(cfg['releaseSha1']), 'SHA_1'))
    wanted.append((clean_fp(cfg['releaseSha256']), 'SHA_256'))
    return list(dict.fromkeys(wanted))


def inferable_defaults(cfg):
    """transmute.json fields brandtool can fill automatically from tool config."""
    return {
        'AndroidSHA-1Fingerprint': cfg['debugSha1'],
        'Additional-AndroidSHA-1Fingerprint': cfg['releaseSha1'],
        'billingAccountId': cfg['billingAccountId'],
    }


def missing_inferable_fields(data, cfg):
    """Inferable fields that are absent, empty, or still template placeholders."""
    return [k for k in inferable_defaults(cfg)
            if not data.get(k)
            or (isinstance(data[k], str) and PLACEHOLDER_RE.search(data[k]))]


def google_services_project_id(brand_dir):
    p = os.path.join(brand_dir, 'google-services.json')
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)['project_info']['project_id']


def google_services_project_number(brand_dir):
    p = os.path.join(brand_dir, 'google-services.json')
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)['project_info'].get('project_number')


def brand_project_id(brand_dir, data):
    """google-services.json wins (it reflects the live project); transmute.json is fallback."""
    pid = google_services_project_id(brand_dir)
    if pid:
        return pid
    pid = data.get('firebaseProjectId', '')
    if pid and not PLACEHOLDER_RE.search(pid):
        return pid
    return None


def find_brand_dirs(explicit=None, require_google_services=True, brands_root=None):
    root = brands_root or BRANDS_ROOT
    if explicit:
        return [d.rstrip('/\\') for d in explicit]
    dirs = []
    for entry in sorted(os.listdir(root)):
        d = os.path.join(root, entry)
        if entry == 'STARTER_BRAND_DIR' or not os.path.isdir(d):
            continue
        if not os.path.exists(os.path.join(d, 'transmute.json')):
            continue
        if require_google_services and not os.path.exists(os.path.join(d, 'google-services.json')):
            continue
        dirs.append(d)
    return dirs
