#!/usr/bin/env python3
"""Sign the three judgement seats a machine cannot sit in.

    python3 scripts/sign_off.py out/2026-09-16 --by "Gautam Paduvari"
    python3 scripts/sign_off.py out/2026-09-16 --by "Shameek" --seat culture
    python3 scripts/sign_off.py out/2026-09-16 --status

`brand/review.py` establishes every fact a machine can establish and writes
APPROVAL.md when they are clean. It cannot tell whether the lead is right,
whether a deity is treated with dignity, or whether the package looks like the
channel at its best. Those are the seats this fills, with a name — because a
name can be asked about it afterwards and a score out of ten cannot.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.review import (JUDGEMENT_SEATS, is_signed, sign,  # noqa: E402
                          signoff_state)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('outdir', help='the rendered package, e.g. out/2026-09-16')
    ap.add_argument('--by', help='your name — the person answerable for this')
    ap.add_argument('--seat', action='append', choices=sorted(JUDGEMENT_SEATS),
                    help='sign one seat only; repeatable. Default: all three.')
    ap.add_argument('--notes', default='', help='anything the next reader needs')
    ap.add_argument('--status', action='store_true', help='show, change nothing')
    args = ap.parse_args()

    if not os.path.isdir(args.outdir):
        print(f'✗ {args.outdir} is not a folder', file=sys.stderr)
        return 1

    if args.status or not args.by:
        state = signoff_state(args.outdir)
        print(f'\n  {args.outdir}')
        for seat, question in JUDGEMENT_SEATS.items():
            who = str(state.get(seat, '')).strip()
            print(f'    [{"x" if who else " "}] {seat:<8} {who or "— unsigned"}')
            print(f'             {question}')
        print(f'\n  {"🟢 cleared to publish" if is_signed(args.outdir) else "🟡 not yet cleared to publish"}\n')
        if not args.by:
            if not args.status:
                print('  Pass --by "<your name>" to sign.\n')
            return 0 if args.status else 1

    approval = os.path.join(args.outdir, 'APPROVAL.md')
    if not os.path.exists(approval):
        print(f'✗ {approval} does not exist — the mechanical checks have not '
              f'passed, so there is nothing to sign yet. Re-run render.py and '
              f'fix what review_report.json lists.', file=sys.stderr)
        return 1

    evidence = os.path.join(args.outdir, '_review')
    if not os.path.isdir(evidence) or not os.listdir(evidence):
        print(f'! {evidence} is empty. You are signing for craft without the '
              f'frames the judgement is meant to be made against.',
              file=sys.stderr)

    sign(args.outdir, args.by, tuple(args.seat or ()), args.notes)
    seats = ', '.join(args.seat or sorted(JUDGEMENT_SEATS))
    print(f'✓ {seats} signed by {args.by}')
    if is_signed(args.outdir):
        print('🟢 APPROVAL.md now reads: cleared to publish.')
    else:
        left = [s for s in JUDGEMENT_SEATS
                if not str(signoff_state(args.outdir).get(s, '')).strip()]
        print(f'🟡 still unsigned: {", ".join(left)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
