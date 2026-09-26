"""
The picture desk, when nobody is at it. D80.
===========================================
House rule 2026-09-17-03 requires a photograph on every carousel slide and
the gate enforces it as IMG-04. `draft_edition.py` attaches none — it copies
text and nothing else — so the two changes together held every auto-drafted
morning at the gate on four counts before anybody had read a word. That is
what this module fixes, and these are the three ways it could go wrong.

  * **The wrong picture.** A frame the story cannot defend is worse than no
    frame: `docs/AI_BRIEF.md` has always said so. The first run put a
    farmers-market photograph on a story about a political row, because `ದರ`
    (price) sits inside `ವಿಚಾರದಲ್ಲಿ` (on the matter of).
  * **The same picture twice.** Two slides of one carousel carrying the
    identical frame reads as a broken render.
  * **A picture at any cost.** When the library holds nothing that belongs,
    the honest answer is to leave it bare and let a person choose.
"""
from __future__ import annotations

import os
import unittest

from brand import stock
from brand.content import Story, Edition, Photo, OWN_REPORTING


def story(headline, category='civic', **kw):
    base = dict(headline=headline, category=category, sources=[OWN_REPORTING],
                verified_by='Gautam Paduvari')
    base.update(kw)
    return Story(**base)


class AFrameTheStoryCanDefend(unittest.TestCase):

    def test_a_word_in_the_story_picks_the_frame_over_the_category(self):
        s = story('ಕುಂದಾಪುರ: ಕಿಂಡಿ ಅಣೆಕಟ್ಟುಗಳಿಗೆ ಬೇಗ ಹಲಗೆ', 'farm')
        self.assertEqual(stock.frame_for(s),
                         'coastal_vented_dam_river_water.jpg')

    def test_the_category_alone_never_picks_a_frame(self):
        """A category is what a story is filed under, not what happened in
        it. The PGCET seat allotment that got a certificate ceremony was the
        category match house rule 2026-09-20-01 forbids. D85."""
        s = story('ಜಿಲ್ಲಾಡಳಿತದಿಂದ ಹೊಸ ಆದೇಶ ಪ್ರಕಟ', 'weather')
        self.assertEqual(stock.frame_for(s), '')

    def test_exam_results_get_the_portal_not_the_ceremony(self):
        s = story('ಪಿಜಿಸಿಇಟಿ ಅಣಕು ಸೀಟು ಹಂಚಿಕೆ ಫಲಿತಾಂಶ ಪ್ರಕಟ', 'education')
        self.assertEqual(stock.frame_for(s),
                         'student_exam_results_counselling_portal.jpg')

    def test_the_best_match_wins_not_the_first_listed(self):
        """Three words about a flooded road beat one incidental word about
        an ambulance, whichever the table lists first."""
        s = story('ಜಲಾವೃತ ರಸ್ತೆ: ಗ್ರಾಮಸ್ಥರ ಆಕ್ರೋಶ', 'civic',
                  deck='ಚರಂಡಿ ಇಲ್ಲದೆ ಕೆಸರು ತುಂಬಿದ ರಸ್ತೆ',
                  points=['ಅಪಘಾತ ಭೀತಿ ಇದೆ ಎಂದು ಗ್ರಾಮಸ್ಥರು ಹೇಳಿದ್ದಾರೆ'])
        self.assertEqual(stock.frame_for(s),
                         'civic_flooded_road_villagers_complaint.jpg')

    def test_a_passing_mention_in_the_facts_is_not_enough(self):
        """One word in the third bullet is context, not the story."""
        s = story('ಗ್ರಾಮ ಸಭೆಯಲ್ಲಿ ಹೊಸ ನಿರ್ಣಯ', 'civic',
                  points=['ಮಳೆಗಾಲದ ಮೊದಲು ಕಾಮಗಾರಿ ಮುಗಿಸಲು ಸೂಚನೆ'])
        self.assertEqual(stock.frame_for(s), '')

    def test_a_two_word_key_can_match(self):
        """Split per word, ರೆಡ್ ಅಲರ್ಟ್ could never match anything."""
        self.assertTrue(stock._mentions('ಕರಾವಳಿಗೆ ರೆಡ್ ಅಲರ್ಟ್ ಘೋಷಣೆ', 'ರೆಡ್ ಅಲರ್ಟ್'))
        self.assertFalse(stock._mentions('ಬೆರೆಡ್ ಅಲರ್ಟ್', 'ರೆಡ್ ಅಲರ್ಟ್'))

    def test_a_keyword_inside_another_word_does_not_count(self):
        """ದರ (price) sits inside ವಿಚಾರದಲ್ಲಿ. Matching raw substrings put a
        farmers' market on a story about a political row."""
        s = story('ವಂದೇ ಮಾತರಂ ಹಾಡುವ ವಿಚಾರದಲ್ಲಿ ಬಿಜೆಪಿ ಚುನಾವಣಾ ರಾಜಕೀಯ', 'civic')
        self.assertNotEqual(stock.frame_for(s),
                            'rural_weekly_market_farmers_shandy.jpg')

    def test_an_inflected_form_still_matches(self):
        """Kannada agglutinates: ಮಳೆ becomes ಮಳೆಯಿಂದ and it is the same word."""
        self.assertTrue(stock._mentions('ಭಾರಿ ಮಳೆಯಿಂದ ಹಾನಿ', 'ಮಳೆ'))
        self.assertFalse(stock._mentions('ವಿಚಾರದಲ್ಲಿ ಚರ್ಚೆ', 'ದರ'))


class NothingIsAttachedThatCannotBeDefended(unittest.TestCase):

    def test_a_category_with_no_honest_frame_gets_none(self):
        """sport and obituary have nothing in this library, and inventing a
        match for them is the one thing this module must not do."""
        self.assertEqual(stock.frame_for(story('ಪಂದ್ಯ ಗೆದ್ದ ತಂಡ', 'sport')), '')
        self.assertIsNone(stock.photo_for(story('ನಿಧನ', 'obituary')))

    def test_a_frame_named_here_is_a_frame_that_exists(self):
        """A table pointing at a deleted file fails at render, not here."""
        for name, _ in stock.KEYWORD_FRAMES:
            self.assertTrue(stock._exists(name), name)

    def test_every_frame_it_can_choose_is_in_the_catalogue(self):
        """An uncatalogued frame is invisible to the rule that says check
        stock before generating, so it gets generated again."""
        with open(os.path.join(stock.STOCK_DIR, 'CATALOG.md'),
                  encoding='utf-8') as fh:
            cat = fh.read()
        for name, _ in stock.KEYWORD_FRAMES:
            self.assertIn(name, cat, f'{name} is not in CATALOG.md')


class AFrameWithTextInItIsNeverAttached(unittest.TestCase):
    """D91. 21 of 39 frames carried AI-made text — UDUPI TRAFFIC on a jeep,
    a court sign naming ಕುಂದಾಪುರ, a fake officer's nameplate, a leopard
    already in the trap. A story that says exactly what such a frame is for
    still does not get it."""

    def test_every_withdrawn_frame_is_refused_even_on_its_own_words(self):
        for name, words in stock.KEYWORD_FRAMES:
            if name not in stock.WITHDRAWN:
                continue
            s = story(' '.join(words[:3]), 'civic')
            self.assertNotEqual(stock.frame_for(s), name, name)

    def test_every_withdrawal_says_why(self):
        for name, why in stock.WITHDRAWN.items():
            self.assertTrue(why.strip(), name)
            self.assertTrue(stock._exists(name), f'{name} is not in assets/stock')


class TheLabellingIsHonest(unittest.TestCase):

    def test_a_generated_frame_is_never_called_representative(self):
        """`representative` means a real photograph of a similar scene.
        These are generated, so they wear nature='ai' and the card says
        ಎಐ ರಚಿತ ಚಿತ್ರ on every frame it appears in (D57)."""
        p = stock.photo_for(story('ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'weather'))
        self.assertEqual(p.nature, 'ai')
        self.assertEqual(p.licence, 'own')
        self.assertTrue(p.caption.strip())

    def test_the_label_is_said_once(self):
        """House rule 2026-09-17-05: disclosure prints ಎಐ ರಚಿತ ಚಿತ್ರ itself."""
        p = stock.photo_for(story('ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'weather'))
        self.assertNotIn('ಎಐ', p.caption)
        self.assertNotIn('AI', p.credit)

    def test_the_photo_it_makes_survives_validation(self):
        s = story('ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'weather')
        s.photo = stock.photo_for(s)
        s.validate()


class NoCarouselRepeatsAFrame(unittest.TestCase):

    def test_two_stories_of_one_category_get_different_frames(self):
        ed = Edition(stories=[story('ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'weather'),
                              story('ಚಂಡಮಾರುತ: ಕಡಲ್ಕೊರೆತ ಭೀತಿ', 'weather')],
                     edition_no=1)
        filled, bare = stock.illustrate(ed)
        self.assertEqual(filled, 2)
        self.assertEqual(bare, [])
        paths = {s.photo.path for s in ed.stories}
        self.assertEqual(len(paths), 2, 'the same frame was used twice')

    def test_a_photograph_somebody_chose_is_never_replaced(self):
        chosen = Photo('assets/stock/coastal_fishing_harbour_docks.jpg',
                       nature='ai', credit=stock.CREDIT, licence='own',
                       caption='x')
        ed = Edition(stories=[story('ಭಾರಿ ಮಳೆ', 'weather', photo=chosen)],
                     edition_no=1)
        filled, _ = stock.illustrate(ed)
        self.assertEqual(filled, 0)
        self.assertEqual(ed.stories[0].photo.path, chosen.path)


if __name__ == '__main__':
    unittest.main()
