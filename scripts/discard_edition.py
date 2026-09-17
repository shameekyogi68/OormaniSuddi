#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — undo a day that never got posted.
====================================================
The mirror of archive_edition.py: that one keeps the edition JSON and the
published record, and deletes only throwaway media. This one is for a day
that was drafted, maybe rendered, and then abandoned before anyone signed it
off — "Stop" in the Start / approve / Stop chat workflow (see AGENTS.md).
Everything about the day is undone: the edition JSON, the render, the
checklist. A day that was actually signed off is never touched by this
script; it refuses and points at archive_edition.py instead.

    python3 scripts/discard_edition.py 2026-09-17
    python3 scripts/discard_edition.py 2026-09-17 --force-assets
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.review import is_signed  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('date', help='YYYY-MM-DD')
    ap.add_argument('--force-assets', action='store_true',
                    help='also delete assets/daily/{date} — only after '
                         'copying anything worth keeping into assets/stock/ '
                         'by hand; nothing there is deleted without this flag')
    args = ap.parse_args()
    date = args.date

    edition = os.path.join(ROOT, 'editions', f'{date}.json')
    out = os.path.join(ROOT, 'out', date)
    daily = os.path.join(ROOT, 'assets', 'daily', date)
    checklist = os.path.join(ROOT, 'inbox', f'checklist_{date}.md')

    if os.path.isdir(out) and is_signed(out):
        print(f'✗ out/{date} is signed off — this day was published. '
              f'discard_edition.py is only for a day that never got that '
              f'far. Use scripts/archive_edition.py {date} instead.',
              file=sys.stderr)
        return 1

    removed = []
    if os.path.exists(edition):
        os.remove(edition)
        removed.append(f'editions/{date}.json')
    if os.path.exists(checklist):
        os.remove(checklist)
        removed.append(f'inbox/checklist_{date}.md')
    if os.path.isdir(out):
        shutil.rmtree(out)
        removed.append(f'out/{date}/')

    if os.path.isdir(daily):
        if args.force_assets:
            shutil.rmtree(daily)
            removed.append(f'assets/daily/{date}/')
        else:
            names = sorted(os.listdir(daily))
            print(f'  assets/daily/{date}/ still has {len(names)} file(s): '
                 f'{", ".join(names[:6])}{"…" if len(names) > 6 else ""}')
            print(f'  A generic scene in there is worth keeping — copy it to '
                 f'assets/stock/ first. Once you have, or if none of it is '
                 f'worth keeping:')
            print(f'    python3 scripts/discard_edition.py {date} --force-assets')

    if not removed:
        print(f'· nothing to discard for {date}')
        return 0

    print(f'✓ discarded: {", ".join(removed)}')
    print('  assets/stock/ was not touched — nothing evergreen was removed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
