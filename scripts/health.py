#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — is the newsroom actually running?
=================================================
One page, everything that can go quietly wrong. Run it when you sit down.

    python3 scripts/health.py

It answers the questions that only have a bad answer once it is too late:

  * Did the morning fetch run, and did it produce leads or just headlines?
  * Is anything past a statutory clock?
  * Is there more than one copy of the published record?
  * Is a recurring review overdue?
  * Is the code pushed, and do the fast suites still pass?

Everything it reads lives inside this repository. The 06:05 schedule on this
machine is owned by a script outside it, and that is fine — whatever calls
`fetch_daily_news.py` writes `logs/last_fetch.json` on the way through, so this
can tell you whether the morning worked without knowing or caring who started
it. Issue #19 was never about owning the scheduler.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OK, WARN, BAD = '  ✓', '  !', '  ✗'


def _age(iso: str) -> timedelta | None:
    try:
        return datetime.now() - datetime.fromisoformat(iso)
    except Exception:
        return None


def check_fetch() -> list[str]:
    out = []
    hb = os.path.join(ROOT, 'logs', 'last_fetch.json')
    if not os.path.exists(hb):
        return [f'{WARN} morning fetch — never recorded a run.',
                '      Whatever runs at 06:05 has not called '
                'scripts/fetch_daily_news.py since this check was added.',
                '      Run it once by hand to confirm the path works:',
                '        python3 scripts/fetch_daily_news.py']
    try:
        with open(hb, encoding='utf-8') as fh:
            d = json.load(fh)
    except Exception as e:
        return [f'{BAD} morning fetch — heartbeat unreadable ({e})']

    age = _age(d.get('at', ''))
    hours = age.total_seconds() / 3600 if age else 999
    when = f'{hours:.0f}h ago' if hours < 48 else f'{hours / 24:.0f} days ago'

    if not d.get('ok'):
        out.append(f'{BAD} morning fetch — FAILED {when}: {d.get("reason", "")}')
    elif hours > 30:
        out.append(f'{BAD} morning fetch — last succeeded {when}. '
                   f'Something has stopped running it.')
    else:
        c = d.get('counts', {})
        out.append(f'{OK} morning fetch — ran {when}, {c.get("tips", 0)} tips, '
                   f'{c.get("full_articles", 0)} full articles')

    if d.get('ok'):
        if not d.get('leads_written'):
            out.append(f'{WARN} …but NO Kannada leads were written. The sheet '
                       f'is raw headlines.')
            out.append(f'      text model: {d.get("text_model", "?")} — if it '
                       f'has been retired, set OORMANI_TEXT_MODEL.')
        if d.get('extractor') == 'none':
            out.append(f'{WARN} …and no article bodies (trafilatura missing), '
                       f'so leads rest on headlines alone.')
        flagged = d.get('counts', {}).get('flagged_unsupported', 0)
        if flagged:
            out.append(f'      {flagged} lead(s) carry words the source does '
                       f'not — read those first in inbox/today.md')
    return out


def check_edition() -> list[str]:
    """Does today have a draft, and how far is it from postable."""
    from datetime import date
    today = date.today().isoformat()
    path = os.path.join(ROOT, 'editions', f'{today}.json')
    if not os.path.exists(path):
        return [f'{WARN} today\'s edition — none yet. '
                f'python3 scripts/draft_edition.py']
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
    tars = sorted((f for f in os.listdir(local)), reverse=True) \
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


def check_tests() -> list[str]:
    r = subprocess.run(
        [sys.executable, '-m', 'unittest', 'tests.test_contract',
         'tests.test_legibility', 'tests.test_legal_corpus',
         'tests.test_intake', 'tests.test_calendar', '-q'],
        cwd=ROOT, capture_output=True, text=True)
    tail = (r.stderr or r.stdout).strip().split('\n')[-1]
    if r.returncode == 0:
        return [f'{OK} contract — {tail}']
    return [f'{BAD} contract — FAILING. {tail}',
            '      python3 -m unittest discover tests']


def main() -> int:
    print(f'\n  ಊರ್ಮನಿ ಸುದ್ದಿ — health   {datetime.now():%Y-%m-%d %H:%M}\n')
    lines: list[str] = []
    for fn in (check_fetch, check_edition, check_clocks, check_reviews,
               check_house, check_music, check_backups, check_git, check_tests):
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
