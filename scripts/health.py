#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — is the newsroom actually running?
=================================================
One page, everything that can go quietly wrong. Run it when you sit down.

    python3 scripts/health.py

It answers the questions that only have a bad answer once it is too late:

  * Does today have an edition, and how far is it from postable?
  * Is anything past a statutory clock?
  * Is there more than one copy of the published record?
  * Is a recurring review overdue?
  * Is the code pushed, and do the fast suites still pass?

Everything it reads lives inside this repository. There is no morning job to
watch any more: news is pasted in by the editor (D92), so the first question
is simply whether today's edition exists and is verified.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OK, WARN, BAD = '  ✓', '  !', '  ✗'


def check_edition() -> list[str]:
    """Does today have a draft, and how far is it from postable."""
    from datetime import date
    today = date.today().isoformat()
    path = os.path.join(ROOT, 'editions', f'{today}.json')
    if not os.path.exists(path):
        return [f'{WARN} today\'s edition — none yet. Paste the news in: '
                f'python3 scripts/intake.py source --help']
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as e:
        return [f'{BAD} today\'s edition — unreadable ({e})']
    stories = data.get('stories', [])
    verified = sum(1 for s in stories if (s.get('verified_by') or '').strip())
    left = len(stories) - verified
    if left == 0 and stories:
        return [f'{OK} today\'s edition — {len(stories)} stories, all '
               f'verified. Render, then sign off.']
    return [f'{WARN} today\'s edition — {verified}/{len(stories)} verified. '
           f'python3 scripts/verify.py editions/{today}.json --status']


def check_clocks() -> list[str]:
    try:
        from brand import corrections as C
    except Exception as e:
        return [f'{WARN} corrections — could not check ({e})']
    late = C.overdue()
    out = []
    if late['unacknowledged']:
        out.append(f'{BAD} corrections — {len(late["unacknowledged"])} past the '
                   f'{C.ACK_HOURS}h acknowledgement clock (IT Rules Part III)')
    if late['unresolved']:
        out.append(f'{BAD} corrections — {len(late["unresolved"])} past the '
                   f'{C.CLOSE_DAYS}-day resolution clock')
    if not any(late.values()):
        out.append(f'{OK} corrections — {C.summary_line()}')
    return out


def check_reviews() -> list[str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'os_whats_on', os.path.join(ROOT, 'scripts', 'whats_on.py'))
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        cal, st = m.load(), m._state()
    except Exception as e:
        return [f'{WARN} reviews — could not check ({e})']
    from datetime import date
    today = date.today()
    late = []
    for r in cal['recurring_reviews']:
        last = st.get(r['id'])
        if not last:
            late.append(r['id'])
            continue
        if (today - date.fromisoformat(last)).days > int(r['every_days']):
            late.append(r['id'])
    if late:
        return [f'{WARN} reviews — overdue: {", ".join(late)}',
                '      python3 scripts/whats_on.py --reviews']
    return [f'{OK} reviews — all current']


def check_backups() -> list[str]:
    out = []
    local = os.path.join(ROOT, '.backups')
    # Newest by TIME. Sorted by name, `oormani-full-2026-09-16` outranked
    # every daily `oormani-2026-09-2x` and a fresh backup read as 9 days old.
    tars = sorted((f for f in os.listdir(local) if f.endswith('.tar.gz')),
                  reverse=True,
                  key=lambda f: os.path.getmtime(os.path.join(local, f))) \
        if os.path.isdir(local) else []
    if not tars:
        out.append(f'{BAD} backups — never run. bash scripts/backup.sh')
    else:
        newest = os.path.join(local, tars[0])
        age = (datetime.now()
               - datetime.fromtimestamp(os.path.getmtime(newest)))
        d = age.days
        mark = OK if d <= 2 else (WARN if d <= 7 else BAD)
        out.append(f'{mark} backups — newest local copy {d} day(s) old')
    icloud = os.path.expanduser(
        '~/Library/Mobile Documents/com~apple~CloudDocs/OormaniSuddi')
    ext = os.environ.get('OORMANI_BACKUP_DIR') or icloud
    if os.path.isdir(ext):
        out.append(f'{OK} backups — second copy at '
                   f'{"iCloud Drive" if ext == icloud else ext}')
    else:
        out.append(f'{BAD} backups — no second copy anywhere')
    return out


def check_house() -> list[str]:
    try:
        from brand import house
        live = house.rules()
    except Exception as e:
        return [f'{WARN} house rules — could not read ({e})']
    if not live:
        return [f'{OK} house rules — none set',
                '      python3 scripts/house_rule.py add "…" --scope desk']
    by_scope: dict[str, int] = {}
    for r in live:
        by_scope[r.scope] = by_scope.get(r.scope, 0) + 1
    where = ', '.join(f'{k} {v}' for k, v in sorted(by_scope.items()))
    return [f'{OK} house rules — {len(live)} in force ({where})',
            '      docs/HOUSE_RULES.md']


def check_music() -> list[str]:
    """The quarterly licence audit, as something that runs."""
    try:
        from brand import music
        problems = music.audit()
    except Exception as e:
        return [f'{WARN} music licences — could not check ({e})']
    if not problems:
        n = len(music.allowed_paths('bed'))
        return [f'{OK} music licences — register clean, {n} bed(s) usable']
    out = [f'{BAD} music licences — {len(problems)} problem(s). Every video '
           f'that used an unverified bed is exposed, and a strike is how you '
           f'find out.']
    for m in problems[:4]:
        out.append(f'      {m[:150]}')
    return out


def check_git() -> list[str]:
    def run(*a):
        return subprocess.run(a, cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    out = []
    dirty = run('git', 'status', '--porcelain')
    n = len([x for x in dirty.split('\n') if x.strip()])
    out.append(f'{OK} git — clean' if not n
               else f'{WARN} git — {n} uncommitted file(s)')
    ahead = run('git', 'rev-list', '--count', '@{upstream}..HEAD')
    if ahead and ahead != '0':
        out.append(f'{BAD} git — {ahead} commit(s) NOT pushed. '
                   f'That is the offsite copy.')
    elif ahead == '0':
        out.append(f'{OK} git — pushed, up to date')
    return out


def check_disk() -> list[str]:
    """Room to render. A full disk fails mid-render with an error about
    something else entirely. D113."""
    from brand.tokens import Limits
    free = shutil.disk_usage(ROOT).free / 1e9
    if free < Limits.disk_min_gb:
        return [f'{BAD} disk — {free:.1f} GB free. Renders will fail. Archive '
                'finished days (scripts/archive_edition.py) and empty the Trash.']
    if free < Limits.disk_warn_gb:
        return [f'{WARN} disk — {free:.1f} GB free; under {Limits.disk_warn_gb} GB. '
                'du -sh out build .backups shows what is local to this project.']
    return [f'{OK} disk — {free:.0f} GB free']


def check_tools() -> list[str]:
    """What a render needs from this Mac, beyond Python. A system update can
    take any of these away without touching the repo. D113."""
    out = []
    missing = [t for t in ('ffmpeg', 'ffprobe') if not shutil.which(t)]
    if missing:
        out.append(f'{BAD} tools — {", ".join(missing)} not found: no reel, no '
                   'carousel video. brew install ffmpeg')
    try:
        from PIL import features
        raqm = features.check_feature('raqm')
    except Exception:
        raqm = False
    if not raqm:
        out.append(f'{BAD} tools — Pillow has no raqm: Kannada conjuncts will '
                   'render broken. The wheel bundles it: python3 -m pip install '
                   '--break-system-packages --force-reinstall Pillow')
    import importlib.util
    if importlib.util.find_spec('fontTools') is None:
        out.append(f'{BAD} tools — fontTools not installed: the guard against '
                   'letters rendering as empty boxes is OFF (TYPE-01). '
                   'python3 -m pip install --break-system-packages -r requirements.txt')
    try:
        edge = importlib.util.find_spec('edge_tts') is not None
    except Exception:
        edge = False
    if not edge:
        out.append(f'{WARN} tools — edge-tts not installed: no fallback voice if '
                   'Google TTS is down. pip install -r requirements.txt')
    return out or [f'{OK} tools — ffmpeg, Kannada shaping, glyph check, fallback voice']


def check_tests() -> list[str]:
    # Every suite but the four that render video — the same set the
    # pre-commit hook runs, a few seconds in all.
    slow = {'test_golden', 'test_animate', 'test_formats', 'test_speednews'}
    suites = sorted(f'tests.{f[:-3]}' for f in os.listdir(os.path.join(ROOT, 'tests'))
                    if f.startswith('test_') and f.endswith('.py') and f[:-3] not in slow)
    r = subprocess.run(
        [sys.executable, '-m', 'unittest', *suites, '-q'],
        cwd=ROOT, capture_output=True, text=True)
    tail = (r.stderr or r.stdout).strip().split('\n')[-1]
    if r.returncode == 0:
        return [f'{OK} contract — {tail}']
    return [f'{BAD} contract — FAILING. {tail}',
            '      python3 -m unittest discover tests']


def main() -> int:
    print(f'\n  ಊರ್ಮನಿ ಸುದ್ದಿ — health   {datetime.now():%Y-%m-%d %H:%M}\n')
    lines: list[str] = []
    for fn in (check_edition, check_clocks, check_reviews,
               check_house, check_music, check_disk, check_tools,
               check_backups, check_git, check_tests):
        try:
            lines += fn()
        except Exception as e:                      # never fail the check
            lines.append(f'{WARN} {fn.__name__} raised {type(e).__name__}: {e}')
        lines.append('')
    print('\n'.join(lines))
    bad = sum(1 for l in lines if l.startswith(BAD))
    warn = sum(1 for l in lines if l.startswith(WARN))
    if bad:
        print(f'  {bad} thing(s) need attention, {warn} worth a look.\n')
    elif warn:
        print(f'  Nothing broken. {warn} thing(s) worth a look.\n')
    else:
        print('  Everything is where it should be.\n')
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
