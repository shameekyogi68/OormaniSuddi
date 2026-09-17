#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — which formats today actually earns.
=======================================================
House rule 2026-09-17-02: carousel ships every day — it is the one format
that works for any story at any relevance. story_card and broadsheet are
dropped from the daily default entirely; they cover ground the carousel
already covers, and every extra file is more time spent posting instead of
reading it. The reel is not a default at all — it is earned, per edition, by
whether the LEAD story clears brand.reach.should_be_reel() (D72), the same
mechanical relevance check the Chief Editor gate already trusts elsewhere.
This is the "second brain" deciding by evidence, not a script guessing.

    python3 scripts/pick_formats.py editions/2026-09-17.json
    # -> carousel
    # or -> carousel reel

Use the result directly:
    python3 render.py editions/{date}.json \\
        --only $(python3 scripts/pick_formats.py editions/{date}.json) \\
        --out out/{date}
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.content import Story  # noqa: E402
from brand.reach import should_be_reel  # noqa: E402


def formats_for_edition(path: str) -> tuple[list[str], str]:
    """(formats to render, why) — carousel always, reel only if the lead
    story earns it."""
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    stories = data.get('stories', [])
    formats = ['carousel']
    if not stories:
        return formats, 'no stories in this edition'
    lead = Story.from_dict(stories[0])
    earns, why = should_be_reel(lead)
    if earns:
        formats.append('reel')
    return formats, why


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: pick_formats.py editions/{date}.json', file=sys.stderr)
        return 1
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f'✗ {path} does not exist', file=sys.stderr)
        return 1
    formats, why = formats_for_edition(path)
    print(' '.join(formats))
    print(f'# reel: {why}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
