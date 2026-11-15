"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Kannada spelling & sound watch for what the voice will say (D136)
================================================================================
Kannada changes meaning with a single sound: a short or long vowel (ಹ್ರಸ್ವ / ದೀರ್ಘ — ದಿನ "day", ದೀನ "wretched"),
ಲ / ಳ (ಕೊಲೆ "murder", ಕೊಳೆ "dirt"), ನ / ಣ (ಅನ್ನ "rice", ಅಣ್ಣ "elder brother"), a plain or aspirated
consonant (ದನ "cattle", ಧನ "wealth"), a single or a doubled one (ಕಲೆ "art", ಕಲ್ಲು "stone"). The voice reads exactly the
letters it is given, so for a news channel the whole defence is the SPELLING of what is said — and the one place a
spelling can be wrong without anyone noticing is a word a model wrote that no newspaper had spelled.

Two lists, both only warnings, both printed before the render and in the report:

  meaning_pairs(text)  the words in `text` that are one sound away from a different word (assets/kannada_pairs.json):
                       the Kannada desk confirms each letter by letter; the editor listens for it.
  unseen_spellings(text)  the words NOT found, spelled that way, in any kept source paste. A word a
                       newspaper printed is spelled by a newspaper; a word that is in no kept paste
                       is the model's own, and its vowel length and ಲ/ಳ/ನ/ಣ are the model's guess.

Neither can hear. They narrow the whole script to the few words where a slip could change what the news says.
"""
from __future__ import annotations

import glob
import json
import os
import re
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KN = re.compile(r'[ಀ-೿]+')
# What may follow a word's stem (case endings and plurals): "ಮಳೆಯಲ್ಲಿ" is still ಮಳೆ.
_ENDINGS = ('', 'ಯ', 'ಯು', 'ಯನ್ನು', 'ಯಲ್ಲಿ', 'ಯಿಂದ', 'ಗೆ', 'ಕ್ಕೆ', 'ಗಳು', 'ಗಳ', 'ಗಳನ್ನು', 'ಗಳಲ್ಲಿ', 'ಗಳಿಗೆ',
            'ದ', 'ದಲ್ಲಿ', 'ದಿಂದ', 'ವನ್ನು', 'ವು', 'ವಿನ', 'ವಿಗೆ', 'ಗಾಗಿ', 'ನ', 'ನನ್ನು', 'ನಿಗೆ', 'ರು', 'ರನ್ನು', 'ರ', 'ರಿಗೆ',
            'ಅನ್ನು', 'ದ', 'ನಲ್ಲಿ', 'ನಿಂದ', 'ಕ್ಕೂ', 'ಯೂ', 'ವೂ')


def words(text: str) -> list[str]:
    """The Kannada words of a line, joiners removed, punctuation gone."""
    t = text.replace('‌', '').replace('‍', '')
    return _KN.findall(t)


@lru_cache(maxsize=1)
def _pairs() -> list[dict]:
    with open(os.path.join(ROOT, 'assets', 'kannada_pairs.json'), encoding='utf-8') as fh:
        return json.load(fh)['pairs']


def meaning_pairs(text: str) -> list[dict]:
    """[{word, means, vs, vs_means}] for each spoken word one sound from a different word."""
    out, seen = [], set()
    for w in words(text):
        for row in _pairs():
            stem = row['w']
            if w.startswith(stem) and w[len(stem):] in _ENDINGS and (w, stem) not in seen:
                seen.add((w, stem))
                out.append(dict(word=w, means=row['en'], vs=row['vs'], vs_means=row['vs_en']))
    return out


@lru_cache(maxsize=1)
def _corpus() -> frozenset:
    """Every word any newspaper source paste has used — the kept texts in inbox/sources/. Earlier EDITIONS are not
    counted: they hold the model's own spellings, which are exactly what is being checked."""
    tokens: set[str] = set()
    for path in glob.glob(os.path.join(ROOT, 'inbox', 'sources', '*.txt')):
        try:
            with open(path, encoding='utf-8') as fh:
                tokens.update(words(fh.read()))
        except OSError:
            pass
    return frozenset(tokens)


def _known(w: str, corpus) -> bool:
    """Is `w` spelled as some newspaper spelled it, give or take a case ending? The ending is the ONLY thing forgiven:
    a changed vowel length or ಲ/ಳ in the stem is exactly what is being looked for."""
    if w in corpus:
        return True
    stems = {w}
    for e in _ENDINGS:
        if e and w.endswith(e) and len(w) - len(e) >= 3:
            stems.add(w[:-len(e)])
    for s in list(stems):
        if s.endswith('ಿ'):                       # a noun in ು takes ಇ before an ending: ಬರಗೂರು → ಬರಗೂರಿಗೆ
            stems.add(s[:-1] + 'ು')
    for c in corpus:
        for s in stems:
            if c.startswith(s) and c[len(s):] in _ENDINGS:
                return True
    return False


def unseen_spellings(text: str, source: str = '') -> list[str]:
    """Spoken words spelled in no source paste (today's `source` first) and no earlier edition."""
    corpus = set(_corpus()) | set(words(source))
    out = []
    for w in words(text):
        if len(w) >= 3 and not _known(w, corpus) and w not in out:
            out.append(w)
    return out


# Colour a television-style rewrite likes to add and a source rarely carries (D145). A death or a crash is reported in the paste's
# own words; "ಭೀಕರ", "ದಾರುಣ" … belong only where the paste says them.
_COLOUR = ('ದಾರುಣ', 'ಭೀಕರ', 'ತೀವ್ರ', 'ಸುಸಜ್ಜಿತ', 'ಅಮಾನುಷ', 'ಹೃದಯವಿದ್ರಾವಕ', 'ಭಯಾನಕ', 'ಶೋಚನೀಯ', 'ವೈಭವದ', 'ಯಶಸ್ವಿ', 'ಭಾರಿ', 'ಬೃಹತ್',
           'ಭಾರೀ', 'ಅತ್ಯಂತ', 'ಮಹತ್ವದ', 'ಐತಿಹಾಸಿಕ', 'ಸಂಚಲನ', 'ಆಘಾತಕಾರಿ', 'ಬೆಚ್ಚಿಬೀಳಿಸುವ')


def colour_words(text: str) -> list[str]:
    """Intensifiers in `text` that no kept source paste uses."""
    corpus = _corpus()
    return [w for w in dict.fromkeys(words(text)) if any(w.startswith(c) for c in _COLOUR) and not any(c.startswith(w[:5]) for c in corpus)]


_PROMOTIONAL = ('ಹೊಸ ಚೈತನ್ಯ', 'ವಿಜೃಂಭಣೆಯಿಂದ')
_GRAPHIC = ('ರಕ್ತದ ಮಡುವಿನಲ್ಲಿ', 'ರಕ್ತಸಿಕ್ತ', 'ಕೂದಲೆಳೆಯ ಅಂತರದಲ್ಲಿ')
_TERMINAL = re.compile(r'[.!?।][\"\'’”)]*$')


def style_notes(text: str, complete: bool = False) -> list[str]:
    """Editorial faults a rewrite must fix by hand, never by automatic substitution."""
    out = []
    stripped = (text or '').strip()
    if complete and stripped and not _TERMINAL.search(stripped):
        out.append('the support sentence has no terminal punctuation — finish the sentence')
    for phrase in _PROMOTIONAL:
        if phrase in stripped:
            out.append(f'"{phrase}" is promotional filler — replace it with a sourced fact')
    for phrase in _GRAPHIC:
        if phrase in stripped:
            out.append(f'"{phrase}" adds gratuitous graphic detail — keep only the fact needed to understand the news')
    return out


def reset() -> None:
    _corpus.cache_clear()
