#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the team lead's board: which agents are due, and why. D89.

    python3 scripts/dispatch.py                      # today's plan, in waves
    python3 scripts/dispatch.py --day 2026-09-24     # another day
    python3 scripts/dispatch.py --json               # for tools

    # every agent files its report this way — the receipt is what stops the
    # same work being done twice, and what makes an edit due for re-checking
    python3 scripts/dispatch.py receipt --agent fact-checker \\
        --edition editions/2026-09-25.json --story 3 --verdict PASS --file report.md
    … --file - reads the report from stdin

    # wired into .claude/settings.json; not for typing
    python3 scripts/dispatch.py hook session         # proactive briefing
    python3 scripts/dispatch.py hook post-bash       # reactive, after a command

What no agent may do is listed under "needs a person": verified_by, the
sign-off, uploading, answering a complaint. The plan names them; it never
does them.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from brand import dispatch as D                          # noqa: E402

# Commands after which the state can have changed enough to react to.
REACT_ON = ('render.py', 'fact_check.py', 'correction.py', 'draft_edition.py',
            'verify.py', 'fetch_daily_news.py')
QUIET = ('--check', '--describe', '--schema', '--help', 'status', '--show')


def ran_pipeline(cmd: str) -> bool:
    """True when the command RUNS a pipeline script — not when one is merely
    mentioned in a heredoc, a grep, or a file being written. Only the first
    line counts: a heredoc body is data."""
    first = (cmd or '').split('\n', 1)[0]
    for part in re.split(r'&&|\|\||;|\|', first):
        m = re.match(r'\s*(?:\S+=\S+\s+)*python3?\s+(?:-\S+\s+)*(\S+\.py)(.*)', part)
        if not m:
            continue
        script, rest = os.path.basename(m.group(1)), m.group(2)
        if script in REACT_ON and not any(q in rest.split() for q in QUIET):
            return True
    return False


def _hook_post_bash() -> int:
    """Reactive: after a command that changes the newsroom, say what is now
    due. Exit 2 puts the message in front of the assistant; 0 is silence."""
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (event.get('tool_input') or {}).get('command', '')
    if not ran_pipeline(cmd):
        return 0
    p = D.plan(include_ops=False)
    react = [t for t in p.tasks if t.kind == 'reactive']
    if not react:
        return 0
    p.tasks = react
    print('REACTIVE — the command just changed what is due:\n' + D.brief(p),
          file=sys.stderr)
    return 2


def _hook_session() -> int:
    """Proactive: the briefing a session starts with. stdout is context."""
    try:
        p = D.plan()
    except Exception as e:                       # a briefing must never block
        print(f'Team plan unavailable: {type(e).__name__}: {e}')
        return 0
    print(D.brief(p))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='which agents are due, and why')
    sub = ap.add_subparsers(dest='cmd')
    ap.add_argument('--day')
    ap.add_argument('--json', action='store_true')
    r = sub.add_parser('receipt', help='file an agent report')
    r.add_argument('--agent', required=True)
    r.add_argument('--edition', required=True,
                   help='editions/X.json, out/X, or a YYYY-MM-DD day')
    r.add_argument('--story', type=int, default=0)
    r.add_argument('--verdict', required=True)
    r.add_argument('--file', default='-')
    h = sub.add_parser('hook')
    h.add_argument('which', choices=('session', 'post-bash'))
    a = ap.parse_args(argv)

    if a.cmd == 'hook':
        return _hook_session() if a.which == 'session' else _hook_post_bash()
    if a.cmd == 'receipt':
        body = (sys.stdin.read() if a.file == '-'
                else open(a.file, encoding='utf-8').read())
        path = D.write_receipt(a.agent, a.edition, a.verdict, body, a.story)
        print(f'✓ receipt filed: {os.path.relpath(path, ROOT)}')
        return 0
    p = D.plan(a.day)
    print(json.dumps(p.to_dict(), ensure_ascii=False, indent=1) if a.json
          else D.brief(p, limit=200))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
