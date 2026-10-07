#!/usr/bin/env python3
"""Turn unittest failures in a log into GitHub annotations.

A red run whose reason is only in the raw log is a red run nobody reads: the
contract failed on every push for three weeks (D114). Annotations show on the
run page, in the API, and without signing in.

    python -m unittest … 2>&1 | tee test.log
    python .github/annotate_failures.py test.log
"""
from __future__ import annotations

import re
import sys


def blocks(text: str):
    """(test name, body) for every FAIL: / ERROR: block in unittest output."""
    for m in re.finditer(r'^(FAIL|ERROR): (.+?)\n-{20,}\n(.*?)(?=^={20,}|^-{20,}\nRan |\Z)',
                         text, re.S | re.M):
        yield f'{m[1]}: {m[2].strip()}', m[3].strip()


def escape(s: str) -> str:
    return s.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def main(path: str) -> int:
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    found = 0
    for name, body in blocks(text):
        # The end of a traceback is the part that says what went wrong.
        tail = '\n'.join(body.splitlines()[-12:])
        print(f'::error title={escape(name)[:200]}::{escape(tail)[:3000]}')
        found += 1
    if not found and re.search(r'^FAILED', text, re.M):
        print('::error title=unittest failed::' + escape(text[-3000:]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
