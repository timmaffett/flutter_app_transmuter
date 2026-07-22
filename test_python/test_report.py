import json

from brandtool_lib.report import (OK, ISSUE, ERROR, SKIP, BrandReport, render_json,
                                  render_text, run_fixes)


def make_report():
    r = BrandReport('demo', 'demo-proj', 'us.netpark.demo')
    r.add('billing linked', OK)
    r.add('cert fingerprints', ISSUE, 'missing SHA_256', fix=lambda: None,
          console_url='https://example.com')
    r.add('project', ERROR, 'boom')
    return r


def test_issues_and_fixable():
    r = make_report()
    assert [c.name for c in r.issues] == ['cert fingerprints', 'project']
    assert [c.name for c in r.fixable] == ['cert fingerprints']


def test_render_text_is_ascii_and_mentions_everything():
    text = render_text([make_report()])
    assert text.encode('ascii')
    for expected in ('demo', 'demo-proj', 'ISSUE', 'ERROR', 'missing SHA_256', 'SUMMARY'):
        assert expected in text


def test_render_json():
    data = json.loads(render_json([make_report()]))
    assert data[0]['brand'] == 'demo'
    assert data[0]['checks'][1] == {'name': 'cert fingerprints', 'status': 'issue',
                                    'detail': 'missing SHA_256', 'fixable': True}


def test_flash_detail_rendering():
    r = BrandReport('demo')
    r.add('ASC authentication', ISSUE, 'MISSING APPLE APP MANAGER API KEY', flash=True)
    plain = render_text([r])
    assert 'MISSING APPLE APP MANAGER API KEY' in plain and '\x1b[' not in plain
    colored = render_text([r], color=True)
    assert '\x1b[5;91;1mMISSING APPLE APP MANAGER API KEY\x1b[0m' in colored


def test_render_alert_box():
    from brandtool_lib.report import render_alert
    plain = render_alert(['LINE ONE', 'line two'])
    assert 'LINE ONE' in plain and plain.startswith('!!')
    assert '\x1b[' not in plain
    colored = render_alert(['LINE ONE'], color=True)
    assert '\x1b[41;93;1m' in colored and 'LINE ONE' in colored


def test_boxed_ascii_double_line_and_ansi_aware_padding():
    from brandtool_lib.report import boxed
    text = 'short\n\x1b[36mcolored line longer\x1b[0m'
    plain = boxed(text)
    lines = plain.split('\n')
    assert lines[0].startswith('++==') and lines[0].endswith('==++')
    assert lines[-1] == lines[0]
    assert lines[1].startswith('|| ') and lines[1].endswith(' ||')
    # visible width identical on every body line despite embedded ANSI codes
    import re
    strip = lambda s: re.sub(r'\x1b\[[0-9;]*m', '', s)
    assert len(strip(lines[1])) == len(strip(lines[2])) == len(strip(lines[0]))

    colored = boxed('x', color_name='orange', color=True)
    assert '\x1b[38;5;208m++' in colored and '\x1b[38;5;208m||\x1b[0m' in colored


def test_boxed_wraps_colored_lines_by_visible_width():
    import re
    from brandtool_lib.report import boxed
    long_colored = '    name: \x1b[31m' + ('word ' * 40).strip() + '\x1b[0m'
    out = boxed(long_colored, wrap=60)
    strip = lambda s: re.sub(r'\x1b\[[0-9;]*m', '', s)
    lines = out.split('\n')
    # border must be sized near the wrap width, not the unwrapped line (~210)
    assert len(lines[0]) < 75
    assert all(len(strip(ln)) == len(lines[0]) for ln in lines[1:-1])
    assert len(lines) > 4  # actually wrapped into multiple body lines


def test_paint_respects_session_override():
    from brandtool_lib import report
    try:
        report.set_color(True)
        assert report.paint('x', 'green') == '\x1b[32mx\x1b[0m'
        report.set_color(False)
        assert report.paint('x', 'green') == 'x'
    finally:
        report.set_color(None)


def test_run_fixes_prompts_and_applies():
    applied = []
    r = BrandReport('demo')
    r.add('a', ISSUE, 'fix me', fix=lambda: applied.append('a'))
    r.add('b', ISSUE, 'skip me', fix=lambda: applied.append('b'))
    answers = iter(['y', 'n'])
    out = []
    fixed = run_fixes([r], input_fn=lambda _: next(answers), print_fn=out.append)
    assert fixed == 1 and applied == ['a']
    assert r.checks[0].status == OK and r.checks[1].status == ISSUE


def test_render_text_plain_by_default():
    assert '\x1b[' not in render_text([make_report()])


def test_render_text_color_statuses_platforms_and_legend():
    r = BrandReport('demo', 'p', 'pkg')
    r.add('Firebase Android app', OK)
    r.add('Firebase iOS app', ISSUE, 'x')
    r.add('Play Store app', SKIP, 'y')
    r.add('APNs key in Firebase', 'info', 'z')
    r.add('billing linked', ERROR, 'boom')
    text = render_text([r], color=True)
    assert 'Legend:' in text
    assert '\x1b[32mok    \x1b[0m' in text        # green, padding inside
    assert '\x1b[31mISSUE \x1b[0m' in text        # red
    assert '\x1b[91mERROR \x1b[0m' in text        # bright red
    assert '\x1b[33mskip  \x1b[0m' in text        # yellow
    assert '\x1b[36minfo  \x1b[0m' in text        # cyan
    assert '\x1b[94mFirebase Android app\x1b[0m' in text   # blue = Android
    assert '\x1b[95mFirebase iOS app\x1b[0m' in text       # magenta = iOS
    assert '\x1b[94mPlay Store app\x1b[0m' in text
    assert '\x1b[95mAPNs key in Firebase\x1b[0m' in text
    assert '\x1b[91mbilling linked' not in text   # neutral checks uncolored
    # summary line colored red (issues present)
    assert '\x1b[31m5 issue(s)' not in text       # ERROR+ISSUE = 2 issues
    assert '\x1b[31m2 issue(s)\x1b[0m' in text


def test_run_fixes_assume_yes_and_fix_failure():
    r = BrandReport('demo')
    r.add('a', ISSUE, 'boom', fix=lambda: (_ for _ in ()).throw(RuntimeError('nope')))
    fixed = run_fixes([r], assume_yes=True, print_fn=lambda *_: None)
    assert fixed == 0 and r.checks[0].status == ERROR and 'nope' in r.checks[0].detail


def test_render_alert_inline_highlight():
    from brandtool_lib.report import alert_highlight, render_alert
    line = 'No key for: ' + alert_highlight('parkngo_440')
    # uncolored: highlight codes are stripped, padding is by visible length
    plain = render_alert([line])
    assert '\x1b' not in plain
    assert 'No key for: parkngo_440' in plain
    for ln in plain.splitlines()[1:-1]:
        assert ln.endswith(' !!')
    # colored: dark-blue fragment switches back to the alert yellow, never a
    # full reset mid-line (that would kill the red background)
    colored = render_alert([line], color=True)
    assert '\x1b[34;1mparkngo_440\x1b[93;1m' in colored
    body = [ln for ln in colored.splitlines() if 'parkngo' in ln][0]
    assert body.count('\x1b[0m') == 1 and body.endswith('\x1b[0m')


def test_run_fixes_ctrl_c_exits_instead_of_reauditing():
    import pytest
    from brandtool_lib.report import Check, BrandReport
    r = BrandReport('b')
    r.checks.append(Check('c1', ISSUE, 'd', fix=lambda: None))

    def interrupt(_prompt):
        raise KeyboardInterrupt

    with pytest.raises(SystemExit) as e:
        run_fixes([r], input_fn=interrupt, print_fn=lambda *_: None)
    assert 'interrupted' in str(e.value)
