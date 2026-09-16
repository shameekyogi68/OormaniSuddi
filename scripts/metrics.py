#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — turn twenty opinions into seven measurements.
=============================================================
Every number in this system is currently a guess: 28–45s reels, a 1.5s hook,
11:30/14:30/17:30/20:30, six carousel slides. The docs honestly call them
starting positions and say "review after 30 days of analytics", and nothing
has been collecting analytics.

This is the smallest thing that fixes that, and it needs no API key, no
Business account and no follower threshold — all of which are real blockers
(Instagram insights are unavailable under 1,000 followers). The editor types
what the app already shows them, once a week, in about two minutes:

    python3 scripts/metrics.py add --date 2026-09-16 --asset reel_01.mp4 \\
        --format reel --category civic --at 17:30 \\
        --views 412 --reach 380 --saves 9 --shares 14 --watch 62

    python3 scripts/metrics.py report          # what the numbers say so far
    python3 scripts/metrics.py report --weeks 4

SQLite because it is in the standard library, it is one file, it survives a
crash mid-write, and "show me every civic reel posted at 17:30" is a question
scattered JSON cannot answer.

When there is enough data, the report stops hedging and names the change to
make. Until there is, it says how much more is needed — a recommendation from
four posts is astrology.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB = os.path.join(ROOT, 'archive', 'metrics.db')

# Below this, a difference between two slots is noise. Stated as a constant so
# the report cannot quietly start recommending things off three data points.
MIN_PER_GROUP = 5
MIN_TOTAL = 20


SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT NOT NULL,          -- the edition date, YYYY-MM-DD
    asset     TEXT NOT NULL,          -- reel_01.mp4, carousel, broadsheet …
    format    TEXT NOT NULL,          -- reel | carousel | story | broadsheet | bulletin | footage
    category  TEXT,                   -- the tokens.CATEGORIES key
    platform  TEXT DEFAULT 'instagram',
    at        TEXT,                   -- HH:MM the slot it actually went out
    seconds   REAL,                   -- duration, for video
    views     INTEGER DEFAULT 0,
    reach     INTEGER DEFAULT 0,
    likes     INTEGER DEFAULT 0,
    saves     INTEGER DEFAULT 0,
    shares    INTEGER DEFAULT 0,
    comments  INTEGER DEFAULT 0,
    follows   INTEGER DEFAULT 0,
    watch_pct REAL,                   -- average watch-through, 0-100
    note      TEXT,
    entered   TEXT NOT NULL,
    UNIQUE(date, asset, platform)
);
CREATE INDEX IF NOT EXISTS posts_date ON posts(date);
CREATE INDEX IF NOT EXISTS posts_slot ON posts(at);
"""


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def add(args) -> int:
    con = connect()
    try:
        con.execute(
            """INSERT INTO posts (date, asset, format, category, platform, at,
                                  seconds, views, reach, likes, saves, shares,
                                  comments, follows, watch_pct, note, entered)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(date, asset, platform) DO UPDATE SET
                 views=excluded.views, reach=excluded.reach,
                 likes=excluded.likes, saves=excluded.saves,
                 shares=excluded.shares, comments=excluded.comments,
                 follows=excluded.follows, watch_pct=excluded.watch_pct,
                 note=excluded.note, entered=excluded.entered""",
            (args.date, args.asset, args.format, args.category, args.platform,
             args.at, args.seconds, args.views, args.reach, args.likes,
             args.saves, args.shares, args.comments, args.follows, args.watch,
             args.note, datetime.now().isoformat(timespec='seconds')))
        con.commit()
    finally:
        con.close()
    print(f'✓ {args.date} {args.asset} recorded')
    n = count()
    if n < MIN_TOTAL:
        print(f'  {n}/{MIN_TOTAL} posts logged. The report stays quiet until '
              f'there is enough to mean something.')
    return 0


def count() -> int:
    con = connect()
    try:
        return con.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    finally:
        con.close()


def _rows(weeks: int | None) -> list[sqlite3.Row]:
    con = connect()
    try:
        if weeks:
            since = (datetime.now() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
            return con.execute('SELECT * FROM posts WHERE date >= ? ORDER BY date',
                               (since,)).fetchall()
        return con.execute('SELECT * FROM posts ORDER BY date').fetchall()
    finally:
        con.close()


def _group(rows, key):
    out: dict[str, list] = {}
    for r in rows:
        k = r[key] or '—'
        out.setdefault(str(k), []).append(r)
    return out


def _mean(rows, field: str) -> float:
    vals = [r[field] for r in rows if r[field] is not None]
    return sum(vals) / len(vals) if vals else 0.0


def _per_thousand(rows, field: str) -> float:
    """Shares and saves per 1,000 reach — the only way to compare a post that
    reached 200 people with one that reached 4,000."""
    reach = sum(r['reach'] or r['views'] or 0 for r in rows)
    if not reach:
        return 0.0
    return sum(r[field] or 0 for r in rows) / reach * 1000


def report(args) -> int:
    rows = _rows(args.weeks)
    lines: list[str] = ['# What the numbers say', '']
    if not rows:
        print('No posts logged yet.\n\n'
              '  python3 scripts/metrics.py add --date 2026-09-16 '
              '--asset reel_01.mp4 --format reel --category civic '
              '--at 17:30 --views 412 --reach 380 --saves 9 --shares 14')
        return 0

    span = f'{rows[0]["date"]} → {rows[-1]["date"]}'
    lines += [f'{len(rows)} posts · {span}', '']

    if len(rows) < MIN_TOTAL:
        lines += [
            f'> **Not enough yet.** {len(rows)} of {MIN_TOTAL} posts. '
            f'A recommendation from this many is astrology, so this report '
            f'shows the data and recommends nothing.', '']

    def table(title, grouped, note=''):
        block = [f'## {title}', '']
        if note:
            block += [note, '']
        block += ['| | n | reach | shares/1k | saves/1k | watch % |',
                  '|---|--:|--:|--:|--:|--:|']
        for k, rs in sorted(grouped.items(),
                            key=lambda kv: -_per_thousand(kv[1], 'shares')):
            block.append(
                f'| {k} | {len(rs)} | {_mean(rs, "reach"):.0f} | '
                f'{_per_thousand(rs, "shares"):.1f} | '
                f'{_per_thousand(rs, "saves"):.1f} | '
                f'{_mean(rs, "watch_pct"):.0f} |')
        return block + ['']

    lines += table('By posting slot', _group(rows, 'at'),
                   'The slots in `tokens.Limits.reel_slots` are a hypothesis. '
                   'This is the evidence.')
    lines += table('By format', _group(rows, 'format'))
    lines += table('By category', _group(rows, 'category'))

    # Reel length against watch-through — the number that decides whether
    # 28–45s is right for THIS audience rather than for social media in general.
    reels = [r for r in rows if r['format'] == 'reel' and r['seconds']]
    if len(reels) >= MIN_PER_GROUP:
        buckets: dict[str, list] = {}
        for r in reels:
            s = r['seconds']
            k = ('under 28s' if s < 28 else '28–35s' if s < 35
                 else '35–45s' if s < 45 else 'over 45s')
            buckets.setdefault(k, []).append(r)
        lines += table('Reel length vs watch-through', buckets,
                       'If a bucket outside 28–45s wins consistently, change '
                       '`tokens.Limits`, write a decision, and let the test '
                       'fail until everything agrees.')

    # ── what to actually change ───────────────────────────────────────────
    lines += ['## What to change', '']
    said_something = False
    if len(rows) >= MIN_TOTAL:
        slots = {k: v for k, v in _group(rows, 'at').items()
                 if len(v) >= MIN_PER_GROUP and k != '—'}
        if len(slots) >= 2:
            ranked = sorted(slots.items(),
                            key=lambda kv: -_per_thousand(kv[1], 'shares'))
            best, worst = ranked[0], ranked[-1]
            b, w = _per_thousand(best[1], 'shares'), _per_thousand(worst[1], 'shares')
            if w and b / w >= 1.4:
                lines += [
                    f'- **{best[0]} outperforms {worst[0]} by '
                    f'{(b / w - 1) * 100:.0f}% on shares per 1,000 reach** '
                    f'({len(best[1])} vs {len(worst[1])} posts). Move the '
                    f'{worst[0]} slot toward {best[0]} in '
                    f'`tokens.Limits.reel_slots`, and write it down as a '
                    f'decision so the schedule and the docs move together.']
                said_something = True
        cats = {k: v for k, v in _group(rows, 'category').items()
                if len(v) >= MIN_PER_GROUP}
        if cats:
            top = max(cats.items(), key=lambda kv: _per_thousand(kv[1], 'saves'))
            if _per_thousand(top[1], 'saves') > 0:
                lines += [
                    f'- **{top[0]} is the most-saved category** '
                    f'({_per_thousand(top[1], "saves"):.1f} saves/1k). Saves '
                    f'mean reference value — that is the category to build a '
                    f'weekly explainer around.']
                said_something = True
    if not said_something:
        lines += ['- Nothing yet that survives the noise floor '
                  f'({MIN_PER_GROUP}+ posts per group, {MIN_TOTAL}+ total). '
                  'Keep logging.']
    lines += ['']

    body = '\n'.join(lines)
    print(body)
    out = os.path.join(ROOT, 'archive', 'metrics_report.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(body)
    print(f'→ {os.path.relpath(out, ROOT)}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add', help='record one post, by hand, from the app')
    a.add_argument('--date', required=True, help='edition date YYYY-MM-DD')
    a.add_argument('--asset', required=True, help='reel_01.mp4, carousel, …')
    a.add_argument('--format', required=True,
                   choices=['reel', 'carousel', 'story', 'broadsheet',
                            'bulletin', 'footage', 'short'])
    a.add_argument('--category', default='')
    a.add_argument('--platform', default='instagram')
    a.add_argument('--at', default='', help='HH:MM it actually went out')
    a.add_argument('--seconds', type=float, default=None)
    for f in ('views', 'reach', 'likes', 'saves', 'shares', 'comments', 'follows'):
        a.add_argument(f'--{f}', type=int, default=0)
    a.add_argument('--watch', type=float, default=None,
                   help='average watch-through %%')
    a.add_argument('--note', default='')
    a.set_defaults(fn=add)

    r = sub.add_parser('report', help='what the numbers say so far')
    r.add_argument('--weeks', type=int, default=None,
                   help='only the last N weeks')
    r.set_defaults(fn=report)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    raise SystemExit(main())
