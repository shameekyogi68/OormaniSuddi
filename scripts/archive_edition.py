#!/usr/bin/env python3
"""Archive a day's published record, then delete throwaway media.

Keeps: editions/{date}.json, APPROVAL.md, SIGNOFF.json, review_report.json,
PROVENANCE.json, copy, schedule, review frames, and any evergreen stock the
editor already copied.

Deletes: out/{date}/ renders and leftover assets/daily/{date}/ frames.

    python3 scripts/archive_edition.py 2026-09-16
    python3 scripts/archive_edition.py 2026-09-16 --snapshot

`--snapshot` asks the Wayback Machine to keep a copy of every source URL the
edition cited, and records what came back in sources.json. Web pages change and
disappear; a story disputed in March rests on a page that may not say in March
what it said in November. This is opt-in on purpose — it is an outbound request
to a third party about pages you read, so it is a decision rather than a
default.
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
    # The evidence of HOW it was cleared, not only that it was. Six months
    # later "who signed this and what did the machine actually check" is the
    # question, and prose in a chat log does not answer it.
    'SIGNOFF.json', 'review_report.json', 'PROVENANCE.json',
    'run_report.md', 'narration_audit.json',
)


def snapshot_sources(date: str, dest: str) -> None:
    """Ask the Wayback Machine to keep a copy of every source this day cited.

    Not a guarantee — the service can decline, rate-limit, or be blocked by the
    publisher's robots policy. Whatever happens is written down, including the
    failures, because "we tried and it refused" is itself the record.
    """
    import json
    import urllib.request
    import urllib.error

    edition = os.path.join(ROOT, 'editions', f'{date}.json')
    if not os.path.exists(edition):
        print('  · no edition JSON — nothing to snapshot')
        return
    with open(edition, encoding='utf-8') as fh:
        data = json.load(fh)

    rows = []
    seen = set()
    for i, st in enumerate(data.get('stories', []), 1):
        for url in st.get('source_urls', []) or []:
            if not url or url in seen:
                continue
            seen.add(url)
            row = {'story': i, 'url': url, 'headline': st.get('headline', '')[:80]}
            try:
                req = urllib.request.Request(
                    'https://web.archive.org/save/' + url,
                    headers={'User-Agent': 'OormaniSuddi-newsroom/1.0 '
                                           '(local Kannada news; archiving own citations)'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    row['snapshot'] = resp.geturl()
                    row['status'] = 'saved'
                print(f'  ✓ {url}')
            except urllib.error.HTTPError as e:
                row['status'] = f'refused ({e.code})'
                print(f'  ! {url} — refused ({e.code})')
            except Exception as e:
                row['status'] = f'failed ({type(e).__name__})'
                print(f'  ! {url} — {type(e).__name__}')
            rows.append(row)

    if not rows:
        print('  · no source URLs (own reporting?) — nothing to snapshot')
        return
    out = os.path.join(dest, 'sources.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump({'date': date, 'sources': rows}, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    ok = sum(1 for r in rows if r.get('status') == 'saved')
    print(f'  {ok}/{len(rows)} sources snapshotted → archive/{date}/sources.json')


def main() -> int:
    ap = argparse.ArgumentParser(description='Archive then clean one edition day.')
    ap.add_argument('date', help='YYYY-MM-DD')
    ap.add_argument('--snapshot', action='store_true',
                    help='ask the Wayback Machine to keep a copy of every '
                         'source URL this edition cited')
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

    if args.snapshot:
        print('  snapshotting sources…')
        snapshot_sources(date, dest)
    else:
        print('  · sources not snapshotted. --snapshot asks the Wayback '
              'Machine to keep a copy, which is worth it on anything '
              'contentious.')

    print(f'✓ archive/{date}/ holds the published record. Edition JSON is kept.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
