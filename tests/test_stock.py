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
        s = story('Karkala: ಜ್ವರದಿಂದ ವ್ಯಕ್ತಿ ಸಾವು', 'health')
        self.assertEqual(stock.frame_for(s),
                         'health_hospital_campus_outpatients.jpg')

    def test_the_category_decides_when_no_word_does(self):
        s = story('ಜಿಲ್ಲಾಡಳಿತದಿಂದ ಹೊಸ ಆದೇಶ ಪ್ರಕಟ', 'weather')
        self.assertEqual(stock.frame_for(s),
                         'coastal_ghats_monsoon_homestead.jpg')

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
        for name in stock.CATEGORY_FRAMES.values():
            self.assertTrue(stock._exists(name), name)
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


class TheLabellingIsHonest(unittest.TestCase):

    def test_a_generated_frame_is_never_called_representative(self):
        """`representative` means a real photograph of a similar scene.
        These are generated, so they wear nature='ai' and the card says
        ಎಐ ರಚಿತ ಚಿತ್ರ on every frame it appears in (D57)."""
        p = stock.photo_for(story('ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'weather'))
        self.assertEqual(p.nature, 'ai')
        self.assertEqual(p.licence, 'own')
        self.assertTrue(p.caption.strip())

    def test_the_photo_it_makes_survives_validation(self):
        s = story('ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'weather')
        s.photo = stock.photo_for(s)
        s.validate()


class NoCarouselRepeatsAFrame(unittest.TestCase):

    def test_two_stories_of_one_category_get_different_frames(self):
        ed = Edition(stories=[story('ಆಸ್ಪತ್ರೆಗೆ ದಾಖಲು', 'health'),
                              story('ಅಪಘಾತದಲ್ಲಿ ಗಾಯ', 'health')],
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
