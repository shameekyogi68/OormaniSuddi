#!/usr/bin/env python3
"""
Confirm a story, in one line, after you have actually opened the source.
=========================================================================

    python3 scripts/verify.py editions/2026-09-17.json --story 1 --by "Gautam Paduvari"
    python3 scripts/verify.py editions/2026-09-17.json --all --by "Gautam Paduvari"
    python3 scripts/verify.py editions/2026-09-17.json --status

This is the one command the whole morning collapses to. It does not check
that you actually opened the link — it cannot, and pretending otherwise would
be worse than not having the check at all. It exists to make the ONE thing a
person must do (D59) take five seconds instead of hand-editing JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.content import Edition, ContentError, now  # noqa: E402


def _load(path: str) -> dict:
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _save(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def cmd_status(path: str) -> int:
    data = _load(path)
    stories = data.get('stories', [])
    print(f'\n  {path}\n')
    for i, s in enumerate(stories, 1):
        vb = (s.get('verified_by') or '').strip()
        mark = '✓' if vb else '·'
        print(f'  {mark} {i}. {s.get("headline", "")[:60]}')
        print(f'       {"verified by " + vb if vb else "NOT verified"}')
    left = sum(1 for s in stories if not (s.get('verified_by') or '').strip())
    print(f'\n  {len(stories) - left}/{len(stories)} verified.'
         + (f' {left} left before this can be approved.' if left else
            ' Ready to render.'))
    print()
    return 0


def cmd_verify(path: str, by: str, index: int | None) -> int:
    by = (by or '').strip()
    if not by:
        print('✗ --by needs a real name — that is the whole point', file=sys.stderr)
        return 1
    data = _load(path)
    stories = data.get('stories', [])
    targets = range(len(stories)) if index is None else [index - 1]
    for i in targets:
        if not (0 <= i < len(stories)):
            print(f'✗ no story {i + 1} in this edition (it has {len(stories)})',
                  file=sys.stderr)
            return 1
    for i in targets:
        stories[i]['verified_by'] = by
        stories[i]['verified_at'] = f'{now():%Y-%m-%dT%H:%M:%S%z}'
    _save(path, data)

    try:
        Edition.load(path)
    except ContentError as e:
        print(f'⚠️  saved, but this edition no longer validates: {e}',
              file=sys.stderr)
        print('   Fix the story before rendering.', file=sys.stderr)
        return 1

    who = f'story {index}' if index else f'all {len(stories)} stories'
    print(f'✓ {who} verified by {by}')
    left = sum(1 for s in stories if not (s.get('verified_by') or '').strip())
    if left:
        print(f'  {left} more to go before this can be approved.')
    else:
        print(f'  Every story verified. Render:')
        print(f'    python3 render.py {path} --minimal '
             f'--out out/{os.path.basename(path).removesuffix(".json")}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('edition', help='editions/YYYY-MM-DD.json')
    ap.add_argument('--story', type=int, default=None,
                    help='1-indexed story number; omit with --all for every story')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--by', default='', help='your name — required to verify')
    ap.add_argument('--status', action='store_true', help='show, change nothing')
    args = ap.parse_args()

    if not os.path.exists(args.edition):
        print(f'✗ {args.edition} does not exist', file=sys.stderr)
        return 1

    if args.status or not args.by:
        return cmd_status(args.edition)

    if not args.all and args.story is None:
        print('✗ pass --story N or --all', file=sys.stderr)
        return 1

    return cmd_verify(args.edition, args.by, None if args.all else args.story)


if __name__ == '__main__':
    raise SystemExit(main())
