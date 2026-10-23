#!/usr/bin/env python3
"""
Will today's ಸುದ್ದಿ ಸಾರ copy make a clean reel? Say so BEFORE the render (D132).

    python3 scripts/reel_check.py editions/2026-10-23.json
    python3 scripts/reel_check.py editions/2026-10-23.json --strict     # warnings fail too
    python3 scripts/reel_check.py editions/2026-10-23.json --shots /tmp/look   # preview frames

It lays the real page out in headless Chrome with an estimated voice — a few
seconds, no voice, no film — and reports, per story, what the render would
find out three minutes later: the headline that needs a third line, the
sentence too long for the clock, a figure the voice may misread, a card that
runs under the Reels caption. The intake desk runs it on the copy it has just
written and rewrites until it says CLEAN; the render runs the same checks and
stops on anything that does not fit.

Exit 0: clean (or only warnings, unless --strict). 1: something does not fit.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import saara_reel as R                      # noqa: E402
from brand.content import Edition, edition_day        # noqa: E402
from brand.tokens import Limits                        # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('edition', help='editions/<date>.json (or just the date)')
    ap.add_argument('--strict', action='store_true', help='warnings fail too')
    ap.add_argument('--shots', help='write the preview frames into this folder')
    ap.add_argument('--json', action='store_true', help='machine-readable')
    a = ap.parse_args()

    path = a.edition
    if not os.path.exists(path):
        path = os.path.join(ROOT, 'editions', f'{edition_day(a.edition)}.json')
    with open(path, encoding='utf-8') as fh:
        ed = Edition.from_dict(json.load(fh))
    saara = ed.segment('saara')
    if not saara:
        print('No ಸುದ್ದಿ ಸಾರ stories in this edition — nothing for the reel.')
        return 0
    if not R.available():
        print(f'✗ Google Chrome not found at {R.CHROME} (set OORMANI_CHROME)', file=sys.stderr)
        return 2
    res = R.check(Edition(stories=saara, date=ed.date), shots=a.shots)
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k != 'copies'}, ensure_ascii=False, indent=2))
    else:
        b = res['budget']
        print(f'ಸುದ್ದಿ ಸಾರ reel — {len(saara)} stories · about {res["estimated_seconds"]:.0f}s '
              f'(house cap {Limits.saara_reel_max_seconds:.0f}s) · '
              f'a card sentence may run ~{b["support_chars"]} chars (~{b["support_words"]} words), '
              f'a headline ≤{b["head_chars"]} chars\n')
        for i, c in enumerate(res['copies']):
            lines = (res['lines'] or [0] * len(res['copies']))[i]
            mark = '✓' if lines <= 2 and len(c['body']) <= b['support_chars'] + 25 and not c['notes'] else '·'
            print(f' {mark} {i + 1}. {c["place_short"]:<14} headline {len(c["head"]):>3} chars → {lines} line(s)'
                  f' · card {len(c["body"]):>3} chars ({len(c["body"].split())} words)')
        for msg in res['issues']:
            print(f'\n ✗ DOES NOT FIT  {msg}')
        for msg in res['warnings']:
            print(f'\n ⚠ {msg}')
        for who, toks in res['pronunciation'].items():
            print(f'\n ⚠ voice, {who}: {" ".join(toks)} — may be misread; respell it in assets/pronunciation.json')
        clean = not res['issues'] and not res['warnings'] and not res['pronunciation']
        print('\n' + ('CLEAN — the reel will come out as designed.' if clean else
                      'NOT CLEAN — rewrite the copy named above (reel_line / reel_support), then run this again.'))
    bad = bool(res['issues']) or (a.strict and bool(res['warnings'] or res['pronunciation']))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
