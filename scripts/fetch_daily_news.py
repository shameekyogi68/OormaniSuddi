"""Daily news intake for ಊರ್ಮನಿ ಸುದ್ದಿ.

This is a TIP SHEET, not copy. Headlines and RSS descriptions are collected
from coastal sources. Gemini, if a text key is present, may cluster and write
a one-line Kannada lead from the supplied text only. It may not invent
officials, hospitals, vehicle models, or causes.

Output:
  inbox/today.md   — what the editor reads
  inbox/today.json — the same tips, machine-readable
  inbox/today.txt  — identical to the markdown (legacy path)

Nothing here becomes editions/{date}.json until the editor confirms.
Do not schedule this job until this tip-sheet mode is the only path.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand.voice import load_gemini_key

INBOX_DIR = os.path.join(ROOT, 'inbox')
TODAY_MD = os.path.join(INBOX_DIR, 'today.md')
TODAY_JSON = os.path.join(INBOX_DIR, 'today.json')
TODAY_TXT = os.path.join(INBOX_DIR, 'today.txt')
FAIL_MARKER = os.path.join(INBOX_DIR, '.fetch_failed')
MIN_SOURCES = 3
MAX_RETRIES = 3
BACKOFF_BASE = 4
HTTP_TIMEOUT = 10
USER_AGENT = (
    'OormaniSuddi-newsroom/1.0 (+https://instagram.com/oormanisuddi; '
    'local Kannada news tip sheet)'
)

UDUPI_KW = (
    'ಉಡುಪಿ', 'ಕುಂದಾಪುರ', 'ಬೈಂದೂರು', 'ಬ್ರಹ್ಮಾವರ', 'ಕಾರ್ಕಳ',
    'ಕಾಪು', 'ಹೆಬ್ರಿ', 'ಮಣಿಪಾಲ', 'ಕರಾವಳಿ', 'ಮಂಗಳೂರು',
    'udupi', 'kundapura', 'byndoor', 'brahmavar', 'karkala',
    'kaup', 'hebri', 'manipal', 'mangalore', 'mangaluru',
)

CRIME_MARK = ('ಕೊಲೆ', 'ಹತ್ಯೆ', 'ಬಂಧನ', 'ದಾಳಿ', 'ಅತ್ಯಾಚಾರ', 'ಹಲ್ಲೆ',
              'murder', 'arrest', 'rape', 'assault')
MINOR_MARK = ('ಬಾಲಕ', 'ಬಾಲಕಿ', 'ಮಗು', 'ಶಾಲೆ', 'minor', 'child', 'schoolboy')


@dataclass
class Tip:
    headline: str
    source_name: str
    source_url: str
    snippet: str = ''
    taluk: str = ''
    risk: str = 'normal'   # normal | crime | minor
    lead_kn: str = ''
    fetched_at: str = ''
    needs_editor: bool = True
    # The article text this tip's lead is allowed to rest on. Empty means the
    # tip is a headline and nothing more, and the sheet says so.
    body: str = ''
    body_source: str = ''  # 'article' | 'rss' | '' — how much we actually have
    # Tokens in the generated lead that do NOT appear in the source text. This
    # is the whole point of the groundedness pass: it does not decide whether
    # the lead is true, it points the editor's eye at the two or three words
    # that are not in anything we fetched.
    unsupported: list = None

    def __post_init__(self):
        if self.unsupported is None:
            self.unsupported = []


def log(msg: str) -> None:
    print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}')


def log_err(msg: str) -> None:
    print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] ERROR: {msg}', file=sys.stderr)


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def _guess_taluk(text: str) -> str:
    pairs = (
        ('ಬೈಂದೂರು', 'ಬೈಂದೂರು'), ('byndoor', 'ಬೈಂದೂರು'),
        ('ಕುಂದಾಪುರ', 'ಕುಂದಾಪುರ'), ('kundapur', 'ಕುಂದಾಪುರ'),
        ('ಬ್ರಹ್ಮಾವರ', 'ಬ್ರಹ್ಮಾವರ'), ('brahmavar', 'ಬ್ರಹ್ಮಾವರ'),
        ('ಕಾರ್ಕಳ', 'ಕಾರ್ಕಳ'), ('karkala', 'ಕಾರ್ಕಳ'),
        ('ಕಾಪು', 'ಕಾಪು'), ('kaup', 'ಕಾಪು'),
        ('ಹೆಬ್ರಿ', 'ಹೆಬ್ರಿ'), ('hebri', 'ಹೆಬ್ರಿ'),
        ('ಮಣಿಪಾಲ', 'ಮಣಿಪಾಲ'), ('manipal', 'ಮಣಿಪಾಲ'),
        ('ಉಡುಪಿ', 'ಉಡುಪಿ'), ('udupi', 'ಉಡುಪಿ'),
    )
    low = text.lower()
    for needle, taluk in pairs:
        if needle.lower() in low:
            return taluk
    return ''


def _risk(text: str) -> str:
    low = text.lower()
    if any(m.lower() in low for m in MINOR_MARK):
        return 'minor'
    if any(m.lower() in low for m in CRIME_MARK):
        return 'crime'
    return 'normal'


def _cdata(raw: str) -> str:
    return re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', raw, flags=re.S).strip()


def _rss_items(url: str) -> list[tuple[str, str, str]]:
    """Return (title, link, description) from an RSS/Atom document."""
    raw = _http_get(url)
    text = raw.decode('utf-8', errors='replace')
    out: list[tuple[str, str, str]] = []
    try:
        root = ET.fromstring(raw)
        for item in root.findall('.//item') + root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title_el = item.find('title')
            if title_el is None:
                title_el = item.find('{http://www.w3.org/2005/Atom}title')
            title = _cdata((title_el.text or '') if title_el is not None else '')
            link_el = item.find('link')
            if link_el is None:
                link_el = item.find('{http://www.w3.org/2005/Atom}link')
            link = ''
            if link_el is not None:
                link = (link_el.get('href') or link_el.text or '').strip()
            desc_el = item.find('description')
            if desc_el is None:
                desc_el = item.find('{http://www.w3.org/2005/Atom}summary')
            desc = _cdata((desc_el.text or '') if desc_el is not None else '')
            desc = re.sub(r'<[^>]+>', ' ', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()
            if len(title) > 12:
                out.append((title, link, desc))
        if out:
            return out
    except ET.ParseError:
        pass
    titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', text) or \
             re.findall(r'<title>(.*?)</title>', text)
    links = re.findall(r'<link>(.*?)</link>', text)
    for i, t in enumerate(titles[1:]):
        link = links[i + 1].strip() if i + 1 < len(links) else url
        if len(t.strip()) > 12:
            out.append((t.strip(), link, ''))
    return out


def scrape_udayavani_html() -> list[Tip]:
    page = 'https://www.udayavani.com/district-news/udupi-news'
    now = datetime.now().isoformat(timespec='seconds')
    try:
        html = _http_get(page).decode('utf-8', errors='ignore')
        raw = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', html, re.DOTALL)
        tips = []
        for t in raw:
            title = re.sub(r'<[^<]+?>', '', t).strip()
            if len(title) <= 15 or 'ಇನ್ನಷ್ಟು' in title:
                continue
            hrefs = re.findall(r'href="([^"]+)"', t)
            link = hrefs[0] if hrefs else page
            if link.startswith('/'):
                link = 'https://www.udayavani.com' + link
            tips.append(Tip(
                headline=title, source_name='ಉದಯವಾಣಿ', source_url=link,
                taluk=_guess_taluk(title), risk=_risk(title), fetched_at=now))
            if len(tips) >= 12:
                break
        log(f'  Udayavani HTML: {len(tips)} tips')
        return tips
    except Exception as e:
        log(f'  Udayavani HTML: skipped ({type(e).__name__})')
        return []


def scrape_udayavani_rss() -> list[Tip]:
    url = 'https://www.udayavani.com/rss/udupi-district-news'
    now = datetime.now().isoformat(timespec='seconds')
    try:
        tips = []
        for title, link, desc in _rss_items(url)[:10]:
            tips.append(Tip(
                headline=title, source_name='ಉದಯವಾಣಿ',
                source_url=link or url, snippet=desc[:400],
                taluk=_guess_taluk(title + ' ' + desc),
                risk=_risk(title + ' ' + desc), fetched_at=now))
        log(f'  Udayavani RSS:  {len(tips)} tips')
        return tips
    except Exception as e:
        log(f'  Udayavani RSS:  skipped ({type(e).__name__})')
        return []


def scrape_google_news_en() -> list[Tip]:
    q = 'Udupi OR Kundapura OR Byndoor OR Brahmavar OR Karkala OR Kaup OR Hebri when:1d'
    url = ('https://news.google.com/rss/search?q='
           + urllib.parse.quote(q) + '&hl=en-IN&gl=IN&ceid=IN:en')
    now = datetime.now().isoformat(timespec='seconds')
    try:
        tips = []
        for title, link, desc in _rss_items(url)[:15]:
            title = re.sub(r'\s*-\s*[^-]+$', '', title.strip())
            tips.append(Tip(
                headline=title, source_name='Google News',
                source_url=link or url, snippet=desc[:400],
                taluk=_guess_taluk(title + ' ' + desc),
                risk=_risk(title + ' ' + desc), fetched_at=now))
        log(f'  Google News EN: {len(tips)} tips')
        return tips
    except Exception as e:
        log(f'  Google News EN: skipped ({type(e).__name__})')
        return []


def scrape_oneindia_kannada() -> list[Tip]:
    url = 'https://kannada.oneindia.com/rss/kannada-news-fb.xml'
    now = datetime.now().isoformat(timespec='seconds')
    try:
        items = _rss_items(url)
        local, rest = [], []
        for title, link, desc in items:
            blob = (title + ' ' + desc).lower()
            row = Tip(
                headline=title, source_name='OneIndia Kannada',
                source_url=link or url, snippet=desc[:400],
                taluk=_guess_taluk(title + ' ' + desc),
                risk=_risk(title + ' ' + desc), fetched_at=now)
            if any(kw.lower() in blob for kw in UDUPI_KW):
                local.append(row)
            else:
                rest.append(row)
        tips = local[:8] + rest[:5]
        log(f'  OneIndia KN:    {len(tips)} tips ({len(local)} coastal)')
        return tips
    except Exception as e:
        log(f'  OneIndia KN:    skipped ({type(e).__name__})')
        return []


# ─────────────────────────────────────────────────────────────────────────────
#  ARTICLE BODIES
#  A headline plus an RSS blurb is thin material. Where the publisher actually
#  serves the article, fetching it turns "write five sentences from a headline"
#  into "condense five paragraphs" — which is the difference between a model
#  inventing a police jurisdiction and a model summarising one.
#
#  trafilatura is optional on purpose. If it is not installed the tip sheet
#  still works, it just says `source: headline only` and the editor knows to
#  open the link. A missing dependency must never silently downgrade the
#  honesty of the sheet.
# ─────────────────────────────────────────────────────────────────────────────

BODY_MIN_CHARS = 220
BODY_MAX_CHARS = 4000
BODY_BUDGET = 12          # articles fetched per run; be a polite guest


def _extractor():
    try:
        import trafilatura            # noqa: F401
        return 'trafilatura'
    except ImportError:
        return ''


def fetch_body(url: str) -> str:
    """The article text, or '' when we cannot honestly get it."""
    if not url or not url.startswith('http'):
        return ''
    if not _extractor():
        return ''
    try:
        import trafilatura
        raw = _http_get(url).decode('utf-8', errors='replace')
        text = trafilatura.extract(
            raw, include_comments=False, include_tables=False,
            favor_precision=True) or ''
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) < BODY_MIN_CHARS:
            return ''
        return text[:BODY_MAX_CHARS]
    except Exception:
        return ''


def attach_bodies(tips: list[Tip]) -> int:
    """Fill `body` where the publisher serves the article. Returns how many."""
    if not _extractor():
        log('  bodies:         trafilatura not installed — headlines only.')
        log('                  pip install trafilatura  (this is the single '
            'biggest accuracy upgrade available to the intake)')
        for t in tips:
            if t.snippet:
                t.body, t.body_source = t.snippet, 'rss'
        return 0
    got = 0
    # Crime and minor tips first: those are the ones where an invented detail
    # is not an embarrassment but an exposure.
    order = sorted(range(len(tips)),
                   key=lambda i: 0 if tips[i].risk != 'normal' else 1)
    for i in order[:BODY_BUDGET]:
        t = tips[i]
        body = fetch_body(t.source_url)
        if body:
            t.body, t.body_source = body, 'article'
            got += 1
        elif t.snippet:
            t.body, t.body_source = t.snippet, 'rss'
    for t in tips:
        if not t.body and t.snippet:
            t.body, t.body_source = t.snippet, 'rss'
    log(f'  bodies:         {got} full articles, '
        f'{sum(1 for t in tips if t.body_source == "rss")} from RSS text')
    return got


# ─────────────────────────────────────────────────────────────────────────────
#  GROUNDEDNESS
#  The second cheap pass. It does not judge whether a lead is TRUE — nothing
#  here can. It asks a narrower question a machine can actually answer: does
#  every number, place and proper noun in this lead appear in the text we
#  fetched? Anything that does not is flagged, and the editor's eye goes to
#  the two or three words that matter instead of to all forty.
# ─────────────────────────────────────────────────────────────────────────────

# Words a Kannada lead can carry without them appearing in an English source,
# and vice versa. These are grammar, not claims.
_FUNCTION_WORDS = {
    'ಮತ್ತು', 'ಅಥವಾ', 'ಎಂದು', 'ಇದೆ', 'ಆಗಿದೆ', 'ಎಂಬ', 'ಈ', 'ಆ', 'ಅವರು',
    'ನಂತರ', 'ಬಳಿಕ', 'ಜೊತೆಗೆ', 'ಬಗ್ಗೆ', 'ಮೇಲೆ', 'ಕುರಿತು', 'ಇಲ್ಲ',
    'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for',
    'is', 'was', 'were', 'has', 'have', 'said', 'says',
}

_TOKEN = re.compile(r'[ಀ-೿]{3,}|[A-Z][A-Za-z]{2,}|\d[\d.,]*')


def _normalise(text: str) -> str:
    return re.sub(r'[^\wಀ-೿]+', ' ', text.lower())


# Kannada agglutinates: the source writes ಉಡುಪಿ and the lead writes
# ಉಡುಪಿಯಲ್ಲಿ, ಉಡುಪಿಗೆ, ಉಡುಪಿಯ. A case ending is grammar, not an invented fact,
# so a token counts as supported when the source carries any stem of it down
# to this length. Below four characters a "stem" matches everything and the
# check stops meaning anything.
_MIN_STEM = 4


def _supported(token: str, haystack: str) -> bool:
    low = token.lower()
    if low in haystack:
        return True
    # Latin and digits do not agglutinate — an exact miss is a real miss.
    if not any('ಀ' <= ch <= '೿' for ch in low):
        return False
    for cut in range(len(low) - 1, _MIN_STEM - 1, -1):
        if low[:cut] in haystack:
            return True
    return False


def unsupported_tokens(lead: str, source_text: str) -> list[str]:
    """Numbers, places and proper nouns in `lead` that the source never says.

    Deliberately crude and deliberately over-eager. A false flag costs the
    editor a glance; a missed one costs a helpline number that rings nobody.
    """
    if not lead.strip() or not source_text.strip():
        return []
    hay = _normalise(source_text)
    out: list[str] = []
    for tok in _TOKEN.findall(lead):
        low = tok.lower()
        if low in _FUNCTION_WORDS:
            continue
        # The length guard is for words, never for figures. "45 ಮಂದಿ" is two
        # characters and it is the single most dangerous thing a model can
        # supply — a casualty count, a rupee amount, a helpline number.
        is_number = low[0].isdigit()
        if not is_number and len(low) < 3:
            continue
        if _supported(tok, hay):
            continue
        if tok not in out:
            out.append(tok)
    return out[:8]


def audit_groundedness(tips: list[Tip]) -> int:
    """Flag every lead against the text it was written from. Returns flagged."""
    flagged = 0
    for t in tips:
        if not t.lead_kn or t.lead_kn.strip() == t.headline.strip():
            continue                       # nothing was generated; nothing to audit
        haystack = ' '.join([t.headline, t.body or '', t.snippet or ''])
        t.unsupported = unsupported_tokens(t.lead_kn, haystack)
        if t.unsupported:
            flagged += 1
    if flagged:
        log(f'  groundedness:   {flagged} lead(s) carry words the source does '
            f'not — flagged for the editor, not dropped')
    else:
        log('  groundedness:   every generated lead is anchored in its source')
    return flagged


def deduplicate(tips: list[Tip]) -> list[Tip]:
    seen: set[str] = set()
    unique: list[Tip] = []
    for t in tips:
        norm = re.sub(r'[^\w\s]', '', t.headline.lower())
        norm = re.sub(r'\s+', ' ', norm).strip()
        key = hashlib.md5(norm[:60].encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


EXTRACT_PROMPT = """You are a coastal Karnataka news desk assistant for ಊರ್ಮನಿ ಸುದ್ದಿ.
You receive TIP RECORDS. Each has a source name, a source URL, a headline, and
a `text` field holding whatever we could actually fetch — the full article when
the publisher served it, an RSS summary otherwise, sometimes nothing.

You are CONDENSING, not writing. The single rule everything else follows from:
every word you produce must be traceable to the `text` or the `headline` of
that same record.

Rules:
- Write a one-line Kannada lead using only what is in that record's headline and text.
- Add at most three fact bullets, each one restating something the text says.
- If a detail is not in the text, OMIT it. Do not supply officials, ranks, hospital
  names, vehicle models, road numbers, casualty figures, causes, procedures, or quotes
  that the text does not contain. A short lead is correct; a complete-sounding one is not.
- `text` empty means you have a headline and nothing else: return the headline
  unchanged and facts []. Do not expand it. This is the case the whole tip-sheet
  design exists for.
- Latin numerals only.
- Reply as JSON: an array of objects with keys index (int), lead_kn (string),
  facts (array of strings, max 3).

Tips:
{tips}
"""


def _optional_extract(tips: list[Tip]) -> None:
    """Optional Kannada leads from supplied text. Never invents. Never required."""
    api_key = load_gemini_key('text')
    if not api_key:
        log('No GEMINI_API_KEY_TEXT / GEMINI_API_KEY — writing raw tips only.')
        return
    try:
        from google import genai
    except ImportError:
        log('google.genai not installed — writing raw tips only.')
        return

    payload = [
        {'index': i, 'headline': t.headline,
         'text': (t.body or t.snippet or ''),
         'text_is': t.body_source or 'nothing',
         'source': t.source_name, 'url': t.source_url}
        for i, t in enumerate(tips)
    ]
    prompt = EXTRACT_PROMPT.format(tips=json.dumps(payload, ensure_ascii=False, indent=2))
    client = genai.Client(api_key=api_key)
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f'  extract pass {attempt}/{MAX_RETRIES}…')
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            text = (response.text or '').strip()
            text = re.sub(r'^```json|```$', '', text, flags=re.M).strip()
            rows = json.loads(text)
            for row in rows:
                i = int(row.get('index', -1))
                if 0 <= i < len(tips):
                    lead = (row.get('lead_kn') or '').strip()
                    if lead:
                        tips[i].lead_kn = lead
                    facts = [f.strip() for f in row.get('facts') or [] if str(f).strip()]
                    if facts:
                        tips[i].snippet = ' | '.join(facts[:3])
            log('  extract pass applied (leads only; editor still confirms)')
            return
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
    log(f'  extract pass skipped ({last_error}); raw tips still written.')


def render_markdown(tips: list[Tip], date_s: str) -> str:
    lines = [
        f'# ಊರ್ಮನಿ ಸುದ್ದಿ — tip sheet · {date_s}',
        '',
        'These are TIPS, not copy. Do not paste them into an edition until you',
        'have opened the source URL and confirmed every fact. Crime / minor',
        'items need a human flag before render.',
        '',
        f'{len(tips)} unique tips. Editor must confirm before `start with content`.',
        '',
    ]
    order = {'crime': 0, 'minor': 0, 'normal': 1}
    ranked = sorted(tips, key=lambda t: (
        0 if t.taluk in ('ಬೈಂದೂರು', 'ಕುಂದಾಪುರ') else 1,
        order.get(t.risk, 1),
    ))
    depth = {'article': 'full article text', 'rss': 'RSS summary only',
             '': 'HEADLINE ONLY — nothing below the headline was fetched'}
    for i, t in enumerate(ranked, 1):
        lead = t.lead_kn or t.headline
        lines += [
            f'## {i}. {lead}',
            f'- Source: {t.source_name} — {t.source_url}',
            f'- Taluk: {t.taluk or "—"}',
            f'- Risk: {t.risk}',
            f'- We have: {depth.get(t.body_source, t.body_source)}',
            f'- Needs editor: yes',
        ]
        if t.unsupported:
            lines.append(
                f'- ⚠️ **VERIFY** — not found in anything we fetched: '
                + ', '.join(f'`{w}`' for w in t.unsupported))
        if t.body_source == 'article':
            lines.append(f'- From the article: {t.body[:600]}'
                         + ('…' if len(t.body) > 600 else ''))
        elif t.snippet:
            lines.append(f'- From source: {t.snippet}')
        lines.append('')
    flagged = sum(1 for t in tips if t.unsupported)
    lines += [
        '---',
        '## Before any of this becomes an edition',
        '',
        '1. Open the source URL. Read it. A lead written from a headline is a '
        'headline, whatever it looks like.',
        '2. Anything marked ⚠️ VERIFY is a word the source never used. Either '
        'find it in the source or cut it.',
        '3. Copy only confirmed facts into `editions/YYYY-MM-DD.json`.',
        '4. Every story needs `source_urls`, or '
        '`sources=["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"]`.',
        '5. Every story needs `verified_by: "<your name>"` — the Chief Editor '
        'gate will not write APPROVAL.md without it (D59).',
        '6. AI-card reels are Instagram only. YouTube gets real footage.',
        '',
    ]
    if flagged:
        lines += [f'**{flagged} lead(s) carry unsupported words.** '
                  f'Those are the ones to read first.', '']
    return '\n'.join(lines)


def _write_failure(reason: str) -> None:
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(FAIL_MARKER, 'w', encoding='utf-8') as f:
        f.write(f'{datetime.now().isoformat()} | {reason}\n')
    log(f'Failure marker written: {FAIL_MARKER}')


def main() -> int:
    os.makedirs(INBOX_DIR, exist_ok=True)
    if os.path.exists(FAIL_MARKER):
        os.remove(FAIL_MARKER)

    log('═══ Oormani Suddi tip sheet ═══')
    all_tips: list[Tip] = []
    alive = 0
    for name, scraper in (
        ('Udayavani HTML', scrape_udayavani_html),
        ('Udayavani RSS', scrape_udayavani_rss),
        ('Google News EN', scrape_google_news_en),
        ('OneIndia KN', scrape_oneindia_kannada),
    ):
        rows = scraper()
        if rows:
            alive += 1
            all_tips.extend(rows)
    log(f'Sources alive: {alive}/4 | Raw tips: {len(all_tips)}')
    unique = deduplicate(all_tips)
    log(f'After dedup: {len(unique)} unique tips')
    if len(unique) < MIN_SOURCES:
        msg = f'Only {len(unique)} tips (need {MIN_SOURCES}+). Sources may be down.'
        log_err(msg)
        _write_failure(msg)
        return 1

    attach_bodies(unique)
    _optional_extract(unique)
    audit_groundedness(unique)
    date_s = datetime.now().strftime('%Y-%m-%d')
    md = render_markdown(unique, date_s)
    payload = {
        'kind': 'tip_sheet',
        'date': date_s,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'note': 'Tips only. Editor confirms before any edition JSON.',
        'extractor': _extractor() or 'none (headlines only)',
        'counts': {
            'tips': len(unique),
            'full_articles': sum(1 for t in unique if t.body_source == 'article'),
            'rss_only': sum(1 for t in unique if t.body_source == 'rss'),
            'headline_only': sum(1 for t in unique if not t.body_source),
            'flagged_unsupported': sum(1 for t in unique if t.unsupported),
        },
        'tips': [asdict(t) for t in unique],
    }
    with open(TODAY_MD, 'w', encoding='utf-8') as f:
        f.write(md)
    with open(TODAY_TXT, 'w', encoding='utf-8') as f:
        f.write(md)
    with open(TODAY_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write('\n')
    log(f'✅ {len(unique)} tips → {TODAY_MD}')
    print('\n--- FIRST 3 TIPS ---\n')
    print('\n'.join(md.split('\n\n')[:6]))
    print('\n--------------------\n')
    print('Open inbox/today.md. Confirm. Then start with content.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
