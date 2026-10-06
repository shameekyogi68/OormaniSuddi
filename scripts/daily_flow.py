#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Daily News Production Flow Helper.
===================================================
Automates the repetitive mechanical daily tasks:
  1. Archive yesterday's edition (`python3 scripts/daily_flow.py archive-yesterday`)
  2. Show which desks are due, batched (`python3 scripts/daily_flow.py receipts`) — files nothing
  3. Verify all stories, with the name the editor gave (`python3 scripts/daily_flow.py verify --by "<name>"`)
  4. Render, then show what still has to inspect it (`python3 scripts/daily_flow.py render`)

Sources are kept one story at a time with `scripts/intake.py source` (D111).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import dispatch as D

def get_today() -> str:
    return dt.date.today().isoformat()


def resolve_day(value: str | None) -> str:
    """Today, or a real YYYY-MM-DD. A path-shaped date is refused. D106."""
    if not value:
        return get_today()
    from brand.content import ContentError, edition_day
    try:
        return edition_day(value)
    except ContentError as e:
        print(f'✗ {e}', file=sys.stderr)
        raise SystemExit(2)


def sign_off_hint(day: str, by: str | None) -> str:
    """The command to print. Never invents a person's name. D106."""
    who = (by or '').strip() or '<name>'
    return f'python3 scripts/sign_off.py out/{day} --by "{who}"'


def cmd_archive_yesterday(args) -> int:
    today = resolve_day(args.date)
    editions = sorted(glob.glob(os.path.join(ROOT, 'editions', '????-??-??.json')))
    prev = [e for e in editions if os.path.basename(e)[:10] < today]
    if not prev:
        print(f"No edition prior to {today} found to archive.")
        return 0
    target_date = os.path.basename(prev[-1])[:10]
    print(f"Archiving previous edition: {target_date}...")
    cmd = [sys.executable, os.path.join(ROOT, 'scripts', 'archive_edition.py'), target_date]
    res = subprocess.run(cmd)
    return res.returncode


def cmd_intake(args) -> int:
    """Retired (D111). Splitting a paste into stories, and crediting each to
    the outlet its own link belongs to, is the intake desk's judgement — not a
    regex's. This command split by line, saved one line per "story", and
    credited any link it did not recognise to ಉದಯವಾಣಿ (FACT-06)."""
    print('✗ `daily_flow.py intake` is retired (D111). Keep each story\'s '
          'source on its own:\n'
          '    python3 scripts/intake.py source --url URL --outlet NAME < story.txt\n'
          '    python3 scripts/intake.py source < notes.txt      # own reporting / press release\n'
          'or let the intake-editor agent split the paste.', file=sys.stderr)
    return 2


def cmd_receipts(args) -> int:
    """Show which desks are due, as BATCHED agent runs. Files nothing.

    This command used to write PASS receipts for the fact, legal, Kannada and
    inspection desks — "Facts, names and figures verified against kept
    source" — without any desk having read anything. A receipt is the proof a
    desk ran; forging it defeats the gate (OPS-04, D95) and is how a death
    headline shipped in red on 2026-09-27. The saving that motive was after is
    real and now comes honestly: dispatch.py launches ONE agent per desk for
    up to Limits.agent_batch_max stories (D97), not one per story.
    """
    today = resolve_day(args.date)
    print(D.brief(D.plan(today), limit=200))
    print("\nLaunch each wave as ONE message of parallel Agent calls, one per "
          "line above. Each agent files its own receipts; this script files none.")
    return 0


def cmd_verify(args) -> int:
    today = resolve_day(args.date)
    ed_path = os.path.join(ROOT, 'editions', f"{today}.json")
    if not args.by:
        print("Error: --by <name> is required to verify.", file=sys.stderr)
        return 1
    cmd = [sys.executable, os.path.join(ROOT, 'scripts', 'verify.py'), ed_path, '--all', '--by', args.by]
    res = subprocess.run(cmd)
    return res.returncode


def cmd_render(args) -> int:
    today = resolve_day(args.date)
    ed_path = os.path.join(ROOT, 'editions', f"{today}.json")
    print(f"Rendering {ed_path}...")
    cmd = [sys.executable, os.path.join(ROOT, 'render.py'), ed_path]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        return res.returncode
    # What still has to look at the render — the inspectors do, not this script.
    print("\n" + D.brief(D.plan(today), limit=200))
    print("\n" + "=" * 60)
    print(f"✓ Output ready in out/{today}/")
    print(f"  Instagram Carousel: Animated .mp4 video slides (out/{today}/saara_01_cover.mp4 …)")
    print(f"  Instagram Caption : out/{today}/saara_caption.txt")
    print(f"  Sign-off Command  : {sign_off_hint(today, args.by)}")
    print("=" * 60)
    return 0


def main():
    p = argparse.ArgumentParser(description="Oormani Suddi Daily News Flow Automation")
    sub = p.add_subparsers(dest="cmd")

    p_arch = sub.add_parser("archive-yesterday", help="Archive previous edition day")
    p_arch.add_argument("--date", help="Today's date (defaults to today)")

    p_in = sub.add_parser("intake", help="retired (D111) — use scripts/intake.py source")
    p_in.add_argument("--date", help=argparse.SUPPRESS)
    p_in.add_argument("--file", help=argparse.SUPPRESS)

    p_rec = sub.add_parser("receipts", help="Show which desks are due (files nothing)")
    p_rec.add_argument("--date", help="Today's date")

    p_ver = sub.add_parser("verify", help="Verify all stories in edition")
    p_ver.add_argument("--date", help="Today's date")
    p_ver.add_argument("--by", required=True, help="Editor's name")

    p_rnd = sub.add_parser("render", help="Render the edition and show what still has to inspect it")
    p_rnd.add_argument("--date", help="Today's date")
    p_rnd.add_argument("--by", help="Editor's name for sign-off prompt")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1

    if args.cmd == "archive-yesterday":
        return cmd_archive_yesterday(args)
    elif args.cmd == "intake":
        return cmd_intake(args)
    elif args.cmd == "receipts":
        return cmd_receipts(args)
    elif args.cmd == "verify":
        return cmd_verify(args)
    elif args.cmd == "render":
        return cmd_render(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
