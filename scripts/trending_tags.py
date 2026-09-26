#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the morning trend sheet. D86.

    python3 scripts/trending_tags.py            # fetch today's trends
    python3 scripts/trending_tags.py --show     # print what is held

Reads Google Trends' daily feed for Karnataka, then India, and writes
inbox/trends_<date>.json. Items the trend-scout agent added by hand (anything
whose `source` is not "google-trends") are kept across re-runs, so the agent's
Instagram / YouTube findings survive the 07:00 refresh.

Each item:
    {"term": "ಬಿಗ್ ಬಾಸ್ ಕನ್ನಡ", "tag": "BiggBossKannada",
     "match": ["ಬಿಗ್ ಬಾಸ್", "Bigg Boss"], "platforms": ["instagram","youtube"],
     "scope": "karnataka", "traffic": "20000+", "rank": 3,
     "source": "google-trends", "news": ["…headline…"]}

`match` is what a story must SAY for the tag to go on it (brand/trends.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import trends as T                           # noqa: E402

FEEDS = (('karnataka', 'https://trends.google.com/trending/rss?geo=IN-KA'),
         ('india', 'https://trends.google.com/trending/rss?geo=IN'))
NS = {'ht': 'https://trends.google.com/trending/rss'}


def _tag(term: str) -> str:
    """A hashtag body: words joined, each Latin word capitalised."""
    parts = re.findall(r'[A-Za-z0-9]+|[ಀ-೿]+', term)
    return ''.join(p[:1].upper() + p[1:] if p.isascii() else p for p in parts)


def _fetch(scope: str, url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    out = []
    for rank, item in enumerate(root.iter('item'), 1):
        term = (item.findtext('title') or '').strip()
        # Our readers search in Kannada and English. A trend in another
        # script is somebody else's audience.
        if not term or not _tag(term):
            continue
        news = [(n.findtext('ht:news_item_title', '', NS) or '').strip()
                for n in item.findall('ht:news_item', NS)]
        out.append({
            'term': term, 'tag': _tag(term),
            'match': [term] + ([w for w in term.split() if len(w) >= 4]
                               if len(term.split()) > 1 else []),
            'platforms': ['instagram', 'youtube'],
            'scope': scope, 'rank': rank, 'source': 'google-trends',
            'traffic': (item.findtext('ht:approx_traffic', '', NS) or '').strip(),
            'news': [n for n in news if n][:3],
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=date.today().isoformat())
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args(argv)
    path = T.path_for(a.date)

    kept = []
    if os.path.exists(path):
        with open(path, encoding='utf-8') as fh:
            kept = [i for i in json.load(fh).get('items', [])
                    if i.get('source') != 'google-trends']
    if a.show:
        for i in T.load(a.date):
            print(f"{i.get('scope', ''):10} #{i['tag']:30} {i.get('traffic', '')}"
                  f"  ← {', '.join(i.get('match', []))}")
        return 0

    items, errors = [], []
    seen = {i['tag'].lower() for i in kept}
    for scope, url in FEEDS:
        try:
            for it in _fetch(scope, url):
                if it['tag'].lower() not in seen:
                    seen.add(it['tag'].lower())
                    items.append(it)
        except Exception as e:                 # a dead feed is a note, not a crash
            errors.append(f'{scope}: {e}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'date': a.date, 'fetched_at': datetime.now().isoformat(
            timespec='seconds'), 'errors': errors, 'items': kept + items},
            fh, ensure_ascii=False, indent=1)
    print(f'trends: {len(items)} from Google Trends, {len(kept)} kept from the '
          f'scout → {os.path.relpath(path, ROOT)}')
    for e in errors:
        print('  feed failed —', e)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
