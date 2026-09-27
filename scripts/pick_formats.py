#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — which formats this edition renders (D92).
=========================================================
Read off the stories' segments, never guessed from how many there are. A
story runs in exactly one format, so the answer is simply the set of
segments present — in the order they post:

    saara   ಸುದ್ದಿ ಸಾರ    text carousel
    mukhya  ಮುಖ್ಯ ಸುದ್ದಿ  one photo carousel per top story
    roundup ಸ್ಪೀಡ್ ನ್ಯೂಸ್  the reel

    python3 scripts/pick_formats.py editions/2026-09-27.json
    # -> saara roundup

`python3 render.py editions/DATE.json` already renders exactly these; this
exists for anything that wants to know without rendering.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.content import SEGMENTS  # noqa: E402

ORDER = ('saara', 'mukhya', 'speed')


def formats_for_edition(path: str) -> tuple[list[str], str]:
    """(formats to render, why)."""
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    stories = data.get('stories', [])
    if not stories:
        return [], 'no stories in this edition'
    count = {k: 0 for k in ORDER}
    missing = 0
    for st in stories:
        seg = st.get('segment', '')
        if seg in count:
            count[seg] += 1
        else:
            missing += 1
    formats = [SEGMENTS[k][1] for k in ORDER if count[k]]
    why = ' · '.join(f'{SEGMENTS[k][0]} {count[k]}' for k in ORDER if count[k])
    if missing:
        why += (f'{" · " if why else ""}{missing} story(ies) with no segment — '
                'give each one speed, saara or mukhya')
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
    print(f'# {why}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
