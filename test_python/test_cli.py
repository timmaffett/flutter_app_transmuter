import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    'brandtool_cli', os.path.join(os.path.dirname(__file__), '..', 'lib',
                     'python', 'brandtool', 'brandtool.py'))
brandtool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brandtool)


def test_propose_project_id_uses_valid_transmute_value():
    assert brandtool.propose_project_id('x/my_brand', {'firebaseProjectId': 'good-id'}) == 'good-id'


def test_propose_project_id_ignores_placeholder_and_sanitizes_dirname():
    pid = brandtool.propose_project_id(
        'branded_loyalty/Extra_Car_185', {'firebaseProjectId': 'PLACE_PROJECT_ID_HERE'})
    assert pid == 'extra-car-185'


def test_propose_project_id_prefixes_leading_digit():
    assert brandtool.propose_project_id('x/440_parkngo', {}).startswith('brand-')


def make_gate_brand(tmp_path, holder_name='Pat', holder_email='pat@x.example'):
    import json
    root = tmp_path / 'branded_loyalty'
    root.mkdir(exist_ok=True)
    d = root / 'demo'
    d.mkdir()
    data = {'appName': 'Demo', 'packageName': 'com.d', 'iosBundleIdentifier': 'com.d.ios'}
    if holder_name is not None:
        data['appleAccountHolderName'] = holder_name
    if holder_email is not None:
        data['appleAccountHolderEmail'] = holder_email
    (d / 'transmute.json').write_text(json.dumps(data))
    return d


def test_gate_request_email_sentinel_writes_email_file(tmp_path):
    d = make_gate_brand(tmp_path)
    # Enter twice keeps the stored defaults, then bail out of the gate.
    answers = iter(['GIVE_ME_REQUEST_EMAIL', '', '', 'INEEDTOSETUPAPPLE'])
    brandtool.gate_apple_credentials([str(d)], use_color=False, interactive=True,
                                     input_fn=lambda _: next(answers))
    email_file = d / 'apple_api_access_request_email.txt'
    assert email_file.exists()
    assert 'pat@x.example' in email_file.read_text()


def test_request_email_always_prompts_and_allows_correction(tmp_path):
    import json
    # The bug scenario: email address stored in BOTH fields. Email prompt comes
    # first (keep it), then the name - a stored name containing '@' cannot be
    # kept with Enter, forcing the correction.
    d = make_gate_brand(tmp_path, holder_name='pat@x.example', holder_email='pat@x.example')
    answers = iter(['', '', 'Pat Smith'])  # keep email; Enter on name rejected; corrected
    brandtool.handle_request_email(str(d), input_fn=lambda _: next(answers))
    data = json.loads((d / 'transmute.json').read_text())
    assert data['appleAccountHolderName'] == 'Pat Smith'
    assert data['appleAccountHolderEmail'] == 'pat@x.example'
    assert 'Pat Smith' in (d / 'apple_api_access_request_email.txt').read_text()


def test_request_email_rejects_email_without_at_sign(tmp_path):
    import json
    d = make_gate_brand(tmp_path, holder_name=None, holder_email=None)
    # email asked FIRST: bad email rejected, good accepted; then the name
    answers = iter(['not-an-email', 'pat@x.example', 'Pat Smith'])
    brandtool.handle_request_email(str(d), input_fn=lambda _: next(answers))
    data = json.loads((d / 'transmute.json').read_text())
    assert data['appleAccountHolderEmail'] == 'pat@x.example'
    assert data['appleAccountHolderName'] == 'Pat Smith'


def test_request_email_name_rejects_at_sign(tmp_path):
    import json
    d = make_gate_brand(tmp_path, holder_name=None, holder_email=None)
    answers = iter(['pat@x.example', 'also@x.example', 'Pat Smith'])
    brandtool.handle_request_email(str(d), input_fn=lambda _: next(answers))
    data = json.loads((d / 'transmute.json').read_text())
    assert data['appleAccountHolderName'] == 'Pat Smith'


def test_request_email_dash_clears_to_placeholder(tmp_path):
    import json
    d = make_gate_brand(tmp_path)
    answers = iter(['-', '-'])
    brandtool.handle_request_email(str(d), input_fn=lambda _: next(answers))
    data = json.loads((d / 'transmute.json').read_text())
    assert data['appleAccountHolderName'] == '' and data['appleAccountHolderEmail'] == ''
    assert '[ACCOUNT HOLDER NAME]' in (d / 'apple_api_access_request_email.txt').read_text()


def test_find_downloaded_p8_enter_rechecks_downloads(tmp_path):
    dl = tmp_path / 'Downloads'
    dl.mkdir()
    target = dl / 'AuthKey_ZZ99887766.p8'

    def answer(_prompt):
        target.write_text('k')  # the download completes while the prompt waits
        return ''               # user just presses Enter

    found = brandtool.find_downloaded_p8('ZZ99887766', downloads_dir=str(dl),
                                         input_fn=answer)
    assert found == str(target)


def test_find_downloaded_p8_directory_input_resolves_key_inside(tmp_path):
    dl = tmp_path / 'Downloads'
    dl.mkdir()
    (dl / 'AuthKey_UDD3YL9FB2.p8').write_text('k')
    other_dir = tmp_path / 'elsewhere'
    other_dir.mkdir()
    # user answers with the DIRECTORY (the exact bug): resolve the file inside it
    answers = iter([str(dl)])
    found = brandtool.find_downloaded_p8('UDD3YL9FB2', downloads_dir=str(other_dir),
                                         input_fn=lambda _: next(answers))
    assert found == str(dl / 'AuthKey_UDD3YL9FB2.p8')
    # a directory NOT containing the key re-prompts instead of returning the dir
    answers = iter([str(other_dir), str(dl)])
    found = brandtool.find_downloaded_p8('UDD3YL9FB2', downloads_dir=str(other_dir),
                                         input_fn=lambda _: next(answers))
    assert found.endswith('AuthKey_UDD3YL9FB2.p8')


def test_find_downloaded_p8_reject_forces_reprompt(tmp_path):
    dl = tmp_path / 'Downloads'
    dl.mkdir()
    bad = dl / 'AuthKey_UDD3YL9FB2.p8'
    bad.write_text('not-a-key')
    good = tmp_path / 'good.p8'
    good.write_text('k')
    answers = iter([str(good)])
    found = brandtool.find_downloaded_p8('UDD3YL9FB2', downloads_dir=str(dl),
                                         input_fn=lambda _: next(answers),
                                         reject=str(bad))
    assert found == str(good)


def test_usage_guide_covers_all_commands_and_process():
    from brandtool_lib import report
    try:
        report.set_color(False)
        guide = brandtool.usage_guide()
    finally:
        report.set_color(None)
    for cmd in ('audit', 'audit-unique', 'create-project', 'create-apps',
                'create-keys', 'create', 'create-apple', 'add-asc-key'):
        assert cmd in guide, cmd
    for expected in ('TYPICAL PROCESS', 'transmute.json', 'AUDIT CLEAN',
                     'INEEDTOSETUPAPPLE' if False else 'GIVE_ME_REQUEST_EMAIL',
                     'firebaseProjectId', 'transmute_provisioning.yaml'):
        assert expected in guide, expected
    assert '\x1b[' not in guide  # plain when color disabled
    try:
        report.set_color(True)
        assert '\x1b[36m' in brandtool.usage_guide()  # cyan headers when colored
    finally:
        report.set_color(None)


def test_missing_brand_dir_gives_clear_error_and_suggestion(capsys):
    import pytest
    with pytest.raises(SystemExit):
        brandtool.ensure_brand_dirs_exist(
            ['branded_loyalty/mke_smartpark_1495OK'],
            known_brands=['mke_smartpark_1495', 'ftmyers_2195'], interactive=False)
    out = capsys.readouterr().out
    assert 'BRAND DIRECTORY NOT FOUND' in out
    assert 'branded_loyalty/mke_smartpark_1495OK' in out
    assert 'did you mean' in out and 'mke_smartpark_1495' in out


def test_dir_without_transmute_is_flagged(tmp_path, capsys):
    import pytest
    d = tmp_path / 'not_a_brand'
    d.mkdir()
    with pytest.raises(SystemExit):
        brandtool.ensure_brand_dirs_exist([str(d)], known_brands=['mke_smartpark_1495'],
                                          interactive=False)
    out = capsys.readouterr().out
    assert 'no transmute.json' in out


def test_valid_brand_dirs_pass_silently(tmp_path):
    d = tmp_path / 'brand'
    d.mkdir()
    (d / 'transmute.json').write_text('{}')
    resolved = brandtool.ensure_brand_dirs_exist([str(d)], known_brands=[])
    assert resolved == [str(d)]


def _brands_root(tmp_path, monkeypatch, names):
    root = tmp_path / 'branded_loyalty'
    for name in names:
        d = root / name
        d.mkdir(parents=True)
        (d / 'transmute.json').write_text('{}')
    monkeypatch.setattr(brandtool.cfgmod, 'BRANDS_ROOT', str(root))
    return root


def test_bad_brand_dir_interactive_pick_by_number(tmp_path, monkeypatch):
    root = _brands_root(tmp_path, monkeypatch, ['good_brand'])
    answers = iter(['1'])
    resolved = brandtool.ensure_brand_dirs_exist(
        [str(root / 'good_brandOK')], known_brands=['good_brand'],
        interactive=True, input_fn=lambda _: next(answers))
    assert resolved == [os.path.join(str(root), 'good_brand')]


def test_bad_brand_dir_interactive_typed_name(tmp_path, monkeypatch):
    root = _brands_root(tmp_path, monkeypatch, ['good_brand', 'other_brand'])
    answers = iter(['other_brand'])  # bare name, no branded_loyalty/ prefix
    resolved = brandtool.ensure_brand_dirs_exist(
        [str(root / 'nope')], known_brands=['good_brand', 'other_brand'],
        interactive=True, input_fn=lambda _: next(answers))
    assert resolved == [os.path.join(str(root), 'other_brand')]


def test_bad_brand_dir_interactive_exit(tmp_path, monkeypatch, capsys):
    import pytest
    root = _brands_root(tmp_path, monkeypatch, ['good_brand'])
    answers = iter(['e'])
    with pytest.raises(SystemExit):
        brandtool.ensure_brand_dirs_exist(
            [str(root / 'nope')], known_brands=['good_brand'],
            interactive=True, input_fn=lambda _: next(answers))


def test_asc_key_id_and_issuer_validation():
    assert brandtool.KEY_ID_RE.match('ABC123XYZ0')
    assert not brandtool.KEY_ID_RE.match('short')
    assert brandtool.ISSUER_RE.match('69a6de70-1234-4abc-9def-001122334455')
    assert not brandtool.ISSUER_RE.match('not-a-uuid')


def test_find_downloaded_p8_prefers_downloads_then_prompts(tmp_path):
    dl = tmp_path / 'Downloads'
    dl.mkdir()
    (dl / 'AuthKey_ABC123XYZ0.p8').write_text('k')
    assert brandtool.find_downloaded_p8(
        'ABC123XYZ0', downloads_dir=str(dl)) == str(dl / 'AuthKey_ABC123XYZ0.p8')

    other = tmp_path / 'elsewhere.p8'
    other.write_text('k')
    answers = iter(['missing-file.p8', str(other)])
    found = brandtool.find_downloaded_p8('ZZZZZZZZZZ', downloads_dir=str(dl),
                                         input_fn=lambda _: next(answers))
    assert found == str(other)
