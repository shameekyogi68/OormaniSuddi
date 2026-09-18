#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — which formats today actually earns.
=======================================================
House rule 2026-09-18-02 (D81): carousel ships every day, plus ONE reel.
With three or more stories that reel is ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — the whole day as one
quick-news video. On a thin day it is the lead-story reel, and only if the
lead clears brand.reach.should_be_reel() (D72). Never both: two reels of one
morning split the same audience. story_card and broadsheet are never in the
default; carousel already covers that ground.

    python3 scripts/pick_formats.py editions/2026-09-18.json
    # -> carousel roundup        (3+ stories)
    # -> carousel reel           (thin day, lead earns it)
    # -> carousel                (thin day, it does not)

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
    """(formats to render, why) — carousel always, and one reel.

    The daily reel is ಸ್ಪೀಡ್ ನ್ಯೂಸ್ whenever the edition has enough stories
    to make one (D81, house rule 2026-09-18-02). On a thin day — one or two
    stories — the lead-story reel is rendered only if the lead earns it, the
    same mechanical test as before (should_be_reel, D72). Never both: two
    reels of the same morning split the same audience.
    """
    from brand.tokens import Limits
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    stories = data.get('stories', [])
    formats = ['carousel']
    if not stories:
        return formats, 'no stories in this edition'
    if len(stories) >= Limits.roundup_min_stories:
        formats.append('roundup')
        return formats, (f'{len(stories)} stories — the day goes out as one '
                         f'speed-news reel')
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
