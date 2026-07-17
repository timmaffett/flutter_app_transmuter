#!/usr/bin/env python
"""brandtool - create and audit netPark loyalty brand Google projects.

See MANUAL_BRAND_TOOLING.md for full documentation and INSTRUCTIONS_BRAND_SETUP.md for the
new-brand walkthrough. Auth is ADC by default:
    gcloud auth application-default login    (one time)
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brandtool_lib import apple_ops
from brandtool_lib import asc_api
from brandtool_lib import audit as audit_mod
from brandtool_lib import auth
from brandtool_lib import config as cfgmod
from brandtool_lib import firebase_ops as fb
from brandtool_lib import keys_ops
from brandtool_lib import remediation
from brandtool_lib import report as report_mod
from brandtool_lib import uniqueness


def get_context(args):
    cfg = cfgmod.load_tool_config(args.config)
    creds = auth.build_credentials(args.creds, cfg.get('quotaProject'))
    return cfg, auth.build_services(creds)


def get_publisher(args, cfg):
    pc = cfg.get('play', {}).get('credentialsFile', '')
    path = os.path.join(cfgmod.REPO_ROOT, pc) if pc else ''
    if not path or not os.path.exists(path):
        return None
    pcreds = auth.build_credentials(path, cfg.get('quotaProject'),
                                    scopes=[auth.PUBLISHER_SCOPE])
    return auth.build_service('androidpublisher', 'v3', pcreds)


def _color_enabled(args):
    if args.no_color or args.json or os.environ.get('NO_COLOR'):
        return False
    if not sys.stdout.isatty():
        return False
    try:
        import colorama
        colorama.just_fix_windows_console()
    except ImportError:
        pass  # ANSI-capable terminals (Git Bash, Windows Terminal) work regardless
    return True


def handle_request_email(brand_dir, input_fn=input):
    """Generate + save the email asking the client's Account Holder to enable
    App Store Connect API access. ALWAYS prompts for the holder's name and email
    (current values shown as defaults - Enter keeps, typing replaces, '-' clears)
    so wrong data recorded earlier can be corrected."""
    data = cfgmod.load_transmute(brand_dir)
    changed = False
    prompts = (  # email FIRST (forces the @-shaped answer), then the human name
        ('appleAccountHolderEmail', "Account Holder's EMAIL ADDRESS"),
        ('appleAccountHolderName', "Account Holder's FULL NAME (a person, no email here)"),
    )
    for field, label in prompts:
        current = data.get(field, '')
        hint = f'[Enter = keep "{current}", "-" = clear]' if current \
            else '[Enter = leave a placeholder]'
        while True:
            try:
                value = input_fn(f'{label} {hint}: ').strip()
            except (EOFError, KeyboardInterrupt):
                raise SystemExit('\nAborted - account holder contact unchanged.')
            if value == '-':
                value = ''
            elif not value:
                value = current
            if field == 'appleAccountHolderEmail' and value and '@' not in value:
                print('  That does not look like an email address (no "@") - re-enter, '
                      'or "-" to clear.')
                continue
            if field == 'appleAccountHolderName' and '@' in value:
                print('  A name must not contain "@" (the email was already asked) - '
                      're-enter, or "-" to clear.')
                continue
            break
        if value != current:
            data[field] = value
            changed = True
    if changed:
        cfgmod.save_transmute(brand_dir, data)
        print('transmute.json updated with the account holder contact.')
    email = remediation.asc_access_request_email(data)
    dest = os.path.join(brand_dir, 'apple_api_access_request_email.txt')
    with open(dest, 'w') as f:
        f.write(email)
    print('\n' + '=' * 78)
    print(email)
    print('=' * 78)
    print(f'(saved to {dest})')


def _brand_dir_problem(d):
    if not os.path.isdir(d):
        return 'BRAND DIRECTORY NOT FOUND'
    if not os.path.exists(os.path.join(d, 'transmute.json')):
        return 'NOT A BRAND DIRECTORY (no transmute.json)'
    return None


def ensure_brand_dirs_exist(brand_dirs, known_brands=None, interactive=None,
                            input_fn=input):
    """Validate brand paths; returns the (possibly corrected) list.

    Typo'd paths get a red error with numbered suggestions - interactively the
    user picks a number, types a brand name, or [E]xits; non-interactively the
    process exits 1."""
    import difflib
    if interactive is None:
        interactive = sys.stdin.isatty()
    if known_brands is None:
        known_brands = [os.path.basename(p) for p in
                        cfgmod.find_brand_dirs(require_google_services=False)]

    # '.'/'active' means the brand currently transmuted into the working tree
    mapped = []
    for d in brand_dirs:
        if d in ('.', 'active', 'ACTIVE'):
            active = cfgmod.active_brand_dir()
            if not active:
                sys.exit('Cannot determine the ACTIVE brand - the root transmute.json '
                         'has no brand_source_directory.')
            print('active brand: ' + report_mod.paint(active, 'value'))
            d = active
        mapped.append(d)
    brand_dirs = mapped

    resolved = []
    fatal = False
    for d in brand_dirs:
        while True:
            why = _brand_dir_problem(d)
            if why is None:
                resolved.append(d)
                break
            print(report_mod.paint(f'{why}: {d}', 'brightred'))
            name = os.path.basename(os.path.normpath(d))
            close = difflib.get_close_matches(name, known_brands, n=3, cutoff=0.5)
            if not interactive:
                if close:
                    print('  did you mean: ' + ' or '.join(
                        os.path.join('branded_loyalty', c) for c in close) + ' ?')
                fatal = True
                break
            for i, cand in enumerate(close, 1):
                print(f'  [{i}] {os.path.join("branded_loyalty", cand)}')
            hint = f'[1-{len(close)}], ' if close else ''
            try:
                answer = input_fn(f'Choose {hint}type a brand name, or [E]xit: ').strip()
            except (EOFError, KeyboardInterrupt):
                sys.exit(1)
            if answer.lower() in ('e', 'exit', 'q', 'quit'):
                sys.exit(1)
            if answer.isdigit() and close and 1 <= int(answer) <= len(close):
                d = os.path.join(cfgmod.BRANDS_ROOT, close[int(answer) - 1])
                continue
            if answer:
                candidate = answer
                if _brand_dir_problem(candidate):
                    inside = os.path.join(cfgmod.BRANDS_ROOT,
                                          os.path.basename(os.path.normpath(answer)))
                    if not _brand_dir_problem(inside):
                        candidate = inside
                d = candidate
            # loop re-validates (blank answer just re-shows the choices)
    if fatal:
        sys.exit(1)
    return resolved


def gate_apple_credentials(brand_dirs, use_color, interactive, input_fn=input,
                           flow_fn=None):
    """Loud gate for brands with no ASC Team Key: banner at the top, then (when
    interactive) offer to record keys right now; INEEDTOSETUPAPPLE proceeds without."""
    missing = []
    for d in brand_dirs:
        try:
            data = cfgmod.load_transmute(d)
        except Exception:
            continue
        if audit_mod.asc_client_for_brand(d, data)[0] is None:
            missing.append(d)
    if not missing:
        return
    names = ', '.join(report_mod.alert_highlight(os.path.basename(os.path.normpath(d)))
                      for d in missing)
    print(report_mod.render_alert([
        'iOS ADMIN API CREDENTIALS MUST BE SET UP',
        'No App Store Connect Team Key recorded for: ' + names,
        'Without one, the iOS side of the audit CANNOT run and those checks',
        'will be flagged as MISSING APPLE APP MANAGER API KEY.',
    ], color=use_color))
    if not interactive:
        return
    flow = flow_fn or add_asc_key_flow
    for d in missing:
        brand = os.path.basename(os.path.normpath(d))
        print_asc_key_instructions(cfgmod.load_transmute(d))
        while True:
            try:
                paint = report_mod.paint
                answer = input_fn(
                    f"{paint('Key ID', 'pink')} for {paint(brand, 'value')} (or "
                    f"{paint('INEEDTOSETUPAPPLE', 'command')} to audit without Apple "
                    f"credentials, or {paint('GIVE_ME_REQUEST_EMAIL', 'command')} if "
                    'the client Account Holder must enable API access first): ').strip()
            except (EOFError, KeyboardInterrupt):
                raise SystemExit('\nAborted at the Apple key prompt - nothing was '
                                 'changed. Re-run the audit when ready (or type '
                                 'INEEDTOSETUPAPPLE at this prompt to audit without '
                                 'Apple credentials).')
            if answer == 'INEEDTOSETUPAPPLE':
                print('Continuing without Apple credentials - iOS entries will be '
                      'flagged as MISSING.')
                return
            if answer == 'GIVE_ME_REQUEST_EMAIL':
                handle_request_email(d, input_fn=input_fn)
                continue
            if KEY_ID_RE.match(answer.upper()):
                if flow(d, key_id=answer.upper()):
                    break
                print('  Key verification failed - try again, or type INEEDTOSETUPAPPLE.')
            else:
                print('  Expected a 10-character Key ID, INEEDTOSETUPAPPLE, '
                      'or GIVE_ME_REQUEST_EMAIL.')


def _print_info(reports, use_color):
    addendum = remediation.render_addendum(reports, color=use_color)
    if addendum:
        print(addendum)
    links = remediation.render_console_urls(reports, color=use_color)
    if links:
        print(links)


def cmd_audit(args):
    cfg, services = get_context(args)
    publisher = get_publisher(args, cfg)
    use_color = _color_enabled(args)
    report_mod.set_color(use_color)
    brand_dirs = cfgmod.find_brand_dirs(args.brands)
    interactive = sys.stdin.isatty() and not args.json and not args.noprompt
    if args.brands:
        brand_dirs = ensure_brand_dirs_exist(brand_dirs, interactive=interactive)
    gate_apple_credentials(brand_dirs, use_color, interactive and not args.yes)

    links_shown = False
    auto_fix_done = not args.fix
    while True:
        reports = []
        for brand_dir in brand_dirs:
            print(f'auditing {os.path.basename(brand_dir)}...')
            if cfgmod.is_active_brand(brand_dir):
                print(report_mod.paint(
                    f'REMINDER WARNING: {os.path.basename(os.path.normpath(brand_dir))} '
                    'is the ACTIVE brand - the audit reads ONLY the brand dir, NOT '
                    'your working-tree files', 'flash'))
            reports.append(audit_mod.audit_brand(services, cfg, brand_dir, publisher))

        if args.json:
            print(report_mod.render_json(reports))
            sys.exit(1 if any(r.issues for r in reports) else 0)

        print(report_mod.render_text(reports, color=use_color))
        dirty = any(r.issues for r in reports)
        # Interactive + dirty: keep the screen focused on the audit results; the
        # addenda (fix advice + console links) are available via the [I]nfo option.
        if not (interactive and dirty):
            addendum = remediation.render_addendum(reports, color=use_color)
            if addendum:
                print(addendum)
            if not links_shown and not args.no_links:
                links = remediation.render_console_urls(reports, color=use_color)
                if links:
                    print(links)
                links_shown = True

        if not dirty:
            clean = 'AUDIT CLEAN - all checks passed.'
            print(report_mod._c(clean, 'green') if use_color else clean)
            sys.exit(0)

        if not auto_fix_done:
            # --fix: run one fix pass immediately, then re-audit and continue below.
            auto_fix_done = True
            fixed = report_mod.run_fixes(reports, assume_yes=args.yes)
            print(f'\n{fixed} issue(s) fixed - re-auditing...\n')
            continue

        if not interactive:
            sys.exit(1)

        # Audit is NOT clean: do not exit until the user fixes or explicitly quits.
        while True:
            try:
                answer = input('\nAudit is NOT clean. Addendums (fix advice + console '
                               'links) can be shown with the [I]nfo option.\n'
                               '[F]ix now  [R]e-audit  [I]nfo  [A]pple key setup  '
                               '[Q]uit without fixing: ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                print('\nExiting with unresolved issues (exit code 1).')
                sys.exit(1)
            if answer in ('f', 'fix'):
                fixed = report_mod.run_fixes(reports, assume_yes=args.yes)
                print(f'\n{fixed} issue(s) fixed - re-auditing...\n')
                break
            if answer in ('r', 're-audit', 'reaudit'):
                print('re-auditing...\n')
                break
            if answer in ('i', 'info'):
                _print_info(reports, use_color)
                continue
            if answer in ('a', 'apple'):
                gate_apple_credentials(brand_dirs, use_color, True)
                print('re-auditing...\n')
                break
            if answer in ('q', 'quit'):
                print('Exiting with unresolved issues (exit code 1).')
                sys.exit(1)
            print('  Enter F, R, I, A, or Q.')


def propose_project_id(brand_dir, data):
    pid = data.get('firebaseProjectId', '')
    if pid and not cfgmod.PLACEHOLDER_RE.search(pid):
        return pid
    base = re.sub(r'[^a-z0-9-]+', '-', os.path.basename(os.path.normpath(brand_dir)).lower())
    base = re.sub(r'-+', '-', base).strip('-')[:30].rstrip('-')
    if not base or not base[0].isalpha():
        base = ('brand-' + base)[:30].rstrip('-')
    return base


KEY_ID_RE = re.compile(r'^[A-Z0-9]{10}$')
ISSUER_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
                       r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


def find_downloaded_p8(key_id, downloads_dir=None, input_fn=input, reject=None):
    """Locate the downloaded AuthKey file. Accepts only real FILES; a directory
    answer is searched for AuthKey_<keyId>.p8 inside it. `reject` is a path that
    already failed validation - never auto-return it again."""
    downloads = downloads_dir or os.path.join(os.path.expanduser('~'), 'Downloads')
    fname = f'AuthKey_{key_id}.p8'
    candidate = os.path.join(downloads, fname)
    while True:
        if os.path.isfile(candidate) and candidate != reject:
            return candidate
        path = input_fn(f'{report_mod.paint(fname, "value")} not found in '
                        f'{report_mod.paint(downloads, "value")}.\n'
                        'Download it now, then press Enter (or R) to RE-CHECK the '
                        'Downloads folder - or type the full path to the .p8 file: '
                        ).strip().strip('"')
        if not path or path.lower() in ('r', 'retry'):
            continue  # loop re-checks the Downloads candidate
        if os.path.isdir(path):
            inner = os.path.join(path, fname)
            if os.path.isfile(inner) and inner != reject:
                return inner
            print(f'  That is a directory and {fname} is not usable inside it - '
                  'give the .p8 FILE itself.')
            continue
        if os.path.isfile(path) and path != reject:
            return path
        print('  Not a usable file - Enter/R re-checks Downloads, or give a full path.')


def print_asc_key_instructions(data):
    paint = report_mod.paint
    team = data.get('DEVELOPMENT_TEAM', '')
    account = data.get('AppleDeveloperAccountName', 'the client')
    url = paint('https://appstoreconnect.apple.com', 'cyan')
    acct = paint(account, 'value')
    team_txt = f" (team {paint(team, 'value')})" if team else ''
    nav = paint('Users and Access -> Integrations -> App Store Connect API', 'pink')
    tab = paint('"Team Keys"', 'pink')
    name1 = paint('"netPark brandtool"', 'pink')
    name2 = paint('"netParkLoyaltyAppBrandTool"', 'pink')
    role = paint('"App Manager"', 'darkblue')
    admin_role = paint('"Admin"', 'darkblue')
    sentinel = paint('GIVE_ME_REQUEST_EMAIL', 'command')
    print(f'''
How to create the App Store Connect API Team Key (one time per Apple account):

  1. Sign in to {url} as an Admin of
     {acct}{team_txt} - use the account
     switcher (top right) if you belong to multiple teams.
  2. Go to  {nav},
     and select the {tab} tab.
  3. If the page shows "Request Access": ONLY the client's ACCOUNT HOLDER can
     grant it (netPark is never the Account Holder - Apple's rule). Type
     {sentinel} at the prompt below to generate a ready-to-send
     email asking them to enable it (can take days-weeks), and continue
     without Apple credentials in the meantime.
  4. Click "+" to generate a key:  name it something like {name1}
     or {name2} (the exact name does not matter).
     In the section Apple calls "Access" ("Select Roles"), choose the role
     {role}  (if brandtool later reports 403 errors, revoke the key
     and re-create it with role {admin_role}).
  5. Click "Download API Key" - the .p8 file downloads ONCE and cannot be
     re-downloaded. Leave it in your Downloads folder; this command will
     find it.
  6. Have ready:  the key's {paint('"KEY ID"', 'pink')} (10 characters) and the {paint('"Issuer ID"', 'pink')}
     (UUID at the top of the Team Keys page). Use Apple's COPY BUTTONS rather
     than selecting the text by hand: hovering over the {paint('Key ID', 'pink')} column makes a
     {paint('"Copy Key ID"', 'cyan')} button appear on each row, and the {paint('Issuer ID', 'pink')} has a blue
     {paint('"Copy"', 'cyan')} button just to the right of the UUID.

When you have done the above, answer the prompts:
''')


def add_asc_key_flow(brand_dir, key_id=None):
    """Record + live-verify a downloaded ASC Team Key for a brand. Returns True on
    verified success; False when verification fails (fields stay written)."""
    import shutil
    from cryptography.hazmat.primitives import serialization
    from brandtool_lib.asc_api import AscClient

    data = cfgmod.load_transmute(brand_dir)
    try:
        while not (key_id and KEY_ID_RE.match(key_id)):
            paint = report_mod.paint
            raw = input(f"{paint('Key ID', 'pink')} (10 chars, e.g. "
                        f"{paint('ABC123XYZ0', 'value')}, or "
                        f"{paint('GIVE_ME_REQUEST_EMAIL', 'command')} "
                        'if the Account Holder must enable API access first): ').strip()
            if raw == 'GIVE_ME_REQUEST_EMAIL':
                handle_request_email(brand_dir)
                continue
            key_id = raw.upper()
            if not KEY_ID_RE.match(key_id):
                print('  Expected exactly 10 letters/digits.')
                key_id = None
        issuer_id = ''
        while not ISSUER_RE.match(issuer_id):
            issuer_id = input(f"{report_mod.paint('Issuer ID', 'pink')} (UUID shown at "
                              'the top of the same page - use its blue "Copy" button): '
                              ).strip()
            if not ISSUER_RE.match(issuer_id):
                print('  Expected a UUID like 69a6de70-....')
        src, pem = None, None
        while pem is None:
            src = find_downloaded_p8(key_id, reject=src)
            try:
                with open(src, 'rb') as f:
                    candidate_pem = f.read()
                serialization.load_pem_private_key(candidate_pem, password=None)
                pem = candidate_pem
            except Exception as e:
                print(f'  Cannot use {src}: {e}')
                print('  (need the AuthKey .p8 private-key FILE downloaded from '
                      'App Store Connect)')
    except (EOFError, KeyboardInterrupt):
        raise SystemExit('\nAborted - nothing was changed.')

    dest_name = f'AuthKey_ASC_{key_id}.p8'
    shutil.copyfile(src, os.path.join(brand_dir, dest_name))
    data['ascApiKeyId'] = key_id
    data['ascApiIssuerId'] = issuer_id
    data['ascApiKeyFile'] = dest_name
    cfgmod.save_transmute(brand_dir, data)
    print(f'copied key to {os.path.join(brand_dir, dest_name)} and updated transmute.json')

    print('verifying key against App Store Connect...')
    try:
        client = AscClient(key_id, issuer_id, os.path.join(brand_dir, dest_name))
        seeds, count = apple_ops.verify_key(client)
        print(f'authenticated OK; team seed id(s): {", ".join(sorted(seeds)) or "(none)"}; '
              f'{count} bundle id(s) visible')
        team = data.get('DEVELOPMENT_TEAM', '')
        if team and seeds and team not in seeds:
            print(f'WARNING: DEVELOPMENT_TEAM is {team} but this key sees team(s) '
                  f'{", ".join(sorted(seeds))} - wrong account key?')
        return True
    except Exception as e:
        msg = str(e)
        if asc_api.needs_account_holder(msg):
            # The agreements/membership 403 arrives AFTER Apple accepts the JWT,
            # so the key itself is good - success, with a loud explanation.
            holder = data.get('appleAccountHolderName', '')
            email = data.get('appleAccountHolderEmail', '')
            contact = f'{holder} <{email}>' if holder and email else (holder or email)
            print(report_mod.paint(f'VERIFICATION BLOCKED BY APPLE ACCOUNT STATUS: {msg}',
                                   'brightred'))
            print('Your key AUTHENTICATED - this error happens after Apple accepts the '
                  'key, so the')
            print('recorded key/IDs/.p8 are good. Do NOT re-create the key.')
            print("Only the team's ACCOUNT HOLDER can clear this (sign the pending "
                  'agreement /')
            print(f'renew the membership): {apple_ops.AGREEMENTS_URL}')
            if contact:
                print(f'Account Holder contact: {contact}')
            print('Until then, audit reports this brand as "Apple account status: '
                  'ACCOUNT HOLDER action needed".')
            return True
        print(f'VERIFICATION FAILED: {msg}')
        print('transmute.json fields were written - fix the key/IDs and re-run.')
        return False


def cmd_add_asc_key(args):
    args.brand = ensure_brand_dirs_exist([args.brand])[0]
    data = cfgmod.load_transmute(args.brand)
    print_asc_key_instructions(data)
    if not add_asc_key_flow(args.brand):
        sys.exit(1)


def ensure_required_fields(brand_dir, data, assume_yes=False):
    """Prompt for required identity fields that are missing or still placeholders.

    These cannot be inferred (packageName, iosBundleIdentifier, appName) - the user
    must supply them. Entered values are validated and written back to transmute.json.
    Non-interactive (--yes) runs abort with an actionable message instead.
    """
    problems = [k for k in cfgmod.REQUIRED_TRANSMUTE_FIELDS
                if not data.get(k) or cfgmod.PLACEHOLDER_RE.search(data.get(k) or '')]
    if not problems:
        return data
    print('\ntransmute.json is missing required values that cannot be inferred:')
    for k in problems:
        print(f'  {k} = {data.get(k, "(absent)")!r}')
    if assume_yes:
        raise SystemExit('Cannot proceed: edit these fields in transmute.json, '
                         'or run without --yes to be prompted for them.')
    for k in problems:
        while True:
            try:
                value = input(f'Enter value for {k}: ').strip()
            except (EOFError, KeyboardInterrupt):
                raise SystemExit('\nAborted - transmute.json unchanged.')
            if value and not cfgmod.PLACEHOLDER_RE.search(value):
                break
            print('  A real (non-placeholder) value is required.')
        data[k] = value
    cfgmod.save_transmute(brand_dir, data)
    print('transmute.json updated with the entered values.')
    return data


def apply_inferable_defaults(brand_dir, data, cfg):
    """Auto-fill fields whose correct values are known from brandtool_config.json."""
    missing = cfgmod.missing_inferable_fields(data, cfg)
    if missing:
        defaults = cfgmod.inferable_defaults(cfg)
        for k in missing:
            data[k] = defaults[k]
            print(f'auto-filled {k} in transmute.json from brandtool_config.json')
        cfgmod.save_transmute(brand_dir, data)
    return data


def cmd_create_project(args):
    args.brand = ensure_brand_dirs_exist([args.brand])[0]
    cfg, services = get_context(args)
    crm, usage, billing, firebase = (services['crm'], services['usage'],
                                     services['billing'], services['firebase'])
    brand_dir = args.brand
    data = cfgmod.load_transmute(brand_dir)
    data = ensure_required_fields(brand_dir, data, assume_yes=args.yes)
    data = apply_inferable_defaults(brand_dir, data, cfg)
    project_id = args.project_id or propose_project_id(brand_dir, data)
    display = data.get('firebaseProjectName') or data.get('appName') or project_id

    while True:
        print(f'\nAbout to create GCP/Firebase project:')
        print(f'  project id:   {project_id}')
        print(f'  display name: {display}')
        print(f'  billing:      {cfg["billingAccountId"]}')
        print(f'  grants:       serviceAccount:{cfg["automationServiceAccount"]} (editor)')
        admin = cfg.get('netparkAdminGrantee', '')
        print(f'                user:{admin} (owner)' if admin else
              '                WARNING: netparkAdminGrantee empty - no admin grant')
        if not args.yes:
            try:
                proceed = input('Proceed? [y/N] ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                print('\nAborted.')
                return
            if proceed != 'y':
                print('Aborted.')
                return
        try:
            fb.create_project(crm, project_id, display,
                              parent=cfg.get('parentResource') or None)
            break
        except Exception as e:
            msg = str(e).lower()
            if '409' in msg or 'already' in msg or 'requested entity' in msg:
                try:
                    project_id = input(
                        f'Project id "{project_id}" is taken. Enter a different id: ').strip()
                except (EOFError, KeyboardInterrupt):
                    raise SystemExit('\nAborted - no project created.')
                continue
            raise

    print('granting standard access...')
    fb.grant_role(crm, project_id,
                  f'serviceAccount:{cfg["automationServiceAccount"]}', 'roles/editor')
    admin = cfg.get('netparkAdminGrantee', '')
    if admin:
        fb.grant_role(crm, project_id, f'user:{admin}', 'roles/owner')
    print('linking billing...')
    fb.link_billing(billing, project_id, cfg['billingAccountId'])
    print('enabling APIs...')
    fb.enable_apis(usage, project_id, cfg['requiredApis'])
    print('adding Firebase...')
    fb.add_firebase(firebase, project_id)

    data['firebaseProjectId'] = project_id
    data['firebaseProjectNumber'] = fb.get_project_number(crm, project_id)
    cfgmod.save_transmute(brand_dir, data)
    print(f'\nDone. transmute.json updated with project id/number for {project_id}.')


def ensure_apps(services, cfg, brand_dir):
    """Create Firebase Android+iOS apps if missing, register fingerprints, download configs."""
    firebase = services['firebase']
    data = cfgmod.load_transmute(brand_dir)
    data = ensure_required_fields(brand_dir, data)
    data = apply_inferable_defaults(brand_dir, data, cfg)
    project_id = cfgmod.brand_project_id(brand_dir, data) or data['firebaseProjectId']

    android_app_id = fb.get_android_app(firebase, project_id, data['packageName'])
    if not android_app_id:
        print(f'creating Firebase Android app for {data["packageName"]}...')
        android_app_id = fb.create_android_app(firebase, project_id,
                                               data['appName'], data['packageName'])
    else:
        print('Firebase Android app already exists')

    ios_app_id = fb.get_ios_app(firebase, project_id, data['iosBundleIdentifier'])
    if not ios_app_id:
        print(f'creating Firebase iOS app for {data["iosBundleIdentifier"]}...')
        # same Firebase display name as the Android app (appName); the on-device
        # name comes from iosBundleDisplayName via Info.plist, not from Firebase
        ios_app_id = fb.create_ios_app(firebase, project_id, data['appName'],
                                       data['iosBundleIdentifier'],
                                       team_id=data.get('DEVELOPMENT_TEAM'),
                                       app_store_id=data.get('appStoreId'))
        if data.get('DEVELOPMENT_TEAM'):
            print(f'  Team ID set to {data["DEVELOPMENT_TEAM"]}')
        if data.get('appStoreId'):
            print(f'  App Store ID set to {data["appStoreId"]}')
    else:
        print('Firebase iOS app already exists (audit --fix maintains its '
              'Team ID / App Store ID)')

    print('registering cert fingerprints...')
    have = fb.list_sha_hashes(firebase, project_id, android_app_id)
    for sha_hash, cert_type in cfgmod.brand_fingerprints(data, cfg):
        if sha_hash not in have:
            fb.add_sha(firebase, project_id, android_app_id, sha_hash, cert_type)
            print(f'  added {cert_type} {sha_hash[:12]}...')

    print('downloading config files into brand dir...')
    fb.download_android_config(firebase, project_id, android_app_id, brand_dir)
    if ios_app_id:
        fb.download_ios_config(firebase, project_id, ios_app_id, brand_dir)
    else:
        print('  WARNING: iOS app id unavailable - GoogleService-Info.plist not downloaded')
    return android_app_id, ios_app_id


def cmd_create_apps(args):
    args.brand = ensure_brand_dirs_exist([args.brand])[0]
    cfg, services = get_context(args)
    ensure_apps(services, cfg, args.brand)
    print('Done.')


def ensure_keys(services, cfg, brand_dir):
    """Create the three restricted API keys + FCM admin SA where missing; update transmute.json."""
    apikeys, iam, crm = services['apikeys'], services['iam'], services['crm']
    data = cfgmod.load_transmute(brand_dir)
    data = ensure_required_fields(brand_dir, data)
    data = apply_inferable_defaults(brand_dir, data, cfg)
    project_id = cfgmod.brand_project_id(brand_dir, data) or data['firebaseProjectId']
    fps_sha1 = [h for h, t in cfgmod.brand_fingerprints(data, cfg) if t == 'SHA_1']
    changed = False

    specs = [
        ('androidGoogleMapsSDKApiKey',
         keys_ops.android_restrictions_body(fps_sha1, data['packageName'])),
        ('iosGoogleMapsSDKApiKey',
         keys_ops.ios_restrictions_body(data['iosBundleIdentifier'])),
        ('serverGooglePlacesAPIKey', keys_ops.places_restrictions_body()),
    ]
    for field, restrictions in specs:
        display_name = keys_ops.key_display_name(field, data, brand_dir)
        if data.get(field) and keys_ops.find_key_by_string(apikeys, project_id, data[field]):
            print(f'{field}: key already exists in {project_id}')
            continue
        old_string = data.get(field, '')
        data[field], action = keys_ops.ensure_key(
            apikeys, project_id, display_name, restrictions,
            tokens=keys_ops.KEY_PURPOSES[field]['tokens'])
        print(f'{field}: {"matching key adopted (restrictions corrected)" if action == "reused" else f"created new key {display_name!r}"}')
        if field == 'serverGooglePlacesAPIKey' and data[field] != old_string:
            audit_mod.places_server_update_notice(brand_dir, data[field])
        changed = True

    keyfile = data.get('messagingServiceAccountKeyFile', '')
    if not (keyfile and os.path.exists(os.path.join(brand_dir, keyfile))):
        print('provisioning FCM messaging service account + key...')
        data['messagingServiceAccountKeyFile'] = fb.ensure_fcm_admin(
            iam, crm, project_id, brand_dir,
            sa_email=data.get('fcmServiceAccount') or None)
        if not data.get('fcmServiceAccount'):
            data['fcmServiceAccount'] = (f'{fb.FCM_ADMIN_ID}@{project_id}'
                                         '.iam.gserviceaccount.com')
        changed = True
    else:
        print('FCM admin key file already present')

    if changed:
        cfgmod.save_transmute(brand_dir, data)
        print('transmute.json updated.')


def cmd_create_keys(args):
    args.brand = ensure_brand_dirs_exist([args.brand])[0]
    cfg, services = get_context(args)
    ensure_keys(services, cfg, args.brand)
    print('Done.')


def ensure_apple(cfg, brand_dir):
    """Register the bundle ID and enable required capabilities. Idempotent."""
    data = cfgmod.load_transmute(brand_dir)
    data = ensure_required_fields(brand_dir, data)
    client, reason = audit_mod.asc_client_for_brand(brand_dir, data)
    if client is None:
        raise SystemExit(f'App Store Connect: {reason}')
    bundle_id = data['iosBundleIdentifier']
    resource = apple_ops.find_bundle_id(client, bundle_id)
    if not resource:
        print(f'registering bundle id {bundle_id}...')
        resource = apple_ops.register_bundle_id(client, bundle_id, data['appName'])
    else:
        print('bundle id already registered')
    missing = apple_ops.missing_capabilities(
        client, resource, cfg.get('iosRequiredCapabilities', []))
    for cap in missing:
        print(f'enabling capability {cap}...')
        apple_ops.enable_capability(client, resource, cap)
    if not missing:
        print('all required capabilities already enabled')


def cmd_audit_unique(args):
    """Local-only cross-brand duplicate scan (no Google/Apple API calls)."""
    brand_dirs = cfgmod.find_brand_dirs(require_google_services=False)
    print(f'scanning {len(brand_dirs)} brand dirs for values that should be unique...')
    duplicates = uniqueness.find_duplicates(brand_dirs)
    use_color = _color_enabled(args)
    report_mod.set_color(use_color)
    text = uniqueness.render_duplicates(duplicates, color=use_color)
    if text:
        print(text)
        sys.exit(1)
    print('OK - no duplicated values found across brands.')


def cmd_create_apple(args):
    args.brand = ensure_brand_dirs_exist([args.brand])[0]
    cfg = cfgmod.load_tool_config(args.config)
    ensure_apple(cfg, args.brand)
    print('Done.')


def cmd_create(args):
    args.brand = ensure_brand_dirs_exist([args.brand])[0]
    cmd_create_project(args)
    cfg, services = get_context(args)
    ensure_apps(services, cfg, args.brand)
    ensure_keys(services, cfg, args.brand)
    data = cfgmod.load_transmute(args.brand)
    if audit_mod.asc_client_for_brand(args.brand, data)[0] is not None:
        ensure_apple(cfg, args.brand)
    else:
        print('skipping Apple stage - no ASC credentials (run brandtool add-asc-key '
              f'{args.brand} after generating a Team Key)')
    print('\nBrand Google setup complete. Next: run '
          f'"{remediation.default_tool_cmd()} audit {args.brand}" to verify, and see '
          'INSTRUCTIONS_BRAND_SETUP.md for the manual Play Console app creation steps.')


def cmd_check_agreements(args):
    """Fast Apple account/agreements sweep - no Google auth, one ASC probe per brand."""
    import json as jsonmod
    use_color = _color_enabled(args)
    report_mod.set_color(use_color)
    brand_dirs = cfgmod.find_brand_dirs(args.brands, require_google_services=False)
    if args.brands:
        brand_dirs = ensure_brand_dirs_exist(
            brand_dirs, interactive=sys.stdin.isatty() and not args.json)
    if not args.json:
        print(f'probing App Store Connect for {len(brand_dirs)} brand(s)...')
    results = audit_mod.agreements_status(brand_dirs)
    if args.json:
        print(jsonmod.dumps(results, indent=2))
        sys.exit(0 if all(r['status'] == 'OK' for r in results) else 1)

    colors = {'OK': 'green', 'ACTION NEEDED': 'brightred',
              'NO KEY': 'yellow', 'ERROR': 'brightred'}
    width = max((len(r['brand']) for r in results), default=0)
    print()
    for r in results:
        print(f"  {report_mod.paint(r['status'].ljust(13), colors[r['status']])} "
              f"{r['brand'].ljust(width)}  {r['detail']}")
        if r['status'] == 'ACTION NEEDED' and (r['holder_name'] or r['holder_email']):
            contact = f"{r['holder_name']} <{r['holder_email']}>".strip()
            print(f"  {''.ljust(13)} {''.ljust(width)}  -> contact Account Holder: {contact}")

    counts = {}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    print('\nSummary: ' + ', '.join(f'{n} {s}' for s, n in sorted(counts.items())))
    blocked = [r for r in results if r['status'] == 'ACTION NEEDED']
    if blocked:
        print(report_mod.paint(
            f'{len(blocked)} team(s) need their ACCOUNT HOLDER to act (sign the pending '
            f'agreement / renew): {apple_ops.AGREEMENTS_URL}', 'brightred'))
        for r in blocked:
            contact = f"{r['holder_name']} <{r['holder_email']}>".strip() or '(no contact recorded)'
            print(f"  {r['brand']}: {contact}")
    if counts.get('NO KEY'):
        print(report_mod.paint(
            f"status UNKNOWN for {counts['NO KEY']} brand(s) with no ASC Team Key - "
            f'record one with: {remediation.default_tool_cmd()} add-asc-key <brand_dir>',
            'yellow'))
    sys.exit(1 if (counts.get('ACTION NEEDED') or counts.get('ERROR')) else 0)


def cmd_check_certs(args):
    """Apple certificate-expiry sweep across brand teams - no Google auth."""
    import json as jsonmod
    use_color = _color_enabled(args)
    report_mod.set_color(use_color)
    brand_dirs = cfgmod.find_brand_dirs(args.brands, require_google_services=False)
    if args.brands:
        brand_dirs = ensure_brand_dirs_exist(
            brand_dirs, interactive=sys.stdin.isatty() and not args.json)
    if not args.json:
        print(f'checking Apple certificates for {len(brand_dirs)} brand(s), '
              f'{args.days}-day window...')
    results = audit_mod.certs_status(brand_dirs, days=args.days)
    if args.json:
        print(jsonmod.dumps(results, indent=2))
        sys.exit(0 if all(r['status'] in ('OK', 'NO KEY') for r in results) else 1)

    colors = {'OK': 'green', 'EXPIRING': 'brightred', 'NO KEY': 'yellow',
              'BLOCKED': 'brightred', 'ERROR': 'brightred'}
    width = max((len(r['brand']) for r in results), default=0)
    dist_expiring = dev_only = 0
    print()
    for r in results:
        print(f"  {report_mod.paint(r['status'].ljust(9), colors[r['status']])} "
              f"{r['brand'].ljust(width)}  {r['detail']}")
        if r['status'] == 'EXPIRING':
            has_dist = False
            for name, ctype, date, days_left in r['certs']:
                when = (f'EXPIRED {date}' if days_left < 0
                        else f'expires {date} ({days_left}d)')
                is_dist = 'DISTRIBUTION' in ctype
                has_dist = has_dist or is_dist
                line = f'{name} ({ctype}) {when}'
                color = 'brightred' if (is_dist or days_left < 0) else 'yellow'
                print(f"  {''.ljust(9)} {''.ljust(width)}    "
                      + report_mod.paint(line, color))
            if has_dist:
                dist_expiring += 1
            else:
                dev_only += 1

    counts = {}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    print('\nSummary: ' + ', '.join(f'{n} {s}' for s, n in sorted(counts.items())))
    if dist_expiring:
        print(report_mod.paint(
            f'{dist_expiring} team(s) have a DISTRIBUTION cert expiring - that '
            'blocks releasing; renew before the next release.', 'brightred'))
    if dev_only:
        print(report_mod.paint(
            f'{dev_only} team(s) only have DEVELOPMENT certs expiring - harmless '
            '(Xcode auto-renews on the next device build).', 'yellow'))
    if counts.get('NO KEY'):
        print(report_mod.paint(
            f"status UNKNOWN for {counts['NO KEY']} brand(s) with no ASC Team Key - "
            f'record one with: {remediation.default_tool_cmd()} add-asc-key <brand_dir>',
            'yellow'))
    if dist_expiring or dev_only:
        print()
        for line in remediation.xcode_cert_renewal_instructions():
            print(line)
    sys.exit(1 if (dist_expiring or counts.get('BLOCKED') or counts.get('ERROR'))
             else 0)


def usage_guide():
    """The full colored usage guide (bare invocation, -h, --help)."""
    from brandtool_lib.report import paint

    def h(text):    # section header
        return paint(text, 'cyan')

    def c(text):    # command name
        return paint(text, 'green')

    def warn(text):
        return paint(text, 'brightred')

    return f'''
{h('brandtool - create and audit netPark loyalty brand Google/Apple resources')}

  Usage:   bin\\brandtool <command> [brand_dir ...] [options]     (Windows)
           ./bin/brandtool.sh <command> ...                      (macOS/Linux)
  Details: MANUAL_BRAND_TOOLING.md (reference) and INSTRUCTIONS_BRAND_SETUP.md (new-brand walkthrough)
  Auth:    ADC by default - run "gcloud auth application-default login" once.
           Per-command flag help: bin\\brandtool <command> --help

{h('COMMANDS')}

  {c('audit')} [brand_dir ...] [--fix] [--yes] [--json] [--no-color] [--no-links] [--noprompt]
      Audit one/many/ALL brands against Firebase, Google Cloud, Play, and App
      Store Connect. With no brand args, ALL brands are audited - use
      {c('active')} (or {c('.')}) as the brand arg to audit only the brand currently
      transmuted into the working tree (works for every command taking a
      brand dir). In a terminal it LOOPS until clean: after a dirty pass you
      choose [F]ix / [R]e-audit / [I]nfo (fix advice + console links) / [A]pple
      key setup / [Q]uit. {warn('Exit code 0 ONLY when every check passes')} - wire
      --noprompt into release scripts. --fix runs one fix pass immediately.
      Fixes read/write transmute.json (records inferred appStoreId, apnsKeyId,
      firebaseProjectId/Name, fcmServiceAccount) and patch live Google state.

  {c('audit-unique')} [--no-color]
      Local-only scan of ALL brand dirs for duplicated values that must be
      unique (package/bundle ids, API keys, project ids, key ids, teams).
      Catches copy-paste leftovers from cloning a brand dir. No API calls.

  {c('create-project')} <brand_dir> [--project-id ID] [--yes]
      Create + provision the brand's GCP/Firebase project. The project id is
      proposed from transmute.json's firebaseProjectId, else derived from the
      brand directory name; if Google reports the id taken you are prompted
      for another. Grants the automation service account (editor) and the
      netPark admin (owner), links billing, enables the required APIs,
      initializes Firebase, then writes firebaseProjectId/Number back into
      transmute.json.

  {c('create-apps')} <brand_dir>
      Create the Firebase Android app (from packageName + appName) and iOS app
      (from iosBundleIdentifier + iosBundleDisplayName, with Team ID from
      DEVELOPMENT_TEAM and App Store ID from appStoreId when present).
      Registers all debug/release cert fingerprints and downloads fresh
      google-services.json + GoogleService-Info.plist into the brand dir.
      Idempotent - existing apps are detected and left alone.

  {c('create-keys')} <brand_dir>
      Create the three restricted API keys - "Android Loyalty App Google Maps
      SDK API Key" (signing certs x packageName + Maps SDK for Android API
      target), "iOS Loyalty App Google Maps SDK API Key" (bundle id + Maps
      SDK for iOS target), "Loyalty App Google Places API Key for netPark
      Server <locationId(s)>" (both Places API targets). No brand prefix: the
      project identifies the brand, and Google caps key names at 63 chars
      (many-location brands drop 'Loyalty App' from the Places name to fit).
      An existing key whose name matches the purpose (android+maps /
      ios+maps / places) is adopted instead - its restrictions get corrected.
      Also provisions the FCM messaging service account (honors
      fcmServiceAccount if recorded) and its key file. All results are written
      into transmute.json.

  {c('create')} <brand_dir> [--project-id ID] [--yes]
      One shot: {c('create-project')} -> {c('create-apps')} -> {c('create-keys')}, then the
      Apple stage ({c('create-apple')}) automatically IF ASC credentials are
      recorded, else it prints a skip notice. Every stage is idempotent, so
      re-run after any failure. Ends by suggesting an audit.

  {c('create-apple')} <brand_dir>
      App Store Connect side: registers the bundle ID (iosBundleIdentifier,
      named after appName) in the client's developer portal and enables the
      required App ID capabilities (push, Sign in with Apple, associated
      domains, Wallet). Requires the brand's ASC Team Key ({c('add-asc-key')}).

  {c('add-asc-key')} <brand_dir>
      Record + verify an App Store Connect Team Key for the brand's client
      Apple account. Prints the key-generation click-path, prompts for Key ID
      and Issuer ID, finds the downloaded .p8 (Enter/R re-checks Downloads),
      copies it into the brand dir, writes the asc* fields to transmute.json,
      and live-verifies against the right team. If the client's Account Holder
      has not enabled API access, GIVE_ME_REQUEST_EMAIL generates the email to
      send them.

  {c('check-agreements')} [brand_dir ...] [--json] [--no-color]
      The "did Apple change the agreements again?" sweep: one cheap ASC probe
      per brand that has a Team Key recorded. Reports {paint('OK', 'green')} /
      {warn('ACTION NEEDED')} (the team's Account Holder must sign at
      appstoreconnect.apple.com/agreements - prints who to contact) /
      {paint('NO KEY', 'yellow')} (status unknown - record a Team Key) / ERROR.
      Needs NO Google auth, so it is fast. Exit 0 only when no team is blocked.

  {c('check-personal-ios-dev-certs')} [brand_dir ...] [--days N] [--json] [--no-color]
      Apple certificate-expiry sweep across brand teams (default window 60
      days). {warn('DISTRIBUTION certs block releasing')}; DEVELOPMENT certs are
      harmless (Xcode auto-renews on the next device build). When anything is
      expiring it prints the step-by-step Xcode renewal instructions. Needs NO
      Google auth. Exit 0 unless a distribution cert is at risk.

{h('MISSING transmute.json DATA - who supplies what')}

  Identity fields you must decide (packageName, iosBundleIdentifier, appName):
  the create commands PROMPT for missing/placeholder values and write your
  answers back to transmute.json. Inferable fields (cert fingerprints,
  billingAccountId) are auto-filled from bin/brandtool_config.json with a
  notice. Live-inferable fields (appStoreId, apnsKeyId, fcmServiceAccount,
  firebaseProjectId/Name) are offered as recorded fixes by {c('audit')} --fix.

{h('TYPICAL PROCESS - new brand')}

  1. Copy branded_loyalty/STARTER_BRAND_DIR -> branded_loyalty/<brand>, replace
     the assets, fill the USER fields in transmute.json  (INSTRUCTIONS_BRAND_SETUP.md step 1-2)
  2. bin\\brandtool {c('create')} branded_loyalty/<brand>
  3. Manual Google Play: create the app in Play Console + declarations
     (cannot be automated)                              (INSTRUCTIONS_BRAND_SETUP.md step 4)
  4. Apple: {c('add-asc-key')}, then {c('create-apple')} if step 2 skipped it; create the
     ASC app record manually; APNs key into the brand dir + Firebase console
  5. bin\\brandtool {c('audit')} branded_loyalty/<brand>  - repeat [F]ix until
     {paint('AUDIT CLEAN', 'green')}

{h('TYPICAL PROCESS - maintenance / pre-release')}

  bin\\brandtool {c('audit')} branded_loyalty/<brand> --fix    (interactive fix loop)
  bin\\brandtool {c('audit')} --noprompt                       (all brands, CI/script gate)
  bin\\brandtool {c('audit-unique')}                           (cross-brand duplicate scan)
  bin\\brandtool {c('check-agreements')}                       (weekly Apple agreements sweep)
  bin\\brandtool {c('check-personal-ios-dev-certs')}                            (Apple cert-expiry sweep + Xcode how-to)
'''


def main():
    # Bare invocation / top-level help shows the full usage guide.
    if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help', 'help'):
        print(usage_guide())
        return

    parser = argparse.ArgumentParser(prog='brandtool', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--creds', help='service-account JSON file (default: ADC)')
    parser.add_argument('--config', help='tool config path (default: bin/brandtool_config.json)')
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('audit', help='audit brands against Firebase/Cloud/Play')
    p.add_argument('brands', nargs='*', help='brand dirs (default: all real brands)')
    p.add_argument('--fix', action='store_true', help='interactively fix fixable issues')
    p.add_argument('--yes', '-y', action='store_true', help='fix without prompting')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--no-color', action='store_true',
                   help='disable ANSI colors (auto-disabled when piped or NO_COLOR is set)')
    p.add_argument('--no-links', action='store_true',
                   help='omit the "useful console links" addendum')
    p.add_argument('--noprompt', '--no-prompt', action='store_true', dest='noprompt',
                   help='never prompt: print report + exit code only (also implied '
                        'by piped output and --json)')
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser('create-project', help='create + provision the GCP/Firebase project')
    p.add_argument('brand', help='brand directory')
    p.add_argument('--project-id', help='override the proposed project id')
    p.add_argument('--yes', '-y', action='store_true', help='skip confirmation prompt')
    p.set_defaults(func=cmd_create_project)

    p = sub.add_parser('create-apps', help='create Firebase Android/iOS apps + fingerprints + configs')
    p.add_argument('brand', help='brand directory')
    p.set_defaults(func=cmd_create_apps)

    p = sub.add_parser('create-keys', help='create restricted API keys + FCM admin SA')
    p.add_argument('brand', help='brand directory')
    p.set_defaults(func=cmd_create_keys)

    p = sub.add_parser('create', help='one-shot: create-project + create-apps + create-keys')
    p.add_argument('brand', help='brand directory')
    p.add_argument('--project-id', help='override the proposed project id')
    p.add_argument('--yes', '-y', action='store_true', help='skip confirmation prompt')
    p.set_defaults(func=cmd_create)

    p = sub.add_parser('create-apple', help='register bundle ID + enable capabilities (ASC)')
    p.add_argument('brand', help='brand directory')
    p.set_defaults(func=cmd_create_apple)

    p = sub.add_parser('add-asc-key', help='record + verify a downloaded ASC Team Key for a brand')
    p.add_argument('brand', help='brand directory')
    p.set_defaults(func=cmd_add_asc_key)

    p = sub.add_parser('check-agreements',
                       help='fast Apple agreements/account-status sweep across brands')
    p.add_argument('brands', nargs='*', help='brand dirs (default: ALL brands)')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--no-color', action='store_true', help='disable ANSI colors')
    p.set_defaults(func=cmd_check_agreements)

    p = sub.add_parser('check-personal-ios-dev-certs',
                       help='Apple certificate-expiry sweep across brand teams')
    p.add_argument('brands', nargs='*', help='brand dirs (default: ALL brands)')
    p.add_argument('--days', type=int, default=60,
                   help='flag certs expiring within this many days (default 60)')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--no-color', action='store_true', help='disable ANSI colors')
    p.set_defaults(func=cmd_check_certs)

    p = sub.add_parser('audit-unique',
                       help='scan ALL brands for duplicated values that should be unique '
                            '(local-only, no API calls)')
    p.add_argument('--no-color', action='store_true', help='disable ANSI colors')
    p.set_defaults(func=cmd_audit_unique, json=False)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
