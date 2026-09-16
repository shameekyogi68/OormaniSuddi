#!/usr/bin/env python3
"""Archive a day's published record, then delete throwaway media.

Keeps: editions/{date}.json, APPROVAL.md, copy, schedule, review frames,
and any evergreen stock the editor already copied.

Deletes: out/{date}/ renders and leftover assets/daily/{date}/ frames.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


KEEP_NAMES = (
    'APPROVAL.md', 'APPROVAL_FOOTAGE.md', 'MASTER_COPY.md',
    'schedule.txt', 'schedule.json',
)


def main() -> int:
    ap = argparse.ArgumentParser(description='Archive then clean one edition day.')
    ap.add_argument('date', help='YYYY-MM-DD')
    args = ap.parse_args()
    date = args.date
    out = os.path.join(ROOT, 'out', date)
    daily = os.path.join(ROOT, 'assets', 'daily', date)
    edition = os.path.join(ROOT, 'editions', f'{date}.json')
    dest = os.path.join(ROOT, 'archive', date)
    os.makedirs(dest, exist_ok=True)

    if os.path.exists(edition):
        shutil.copy2(edition, os.path.join(dest, os.path.basename(edition)))
        print(f'  kept {edition}')
    else:
        print(f'  ! no {edition} — nothing to archive as the editorial record')

    if os.path.isdir(out):
        review = os.path.join(out, '_review')
        if os.path.isdir(review):
            shutil.copytree(review, os.path.join(dest, '_review'), dirs_exist_ok=True)
        for name in os.listdir(out):
            if name in KEEP_NAMES or name.endswith('_copy.txt') or name.endswith('_copy.json'):
                shutil.copy2(os.path.join(out, name), os.path.join(dest, name))
        shutil.rmtree(out, ignore_errors=True)
        print(f'  archived copy/approval/review → {dest}')
        print(f'  deleted {out}')
    else:
        print(f'  · no {out}')

    if os.path.isdir(daily):
        print(f'  leftover daily frames in {daily} — copy evergreen ones to '
              f'assets/stock/ first, then this folder can be removed.')
        # Do not auto-delete daily frames: a generic harbour shot is stock.
        # The editor / Stop close copies first, then:
        # shutil.rmtree(daily)

    print(f'✓ archive/{date}/ holds the published record. Edition JSON is kept.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
