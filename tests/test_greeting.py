"""Greeting layout — the promise that type is never set across the deity.

D54. The whole value of `keep_clear` is that it is a guarantee rather than a
tendency, so it is tested on every format through the planner, which draws
nothing and runs in milliseconds. One poster is actually rendered, to prove
the planner and the drawing agree.

The photograph is synthesised here rather than taken from assets/daily/: the
daily AI images are deleted by the newsroom's `close` step, and the planner
only needs the image's size.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import shutil
import tempfile
import unittest
from unittest import mock

from PIL import Image

from brand.content import Photo, ContentError
from templates import greeting as G

BLESSING = 'ವಿಘ್ನ ನಿವಾರಕ ಗಣಪತಿ ಹಾಗೂ ತಾಯಿ ಗೌರಿಯ ಕೃಪೆ ಸದಾ ನಿಮ್ಮ ಮೇಲಿರಲಿ'


class SubjectIsNeverCovered(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.photo = os.path.join(cls.tmp, 'portrait.jpg')
        # The shape of a phone-generated devotional portrait: 768 x 1376.
        Image.new('RGB', (768, 1376), (96, 42, 20)).save(cls.photo)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def greeting(self, band=(0.32, 0.66), **kw):
        return G.Greeting(
            occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ', blessing=BLESSING,
            photo=Photo(path=self.photo, nature='ai',
                        credit='AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own'),
            keep_clear=band, **kw)

    def test_every_format_plans_the_subject_clear_of_all_type(self):
        for key in G.SCALE:
            p = G._plan(self.greeting(), key)
            self.assertIn(p.mode, ('bleed', 'window'), key)
            self.assertLessEqual(p.sol.bottom, p.text_top - 8,
                                 f'{key}: the wish runs into the subject')
            self.assertGreaterEqual(p.sol.top, p.top - 1,
                                    f'{key}: the salutation runs into the subject')

    def test_a_subject_low_in_the_picture_is_still_kept_clear(self):
        for key in G.SCALE:
            p = G._plan(self.greeting(band=(0.50, 0.86)), key)
            self.assertLessEqual(p.sol.bottom, p.text_top - 8, key)

    def test_when_nothing_keeps_the_subject_clear_it_refuses(self):
        """Refusal, never a covered deity."""
        with mock.patch.object(G, '_solve_bleed', return_value=None), \
                mock.patch.object(G, '_solve_window', return_value=None):
            with self.assertRaisesRegex(ContentError, 'cannot carry the wish'):
                G._plan(self.greeting(), 'story')

    def test_solvers_decline_space_that_is_too_small(self):
        self.assertIsNone(G._solve_window((768, 1376), (0.3, 0.66), 1080,
                                          G.SCALE['square'], 500, 640))
        self.assertIsNone(G._solve_bleed((768, 1376), (0.3, 0.66), 1080, 1080,
                                         500, 640))

    def test_no_photograph_is_a_plate_not_a_failure(self):
        g = G.Greeting(occasion='ದೀಪಾವಳಿ ಹಬ್ಬದ', theme='lights')
        for key in G.SCALE:
            self.assertEqual(G._plan(g, key).mode, 'plate')

    def test_the_drawing_agrees_with_the_plan(self):
        sf, lay = G._compose(self.greeting(), 'square')
        self.assertEqual(sf.finish().size, (1080, 1080))
        self.assertLessEqual(lay.subject[1], lay.text_top - 8)


if __name__ == '__main__':
    unittest.main()
