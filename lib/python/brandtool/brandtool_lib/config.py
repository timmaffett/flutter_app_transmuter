"""Shared configuration loading for brandtool (tool config + per-brand transmute.json)."""
import json
import os
import re

LIB_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.dirname(LIB_DIR)
REPO_ROOT = os.path.dirname(BIN_DIR)
DEFAULT_CONFIG_PATH = os.path.join(BIN_DIR, 'brandtool_config.json')
BRANDS_ROOT = os.path.join(REPO_ROOT, 'branded_loyalty')

# Values left over from STARTER_BRAND_DIR templates ("PLACE_..._HERE", "MAKE_..._HERE", "#####").
PLACEHOLDER_RE = re.compile(r'_HERE|^#+$')

REQUIRED_TRANSMUTE_FIELDS = ['packageName', 'iosBundleIdentifier', 'appName']


def load_tool_config(path=None):
    with open(path or DEFAULT_CONFIG_PATH) as f:
        return json.load(f)


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
