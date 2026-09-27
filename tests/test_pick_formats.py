"""
The formats an edition renders are its stories' segments, and nothing else.
D92 — replacing "carousel every day, plus one reel" (D77, D81), which put the
same stories out twice every morning.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from scripts import pick_formats as pf


def edition(*segments):
    return {'schema_version': 4, 'date': '2026-09-27T08:00:00+05:30',
            'edition_no': 1,
            'stories': [{'headline': 'ಸುದ್ದಿ', 'category': 'civic',
                         'location': 'ಉಡುಪಿ', 'sources': ['ಉದಯವಾಣಿ'],
                         'source_urls': ['https://www.example.com/x'],
                         'segment': s} for s in segments]}


class FormatsComeFromSegments(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, 'e.json')

    def tearDown(self):
        self._tmp.cleanup()

    def formats(self, *segments):
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(edition(*segments), fh, ensure_ascii=False)
        return pf.formats_for_edition(self.path)

    def test_each_segment_present_is_one_format(self):
        f, _ = self.formats('saara', 'saara', 'speed', 'speed', 'speed', 'mukhya')
        self.assertEqual(f, ['saara', 'mukhya', 'roundup'])

    def test_no_format_is_added_that_no_story_asked_for(self):
        """The old rule shipped a carousel every day whatever the stories were."""
        f, _ = self.formats('speed', 'speed', 'speed')
        self.assertEqual(f, ['roundup'])
        self.assertNotIn('saara', f)

    def test_a_story_without_a_segment_is_named_not_guessed(self):
        f, why = self.formats('saara', '')
        self.assertEqual(f, ['saara'])
        self.assertIn('no segment', why)


if __name__ == '__main__':
    unittest.main()
