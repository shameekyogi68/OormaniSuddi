#!/usr/bin/env python3
"""
Which decisions are enforced, and which are only written down.
==============================================================
`docs/DECISIONS.md` carries D1..D66. `tests/` carries several hundred
assertions. Nobody has ever been able to say which decisions the tests
actually hold up — and a decision with no test behind it is a paragraph, not a
rule, however firmly it is phrased.

This reads both and writes `docs/TRACEABILITY.md`: every decision, the tests
that name it, and a list of the ones nothing enforces. That last list is the
useful output. It is not a failure — some decisions are genuinely about taste
or process and cannot be tested — but it should be a list somebody has looked
at, rather than a question nobody has asked.

    python3 docs/_build_traceability.py          # write the table
    python3 docs/_build_traceability.py --check  # non-zero if coverage dropped

Generated. Do not edit TRACEABILITY.md by hand.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS = os.path.join(ROOT, 'docs', 'DECISIONS.md')
OUT = os.path.join(ROOT, 'docs', 'TRACEABILITY.md')
SEARCH_DIRS = ('tests', 'brand', 'templates', 'scripts')

# Decisions that are deliberately not mechanically testable, with the reason.
# A decision is allowed in here only when someone has said why — an
# exemption list nobody defends is just a way to make the number look better.
UNTESTABLE = {
    'D33': 'the opening frame is the cover — a composition choice',
    'D66': 'the plate is a designed scene; "reads as a graphic, not as a bad '
           'photograph" is a judgement, and the one it replaced passed every '
           'number while looking wrong',
}

# Decisions the golden fingerprints guard without asserting.
#
# This is a WEAKER guarantee than a test and is recorded as its own category
# rather than counted as one, because the distinction is real: the golden hash
# would fail if leading stopped coming from the em, but nothing anywhere
# asserts that it does. A regression is caught; the rule is not verified. Most
# of these are pure typography and surface decisions where "the pixels did not
# move" is genuinely most of what there is to check.
GOLDEN_GUARDED = {
    'D1': 'leading from the em', 'D2': 'baseline drawing',
    'D3': 'no tracking on Kannada', 'D4': 'Latin falls back to Kannada',
    'D5': 'photographs fade their own alpha', 'D6': 'smoothstep scrim ramp',
    'D7': 'focal default (0.5, 0.42)', 'D8': 'grain is mandatory',
    'D9': 'category colour only on the rail',
    'D10': 'hairlines, square corners, no border',
    'D11': 'layouts flow content', 'D12': 'item gaps exceed line gaps',
    'D13': 'reels are full-bleed', 'D14': 'headline plus one supporting line',
    'D16': 'nothing cuts on a hard frame',
    'D24': 'translucent text on its own layer',
    'D34': 'landscape is a different typographic problem',
    'D35': 'progress bar flush to the top edge',
    'D36': 'a lower-third is a panel',
    'D38': 'landscape spends width on the type',
    'D40': 'the 4K bulletin is the same design at twice the size',
    'D64': 'brand rules are gilded, not stamped',
    'D65': 'the filmic highlight shoulder',
}


def decisions() -> list[tuple[str, str]]:
    """(number, title) for every decision heading, in file order."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    with open(DECISIONS, encoding='utf-8') as fh:
        for line in fh:
            m = re.match(r'^##\s+(D\d+)\s*[·•\-—]\s*(.+?)\s*$', line)
            if not m:
                continue
            num, title = m.group(1), m.group(2)
            # D29/D30/D31 were each duplicated by an old renumber — one
            # design decision and one legal decision sharing a number, which
            # made "see D29" ambiguous in AGENTS.md, CLAUDE.md and the code.
            # The design three are now D64-D66. This guard stays so a future
            # duplicate is dropped from the table rather than double-counted.
            if num in seen:
                continue
            seen.add(num)
            out.append((num, title))
    return sorted(out, key=lambda r: int(r[0][1:]))


def mentions() -> dict[str, set[str]]:
    """Every file that names a decision number, by number."""
    hits: dict[str, set[str]] = {}
    pat = re.compile(r'\bD(\d{1,3})\b')
    for d in SEARCH_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != '__pycache__']
            for name in filenames:
                if not name.endswith(('.py', '.json', '.md')):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, encoding='utf-8') as fh:
                        body = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                rel = os.path.relpath(path, ROOT)
                for m in pat.finditer(body):
                    hits.setdefault(f'D{m.group(1)}', set()).add(rel)
    return hits


def build() -> tuple[str, list[str]]:
    rows = decisions()
    hits = mentions()
    tested, untested, golden = [], [], []
    lines = [
        '# Decision → enforcement',
        '',
        '_Generated by `docs/_build_traceability.py`. Do not edit._',
        '',
        'A decision with no test behind it is a paragraph, not a rule. This is',
        'the list of which is which. Some entries are honestly untestable —',
        'those carry a reason rather than a test.',
        '',
    ]
    for num, title in rows:
        files = sorted(hits.get(num, set()))
        in_tests = [f for f in files if f.startswith('tests/')]
        in_code = [f for f in files if not f.startswith('tests/')]
        if in_tests:
            tested.append(num)
        elif num in GOLDEN_GUARDED:
            golden.append(num)
        elif num not in UNTESTABLE:
            untested.append(num)
        lines.append(f'## {num} · {title}')
        lines.append('')
        if in_tests:
            lines.append(f'- **Tested by:** '
                         + ', '.join(f'`{f}`' for f in in_tests))
        elif num in GOLDEN_GUARDED:
            lines.append(
                f'- **Regression-guarded by the golden fingerprints** '
                f'({GOLDEN_GUARDED[num]}). A change here moves pixels and '
                f'`tests/test_golden.py` fails. Note this catches a '
                f'regression; it does not assert the rule.')
        elif num in UNTESTABLE:
            lines.append(f'- **Not mechanically testable:** {UNTESTABLE[num]}')
        else:
            lines.append('- ⚠️ **No test names this decision.** Either write '
                         'one, or add it to `GOLDEN_GUARDED` / `UNTESTABLE` '
                         'with a reason.')
        if in_code:
            lines.append(f'- Enforced in: ' + ', '.join(f'`{f}`' for f in in_code))
        lines.append('')

    total = len(rows)
    summary = [
        '## Coverage',
        '',
        f'- **{len(tested)}/{total}** decisions are named by at least one test',
        f'- **{len(golden)}** are regression-guarded by the golden '
        f'fingerprints — a change moves pixels and the hash fails, which '
        f'catches a regression without asserting the rule',
        f'- **{len(UNTESTABLE)}** are recorded as not mechanically testable, '
        f'each with a reason',
        f'- **{len(untested)} are enforced by nothing**'
        + (': ' + ', '.join(untested) if untested else ''),
        '',
    ]
    lines[7:7] = summary
    return '\n'.join(lines) + '\n', untested


def main() -> int:
    body, untested = build()
    check = '--check' in sys.argv
    if not check:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write(body)
        print(f'✓ {os.path.relpath(OUT, ROOT)}')
    n = len(decisions())
    tested = n - len(untested) - len(UNTESTABLE) - len(GOLDEN_GUARDED)
    print(f'  {n} decisions · {tested} tested · {len(GOLDEN_GUARDED)} '
          f'golden-guarded · {len(UNTESTABLE)} untestable by design · '
          f'{len(untested)} unenforced')
    if untested:
        print(f'  unenforced: {", ".join(untested)}')
        if check:
            print('\n  A decision enforced by nothing is a paragraph, not a '
                  'rule. Write a test that names the number, or add it to '
                  'GOLDEN_GUARDED / UNTESTABLE with a reason somebody would '
                  'defend.', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
