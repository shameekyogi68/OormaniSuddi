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

from brand.content import ContentError, Edition, edition_day            # noqa: E402
from brand.review import approve, is_signed, review       # noqa: E402


MARK = '<!-- regate -->'


def _note_run_report(outdir: str, rep, ok: bool) -> None:
    """run_report.md is written by the render; a re-check after it left the page saying "Failed … no
    APPROVAL.md written" beside an APPROVAL.md (2026-11-15). Put what is true NOW at the top (D151)."""
    import time
    path = os.path.join(outdir, 'run_report.md')
    try:
        with open(path, encoding='utf-8') as fh:
            body = fh.read()
    except OSError:
        return
    if MARK in body:
        body = body.split(MARK, 2)[-1].lstrip('\n')
    head = [f'> **Gate re-checked {time.strftime("%Y-%m-%d %H:%M")}** — ' +
            ('mechanically clean, `APPROVAL.md` written. ' if ok else
             f'HELD on {len(rep.fail)} fault(s); no `APPROVAL.md`. ') +
            'Everything below this note is the render as it ran; its "Failed" list is from then, not now.']
    head += [f'> - {m}' for m in rep.fail]
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(head) + f'\n{MARK}\n\n' + body)
    except OSError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('edition', help='editions/<date>.json (or just the date)')
    ap.add_argument('--out', help='the render folder (default out/<date>)')
    a = ap.parse_args()

    path = a.edition
    try:
        if not os.path.exists(path):
            path = os.path.join(ROOT, 'editions', f'{edition_day(a.edition)}.json')
        ed = Edition.load(path)
    except ContentError as e:
        print(f'✗ {path}: {e}', file=sys.stderr)
        return 2
    outdir = a.out or os.path.join(ROOT, 'out', ed.date.strftime('%Y-%m-%d'))
    if not os.path.isdir(outdir):
        print(f'✗ {outdir} does not exist — render first: python3 render.py {a.edition} --only saara', file=sys.stderr)
        return 2
    rep = review(outdir, ed).show()
    ok = approve(outdir, rep)
    _note_run_report(outdir, rep, ok)
    if ok:
        print('🟢 APPROVAL.md written — mechanical checks clean')
        print('🟢 signed — cleared to publish' if is_signed(outdir) else
              f'🟡 not yet signed: python3 scripts/sign_off.py {os.path.relpath(outdir, ROOT)} --by "<name>"')
        return 0
    print(f'🔴 HELD — {len(rep.fail)} fault(s) above. Codes and owners in review_report.json.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
