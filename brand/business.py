"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the company: money, audience, deals, and the firewall. D118.
==========================================================================
The newsroom makes the news. This module keeps the business that pays for it
honest and visible: what came in and went out, how far each platform is from
paying us, who is a sponsor, and — the load-bearing part — that nothing a
sponsor pays for ever rides a news format.

Nothing here calls a model, a platform or the web. The owner types what the
platforms and the bank already show (`scripts/business.py`), and the business
desks (`.claude/agents/`, kind `business`) read it.

The books are PRIVATE. They live in `business/` (gitignored — the remote is a
public repo) and are carried by `scripts/backup.sh`. `business/README.md` is
the only tracked file in that folder.

    business/ledger.csv     every rupee in and out          (owner types)
    business/audience.csv   platform numbers, weekly        (owner types)
    business/deals.json     sponsors, from lead to paid     (CLI writes)
    business/goals.json     this quarter's targets          (owner confirms)
    business/rate_card.json what each product costs         (owner sets)
    business/notes.md       platform announcements pasted   (owner pastes)
    business/reports/       what the business desks wrote   (agents write)
    business/drafts/        pitches, invoices, replies      (agents draft;
                                                             a person sends)

THE FIREWALL (docs/ADVERTISING.md)
  1. Money buys a labelled product from PRODUCTS. It never buys a story, a
     slot in ಸ್ಪೀಡ್ ನ್ಯೂಸ್ / ಸುದ್ದಿ ಸಾರ / ಮುಖ್ಯ ಸುದ್ದಿ, a softer story, or a
     deleted one. A news Story has no field for money, deliberately.
  2. Every published product carries its label on the work itself and the
     platform's paid-partnership tool on the post.
  3. Some advertisers we never take (PROHIBITED); some need the ad-standards
     desk to read the claims first (SENSITIVE); political ads need the
     MCMC pre-certificate.
  4. A deal goes live only after a PERSON clears it (`deal clear --by`),
     as a story is published only after a person verifies it (D59).
  5. A story that names a current sponsor is flagged to the editor.
"""
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIZ = os.path.join(ROOT, 'business')
LEDGER = os.path.join(BIZ, 'ledger.csv')
AUDIENCE = os.path.join(BIZ, 'audience.csv')
DEALS = os.path.join(BIZ, 'deals.json')
GOALS = os.path.join(BIZ, 'goals.json')
RATE_CARD = os.path.join(BIZ, 'rate_card.json')
NOTES = os.path.join(BIZ, 'notes.md')
REPORTS = os.path.join(BIZ, 'reports')
DRAFTS = os.path.join(BIZ, 'drafts')

LEDGER_COLS = ('date', 'kind', 'amount_inr', 'stream', 'party', 'note', 'ref',
               'tds_inr')
AUDIENCE_COLS = ('date', 'platform', 'followers', 'watch_hours_12m',
                 'shorts_views_90d', 'uploads_90d', 'minutes_60d', 'views_28d')

PLATFORMS = ('youtube', 'instagram', 'facebook', 'whatsapp')

# Where money comes from, and where it goes. A row outside these is refused,
# so a month's report never has to guess what "misc" was.
INCOME_STREAMS = ('youtube_ads', 'youtube_fans', 'facebook_ads', 'instagram',
                  'greeting_sponsor', 'ad_post', 'sponsored_video',
                  'event_coverage', 'live_stream', 'notice', 'production',
                  'grant', 'other_income')
EXPENSE_STREAMS = ('ai_tools', 'software', 'equipment', 'phone_internet',
                   'travel', 'freelancer', 'boost', 'fees', 'other_expense')

# ── The products — the only things money buys (firewall rule 1) ─────────────
# label: the word on the work itself. '' only for work we do not publish.
PRODUCTS: dict[str, dict] = {
    'greeting_sponsor': {
        'label': 'ಪ್ರಾಯೋಜಿತ', 'name': 'ಹಬ್ಬದ ಶುಭಾಶಯ — ಪ್ರಾಯೋಜಕರ ಹೆಸರಿನೊಂದಿಗೆ',
        'runs': 'a festival greeting card (templates/greeting.py) carrying the '
                'sponsor\'s name; Instagram + Facebook'},
    'ad_post': {
        'label': 'ಜಾಹೀರಾತು', 'name': 'ಜಾಹೀರಾತು ಪೋಸ್ಟ್ / ರೀಲ್',
        'runs': 'a standalone post or reel, never inside a news format'},
    'sponsored_video': {
        'label': 'ಪ್ರಾಯೋಜಿತ', 'name': 'ಪ್ರಾಯೋಜಿತ ವಿಡಿಯೋ',
        'runs': 'a YouTube video or Short about the client, with YouTube\'s '
                '"includes paid promotion" box ticked'},
    'event_coverage': {
        'label': 'ಪ್ರಾಯೋಜಿತ', 'name': 'ಕಾರ್ಯಕ್ರಮದ ವಿಡಿಯೋ ಪ್ರಸಾರ',
        'runs': 'an organiser pays us to film and post their event — the '
                'footage skills, labelled; the newsroom may still cover the '
                'same event as news, on its own judgement and unpaid'},
    'live_stream': {
        'label': 'ಪ್ರಾಯೋಜಿತ', 'name': 'ನೇರ ಪ್ರಸಾರ',
        'runs': 'a paid live broadcast of an event'},
    'notice': {
        'label': 'ಜಾಹೀರಾತು', 'name': 'ಶ್ರದ್ಧಾಂಜಲಿ / ಅಭಿನಂದನೆ / ಶುಭಾಶಯ ಪ್ರಕಟಣೆ',
        'runs': 'a personal notice paid for by a family or a group, as its '
                'own post'},
    'production': {
        'label': '', 'name': 'ವಿಡಿಯೋ ನಿರ್ಮಾಣ ಸೇವೆ',
        'runs': 'we film or edit FOR a client; it is not published on our '
                'channels and carries no ಊರ್ಮನಿ ಸುದ್ದಿ branding'},
}
LABELS = ('ಪ್ರಾಯೋಜಿತ', 'ಜಾಹೀರಾತು')

# Things only the newsroom decides. A deal that asks for one is refused.
NEWS_WORDS = ('news', 'headline', 'roundup', 'saara', 'mukhya', 'ಸ್ಪೀಡ್ ನ್ಯೂಸ್',
              'ಸುದ್ದಿ ಸಾರ', 'ಮುಖ್ಯ ಸುದ್ದಿ', 'ಸುದ್ದಿಯಾಗಿ', 'ಸುದ್ದಿ ಮಾಡಿ', 'ಸುದ್ದಿ ಹಾಕಿ',
              'remove', 'delete', 'take down', 'ತೆಗೆದುಹಾಕಿ', 'ಡಿಲೀಟ್',
              # D118 / research 2026-10: a sponsor inside a bulletin, a digest
              # or a breaking card, or paid work dressed in a news word
              'bulletin', 'ಬುಲೆಟಿನ್', 'digest', 'ಡೈಜೆಸ್ಟ್', 'breaking',
              'ಬ್ರೇಕಿಂಗ್', 'ವರದಿ', 'ಪ್ರಾಯೋಜಿತ ಸುದ್ದಿ')
# Our own name is not a request for news.
_OUR_NAME = ('ಊರ್ಮನಿ ಸುದ್ದಿ', 'oormani suddi', 'oormanisuddi')

# Advertisers we never take (firewall rule 3). Indian law, or our own line.
PROHIBITED = {
    'online_money_gaming': 'Promotion and Regulation of Online Gaming Act, 2025',
    'betting': 'illegal gambling; ASCI',
    'tobacco': 'COTPA 2003, s.5',
    'liquor': 'surrogate liquor ads — ASCI and Cable TV rules; our line',
    'magic_remedy': 'Drugs and Magic Remedies (Objectionable Ads) Act, 1954',
}
# Advertisers whose claims the ad-standards desk reads before a person clears.
SENSITIVE = ('health', 'medicine', 'hospital', 'finance', 'chit_fund', 'loan',
             'insurance', 'real_estate', 'education', 'crypto', 'political',
             'religious', 'government')
CATEGORIES = tuple(sorted(set(SENSITIVE) | set(PROHIBITED) | {
    'jewellery', 'textiles', 'retail', 'food', 'hotel', 'automobile',
    'electronics', 'construction', 'temple_event', 'community_event', 'school_event',
    'family', 'services', 'other'}))

STAGES = ('lead', 'pitched', 'agreed', 'live', 'paid', 'lost')

# ── What the platforms require before they pay (external rules) ─────────────
# Platforms change these. `checked` is when a person last confirmed each one
# against the platform's own page; the steward flags any older than
# RULES_STALE_DAYS. `any_of` = one of these groups must be met in full.
RULES_STALE_DAYS = 180
PLATFORM_RULES: dict[str, dict] = {
    'youtube_fans': {
        'platform': 'youtube', 'checked': '2026-10-12',
        'pays': 'memberships, Super Thanks, Super Chat, Shopping (no ad share)',
        'all': {'followers': 500, 'uploads_90d': 3},
        'any_of': [{'watch_hours_12m': 3000}, {'shorts_views_90d': 3_000_000}],
        'where': 'YouTube Studio → Earn'},
    'youtube_ads': {
        'platform': 'youtube', 'checked': '2026-10-12',
        'pays': 'a share of ad revenue on long videos and Shorts',
        'all': {'followers': 1000},
        'any_of': [{'watch_hours_12m': 4000}, {'shorts_views_90d': 10_000_000}],
        'where': 'YouTube Studio → Earn'},
    'facebook_ads': {
        'platform': 'facebook', 'checked': '2026-10-12',
        'pays': 'in-stream / Reels ads (Meta now runs these as Content '
                'Monetization, partly by invitation)',
        'all': {'followers': 5000, 'minutes_60d': 60_000},
        'any_of': [],
        'where': 'Professional dashboard → Monetisation — last known '
                 'figures; Meta also invites Pages and takes an expression '
                 'of interest there. Confirm there'},
    'instagram_subscriptions': {
        'platform': 'instagram', 'checked': '2026-10-12',
        'pays': 'monthly subscriptions from followers',
        'all': {'followers': 10_000},
        'any_of': [],
        'where': 'Professional dashboard → Monetisation status'},
}

# GST: registration is compulsory once a financial year's aggregate turnover
# from services passes this in Karnataka. Warn well before it.
GST_THRESHOLD_INR = 2_000_000
GST_WARN_SHARE = 0.75

AUDIENCE_STALE_DAYS = 8


class BizError(ValueError):
    """A row or a deal the books refuse. `code` says which rule."""

    def __init__(self, code: str, msg: str):
        super().__init__(msg if msg.startswith(code) else f'{code}: {msg}')
        self.code = code


# ─────────────────────────────────────────────────────────────────────────────
#  FILES
# ─────────────────────────────────────────────────────────────────────────────

def ready() -> bool:
    return os.path.exists(LEDGER)


def init() -> list[str]:
    """Create the books once. Never overwrites a file that exists."""
    made = []
    os.makedirs(REPORTS, exist_ok=True)
    os.makedirs(DRAFTS, exist_ok=True)
    starters = {
        LEDGER: ','.join(LEDGER_COLS) + '\n',
        AUDIENCE: ','.join(AUDIENCE_COLS) + '\n',
        DEALS: '[]\n',
        GOALS: json.dumps(_starter_goals(), ensure_ascii=False, indent=1) + '\n',
        RATE_CARD: json.dumps(_starter_rate_card(), ensure_ascii=False,
                              indent=1) + '\n',
        NOTES: ('# Platform notes\n\nPaste here what YouTube, Meta and '
                'Instagram announce about monetisation or reach, with the '
                'date. The business desks weigh it above docs/BUSINESS.md.\n'),
    }
    for path, body in starters.items():
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(body)
            made.append(os.path.relpath(path, ROOT))
    return made


def _starter_goals() -> dict:
    today = date.today()
    q = (today.month - 1) // 3 + 1
    end = date(today.year + (q == 4), (q % 4) * 3 + 1, 1) - timedelta(days=1)
    return {
        'quarter': f'{today.year}-Q{q}',
        'confirmed_by': '',
        'goals': [
            {'name': 'YouTube fan-funding eligibility', 'platform': 'youtube',
             'metric': 'followers', 'target': 500, 'by': end.isoformat()},
            {'name': 'YouTube watch hours (12 months)', 'platform': 'youtube',
             'metric': 'watch_hours_12m', 'target': 3000, 'by': end.isoformat()},
            {'name': 'Paying sponsors this quarter', 'metric': 'deals_paid',
             'target': 3, 'by': end.isoformat()},
            {'name': 'Income covers the AI tools', 'metric': 'tools_covered',
             'target': 1, 'by': end.isoformat()},
        ],
    }


def _starter_rate_card() -> dict:
    # [Guess] starting prices for a young coastal page — the owner sets the
    # real ones; the revenue desk proposes changes once deals exist.
    guess = {'greeting_sponsor': 1500, 'ad_post': 2000, 'sponsored_video': 5000,
             'event_coverage': 5000, 'live_stream': 8000, 'notice': 700,
             'production': 6000}
    return {'set_by': '', 'currency': 'INR', 'gst_included': False,
            'note': 'Starting guesses. Owner sets the real prices.',
            'products': {k: {'price_inr': v, 'name': PRODUCTS[k]['name']}
                         for k, v in guess.items()}}


def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', newline='') as fh:
        return [r for r in csv.DictReader(fh) if any((v or '').strip()
                                                     for v in r.values())]


def _append_csv(path: str, cols: tuple, row: dict) -> None:
    new = not os.path.exists(path)
    with open(path, 'a', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerow({c: row.get(c, '') for c in cols})


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _write_json(path: str, data) -> None:
    tmp = path + '.part'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    os.replace(tmp, path)


def _num(v, default=0.0) -> float:
    try:
        return float(str(v).replace(',', '').strip() or default)
    except ValueError:
        return default


# ─────────────────────────────────────────────────────────────────────────────
#  MONEY
# ─────────────────────────────────────────────────────────────────────────────

def check_money(row: dict) -> dict:
    d = str(row.get('date', ''))
    try:
        date.fromisoformat(d)
    except ValueError:
        raise BizError('BIZ-01', f'date {d!r} is not YYYY-MM-DD')
    kind = row.get('kind')
    if kind not in ('income', 'expense'):
        raise BizError('BIZ-01', f'kind must be income or expense, not {kind!r}')
    allowed = INCOME_STREAMS if kind == 'income' else EXPENSE_STREAMS
    if row.get('stream') not in allowed:
        raise BizError('BIZ-01', f'{kind} stream {row.get("stream")!r} is not '
                                 f'one of {", ".join(allowed)}')
    amt = _num(row.get('amount_inr'), -1)
    if amt <= 0:
        raise BizError('BIZ-01', 'amount_inr must be a positive number of rupees')
    if _num(row.get('tds_inr')) < 0 or _num(row.get('tds_inr')) > amt:
        raise BizError('BIZ-01', 'tds_inr must be between 0 and the amount')
    return {**row, 'amount_inr': f'{amt:g}',
            'tds_inr': f'{_num(row.get("tds_inr")):g}' if row.get('tds_inr') else ''}


def add_money(row: dict) -> dict:
    row = check_money(row)
    _append_csv(LEDGER, LEDGER_COLS, row)
    return row


def ledger() -> list[dict]:
    return _read_csv(LEDGER)


def fy_of(d: date) -> int:
    """Indian financial year by its starting year: 2026 = Apr 2026–Mar 2027."""
    return d.year if d.month >= 4 else d.year - 1


def totals(rows: list[dict], start: date, end: date) -> dict:
    """Income and expense by stream, for start <= date <= end."""
    inc: dict[str, float] = {}
    exp: dict[str, float] = {}
    tds = 0.0
    for r in rows:
        try:
            d = date.fromisoformat(r['date'])
        except (ValueError, KeyError):
            continue
        if not start <= d <= end:
            continue
        a = _num(r.get('amount_inr'))
        if r.get('kind') == 'income':
            inc[r['stream']] = inc.get(r['stream'], 0) + a
            tds += _num(r.get('tds_inr'))
        elif r.get('kind') == 'expense':
            exp[r['stream']] = exp.get(r['stream'], 0) + a
    i, e = sum(inc.values()), sum(exp.values())
    return {'income': i, 'expense': e, 'net': i - e, 'by_income': inc,
            'by_expense': exp, 'tds': tds}


def month_bounds(ym: str) -> tuple[date, date]:
    y, m = map(int, ym.split('-'))
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    return start, end


def gst_watch(rows: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    fy = fy_of(today)
    t = totals(rows, date(fy, 4, 1), date(fy + 1, 3, 31))
    share = t['income'] / GST_THRESHOLD_INR
    return {'fy': f'{fy}-{(fy + 1) % 100:02d}', 'turnover': t['income'],
            'threshold': GST_THRESHOLD_INR, 'share': share,
            'warn': share >= GST_WARN_SHARE, 'over': share >= 1}


# ─────────────────────────────────────────────────────────────────────────────
#  AUDIENCE
# ─────────────────────────────────────────────────────────────────────────────

def add_audience(row: dict) -> dict:
    try:
        date.fromisoformat(str(row.get('date', '')))
    except ValueError:
        raise BizError('BIZ-02', 'date is not YYYY-MM-DD')
    if row.get('platform') not in PLATFORMS:
        raise BizError('BIZ-02', f'platform must be one of {", ".join(PLATFORMS)}')
    for c in AUDIENCE_COLS[2:]:
        if row.get(c) not in (None, '') and _num(row[c], -1) < 0:
            raise BizError('BIZ-02', f'{c} must be a number ≥ 0')
    if row.get('followers') in (None, ''):
        raise BizError('BIZ-02', 'followers (subscribers on YouTube) is required')
    _append_csv(AUDIENCE, AUDIENCE_COLS, row)
    return row


def latest_audience() -> dict[str, dict]:
    """The newest row per platform; each figure from the newest row that has it."""
    out: dict[str, dict] = {}
    for r in sorted(_read_csv(AUDIENCE), key=lambda r: r.get('date', '')):
        p = r.get('platform')
        cur = out.setdefault(p, {})
        for k, v in r.items():
            if v not in (None, ''):
                cur[k] = v
    return out


def monetisation(aud: dict[str, dict] | None = None) -> list[dict]:
    """How far each platform programme is, from the latest numbers."""
    aud = latest_audience() if aud is None else aud
    out = []
    for key, rule in PLATFORM_RULES.items():
        a = aud.get(rule['platform'], {})
        missing, parts = [], []
        for metric, need in rule['all'].items():
            have = _num(a.get(metric))
            parts.append(min(have / need, 1))
            if have < need:
                missing.append(f'{metric} {have:,.0f}/{need:,}')
        if rule['any_of']:
            best, best_gap = 0.0, ''
            for group in rule['any_of']:
                (metric, need), = group.items()
                have = _num(a.get(metric))
                if have / need >= best:
                    best = min(have / need, 1)
                    best_gap = '' if have >= need else f'{metric} {have:,.0f}/{need:,}'
            parts.append(best)
            if best_gap:
                missing.append(best_gap)
        out.append({'programme': key, 'platform': rule['platform'],
                    'progress': sum(parts) / len(parts) if parts else 0,
                    'eligible': not missing and bool(a), 'missing': missing,
                    'known': bool(a), 'as_of': a.get('date', ''),
                    'pays': rule['pays'], 'where': rule['where']})
    return out


def stale_rules(today: date | None = None) -> list[str]:
    today = today or date.today()
    return [k for k, r in PLATFORM_RULES.items()
            if (today - date.fromisoformat(r['checked'])).days > RULES_STALE_DAYS]


# ─────────────────────────────────────────────────────────────────────────────
#  DEALS AND THE FIREWALL
# ─────────────────────────────────────────────────────────────────────────────

def deals() -> list[dict]:
    return _read_json(DEALS, [])


def _asks_for_news(text: str) -> str:
    text = text or ''
    for n in _OUR_NAME:
        text = re.sub(re.escape(n), ' ', text, flags=re.I)
    low = text.lower()
    for w in NEWS_WORDS:
        if re.search(rf'(?<![\w]){re.escape(w.lower())}(?![\w])', low) or \
                (not w.isascii() and w in text):
            return w
    return ''


def check_deal(d: dict, going_live: bool = False) -> list[str]:
    """Every rule the firewall holds a deal to. Empty list = clean.

    A refusal here is never waived: there is no flag. A story bought is a
    newsroom sold, and the readers are the only asset this company has."""
    errs = []
    prod = d.get('product')
    if prod not in PRODUCTS:
        errs.append(f'AD-01: product {prod!r} is not on the list — money buys '
                    f'{", ".join(PRODUCTS)}; never a news story or slot')
    ask = _asks_for_news(' '.join(str(d.get(k, '')) for k in
                                  ('deliverable', 'notes', 'next_action')))
    if ask:
        errs.append(f'AD-02: the deal mentions "{ask}" — what is news, and '
                    f'what is removed, is decided by the newsroom, never sold')
    cat = d.get('category')
    if cat not in CATEGORIES:
        errs.append(f'AD-03: category {cat!r} is not one of {", ".join(CATEGORIES)}')
    elif cat in PROHIBITED:
        errs.append(f'AD-04: we do not take {cat} advertising ({PROHIBITED[cat]})')
    if (cat == 'political' or d.get('political')) and not d.get('mcmc_ref'):
        errs.append('AD-05: a political ad needs its MCMC pre-certificate '
                    'number in mcmc_ref before it can go live')
    if prod in PRODUCTS and PRODUCTS[prod]['label'] and \
            d.get('label') != PRODUCTS[prod]['label']:
        errs.append(f'AD-06: {prod} carries the label '
                    f'"{PRODUCTS[prod]["label"]}" on the work itself')
    if not d.get('names'):
        errs.append('AD-07: names — the client\'s name as it would appear in a '
                    'story, in Kannada and English — so a conflict is caught')
    if going_live:
        if not d.get('cleared_by'):
            errs.append('AD-08: a person clears a deal before it goes live: '
                        'python3 scripts/business.py deal clear ID --by NAME')
        if cat in SENSITIVE and not os.path.exists(ad_report_path(d.get('id', ''))):
            errs.append(f'AD-09: {cat} — the ad-standards desk reads the claims '
                        f'first (business/reports/ad_{d.get("id")}.md)')
    return errs


def ad_report_path(deal_id: str) -> str:
    return os.path.join(REPORTS, f'ad_{deal_id}.md')


def _next_id(existing: list[dict], today: date) -> str:
    prefix = today.strftime('%Y-%m')
    n = sum(1 for d in existing if str(d.get('id', '')).startswith(prefix))
    return f'{prefix}-{n + 1:03d}'


def add_deal(d: dict, today: date | None = None) -> dict:
    today = today or date.today()
    all_ = deals()
    prod = d.get('product')
    d = {'id': _next_id(all_, today), 'stage': 'lead', 'created': today.isoformat(),
         'label': PRODUCTS.get(prod, {}).get('label', ''), 'names': [],
         'political': False, 'mcmc_ref': '', 'cleared_by': '', 'cleared_at': '',
         'next_action': '', 'next_date': '', 'deliverable': '', 'notes': '',
         'history': [], **{k: v for k, v in d.items() if v not in (None, '')}}
    errs = [e for e in check_deal(d) if not e.startswith(('AD-05', 'AD-08'))]
    if errs:
        raise BizError(errs[0][:5], '; '.join(errs))
    all_.append(d)
    _write_json(DEALS, all_)
    return d


def _find(all_: list[dict], deal_id: str) -> dict:
    for d in all_:
        if d.get('id') == deal_id:
            return d
    raise BizError('BIZ-03', f'no deal {deal_id}')


def move_deal(deal_id: str, stage: str, today: date | None = None,
              **fields) -> dict:
    today = today or date.today()
    if stage not in STAGES:
        raise BizError('BIZ-03', f'stage must be one of {", ".join(STAGES)}')
    all_ = deals()
    d = _find(all_, deal_id)
    d.update({k: v for k, v in fields.items() if v not in (None, '')})
    if stage in ('live', 'paid') or (stage == 'agreed'):
        errs = check_deal(d, going_live=stage in ('live', 'paid'))
        if stage == 'agreed':
            errs = [e for e in errs if not e.startswith(('AD-08', 'AD-09'))]
        if errs:
            raise BizError(errs[0][:5], '; '.join(errs))
    d.setdefault('history', []).append(f'{today.isoformat()} {d.get("stage")}→{stage}')
    d['stage'] = stage
    _write_json(DEALS, all_)
    return d


def clear_deal(deal_id: str, by: str, today: date | None = None) -> dict:
    """A PERSON clears a deal to go live. Never called by an agent with a name
    the owner did not give in chat — the same rule as verify.py (D59)."""
    by = (by or '').strip()
    if len(by) < 2:
        raise BizError('AD-08', 'clear needs the name of the person clearing it')
    all_ = deals()
    d = _find(all_, deal_id)
    errs = [e for e in check_deal(d) if not e.startswith('AD-08')]
    if d.get('category') in SENSITIVE and not os.path.exists(ad_report_path(deal_id)):
        errs.append(f'AD-09: the ad-standards desk has not read {deal_id} yet')
    if errs:
        raise BizError(errs[0][:5], '; '.join(errs))
    d['cleared_by'] = by
    d['cleared_at'] = (today or date.today()).isoformat()
    _write_json(DEALS, all_)
    return d


def active_sponsors(today: date | None = None, days: int = 90) -> list[dict]:
    """Anyone who is paying us, about to, or did within `days`."""
    today = today or date.today()
    out = []
    for d in deals():
        if d.get('stage') in ('agreed', 'live'):
            out.append(d)
        elif d.get('stage') == 'paid':
            last = max([h.split()[0] for h in d.get('history', [])] or
                       [d.get('created', '1970-01-01')])
            if (today - date.fromisoformat(last)).days <= days:
                out.append(d)
    return out


_STORY_TEXT = ('headline', 'deck', 'points', 'takeaway', 'reel_line',
               'reel_points', 'narration_script', 'quote', 'location')


def conflicts(edition: dict, today: date | None = None) -> list[str]:
    """Stories that name a current sponsor (firewall rule 5). The editor
    decides — disclose it, or have someone else judge the story."""
    sponsors = active_sponsors(today)
    out = []
    for i, st in enumerate(edition.get('stories') or [], 1):
        text = json.dumps({k: st.get(k) for k in _STORY_TEXT}, ensure_ascii=False)
        for d in sponsors:
            for name in d.get('names') or []:
                if len(name.strip()) >= 3 and name.strip().lower() in text.lower():
                    out.append(f'story {i} names "{name}", a current sponsor '
                               f'(deal {d["id"]}) — disclose it on the story, '
                               f'or let someone with no stake judge it '
                               f'(docs/ADVERTISING.md §3)')
                    break
    return out


def follow_ups(today: date | None = None) -> list[dict]:
    today = today or date.today()
    return [d for d in deals()
            if d.get('stage') not in ('paid', 'lost') and d.get('next_date')
            and d['next_date'] <= today.isoformat()]


# ─────────────────────────────────────────────────────────────────────────────
#  THE ONE-SCREEN VIEW
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Status:
    month: dict
    fy: dict
    gst: dict
    money_rows: int
    monetisation: list[dict]
    audience_age: int | None
    pipeline: dict
    follow_ups: list[dict]
    tools_cover: float | None
    stale_rules: list[str]


def status(today: date | None = None) -> Status:
    today = today or date.today()
    rows = ledger()
    ms, me = month_bounds(today.strftime('%Y-%m'))
    fy = fy_of(today)
    month = totals(rows, ms, me)
    aud = latest_audience()
    dates = [r.get('date') for r in aud.values() if r.get('date')]
    age = (today - date.fromisoformat(max(dates))).days if dates else None
    pipe: dict[str, list] = {s: [] for s in STAGES}
    for d in deals():
        pipe.setdefault(d.get('stage', 'lead'), []).append(d)
    tools = month['by_expense'].get('ai_tools', 0)
    return Status(month=month, fy=totals(rows, date(fy, 4, 1), date(fy + 1, 3, 31)),
                  gst=gst_watch(rows, today), money_rows=len(rows),
                  monetisation=monetisation(aud), audience_age=age,
                  pipeline=pipe, follow_ups=follow_ups(today),
                  tools_cover=(month['income'] / tools) if tools else None,
                  stale_rules=stale_rules(today))


def validate_books() -> list[str]:
    """Every row and deal against the rules — for health and the steward."""
    problems = []
    for n, r in enumerate(ledger(), 2):
        try:
            check_money(r)
        except BizError as e:
            problems.append(f'ledger.csv line {n}: {e}')
    for d in deals():
        live = d.get('stage') in ('live', 'paid')
        for e in check_deal(d, going_live=live):
            if not live and e.startswith('AD-05'):
                continue
            problems.append(f'deal {d.get("id")}: {e}')
    return problems
