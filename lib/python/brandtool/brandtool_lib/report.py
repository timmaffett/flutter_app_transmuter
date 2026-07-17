"""Audit data model, report rendering, and interactive fixing. ASCII-only output
(ANSI color escapes are optional and ASCII-safe)."""
import json
import os
import re
import sys

_COLOR_OVERRIDE = None


def set_color(enabled):
    """CLI sets the session's color decision (None = auto by TTY/NO_COLOR)."""
    global _COLOR_OVERRIDE
    _COLOR_OVERRIDE = enabled


def color_enabled():
    if _COLOR_OVERRIDE is not None:
        return _COLOR_OVERRIDE
    return sys.stdout.isatty() and not os.environ.get('NO_COLOR')


def paint(text, color_name):
    """Color text only when the session has color enabled (safe for piped/json)."""
    return _c(text, color_name) if color_enabled() else text

OK, ISSUE, ERROR, SKIP, INFO = 'ok', 'issue', 'error', 'skip', 'info'

STATUS_LABEL = {OK: 'ok', ISSUE: 'ISSUE', ERROR: 'ERROR', SKIP: 'skip', INFO: 'info'}

_COLORS = {'green': '\x1b[32m', 'red': '\x1b[31m', 'brightred': '\x1b[91m',
           'yellow': '\x1b[33m', 'cyan': '\x1b[36m', 'blue': '\x1b[94m',
           'magenta': '\x1b[95m', 'orange': '\x1b[38;5;208m',
           'alert': '\x1b[41;93;1m', 'flash': '\x1b[5;91;1m',
           'command': '\x1b[38;5;111m',  # cornflower blue for command suggestions
           'value': '\x1b[38;5;228m',    # light yellow for run/brand-varying values
           'pink': '\x1b[38;5;213m',     # UI click-path / literal-text highlights
           'darkblue': '\x1b[34m'}       # role/choice selections in external UIs
_RESET = '\x1b[0m'

STATUS_COLOR = {OK: 'green', ISSUE: 'red', ERROR: 'brightred',
                SKIP: 'yellow', INFO: 'cyan'}

# Platform classification for check names (Android = blue, iOS = magenta).
_IOS_RE = re.compile(r'iOS|\bASC\b|App Store|Bundle ID|APNs|Certificates|App ID'
                     r'|GoogleService-Info')
_ANDROID_RE = re.compile(r'Android|google-services|\bPlay\b|cert fingerprints')


def _c(text, color_name):
    return f'{_COLORS[color_name]}{text}{_RESET}'


def _platform_color(check_name):
    if _IOS_RE.search(check_name):
        return 'magenta'
    if _ANDROID_RE.search(check_name):
        return 'blue'
    return None


class Check:
    def __init__(self, name, status, detail='', fix=None, console_url=None, flash=False):
        self.name = name
        self.status = status
        self.detail = detail
        self.fix = fix
        self.console_url = console_url
        self.flash = flash


class BrandReport:
    def __init__(self, brand, project_id='?', package='?'):
        self.brand = brand
        self.project_id = project_id
        self.package = package
        self.checks = []

    def add(self, *args, **kwargs):
        check = Check(*args, **kwargs)
        self.checks.append(check)
        return check

    @property
    def issues(self):
        return [c for c in self.checks if c.status in (ISSUE, ERROR)]

    @property
    def fixable(self):
        return [c for c in self.checks if c.status == ISSUE and c.fix]


def render_text(reports, color=False):
    lines = ['', '=' * 78, 'BRAND AUDIT REPORT', '=' * 78]
    if color:
        lines.append('  Legend: ' + _c('Android', 'blue') + '   ' + _c('iOS', 'magenta')
                     + '     ' + _c('ok', 'green') + '  ' + _c('ISSUE', 'red') + '  '
                     + _c('ERROR', 'brightred') + '  ' + _c('skip', 'yellow') + '  '
                     + _c('info', 'cyan'))
    for r in reports:
        lines.append('')
        lines.append(f'  {r.brand}')
        lines.append('      project: ' + paint(r.project_id, 'cyan')
                     + '   package: ' + paint(r.package, 'value'))
        for c in r.checks:
            detail = c.detail
            if color and c.flash and detail:
                detail = _c(detail, 'flash')
            suffix = f': {detail}' if detail else ''
            label = STATUS_LABEL[c.status].ljust(6)
            name = c.name
            if color:
                label = _c(label, STATUS_COLOR[c.status])
                platform = _platform_color(c.name)
                if platform:
                    name = _c(name, platform)
            lines.append(f'      {label} {name}{suffix}')
    lines += ['', '=' * 78, 'SUMMARY', '-' * 78]
    for r in reports:
        n = len(r.issues)
        status_txt = 'OK' if n == 0 else f'{n} issue(s)'
        if color:
            status_txt = _c(status_txt, 'green' if n == 0 else 'red')
        lines.append(f'  {r.brand:42} {status_txt}')
    lines.append('=' * 78)
    return '\n'.join(lines)


_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _visible_len(text):
    return len(_ANSI_RE.sub('', text))


def _wrap_visible(ln, width):
    """Greedy word-wrap by VISIBLE length (ANSI codes ignored for measuring).
    Continuation lines get a hanging indent; over-long single words (URLs)
    are kept whole."""
    if _visible_len(ln) <= width:
        return [ln]
    prefix = ' ' * (len(ln) - len(ln.lstrip(' ')))
    indent = prefix + '    '
    out = []
    cur, cur_len = [], len(prefix)
    for word in ln.strip(' ').split(' '):
        wlen = _visible_len(word)
        extra = wlen + (1 if cur else 0)
        if cur and cur_len + extra > width:
            out.append((prefix if not out else indent) + ' '.join(cur))
            cur, cur_len = [word], len(indent) + wlen
        else:
            cur.append(word)
            cur_len += extra
    if cur:
        out.append((prefix if not out else indent) + ' '.join(cur))
    return out


def boxed(text, color_name=None, color=False, wrap=None, min_width=None):
    """Wrap text in an ASCII double-line box (++==++ / || ||); the border can be
    colored while inner lines keep their own colors (padding is ANSI-aware).
    wrap=N word-wraps by visible length (whole URLs are never split);
    min_width pads the box so multiple boxes can share one width."""
    lines = text.split('\n')
    if wrap:
        wrapped = []
        for ln in lines:
            wrapped.extend(_wrap_visible(ln, wrap))
        lines = wrapped
    width = max(max(_visible_len(ln) for ln in lines), min_width or 0)
    horizontal = '++' + '=' * (width + 2) + '++'
    edge = _c(horizontal, color_name) if color and color_name else horizontal
    side = _c('||', color_name) if color and color_name else '||'
    out = [edge]
    for ln in lines:
        pad = ' ' * (width - _visible_len(ln))
        out.append(f'{side} {ln}{pad} {side}')
    out.append(edge)
    return '\n'.join(out)


def alert_highlight(text):
    """Highlight a fragment INSIDE a render_alert line: switches the foreground
    to bold dark blue and back to the alert's bright yellow. Never emits a full
    reset (that would kill the banner's red background mid-line); render_alert
    strips the codes when rendering uncolored."""
    return f'\x1b[34;1m{text}\x1b[93;1m'


def render_alert(message_lines, color=False):
    """A loud !!-bordered banner (yellow-on-red when colored) for must-see notices.
    Lines may contain alert_highlight() fragments; padding is ANSI-aware."""
    if not color:
        message_lines = [_ANSI_RE.sub('', ln) for ln in message_lines]
    width = max(60, max(_visible_len(ln) for ln in message_lines))
    border = '!' * (width + 6)
    out = [border]
    for ln in message_lines:
        pad = ' ' * (width - _visible_len(ln))
        out.append('!! ' + ln + pad + ' !!')
    out.append(border)
    if color:
        out = [_c(ln, 'alert') for ln in out]
    return '\n'.join(out)


def render_json(reports):
    return json.dumps([
        {'brand': r.brand, 'project': r.project_id, 'package': r.package,
         'checks': [{'name': c.name, 'status': c.status, 'detail': c.detail,
                     'fixable': c.fix is not None} for c in r.checks]}
        for r in reports], indent=2)


def run_fixes(reports, assume_yes=False, input_fn=input, print_fn=print):
    """Walk fixable issues, prompting per issue (console URL shown first). Returns count fixed."""
    fixed = 0
    for r in reports:
        for c in r.fixable:
            print_fn(f'\n--- {r.brand}: {c.name}: {c.detail}')
            if c.console_url:
                print_fn('    Inspect first if you like: '
                         + paint(c.console_url, 'cyan'))
            if assume_yes:
                answer = 'y'
            else:
                try:
                    answer = input_fn('    Fix this? [y/N] ').strip().lower()
                except EOFError:
                    print_fn('    (no interactive input - skipping; use --yes to fix without prompts)')
                    continue
                except KeyboardInterrupt:
                    raise SystemExit('\n    (interrupted - exiting; re-run the audit '
                                     'when ready)')
            if answer != 'y':
                print_fn('    Skipped.')
                continue
            try:
                c.fix()
                c.status = OK
                fixed += 1
                print_fn('    FIXED')
            except KeyboardInterrupt:
                raise SystemExit('\n    (interrupted - exiting; re-run the audit '
                                 'when ready)')
            except Exception as e:
                c.status = ERROR
                c.detail += f' (fix failed: {e})'
                print_fn(f'    FIX FAILED: {e}')
    return fixed
