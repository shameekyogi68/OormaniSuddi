"""
ಊರ್ಮನಿ ಸುದ್ದಿ — groundedness: is every figure and name in the source? D63, D78, D84.
=================================================================================
Pure functions, no network. This is the comparison the fact desk
(`brand/factcheck.py`) runs between a line we publish and the source text we
kept for it (`inbox/sources/`). It used to live inside the morning scraper;
the scraper is gone (D92) and the comparison is the part worth keeping.

It does not judge whether a line is TRUE — nothing here can. It asks a
narrower question a machine can actually answer: does every number, place
and proper noun in this line appear in the text we hold? Anything that does
not is flagged, and the editor's eye goes to the two or three words that
matter instead of to all forty.

Figures are compared as FIGURES, not as substrings (fixed 2026-09-27):

  * The source is normalised by turning punctuation into spaces, which is
    right for words and wrong for numbers — "82.9 mm" became "82 9 mm", so
    the figure 82.9 was reported missing from an article that printed it
    (the 2026-09-26 rain story, BLOCKed by the fact desk).
  * And a figure was "found" whenever its digits appeared inside any longer
    number: "4" was supported by "24 hours", "5" by "45.1". A check that
    passes 5 because the source says 45 cannot catch an invented count.

Both are fixed by extracting every figure from the source with the same
pattern the line is tokenised with, canonicalising both sides (Kannada
digits → 0-9, thousands commas dropped, leading zeros and trailing decimal
zeros removed) and comparing whole figures. A small, unambiguous bridge maps
spelled numbers ("four", "ಐದು") to their digits, like the month bridge; any
other spelling still needs a quoted sentence in the fact ledger.
"""
from __future__ import annotations

import functools
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Words a Kannada lead can carry without them appearing in an English source,
# and vice versa. These are grammar, not claims.
_FUNCTION_WORDS = {
    'ಮತ್ತು', 'ಅಥವಾ', 'ಎಂದು', 'ಇದೆ', 'ಆಗಿದೆ', 'ಎಂಬ', 'ಈ', 'ಆ', 'ಅವರು',
    'ನಂತರ', 'ಬಳಿಕ', 'ಜೊತೆಗೆ', 'ಬಗ್ಗೆ', 'ಮೇಲೆ', 'ಕುರಿತು', 'ಇಲ್ಲ',
    # Measured against the run of 2026-09-17, where 26 leads of 50 were
    # flagged and the most-flagged token in the whole sheet was ಹಾಗೂ — "and".
    # None of these can be an invented fact in any sentence: they are
    # conjunctions, postpositions and connectives. Flagging them buries the
    # one flag that matters, which is the failure D75 names by name.
    'ಹಾಗೂ', 'ರಂದು', 'ವೇಳೆ', 'ಮೂಲಕ', 'ಪ್ರಕಾರ', 'ಕಾರಣ', 'ಆದರೆ', 'ಸಹಿತ',
    'ಹಿನ್ನೆಲೆಯಲ್ಲಿ', 'ಸಂಬಂಧಿಸಿದಂತೆ', 'ಕುರಿತಂತೆ', 'ಸೇರಿದಂತೆ', 'ಒಳಗೊಂಡ',
    'ಸಂಪೂರ್ಣ', 'ನಿಗದಿತ', 'ವಿವಿಧ', 'ಹೆಚ್ಚು', 'ಮಾಡಲು', 'ಸಿಗುವ', 'ಇದ್ದು',
    'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for',
    'is', 'was', 'were', 'has', 'have', 'said', 'says',
}

# Kannada case endings. The source writes ಸಭೆ and the lead writes ಸಭೆಯ or
# ಸಭೆಗೆ; that is the same noun wearing a case marker, not a new claim.
_CASE_TAILS = (
    'ಗಳನ್ನು', 'ಗಳಿಗೆ', 'ಗಳಲ್ಲಿ', 'ಗಳಿಂದ', 'ವನ್ನು', 'ಯನ್ನು', 'ನ್ನು',
    'ಯಲ್ಲಿ', 'ದಲ್ಲಿ', 'ನಲ್ಲಿ', 'ಅಲ್ಲಿ', 'ಯಿಂದ', 'ದಿಂದ', 'ನಿಂದ',
    'ಕ್ಕೆ', 'ಗಳು', 'ಗಳ', 'ಗೆ', 'ಯ', 'ದ', 'ನ', 'ರ',
)
_MIN_CASE_STEM = 3

_TOKEN = re.compile(r'[ಀ-೿]{3,}|[A-Z][A-Za-z]{2,}|\d(?:[\d.,]*\d)?')
_FIGURE_RE = re.compile(r'\d(?:[\d.,]*\d)?')


def _normalise(text: str) -> str:
    # NFC first: Udayavani writes ೊ as ೆ + ೂ (two code points), which looks
    # identical and never matched the one-code-point ೊ in our copy. Found by
    # the fact desk, 2026-09-25.
    text = unicodedata.normalize('NFC', text)
    return re.sub(r'[^\wಀ-೿]+', ' ', text.lower())


# ─── figures ─────────────────────────────────────────────────────────────────

def canon_figure(tok: str) -> str:
    """One spelling per figure: ASCII digits, no thousands commas, no leading
    zeros, no trailing decimal zeros. '೮೨.೯' → '82.9', '1,20,000' → '120000',
    '09' → '9', '82.90' → '82.9'."""
    t = ''.join(str(unicodedata.digit(c)) if c.isdigit() else c for c in tok)
    t = t.replace(',', '').strip('.')
    parts = t.split('.')
    if len(parts) == 2:
        whole, frac = parts[0].lstrip('0') or '0', parts[1].rstrip('0')
        return whole + ('.' + frac if frac else '')
    return '.'.join(p.lstrip('0') or '0' for p in parts)


# Spelled numbers that mean exactly one figure. "one" is left out on purpose:
# "one of the…" is in every English article and would support any invented 1.
_NUMBER_WORDS = {
    'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6',
    'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10', 'eleven': '11',
    'twelve': '12', 'thirteen': '13', 'fourteen': '14', 'fifteen': '15',
    'sixteen': '16', 'seventeen': '17', 'eighteen': '18', 'nineteen': '19',
    'twenty': '20', 'thirty': '30', 'forty': '40', 'fifty': '50',
    'sixty': '60', 'seventy': '70', 'eighty': '80', 'ninety': '90',
    'ಎರಡು': '2', 'ಮೂರು': '3', 'ನಾಲ್ಕು': '4', 'ಐದು': '5', 'ಆರು': '6',
    'ಏಳು': '7', 'ಎಂಟು': '8', 'ಒಂಬತ್ತು': '9', 'ಹತ್ತು': '10',
    'ಇಬ್ಬರು': '2', 'ಮೂವರು': '3', 'ನಾಲ್ವರು': '4', 'ಐವರು': '5',
}


@functools.lru_cache(maxsize=64)
def source_figures(source_text: str) -> frozenset[str]:
    """Every figure the source prints, canonical — plus the parts of a dotted
    date (25.09.2026 → 25, 9, 2026) and any number it spells out."""
    text = unicodedata.normalize('NFC', source_text)
    out: set[str] = set()
    for m in _FIGURE_RE.findall(text):
        c = canon_figure(m)
        out.add(c)
        if c.count('.') >= 2:
            out.update(canon_figure(p) for p in c.split('.') if p)
    for w in _normalise(text).split():
        if w in _NUMBER_WORDS:
            out.add(_NUMBER_WORDS[w])
    return frozenset(out)


def _is_figure(tok: str) -> bool:
    return bool(tok) and tok[0].isdigit()


# ─── places, abbreviations, months ───────────────────────────────────────────

def _place_bridge() -> dict[str, str]:
    """Latin place name → Kannada, reusing the TTS pronunciation lexicon
    (assets/pronunciation.json). "Udupi:" in a source supports ಉಡುಪಿಯಲ್ಲಿ."""
    path = os.path.join(ROOT, 'assets', 'pronunciation.json')
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        return {str(k).lower(): str(v) for k, v in data.items() if k and v}
    except Exception:
        return {}


_PLACES = _place_bridge()


def _expand_abbreviations(text: str) -> str:
    """ರೂ. → ರೂಪಾಯಿ, ಕಿ.ಮೀ → ಕಿಲೋಮೀಟರ್ — the table brand/voice already
    keeps for the TTS engine, so there is one list, not two that drift."""
    try:
        from brand.voice import SPOKEN_ABBREV, _ABBREV_RE
    except Exception:
        return text
    return _ABBREV_RE.sub(lambda m: SPOKEN_ABBREV[m.group(0)], text)


def _month_bridge(source_text: str) -> str:
    """Full Kannada month names for any month the source abbreviated
    (ಸೆ.18 → ಸೆಪ್ಟೆಂಬರ್), from brand.content.KN_MONTHS."""
    try:
        from brand.content import KN_MONTHS
    except Exception:
        return ''
    out = []
    for month in KN_MONTHS:
        for n in (1, 2, 3):
            if len(month) > n and f'{month[:n]}.' in source_text:
                out.append(month.lower())
                break
    return ' '.join(out)


# ─── morphology ──────────────────────────────────────────────────────────────
# Kannada agglutinates and derives, and neither is an invented fact. Match in
# both directions on a stem, and skip tokens that are plainly verb forms.
_MIN_STEM = 4

_VERB_TAILS = (
    'ಲಾಗಿದೆ', 'ಲಾಗಿತ್ತು', 'ಲಾಗುತ್ತದೆ', 'ಲಾಗುವ',
    'ುತ್ತಿದ್ದ', 'ುತ್ತಿದೆ', 'ುತ್ತಾರೆ', 'ುತ್ತದೆ',
    'ಾಗಿದೆ', 'ಾಗಿತ್ತು', 'ಾಗುವ', 'ಾಗಿ',
    'ಿಸಲಾಗಿದೆ', 'ಿಸಿದ', 'ಿಸುವ', 'ಿಸಲು',
    'ಿದ್ದಾರೆ', 'ಿದ್ದಾನೆ', 'ಿದ್ದಳು', 'ಿದ್ದು', 'ಿದರು', 'ಿತ್ತು', 'ಿದೆ', 'ಿದ',
    'ಯಾಗಿದೆ', 'ವಾಗಿದೆ', 'ಕೊಂಡು', 'ವುದು', 'ುವುದು',
)


def _is_verb_form(token: str) -> bool:
    """A Kannada verb or participle. Length-gated: short words ending in ಿದ
    are often nouns, and over-skipping would hide real facts."""
    return len(token) > 5 and any(token.endswith(t) for t in _VERB_TAILS)


def _kannada_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if 'ಀ' <= c <= '೿') / len(letters)


# The marker returned when the line and its source are in different scripts.
# "These words are invented" would be true and useless; "this cannot be
# checked word by word — open the link" points at the right action.
UNCHECKABLE = '⟨source is not in Kannada — open the link⟩'


def _supported(token: str, haystack_tokens: set, haystack: str) -> bool:
    low = token.lower()
    if low in haystack:
        return True
    # Latin does not agglutinate — an exact miss is a real miss.
    if not any('ಀ' <= ch <= '೿' for ch in low):
        return False
    # The line's word GREW OUT OF a source word:  ಮಳೆ → ಮಳೆಯಾಗುವ
    for h in haystack_tokens:
        if low.startswith(h[:_MIN_STEM]):
            return True
    # The line's word is an inflection of a source word: ಉಡುಪಿಯಲ್ಲಿ → ಉಡುಪಿ
    for cut in range(len(low) - 1, _MIN_STEM - 1, -1):
        if low[:cut] in haystack:
            return True
    # A case marker on a source word too short for haystack_tokens: ಸಭೆಯ → ಸಭೆ
    for tail in _CASE_TAILS:
        if low.endswith(tail):
            stem = low[:-len(tail)]
            if len(stem) >= _MIN_CASE_STEM and stem in haystack:
                return True
    return False


def unsupported_tokens(lead: str, source_text: str) -> list[str]:
    """Numbers, places and proper nouns in `lead` that the source never says.

    Deliberately crude and deliberately over-eager. A false flag costs the
    editor a glance; a missed one costs a helpline number that rings nobody.
    Capped at eight — `brand.factcheck._unsupported` chunks a long line so the
    cap never hides a flag there.
    """
    if not lead.strip() or not source_text.strip():
        return []
    lead = unicodedata.normalize('NFC', lead)
    source_text = unicodedata.normalize('NFC', source_text)
    figures = source_figures(_expand_abbreviations(source_text))

    # A Kannada line against an English source cannot be grounded word by
    # word. But a FIGURE is a figure in both scripts, and so is a Latin name —
    # the two most dangerous things a model can add. Those are still checked.
    if _kannada_share(lead) > 0.5 and _kannada_share(source_text) < 0.15:
        hay = _normalise(_expand_abbreviations(source_text))
        cross = []
        for tok in _TOKEN.findall(lead):
            low = tok.lower()
            if _is_figure(tok):
                if canon_figure(tok) in figures:
                    continue
            elif any('ಀ' <= ch <= '೿' for ch in low):
                continue                     # Kannada: genuinely uncheckable
            elif low in _FUNCTION_WORDS or low in hay:
                continue
            if tok not in cross:
                cross.append(tok)
        return [UNCHECKABLE] + cross[:6]

    hay = _normalise(_expand_abbreviations(source_text))
    for latin, kannada in _PLACES.items():
        if latin in hay:
            hay += ' ' + kannada.lower()
    hay += ' ' + _month_bridge(source_text)
    hay_tokens = {t for t in hay.split() if len(t) >= _MIN_STEM}
    out: list[str] = []
    for tok in _TOKEN.findall(lead):
        low = tok.lower()
        if _is_figure(tok):
            # No length guard for figures: "45 ಮಂದಿ" is two characters and
            # the single most dangerous thing a model can supply.
            if canon_figure(tok) in figures:
                continue
        else:
            if low in _FUNCTION_WORDS or len(low) < 3:
                continue
            if _is_verb_form(low):
                continue
            if _supported(tok, hay_tokens, hay):
                continue
        if tok not in out:
            out.append(tok)
    return out[:8]
