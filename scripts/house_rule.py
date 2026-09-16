#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — tell the newsroom something once, and have it stick.
====================================================================

    python3 scripts/house_rule.py add "ಗಣೇಶ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ" \
        --scope picture --why "organisers reshare when credited" --by Gautam

    python3 scripts/house_rule.py list
    python3 scripts/house_rule.py list --scope desk
    python3 scripts/house_rule.py retire 2026-09-16-01 --why "no longer true"
    python3 scripts/house_rule.py where "reels should be 30 seconds"

`where` is the one to reach for when you are not sure. It reads what you want
changed and tells you which of the four places it belongs in, because putting a
number here instead of in tokens.Limits is how this project ends up with two
answers to the same question again.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import house   # noqa: E402


def cmd_add(a) -> int:
    try:
        r = house.add(a.text, scope=a.scope, why=a.why, by=a.by)
    except house.HouseRuleRefused as e:
        print(f'✗ refused.\n\n{e}\n', file=sys.stderr)
        return 1
    except ValueError as e:
        print(f'✗ {e}', file=sys.stderr)
        return 1
    print(f'✓ {r.id}  [{r.scope}]  {r.said}')
    print(f'  Live from now on. The newsroom prints it at the {r.scope} stop.')
    print(f'  docs/HOUSE_RULES.md regenerated.')
    return 0


def cmd_list(a) -> int:
    live = house.rules(a.scope or '')
    if not live:
        print('\n  No house rules' + (f' for {a.scope}' if a.scope else '')
              + '.\n\n  python3 scripts/house_rule.py add "…" --scope desk\n')
        return 0
    print()
    for r in live:
        print(f'  {r.id}  [{r.scope}]')
        print(f'      {r.said}')
        if r.why:
            print(f'      why: {r.why}')
    print()
    return 0


def cmd_retire(a) -> int:
    try:
        r = house.retire(a.id, a.why)
    except KeyError as e:
        print(f'✗ {e}', file=sys.stderr)
        return 1
    print(f'✓ {r.id} retired. Kept in the file — knowing a rule was dropped '
          f'and when is worth more than a tidy list.')
    return 0


# Which of the four places a change belongs in. Deliberately blunt: the cost of
# a wrong answer here is two sources of truth, which is the failure this whole
# project is arranged to prevent.
NUMBERY = re.compile(
    r'\b\d+\s*(s|sec|second|seconds|ms|char|characters|px|kb|mb|lufs|dbtp|%)\b'
    r'|\b(how many|at most|no more than|maximum|minimum|cap|limit|target)\b',
    re.I)
LEGALLY = re.compile(
    r'\b(defam|allegation|ಆರೋಪ|POCSO|minor|juvenile|victim|BNS|guilt|'
    r'convict|grievance|IT Rules|licence|license|copyright)\b', re.I)
PLACEY = re.compile(
    r'\b(taluk|town|village|place name|hashtag for|cover\w* (the )?area)\b',
    re.I)


def cmd_where(a) -> int:
    text = a.text
    print()
    waiver = house.looks_like_a_waiver(text)
    if waiver:
        print(f'  ⚠️  This reads like a waiver ({waiver!r}).')
        print('      A house rule cannot switch a check off. If the check is')
        print('      genuinely wrong, change the code, write the decision, add')
        print('      a test. See docs/DECISIONS.md D29.\n')
        return 1
    if LEGALLY.search(text):
        print('  → brand/content.py, plus a test, plus a decision.')
        print('      Legal rules do not live in a markdown file, because a')
        print('      markdown file can be edited on a deadline. D29.\n')
        return 0
    if NUMBERY.search(text):
        print('  → brand/tokens.py :: Limits, plus a decision, plus a test.')
        print('      Numbers live in exactly one place (D56). A house rule')
        print('      restating one drifts from it within a month.\n')
        return 0
    if PLACEY.search(text):
        print('  → brand/copy.py :: PLACE_TAGS. One registry of places.\n')
        return 0
    print('  → a house rule. This is the right place for it:\n')
    print(f'      python3 scripts/house_rule.py add "{text}" \\')
    print('          --scope desk --why "…"\n')
    print(f'      scopes: {", ".join(house.SCOPES)}\n')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add', help='record a rule that applies from now on')
    a.add_argument('text')
    a.add_argument('--scope', default='always', choices=house.SCOPES)
    a.add_argument('--why', default='')
    a.add_argument('--by', default='')
    a.set_defaults(fn=cmd_add)

    l = sub.add_parser('list', help='what is in force')
    l.add_argument('--scope', default='', choices=('',) + house.SCOPES)
    l.set_defaults(fn=cmd_list)

    r = sub.add_parser('retire', help='stop applying one')
    r.add_argument('id')
    r.add_argument('--why', default='')
    r.set_defaults(fn=cmd_retire)

    w = sub.add_parser('where', help='which of the four places does this belong')
    w.add_argument('text')
    w.set_defaults(fn=cmd_where)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    raise SystemExit(main())
