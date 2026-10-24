#!/usr/bin/env python3
"""
Run the gate again on a render that already exists — seconds, not minutes (D134).

    python3 scripts/regate.py editions/2026-10-24.json            # out/2026-10-24 against the edition as it is now
    python3 scripts/regate.py editions/2026-10-24.json --json

The desks (fact, Kannada, legal, reach) file their receipts AFTER the render has started, and the gate
wants every receipt. Re-rendering a finished film only to let the gate see a receipt was most of a
morning's lost time. This re-reads the same folder against the same edition and writes (or withdraws)
APPROVAL.md. It is safe: the gate also compares the reel with the copy as it is NOW, so if a desk
changed a word the film shows or says, it says "re-render" instead of passing.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from brand.content import Edition, edition_day            # noqa: E402
from brand.review import approve, is_signed, review       # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('edition', help='editions/<date>.json (or just the date)')
    ap.add_argument('--out', help='the render folder (default out/<date>)')
    a = ap.parse_args()

    path = a.edition if os.path.exists(a.edition) else os.path.join(ROOT, 'editions', f'{edition_day(a.edition)}.json')
    ed = Edition.load(path)
    outdir = a.out or os.path.join(ROOT, 'out', ed.date.strftime('%Y-%m-%d'))
    if not os.path.isdir(outdir):
        print(f'✗ {outdir} does not exist — render first: python3 render.py {a.edition} --only saara', file=sys.stderr)
        return 2
    rep = review(outdir, ed).show()
    if approve(outdir, rep):
        print('🟢 APPROVAL.md written — mechanical checks clean')
        print('🟢 signed — cleared to publish' if is_signed(outdir) else
              f'🟡 not yet signed: python3 scripts/sign_off.py {os.path.relpath(outdir, ROOT)} --by "<name>"')
        return 0
    print(f'🔴 HELD — {len(rep.fail)} fault(s) above. Codes and owners in review_report.json.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
