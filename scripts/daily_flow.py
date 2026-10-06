#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Daily News Production Flow Helper.
===================================================
Automates the repetitive mechanical daily tasks:
  1. Archive yesterday's edition (`python3 scripts/daily_flow.py archive-yesterday`)
  2. Parse pasted news, save sources to inbox/sources/, auto-quote number claims in inbox/factcheck/
     (`python3 scripts/daily_flow.py intake < paste.txt`)
  3. Show which desks are due, batched (`python3 scripts/daily_flow.py receipts`) — files nothing
  4. Verify all stories (`python3 scripts/daily_flow.py verify --by "Gautam Paduvari"`)
  5. Render, then show what still has to inspect it (`python3 scripts/daily_flow.py render`)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import intake as I
from brand import sourcing as S
from brand import dispatch as D

URL_PAT = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)|(https?://[^\s]+)')

NUMBER_WORDS = [
    (r'\b(?:ಆರುನೂರು|ಆರುನೂರಕ್ಕೂ)\b', '600'),
    (r'\b(?:ಹದಿನಾರು|ಹದಿನಾರಕ್ಕೂ)\b', '16'),
    (r'\b(?:ಇಪ್ಪತ್ತು|ಇಪ್ಪತ್ತಕ್ಕೂ)\b', '20'),
    (r'\b(?:ಇಪ್ಪತ್ಮೂರು|ಇಪ್ಪತ್ತುಮೂರು)\b', '23'),
    (r'\b(?:ಹತ್ತು|ಹತ್ತಕ್ಕೂ)\b', '10'),
    (r'\b(?:ನಾಲ್ಕು|ನಾಲ್ಕರಂದು|ನಾಲ್ಕಕ್ಕೂ)\b', '4'),
    (r'\b(?:ಮೂರು|ಮೂರರಂದು|ಮೂರಕ್ಕೂ)\b', '3'),
    (r'\b(?:ಎರಡು|ಎರಡಕ್ಕೂ)\b', '2'),
    (r'\b(?:ಒಂದು|ಒಂದಕ್ಕೂ)\b', '1'),
]


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
    today = resolve_day(args.date)
    text = ""
    if args.file:
        with open(args.file, encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("Error: No pasted news text provided.", file=sys.stderr)
        return 1

    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    items = []
    for line in lines:
        m = URL_PAT.search(line)
        if m:
            url = m.group(2) or m.group(3)
            clean_text = URL_PAT.sub('', line).strip()
            outlet_list = S.outlet_names(url)
            outlet = outlet_list[0] if outlet_list else 'ಉದಯವಾಣಿ'
            items.append({'text': clean_text, 'url': url, 'outlet': outlet})

    if not items:
        # Fallback: maybe URL is in a multiline block
        parts = re.split(r'\n{2,}', text.strip())
        for part in parts:
            m = URL_PAT.search(part)
            if m:
                url = m.group(2) or m.group(3)
                clean_text = URL_PAT.sub('', part).strip()
                outlet_list = S.outlet_names(url)
                outlet = outlet_list[0] if outlet_list else 'ಉದಯವಾಣಿ'
                items.append({'text': clean_text, 'url': url, 'outlet': outlet})

    print(f"✓ Found {len(items)} news stories in paste:")
    ledger_claims = []
    for idx, item in enumerate(items, 1):
        path = I.save_pasted(item['text'], url=item['url'], outlet=item['outlet'])
        print(f"  [{idx}] {item['outlet']} → {os.path.relpath(path, ROOT)}")

        # Check for number words in text to extract claims
        sentences = re.split(r'[.!?।]\s*', item['text'])
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            for pat, token in NUMBER_WORDS:
                if re.search(pat, s_clean):
                    if not any(c['token'] == token and c['url'] == item['url'] for c in ledger_claims):
                        ledger_claims.append({
                            'token': token,
                            'quote': s_clean,
                            'url': item['url']
                        })

    # Save initial factcheck claims if any found
    if ledger_claims:
        os.makedirs(os.path.join(ROOT, 'inbox', 'factcheck'), exist_ok=True)
        fc_path = os.path.join(ROOT, 'inbox', 'factcheck', f"{today}.json")
        existing_claims = []
        if os.path.exists(fc_path):
            try:
                with open(fc_path, encoding='utf-8') as f:
                    existing_claims = json.load(f).get('claims', [])
            except Exception:
                pass
        for c in ledger_claims:
            if not any(e['token'] == c['token'] and e['url'] == c['url'] for e in existing_claims):
                existing_claims.append(c)
        with open(fc_path, 'w', encoding='utf-8') as f:
            json.dump({'claims': existing_claims}, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {len(existing_claims)} factcheck claim quote(s) to inbox/factcheck/{today}.json")

    return 0


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

    p_in = sub.add_parser("intake", help="Parse and save pasted news stories")
    p_in.add_argument("--date", help="Today's date")
    p_in.add_argument("--file", help="Path to paste file (reads stdin if omitted)")

    p_rec = sub.add_parser("receipts", help="Show which desks are due (files nothing)")
    p_rec.add_argument("--date", help="Today's date")
    p_rec.add_argument("--wave", default="1,2", help="Wave numbers (1, 2, 3, or all)")

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
