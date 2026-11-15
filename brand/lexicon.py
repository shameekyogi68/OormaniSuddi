"""
ಊರ್ಮನಿ ಸುದ್ದಿ — other ways to spell a word the voice would not say (D146)
=======================================================================
When the ear hears a clip wrong, the clip is asked for again. Asking the same text again sometimes gives the same
mistake; so each new take also spells the failing word another way. These are the three things that, on
2026-10-30, changed what the voice made of a word:

  * a JOINER after a virama keeps the consonant separate from the next ("ವಂಡ್‌ಸೆ"),
  * a nasal written out ("ಉಪ್ಪುನ್ದ" for "ಉಪ್ಪುಂದ"),
  * (until D147) the virama dropped, so the consonant carries its own vowel ("ವಂಡಸೆ").

The third is gone (D147). It is not another spelling of the word; it is another word. On 2026-11-01 the third take of
story 5 was handed "ಬರಹಮಾವರ" for ಬ್ರಹ್ಮಾವರ, the voice said exactly that, and the reel went out with it. Every candidate is
now the same SOUND written another way — `ear.shape(candidate) == ear.shape(word)`, pinned by tests/test_name_ear.py.

Said plainly: none of them is a cure. The voice is not consistent on a word it cannot say — a spelling heard right on
one take was heard wrong on the next (measured: ವಂಡ್ಸೆ, 9 takes in 3 spellings, none right; ಉಪ್ಪುಂದ and ಯಡ್ತರೆ the
same). So a candidate is only ever used for ONE take, and kept only if the ear then hears the word right; the cure for
a name the voice cannot say is a recorded clip of the name (`brand/town_clips.py`), not a cleverer spelling.
"""
from __future__ import annotations

import re

ZWNJ = '‌'
_C = '[ಕ-ಹ]'
_NASAL = {'ತ': 'ನ್', 'ಥ': 'ನ್', 'ದ': 'ನ್', 'ಧ': 'ನ್', 'ನ': 'ನ್', 'ಟ': 'ನ್', 'ಠ': 'ನ್', 'ಡ': 'ನ್', 'ಢ': 'ನ್',
          'ಪ': 'ಮ್', 'ಫ': 'ಮ್', 'ಬ': 'ಮ್', 'ಭ': 'ಮ್', 'ಮ': 'ಮ್', 'ಕ': 'ಂ', 'ಖ': 'ಂ', 'ಗ': 'ಂ', 'ಘ': 'ಂ',
          'ಚ': 'ನ್', 'ಛ': 'ನ್', 'ಜ': 'ನ್', 'ಝ': 'ನ್', 'ಸ': 'ನ್', 'ಶ': 'ನ್', 'ಷ': 'ನ್', 'ಹ': 'ನ್', 'ಲ': 'ನ್', 'ರ': 'ನ್',
          'ವ': 'ನ್', 'ಯ': 'ನ್'}


def candidates(word: str) -> list[str]:
    """Other spellings of `word` to try, one per take, most conservative first. Never the word itself.

    A doubled consonant (ಪ್ಪ, ಮ್ಮ, ಟ್ಟ) is a sound of its own and is never split or dropped."""
    w = word.strip()
    out: list[str] = []
    cluster = re.compile('(' + _C + ')್(' + _C + ')')
    if '್' in w:
        out.append(cluster.sub(lambda m: m.group(0) if m.group(1) == m.group(2) else m.group(1) + '್' + ZWNJ + m.group(2), w))
    if 'ಂ' in w:
        out.append(re.sub('ಂ(' + _C + ')', lambda m: _NASAL.get(m.group(1), 'ನ್') + m.group(1), w))
    seen: set[str] = set()
    return [c for c in out if c != w and not (c in seen or seen.add(c))]
