"""
ಊರ್ಮನಿ ಸುದ್ದಿ — House rules: the things you told us once
========================================================
The gap this fills is small and it costs a day every time it bites.

You say "from now on never open a weather headline with the word ಮಳೆ" or
"always credit the organiser by name on festival cards". It gets done that
morning. Three weeks later nobody remembers, the skill was never changed, and
the instruction is somewhere in a chat log that no longer exists.

A house rule is that instruction, written down where the newsroom reads it at
the start of every day, with the date you said it and the reason.

WHERE A CHANGE BELONGS
----------------------
Not everything is a house rule, and putting the wrong thing here is how the
project gets two sources of truth again:

  a NUMBER            → `tokens.Limits`, plus a decision, plus a test.
                        Durations, character budgets, loudness, slots, floors.
                        `Limits` is the only home for those (D56) and a house
                        rule that restates one will drift from it.
  a LEGAL rule        → `brand/content.py`, plus a test, plus a decision.
                        Never here: a legal guard that lives in a markdown file
                        is a guard that can be edited on a deadline (D29).
  a PLACE             → `copy.PLACE_TAGS`. One registry.
  everything else     → here. Wording, habits, preferences, the order you like
                        things done in, what to avoid on a Ganesha card, which
                        source to trust first for exam dates.

WHAT A HOUSE RULE CANNOT DO
---------------------------
It cannot switch anything off. `add()` refuses a rule that reads like a waiver
of a guard, because the entire architecture of this project rests on there
being no override flag anywhere, and a plain-text file that quietly becomes one
would be the most dangerous file in the repository.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'docs', 'HOUSE_RULES.json')
RENDERED = os.path.join(ROOT, 'docs', 'HOUSE_RULES.md')

# Where a rule applies. The newsroom reads the ones for the stop it is at, so a
# picture rule does not have to be re-read while writing copy.
SCOPES = ('desk', 'picture', 'package', 'gate', 'footage', 'greeting', 'always')

# Phrases that mean "stop checking something". A house rule is allowed to make
# the desk stricter or more particular; it is not allowed to disable a guard,
# because the guards are the only thing standing between a deadline and a
# defamation suit. If you genuinely need one changed, that is a decision with a
# number, a test and a paragraph about what breaks — not a line in a file.
WAIVER_PATTERNS = [
    re.compile(p, re.I) for p in (
        r'\b(skip|bypass|ignore|disable|turn off|switch off|suppress)\b.*'
        r'\b(check|guard|gate|validation|test|approval|sign[- ]?off|verif)',
        r'\b(no need|don.?t need|not required|optional)\b.*'
        r'\b(verified_by|source_url|approval|sign[- ]?off|licence|license|credit)',
        r'\b(allow|permit)\b.*\b(without)\b.*'
        r'\b(source|credit|licence|license|verification|approval)',
        r'\boverride\b',
        r'\bpublish (anyway|without)\b',
    )
]


class HouseRuleRefused(ValueError):
    """Raised when a rule would waive a guard rather than add one."""


@dataclass
class Rule:
    id: str
    said: str                  # what you actually asked for, in your words
    scope: str = 'always'
    why: str = ''              # the reason, so a future reader can judge it
    added: str = ''            # ISO date
    retired: str = ''          # ISO date, when it stops applying
    by: str = ''

    @property
    def live(self) -> bool:
        return not self.retired

    def to_dict(self) -> dict:
        return asdict(self)


def _load() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    try:
        with open(LEDGER, encoding='utf-8') as fh:
            data = json.load(fh)
        return data.get('rules', []) if isinstance(data, dict) else []
    except Exception:
        return []


def _save(rules: list[dict]) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'w', encoding='utf-8') as fh:
        json.dump({
            'kind': 'house_rules',
            'note': ('Things the owner asked for once. Read at the start of '
                     'every run. Numbers belong in tokens.Limits, legal rules '
                     'in brand/content.py, places in copy.PLACE_TAGS — see '
                     'brand/house.py for why.'),
            'rules': rules,
        }, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    render()


def rules(scope: str = '') -> list[Rule]:
    """Live rules, optionally for one stop. 'always' rules come back for all."""
    out = [Rule(**r) for r in _load()]
    out = [r for r in out if r.live]
    if scope:
        out = [r for r in out if r.scope in (scope, 'always')]
    return out


def looks_like_a_waiver(text: str) -> str:
    """The pattern this text matches, or '' when it is a normal rule."""
    for pat in WAIVER_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0)
    return ''


def add(said: str, scope: str = 'always', why: str = '', by: str = '') -> Rule:
    """Record a house rule. Refuses anything that reads like a waiver."""
    said = (said or '').strip()
    if not said:
        raise ValueError('a house rule needs to say something')
    if scope not in SCOPES:
        raise ValueError(f'unknown scope {scope!r}; choose from {SCOPES}')

    hit = looks_like_a_waiver(said)
    if hit:
        raise HouseRuleRefused(
            f'this reads like a waiver ({hit!r}), and a house rule cannot '
            f'switch a check off.\n\n'
            f'The guards are the only thing standing between a deadline and a '
            f'defamation suit, and the whole architecture rests on there being '
            f'no override anywhere (D29). A markdown file that quietly became '
            f'one would be the most dangerous file in this repository.\n\n'
            f'If the check is genuinely wrong, that is a DECISION: change the '
            f'code, write the entry in docs/DECISIONS.md saying what breaks '
            f'without it, and add a test. That takes an hour and it survives.')

    from .content import now
    today = f'{now():%Y-%m-%d}'
    existing = _load()
    n = sum(1 for r in existing if r['id'].startswith(today)) + 1
    rule = Rule(id=f'{today}-{n:02d}', said=said, scope=scope, why=why,
                added=today, by=by)
    existing.append(rule.to_dict())
    _save(existing)
    return rule


def retire(rule_id: str, why: str = '') -> Rule:
    """Stop applying a rule. Never deletes it — the record is the point."""
    from .content import now
    existing = _load()
    for r in existing:
        if r['id'] == rule_id:
            r['retired'] = f'{now():%Y-%m-%d}'
            if why:
                r['why'] = (r.get('why', '') + f'  · retired: {why}').strip()
            _save(existing)
            return Rule(**r)
    raise KeyError(f'no house rule {rule_id!r}')


def render() -> str:
    """Write the human-readable twin. Generated — do not edit by hand."""
    all_rules = [Rule(**r) for r in _load()]
    live = [r for r in all_rules if r.live]
    gone = [r for r in all_rules if not r.live]

    lines = [
        '# House rules',
        '',
        '_Generated from `docs/HOUSE_RULES.json` by `brand/house.py`. '
        'Do not edit by hand — use `python3 scripts/house_rule.py`._',
        '',
        'Things the owner asked for once, written down where the newsroom reads',
        'them at the start of every run. The alternative is an instruction that',
        'lives in a chat log until everybody forgets it.',
        '',
        '**A house rule cannot switch a check off.** Numbers live in',
        '`tokens.Limits`, legal rules in `brand/content.py`, places in',
        '`copy.PLACE_TAGS`. This file is for wording, habits and preferences —',
        'the things that are genuinely house style rather than contract.',
        '',
    ]
    if not live:
        lines += ['_No house rules yet._', '',
                  '```bash',
                  'python3 scripts/house_rule.py add "…" --scope desk '
                  '--why "…"',
                  '```', '']
    for scope in SCOPES:
        here = [r for r in live if r.scope == scope]
        if not here:
            continue
        lines += [f'## {scope}', '']
        for r in here:
            lines.append(f'- **{r.id}** — {r.said}')
            if r.why:
                lines.append(f'  - _why:_ {r.why}')
            if r.by:
                lines.append(f'  - _asked by:_ {r.by}')
        lines.append('')
    if gone:
        lines += ['## Retired', '',
                  'Kept, because knowing a rule was dropped and when is worth '
                  'more than a tidy file.', '']
        for r in gone:
            lines.append(f'- ~~{r.id}~~ ({r.added} → {r.retired}) — {r.said}')
            if r.why:
                lines.append(f'  - {r.why}')
        lines.append('')
    body = '\n'.join(lines)
    os.makedirs(os.path.dirname(RENDERED), exist_ok=True)
    with open(RENDERED, 'w', encoding='utf-8') as fh:
        fh.write(body)
    return body


def brief(scope: str = '') -> str:
    """The lines the newsroom prints at a stop. Empty when there are none."""
    live = rules(scope)
    if not live:
        return ''
    head = (f'HOUSE RULES ({scope})' if scope else 'HOUSE RULES')
    out = [f'  {head} — {len(live)} in force:']
    for r in live:
        out.append(f'    · [{r.id}] {r.said}')
    return '\n'.join(out)
