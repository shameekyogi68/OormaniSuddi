#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — what is coming, and what the desk should already be on.
======================================================================
A local channel is judged on whether it turned up for the things its town
cares about. Missing Krishna Janmashtami in Udupi is a miss a reader remembers
longer than any good story — and the way it gets missed is never a decision,
it is a Tuesday.

Not named calendar.py, and it matters: a module of that name in scripts/
shadows the standard library's `calendar` for anything run from that directory,
and Python's own date parsing depends on it. It broke trafilatura — and so the
whole 06:05 intake — the first time the real fetch ran after this was added.

    python3 scripts/whats_on.py                 # the next 30 days
    python3 scripts/whats_on.py --days 90
    python3 scripts/whats_on.py --scaffold ganesha   # start the greeting JSON
    python3 scripts/whats_on.py --reviews       # what is due, and what is overdue

On lunar dates this tool tells you the MONTH and refuses to tell you the day.
Every Hindu and Islamic festival here moves with its own calendar, and a
greeting posted on the wrong day is worse than no greeting — so the reminder
fires at the start of the month and says "confirm from the panchanga", which is
a thing a person does and a thing this script must not pretend to have done.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CAL = os.path.join(ROOT, 'editions', 'greetings', 'calendar.json')
STATE = os.path.join(ROOT, 'archive', 'calendar_state.json')

WEIGHT_MARK = {'highest': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '·'}


def load() -> dict:
    with open(CAL, encoding='utf-8') as fh:
        return json.load(fh)


def _today() -> date:
    # Honours the frozen clock, so a test or a reproduction sees a fixed day.
    from brand.content import now
    return now().date()


def next_occurrence(mmdd: str, frm: date) -> date:
    m, d = (int(x) for x in mmdd.split('-'))
    try:
        this = date(frm.year, m, d)
    except ValueError:                      # 29 Feb in a non-leap year
        this = date(frm.year, m, 28)
    if this < frm:
        try:
            return date(frm.year + 1, m, d)
        except ValueError:
            return date(frm.year + 1, m, 28)
    return this


def upcoming(days: int) -> tuple[list, list, list]:
    """(dated observances, lunar months opening, seasons running or starting)."""
    cal = load()
    today = _today()
    horizon = today + timedelta(days=days)

    dated, lunar, seasons = [], [], []

    for o in cal['observances']:
        if o['when'] == 'fixed':
            when = next_occurrence(o['date'], today)
            if when <= horizon:
                dated.append((when, (when - today).days, o))
        else:
            # A lunar festival's month is reliable; its day is not. Surface it
            # when that month is inside the horizon.
            m = int(o['month'])
            start = next_occurrence(f'{m:02d}-01', today)
            if start <= horizon:
                lunar.append((start, (start - today).days, o))

    for s in cal['seasons']:
        start = next_occurrence(s['from'], today)
        end_mmdd = s['to']
        em, ed = (int(x) for x in end_mmdd.split('-'))
        sm = int(s['from'].split('-')[0])
        # Is it running right now? A season that wraps the new year (Nov→Mar)
        # needs the wrap handled or Kambala vanishes every December.
        cur = (today.month, today.day)
        a, b = (sm, int(s['from'].split('-')[1])), (em, ed)
        running = (a <= cur <= b) if a <= b else (cur >= a or cur <= b)
        if running:
            seasons.append((None, 0, s, 'running'))
        elif start <= horizon:
            seasons.append((start, (start - today).days, s, 'starts'))

    dated.sort(key=lambda r: r[0])
    lunar.sort(key=lambda r: r[0])
    seasons.sort(key=lambda r: r[1])
    return dated, lunar, seasons


def show(days: int) -> int:
    dated, lunar, seasons = upcoming(days)
    today = _today()
    print(f'\n  ಊರ್ಮನಿ ಸುದ್ದಿ — the next {days} days   (from {today})\n')

    running = [s for s in seasons if s[3] == 'running']
    if running:
        print('  ON NOW')
        for _w, _d, s, _k in running:
            print(f'    {WEIGHT_MARK.get(s["weight"], "·")} {s["kn"]}  ({s["id"]})')
            print(f'        {s["desk"]}')
        print()

    if dated:
        print('  DATED — these are safe to schedule against')
        for when, away, o in dated:
            print(f'    {WEIGHT_MARK.get(o["weight"], "·")} {when}  '
                  f'in {away:>3}d   {o["kn"]}  —  {o["en"]}')
            if o.get('note'):
                print(f'        {o["note"]}')
        print()

    if lunar:
        print('  LUNAR — the month is reliable, the day is NOT in this file')
        for start, away, o in lunar:
            month = start.strftime('%B %Y')
            print(f'    {WEIGHT_MARK.get(o["weight"], "·")} {month}  '
                  f'(opens in {away}d)   {o["kn"]}  —  {o["en"]}')
            if o.get('note'):
                print(f'        {o["note"]}')
        print('\n    Confirm each of these against a Udupi panchanga. This '
              'script will not guess a date, because a greeting on the wrong '
              'day is worse than none.\n')

    starting = [s for s in seasons if s[3] == 'starts']
    if starting:
        print('  SEASONS OPENING')
        for when, away, s, _k in starting:
            print(f'    {WEIGHT_MARK.get(s["weight"], "·")} {when}  in {away:>3}d   {s["kn"]}')
            print(f'        {s["desk"]}')
        print()

    if not (running or dated or lunar or starting):
        print('  Nothing in the window. A quiet month is a good month to shoot '
              'evergreen footage.\n')
    return 0


# ─────────────────────────────────────────────────────────────────────────────
#  RECURRING REVIEWS
# ─────────────────────────────────────────────────────────────────────────────

def _state() -> dict:
    if not os.path.exists(STATE):
        return {}
    try:
        with open(STATE, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_state(d: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def reviews(mark: str = '') -> int:
    cal = load()
    st = _state()
    today = _today()

    if mark:
        ids = {r['id'] for r in cal['recurring_reviews']}
        if mark not in ids:
            print(f'✗ unknown review {mark!r}; choose from {sorted(ids)}',
                  file=sys.stderr)
            return 1
        st[mark] = today.isoformat()
        _save_state(st)
        print(f'✓ {mark} marked done on {today}')
        return 0

    print(f'\n  Recurring reviews   ({today})\n')
    overdue = 0
    for r in sorted(cal['recurring_reviews'],
                    key=lambda x: {'highest': 0, 'high': 1,
                                   'medium': 2, 'low': 3}.get(x['weight'], 9)):
        last = st.get(r['id'])
        every = int(r['every_days'])
        if last:
            age = (today - date.fromisoformat(last)).days
            due_in = every - age
            when = f'last {last}, {age}d ago'
        else:
            due_in = -1
            when = 'never run'
        late = due_in < 0
        overdue += 1 if late else 0
        mark_ = '⚠️ ' if late else '   '
        print(f'  {mark_}{WEIGHT_MARK.get(r["weight"], "·")} {r["id"]:<22} '
              f'every {every:>3}d · {when}'
              + ('  → DUE' if late else f'  → in {due_in}d'))
        if late:
            print(f'        {r["what"]}')
            print(f'        mark done: python3 scripts/whats_on.py '
                  f'--reviews --done {r["id"]}')
    print()
    if overdue:
        print(f'  {overdue} overdue. The backup restore test is the one that '
              f'costs the most to skip.\n')
    return 0


# ─────────────────────────────────────────────────────────────────────────────
#  SCAFFOLD
# ─────────────────────────────────────────────────────────────────────────────

def scaffold(obs_id: str) -> int:
    cal = load()
    o = next((x for x in cal['observances'] if x['id'] == obs_id), None)
    if not o:
        print(f'✗ unknown observance {obs_id!r}. Known: '
              f'{", ".join(x["id"] for x in cal["observances"])}', file=sys.stderr)
        return 1

    out = os.path.join(ROOT, 'editions', 'greetings', f'{obs_id}.json')
    if os.path.exists(out):
        print(f'! {out} already exists — not overwriting.')
        return 1

    when = (next_occurrence(o['date'], _today()).isoformat()
            if o['when'] == 'fixed' else 'CONFIRM-FROM-PANCHANGA')
    # Only fields the Greeting contract accepts. It rejects unknown keys
    # loudly and it is right to — a scaffold that does not validate is a
    # scaffold that wastes the first two minutes of every festival.
    doc = {
        'kind': 'greeting',
        'occasion': o['kn'],
        'theme': o['theme'],
        'salutation': '',
        'wish': '',
        'blessing': '',
        'date': when,
        'slug': obs_id,
        'tags': [],
    }
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    print(f'✓ {os.path.relpath(out, ROOT)}')
    print(f'  Fill salutation / wish / blessing in Kannada, then:')
    print(f'    python3 render.py {os.path.relpath(out, ROOT)}')
    if o['when'] == 'lunar':
        print('  ⚠️  The date is a placeholder. Confirm it first.')
    if o.get('note'):
        print(f'  {o["note"]}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--scaffold', metavar='ID', help='start a greeting JSON')
    ap.add_argument('--reviews', action='store_true',
                    help='the recurring reviews, and what is overdue')
    ap.add_argument('--done', metavar='ID', default='',
                    help='mark a recurring review done today')
    args = ap.parse_args()

    if args.scaffold:
        return scaffold(args.scaffold)
    if args.reviews or args.done:
        return reviews(args.done)
    return show(args.days)


if __name__ == '__main__':
    raise SystemExit(main())
