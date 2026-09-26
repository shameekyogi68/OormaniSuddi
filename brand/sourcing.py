"""
ಊರ್ಮನಿ ಸುದ್ದಿ — is this link a real, fresh article, and is it credited right. D88.
=================================================================================
One place for three questions the intake, the drafter and the gate all ask:

  * **Whose is it?** A link on daijiworld.com is Daijiworld's story, and the
    story must say so. On 2026-09-24 six stories — some found by the intake,
    some the editor added by hand — all went out credited to ಉದಯವಾಣಿ, and the
    sources slide faithfully printed the one name it was given.
  * **Is it an article?** A section page (`varthabharati.in/karavali`), a URL
    carrying a chatbot's tracking tag (`utm_source=gemini`), or a slug nobody
    would publish (`english-heading-…`) is not something a reader or a
    person verifying can reopen and find the story in.
  * **Is it today's news?** A URL that carries its own date
    (`…/22092026`, `/2026/09/22/`) says how old it is. Anything past
    `Limits.news_max_age_hours` is not news for a daily edition.

Pure functions; no network. News is pasted in (D92, `scripts/intake.py`);
these checks run on the URL the editor gives with it.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs

from .tokens import Limits

IST = timezone(timedelta(hours=5, minutes=30))

# Domain → every name a story may credit it under. The FIRST is the house
# spelling the intake writes. Add an outlet here when we start citing it.
OUTLETS: dict[str, tuple[str, ...]] = {
    'udayavani.com': ('ಉದಯವಾಣಿ', 'Udayavani'),
    'daijiworld.com': ('Daijiworld', 'ದಾಯ್ಜಿವರ್ಲ್ಡ್', 'Daijiworld Media Network'),
    'newskarnataka.com': ('News Karnataka', 'ನ್ಯೂಸ್ ಕರ್ನಾಟಕ'),
    'varthabharati.in': ('ವಾರ್ತಾ ಭಾರತಿ', 'Vartha Bharati', 'ವಾರ್ತಾಭಾರತಿ'),
    'oneindia.com': ('OneIndia Kannada', 'ಒನ್‌ಇಂಡಿಯಾ ಕನ್ನಡ', 'OneIndia'),
    'thehindustangazette.com': ('ದಿ ಹಿಂದೂಸ್ತಾನ್ ಗೆಜೆಟ್', 'The Hindustan Gazette'),
    'sanjevani.com': ('ಸಂಜೆವಾಣಿ', 'Sanjevani'),
    'prajavani.net': ('ಪ್ರಜಾವಾಣಿ', 'Prajavani'),
    'vijaykarnataka.com': ('ವಿಜಯ ಕರ್ನಾಟಕ', 'Vijay Karnataka'),
    'vijaykarnataka.indiatimes.com': ('ವಿಜಯ ಕರ್ನಾಟಕ', 'Vijay Karnataka'),
    'kannadaprabha.com': ('ಕನ್ನಡಪ್ರಭ', 'Kannada Prabha'),
    'thehindu.com': ('The Hindu', 'ದಿ ಹಿಂದೂ'),
    'deccanherald.com': ('Deccan Herald', 'ಡೆಕ್ಕನ್ ಹೆರಾಲ್ಡ್'),
    'timesofindia.indiatimes.com': ('The Times of India', 'Times of India'),
    'mangaloretoday.com': ('Mangalore Today',),
    'mangalorean.com': ('Mangalorean.com',),
    'nammakudlanews.com': ('Namma Kudla', 'ನಮ್ಮ ಕುಡ್ಲ'),
    'tv9kannada.com': ('TV9 ಕನ್ನಡ', 'TV9 Kannada'),
    'publictv.in': ('ಪಬ್ಲಿಕ್ ಟಿವಿ', 'Public TV'),
    'suvarnanews.com': ('ಸುವರ್ಣ ನ್ಯೂಸ್', 'Suvarna News'),
    'kannada.asianetnews.com': ('ಏಷ್ಯಾನೆಟ್ ಸುವರ್ಣ ನ್ಯೂಸ್', 'Asianet Suvarna News'),
    'hosakannada.com': ('ಹೊಸಕನ್ನಡ', 'Hosakannada'),
    'etvbharat.com': ('ಈಟಿವಿ ಭಾರತ್', 'ETV Bharat'),
    'theweek.in': ('The Week',),
}

# Tracking tags that mean the link came out of a chatbot answer, not off the
# publisher's page. The link may still be real — but it has to be opened, and
# the one that gets cited is the publisher's own, without the tag.
BOT_TAGS = ('gemini', 'chatgpt', 'openai', 'perplexity', 'copilot', 'bard',
            'claude', 'grok', 'bing')

# Slugs a newsroom does not publish.
# (`english-heading-…` is NOT one: it is Udayavani's own CMS slug, and the
# article behind it is real — found by the fact desk, 2026-09-25.)
PLACEHOLDER = re.compile(r'lorem|your-slug|headline-here|example-article')

# Last path segments that name a section, not an article.
SECTIONS = {'karavali', 'udupi', 'mangaluru', 'mangalore', 'dakshina-kannada',
            'udupi-news', 'karavali-udupi', 'news', 'latest', 'state',
            'karnataka', 'district', 'local', 'coastal', 'home', 'index'}


def _host(url: str) -> str:
    h = (urlparse(url).hostname or '').lower()
    return h[4:] if h.startswith('www.') else h


def outlet_domain(url: str) -> str:
    """The OUTLETS key this URL belongs to, or ''."""
    h = _host(url)
    best = ''
    for d in OUTLETS:
        if (h == d or h.endswith('.' + d)) and len(d) > len(best):
            best = d
    return best


def outlet_names(url: str) -> tuple[str, ...]:
    d = outlet_domain(url)
    return OUTLETS.get(d, ())


def url_problem(url: str) -> str:
    """Why this is not a citable article URL, or '' when it is fine."""
    u = (url or '').strip()
    if not u.startswith(('http://', 'https://')):
        return 'not a web link'
    p = urlparse(u)
    q = parse_qs(p.query)
    src = ' '.join(q.get('utm_source', []) + q.get('ref', [])).lower()
    if any(b in src for b in BOT_TAGS):
        return (f'carries a chatbot tracking tag (utm_source={src}) — the '
                f'link came from an AI answer, not from the publisher. Open '
                f'it; cite the publisher\'s own URL')
    path = p.path.strip('/')
    if PLACEHOLDER.search(path.lower()):
        return 'the slug is a placeholder, not a published article'
    # An official portal's front page is the source for what the portal
    # offers (a helpline number, a complaint form) — the "listing page" rule
    # exists for news sites, where a home page is a pile of other stories.
    host = _host(u)
    if host.endswith(('.gov.in', '.nic.in')) or host in ('gov.in', 'nic.in'):
        return ''
    segs = [s for s in path.split('/') if s]
    has_id = bool(re.search(r'\d{4,}', u)) or 'newsid=' in p.query.lower()
    # A one-word path (/karavali) is a section; a slug of words
    # (/udupi-rain-warning) is an article.
    if not segs or (len(segs) == 1 and not has_id and segs[0].isalpha()
                    and len(segs[0]) >= 3):
        return 'is a home or section page, not an article'
    if segs[-1].lower() in SECTIONS and not has_id:
        return 'is a section page, not an article'
    return ''


def date_in_url(url: str) -> datetime | None:
    """The publish date a URL carries in its own path, if it carries one."""
    path = urlparse(url or '').path
    pats = (
        (r'/(20\d\d)/(\d{1,2})/(\d{1,2})(?:/|$)', ('y', 'm', 'd')),
        (r'(20\d\d)-(\d{2})-(\d{2})', ('y', 'm', 'd')),
        (r'/(\d{2})(\d{2})(20\d\d)(?:/|$)', ('d', 'm', 'y')),      # …/22092026
        (r'(\d{2})-(\d{2})-(20\d\d)', ('d', 'm', 'y')),
    )
    for pat, order in pats:
        m = re.search(pat, path)
        if not m:
            continue
        parts = dict(zip(order, (int(g) for g in m.groups())))
        try:
            return datetime(parts['y'], parts['m'], parts['d'], tzinfo=IST)
        except ValueError:
            continue
    return None


def parse_when(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=IST)


def age_hours(published: datetime | None, now: datetime | None = None
              ) -> float | None:
    if published is None:
        return None
    now = now or datetime.now(IST)
    return (now - published).total_seconds() / 3600


def is_stale(published: datetime | None, now: datetime | None = None,
             date_only: bool = False) -> bool:
    """Past the house freshness window. A date with no time (from a URL) is
    counted in calendar days — the window in whole days back from today — so
    yesterday's evening story is kept and the day before's is not."""
    if published is None:
        return False
    now = now or datetime.now(IST)
    if date_only:
        days = (now.astimezone(IST).date() - published.astimezone(IST).date()).days
        return days > Limits.news_max_age_hours // 24
    return age_hours(published, now) > Limits.news_max_age_hours


def source_problems(story) -> list[tuple[str, str]]:
    """(code, message) for every sourcing fault in a story. Codes in
    brand/codes.py: FACT-05 not an article, FACT-06 credited to the wrong
    outlet."""
    out = []
    names = {s.strip().lower() for s in story.sources}
    for url in (u.strip() for u in story.source_urls if (u or '').strip()):
        why = url_problem(url)
        if why:
            out.append(('FACT-05', f'{url} {why}.'))
        credit = outlet_names(url)
        if credit and not ({c.lower() for c in credit} & names):
            out.append(('FACT-06',
                        f'{url} is {credit[0]}\'s, but the story credits '
                        f'{", ".join(story.sources)}. Each story credits the '
                        f'outlet it actually came from.'))
    return out
