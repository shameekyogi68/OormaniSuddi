"""
D92 — three formats, one story in one of them, real pictures first.
===================================================================
What the year's final upgrade promised, asserted end to end: the render
makes exactly the formats the stories' segments ask for, and nothing twice.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from dataclasses import replace

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import render  # noqa: E402
import templates as TP  # noqa: E402
from brand import paper, typo  # noqa: E402
from brand.content import ContentError, Edition, frozen  # noqa: E402

FIXTURE = 'tests/fixture_edition.json'
NOW = '2026-08-25T09:40:00+05:30'


class TheRenderMakesWhatTheSegmentsAsk(unittest.TestCase):
    """D92: the old default rendered a carousel AND a reel of the same
    stories every day. Now each story is drawn once, in its own format."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with frozen(NOW):
            ed = Edition.load(FIXTURE)
            cls.made = render.render_edition(ed, cls.tmp.name,
                                             ['saara', 'mukhya'])
        cls.files = sorted(os.listdir(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_one_saara_set_and_one_mukhya_set(self):
        saara = [f for f in self.files if f.startswith('saara_') and f.endswith('.jpg')]
        mukhya = [f for f in self.files if f.startswith('mukhya_1_') and f.endswith('.jpg')]
        self.assertEqual(len(saara), 3 + 2)       # cover + 3 stories + sources
        self.assertEqual(len(mukhya), 3)

    def test_no_old_format_is_made(self):
        for f in self.files:
            self.assertFalse(f.startswith(('carousel_', 'post_', 'story_9x16',
                                           'broadsheet', 'yt_thumbnail',
                                           'bulletin', 'reel')), f)

    def test_every_rendered_set_has_its_caption(self):
        for name in ('saara_caption.txt', 'mukhya_1_caption.txt'):
            self.assertIn(name, self.files)

    def test_the_schedule_lists_only_what_was_made(self):
        with open(os.path.join(self.tmp.name, 'schedule.txt'),
                  encoding='utf-8') as fh:
            plan = fh.read()
        self.assertIn('saara_01_cover.jpg', plan)
        self.assertIn('mukhya_1_01_cover.jpg', plan)
        self.assertNotIn('roundup.mp4', plan)


class PicturesAreRealFirstAndAIOnlyWhenAsked(unittest.TestCase):

    def setUp(self):
        self.ed = Edition.load(FIXTURE)

    def test_a_mukhya_without_a_picture_will_not_render(self):
        top = replace(self.ed.segment('mukhya')[0], photo=None)
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ContentError):
            TP.get('mukhya')(top, d)

    def test_the_edition_says_what_to_ask(self):
        top = replace(self.ed.segment('mukhya')[0], photo=None)
        ed = replace(self.ed, stories=[top] + self.ed.segment('saara'))
        probs = ed.format_problems()
        self.assertTrue(any('real photograph, or generate' in p for p in probs))

    def test_a_saara_slide_never_draws_a_picture(self):
        """The text bulletin is text, whatever the JSON carries."""
        story = self.ed.segment('mukhya')[0]
        sub = replace(self.ed, stories=[replace(s, photo=story.photo)
                                        for s in self.ed.segment('saara')])
        with tempfile.TemporaryDirectory() as d, frozen(NOW):
            a = TP.render('saara', sub, d)[1]
            with tempfile.TemporaryDirectory() as e:
                bare = replace(self.ed, stories=self.ed.segment('saara'))
                b = TP.render('saara', bare, e)[1]
                from PIL import Image
                self.assertEqual(Image.open(a).tobytes(), Image.open(b).tobytes())


class TheLookHoldsItsRules(unittest.TestCase):

    def test_a_crime_headline_carries_no_red(self):
        """Red on a person's name reads as a verdict (D92 point 5)."""
        crime = next(s for s in Edition.load(FIXTURE).stories
                     if s.category == 'crime')
        self.assertTrue(paper.ink_only(crime))

    def test_the_colon_splits_ink_from_red(self):
        self.assertEqual(paper.split_headline('ಉಡುಪಿ: ಭಾರಿ ಮಳೆ'),
                         ('ಉಡುಪಿ:', 'ಭಾರಿ ಮಳೆ'))
        self.assertEqual(paper.split_headline('ಭಾರಿ ಮಳೆ'), ('ಭಾರಿ ಮಳೆ', ''))

    def test_the_headline_face_is_actually_bold(self):
        """fonts/NotoSansKannada-Bold.ttf is a variable font whose default
        instance is Regular: every "bold" headline was drawn at 400 until
        2026-09-27. The default is now the weight the file name promises."""
        import numpy as np
        from PIL import Image, ImageDraw

        def ink(f):
            im = Image.new('L', (700, 120), 0)
            ImageDraw.Draw(im).text((10, 10), 'ಕರಾವಳಿ ಸುದ್ದಿ', font=f, fill=255)
            return float(np.asarray(im).mean())
        self.assertGreater(ink(typo.font('kn', 70)),
                           ink(typo.font('kn', 70, weight=400)) * 1.3)


if __name__ == '__main__':
    unittest.main()
