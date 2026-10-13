#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the company's books, in one command. D118.
==========================================================
The newsroom has render.py; the company has this. Everything the business
desks decide from is typed in here by a person, from what the bank and the
platforms already show. Two minutes a week.

    python3 scripts/business.py init                 # once: create business/
    python3 scripts/business.py status               # the one-screen view

    # money — every rupee, in and out
    python3 scripts/business.py money --date 2026-10-12 --kind income \\
        --amount 2000 --stream greeting_sponsor --party "Sri Durga Jewellers" \\
        --ref 2026-10-001 [--tds 200]
    python3 scripts/business.py money --date 2026-10-01 --kind expense \\
        --amount 1999 --stream ai_tools --party Anthropic --note "Claude"
    python3 scripts/business.py pnl [--month 2026-10 | --fy 2026]

    # audience — weekly, from YouTube Studio / Professional dashboard
    python3 scripts/business.py audience --platform youtube --followers 412 \\
        --watch-hours 860 --shorts-views 120000 --uploads-90d 14
    python3 scripts/business.py audience --platform facebook --followers 2300 \\
        --minutes-60d 18000

    # deals — a sponsor from first call to paid
    python3 scripts/business.py deal add --client "Sri Durga Jewellers" \\
        --product greeting_sponsor --category jewellery --price 1500 \\
        --names "ಶ್ರೀ ದುರ್ಗಾ ಜ್ಯುವೆಲ್ಲರ್ಸ್" "Sri Durga Jewellers" \\
        --next "send the Deepavali offer" --on 2026-10-14
    python3 scripts/business.py deal move 2026-10-001 pitched --next "…" --on …
    python3 scripts/business.py deal clear 2026-10-001 --by "<the person>"
    python3 scripts/business.py deal move 2026-10-001 live
    python3 scripts/business.py deal list

    # the firewall
    python3 scripts/business.py conflicts editions/2026-10-12.json
    python3 scripts/business.py check                # every row and deal

`deal clear --by` is a person's act, like verify.py (D59): an assistant runs
it only with the name the owner gives in chat. There is no flag that waives a
firewall rule (docs/ADVERTISING.md).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import business as B                           # noqa: E402

OK, WARN, BAD = '  ✓', '  !', '  ✗'


def rs(x: float) -> str:
    """Indian grouping: 12,34,567."""
    n = int(round(x))
    s, neg = str(abs(n)), n < 0
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ','.join(parts + [tail])
    return f'{"-" if neg else ""}₹{s}'


def _need_books() -> None:
    if not B.ready():
        raise SystemExit('No books yet. Once: python3 scripts/business.py init')


def cmd_init(a) -> int:
    made = B.init()
    print('\n'.join(f'{OK} {m}' for m in made) or f'{OK} business/ already set up')
    print('\n  Next: set your prices in business/rate_card.json, confirm '
          'business/goals.json,\n  and log this week\'s platform numbers '
          '(python3 scripts/business.py audience …).')
    return 0


def cmd_status(a) -> int:
    _need_books()
    today = date.fromisoformat(a.day) if a.day else date.today()
    s = B.status(today)
    print(f'\n  ಊರ್ಮನಿ ಸುದ್ದಿ — the company   {today.isoformat()}\n')

    m = s.month
    print(f'  THIS MONTH   in {rs(m["income"])} · out {rs(m["expense"])} · '
          f'net {rs(m["net"])}')
    for k, v in sorted(m['by_income'].items(), key=lambda x: -x[1]):
        print(f'      + {k:<18} {rs(v)}')
    for k, v in sorted(m['by_expense'].items(), key=lambda x: -x[1]):
        print(f'      − {k:<18} {rs(v)}')
    if s.tools_cover is not None:
        mark = OK if s.tools_cover >= 1 else WARN
        print(f'{mark} income covers the AI tools {s.tools_cover:.1f}×')
    print(f'  THIS FY      in {rs(s.fy["income"])} · out {rs(s.fy["expense"])} · '
          f'net {rs(s.fy["net"])}' + (f' · TDS deducted {rs(s.fy["tds"])}'
                                       if s.fy['tds'] else ''))
    g = s.gst
    mark = BAD if g['over'] else WARN if g['warn'] else OK
    print(f'{mark} GST          FY {g["fy"]} turnover {rs(g["turnover"])} of the '
          f'{rs(g["threshold"])} registration line ({g["share"]:.0%})'
          + (' — talk to a CA now' if g['warn'] else ''))

    print('\n  PLATFORMS — how far from being paid')
    if s.audience_age is None:
        print(f'{WARN} no platform numbers yet — python3 scripts/business.py audience …')
    elif s.audience_age > B.AUDIENCE_STALE_DAYS:
        print(f'{WARN} numbers are {s.audience_age} days old — log this week\'s')
    for p in s.monetisation:
        if not p['known']:
            print(f'      {p["programme"]:<24} no numbers for {p["platform"]}')
            continue
        bar = '█' * int(p['progress'] * 10) + '·' * (10 - int(p['progress'] * 10))
        tail = 'ELIGIBLE — apply: ' + p['where'] if p['eligible'] else \
            'needs ' + ', '.join(p['missing'])
        print(f'      {p["programme"]:<24} {bar} {p["progress"]:>4.0%}  {tail}')

    print('\n  DEALS')
    for st in B.STAGES:
        ds = s.pipeline.get(st, [])
        if ds:
            val = sum(B._num(d.get('price_inr')) for d in ds)
            print(f'      {st:<8} {len(ds):>2}  {rs(val)}')
    if not any(s.pipeline.values()):
        print('      none yet — the revenue desk drafts the first pitches')
    for d in s.follow_ups:
        print(f'{WARN} follow up {d["id"]} {d.get("client")}: '
              f'{d.get("next_action") or "next step"} (due {d["next_date"]})')
    if s.stale_rules:
        print(f'{WARN} platform rules last checked over {B.RULES_STALE_DAYS} days '
              f'ago: {", ".join(s.stale_rules)} — confirm and update '
              f'brand/business.py PLATFORM_RULES')
    print()
    return 0


def cmd_money(a) -> int:
    _need_books()
    row = B.add_money({'date': a.date or date.today().isoformat(), 'kind': a.kind,
                       'amount_inr': a.amount, 'stream': a.stream,
                       'party': a.party, 'note': a.note, 'ref': a.ref,
                       'tds_inr': a.tds})
    print(f'{OK} {row["kind"]} {rs(float(row["amount_inr"]))} · {row["stream"]} · '
          f'{row["party"] or "—"}')
    return 0


def cmd_pnl(a) -> int:
    _need_books()
    rows = B.ledger()
    if a.fy:
        fy = int(a.fy)
        start, end, name = date(fy, 4, 1), date(fy + 1, 3, 31), f'FY {fy}-{(fy + 1) % 100:02d}'
    else:
        ym = a.month or date.today().strftime('%Y-%m')
        (start, end), name = B.month_bounds(ym), ym
    t = B.totals(rows, start, end)
    print(f'\n  {name}\n')
    print('  INCOME')
    for k, v in sorted(t['by_income'].items(), key=lambda x: -x[1]):
        print(f'    {k:<20} {rs(v):>12}')
    print(f'    {"total":<20} {rs(t["income"]):>12}')
    print('  EXPENSES')
    for k, v in sorted(t['by_expense'].items(), key=lambda x: -x[1]):
        print(f'    {k:<20} {rs(v):>12}')
    print(f'    {"total":<20} {rs(t["expense"]):>12}')
    print(f'\n  NET {rs(t["net"])}' + (f'   (TDS deducted by clients: {rs(t["tds"])} — '
                                       f'claim it in the return)' if t['tds'] else ''))
    print()
    return 0


def cmd_audience(a) -> int:
    _need_books()
    row = {'date': a.date or date.today().isoformat(), 'platform': a.platform,
           'followers': a.followers, 'watch_hours_12m': a.watch_hours,
           'shorts_views_90d': a.shorts_views, 'uploads_90d': a.uploads_90d,
           'minutes_60d': a.minutes_60d, 'views_28d': a.views_28d}
    B.add_audience({k: ('' if v is None else v) for k, v in row.items()})
    print(f'{OK} {a.platform} {row["date"]}: {a.followers} followers')
    return 0


def cmd_deal(a) -> int:
    _need_books()
    if a.action == 'add':
        d = B.add_deal({'client': a.client, 'product': a.product,
                        'category': a.category, 'price_inr': a.price,
                        'names': a.names or [], 'political': a.political,
                        'mcmc_ref': a.mcmc, 'deliverable': a.deliverable,
                        'next_action': a.next, 'next_date': a.on,
                        'notes': a.notes})
        print(f'{OK} deal {d["id"]} — {d["client"]} · {d["product"]} · '
              f'{rs(B._num(d.get("price_inr")))} · {d["stage"]}')
        if d['category'] in B.SENSITIVE:
            print(f'{WARN} {d["category"]}: the ad-standards desk reads it before '
                  f'it can be cleared')
    elif a.action == 'move':
        d = B.move_deal(a.id, a.stage, next_action=a.next, next_date=a.on,
                        mcmc_ref=a.mcmc)
        print(f'{OK} deal {d["id"]} → {d["stage"]}')
        if d['stage'] == 'paid':
            print('      log the money: python3 scripts/business.py money '
                  f'--kind income --stream {d["product"]} --ref {d["id"]} …')
    elif a.action == 'clear':
        d = B.clear_deal(a.id, a.by)
        print(f'{OK} deal {d["id"]} cleared by {d["cleared_by"]}')
    else:
        for d in B.deals():
            if d.get('stage') == 'lost' and not a.all:
                continue
            print(f'  {d["id"]}  {d.get("stage", ""):<8} {d.get("client", "")[:28]:<28} '
                  f'{d.get("product", ""):<16} {rs(B._num(d.get("price_inr"))):>9}  '
                  f'{d.get("next_date", "")} {d.get("next_action", "")[:40]}')
    return 0


def cmd_conflicts(a) -> int:
    _need_books()
    with open(a.edition, encoding='utf-8') as fh:
        ed = json.load(fh)
    found = B.conflicts(ed)
    print('\n'.join(f'{WARN} {x}' for x in found) or f'{OK} no story names a '
                                                     f'current sponsor')
    return 1 if found else 0


def cmd_check(a) -> int:
    _need_books()
    p = B.validate_books()
    print('\n'.join(f'{BAD} {x}' for x in p) or f'{OK} the books are clean')
    return 1 if p else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='the company\'s books (D118)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init')
    s = sub.add_parser('status')
    s.add_argument('--day')

    m = sub.add_parser('money')
    m.add_argument('--date')
    m.add_argument('--kind', required=True, choices=('income', 'expense'))
    m.add_argument('--amount', required=True)
    m.add_argument('--stream', required=True,
                   choices=B.INCOME_STREAMS + B.EXPENSE_STREAMS)
    m.add_argument('--party', default='')
    m.add_argument('--note', default='')
    m.add_argument('--ref', default='', help='deal id or invoice number')
    m.add_argument('--tds', default='', help='TDS the client deducted, ₹')

    p = sub.add_parser('pnl')
    p.add_argument('--month')
    p.add_argument('--fy', help='starting year: 2026 = Apr 2026–Mar 2027')

    u = sub.add_parser('audience')
    u.add_argument('--date')
    u.add_argument('--platform', required=True, choices=B.PLATFORMS)
    u.add_argument('--followers', required=True,
                   help='followers; subscribers on YouTube; members on WhatsApp')
    u.add_argument('--watch-hours', help='YouTube: public watch hours, last 12 months')
    u.add_argument('--shorts-views', help='YouTube: Shorts views, last 90 days')
    u.add_argument('--uploads-90d', help='YouTube: public uploads, last 90 days')
    u.add_argument('--minutes-60d', help='Facebook: minutes viewed, last 60 days')
    u.add_argument('--views-28d', help='views or reach, last 28 days')

    d = sub.add_parser('deal')
    d.add_argument('action', choices=('add', 'move', 'clear', 'list'))
    d.add_argument('id', nargs='?')
    d.add_argument('stage', nargs='?', choices=B.STAGES)
    d.add_argument('--client')
    d.add_argument('--product', choices=tuple(B.PRODUCTS))
    d.add_argument('--category', choices=B.CATEGORIES)
    d.add_argument('--price')
    d.add_argument('--names', nargs='*')
    d.add_argument('--political', action='store_true')
    d.add_argument('--mcmc', default='', help='MCMC pre-certificate number')
    d.add_argument('--deliverable', default='')
    d.add_argument('--notes', default='')
    d.add_argument('--next', default='')
    d.add_argument('--on', default='', help='date of the next action')
    d.add_argument('--by', default='', help='clear: the person clearing it')
    d.add_argument('--all', action='store_true', help='list: include lost')

    c = sub.add_parser('conflicts')
    c.add_argument('edition')
    sub.add_parser('check')

    a = ap.parse_args(argv)
    if a.cmd == 'deal':
        if a.action == 'add' and not (a.client and a.product and a.category):
            ap.error('deal add needs --client, --product and --category')
        if a.action in ('move', 'clear') and not a.id:
            ap.error(f'deal {a.action} needs a deal id')
        if a.action == 'move' and not a.stage:
            ap.error(f'deal move needs a stage: {", ".join(B.STAGES)}')
    try:
        return {'init': cmd_init, 'status': cmd_status, 'money': cmd_money,
                'pnl': cmd_pnl, 'audience': cmd_audience, 'deal': cmd_deal,
                'conflicts': cmd_conflicts, 'check': cmd_check}[a.cmd](a)
    except B.BizError as e:
        print(f'{BAD} refused — {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
