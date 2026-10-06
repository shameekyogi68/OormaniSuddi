#!/usr/bin/env python3
"""Archive a day's published record, then delete throwaway media.

Keeps: editions/{date}.json, APPROVAL.md, SIGNOFF.json, review_report.json,
PROVENANCE.json, copy, schedule and review frames. The day's pictures in
assets/daily/{date}/ are left for the editor: a real photograph is the
channel's own record and is never deleted by a script.

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
    'schedule.txt', 'schedule.json', 'REACH.md',
    # The evidence of HOW it was cleared, not only that it was. Six months
    # later "who signed this and what did the machine actually check" is the
    # question, and prose in a chat log does not answer it.
    'SIGNOFF.json', 'review_report.json', 'PROVENANCE.json',
    'run_report.md', 'narration_audit.json',
)


def _keep(name: str) -> bool:
    """Copy that has to survive Stop: captions, town forwards, Facebook posts.

    The heavy renders are deleted. The files a phone posts from are not —
    `forward_*.txt` exists so nobody copies the wrong town out of
    MASTER_COPY.md at 20:00. D106.
    """
    if name in KEEP_NAMES:
        return True
    if name.startswith('facebook_group_') and name.endswith('.txt'):
        return True
    if name.startswith('forward_') and name.endswith('.txt'):
        return True
    return name.endswith(('_copy.txt', '_copy.json', '_caption.txt', '_whatsapp.txt'))


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
            from brand.content import http_url
            if not http_url(url):
                row['status'] = 'skipped (not an http URL)'
                print(f'  ! {url} — not an http URL, not sent')
                rows.append(row)
                continue
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
    from brand.content import ContentError, edition_day, path_inside
    try:
        date = edition_day(args.date)
        out = path_inside(ROOT, 'out', date)
        daily = path_inside(ROOT, 'assets', 'daily', date)
        edition = path_inside(ROOT, 'editions', f'{date}.json')
        dest = path_inside(ROOT, 'archive', date)
    except ContentError as e:
        print(f'✗ {e}', file=sys.stderr)
        return 2
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
            if _keep(name):
                shutil.copy2(os.path.join(out, name), os.path.join(dest, name))
        shutil.rmtree(out, ignore_errors=True)
        print(f'  archived copy/approval/review → {dest}')
        print(f'  deleted {out}')
    else:
        print(f'  · no {out}')

    if os.path.isdir(daily):
        print(f'  pictures left in {daily} — keep any real photograph the '
              f'editor sent (it is our own record), then this folder can be '
              f'removed by hand.')
        # Never auto-deleted: a real photograph is not a render. There is no
        # stock library to promote AI frames into any more (D92).

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
