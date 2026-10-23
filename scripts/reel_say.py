#!/usr/bin/env python3
"""
How will the reel's voice say this? Listen, and fix it for good (D133).

    python3 scripts/reel_say.py "ಸಚಿವ ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ 33ನೇ ಶಾರದೋತ್ಸವ"             # what the voice is GIVEN
    python3 scripts/reel_say.py "ಸಚಿವ ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ" --play                  # …and say it aloud
    python3 scripts/reel_say.py "ಹೆಬ್ರಿ" --respell "ಹೆಬ್ರಿ=ಹೆಬ್ರಿ" --play         # change how a word is spoken

The first line shows the text after the house normaliser and after figures are turned
into Kannada words — the exact string handed to the voice — and lists anything it may
still misread. `--respell WORD=SPOKEN` writes the respelling into
assets/pronunciation.json, which every format reads, so a word the editor hears wrong
once is right in every reel from then on. (Keys are replaced as plain text wherever
they appear, so respell the whole word, not a fragment of one.)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import reel_speech as RS                    # noqa: E402

PRONUNCIATION = Path(ROOT) / 'assets' / 'pronunciation.json'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('text')
    ap.add_argument('--play', action='store_true', help='say it aloud (macOS afplay)')
    ap.add_argument('--respell', metavar='WORD=SPOKEN', help='record how a word should be spoken, from now on')
    a = ap.parse_args()

    if a.respell:
        if '=' not in a.respell:
            print('✗ --respell takes WORD=SPOKEN', file=sys.stderr)
            return 2
        word, spoken = (x.strip() for x in a.respell.split('=', 1))
        if not word or not spoken:
            print('✗ both sides of WORD=SPOKEN are needed', file=sys.stderr)
            return 2
        data = json.loads(PRONUNCIATION.read_text(encoding='utf-8'))
        data[word] = spoken
        PRONUNCIATION.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'✓ {word!r} will be spoken as {spoken!r} in every format, from now on')

    said = RS.spoken(a.text)
    print(f'given to the voice:  {said}')
    risks = RS.lint(a.text)
    print('may still be misread: ' + (' '.join(risks) if risks else 'nothing'))
    if a.play:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / 'say.wav'
            seconds = RS.clip(a.text, wav)
            print(f'{seconds:.1f}s')
            subprocess.run(['afplay', str(wav)], check=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
