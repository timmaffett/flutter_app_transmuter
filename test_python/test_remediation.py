import os

from brandtool_lib import remediation
from brandtool_lib.report import BrandReport, ERROR, ISSUE, OK


def test_empty_when_no_issues():
    r = BrandReport('b')
    r.add('billing linked', OK)
    assert remediation.render_addendum([r]) == ''


def test_default_tool_cmd_is_platform_wrapper():
    tool = remediation.default_tool_cmd()
    if os.name == 'nt':
        assert tool == r'bin\brandtool'
    else:
        assert tool == './bin/brandtool.sh'


def test_commands_and_manual_advice():
    r = BrandReport('demo', 'proj-1')
    r.add('required APIs', ISSUE, 'disabled: x')
    r.add('Play Store app', ISSUE, 'missing')
    r.add('FCM admin key file', ISSUE, 'missing')
    r.add('ASC app record', ISSUE, 'no app record')
    text = remediation.render_addendum([r])
    tool = remediation.default_tool_cmd()
    brand = os.path.join('branded_loyalty', 'demo')
    assert 'ADDENDUM' in text
    assert f'{tool} audit {brand} --fix' in text
    assert 'apis/library?project=proj-1' in text
    assert 'play.google.com/console' in text
    assert f'{tool} create-keys {brand}' in text
    assert 'appstoreconnect.apple.com/apps' in text
    assert 'python bin/brandtool.py' not in text  # wrappers, not raw python
    assert '\x1b[' not in text  # plain without color


def test_console_urls_addendum(tmp_path):
    import json
    d = tmp_path / 'demo'
    d.mkdir()
    (d / 'transmute.json').write_text(json.dumps({
        'DEVELOPMENT_TEAM': 'TEAM123456', 'AppleDeveloperAccountName': 'Demo Inc.'}))
    r = BrandReport('demo', 'proj-1', 'com.demo')
    r.add('billing linked', OK)
    text = remediation.render_console_urls([r], brands_root=str(tmp_path))
    assert 'USEFUL CONSOLE LINKS' in text
    assert 'https://console.cloud.google.com/apis/api/places.googleapis.com/metrics?project=proj-1' in text
    assert 'https://console.cloud.google.com/apis/api/maps-android-backend.googleapis.com/metrics?project=proj-1' in text
    assert 'https://console.cloud.google.com/apis/dashboard?project=proj-1' in text
    assert 'https://console.cloud.google.com/apis/credentials?project=proj-1' in text
    assert 'https://console.firebase.google.com/project/proj-1/overview' in text
    # Apple links + which-account note
    assert 'https://appstoreconnect.apple.com/apps' in text
    assert 'https://developer.apple.com/account/resources/identifiers/list' in text
    assert 'https://developer.apple.com/account/resources/authkeys/list' in text
    assert 'Demo Inc.' in text and 'TEAM123456' in text
    # colored header uses cyan
    colored = remediation.render_console_urls([r], color=True, brands_root=str(tmp_path))
    assert '\x1b[36mUSEFUL CONSOLE LINKS' in colored


def test_addenda_are_boxed():
    r = BrandReport('demo', 'proj-1', 'com.demo')
    r.add('required APIs', ISSUE, 'disabled: x')
    fix_text = remediation.render_addendum([r])
    assert fix_text.split('\n')[1].startswith('++==')  # after leading blank line
    assert '|| ' in fix_text
    links = remediation.render_console_urls([r])
    assert links.split('\n')[1].startswith('++==')
    assert '|| ' in links


def test_console_urls_skips_unknown_project():
    r = BrandReport('demo')  # project_id stays '?'
    assert remediation.render_console_urls([r]) == ''


def test_missing_apple_key_detail_routes_to_add_asc_key():
    r = BrandReport('demo', 'proj-1')
    r.add('Bundle ID registered', ISSUE,
          'MISSING APPLE APP MANAGER API KEY - cannot query App Store Connect')
    text = remediation.render_addendum([r], tool_cmd='brandtool')
    brand = os.path.join('branded_loyalty', 'demo')
    assert f'brandtool add-asc-key {brand}' in text
    assert 'create-apple' not in text  # normal advice suppressed for missing-creds case


def test_asc_access_request_email_content():
    data = {'appName': 'Demo Rewards', 'AppleDeveloperAccountName': 'Demo Inc.',
            'DEVELOPMENT_TEAM': 'TEAM123456',
            'appleAccountHolderName': 'Pat Smith',
            'appleAccountHolderEmail': 'pat@demo.example'}
    email = remediation.asc_access_request_email(data)
    for expected in ('Pat Smith', 'pat@demo.example', 'Demo Rewards', 'Demo Inc.',
                     'TEAM123456', 'ACCOUNT HOLDER', 'Request Access',
                     'appstoreconnect.apple.com',
                     'developer.apple.com/help/app-store-connect'):
        assert expected in email, expected
    assert email.encode('ascii')


def test_asc_access_request_email_placeholders_when_holder_unknown():
    email = remediation.asc_access_request_email({'appName': 'Demo'})
    assert '[ACCOUNT HOLDER NAME]' in email and '[ACCOUNT HOLDER EMAIL]' in email


def test_tool_cmd_override():
    r = BrandReport('demo', 'proj-1')
    r.add('cert fingerprints', ISSUE, 'missing SHA_256')
    text = remediation.render_addendum([r], tool_cmd='brandtool')
    assert f"brandtool audit {os.path.join('branded_loyalty', 'demo')} --fix" in text


def test_run_commands_colored_cornflower_blue():
    r = BrandReport('demo', 'proj-1')
    r.add('cert fingerprints', ISSUE, 'missing')
    text = remediation.render_addendum([r], color=True, tool_cmd='brandtool')
    assert '\x1b[38;5;111mbrandtool audit' in text


def test_unknown_check_fallback_and_orange_header():
    r = BrandReport('demo')
    r.add('mystery check', ERROR, 'boom', console_url='https://x')
    text = remediation.render_addendum([r], color=True)
    assert '\x1b[38;5;208mADDENDUM' in text
    assert 'inspect: https://x' in text
