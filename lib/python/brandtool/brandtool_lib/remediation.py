"""Remediation advice for audit findings, rendered as an addendum after the report.

For each ISSUE/ERROR check name: which brandtool command fixes it (templated with
{brand} = brand dir and {project} = GCP project id), and/or manual instructions
with console URLs when no automation exists.
"""
import os

from .report import ERROR, ISSUE, _c, boxed


def default_tool_cmd():
    """The engine runs inside flutter_app_transmuter; the Dart wrapper is the
    single entry point on every platform."""
    return 'transmute provision'


FIX = '{tool} audit {brand} --fix'
CREATE_APPS = '{tool} create-apps {brand}'
CREATE_KEYS = '{tool} create-keys {brand}'
CREATE_APPLE = '{tool} create-apple {brand}'
ADD_ASC_KEY = '{tool} add-asc-key {brand}'

CREDENTIALS_URL = 'https://console.cloud.google.com/apis/credentials?project={project}'

# One shared width so the orange (fixes) and cyan (links) boxes line up.
BOX_WIDTH = 128

ADVICE = {
    'transmute.json fields': {'manual': [
        'edit {brand}/transmute.json and fill the listed fields (the create '
        'commands will also prompt for required identity fields)']},
    'transmute.json inferable fields': {'commands': [FIX]},
    'root transmute.json sync': {'manual': [
        'decide which copy is right (the audit shows which is NEWER), then sync:',
        '  transmute --update            (working tree -> brand dir)',
        '  transmute --switch {brand}    (brand dir -> working tree, overwrites '
        'working-tree edits)',
        'the audit only ever reads the brand dir, so it stays red until synced']},
    'firebaseProjectId recorded': {'commands': [FIX], 'manual': [
        'on a MISMATCH, --fix is not offered: determine which project the brand really '
        'uses (google-services.json reflects the live Firebase apps) and correct '
        'transmute.json by hand']},
    'firebaseProjectNumber recorded': {'commands': [FIX], 'manual': [
        'on a MISMATCH, --fix is not offered: google-services.json reflects the '
        'live project - correct transmute.json (or refresh a stale '
        'google-services.json via create-apps) by hand']},
    'billing linked': {'commands': [FIX], 'manual': [
        'or link manually: https://console.cloud.google.com/billing/linkedaccount?project={project}']},
    'required APIs': {'commands': [FIX], 'manual': [
        'or enable manually: https://console.cloud.google.com/apis/library?project={project}']},
    'Firebase Android app': {'commands': [FIX, CREATE_APPS], 'manual': [
        '(--fix creates the app, registers cert fingerprints, and downloads a '
        'fresh google-services.json into the brand dir)']},
    'Firebase iOS app': {'commands': [FIX, CREATE_APPS], 'manual': [
        '(--fix creates the app with Team ID / App Store ID from transmute.json '
        'and downloads a fresh GoogleService-Info.plist into the brand dir)']},
    'Firebase iOS Team ID': {'commands': [FIX]},
    'Firebase iOS App Store ID': {'commands': [FIX], 'manual': [
        'if the ID is nowhere yet: create the app record in App Store Connect first '
        '(its record id IS the App Store ID), or type it into transmute.json '
        '(App Store Connect -> App Information -> Apple ID)']},
    'appStoreId recorded': {'commands': [FIX]},
    'cert fingerprints': {'commands': [FIX]},
    'google-services.json in sync': {'commands': [CREATE_APPS], 'manual': [
        '(re-downloads fresh config files from Firebase)']},
    'GoogleService-Info.plist in sync': {'commands': [CREATE_APPS], 'manual': [
        '(re-downloads fresh config files from Firebase)']},
    'firebase_options.dart in sync': {'manual': [
        'flutterfire configure only works on the ACTIVE brand, so switch to it first '
        '(SKIP this if the audit says the brand is already active):',
        '  transmute --switch {brand}',
        "then run: flutterfire configure    (select the brand's Firebase project)",
        'then: transmute --update    (syncs the regenerated files back into {brand}/ '
        'so the fix survives future brand switches)']},
    'Android Maps key': {'commands': [FIX, CREATE_KEYS], 'manual': [
        '(--fix reuses/creates the key in the project the brand actually uses '
        'and records it in transmute.json)',
        'or inspect existing keys: ' + CREDENTIALS_URL]},
    'iOS Maps key': {'commands': [FIX, CREATE_KEYS], 'manual': [
        '(--fix reuses/creates the key in the project the brand actually uses '
        'and records it in transmute.json)',
        'or inspect existing keys: ' + CREDENTIALS_URL]},
    'Places server key': {'commands': [FIX, CREATE_KEYS], 'manual': [
        '(--fix reuses/creates the key and records it; a server_copy-configured '
        'SERVER also uses this key - update it server-side after a change)',
        'or inspect existing keys: ' + CREDENTIALS_URL]},
    'Android Maps key restriction': {'commands': [FIX]},
    'iOS Maps key restriction': {'commands': [FIX]},
    'Places server key restriction': {'commands': [FIX]},
    'FCM admin key file': {'commands': [FIX], 'manual': [
        '(--fix mints a NEW key for the recorded fcmServiceAccount; or run '
        '{tool} create-keys {brand} to provision the standard account)']},
    'FCM admin service account': {'commands': [FIX], 'manual': [
        '(--fix records the detected account into transmute.json; older brands use '
        'custom-named push SAs - the audit finds them via the key file or the '
        'FCM Admin IAM role)']},
    'FCM key file account': {'manual': [
        'the key file and fcmServiceAccount disagree - decide which is right, then '
        'edit transmute.json or replace the key file in the brand dir']},
    'Play Store app': {'manual': [
        'app creation cannot be automated - create the app in Play Console '
        '(your Play developer account): https://play.google.com/console',
        'then follow INSTRUCTIONS_BRAND_SETUP.md "Step 4: Manual Google Play steps" '
        '(declarations, first release AAB)']},
    'Apple account status': {'manual': [
        'only the client ACCOUNT HOLDER can resolve this (sign pending agreements / '
        'renew or un-suspend the membership): https://appstoreconnect.apple.com/agreements',
        'contact them (appleAccountHolderName/Email in {brand}/transmute.json); '
        'the GIVE_ME_REQUEST_EMAIL template can be adapted for the ask']},
    'ASC authentication': {'manual': [
        'the ASC API key was rejected or its role is too low - generate a new Team Key '
        '(role App Manager, or Admin on 403) in the client account, then re-run:',
        ADD_ASC_KEY]},
    'App Store Connect': {'manual': [
        'generate an ASC Team Key for the client account (App Store Connect -> '
        'Users and Access -> Integrations -> Team Keys), then run:',
        ADD_ASC_KEY]},
    'Bundle ID registered': {'commands': [CREATE_APPLE]},
    'Bundle ID team': {'manual': [
        'the key authenticates to a different Apple team than DEVELOPMENT_TEAM - '
        'generate the Team Key in the CORRECT client account, then re-run:',
        ADD_ASC_KEY]},
    'App ID capabilities': {'commands': [CREATE_APPLE]},
    'ASC app record': {'manual': [
        'app records cannot be created via API - in App Store Connect (client '
        'account): My Apps -> "+" -> New App: https://appstoreconnect.apple.com/apps',
        'see INSTRUCTIONS_BRAND_SETUP.md "Step 5: Apple steps"']},
    'Certificates expiring': {'manual': [
        'renew in Xcode: Settings (Cmd ,) -> Accounts -> select your Apple ID -> '
        "select the brand's TEAM -> Manage Certificates... -> '+' -> "
        "'Apple Development' or 'Apple Distribution'",
        'DEVELOPMENT certs only affect device debugging (Xcode auto-renews on the '
        'next device build); DISTRIBUTION certs block releasing - renew those. '
        'Full notes + all-brand sweep: {tool} check-personal-ios-dev-certs']},
    'APNs key in Firebase': {'commands': [FIX], 'manual': [
        'Firebase has NO API for the APNs upload - upload the brand dir\'s '
        'AuthKey_<apnsKeyId>.p8 by hand in the Cloud Messaging page for the iOS '
        'app ("APNs Authentication Key"; ONE auth key covers Development AND '
        'Production), then [F]ix records your confirmation in transmute.json']},
    'APNs key file': {'manual': [
        'generate an APNs auth key in the client developer portal: '
        'https://developer.apple.com/account/resources/authkeys/list',
        'place the .p8 in the brand dir AND the APNs backup dir, then upload it in '
        'Firebase console -> Project settings -> Cloud Messaging']},
}


# Metered APIs worth watching: label -> service (metrics page shows usage/quotas/errors).
METERED_APIS = [
    ('Android Maps SDK', 'maps-android-backend.googleapis.com'),
    ('iOS Maps SDK', 'maps-ios-backend.googleapis.com'),
    ('Places API (legacy)', 'places-backend.googleapis.com'),
    ('Places API (New)', 'places.googleapis.com'),
]


def _apple_account_note(brand, brands_root=None):
    """'sign in as <account>, team <id>' from the brand's transmute.json, or ''."""
    import json

    from . import config as cfgmod
    brand_dir = os.path.join(brands_root or cfgmod.BRANDS_ROOT, brand)
    try:
        with open(os.path.join(brand_dir, 'transmute.json')) as f:
            data = json.load(f)
    except OSError:
        return ''
    account = data.get('AppleDeveloperAccountName', '')
    team = data.get('DEVELOPMENT_TEAM', '')
    if not (account or team):
        return ''
    parts = [p for p in (account, f'team {team}' if team else '') if p]
    return ' (sign in as ' + ', '.join(parts) + ')'


def asc_access_request_email(data):
    """Template email asking the client's Apple ACCOUNT HOLDER to enable App Store
    Connect API access (Apple allows only the Account Holder to click Request
    Access; once granted, the organization's Admin access can generate the keys).
    The organization name and an optional full-template override come from
    transmute_provisioning.yaml (apple.organization_name /
    apple.access_request_email_template - placeholders: {holder_name},
    {holder_email}, {app_name}, {account}, {team}, {organization}).
    Procedure per Apple: developer.apple.com/help/app-store-connect/get-started/app-store-connect-api/
    """
    from . import config as cfgmod
    fields = {
        'holder_name': data.get('appleAccountHolderName') or '[ACCOUNT HOLDER NAME]',
        'holder_email': data.get('appleAccountHolderEmail') or '[ACCOUNT HOLDER EMAIL]',
        'app_name': data.get('appName', '[APP NAME]'),
        'account': data.get('AppleDeveloperAccountName', '[APPLE DEVELOPER ACCOUNT]'),
        'team': data.get('DEVELOPMENT_TEAM', '[TEAM ID]'),
        'organization': cfgmod.ORGANIZATION_NAME,
    }
    template = cfgmod.ACCESS_REQUEST_EMAIL_TEMPLATE or '''To: {holder_name} <{holder_email}>
Subject: Action needed (2 minutes): enable App Store Connect API access for "{app_name}"

Hello {holder_name},

{organization} builds and maintains the "{app_name}" iOS app under your Apple
Developer account "{account}" (Team ID {team}). To automate the app's
configuration checks and release upkeep, the App Store Connect API needs to
be enabled for your team. Apple only allows the account's ACCOUNT HOLDER to
enable it - {organization} cannot perform this step for you.

What to do (one time only, about 2 minutes):

  1. Sign in at https://appstoreconnect.apple.com as the Account Holder.
  2. Open "Users and Access" and select the "Integrations" tab.
     (Direct link: https://appstoreconnect.apple.com/access/integrations/api)
  3. With "App Store Connect API" selected, click "Request Access".
  4. Check the box agreeing to Apple's terms and click Submit.

Once Apple grants access, {organization} will generate the required API key
using our existing team access - you do not need to create or send us anything
else, and this does not change who controls your account.

Apple's documentation for this step:
https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api/

Thank you,
{organization} Support
'''
    return template.format(**fields)


def render_console_urls(reports, color=False, brands_root=None):
    """Informational addendum: per-brand console links for API usage, keys, billing."""
    known = [r for r in reports if r.project_id and r.project_id != '?']
    if not known:
        return ''
    header = 'USEFUL CONSOLE LINKS (API usage / quotas / configuration)'
    if color:
        header = _c(header, 'cyan')
    lines = [header]
    for r in known:
        p = r.project_id
        lines.append('')
        lines.append(f'  {r.brand}  (project: {p})')
        lines.append('    API usage / metrics:')
        for label, service in METERED_APIS:
            lines.append(f'      {label + ":":22} '
                         f'https://console.cloud.google.com/apis/api/{service}/metrics?project={p}')
        lines.append(f'    {"Enabled APIs:":24} '
                     f'https://console.cloud.google.com/apis/dashboard?project={p}')
        lines.append(f'    {"API keys:":24} '
                     f'https://console.cloud.google.com/apis/credentials?project={p}')
        lines.append(f'    {"Billing:":24} '
                     f'https://console.cloud.google.com/billing/linkedaccount?project={p}')
        lines.append(f'    {"Firebase console:":24} '
                     f'https://console.firebase.google.com/project/{p}/overview')
        cm_url = f'https://console.firebase.google.com/project/{p}/settings/cloudmessaging'
        bundle = getattr(r, 'ios_bundle', '')
        if bundle:
            cm_url += f'/ios:{bundle}'
        lines.append(f'    {"Cloud Messaging/APNs:":24} {cm_url}')
        lines.append(f'    {"Play Console:":24} https://play.google.com/console')
        lines.append(f'    Apple{_apple_account_note(r.brand, brands_root)}:')
        lines.append(f'      {"App Store Connect:":22} https://appstoreconnect.apple.com/apps')
        lines.append(f'      {"ASC API keys:":22} https://appstoreconnect.apple.com/access/integrations/api')
        lines.append(f'      {"Bundle IDs (App IDs):":22} https://developer.apple.com/account/resources/identifiers/list')
        lines.append(f'      {"APNs / auth keys:":22} https://developer.apple.com/account/resources/authkeys/list')
        lines.append(f'      {"Certificates:":22} https://developer.apple.com/account/resources/certificates/list')
    return '\n' + boxed('\n'.join(lines), color_name='cyan', color=color,
                        wrap=BOX_WIDTH, min_width=BOX_WIDTH)


def render_addendum(reports, color=False, tool_cmd=None):
    """Addendum text for all ISSUE/ERROR checks across reports; '' when clean."""
    tool_cmd = tool_cmd or default_tool_cmd()
    problem_reports = []
    for r in reports:
        checks = [c for c in r.checks if c.status in (ISSUE, ERROR)]
        if checks:
            problem_reports.append((r, checks))
    if not problem_reports:
        return ''

    header = 'ADDENDUM - HOW TO ADDRESS THE ISSUES ABOVE'
    if color:
        header = _c(header, 'orange')
    lines = [header]
    for r, checks in problem_reports:
        ctx = {'brand': os.path.join('branded_loyalty', r.brand),
               'project': r.project_id, 'tool': tool_cmd}
        lines.append('')
        lines.append(f'  {r.brand}')
        for c in checks:
            name = c.name
            if color:
                name = _c(name, 'red' if c.status == ISSUE else 'brightred')
            lines.append(f'    {name}: {c.detail}')
            if 'MISSING APPLE APP MANAGER API KEY' in c.detail:
                # Missing-credentials case: the only remedy is recording a Team Key.
                cmd_txt = ADD_ASC_KEY.format(**ctx)
                lines.append('        run:  ' + (_c(cmd_txt, 'command') if color else cmd_txt))
                lines.append('        (Team Key generation click-path: see MANUAL_BRAND_TOOLING.md '
                             '"App Store Connect")')
                continue
            advice = ADVICE.get(c.name)
            if advice:
                for cmd in advice.get('commands', []):
                    cmd_txt = cmd.format(**ctx)
                    lines.append('        run:  ' + (_c(cmd_txt, 'command') if color else cmd_txt))
                for note in advice.get('manual', []):
                    lines.append('        ' + note.format(**ctx))
            else:
                if c.console_url:
                    lines.append(f'        inspect: {c.console_url}')
                lines.append('        see MANUAL_BRAND_TOOLING.md for this check')
    return '\n' + boxed('\n'.join(lines), color_name='orange', color=color,
                        wrap=BOX_WIDTH, min_width=BOX_WIDTH)


def xcode_cert_renewal_instructions():
    """The 'how do I renew this in Xcode' explainer printed by check-personal-ios-dev-certs."""
    return [
        'HOW TO RENEW APPLE CERTIFICATES IN XCODE (~2 minutes, on the Mac that builds):',
        '  1. Xcode -> Settings (Cmd ,) -> Accounts tab',
        '  2. Select your Apple ID on the left, then select the TEAM the certificate',
        '     belongs to (each brand/client has its own team)',
        "  3. Click 'Manage Certificates...'",
        "  4. Click '+' (bottom-left) -> 'Apple Development' (or 'Apple Distribution')",
        '',
        'NOTES:',
        '- DEVELOPMENT certs only affect debugging on a physical device. With',
        "  'Automatically manage signing' Xcode mints a fresh one on the next device",
        '  build after expiry - no action is strictly required. Shipped apps and',
        '  TestFlight/App Store builds are unaffected.',
        '- DISTRIBUTION certs DO matter for releasing - renew before a release.',
        '  Apple allows at most 2 active distribution certs per team.',
        "- Certificates are per-Mac (the private key lives in that machine's",
        '  keychain), and each client team has its own - expect several to expire',
        '  around the same date if they were created together.',
        '- No need to revoke the old cert: let it expire; expired certs do not',
        '  count against limits.',
        '- Provisioning profiles regenerate automatically on the next build when',
        '  automatic signing is on.',
    ]
