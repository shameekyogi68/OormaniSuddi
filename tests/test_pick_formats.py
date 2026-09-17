"""
Carousel every day; a reel only when the lead story earns it. D77, house
rule 2026-09-17-02.
=============================================================================
`pick_formats.py` replaces "render the same four formats every morning"
with a decision made from evidence already trusted elsewhere:
`brand.reach.should_be_reel()` (D72), the same relevance check the Chief
Editor gate already reads. story_card and broadsheet are dropped from the
default entirely — the editor's own call, not something to re-derive here —
so this suite is really only about the one live decision left: reel or not.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from scripts import pick_formats as pf


def edition(lead_category, lead_location, *, lead_headline='ಸುದ್ದಿ ಶೀರ್ಷಿಕೆ'):
    return {
        'date': '2026-09-17T08:00:00+05:30',
        'edition_no': 1,
        'stories': [
            {
                'headline': lead_headline,
                'category': lead_category,
                'points': ['ಒಂದು ಅಂಶ'],
                'location': lead_location,
                'sources': ['ಉದಯವಾಣಿ'],
                'source_urls': ['https://www.example.com/x'],
                'status': 'developing',
            },
        ],
    }


class WithATempEdition(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, 'edition.json')

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, data):
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)


class CarouselIsAlwaysIncluded(WithATempEdition):

    def test_carousel_is_in_every_result(self):
        self.write(edition('civic', 'ಉಡುಪಿ'))
        formats, _ = pf.formats_for_edition(self.path)
        self.assertIn('carousel', formats)

    def test_an_empty_edition_still_returns_carousel(self):
        self.write({'date': '2026-09-17T08:00:00+05:30', 'edition_no': 1,
                    'stories': []})
        formats, why = pf.formats_for_edition(self.path)
        self.assertEqual(formats, ['carousel'])
        self.assertIn('no stories', why)


class ReelIsEarnedNotDefault(WithATempEdition):

    def test_a_civic_notice_does_not_earn_a_reel(self):
        """A notice is screenshotted, not watched — FORMAT_BY_CATEGORY says
        so directly for 'civic'."""
        self.write(edition('civic', 'ಉಡುಪಿ'))
        formats, why = pf.formats_for_edition(self.path)
        self.assertNotIn('reel', formats)
        self.assertIn('screenshotted', why)

    def test_a_locally_relevant_weather_story_earns_a_reel(self):
        self.write(edition('weather', 'ಕುಂದಾಪುರ',
                          lead_headline='ಕುಂದಾಪುರದಲ್ಲಿ ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ'))
        formats, why = pf.formats_for_edition(self.path)
        self.assertIn('reel', formats)

    def test_a_reel_worthy_category_with_no_place_does_not_earn_one(self):
        """Nobody scrolling can tell it is about their town without a place
        named — should_be_reel refuses even a 'reel' category here."""
        self.write(edition('weather', ''))
        formats, why = pf.formats_for_edition(self.path)
        self.assertNotIn('reel', formats)

    def test_only_the_lead_story_is_considered(self):
        """render.py's reel template takes the lead story only (stories=1) —
        a reel-worthy story buried second in the edition changes nothing."""
        data = edition('civic', 'ಉಡುಪಿ')
        data['stories'].append({
            'headline': 'ಕುಂದಾಪುರದಲ್ಲಿ ಭಾರಿ ಮಳೆ ಎಚ್ಚರಿಕೆ', 'category': 'weather',
            'points': ['ಅಂಶ'], 'location': 'ಕುಂದಾಪುರ',
            'sources': ['ಉದಯವಾಣಿ'], 'source_urls': ['https://www.example.com/y'],
            'status': 'developing',
        })
        self.write(data)
        formats, _ = pf.formats_for_edition(self.path)
        self.assertNotIn('reel', formats)


class StoryCardAndBroadsheetAreNeverInTheDefault(WithATempEdition):

    def test_neither_ever_appears(self):
        for cat in ('civic', 'weather', 'crime', 'culture', 'sport', 'farm',
                   'health', 'education', 'explainer'):
            self.write(edition(cat, 'ಉಡುಪಿ'))
            formats, _ = pf.formats_for_edition(self.path)
            self.assertNotIn('story_card', formats)
            self.assertNotIn('broadsheet', formats)


if __name__ == '__main__':
    unittest.main()
