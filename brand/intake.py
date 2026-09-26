"""
ಊರ್ಮನಿ ಸುದ್ದಿ — paste-first intake. D92.
=======================================
News comes in because the editor pasted it, not because a scraper found it.
The scraper, the automatic draft and their schedule are gone: they ran for
hours when they ran at all, and 10 of 12 stories on 23–24 Sept carried claims
their source did not contain (D84, D88).

Two jobs, both pure and offline:

  * `save_pasted()` keeps the pasted text as the story's SOURCE, where the fact
    desk (FACT-01/FACT-03, `brand/factcheck.py`) reads it. Every figure we
    publish is checked against exactly what the editor gave us.
  * `published_before()` says whether a story already ran on an earlier day —
    the same source URL, or a headline that is the same story reworded. A
    repeat is refused (DUP-01) unless it is a real follow-up (`follows_up`,
    with a new fact).

`scripts/intake.py` is the command line for both.
"""
from __future__ import annotations

import datetime as _dt
import glob
import hashlib
import json
import os
import re
import unicodedata

from . import factcheck as F
from .grounding import _FUNCTION_WORDS

# Headlines this similar are the same story told twice. Measured on the
# 17–26 Sept editions: a real repeat ("ಕರಾವಳಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ" two days running
# with the same towns) scores ≥ 0.6; two different stories in one town score
# well under it.
HEADLINE_OVERLAP = 0.6
_MIN_WORD = 3
_WORD = re.compile(r'[ಀ-೿]+|[A-Za-z]+|\d+')

# Words every other headline carries. Town names are NOT here on purpose: a
# town is part of what makes two headlines the same story.
_COMMON = set(_FUNCTION_WORDS) | {
    'ಸುದ್ದಿ', 'ಜಿಲ್ಲೆ', 'ಜಿಲ್ಲೆಯಲ್ಲಿ', 'ಜಿಲ್ಲೆಯ', 'ಕರಾವಳಿ', 'ಕರಾವಳಿಯಲ್ಲಿ',
    'ಇಂದು', 'ನಾಳೆ', 'ಹೊಸ', 'ಬ್ರೇಕಿಂಗ್', 'ಬಗ್ಗೆ', 'ಮಾಹಿತಿ', 'ಸೂಚನೆ',
    'with', 'from', 'after', 'over', 'into', 'news', 'district', 'new',
}


# ─── keeping the pasted source ───────────────────────────────────────────────

def save_pasted(text: str, url: str = '', outlet: str = '') -> str:
    """Keep pasted source text where the fact desk will check against it.

    With a URL: `inbox/sources/<sha1(url)[:16]>.txt` via
    `brand.factcheck.save_source` — the same digest FACT-03 looks up from a
    story's `source_urls`. Without one (own reporting, a press release):
    `inbox/sources/own_<sha1(text)[:16]>.txt`. Returns the path written.
    """
    text = unicodedata.normalize('NFC', (text or '')).strip()
    if not text:
        raise ValueError('nothing pasted — the source text is empty')
    outlet = (outlet or '').strip()
    body = (f'Outlet: {outlet}\n\n' if outlet else '') + text
    url = (url or '').strip()
    if url:
        return F.save_source(url, body)
    os.makedirs(F.SOURCES_DIR, exist_ok=True)
    digest = hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]
    path = os.path.join(F.SOURCES_DIR, f'own_{digest}.txt')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('own reporting / press release — no URL\n\n' + body + '\n')
    return path


# ─── has this already run? ───────────────────────────────────────────────────

def _norm_url(u: str) -> str:
    u = (u or '').strip()
    u = re.sub(r'^https?://(www\.)?', '', u, flags=re.I)
    return u.rstrip('/').lower()


def headline_words(headline: str) -> frozenset[str]:
    """Word tokens of three or more characters, common words removed."""
    h = unicodedata.normalize('NFC', headline or '').lower()
    return frozenset(w for w in _WORD.findall(h)
                     if len(w) >= _MIN_WORD and w not in _COMMON)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _get(story, key, default=None):
    if isinstance(story, dict):
        return story.get(key, default)
    return getattr(story, key, default)


def _urls(story) -> list[str]:
    urls = list(_get(story, 'source_urls', None) or [])
    one = _get(story, 'source_url', '')
    if one:
        urls.append(one)
    return [u for u in (_norm_url(x) for x in urls) if u]


def _edition_date(data: dict, path: str) -> _dt.date | None:
    raw = data.get('date')
    if raw:
        try:
            from .content import parse_dt
            return parse_dt(raw).date()
        except Exception:
            pass
    m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(path))
    if m:
        try:
            return _dt.date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def _files(root: str) -> list[str]:
    return sorted(glob.glob(os.path.join(root, 'editions', '*.json'))
                  + glob.glob(os.path.join(root, 'archive', '*', '*.json')))


_CACHE: dict[str, tuple[tuple, list]] = {}


def published_index(root: str = '.') -> list[tuple]:
    """(date, story number, headline, url set, headline words) for every
    story of every edition under `root`. Cached per root, and rebuilt when a
    file is added, removed or changed."""
    root = os.path.abspath(root)
    files = _files(root)
    sig = tuple((p, os.path.getmtime(p)) for p in files)
    hit = _CACHE.get(root)
    if hit and hit[0] == sig:
        return hit[1]
    seen, out = set(), []
    for p in files:
        try:
            with open(p, encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get('stories'), list):
            continue
        day = _edition_date(data, p)
        if day is None:
            continue
        for i, st in enumerate(data['stories'], 1):
            if not isinstance(st, dict):
                continue
            head = st.get('headline', '') or ''
            key = (day, head.strip())
            if key in seen:            # the same edition in editions/ and archive/
                continue
            seen.add(key)
            out.append((day, i, head, frozenset(_urls(st)),
                        headline_words(head)))
    _CACHE[root] = (sig, out)
    return out


def published_before(story, on_date: _dt.date, root: str = '.') -> list[str]:
    """Reasons this story already ran on a day BEFORE `on_date`.

    (a) one of its source URLs is a source URL of an earlier story;
    (b) its headline shares ≥ HEADLINE_OVERLAP of its words (Jaccard) with an
        earlier headline.

    Accepts a `brand.content.Story` or a plain dict. An empty list means
    nothing earlier looks like it.
    """
    if isinstance(on_date, _dt.datetime):
        on_date = on_date.date()
    urls = set(_urls(story))
    words = headline_words(_get(story, 'headline', '') or '')
    reasons: list[str] = []
    for day, n, head, their_urls, their_words in published_index(root):
        if day >= on_date:
            continue
        if urls & their_urls:
            reasons.append(f'same source URL as {day.isoformat()} story {n} '
                           f'("{head}")')
            continue
        score = jaccard(words, their_words)
        if score >= HEADLINE_OVERLAP:
            reasons.append(f'headline {score:.0%} the same as '
                           f'{day.isoformat()} story {n} ("{head}")')
    return reasons


def url_repeat(reasons: list[str]) -> bool:
    return any(r.startswith('same source URL') for r in reasons)
