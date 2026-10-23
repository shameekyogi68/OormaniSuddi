"""D133 — the reel's DESIGN is pinned, so it cannot drift by accident.

The same five stories are laid out in real Chrome (no voice, no film) and seven frames — the front page,
each story, the follow card — are reduced to 27x48 greyscale thumbnails and compared with the blessed ones in
tests/reel_golden.json. The page is deterministic (run-to-run difference is exactly 0.000); a colour change
of the gold card measures 4.7–7.8, so the tolerance below catches any real change and ignores
anti-aliasing. If this fails the design changed: that is not automatically a bug, but LOOK at the frames
(`python3 scripts/reel_check.py editions/<d>.json --shots /tmp/look`) before blessing:

    BLESS_REEL=1 python3 -m unittest tests.test_saara_reel_golden
"""
import datetime
import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from brand import saara_reel as R
from brand.content import Edition, Story

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / 'tests' / 'reel_golden.json'
TOLERANCE = 1.2                       # mean absolute difference per frame, 0-255
DAY = datetime.datetime(2026, 10, 23, 9, 0)
FRAMES = ['cover', 's1', 's2', 's3', 's4', 's5', 'close']


def S(head, support='', loc='ಕುಂದಾಪುರ', cat='civic', deck='', reel=True):
    return Story(headline=head, reel_line=head if reel else '', reel_support=support, deck=deck,
                 location=loc, category=cat, segment='saara')


FIVE = [
    S('ಮದ್ಯ ಮಾರಾಟ ನಿಷೇಧ, ಒಣದಿನ ಘೋಷಣೆ', 'ಮೆರವಣಿಗೆಯ ಶಾಂತಿ ಕಾಪಾಡಲು ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮವಾಗಿ ಈ ನಿರ್ಧಾರ.', 'ಕುಂದಾಪುರ, ಗಂಗೊಳ್ಳಿ'),
    S('ದಸರಾ ಕಂಬಳದಲ್ಲಿ ಕೋಣಗಳಿಗೆ ಚಿನ್ನ', 'ಗಣೇಶ್ ಪೂಜಾರಿ ಅವರ ಕೋಣಗಳು ಪ್ರಥಮ ಸ್ಥಾನದೊಂದಿಗೆ ಚಿನ್ನ ಗೆದ್ದಿವೆ.', 'ಬೈಂದೂರು', 'sport'),
    S('ಮಾರಿಕಾಂಬ ದೇವಸ್ಥಾನದಲ್ಲಿ 33ನೇ ಶಾರದೋತ್ಸವ', 'ಮೂರು ದಿನ ಪೂಜೆ, ಭಜನೆ ಹಾಗೂ ಅನ್ನಸಂತರ್ಪಣೆ ಶ್ರದ್ಧೆಯಿಂದ ನೆರವೇರಿತು.', 'ಕಳವಾಡಿ', 'culture'),
    S('ಐದು ಗ್ರಾಮ ಕೈಬಿಡಲು ಸಚಿವರಿಗೆ ಮನವಿ', 'ಸೂಕ್ತ ಕಾನೂನು ಕ್ರಮದ ಭರವಸೆ ನೀಡಿದ ಸಚಿವ ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ.', 'ಬೈಂದೂರು'),
    S('ಅಂಗನವಾಡಿ ಶಿಕ್ಷಕಿಗೆ ಭಾವನಾತ್ಮಕ ವಿದಾಯ', 'ಗ್ರಾಮಸ್ಥರು ಹಾಗೂ ಪೋಷಕರು ಸನ್ಮಾನಿಸಿ ಪ್ರೀತಿಯ ವಿದಾಯ ಕೋರಿದರು.', 'ಕಳವಾಡಿ, ಕುಂದಾಪುರ', 'education'),
]


def fingerprints():
    (ROOT / 'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'build') as shots:
        R.check(Edition(stories=FIVE, date=DAY), shots=shots)
        return {n: np.asarray(Image.open(Path(shots) / f'{n}.png').convert('L').resize((27, 48), Image.Resampling.BOX),
                              dtype=float).round().astype(int).tolist() for n in FRAMES}


@unittest.skipUnless(R.available(), 'Google Chrome is not installed')
class TheDesignIsPinned(unittest.TestCase):
    def test_the_frames_match_the_blessed_ones(self):
        now = fingerprints()
        if os.environ.get('BLESS_REEL'):
            GOLDEN.write_text(json.dumps(now) + '\n', encoding='utf-8')
            self.skipTest('blessed — now LOOK at the frames before committing')
        self.assertTrue(GOLDEN.exists(), 'tests/reel_golden.json is missing — bless it once, after looking')
        blessed = json.loads(GOLDEN.read_text(encoding='utf-8'))
        for n in FRAMES:
            diff = float(np.abs(np.array(now[n]) - np.array(blessed[n])).mean())
            self.assertLess(diff, TOLERANCE, f'the {n} frame changed by {diff:.2f} — the design moved; look, then bless')


if __name__ == '__main__':
    unittest.main()
