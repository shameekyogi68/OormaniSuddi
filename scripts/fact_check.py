#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — fact-check an edition against its sources, BEFORE render. D84, D92.

    python3 scripts/fact_check.py editions/2026-09-24.json

Offline. Nothing is fetched: the source of every story is the text the editor
pasted, kept in inbox/sources/ by `scripts/intake.py source` (D92). This
checks every figure and name in every published line — headline, reel_line,
hook, deck, points, takeaway, narration — against that text. Prints the
ledger and exits 1 when a figure is not in the source, or when the kept text
does not carry its story. The gate (FACT-01) blocks the same thing, so fixing
it here costs a line; fixing it there costs a re-render.

A source_url with no kept text is listed with the command that keeps it:

    pbpaste | python3 scripts/intake.py source --url https://…

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


def kept_but_wrong(edition: Edition) -> list[str]:
    """Kept source files that do not carry their story — a paste of the wrong
    article. Never evidence."""
    wrong = []
    for st in edition.stories:
        for url in (u.strip() for u in st.source_urls if (u or '').strip()):
            path = F.cache_path(url)
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf-8') as fh:
                body = fh.read()
            if not F.carries(st, body):
                wrong.append(url)
    return wrong


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('edition')
    ap.add_argument('--offline', action='store_true',
                    help='accepted for old habits; the check is always offline')
    a = ap.parse_args(argv)

    ed = Edition.load(a.edition)
    wrong = kept_but_wrong(ed)
    for u in wrong:
        print(f'  BLOCK  {os.path.relpath(F.cache_path(u), ROOT)} ({u})\n'
              f'         does not carry this story — the wrong article was '
              f'pasted. Paste the right one.')
    results = F.check_edition(ed, a.edition)
    print()
    print(F.report(results))
    blocks = sum(len(r.figures) for r in results if r.state != 'mismatch')
    unchecked = sum(1 for r in results if r.state == 'uncheckable')
    print()
    print(f'{blocks} figure(s) not in the source · {unchecked} story(ies) '
          f'could not be checked')
    for r in results:
        for u in r.missing_sources:
            print(f'  no kept text for {u}\n'
                  f'         pbpaste | python3 scripts/intake.py source '
                  f'--url {u}')
    wrong_n = sum(1 for r in results if r.state == 'mismatch') + len(wrong)
    if wrong_n:
        print(f'{wrong_n} source(s) do not carry their story')
    return 1 if (blocks or wrong_n) else 0


if __name__ == '__main__':
    raise SystemExit(main())
