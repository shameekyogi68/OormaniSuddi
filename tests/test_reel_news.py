"""
D96 — the news layer on a real-footage Reel stays out of Instagram's way.
=========================================================================
2026-09-30, MRPL: the masthead sat under the "← Reels" header, the date under
the camera icon, and the news card under the like/share column, with a source
line too small to read. Each frame is now checked against tokens.ReelsChrome.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from brand import reel_news as R  # noqa: E402
from brand.content import ContentError  # noqa: E402
from brand.tokens import ReelsChrome as RC  # noqa: E402

NEWS = {'headline': 'ಎಂಆರ್‌ಪಿಎಲ್‌ನಲ್ಲಿ ಭಾರಿ ಸ್ಫೋಟ: ಓರ್ವ ಸಾವು, ಹಲವರಿಗೆ ಗಂಭೀರ ಗಾಯ',
        'place': 'ಮಂಗಳೂರು · ಜೋಕಟ್ಟೆ', 'date': '30 ಸೆಪ್ಟೆಂಬರ್ 2026',
        'facts': ['ಸಿಸಿಆರ್ ಘಟಕದಲ್ಲಿ ಅಧಿಕ ಒತ್ತಡದ ಕೋಲ್ಡ್ ಸೆಪರೇಟರ್ ಒಡೆದು ದುರಂತ',
                  'ಕಿಲೋಮೀಟರ್‌ಗಳವರೆಗೆ ಕೇಳಿಸಿದ ಸದ್ದು; ಕಂಪಿಸಿದ ಸುರತ್ಕಲ್, ಬೈಕಂಪಾಡಿ'],
        'credit': 'ವೀಡಿಯೊ ಕೃಪೆ: ಸ್ಥಳೀಯರು', 'source': 'ಸ್ಥಳ ವರದಿ',
        'verified_by': 'ಗೌತಮ್ ಪದುವರಿ', 'category': 'accident'}


class NothingSitsUnderInstagram(unittest.TestCase):

    def setUp(self):
        self.n = R.News.from_dict(NEWS).validate()

    def test_every_frame_is_clear_of_the_header_buttons_and_caption(self):
        for fn in (R.hook, R.top_band, R.end_card):
            _img, boxes = fn(self.n)          # check() raises on a collision
            self.assertTrue(boxes)
        for k in range(len(self.n.facts)):
            _img, boxes = R.story(self.n, k)
            x0, y0, x1, y1 = boxes['story card']
            self.assertLess(x1, RC.rail_x)
            self.assertLess(y1, RC.bottom)

    def test_a_box_under_the_header_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'header'):
            R.check({'masthead': (64, 100, 400, 160)}, 1080, 1920)
        with self.assertRaisesRegex(ContentError, 'buttons'):
            R.check({'card': (64, 1100, 1016, 1400)}, 1080, 1920)

    def test_the_hook_opens_the_reel_and_every_fact_can_be_read(self):
        plan = R.schedule(self.n, RC.hook_seconds, 30.0)
        self.assertEqual(plan[0][:3], ('hook', None, 0.0))
        for layer, _fi, a, b in plan:
            if layer == 'story':
                self.assertGreaterEqual(b - a, RC.fact_min_seconds)

    def test_a_death_is_ink(self):
        self.assertTrue(self.n.ink_only)


class TheNewsLayerKeepsTheRules(unittest.TestCase):

    def test_footage_needs_a_credit_and_a_source(self):
        for field in ('credit', 'source'):
            d = dict(NEWS, **{field: ''})
            with self.assertRaisesRegex(ContentError, field):
                R.News.from_dict(d).validate()

    def test_a_hook_cannot_assert_guilt(self):
        d = dict(NEWS, category='crime', hook='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ')
        with self.assertRaisesRegex(ContentError, 'guilt'):
            R.News.from_dict(d).validate()


if __name__ == '__main__':
    unittest.main()


class SpeedNewsKeepsClearToo(unittest.TestCase):
    """D96 found the same fault in ಸ್ಪೀಡ್ ನ್ಯೂಸ್: bug and progress bars in the
    header, text allowed under the caption bar."""

    def test_the_chrome_and_text_are_clear(self):
        from brand import speednews as sn
        from brand.tokens import fmt
        L = sn.Layout(fmt('reel').w, fmt('reel').h)
        self.assertLessEqual(L.bottom, RC.bottom)
        import inspect
        src = inspect.getsource(sn.Chrome)
        self.assertIn('RC.top', src)
