"""
ಊರ್ಮನಿ ಸುದ್ದಿ — hear the reel's voice back (D133)
===================================================
Nobody can listen to every reel before it goes out, and the model that builds it
cannot hear at all. So a speech model listens instead: each clip the reel is cut
from is transcribed by Whisper large-v3-turbo (Kannada, local, no key) and the
transcript is compared with the words the voice was GIVEN.

What this can and cannot tell you — said plainly, because a check that over-claims is
a check that gets ignored:

  * It catches the gross faults: a word dropped, a figure read as something else, an
    initial spelt out wrongly, the wrong language, a clip that is noise or silence. On
    real clips a right voice scores 0.96–1.00 and the wrong audio for the same text
    scores 0.13–0.26 — a wide gap, so the floors below are not close calls.
  * It cannot hear a SUBTLE mispronunciation. Whisper writes Kannada with its own
    spelling habits (ಪೂಜೆ → ಪೋಜೆ), so the comparison is on a phonetic skeleton —
    vowel length and a few near-identical consonants are collapsed. A word that is the
    right word said slightly off passes. The editor's one listen is still the final word.

It runs in its own process: the model is ~1.6 GB, and on an 8 GB Mac it must be gone
before Chrome starts drawing the film.

    python3 -m brand.reel_audit manifest.json     # [{"label":…, "wav":…, "text":…}] → JSON on stdout
"""
from __future__ import annotations

import difflib
import json
import re
import sys

MODEL = 'mlx-community/whisper-large-v3-turbo'

_VOWELS = {'ಆ': 'ಅ', 'ಾ': '', 'ಈ': 'ಇ', 'ೀ': 'ಿ', 'ಏ': 'ಇ', 'ೇ': 'ಿ', 'ಎ': 'ಇ', 'ೆ': 'ಿ',
           'ಊ': 'ಉ', 'ೂ': 'ು', 'ಓ': 'ಉ', 'ೋ': 'ು', 'ಒ': 'ಉ', 'ೊ': 'ು',
           'ಷ': 'ಸ', 'ಶ': 'ಸ', 'ಣ': 'ನ', 'ಳ': 'ಲ', 'ಖ': 'ಕ', 'ಘ': 'ಗ', 'ಛ': 'ಚ', 'ಝ': 'ಜ',
           'ಠ': 'ಟ', 'ಢ': 'ಡ', 'ಥ': 'ತ', 'ಧ': 'ದ', 'ಫ': 'ಪ', 'ಭ': 'ಬ'}
_TABLE = str.maketrans(_VOWELS)


def phonetic(text: str) -> str:
    """A Kannada string as its consonant skeleton: no spaces (where the transcriber breaks
    a word is its whim), no punctuation, vowel length and a few near-twins collapsed."""
    t = re.sub(r'[‌‍]', '', text)
    t = t.replace('ೈ', 'ಯಿ').replace('ೌ', 'ಅವ').replace('ಐ', 'ಅಯಿ').replace('ಔ', 'ಅವು')
    t = t.translate(_TABLE)
    t = re.sub(r'[^ಀ-೿]', '', t)
    return t.replace('ಂ', 'ನ').replace('ಃ', '').replace('್', '')


def compare(script: str, heard: str) -> dict:
    """{similarity 0..1, suspects: the script words the transcript has no close match for}."""
    a, b = phonetic(script), phonetic(heard)
    sim = difflib.SequenceMatcher(None, a, b).ratio() if a else 1.0
    suspects = []
    for w in script.split():
        p = phonetic(w)
        if len(p) < 3:
            continue
        best = 0.0
        for size in range(max(2, len(p) - 1), len(p) + 2):
            for i in range(0, max(1, len(b) - size + 1)):
                best = max(best, difflib.SequenceMatcher(None, p, b[i:i + size]).ratio())
        if best < 0.6:
            suspects.append(w.strip('.,;:!?'))
    return {'similarity': round(sim, 3), 'suspects': suspects}


def transcribe(wav: str) -> str:
    import mlx_whisper
    out = mlx_whisper.transcribe(wav, path_or_hf_repo=MODEL, language='kn', temperature=0.0,
                                 condition_on_previous_text=False)
    return (out.get('text') or '').strip()


def main(argv: list[str]) -> int:
    items = json.load(open(argv[1], encoding='utf-8'))
    results = {}
    for it in items:
        heard = transcribe(it['wav'])
        results[it['label']] = dict(compare(it['text'], heard), heard=heard)
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
