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
# The text model, overridable without editing code. Google retires these on
# their own schedule — gemini-2.5-flash went 404 for new users while this
# pipeline was still asking for it every morning, and the only sign was a line
# in a log nobody reads. See _optional_extract: a model that is GONE is now
# reported loudly and not retried.
TEXT_MODEL = os.environ.get('OORMANI_TEXT_MODEL', 'gemini-3.6-flash')
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


def _shared_urls(tips: list[Tip]) -> set[str]:
    """URLs more than one tip resolved to.

    A genuine per-article scrape gives every tip its own URL. A URL shared by
    two or more tips is structurally a listing or index page, whatever it
    looks like — Udayavani's district page embeds every article's JSON for
    React hydration, and a naive <h2>/<h3> regex over the raw HTML matches
    headline text sitting INSIDE that embedded JSON, with no real per-article
    link next to it, so the scraper falls back to the page URL for every item.
    fetch_body() would then fetch that one page once and hand the same wrong
    text to every tip that shares it, each one wrongly stamped body_source
    'article' — which is worse than no body, because it CLAIMS grounding it
    does not have, and the groundedness pass then flags real facts as invented
    because it is comparing against somebody else's headline.
    This is a structural check, not a list of known-bad URLs, so it catches
    the same class of bug in any scraper, including ones written later.
    """
    seen: dict[str, int] = {}
    for t in tips:
        if t.source_url:
            seen[t.source_url] = seen.get(t.source_url, 0) + 1
    return {u for u, n in seen.items() if n > 1}


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
    shared = _shared_urls(tips)
    if shared:
        log(f'  bodies:         {len(shared)} URL(s) shared by more than one '
            f'tip — that is a listing page, not an article. Skipped rather '
            f'than mislabelled.')
    # Crime and minor tips first: those are the ones where an invented detail
    # is not an embarrassment but an exposure.
    order = sorted(range(len(tips)),
                   key=lambda i: 0 if tips[i].risk != 'normal' else 1)
    for i in order[:BODY_BUDGET]:
        t = tips[i]
        if t.source_url in shared:
            continue
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


def _place_bridge() -> dict[str, str]:
    """Latin place name → Kannada, reusing the TTS pronunciation lexicon.

    Coastal headlines are routinely mixed script: "Udupi: ಅಧಿಕ ಲಾಭದ ಆಮಿಷ".
    The lead then writes ಉಡುಪಿಯಲ್ಲಿ, which appears nowhere in the source as
    far as a byte comparison is concerned — so the place name, the one thing
    we are most confident IS supported, got flagged as invented.

    assets/pronunciation.json already carries exactly this mapping, because
    the TTS engine needed it for the same names. One file, two uses.
    """
    path = os.path.join(ROOT, 'assets', 'pronunciation.json')
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        return {str(k).lower(): str(v) for k, v in data.items() if k and v}
    except Exception:
        return {}


_PLACES = _place_bridge()


def _expand_abbreviations(text: str) -> str:
    """ರೂ. → ರೂಪಾಯಿ, ಕಿ.ಮೀ → ಕಿಲೋಮೀಟರ್, and the rest.

    A source headline writes `ಲಕ್ಷಾಂತರ ರೂ.` and the lead writes `ಲಕ್ಷಾಂತರ
    ರೂಪಾಯಿ`. That is the same fact spelled out, not a new one — but a byte
    comparison sees an unsupported word and flags the money, which is exactly
    the kind of false alarm that trains an editor to skip the flags.

    `brand/voice.SPOKEN_ABBREV` already holds this table, because the TTS
    engine needed the identical expansions to read a bulletin aloud. Importing
    it keeps one list rather than two that drift.
    """
    try:
        from brand.voice import SPOKEN_ABBREV, _ABBREV_RE
    except Exception:
        return text
    return _ABBREV_RE.sub(lambda m: SPOKEN_ABBREV[m.group(0)], text)


# Kannada agglutinates and it derives, and neither is an invented fact.
#
# The source writes ಉಡುಪಿ and the lead writes ಉಡುಪಿಯಲ್ಲಿ. The source writes
# ಮಳೆ and the lead writes ಮಳೆಯಾಗುವ. The source writes ವಂಚನೆ and the lead
# writes ವಂಚಿಸಲಾಗಿದೆ. Flagging any of those is how a check meant to catch an
# invented helpline number ends up firing on thirty leads out of thirty-two —
# at which point the editor stops reading it and it protects nothing. That
# happened on the first real run after this was built.
#
# So: match in BOTH directions on a stem, and skip tokens that are plainly
# verb forms. What survives is what the check is actually for — names,
# places, institutions and figures that appear nowhere in the source.
_MIN_STEM = 4

# Endings that mark a Kannada verbal or participial form. A verb is how the
# lead says the thing; it is not a fact the lead is asserting. Nothing
# dangerous — no name, no number, no institution — ends like this.
_VERB_TAILS = (
    'ಲಾಗಿದೆ', 'ಲಾಗಿತ್ತು', 'ಲಾಗುತ್ತದೆ', 'ಲಾಗುವ',
    'ುತ್ತಿದ್ದ', 'ುತ್ತಿದೆ', 'ುತ್ತಾರೆ', 'ುತ್ತದೆ',
    'ಾಗಿದೆ', 'ಾಗಿತ್ತು', 'ಾಗುವ', 'ಾಗಿ',
    'ಿಸಲಾಗಿದೆ', 'ಿಸಿದ', 'ಿಸುವ', 'ಿಸಲು',
    'ಿದ್ದಾರೆ', 'ಿದ್ದಾನೆ', 'ಿದ್ದಳು', 'ಿದ್ದು', 'ಿದರು', 'ಿತ್ತು', 'ಿದೆ', 'ಿದ',
    'ಯಾಗಿದೆ', 'ವಾಗಿದೆ', 'ಕೊಂಡು', 'ವುದು', 'ುವುದು',
)


def _is_verb_form(token: str) -> bool:
    """A Kannada verb or participle. Deliberately length-gated: short words
    ending in ಿದ are often nouns, and over-skipping would hide real facts."""
    return len(token) > 5 and any(token.endswith(t) for t in _VERB_TAILS)


def _kannada_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if 'ಀ' <= c <= '೿') / len(letters)


# The marker returned when the lead and its source are in different scripts.
# Google News hands us English headlines; the model writes the lead in
# Kannada. Every Kannada word then "appears nowhere in the source", which is
# true and completely useless — it flags the whole lead and tells the editor
# nothing about which part to doubt.
#
# Saying "this one cannot be checked" is a different and far more honest
# statement than "these words are invented", and it points at the right
# action: open the link and read it, because nothing here can help you.
UNCHECKABLE = '⟨source is not in Kannada — open the link⟩'


def _supported(token: str, haystack_tokens: set, haystack: str) -> bool:
    low = token.lower()
    if low in haystack:
        return True
    # Latin and digits do not agglutinate — an exact miss is a real miss.
    if not any('ಀ' <= ch <= '೿' for ch in low):
        return False
    # The lead's word GREW OUT OF a source word:  ಮಳೆ → ಮಳೆಯಾಗುವ
    for h in haystack_tokens:
        if low.startswith(h[:_MIN_STEM]):
            return True
    # The lead's word is an inflection of a source word: ಉಡುಪಿಯಲ್ಲಿ → ಉಡುಪಿ
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
    # A Kannada lead against an English source cannot be grounded word by
    # word, and pretending otherwise flags everything. Say so instead.
    if _kannada_share(lead) > 0.5 and _kannada_share(source_text) < 0.15:
        return [UNCHECKABLE]

    # The source's abbreviations, spelled out the way the lead spells them.
    hay = _normalise(_expand_abbreviations(source_text))
    # Bring the Kannada spelling of any Latin place name in the source into
    # the haystack, so "Udupi:" in the headline supports ಉಡುಪಿಯಲ್ಲಿ in the lead.
    for latin, kannada in _PLACES.items():
        if latin in hay:
            hay += ' ' + kannada.lower()
    hay_tokens = {t for t in hay.split() if len(t) >= _MIN_STEM}
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
        # A verb is how the lead says the thing, not a claim it is making.
        if not is_number and _is_verb_form(low):
            continue
        if _supported(tok, hay_tokens, hay):
            continue
        if tok not in out:
            out.append(tok)
    return out[:8]


def audit_groundedness(tips: list[Tip]) -> int:
    """Flag every lead against the text it was written from. Returns flagged."""
    flagged = 0
    cross = 0
    for t in tips:
        if not t.lead_kn or t.lead_kn.strip() == t.headline.strip():
            continue                       # nothing was generated; nothing to audit
        haystack = ' '.join([t.headline, t.body or '', t.snippet or ''])
        t.unsupported = unsupported_tokens(t.lead_kn, haystack)
        if t.unsupported == [UNCHECKABLE]:
            cross += 1
        elif t.unsupported:
            flagged += 1
    if flagged:
        log(f'  groundedness:   {flagged} lead(s) carry words the source does '
            f'not — flagged for the editor, not dropped')
    else:
        log('  groundedness:   every checkable lead is anchored in its source')
    if cross:
        log(f'                  {cross} could not be checked (source not in '
            f'Kannada) — the sheet says so rather than flagging every word')
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


# Whether the Kannada-lead pass actually ran. The sheet says so either way:
# an editor reading raw scraped headlines should know that is what they are.
_EXTRACT_STATE: dict = {'ran': False, 'error': ''}


def _optional_extract(tips: list[Tip]) -> None:
    """Optional Kannada leads from supplied text. Never invents. Never required."""
    api_key = load_gemini_key('text')
    if not api_key:
        log('No GEMINI_API_KEY_TEXT / GEMINI_API_KEY — writing raw tips only.')
        _EXTRACT_STATE['error'] = 'no text API key'
        return
    try:
        from google import genai
    except ImportError:
        log('google.genai not installed — writing raw tips only.')
        _EXTRACT_STATE['error'] = 'google-genai not installed'
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
                model=TEXT_MODEL,
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
            _EXTRACT_STATE['ran'] = True
            _EXTRACT_STATE['error'] = ''
            return
        except Exception as e:
            last_error = e
            # A retired model, a bad key or a refused request will fail
            # identically on all three attempts. Retrying a permanent error
            # costs twelve seconds of a morning and tells you nothing.
            msg = str(e)
            permanent = any(m in msg for m in (
                'NOT_FOUND', 'no longer available', 'PERMISSION_DENIED',
                'API key not valid', 'INVALID_ARGUMENT', 'UNAUTHENTICATED'))
            if permanent:
                log(f'  extract pass abandoned — this will not succeed on a retry.')
                break
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))

    # Loudly, and on the sheet itself. The failure mode this replaces was a
    # tip sheet that looked completely normal while carrying no Kannada leads
    # at all, because the model behind it had been retired weeks earlier.
    err = str(last_error)
    if 'no longer available' in err or 'NOT_FOUND' in err:
        log('  ' + '=' * 66)
        log(f'  THE TEXT MODEL {TEXT_MODEL!r} IS GONE.')
        log('  Google has retired it. The sheet below is RAW HEADLINES — no')
        log('  Kannada leads were written. Set a current model and re-run:')
        log('      export OORMANI_TEXT_MODEL=<current-flash-model>')
        log('  ' + '=' * 66)
        _EXTRACT_STATE['error'] = f'model {TEXT_MODEL} is retired'
    else:
        _EXTRACT_STATE['error'] = err[:160]
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
    # If the Kannada-lead pass did not run, SAY SO here. A sheet of raw scraped
    # headlines looks identical to a sheet of written leads at a glance, and
    # the difference matters: one has been through a model that was told to
    # stay inside the source text, the other has not been through anything.
    if not _EXTRACT_STATE.get('ran'):
        why = _EXTRACT_STATE.get('error') or 'the lead pass did not run'
        lines += [
            f'> ⚠️ **No Kannada leads were written** — {why}.',
            '>',
            '> Everything below is the scraped headline, verbatim. That is not',
            '> worse, it is just different: nothing has been summarised, so',
            '> nothing has been summarised wrongly. Write the leads yourself,',
            '> or fix the cause and re-run.',
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
        if t.unsupported == [UNCHECKABLE]:
            lines.append(
                '- 🔎 **Cannot be checked here** — the source is not in '
                'Kannada, so nothing in this sheet can tell you which parts '
                'of the lead came from it. Open the link.')
        elif t.unsupported:
            lines.append(
                f'- ⚠️ **VERIFY** — not found in anything we fetched: '
                + ', '.join(f'`{w}`' for w in t.unsupported))
        if t.body_source == 'article':
            lines.append(f'- From the article: {t.body[:600]}'
                         + ('…' if len(t.body) > 600 else ''))
        elif t.snippet:
            lines.append(f'- From source: {t.snippet}')
        lines.append('')
    flagged = sum(1 for t in tips
                  if t.unsupported and t.unsupported != [UNCHECKABLE])
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


HEARTBEAT = os.path.join(ROOT, 'logs', 'last_fetch.json')


def _heartbeat(ok: bool, counts: dict | None = None, reason: str = '') -> None:
    """Record that a fetch happened, and how it went.

    Deliberately written INSIDE the repository, by the script itself, rather
    than by whatever schedules it. The 06:05 job on this machine is owned by
    something outside this project, and it may be replaced, renamed or moved
    without anyone touching this code — but any of those still ends up calling
    this function, because they all end up calling this script.

    That is the whole point of issue #19. The need was never "own the
    scheduler"; it was "know at 09:00 whether the morning actually ran".
    """
    try:
        os.makedirs(os.path.dirname(HEARTBEAT), exist_ok=True)
        with open(HEARTBEAT, 'w', encoding='utf-8') as fh:
            json.dump({
                'at': datetime.now().isoformat(timespec='seconds'),
                'ok': ok,
                'reason': reason,
                'counts': counts or {},
                'extractor': _extractor() or 'none',
                'text_model': TEXT_MODEL,
                'leads_written': bool(_EXTRACT_STATE.get('ran')),
            }, fh, indent=2, ensure_ascii=False)
            fh.write('\n')
    except OSError:
        pass


def _write_failure(reason: str) -> None:
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(FAIL_MARKER, 'w', encoding='utf-8') as f:
        f.write(f'{datetime.now().isoformat()} | {reason}\n')
    _heartbeat(False, reason=reason)
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
        'text_model': TEXT_MODEL,
        'leads_written': bool(_EXTRACT_STATE.get('ran')),
        'leads_error': _EXTRACT_STATE.get('error', ''),
        'counts': {
            'tips': len(unique),
            'full_articles': sum(1 for t in unique if t.body_source == 'article'),
            'rss_only': sum(1 for t in unique if t.body_source == 'rss'),
            'headline_only': sum(1 for t in unique if not t.body_source),
            'flagged_unsupported': sum(1 for t in unique
                                       if t.unsupported and t.unsupported != [UNCHECKABLE]),
            'uncheckable_cross_script': sum(1 for t in unique
                                            if t.unsupported == [UNCHECKABLE]),
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
    _heartbeat(True, counts=payload['counts'])
    log(f'✅ {len(unique)} tips → {TODAY_MD}')
    print('\n--- FIRST 3 TIPS ---\n')
    print('\n'.join(md.split('\n\n')[:6]))
    print('\n--------------------\n')
    print('Open inbox/today.md. Confirm. Then start with content.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
