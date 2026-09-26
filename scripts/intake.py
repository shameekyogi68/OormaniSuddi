#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — paste-first intake. D92.
=======================================
News comes in because the editor pasted it. Nothing is scraped, nothing runs
on a schedule, nothing drafts a story on its own. The workflow:

  1. The editor pastes the news copy (an article, a press release, their own
     notes) and says what to make of it — which format each story runs in
     (`segment`: speed · saara · mukhya), and for a ಮುಖ್ಯ ಸುದ್ದಿ whether a
     real photograph is coming or a picture should be generated.

  2. Keep the pasted text as the story's source, so the fact desk checks
     every figure against exactly what we were given:

         pbpaste | python3 scripts/intake.py source --url https://… --outlet Udayavani
         python3 scripts/intake.py source --file notes.txt        # own reporting

     With --url it lands where FACT-01/FACT-03 look it up from the story's
     source_urls (inbox/sources/<digest>.txt). Without one it is kept as
     inbox/sources/own_<digest>.txt.

  3. Write editions/YYYY-MM-DD.json, then check nothing in it already ran:

         python3 scripts/intake.py seen editions/2026-09-27.json

     Exit 1 when a story repeats an earlier day's source URL and is not
     marked `follows_up` (DUP-01). A headline that merely reads like an
     earlier one is printed for the editor to judge.

  4. python3 scripts/fact_check.py editions/2026-09-27.json — offline, against
     the pasted text. A person still opens the link and signs `verified_by`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import intake as I                           # noqa: E402


def cmd_source(a) -> int:
    if a.file:
        with open(a.file, encoding='utf-8') as fh:
            text = fh.read()
    else:
        if sys.stdin.isatty():
            print('paste the source text, then Ctrl-D:', file=sys.stderr)
        text = sys.stdin.read()
    try:
        path = I.save_pasted(text, url=a.url or '', outlet=a.outlet or '')
    except ValueError as e:
        print(f'  ✗ {e}', file=sys.stderr)
        return 2
    print(os.path.relpath(path, ROOT) if path.startswith(ROOT) else path)
    return 0


def _edition_day(data: dict, path: str) -> dt.date:
    raw = data.get('date')
    if raw:
        try:
            from brand.content import parse_dt
            return parse_dt(raw).date()
        except Exception:
            pass
    m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(path))
    if m:
        return dt.date.fromisoformat(m.group(1))
    return dt.date.today()


def cmd_seen(a) -> int:
    with open(a.edition, encoding='utf-8') as fh:
        data = json.load(fh)
    day = _edition_day(data, a.edition)
    root = a.root or ROOT
    refused = 0
    for i, st in enumerate(data.get('stories', []), 1):
        reasons = I.published_before(st, day, root=root)
        head = st.get('headline', '')
        if not reasons:
            print(f'{i}. {head}\n   new')
            continue
        follow = (st.get('follows_up') or '').strip()
        blocking = I.url_repeat(reasons) and not follow
        refused += blocking
        print(f'{i}. {head}')
        for r in reasons:
            print(f'   {"REFUSE" if blocking else "CHECK "} {r}')
        if follow:
            print(f'   follows_up {follow} — say what is NEW, or drop it')
        elif blocking:
            print('   already published. Drop it, or mark follows_up with '
                  'the earlier date AND a new fact (D72, DUP-01).')
    print()
    print(f'{refused} story(ies) already published' if refused
          else 'nothing in this edition ran before')
    return 1 if refused else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description='Paste-first intake: keep a pasted source, or check an '
                    'edition for stories that already ran (D92).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('source', help='keep pasted source text for the fact desk')
    s.add_argument('--url', default='', help="the article's URL, if it has one")
    s.add_argument('--outlet', default='', help='the publisher, e.g. Udayavani')
    s.add_argument('--file', default='', help='read from a file instead of stdin')
    s.set_defaults(fn=cmd_source)
    n = sub.add_parser('seen', help='was any story in this edition published before?')
    n.add_argument('edition')
    n.add_argument('--root', default='', help=argparse.SUPPRESS)
    n.set_defaults(fn=cmd_seen)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    raise SystemExit(main())
