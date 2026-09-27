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


class TheFirstSaaraFaults(unittest.TestCase):
    """Found on the first real ಸುದ್ದಿ ಸಾರ, 2026-09-27. Each is pinned so it
    cannot come back."""

    def _stories(self, n, headline, **kw):
        from brand.content import OWN_REPORTING, Story
        return [Story(headline=headline, category='civic', location='ಕುಂದಾಪುರ',
                      sources=[OWN_REPORTING], segment='saara',
                      points=['ಒಂದು ಅಂಶ.'], **kw) for _ in range(n)]

    def test_six_long_headlines_never_reach_the_footer(self):
        """The sixth entry ran into the footer rule."""
        from brand.tokens import Limits
        long = ('ಕುಂದಾಪುರ-ಬೈಂದೂರು: ರಾಷ್ಟ್ರೀಯ ಹೆದ್ದಾರಿ 66ರಲ್ಲಿ ಗ್ರೇಡ್ '
                'ಸೆಪರೇಟರ್ ನಿರ್ಮಾಣಕ್ಕೆ ಪ್ರಸ್ತಾವನೆ ಸಲ್ಲಿಕೆ')
        at_limit = long[:Limits.headline_chars].rsplit(' ', 1)[0]
        ed = Edition(stories=self._stories(Limits.saara_max_stories, at_limit),
                     edition_no=1, schema_version=4)
        with tempfile.TemporaryDirectory() as d, frozen(NOW):
            TP.render('saara', ed, d)     # asserts the index fits
        # Past the house limit: set compactly or refused with a reason —
        # never drawn over the footer.
        over = Edition(stories=self._stories(Limits.saara_max_stories,
                                             long + ' ' + long),
                       edition_no=1, schema_version=4)
        with tempfile.TemporaryDirectory() as d, frozen(NOW):
            try:
                TP.render('saara', over, d)   # fits compactly (checked inside)
            except ContentError:
                pass                          # or is refused with a reason

    def test_the_place_is_not_said_twice(self):
        """Kicker "/ ಕುಂದಾಪುರ" over a headline "ಕುಂದಾಪುರ: …"."""
        st = self._stories(1, 'ಕುಂದಾಪುರ: ಕಡಲತೀರಕ್ಕೆ ಮೀನುಗಳ ರಾಶಿ')[0]
        self.assertTrue(paper.leads_with_place(st))
        st2 = self._stories(1, 'ಕಡಲತೀರಕ್ಕೆ ಮೀನುಗಳ ರಾಶಿ')[0]
        self.assertFalse(paper.leads_with_place(st2))

    def test_a_death_is_ink_whatever_it_was_filed_under(self):
        """"ಕಾರ್ಮಿಕ ಸಾವು" was set in red under ಆಡಳಿತ."""
        st = self._stories(1, 'ಗಂಗೊಳ್ಳಿ: ಬಂದರಿನಲ್ಲಿ ಬಿದ್ದು ಗಾಯಗೊಂಡಿದ್ದ ಕಾರ್ಮಿಕ ಸಾವು')[0]
        self.assertTrue(paper.ink_only(st))

    def test_a_coastal_desk_has_somewhere_true_to_file_things(self):
        from brand.tokens import CATEGORIES
        for k in ('fisheries', 'environment', 'accident'):
            self.assertIn(k, CATEGORIES)


class TheDistributionPlan(unittest.TestCase):
    """D94: where each format goes, and what goes with it."""

    def test_the_day_runs_morning_lunch_evening(self):
        from brand import copy as C
        plan = C.publishing_plan(has_saara=True, has_roundup=True,
                                 mukhya=[(1, False, '')])
        self.assertEqual([s.at for s in plan], ['08:00', '13:30', '18:30'])
        for s in plan:
            self.assertIn('Facebook', s.platform)
            self.assertNotIn('YouTube', s.platform)

    def test_a_whatsapp_group_never_gets_more_than_the_limit(self):
        from brand import copy as C
        from brand.tokens import Limits
        from brand.content import OWN_REPORTING, Story
        ed = Edition(stories=[Story(headline=f'ಕುಂದಾಪುರ: ಸುದ್ದಿ {i}',
                                    location='ಕುಂದಾಪುರ', segment='saara',
                                    sources=[OWN_REPORTING]) for i in range(6)],
                     edition_no=1, schema_version=4)
        digests = C.community_digests(ed)
        self.assertIn('kundapura_byndoor', digests)
        self.assertNotIn('mangaluru', digests)       # nothing of theirs today
        body = digests['kundapura_byndoor'][1]
        items = sum(1 for e in ('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣') if e in body)
        self.assertEqual(items, Limits.whatsapp_items_max)

    def test_a_facebook_group_post_asks_and_carries_no_link(self):
        from brand import copy as C
        top = Edition.load(FIXTURE).segment('mukhya')[0]
        post = C.facebook_group_post(top)
        self.assertNotIn('http', post)
        self.assertIn('?', post)

    def test_gulf_news_has_a_category(self):
        from brand.tokens import CATEGORIES
        self.assertEqual(CATEGORIES['nri']['kn'], 'ಅನಿವಾಸಿ')
