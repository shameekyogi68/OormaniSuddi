#!/usr/bin/env python3
"""
Log, acknowledge and close a correction. The IT Rules clocks, in one place.

    python3 scripts/correction.py new --about 2026-09-16 \\
        --summary "Place name wrong: was Brahmavara, should be Kundapura" \\
        --from "WhatsApp +91 …" --channel whatsapp

    python3 scripts/correction.py ack  2026-09-16-01 --by "Gautam Paduvari"
    python3 scripts/correction.py close 2026-09-16-01 --by "Gautam Paduvari" \\
        --outcome "Carousel slide 3 re-rendered" \\
        --published "ತಿದ್ದುಪಡಿ: ಸ್ಥಳ ಕುಂದಾಪುರ, ಬ್ರಹ್ಮಾವರ ಅಲ್ಲ."

    python3 scripts/correction.py status      # what is open, what is late
    python3 scripts/correction.py weekly      # draft the clarifications post

Acknowledge within 24 hours, dispose within 15 days. Those are statutory, and
they start the moment a message arrives — not the moment somebody remembers it.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import corrections as C   # noqa: E402


def cmd_new(a) -> int:
    c = C.receive(a.about, a.summary, a.complainant, a.channel)
    print(f'✓ {c.id} logged')
    print(f'  Acknowledge within {C.ACK_HOURS}h:')
    print(f'    python3 scripts/correction.py ack {c.id} --by "<name>"')
    return 0


def cmd_ack(a) -> int:
    C.acknowledge(a.id, a.by)
    print(f'✓ {a.id} acknowledged by {a.by}. '
          f'{C.CLOSE_DAYS} days to dispose of it.')
    return 0


def cmd_close(a) -> int:
    C.resolve(a.id, a.by, a.outcome, a.published)
    print(f'✓ {a.id} closed by {a.by}')
    if a.published:
        print('  A visible ತಿದ್ದುಪಡಿ was recorded — it will appear in the '
              'weekly clarifications post.')
    else:
        print('  No published correction recorded. If the substance changed, '
              'it has to be visible; a silent edit is the thing the policy '
              'exists to prevent.')
    return 0


def cmd_status(a) -> int:
    print(f'\n  {C.summary_line()}\n')
    late = C.overdue()
    for row in late['unacknowledged']:
        print(f'  ⚠️  {row["id"]} unacknowledged after {row["hours"]:.0f}h '
              f'(clock: {C.ACK_HOURS}h) — {row["summary"][:60]}')
    for row in late['unresolved']:
        print(f'  ⚠️  {row["id"]} unresolved after {row["days"]}d '
              f'(clock: {C.CLOSE_DAYS}d) — {row["summary"][:60]}')
    rows = C.current()
    if rows and not any(late.values()):
        print('  Both statutory clocks are clear.')
    for cid, row in sorted(rows.items()):
        state = row.get('state', 'received')
        mark = {'received': '🔴', 'acknowledged': '🟡'}.get(state, '🟢')
        print(f'  {mark} {cid}  {state:<13} {row.get("summary", "")[:56]}')
    print()
    return 0


def cmd_weekly(a) -> int:
    post = C.weekly_post(a.days)
    if not post:
        print(f'No published corrections in the last {a.days} days. '
              f'Nothing to post — do not manufacture one.')
        return 0
    print(post)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    n = sub.add_parser('new')
    n.add_argument('--about', required=True, help='edition date or asset')
    n.add_argument('--summary', required=True)
    n.add_argument('--from', dest='complainant', default='')
    n.add_argument('--channel', default='',
                   choices=['', 'whatsapp', 'email', 'instagram', 'comment', 'phone'])
    n.set_defaults(fn=cmd_new)

    k = sub.add_parser('ack')
    k.add_argument('id')
    k.add_argument('--by', required=True)
    k.set_defaults(fn=cmd_ack)

    c = sub.add_parser('close')
    c.add_argument('id')
    c.add_argument('--by', required=True)
    c.add_argument('--outcome', required=True)
    c.add_argument('--published', default='',
                   help='the ತಿದ್ದುಪಡಿ text that actually went out')
    c.set_defaults(fn=cmd_close)

    s = sub.add_parser('status')
    s.set_defaults(fn=cmd_status)

    w = sub.add_parser('weekly')
    w.add_argument('--days', type=int, default=7)
    w.set_defaults(fn=cmd_weekly)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    raise SystemExit(main())
