"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the fact desk, mechanised as far as it honestly goes. D84.
===========================================================================
The intake has always checked the one-line LEAD it wrote against the text it
fetched (D63). Nothing checked what came after: the headline the desk
tightened, the deck, the three facts, the takeaway with a helpline in it, the
narration the anchor reads out. Every one of those is a sentence a model can
write, and a figure a model adds is the most dangerous word in the package —
a casualty count, a rupee amount, a phone number that rings nobody.

This module asks the question a machine can answer: does every FIGURE, and
every name, in every line we publish appear in the source we are citing?

  * The source text is kept, per URL, in `inbox/sources/<digest>.txt` — the
    article as it was when we read it. `scripts/fact_check.py` fills it; the
    fact-checker agent fills it when the site will not serve a scraper.
  * A figure the source writes differently ("twenty-five", "3 districts"
    listed by name) is not waved through: the fact-checker records the exact
    sentence of the source that carries it in `inbox/factcheck/<stem>.json`,
    and this module checks that sentence really is in the source. Evidence,
    not an override — a quote that is not in the article supports nothing.

What it cannot do, and says: decide that a source is right, read a Kannada
line against an English article word for word, or replace the person who
opens the link. `verified_by` is still a human name (D59). This is the pass
that makes that person's two minutes land on the two words that matter.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field

from .content import Story, Edition, OWN_REPORTING

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_DIR = os.path.join(ROOT, 'inbox', 'sources')
LEDGER_DIR = os.path.join(ROOT, 'inbox', 'factcheck')
TIP_SHEET = os.path.join(ROOT, 'inbox', 'today.json')

# Every line that reaches a reader, a listener or a search box.
FIELDS = ('headline', 'reel_line', 'hook', 'deck', 'points', 'takeaway',
          'narration_script')

_FIGURE = re.compile(r'\d')


def digest(url: str) -> str:
    return hashlib.sha1(url.strip().encode('utf-8')).hexdigest()[:16]


def cache_path(url: str) -> str:
    return os.path.join(SOURCES_DIR, digest(url) + '.txt')


def save_source(url: str, text: str) -> str:
    """Keep the article as read. First line is the URL, so a person opening
    the file knows what it is."""
    os.makedirs(SOURCES_DIR, exist_ok=True)
    path = cache_path(url)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(url.strip() + '\n\n' + text.strip() + '\n')
    return path


def _tip_bodies() -> dict[str, str]:
    try:
        with open(TIP_SHEET, encoding='utf-8') as fh:
            tips = json.load(fh).get('tips', [])
    except (OSError, ValueError):
        return {}
    out = {}
    for t in tips:
        url = (t.get('source_url') or '').strip()
        text = ' '.join(filter(None, [t.get('headline', ''),
                                      t.get('body', '') or t.get('snippet', '')]))
        if url and text.strip():
            out[url] = text
    return out


def source_text(story: Story, tips: dict[str, str] | None = None
                ) -> tuple[str, list[str]]:
    """(the text of every source we hold for this story, URLs we hold none for)."""
    tips = _tip_bodies() if tips is None else tips
    parts, missing = [], []
    for url in (u.strip() for u in story.source_urls if (u or '').strip()):
        path = cache_path(url)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as fh:
                parts.append(fh.read())
        elif url in tips:
            parts.append(tips[url])
        else:
            missing.append(url)
    return '\n'.join(parts), missing


def ledger_path(edition_path: str) -> str:
    stem = os.path.splitext(os.path.basename(edition_path))[0]
    return os.path.join(LEDGER_DIR, stem + '.json')


def load_ledger(edition_path: str | None = None) -> list[dict]:
    """Every claim the fact-checker proved with a quote, from every ledger.

    A claim belongs to a SOURCE (its `url`), not to an edition file: the
    quote has to be in that article, and it is just as true for the evening
    edition as for the morning one. So the gate, which is not told which
    file an edition came from, reads them all."""
    import glob
    out = []
    for path in sorted(glob.glob(os.path.join(LEDGER_DIR, '*.json'))):
        try:
            with open(path, encoding='utf-8') as fh:
                out += json.load(fh).get('claims', [])
        except (OSError, ValueError):
            continue
    return out


def _norm(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip().lower()


def _lines(story: Story) -> list[tuple[str, str]]:
    out = []
    for f in FIELDS:
        if f == 'points':
            out += [(f'points[{i}]', p) for i, p in enumerate(story.points or [])]
        elif f == 'hook':
            if getattr(story, '_hook', ''):
                out.append((f, story._hook))
        else:
            v = getattr(story, f, '') or ''
            if v.strip():
                out.append((f, v))
    return out


@dataclass
class FactResult:
    headline: str
    state: str             # grounded · flags · mismatch · uncheckable · own
    figures: list[tuple[str, str]] = field(default_factory=list)   # (field, token)
    names: list[tuple[str, str]] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)
    cross_script: bool = False
    proved: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return bool(self.figures) or self.state == 'mismatch'


# Past this share of unsupported words, the text we hold is not this story's
# article at all — a listing page, a home page, or a URL a model invented.
# Measured on 2026-09-24: six model-written udayavani URLs all served the
# sidebar, and 85-100% of every story's words were missing from them.
MISMATCH_SHARE = 0.6
MISMATCH_MIN_TOKENS = 8


def _unsupported(line: str, text: str) -> list[str]:
    """`unsupported_tokens`, without its cap of eight: that cap is right for
    a tip sheet a person skims and wrong for a count, where the ninth missing
    word is exactly what says the page is not this story."""
    from scripts.fetch_daily_news import unsupported_tokens, UNCHECKABLE
    import unicodedata
    line = unicodedata.normalize('NFC', line)
    text = unicodedata.normalize('NFC', text)
    words, out = line.split(), []
    for i in range(0, len(words), 6):
        for t in unsupported_tokens(' '.join(words[i:i + 6]), text):
            if t == UNCHECKABLE:
                if UNCHECKABLE not in out:
                    out.insert(0, UNCHECKABLE)
            elif t not in out:
                out.append(t)
    return out


def carries(story: Story, text: str) -> bool:
    """Does `text` look like an article about this story at all?"""
    from scripts.fetch_daily_news import _TOKEN, UNCHECKABLE
    line = ' '.join(filter(None, [story.headline, story.deck]))
    toks = set(_TOKEN.findall(line))
    if len(toks) < 3:
        return True
    miss = _unsupported(line, text)
    if UNCHECKABLE in miss:
        return True                   # cross-script: figures are checked later
    return len(miss) < max(3, MISMATCH_SHARE * len(toks))


def check(story: Story, claims: list[dict] | None = None,
          tips: dict[str, str] | None = None, index: int | None = None
          ) -> FactResult:
    """Every figure and name in every published line, against the source."""
    from scripts.fetch_daily_news import UNCHECKABLE

    res = FactResult(story.headline, 'grounded')
    if not [u for u in story.source_urls if (u or '').strip()]:
        res.state = 'own' if OWN_REPORTING in story.sources else 'uncheckable'
        return res
    text, res.missing_sources = source_text(story, tips)
    if not text.strip():
        res.state = 'uncheckable'
        return res

    # A figure the source spells another way is proved by a sentence that is
    # really in the source — checked here, never taken on trust.
    src = _norm(text)
    proved = set()
    urls = {u.strip() for u in story.source_urls}
    for c in claims or []:
        if (c.get('url') or '').strip() not in urls:
            continue
        tok, quote = str(c.get('token', '')).strip(), _norm(c.get('quote', ''))
        if tok and quote and quote in src:
            proved.add(tok.lower())
            res.proved.append(tok)

    for fld, line in _lines(story):
        for tok in _unsupported(line, text):
            if tok == UNCHECKABLE:
                res.cross_script = True
                continue
            if tok.lower() in proved:
                continue
            bucket = res.figures if _FIGURE.search(tok) else res.names
            if (fld, tok) not in bucket:
                bucket.append((fld, tok))
    from scripts.fetch_daily_news import _TOKEN
    checked = sum(len(_TOKEN.findall(line)) for _, line in _lines(story))
    wrong = len(res.figures) + len(res.names)
    if (not res.cross_script and wrong >= MISMATCH_MIN_TOKENS
            and wrong >= MISMATCH_SHARE * max(checked, 1)):
        res.state = 'mismatch'
    elif res.figures or res.names:
        res.state = 'flags'
    return res


def check_edition(edition: Edition, edition_path: str | None = None
                  ) -> list[FactResult]:
    claims = load_ledger(edition_path)
    tips = _tip_bodies()
    return [check(st, claims, tips, i)
            for i, st in enumerate(edition.stories, 1)]


def report(results: list[FactResult]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f'{i}. {r.headline}')
        if r.state == 'own':
            lines.append('   OWN REPORTING — the reporter is the source; '
                         'verified_by carries it')
            continue
        if r.state == 'uncheckable':
            lines.append('   COULD NOT CHECK — no source text held for: '
                         + (', '.join(r.missing_sources) or 'no source_url'))
            continue
        if r.state == 'mismatch':
            lines.append('   BLOCK  the source text does not carry this story '
                         '— a listing page or a wrong URL. Open it; replace '
                         'source_url with the article itself')
            continue
        if r.cross_script:
            lines.append('   source is not in Kannada: figures and Latin names '
                         'checked; Kannada wording needs the person')
        for fld, tok in r.figures:
            lines.append(f'   BLOCK  figure "{tok}" in {fld} is not in the source')
        for fld, tok in r.names:
            lines.append(f'   CHECK  "{tok}" in {fld} is not in the source')
        if r.proved:
            lines.append('   proved by quote: ' + ', '.join(r.proved))
        if r.state == 'grounded':
            lines.append('   PASS   every figure and name is in the source')
    return '\n'.join(lines)
