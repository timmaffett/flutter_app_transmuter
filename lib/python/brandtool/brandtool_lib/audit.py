"""Per-brand audit: assembles report checks from the live Google and Apple state."""
import glob
import json
import os
import re
import shutil
import sys

from . import apple_ops
from . import asc_api
from . import config as cfgmod
from . import firebase_ops as fb
from . import keys_ops
from . import play_ops
from .report import ERROR, INFO, ISSUE, OK, SKIP, BrandReport


def firebase_console_url(project_id, package):
    return (f'https://console.firebase.google.com/project/{project_id}'
            f'/settings/general/android:{package}')


def cloud_credentials_url(project_id):
    return f'https://console.cloud.google.com/apis/credentials?project={project_id}'


def _audit_root_transmute_sync(r, brand_dir):
    """When the audited brand is the ACTIVE one: the audit reads ONLY the brand
    dir, so a differing working-tree (root) transmute.json means edits are
    sitting somewhere the audit cannot see. Show the field diff plus both file
    dates and which is newer, so the user can decide the sync direction."""
    import datetime
    root_path = os.path.join(cfgmod.REPO_ROOT, 'transmute.json')
    brand_path = os.path.join(brand_dir, 'transmute.json')
    try:
        with open(root_path) as f:
            root = json.load(f)
        brand = cfgmod.load_transmute(brand_dir)
    except Exception as e:
        r.add('root transmute.json sync', ERROR, str(e)[:160])
        return

    def stamp(path):
        return datetime.datetime.fromtimestamp(
            os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')

    if root == brand:
        r.add('root transmute.json sync', OK,
              'this brand is ACTIVE - the audit reads ONLY the brand dir, and the '
              'working-tree (root) transmute.json currently matches it')
        return
    diffs = [f'{k}: root={root.get(k, "(absent)")!r} vs brand={brand.get(k, "(absent)")!r}'
             for k in sorted(set(root) | set(brand)) if root.get(k) != brand.get(k)]
    shown = '; '.join(diffs[:8]) + (f' (+{len(diffs) - 8} more)' if len(diffs) > 8 else '')
    root_newer = os.path.getmtime(root_path) > os.path.getmtime(brand_path)
    if not root_newer:
        # The brand dir being newer is the normal aftermath of audit fixes
        # recording fields there - no alarm, just a reminder to re-switch.
        from .report import paint
        r.add('root transmute.json sync', INFO,
              paint('this brand is ACTIVE and the brand dir transmute.json is NEWER '
                    f'than the working-tree copy (differences: {shown}; root '
                    f'{stamp(root_path)}, brand dir {stamp(brand_path)}). ', 'pink')
              + paint(f'REMEMBER to run transmute --switch {brand_dir} to update the '
                      'working tree to the latest BRAND DIRECTORY files when the '
                      'audit is complete.', 'green'))
        return
    r.add('root transmute.json sync', ISSUE,
          'this brand is ACTIVE but the working-tree (root) transmute.json DIFFERS '
          'from the brand dir copy, and the audit reads ONLY the brand dir. You must '
          'resolve the differences and sync the project and brand transmute.json '
          f'files before continuing! Differences: {shown}. Modified: root '
          f'{stamp(root_path)}, brand dir {stamp(brand_path)} - ROOT (working tree) '
          'is NEWER. transmute --update copies working tree -> brand dir; '
          f'transmute --switch {brand_dir} copies brand dir -> working tree.',
          flash=True)


def audit_brand(services, cfg, brand_dir, publisher=None):
    brand = os.path.basename(os.path.normpath(brand_dir))
    r = BrandReport(brand)
    try:
        data = cfgmod.load_transmute(brand_dir)
    except Exception as e:
        r.add('transmute.json', ERROR, str(e)[:160])
        return r
    r.package = data.get('packageName', '?')
    r.ios_bundle = data.get('iosBundleIdentifier', '')

    # 0. active brand: verify the working-tree transmute.json matches the brand dir
    if cfgmod.is_active_brand(brand_dir):
        _audit_root_transmute_sync(r, brand_dir)

    # 1. transmute.json completeness
    missing = cfgmod.missing_required_fields(data)
    placeholders = cfgmod.placeholder_fields(data)
    if missing or placeholders:
        parts = []
        if missing:
            parts.append('missing: ' + ', '.join(_val(m) for m in missing))
        if placeholders:
            parts.append('placeholders: ' + ', '.join(_val(p) for p in placeholders))
        r.add('transmute.json fields', ISSUE, '; '.join(parts))
    else:
        r.add('transmute.json fields', OK)

    # 1b. inferable fields brandtool can fill from tool config (audit --fix offers it)
    inferable = cfgmod.missing_inferable_fields(data, cfg)
    if inferable:
        def fix_inferable(fields=tuple(inferable)):
            defaults = cfgmod.inferable_defaults(cfg)
            current = cfgmod.load_transmute(brand_dir)
            for k in fields:
                current[k] = defaults[k]
            cfgmod.save_transmute(brand_dir, current)
        r.add('transmute.json inferable fields', ISSUE,
              'can auto-fill from brandtool_config.json: '
              + ', '.join(_val(f) for f in inferable),
              fix=fix_inferable)
    else:
        r.add('transmute.json inferable fields', OK)

    # 1c. firebaseProjectId recorded in transmute.json, consistent with google-services.json
    # (the local file downloaded from the live Firebase project is the authoritative source).
    gs_pid = cfgmod.google_services_project_id(brand_dir)
    tj_pid = data.get('firebaseProjectId', '')
    tj_pid_valid = bool(tj_pid) and not cfgmod.PLACEHOLDER_RE.search(tj_pid)
    if gs_pid:
        if not tj_pid_valid:
            def fix_record_project():
                current = cfgmod.load_transmute(brand_dir)
                current['firebaseProjectId'] = gs_pid
                number = cfgmod.google_services_project_number(brand_dir)
                if number:
                    current['firebaseProjectNumber'] = number
                cfgmod.save_transmute(brand_dir, current)
            r.add('firebaseProjectId recorded', ISSUE,
                  f'not in transmute.json; google-services.json says "{_val(gs_pid)}"',
                  fix=fix_record_project)
        elif tj_pid != gs_pid:
            r.add('firebaseProjectId recorded', ISSUE,
                  f'transmute.json says "{_val(tj_pid)}" but google-services.json says '
                  f'"{_val(gs_pid)}" - conflicting sources (possibly a second/legacy '
                  'project); resolve manually')
        else:
            r.add('firebaseProjectId recorded', OK, _val(gs_pid))
    elif tj_pid_valid:
        r.add('firebaseProjectId recorded', OK,
              f'{_val(tj_pid)} (no google-services.json to cross-check)')

    project_id = cfgmod.brand_project_id(brand_dir, data)
    if not project_id:
        r.add('project', ERROR, 'no firebaseProjectId or google-services.json - cannot audit further')
        return r
    r.project_id = project_id
    firebase = services['firebase']
    billing = services['billing']
    usage = services['usage']
    apikeys = services['apikeys']
    iam = services['iam']
    _audit_project_name(r, services, brand_dir, data, project_id)

    # 2. billing
    try:
        acct = fb.get_billing_account(billing, project_id)
        want_id = data.get('billingAccountId') or cfg['billingAccountId']
        want = f'billingAccounts/{want_id}'
        if acct == want:
            r.add('billing linked', OK)
        else:
            r.add('billing linked', ISSUE,
                  f'is "{_val(acct or "UNLINKED")}", want "{_val(want)}"',
                  fix=lambda: fb.link_billing(billing, project_id, want_id))
    except Exception as e:
        r.add('billing linked', ERROR, str(e)[:160])

    # 3. required APIs
    try:
        enabled = fb.list_enabled_apis(usage, project_id)
        missing_apis = [a for a in cfg['requiredApis'] if a not in enabled]
        if missing_apis:
            r.add('required APIs', ISSUE,
                  'disabled: ' + ', '.join(_val(a) for a in missing_apis),
                  fix=lambda apis=missing_apis: fb.enable_apis(usage, project_id, apis))
        else:
            r.add('required APIs', OK)
    except Exception as e:
        r.add('required APIs', ERROR, str(e)[:160])

    # 4. Firebase apps
    android_app_id = None
    ios_app_id = None
    try:
        android_app_id = fb.get_android_app(firebase, project_id, data['packageName'])
        if android_app_id:
            r.add('Firebase Android app', OK)
        else:
            def fix_create_android():
                app_id = fb.create_android_app(firebase, project_id,
                                               data['appName'], data['packageName'])
                fps = cfgmod.brand_fingerprints(data, cfg)
                for sha_hash, cert_type in fps:
                    fb.add_sha(firebase, project_id, app_id, sha_hash, cert_type)
                fb.download_android_config(firebase, project_id, app_id, brand_dir)
                print(f'    created Firebase Android app {_val(app_id)}, registered '
                      f'{len(fps)} cert fingerprint(s), and downloaded a fresh '
                      'google-services.json into the brand dir.')
            r.add('Firebase Android app', ISSUE,
                  f'no app for {_val(data["packageName"])} - [F]ix creates it, '
                  'registers the cert fingerprints, and downloads a fresh '
                  'google-services.json (same as create-apps)',
                  fix=fix_create_android,
                  console_url=firebase_console_url(project_id, data['packageName']))
    except Exception as e:
        r.add('Firebase Android app', ERROR, str(e)[:160])
    try:
        ios_app = fb.get_ios_app_full(firebase, project_id, data['iosBundleIdentifier'])
        ios_app_id = ios_app['appId'] if ios_app else None
        r.ios_app_id = ios_app_id
        if ios_app:
            r.add('Firebase iOS app', OK)
            _audit_ios_app_metadata(r, firebase, project_id, brand_dir, data, ios_app)
        else:
            def fix_create_ios():
                # same Firebase display name as the Android app (appName)
                app_id = fb.create_ios_app(firebase, project_id, data['appName'],
                                           data['iosBundleIdentifier'],
                                           team_id=data.get('DEVELOPMENT_TEAM'),
                                           app_store_id=data.get('appStoreId'))
                fb.download_ios_config(firebase, project_id, app_id, brand_dir)
                print(f'    created Firebase iOS app {_val(app_id)} (Team ID '
                      f'{_val(data.get("DEVELOPMENT_TEAM") or "(unset)")}, App Store ID '
                      f'{_val(data.get("appStoreId") or "(unset)")}) and downloaded a '
                      'fresh GoogleService-Info.plist into the brand dir.')
                print(_red('    ACTION REQUIRED: the NEW iOS app has NO APNs key in '
                           'Firebase Cloud Messaging yet - pushes will not work until '
                           'it is uploaded (the "APNs key in Firebase" check walks '
                           'you through it).'))
            r.add('Firebase iOS app', ISSUE,
                  f'no app for {_val(data["iosBundleIdentifier"])} - [F]ix creates it '
                  '(Team ID / App Store ID from transmute.json) and downloads a fresh '
                  'GoogleService-Info.plist (same as create-apps)',
                  fix=fix_create_ios)
    except Exception as e:
        r.add('Firebase iOS app', ERROR, str(e)[:160])

    # 5. fingerprints
    if android_app_id:
        try:
            have = fb.list_sha_hashes(firebase, project_id, android_app_id)
            missing_fps = [(h, t) for h, t in cfgmod.brand_fingerprints(data, cfg)
                           if h not in have]
            if missing_fps:
                def fix_fps(fps=tuple(missing_fps)):
                    for h, t in fps:
                        fb.add_sha(firebase, project_id, android_app_id, h, t)
                r.add('cert fingerprints', ISSUE,
                      'missing ' + ', '.join(f'{t} ' + _val(f'{h[:12]}...')
                                             for h, t in missing_fps),
                      fix=fix_fps,
                      console_url=firebase_console_url(project_id, data['packageName']))
            else:
                r.add('cert fingerprints', OK)
        except Exception as e:
            r.add('cert fingerprints', ERROR, str(e)[:160])

        # 6a. local google-services.json consistent with the live Firebase Android app
        gs_path = os.path.join(brand_dir, 'google-services.json')
        if os.path.exists(gs_path):
            with open(gs_path) as f:
                gs = json.load(f)
            local_ids = {c['client_info']['mobilesdk_app_id'] for c in gs.get('client', [])}
            if android_app_id in local_ids and gs['project_info']['project_id'] == project_id:
                r.add('google-services.json in sync', OK,
                      f'local file contains the live Android appId {_val(android_app_id)}')
            else:
                r.add('google-services.json in sync', ISSUE,
                      f'local file is stale/wrong project - live Android appId '
                      f'{_val(android_app_id)} not in it (re-download via create-apps)')
        else:
            r.add('google-services.json in sync', ISSUE, 'file missing from brand dir')

    # 6b. local plist consistent with the live Firebase iOS app
    if ios_app_id:
        plist_path = os.path.join(brand_dir, 'GoogleService-Info.plist')
        if os.path.exists(plist_path):
            with open(plist_path, encoding='utf-8') as f:
                plist_text = f.read()
            if ios_app_id in plist_text:
                r.add('GoogleService-Info.plist in sync', OK,
                      f'local file contains the live iOS appId {_val(ios_app_id)}')
            else:
                r.add('GoogleService-Info.plist in sync', ISSUE,
                      f'local file is stale/wrong project - live iOS appId '
                      f'{_val(ios_app_id)} not in it (re-download via create-apps)')
        else:
            r.add('GoogleService-Info.plist in sync', ISSUE, 'file missing from brand dir')

    # 6c. local firebase_options.dart consistent with the live Firebase apps
    fo_path = os.path.join(brand_dir, 'firebase_options.dart')
    if os.path.exists(fo_path):
        with open(fo_path, encoding='utf-8') as f:
            fo_text = f.read()
        missing_ids = [i for i in (android_app_id, ios_app_id) if i and i not in fo_text]
        if missing_ids:
            from .report import paint
            configure_cmd = paint('flutterfire configure', 'command')
            update_cmd = paint('transmute --update', 'command')
            if cfgmod.is_active_brand(brand_dir):
                remedy = (' (this brand IS already the ACTIVE brand - run '
                          f'{configure_cmd}, then {update_cmd} to sync the result '
                          'back into the brand dir)')
            else:
                switch_cmd = paint(f'transmute --switch {brand_dir}', 'command')
                remedy = (f' (regenerate: this brand must be the ACTIVE brand first - '
                          f'{switch_cmd} if you want to work on it now, then '
                          f'{configure_cmd}, then {update_cmd} to sync the result '
                          'back into the brand dir)')
            r.add('firebase_options.dart in sync', ISSUE,
                  'local file is stale - live app id(s) not in it: '
                  + ', '.join(_val(i) for i in missing_ids) + remedy)
        else:
            r.add('firebase_options.dart in sync', OK,
                  'local file contains the live Android+iOS app ids')
    else:
        r.add('firebase_options.dart in sync', ISSUE, 'file missing from brand dir')

    # 7. API keys
    fps_sha1 = [h for h, t in cfgmod.brand_fingerprints(data, cfg) if t == 'SHA_1']
    cert_labels = {cfgmod.clean_fp(cfg.get('releaseSha1', '')): 'release signing cert',
                   cfgmod.clean_fp(cfg.get('debugSha1', '')): 'debug signing cert'}

    def describe_android(lacking):
        parts = [f'{fp} ({cert_labels.get(fp, "extra cert from transmute.json")})'
                 for fp in lacking]
        return (f'missing app signing fingerprint(s) for package '
                f'{data["packageName"]}: ' + '; '.join(parts) +
                ' - release builds get denied by the Maps API until allowed')

    try:
        for purpose in cfg.get('apiKeyPurposes', []):
            services_list = purpose.get('services', [])
            if purpose.get('restriction') == 'android':
                missing_fn = (lambda key: keys_ops.android_restriction_missing(
                    key, fps_sha1, data['packageName']))
                body_fn = (lambda s=services_list: keys_ops.android_restrictions_body(
                    fps_sha1, data['packageName'], s))
                describe = describe_android
            elif purpose.get('restriction') == 'ios':
                missing_fn = (lambda key: [] if keys_ops.ios_restriction_ok(
                    key, data['iosBundleIdentifier']) else ['bundle id'])
                body_fn = (lambda s=services_list: keys_ops.ios_restrictions_body(
                    data['iosBundleIdentifier'], s))
                describe = (lambda lacking: f'key does not allow bundle id '
                                            f'{data["iosBundleIdentifier"]}')
            else:  # api_only: the API-target requirement covers it
                missing_fn = lambda key: []
                body_fn = (lambda s=services_list:
                           keys_ops.api_only_restrictions_body(s))
                describe = None
            _audit_key(r, apikeys, project_id, brand_dir, data, purpose, cfg,
                       missing_fn, body_fn, describe)
    except Exception as e:
        r.add('API keys', ERROR, str(e)[:160])

    # 8. FCM messaging service account + key file
    _audit_fcm(r, services, brand_dir, data, project_id,
               server_copy=cfg.get('fcmServerCopy'),
               customer_id_pattern=cfg.get('customerIdPattern', r'\d+'))

    # 9. Play
    if publisher is None:
        r.add('Play Store app', SKIP, 'play credentials not configured')
    else:
        try:
            status, detail = play_ops.check_app(publisher, data['packageName'])
            if status == play_ops.APP_OK:
                r.add('Play Store app', OK)
                r.add('Play signing cert', INFO,
                      'verify app-signing cert equals the release cert in Play Console '
                      '(Test and release -> App integrity); the Play API does not expose it')
            elif status == play_ops.APP_MISSING:
                r.add('Play Store app', ISSUE, detail + ' (creation is manual - see INSTRUCTIONS_BRAND_SETUP.md)')
            else:
                r.add('Play Store app', ERROR, detail)
        except Exception as e:
            r.add('Play Store app', ERROR, str(e)[:160])

    # 10. Apple / App Store Connect
    client, _ = asc_client_for_brand(brand_dir, data)
    _audit_apple(r, cfg, brand_dir, data, client)
    return r


def asc_client_for_brand(brand_dir, data):
    """(AscClient, None), or (None, reason) when per-brand ASC creds are absent/incomplete."""
    key_id = data.get('ascApiKeyId', '')
    issuer_id = data.get('ascApiIssuerId', '')
    key_file = data.get('ascApiKeyFile', '')
    if not (key_id and issuer_id and key_file):
        return None, ('credentials not configured (run: brandtool add-asc-key <brand>; '
                      'generate a Team Key first: App Store Connect -> Users and Access '
                      '-> Integrations -> Team Keys)')
    p8_path = os.path.join(brand_dir, key_file)
    if not os.path.exists(p8_path):
        return None, f'{key_file} missing from brand dir'
    return asc_api.AscClient(key_id, issuer_id, p8_path), None


needs_account_holder = asc_api.needs_account_holder


def agreements_status(brand_dirs, client_factory=None):
    """One cheap ASC probe per brand: is the team's Apple account healthy?

    There is no agreements endpoint - a healthy account answers a trivial
    request, a blocked one 403s with agreement/membership text (see
    asc_api.needs_account_holder). Returns a list of dicts with keys
    brand, status (OK | ACTION NEEDED | NO KEY | ERROR), detail,
    holder_name, holder_email."""
    factory = client_factory or asc_client_for_brand
    results = []
    for d in brand_dirs:
        brand = os.path.basename(os.path.normpath(d))
        entry = {'brand': brand, 'holder_name': '', 'holder_email': ''}
        try:
            data = cfgmod.load_transmute(d)
        except Exception as e:
            entry.update(status='ERROR', detail=f'transmute.json unreadable: {e}')
            results.append(entry)
            continue
        entry['holder_name'] = data.get('appleAccountHolderName', '')
        entry['holder_email'] = data.get('appleAccountHolderEmail', '')
        client, why = factory(d, data)
        if client is None:
            entry.update(status='NO KEY', detail=why)
        else:
            try:
                client.get('/bundleIds', params={'limit': 1})
                entry.update(status='OK', detail='agreements in effect; API answering')
            except Exception as e:
                msg = str(e)
                if needs_account_holder(msg):
                    entry.update(status='ACTION NEEDED', detail=msg[:250])
                else:
                    entry.update(status='ERROR', detail=msg[:250])
        results.append(entry)
    return results


def certs_status(brand_dirs, days=60, client_factory=None):
    """Per brand team: Apple certificates expiring within `days`.

    Returns a list of dicts with keys brand, status (OK | EXPIRING | NO KEY |
    BLOCKED | ERROR), detail, and certs - a list of (name, type, yyyy-mm-dd,
    days_left) tuples, soonest first (days_left < 0 = already expired)."""
    factory = client_factory or asc_client_for_brand
    results = []
    for d in brand_dirs:
        brand = os.path.basename(os.path.normpath(d))
        entry = {'brand': brand, 'certs': []}
        try:
            data = cfgmod.load_transmute(d)
        except Exception as e:
            entry.update(status='ERROR', detail=f'transmute.json unreadable: {e}')
            results.append(entry)
            continue
        client, why = factory(d, data)
        if client is None:
            entry.update(status='NO KEY', detail=why)
        else:
            try:
                certs = apple_ops.expiring_certificates(client, days=days)
                if certs:
                    entry.update(status='EXPIRING', certs=certs,
                                 detail=f'{len(certs)} certificate(s) expiring within '
                                        f'{days} days')
                else:
                    entry.update(status='OK',
                                 detail=f'no certificates expiring within {days} days')
            except Exception as e:
                msg = str(e)
                if needs_account_holder(msg):
                    entry.update(status='BLOCKED', detail=msg[:250])
                else:
                    entry.update(status='ERROR', detail=msg[:250])
        results.append(entry)
    return results


# The iOS/App Store Connect checks that cannot run without a per-brand Team Key.
APPLE_API_CHECKS = ['ASC authentication', 'Bundle ID registered', 'Bundle ID team',
                    'App ID capabilities', 'ASC app record', 'Certificates']
APPLE_MISSING_DETAIL = ('MISSING APPLE APP MANAGER API KEY - cannot query App Store '
                        'Connect; set up with: brandtool add-asc-key <brand>')


def _audit_apple(r, cfg, brand_dir, data, client):
    if client is None:
        # No quiet skip: every unqueryable iOS check is called out loudly.
        for name in APPLE_API_CHECKS:
            r.add(name, ISSUE, APPLE_MISSING_DETAIL, flash=True)
        _audit_apns_key(r, brand_dir, data)
        return
    bundle_id = data['iosBundleIdentifier']
    try:
        resource = apple_ops.find_bundle_id(client, bundle_id)
    except asc_api.AscError as e:
        msg = str(e)
        if needs_account_holder(msg):
            holder = data.get('appleAccountHolderName') or 'the client Account Holder'
            r.add('Apple account status', ISSUE,
                  f'ACCOUNT HOLDER action needed - Apple says: {msg[:250]} '
                  f'- contact {_val(holder)} (appleAccountHolderName/Email in transmute.json)',
                  flash=True)
        else:
            r.add('ASC authentication', ERROR, msg[:200])
        return
    except Exception as e:
        r.add('App Store Connect', ERROR, str(e)[:200])
        return
    r.add('ASC authentication', OK)

    if not resource:
        r.add('Bundle ID registered', ISSUE, f'{_val(bundle_id)} not registered',
              fix=lambda: apple_ops.register_bundle_id(client, bundle_id, data['appName']),
              console_url=apple_ops.IDENTIFIERS_URL)
    else:
        r.add('Bundle ID registered', OK)
        team = data.get('DEVELOPMENT_TEAM', '')
        seed = apple_ops.seed_id(resource)
        if not team:
            r.add('Bundle ID team', INFO,
                  f'DEVELOPMENT_TEAM empty in transmute.json; seedId is {_val(seed)}')
        elif apple_ops.seed_matches_team(resource, team):
            r.add('Bundle ID team', OK)
        else:
            r.add('Bundle ID team', ISSUE,
                  f'bundle id belongs to team {_val(seed)}, transmute says {_val(team)} '
                  f'- wrong account key?')
        try:
            missing_caps = apple_ops.missing_capabilities(
                client, resource, cfg.get('iosRequiredCapabilities', []))
            if missing_caps:
                def fix_caps(caps=tuple(missing_caps), res=resource):
                    apple_ops.enable_capabilities(client, res, caps)
                r.add('App ID capabilities', ISSUE,
                      'missing: ' + ', '.join(_val(c) for c in missing_caps),
                      fix=fix_caps, console_url=apple_ops.IDENTIFIERS_URL)
            else:
                r.add('App ID capabilities', OK)
        except Exception as e:
            r.add('App ID capabilities', ERROR, str(e)[:160])

    try:
        asc_app = apple_ops.find_app(client, bundle_id)
        if asc_app:
            r.add('ASC app record', OK)
            if not data.get('appStoreId') and asc_app.get('id'):
                def fix_store_from_asc(store_id=asc_app['id']):
                    current = cfgmod.load_transmute(brand_dir)
                    current['appStoreId'] = store_id
                    cfgmod.save_transmute(brand_dir, current)
                r.add('appStoreId recorded', ISSUE,
                      f'not in transmute.json; App Store Connect app record id is '
                      f'{_val(asc_app["id"])} (the numeric Apple app id)',
                      fix=fix_store_from_asc)
        else:
            r.add('ASC app record', ISSUE,
                  'no app record - create manually in App Store Connect (see INSTRUCTIONS_BRAND_SETUP.md)',
                  console_url=apple_ops.APPS_URL)
    except Exception as e:
        r.add('ASC app record', ERROR, str(e)[:160])

    _audit_apns_key(r, brand_dir, data)

    try:
        expiring = apple_ops.expiring_certificates(client, days=60)
        if expiring:
            desc = '; '.join(
                f'{_val(n)} ({t}) '
                + (_red(f'EXPIRED {d}') if dl < 0 else f'expires {_val(d)}')
                for n, t, d, dl in expiring)
            if any('DISTRIBUTION' in t for _, t, _, _ in expiring):
                r.add('Certificates expiring', ISSUE,
                      desc + ' - an expired DISTRIBUTION cert blocks releasing; '
                      'renew in Xcode (see addendum, or run: brandtool check-personal-ios-dev-certs)')
            else:
                r.add('Certificates expiring', INFO,
                      desc + ' - DEVELOPMENT certs only affect device debugging and '
                      'Xcode auto-renews them on the next device build; instructions: '
                      'brandtool check-personal-ios-dev-certs')
        else:
            r.add('Certificates', OK)
    except Exception as e:
        r.add('Certificates', ERROR, str(e)[:160])


def _audit_ios_app_metadata(r, firebase, project_id, brand_dir, data, ios_app):
    """Firebase iOS app metadata: Team ID (from DEVELOPMENT_TEAM) and App Store ID
    (from transmute.json's appStoreId; inferable back from Firebase or, in the Apple
    section, from the App Store Connect app record id)."""
    app_id = ios_app['appId']
    team = data.get('DEVELOPMENT_TEAM', '')
    live_team = ios_app.get('teamId', '')
    if not team:
        r.add('Firebase iOS Team ID', INFO,
              f'DEVELOPMENT_TEAM empty in transmute.json; live value: '
              f'"{_val(live_team or "(unset)")}"')
    elif live_team == team:
        r.add('Firebase iOS Team ID', OK, _val(team))
    else:
        r.add('Firebase iOS Team ID', ISSUE,
              f'live "{_val(live_team or "(unset)")}" should be "{_val(team)}" '
              '(from DEVELOPMENT_TEAM)',
              fix=lambda: fb.patch_ios_app(firebase, project_id, app_id, {'teamId': team}))

    tj_store = data.get('appStoreId', '')
    live_store = ios_app.get('appStoreId', '')
    if tj_store:
        if live_store == tj_store:
            r.add('Firebase iOS App Store ID', OK, _val(tj_store))
        else:
            r.add('Firebase iOS App Store ID', ISSUE,
                  f'live "{_val(live_store or "(unset)")}" should be "{_val(tj_store)}" '
                  '(from transmute.json)',
                  fix=lambda: fb.patch_ios_app(firebase, project_id, app_id,
                                               {'appStoreId': tj_store}))
    elif live_store:
        def fix_record_store():
            current = cfgmod.load_transmute(brand_dir)
            current['appStoreId'] = live_store
            cfgmod.save_transmute(brand_dir, current)
        r.add('Firebase iOS App Store ID', ISSUE,
              f'appStoreId not in transmute.json; Firebase has "{_val(live_store)}"',
              fix=fix_record_store)
    else:
        r.add('Firebase iOS App Store ID', ISSUE,
              'not set anywhere - set appStoreId in transmute.json (the numeric Apple '
              'app id; inferred automatically by --fix once the App Store Connect app '
              'record exists and ASC credentials are recorded)')


def customer_urls(brand_name, url_template, customer_id_pattern=r'\d+'):
    """Server admin URLs for a brand: the customer id(s) extracted from the
    brand dir name substituted into the configured url_template; a placeholder
    URL when no ids are present."""
    ids = re.findall(customer_id_pattern, brand_name)
    if not ids:
        return [url_template.replace('{customerId}', '<customerId>')]
    return [url_template.replace('{customerId}', i) for i in ids]


def _red(text):
    from .report import paint
    return paint(text, 'brightred')


def _val(text):
    """Light-yellow highlight for the variable part of a check detail."""
    from .report import paint
    return paint(text, 'value')


def server_copy_notice(server_copy, brand_dir, new_key,
                       customer_id_pattern=r'\d+', print_fn=print):
    """Red banner after a server-copied key changes: some server keeps its own
    copy of this key (per the purpose's server_copy config), and an admin must
    paste the new one into its settings page or server-side use breaks on the
    next key rotation."""
    from .report import paint
    brand = os.path.basename(os.path.normpath(brand_dir))
    note = server_copy.get('note', 'a server also uses this key')
    print_fn(_red('*' * 70))
    print_fn(_red(f'*** ACTION REQUIRED: {note} - it MUST be updated ***'))
    print_fn(_red('Log in to the server admin and paste the NEW key (shown below):'))
    for url in customer_urls(brand, server_copy['url_template'],
                             customer_id_pattern):
        print_fn(_red(f'  {url}  -> {server_copy["settings_path"]}'))
    print_fn(_red('Until updated, the server keeps using the OLD key - it still '
                  'works, so do NOT delete it.'))
    print_fn(_red('*' * 70))
    print_fn('NEW key (copy/paste): ' + paint(new_key, 'green'))


# Consistent option colors for the FCM key fix: MINT is the caution path
# (yellow, with its server-update ramification in red), PASTE is the safe path (green).
def _mint_txt(text):
    from .report import paint
    return paint(text, 'yellow')


def _paste_txt(text):
    from .report import paint
    return paint(text, 'green')


def _read_json_block(input_fn, print_fn):
    print_fn('Paste the service-account JSON now (input ends at the closing brace):')
    buf, depth, started = '', 0, False
    while True:
        line = input_fn('')
        buf += line + '\n'
        depth += line.count('{') - line.count('}')
        if '{' in line:
            started = True
        if started and depth <= 0:
            return buf


def fcm_key_interactive_fix(services, brand_dir, project_id, data, email,
                            input_fn=input, print_fn=print, server_copy=None,
                            customer_id_pattern=r'\d+'):
    """Resolve a missing FCM key file, interactively.

    [M]int a NEW key: when a server_copy is configured, the server keeps pushing
    with the OLD key until an admin uploads the new JSON at its settings page,
    so minting prints a red ACTION REQUIRED warning plus the JSON to copy/paste.
    [P]aste the EXISTING JSON fetched from that same server admin page: saved to
    the brand dir, nothing to upload.
    """
    brand = os.path.basename(os.path.normpath(brand_dir))
    print_fn(f'The key belongs to {email}.')
    from .report import paint
    if server_copy:
        print_fn('The server admin page holding the CURRENT key for this brand:')
        for url in customer_urls(brand, server_copy['url_template'],
                                 customer_id_pattern):
            print_fn('  ' + paint(url, 'cyan')
                     + f'  -> {server_copy["settings_path"]}')
    while True:
        choice = input_fn(_mint_txt('[M]int a NEW key') + ' '
                          + _red('(server admin must then be updated!)') + ' / '
                          + _paste_txt('[P]aste the EXISTING JSON from the server admin')
                          + ' / [C]ancel: ').strip().lower()
        if choice in ('c', 'cancel', 'q'):
            raise RuntimeError('cancelled - no key file created')

        if choice in ('m', 'mint'):
            filename = fb.ensure_fcm_admin(services['iam'], services.get('crm'),
                                           project_id, brand_dir, sa_email=email)
            current = cfgmod.load_transmute(brand_dir)
            current['messagingServiceAccountKeyFile'] = filename
            if not current.get('fcmServiceAccount'):
                current['fcmServiceAccount'] = email
            cfgmod.save_transmute(brand_dir, current)
            with open(os.path.join(brand_dir, filename)) as f:
                content = f.read()
            print_fn(_red('*' * 70))
            print_fn(_red('*** ACTION REQUIRED: a NEW key was minted - the push '
                          'server MUST be updated ***'))
            if server_copy:
                print_fn(_red('Paste the JSON below into the server admin page '
                              f'shown above ({server_copy["settings_path"]}). '
                              'Until then the server pushes with the OLD key '
                              '(which keeps working - do NOT revoke it).'))
            else:
                print_fn(_red('Paste the JSON below wherever your push server '
                              'stores its FCM service-account key. Until then it '
                              'pushes with the OLD key (which keeps working - do '
                              'NOT revoke it).'))
            print_fn(_red('*' * 70))
            print_fn(content)
            print_fn(f'(also saved to {os.path.join(brand_dir, filename)})')
            return

        if choice in ('p', 'paste'):
            raw = _read_json_block(input_fn, print_fn)
            try:
                parsed = json.loads(raw)
            except ValueError:
                # Depending on when the key was stored, the server admin page
                # serves it either plain or HTML-entity encoded (&quot; etc.) -
                # PHP handled it differently over time. Decode and retry.
                import html
                try:
                    parsed = json.loads(html.unescape(raw))
                    print_fn('  (HTML-entity-encoded paste detected - decoded '
                             '&quot; etc. automatically)')
                except ValueError:
                    print_fn('  Not valid JSON - try again.')
                    continue
            if parsed.get('type') != 'service_account':
                print_fn('  That JSON is not a service-account key ("type" is not '
                         '"service_account") - try again.')
                continue
            if parsed.get('project_id') != project_id:
                print_fn(f'  That key belongs to project "{parsed.get("project_id")}", '
                         f'not "{project_id}" - wrong brand? Try again or cancel.')
                continue
            client_email = parsed.get('client_email', '')
            if email and client_email != email:
                confirm = input_fn(f'  Key is for {client_email}, expected {email}. '
                                   + _paste_txt('Use it anyway? [y/N]') + ' ').strip().lower()
                if confirm != 'y':
                    continue
            filename = f"{project_id}-{parsed.get('private_key_id', 'key')[:12]}.json"
            with open(os.path.join(brand_dir, filename), 'w') as f:
                json.dump(parsed, f, indent=2)
            current = cfgmod.load_transmute(brand_dir)
            current['messagingServiceAccountKeyFile'] = filename
            if not current.get('fcmServiceAccount') and client_email:
                current['fcmServiceAccount'] = client_email
            cfgmod.save_transmute(brand_dir, current)
            print_fn(f'saved to {os.path.join(brand_dir, filename)} and recorded in '
                     'transmute.json - the server already has this key, nothing to upload.')
            return

        print_fn('  Enter M, P, or C.')


def _audit_fcm(r, services, brand_dir, data, project_id, server_copy=None,
               customer_id_pattern=r'\d+'):
    """FCM push service account: transmute.json's fcmServiceAccount is the recorded
    truth. Older brands used custom-named SAs (not the standard
    firebase-messaging-admin), so when unrecorded we infer: the key file's
    client_email first, else the IAM policy's FCM-Admin-role holders."""
    iam = services['iam']
    crm = services.get('crm')
    recorded = data.get('fcmServiceAccount', '')
    keyfile = data.get('messagingServiceAccountKeyFile', '')
    keyfile_path = os.path.join(brand_dir, keyfile) if keyfile else ''
    key_email = None
    if keyfile and os.path.exists(keyfile_path):
        try:
            with open(keyfile_path) as f:
                key_email = json.load(f).get('client_email')
        except Exception:
            pass

    effective = recorded
    if recorded:
        try:
            if fb.service_account_exists(iam, project_id, recorded):
                r.add('FCM admin service account', OK, _val(recorded))
            else:
                r.add('FCM admin service account', ISSUE,
                      f'{_val(recorded)} (recorded in transmute.json) not found in project')
        except Exception as e:
            r.add('FCM admin service account', ERROR, str(e)[:160])
        if key_email and key_email != recorded:
            r.add('FCM key file account', ISSUE,
                  f'{_val(keyfile)} belongs to {_val(key_email)}, not the recorded '
                  f'{_val(recorded)} - '
                  'correct fcmServiceAccount or replace the key file')
    else:
        candidate, source = None, ''
        if key_email:
            candidate, source = key_email, f'client_email of {keyfile}'
        else:
            admins = []
            if crm is not None:
                try:
                    admins = fb.fcm_admin_members(crm, project_id)
                except Exception:
                    admins = []
            default_email = f'{fb.FCM_ADMIN_ID}@{project_id}.iam.gserviceaccount.com'
            if not admins:
                try:
                    if fb.service_account_exists(iam, project_id, default_email):
                        admins = [default_email]
                except Exception:
                    pass
            if len(admins) == 1:
                candidate = admins[0]
                source = 'holds role Firebase Cloud Messaging API Admin'
            elif admins:
                r.add('FCM admin service account', ISSUE,
                      'fcmServiceAccount not in transmute.json and multiple accounts '
                      'hold the FCM Admin role: ' + ', '.join(admins) +
                      ' - record the right one in transmute.json')
        if candidate:
            def fix_record_sa(email=candidate):
                current = cfgmod.load_transmute(brand_dir)
                current['fcmServiceAccount'] = email
                cfgmod.save_transmute(brand_dir, current)
            r.add('FCM admin service account', ISSUE,
                  f'not recorded in transmute.json; found {_val(candidate)} ({source})',
                  fix=fix_record_sa)
            effective = candidate
        elif not any(c.name == 'FCM admin service account' for c in r.checks):
            r.add('FCM admin service account', ISSUE,
                  'no FCM messaging service account found (run create-keys to '
                  'provision the standard one)')

    if keyfile and os.path.exists(keyfile_path):
        r.add('FCM admin key file', OK, _val(keyfile))
    elif effective:
        def fix_key(email=effective):
            fcm_key_interactive_fix(services, brand_dir, project_id, data, email,
                                    server_copy=server_copy,
                                    customer_id_pattern=customer_id_pattern)
        detail = ('messagingServiceAccountKeyFile missing - interactive fix: '
                  + _mint_txt(f'mint a NEW key for {effective}') + ' '
                  + _red('(the push server admin must then be updated!)') + ' OR '
                  + _paste_txt('paste the EXISTING JSON from the server admin page'))
        console_url = None
        if server_copy:
            from .report import paint
            brand = os.path.basename(os.path.normpath(brand_dir))
            urls = customer_urls(brand, server_copy['url_template'],
                                 customer_id_pattern)
            admin_urls = ', '.join(paint(u, 'cyan') for u in urls)
            detail += f' ({admin_urls} -> {server_copy["settings_path"]})'
            console_url = urls[0]
        r.add('FCM admin key file', ISSUE, detail,
              fix=fix_key, console_url=console_url)
    else:
        r.add('FCM admin key file', ISSUE,
              'messagingServiceAccountKeyFile missing (run create-keys)')


def _audit_project_name(r, services, brand_dir, data, project_id):
    """firebaseProjectName = the cased console display name. The lowercase variant is
    firebaseProjectId - never store the same value twice differing only in case (the
    legacy CloudAndFirebaseProjectName field did exactly that and was removed)."""
    crm = services.get('crm')
    if crm is None:
        return
    try:
        live_name = crm.projects().get(
            name=f'projects/{project_id}').execute().get('displayName', '')
        tj_name = data.get('firebaseProjectName', '')
        tj_name_valid = bool(tj_name) and not cfgmod.PLACEHOLDER_RE.search(tj_name)
        if not tj_name_valid and live_name:
            def fix_record_name():
                current = cfgmod.load_transmute(brand_dir)
                current['firebaseProjectName'] = live_name
                cfgmod.save_transmute(brand_dir, current)
            r.add('firebaseProjectName recorded', ISSUE,
                  f'not in transmute.json; console display name is "{_val(live_name)}"',
                  fix=fix_record_name)
        elif tj_name_valid and live_name and tj_name != live_name:
            r.add('firebaseProjectName recorded', INFO,
                  f'transmute.json says "{_val(tj_name)}"; console display name is '
                  f'"{_val(live_name)}" (display names are cosmetic - update if desired)')
        elif tj_name_valid:
            r.add('firebaseProjectName recorded', OK, _val(tj_name))
    except Exception as e:
        r.add('firebaseProjectName recorded', ERROR, str(e)[:160])


def _apns_key_ids_in(directory, exclude_basename=None):
    """Key ids of AuthKey_*.p8 files in a directory (minus an excluded filename)."""
    return sorted(os.path.basename(p)[len('AuthKey_'):-len('.p8')]
                  for p in glob.glob(os.path.join(directory, 'AuthKey_*.p8'))
                  if os.path.basename(p) != exclude_basename)


def _unclaimed_apns_keys(apns_root, brands_root):
    """Key ids in the APNs backup dir that no brand dir holds a copy of."""
    if not os.path.isdir(apns_root):
        return []
    claimed = {os.path.basename(p)
               for p in glob.glob(os.path.join(brands_root, '*', 'AuthKey_*.p8'))}
    return sorted(os.path.basename(p)[len('AuthKey_'):-len('.p8')]
                  for p in glob.glob(os.path.join(apns_root, 'AuthKey_*.p8'))
                  if os.path.basename(p) not in claimed)


def cloud_messaging_ios_url(project_id, bundle_id=None):
    """Firebase console Cloud Messaging page; deep-links to the iOS app's card
    (where the uploaded APNs auth key id is shown) when the bundle id is known."""
    if not project_id:
        return 'Firebase console -> Project settings -> Cloud Messaging'
    url = f'https://console.firebase.google.com/project/{project_id}/settings/cloudmessaging'
    if bundle_id:
        url += f'/ios:{bundle_id}'
    return url


APNS_KEY_ID_RE = re.compile(r'^[A-Z0-9]{10}$')


def _ask_apns_key_id(url, candidates=(), input_fn=None):
    """Prompt for the APNs key id the Firebase Cloud Messaging page shows."""
    from .report import paint
    ask = input_fn or input
    print('    Check the APNs auth key id on the Firebase Cloud Messaging page '
          'for this iOS app:')
    print('    ' + paint(url, 'cyan'))
    if candidates:
        print('    Local candidate key id(s): '
              + ', '.join(paint(k, 'green') for k in candidates))
    while True:
        try:
            kid = ask('    APNs Key ID shown there (10 chars, or [C]ancel): ').strip().upper()
        except (EOFError, OSError, KeyboardInterrupt):
            raise RuntimeError('no interactive input - APNs key unchanged')
        if kid in ('C', 'CANCEL', 'Q', 'QUIT'):
            raise RuntimeError('cancelled - APNs key unchanged')
        if APNS_KEY_ID_RE.match(kid):
            return kid
        print(f'    "{kid}" does not look like an APNs key id (exactly 10 letters/digits).')


def _claim_apns_key(brand_dir, apns_root, kid):
    """Record apnsKeyId and pull the backup .p8 into the brand dir when available."""
    current = cfgmod.load_transmute(brand_dir)
    current['apnsKeyId'] = kid
    cfgmod.save_transmute(brand_dir, current)
    fname = f'AuthKey_{kid}.p8'
    src, dest = os.path.join(apns_root, fname), os.path.join(brand_dir, fname)
    if os.path.exists(dest):
        print(f'    recorded apnsKeyId={kid}; {fname} already in the brand dir.')
    elif os.path.exists(src):
        shutil.copyfile(src, dest)
        print(f'    recorded apnsKeyId={kid} and claimed {fname} from {cfgmod.APNS_BACKUP_DIR}/ '
              'into the brand dir.')
    else:
        print(f'    recorded apnsKeyId={kid}, but {fname} is nowhere local - locate '
              'the .p8 and copy it into the brand dir (APNs keys cannot be '
              're-downloaded from Apple).')


def _audit_apns_key(r, brand_dir, data):
    """APNs bookkeeping: transmute.json's apnsKeyId names the key uploaded in Firebase
    Cloud Messaging (no API can read that config - a human verifies it once).
    Local-only, so it runs even when ASC credentials are missing."""
    _audit_apns_key_files(r, brand_dir, data)
    fcm_url = cloud_messaging_ios_url(
        r.project_id if r.project_id != '?' else '', data.get('iosBundleIdentifier'))
    from .report import paint
    # Firebase has NO API to read or upload the FCM APNs key, so a human uploads
    # it once and confirms; the confirmation is recorded per Firebase iOS APP ID
    # in transmute.json - re-creating the iOS app (new bundle id) re-flags it.
    live_ios = getattr(r, 'ios_app_id', None)
    confirmed = data.get('apnsUploadedForIosAppId', '')
    if not live_ios:
        r.add('APNs key in Firebase', INFO,
              'verify the APNs auth key is uploaded for the iOS app: '
              + paint(fcm_url, 'cyan'))
        return
    if confirmed == live_ios:
        r.add('APNs key in Firebase', OK,
              f'upload confirmed for iOS app {_val(live_ios)} '
              '(apnsUploadedForIosAppId in transmute.json)')
        return

    def fix_confirm_apns():
        kid = data.get('apnsKeyId', '')
        key_txt = _val(f'AuthKey_{kid}.p8') if kid else 'the APNs auth key .p8'
        team = data.get('DEVELOPMENT_TEAM', '')
        print('    Firebase offers NO API for this - upload the key by hand, then '
              'confirm here.')
        print(f'    1. Open {paint(fcm_url, "cyan")}')
        print(f'    2. Under the iOS app, in "APNs Authentication Key", upload '
              f'{key_txt} from the brand dir')
        print('       The dialog also asks you to paste these by themselves:')
        print(f'         Key ID:  {_val(kid or "(apnsKeyId not recorded - see the "
                                               "key filename)")}')
        print(f'         Team ID: {_val(team or "(DEVELOPMENT_TEAM not recorded)")}')
        print('       (ONE auth key covers BOTH Development and Production - the '
              'separate dev/prod slots are only for legacy APNs certificates)')
        try:
            ans = input('    Is the APNs auth key uploaded for this app now? [y/N] '
                        ).strip().lower()
        except (EOFError, OSError):
            raise RuntimeError('no interactive input - not confirmed')
        if ans != 'y':
            raise RuntimeError('not confirmed - upload the key and re-run')
        current = cfgmod.load_transmute(brand_dir)
        current['apnsUploadedForIosAppId'] = live_ios
        cfgmod.save_transmute(brand_dir, current)
        print(f'    recorded apnsUploadedForIosAppId={live_ios} in transmute.json.')

    stale_note = (f' (was confirmed for previous iOS app {_val(confirmed)} - the app '
                  'was re-created, so Firebase lost the upload)') if confirmed else ''
    r.add('APNs key in Firebase', ISSUE,
          f'NOT confirmed for the current iOS app {_val(live_ios)}{stale_note} - '
          'pushes will not reach this app until the APNs auth key is uploaded in '
          'Firebase Cloud Messaging (no API exists; [F]ix shows the steps and '
          'records your confirmation)', fix=fix_confirm_apns, console_url=fcm_url,
          flash=True)


def _audit_apns_key_files(r, brand_dir, data):
    brands_root = os.path.dirname(os.path.normpath(brand_dir))
    apns_root = os.path.join(os.path.dirname(brands_root), cfgmod.APNS_BACKUP_DIR)
    dir_keys = _apns_key_ids_in(brand_dir, exclude_basename=data.get('ascApiKeyFile'))
    apns_key_id = data.get('apnsKeyId', '')
    cm_url = cloud_messaging_ios_url(
        getattr(r, 'project_id', '') if getattr(r, 'project_id', '') != '?' else '',
        data.get('iosBundleIdentifier'))

    if apns_key_id:
        fname = f'AuthKey_{apns_key_id}.p8'
        in_dir = apns_key_id in dir_keys
        in_backup = os.path.exists(os.path.join(apns_root, fname))
        if in_dir and in_backup:
            r.add('APNs key file', OK,
                  f'{_val(fname)} present (backup in {cfgmod.APNS_BACKUP_DIR}/)')
        elif in_dir:
            r.add('APNs key file', ISSUE,
                  f'{_val(fname)} present but no backup copy in {cfgmod.APNS_BACKUP_DIR}/',
                  fix=lambda: shutil.copyfile(os.path.join(brand_dir, fname),
                                              os.path.join(apns_root, fname)))
        elif in_backup:
            r.add('APNs key file', ISSUE,
                  f'{_val(fname)} missing from brand dir (backup exists in {cfgmod.APNS_BACKUP_DIR}/)',
                  fix=lambda: shutil.copyfile(os.path.join(apns_root, fname),
                                              os.path.join(brand_dir, fname)))
        else:
            r.add('APNs key file', ISSUE,
                  f'{_val(fname)} not found in brand dir or {cfgmod.APNS_BACKUP_DIR}/ - APNs keys cannot '
                  'be re-downloaded; locate the file, or generate a new key, upload it in '
                  'Firebase Cloud Messaging, and update apnsKeyId',
                  console_url=cm_url)
        extras = [k for k in dir_keys if k != apns_key_id]
        if extras:
            r.add('APNs extra key files', INFO,
                  'brand dir also contains: '
                  + ', '.join(_val(f'AuthKey_{k}.p8') for k in extras))
        return

    if len(dir_keys) == 1:
        def fix_record(kid=dir_keys[0]):
            current = cfgmod.load_transmute(brand_dir)
            current['apnsKeyId'] = kid
            cfgmod.save_transmute(brand_dir, current)
        r.add('APNs key file', ISSUE,
              f'apnsKeyId not recorded in transmute.json (brand dir has '
              f'{_val(f"AuthKey_{dir_keys[0]}.p8")}; confirm it matches Firebase Cloud Messaging '
              'before recording)', fix=fix_record, console_url=cm_url)
    elif dir_keys:
        def fix_pick():
            _claim_apns_key(brand_dir, apns_root, _ask_apns_key_id(cm_url, dir_keys))
        r.add('APNs key file', ISSUE,
              'multiple APNs keys in brand dir ('
              + ', '.join(_val(k) for k in dir_keys) + ') - [F]ix '
              'asks which key id the Firebase Cloud Messaging page shows and records it',
              fix=fix_pick, console_url=cm_url)
    else:
        unclaimed = _unclaimed_apns_keys(apns_root, brands_root)
        hint = (f'; possibly one of the unclaimed keys in {cfgmod.APNS_BACKUP_DIR}/: '
                + ', '.join(_val(k) for k in unclaimed)) if unclaimed else ''

        def fix_claim():
            _claim_apns_key(brand_dir, apns_root, _ask_apns_key_id(cm_url, unclaimed))
        r.add('APNs key file', ISSUE,
              'no APNs AuthKey_*.p8 in brand dir - [F]ix asks for the key id shown on '
              'the Firebase Cloud Messaging page and claims the matching backup from '
              f'{cfgmod.APNS_BACKUP_DIR}/' + hint, fix=fix_claim, console_url=cm_url)


def _audit_key(r, apikeys, project_id, brand_dir, data, purpose, cfg,
               missing_fn, body_fn, describe_fn=None, input_fn=None):
    from .report import paint
    field = purpose['field']
    label = purpose.get('label', field)
    tokens = purpose.get('match_tokens', [])
    id_pattern = cfg.get('customerIdPattern', r'\d+')
    display_name = keys_ops.key_display_name(purpose, data, brand_dir, id_pattern)
    wanted = data.get(field, '')
    snippet = wanted[:12] + '...' + wanted[-4:] if len(wanted) > 20 else wanted
    # color everything that varies run-to-run / brand-to-brand
    proj = paint(project_id, 'cyan')
    snip = paint(snippet, 'yellow')
    disp = paint(f'"{display_name}"', 'green')
    server_copy = purpose.get('server_copy')
    server_note = ''
    if server_copy:
        urls = ', '.join(paint(u, 'cyan') for u in customer_urls(
            os.path.basename(os.path.normpath(brand_dir)),
            server_copy['url_template'], id_pattern))
        server_note = (f'. NOTE: {server_copy.get("note", "a server holds its own "
                       "copy of this key")} - after any change an admin must paste '
                       f'the new key at {urls} -> {server_copy["settings_path"]}')

    def fix_provision():
        # Offer any existing keys that look like they serve this purpose (matched
        # by display-name tokens); the user decides reuse-vs-new. Either way the
        # key ends up with the correct app restriction AND API target(s).
        body = body_fn()
        candidates = keys_ops.find_keys_by_tokens(apikeys, project_id, tokens)
        chosen = None
        if candidates:
            tokens_txt = '"+"'.join(tokens)
            print(f'    Existing key(s) in {project_id} whose display name matches '
                  f'this purpose (contains "{tokens_txt}"):')
            for i, k in enumerate(candidates, 1):
                line = f'      [{i}] ' + paint(k.get('displayName') or '(unnamed)', 'green')
                dropped = keys_ops.restriction_removals(k, body)
                if dropped:
                    line += (' ' + _red('- reusing REMOVES: ')
                             + _red('; ').join(paint(e, 'pink') for e in dropped))
                print(line)
            print("    REUSE overwrites that key's restrictions with the correct "
                  'app restriction + API target(s).')
            ask = input_fn or input   # resolved at fix time so tests can stub input
            try:
                ans = ask(f'    [1-{len(candidates)}] to REUSE (Enter = 1), '
                          '[N]ew key anyway, or [A]bort: ').strip().lower()
            except (EOFError, OSError):
                ans = '1'    # non-interactive (--yes / piped): reuse the first match
            except KeyboardInterrupt:
                raise RuntimeError('aborted - key unchanged')
            if ans in ('a', 'abort', 'c', 'cancel', 'q'):
                raise RuntimeError('aborted - key unchanged')
            if ans not in ('n', 'new'):
                ans = ans or '1'
                if not (ans.isdigit() and 1 <= int(ans) <= len(candidates)):
                    raise RuntimeError(f'answer "{ans}" not understood - key unchanged')
                chosen = candidates[int(ans) - 1]
        if chosen is not None:
            new_string = keys_ops.adopt_key(apikeys, chosen, body)
            did = ('reused existing key '
                   + paint(f'"{chosen.get("displayName") or "(unnamed)"}"', 'green')
                   + ' (restrictions corrected)')
        else:
            new_string = keys_ops.create_key(apikeys, project_id, display_name, body)
            did = f'created new key {disp}'
        current = cfgmod.load_transmute(brand_dir)
        current[field] = new_string
        cfgmod.save_transmute(brand_dir, current)
        print(f'    {did} in {proj}; recorded in {field}.')
        if wanted:
            print(f'    The old key ({snip}) still works in whatever project it '
                  'lives in, so already-shipped')
            print('    builds are unaffected; the NEW key takes effect on the next '
                  'build from this brand dir.')
        if server_copy:
            server_copy_notice(server_copy, brand_dir, new_string, id_pattern)

    if not wanted:
        r.add(label, ISSUE,
              f'{field} empty in transmute.json - [F]ix lists any reusable key in '
              f'{proj} for you to choose from, or creates {disp} (correct '
              f'restrictions either way), then records it in transmute.json'
              + server_note,
              fix=fix_provision, console_url=cloud_credentials_url(project_id))
        return
    key = keys_ops.find_key_by_string(apikeys, project_id, wanted)
    if not key:
        r.add(label, ISSUE,
              f'{field} in transmute.json ({snip}) is not among the API keys of '
              f'Google Cloud project {proj} - it was created in a different (legacy?) '
              f'project or later deleted. [F]ix lists any reusable key in {proj} for '
              f'you to choose from, or creates {disp} (correct restrictions '
              f'either way), then records it in transmute.json' + server_note,
              fix=fix_provision, console_url=cloud_credentials_url(project_id))
        return
    problems = []
    lacking = missing_fn(key)
    if lacking:
        problems.append(describe_fn(lacking) if describe_fn
                        else 'not allowed: ' + ', '.join(str(x) for x in lacking))
    have_targets = keys_ops.api_targets(key)
    missing_targets = [s for s in purpose.get('services', [])
                       if s not in have_targets]
    if missing_targets:
        current = (', '.join(paint(s, 'yellow') for s in sorted(have_targets))
                   if have_targets else paint('ALL APIs (no API restriction)', 'yellow'))
        problems.append(
            'API restriction currently allows ' + current + ' but is missing '
            + ', '.join(paint(s, 'brightred') for s in missing_targets))
    key_name = paint(f'"{key.get("displayName") or "(unnamed)"}"', 'green')
    if problems:
        removed = keys_ops.restriction_removals(key, body_fn())
        warn = ''
        if removed:
            # pink entries inside the red warning (each paint resets, so the red
            # is applied per segment rather than around the whole warning)
            entries = _red('; ').join(paint(e, 'pink') for e in removed)
            warn = ' ' + _red('WARNING: the fix REPLACES the restrictions wholesale - '
                              'currently allowed but NOT kept (existing builds/servers '
                              'using these LOSE access): ') + entries
        r.add(f'{label} restriction', ISSUE,
              f'key {key_name}: ' + '; '.join(problems) + warn,
              fix=lambda k=key: keys_ops.update_restrictions(apikeys, k, body_fn()),
              console_url=cloud_credentials_url(project_id))
    else:
        r.add(f'{label} restriction', OK)
