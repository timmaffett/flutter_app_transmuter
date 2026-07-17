"""Cross-brand uniqueness audit: values that must not be shared between brands.

Brands are created by copying an existing brand dir, so copy-paste leftovers
(another brand's API keys, package name, project id) are a real failure mode -
e.g. a brand shipping a Maps key that lives in a different brand's GCP project,
billing its usage there.
"""
import os

from . import config as cfgmod
from .report import _c

# transmute.json fields whose values must be unique across brands.
UNIQUE_FIELDS = [
    'packageName',
    'iosBundleIdentifier',
    'firebaseProjectId',
    'androidGoogleMapsSDKApiKey',
    'iosGoogleMapsSDKApiKey',
    'serverGooglePlacesAPIKey',
    'messagingServiceAccountKeyFile',
    'apnsKeyId',
    'ascApiKeyId',
    'DEVELOPMENT_TEAM',
]


def find_duplicates(brand_dirs):
    """{field: {value: [brand, ...]}} for values appearing in more than one brand.

    Empty values and STARTER placeholders are ignored. Also compares the
    google-services.json project id (pseudo-field 'google-services project_id').
    """
    seen = {}
    for brand_dir in brand_dirs:
        brand = os.path.basename(os.path.normpath(brand_dir))
        try:
            data = cfgmod.load_transmute(brand_dir)
        except Exception:
            continue
        for field in UNIQUE_FIELDS:
            value = data.get(field, '')
            if not value or not isinstance(value, str) or cfgmod.PLACEHOLDER_RE.search(value):
                continue
            seen.setdefault(field, {}).setdefault(value, []).append(brand)
        pid = cfgmod.google_services_project_id(brand_dir)
        if pid:
            seen.setdefault('google-services project_id', {}).setdefault(pid, []).append(brand)

    duplicates = {}
    for field, by_value in seen.items():
        dup_values = {v: brands for v, brands in by_value.items() if len(brands) > 1}
        if dup_values:
            duplicates[field] = dup_values
    return duplicates


def render_duplicates(duplicates, color=False):
    """Report text for find_duplicates() output; '' when nothing is duplicated."""
    if not duplicates:
        return ''
    header = 'DUPLICATE VALUES ACROSS BRANDS (each should be unique)'
    if color:
        header = _c(header, 'red')
    lines = ['', '=' * 78, header, '=' * 78]
    for field in sorted(duplicates):
        lines.append('')
        field_txt = _c(field, 'red') if color else field
        lines.append(f'  {field_txt}:')
        for value, brands in sorted(duplicates[field].items()):
            lines.append(f'    DUPLICATE value {value!r}')
            lines.append('      shared by: ' + ', '.join(sorted(brands)))
    from .remediation import default_tool_cmd
    lines += ['', '  Likely cause: brand dir created by copying another brand and the',
              f'  field was never regenerated. Fix key fields with: {default_tool_cmd()} '
              'create-keys <brand>',
              '  (new keys take effect on the next app release - do not delete the old',
              "  key from the other brand's project until shipped versions roll over).",
              '=' * 78]
    return '\n'.join(lines)
