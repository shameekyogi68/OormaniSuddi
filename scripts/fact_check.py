#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — fact-check an edition against its sources, BEFORE render. D84.

    python3 scripts/fact_check.py editions/2026-09-24.json
    python3 scripts/fact_check.py editions/2026-09-24.json --offline

Fetches and keeps the text of every source_url (inbox/sources/), then checks
every figure and name in every published line — headline, reel_line, hook,
deck, points, takeaway, narration — against it. Prints the ledger and exits 1
when a figure is not in the source. The gate (FACT-01) blocks the same thing,
so fixing it here costs a line; fixing it there costs a re-render.

A figure the source spells differently is proved in
inbox/factcheck/<stem>.json with the exact source sentence:

    {"claims": [{"token": "3",
                 "quote": "Udupi, Dakshina Kannada and Uttara Kannada",
                 "url": "https://…"}]}

The quote is checked against the kept source. It is evidence, not a waiver.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.content import Edition                      # noqa: E402
from brand import factcheck as F                       # noqa: E402


def fetch_missing(edition: Edition) -> tuple[int, list[str]]:
    from scripts.fetch_daily_news import fetch_body
    got, failed, wrong = 0, [], []
    tips = F._tip_bodies()
    for st in edition.stories:
        for url in (u.strip() for u in st.source_urls if (u or '').strip()):
            if os.path.exists(F.cache_path(url)):
                continue
            body = fetch_body(url)
            if not body and url in tips:
                body = tips[url]
            if body and not F.carries(st, body):
                wrong.append(url)       # never kept: it is not evidence
            elif body:
                F.save_source(url, body)
                got += 1
            else:
                failed.append(url)
    return got, failed, wrong


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('edition')
    ap.add_argument('--offline', action='store_true',
                    help='use only sources already kept; fetch nothing')
    a = ap.parse_args(argv)

    ed = Edition.load(a.edition)
    if not a.offline:
        got, failed, wrong = fetch_missing(ed)
        print(f'sources: {got} fetched and kept in inbox/sources/')
        for u in wrong:
            print(f'  BLOCK  {u}\n         serves a page that does not carry '
                  f'this story (listing page, or a URL nobody published). '
                  f'Find the real article.')
        for u in failed:
            print(f'  could not fetch {u} — open it, paste the article into '
                  f'{os.path.relpath(F.cache_path(u), ROOT)} (URL on line 1)')
    results = F.check_edition(ed, a.edition)
    print()
    print(F.report(results))
    blocks = sum(len(r.figures) for r in results if r.state != 'mismatch')
    unchecked = sum(1 for r in results if r.state == 'uncheckable')
    print()
    print(f'{blocks} figure(s) not in the source · {unchecked} story(ies) '
          f'could not be checked')
    wrong_n = sum(1 for r in results if r.state == 'mismatch')
    if not a.offline:
        wrong_n += len(wrong)
    if wrong_n:
        print(f'{wrong_n} source(s) do not carry their story')
    return 1 if (blocks or wrong_n) else 0


if __name__ == '__main__':
    raise SystemExit(main())
