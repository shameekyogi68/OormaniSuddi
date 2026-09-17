"""
The morning collapsed to a few taps — and never to a guess. D76.
=================================================================
`draft_edition.py` is the one script allowed to write `editions/{date}.json`
without a person having typed a word of it, so its failure mode must always
be "skip and say why", never "guess and move on". This suite pins that:

  * legally unsafe copy (BNS guilt-assertion) is skipped, not softened
  * a headline that would hard-fail `render.py`'s own preflight is skipped
  * a listing-page URL shared by more than one tip (D75) never becomes a
    story's source, in drafting as well as in body-fetching
  * an English-only tip is left for a person, because this is a Kannada brand
  * `verified_by` is never present on anything this script writes

None of it invents a sentence — every case below copies its headline straight
through, exactly as production tips do.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from scripts import draft_edition as de
from brand.content import Story, ContentError


def tip(headline, url, *, source_name='ಉದಯವಾಣಿ', snippet='', taluk='ಉಡುಪಿ',
        risk='normal', lead_kn=''):
    """A minimal, valid raw tip dict — same shape fetch_daily_news.Tip writes."""
    return {
        'headline': headline,
        'source_name': source_name,
        'source_url': url,
        'snippet': snippet,
        'taluk': taluk,
        'risk': risk,
        'lead_kn': lead_kn,
        'unsupported': [],
    }


class WithInbox(unittest.TestCase):
    """Points draft_edition.INBOX_JSON at a throwaway file for the duration of
    the test, so nothing here can touch the real inbox/today.json."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._real_inbox = de.INBOX_JSON
        de.INBOX_JSON = os.path.join(self._tmp.name, 'today.json')

    def tearDown(self):
        de.INBOX_JSON = self._real_inbox
        self._tmp.cleanup()

    def write_tips(self, tips):
        with open(de.INBOX_JSON, 'w', encoding='utf-8') as fh:
            json.dump({'tips': tips}, fh, ensure_ascii=False)


class ACleanTipBecomesAStory(WithInbox):

    def test_headline_and_source_are_copied_verbatim(self):
        self.write_tips([
            tip('ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ',
                'https://www.example.com/udupi-rain-warning',
                snippet='ತಗ್ಗು ಪ್ರದೇಶ ಜಲಾವೃತ | ಶಾಲೆಗಳಿಗೆ ರಜೆ'),
        ])
        stories, notes = de.build('2026-09-17', 4)
        self.assertEqual(len(stories), 1)
        s = stories[0]
        self.assertEqual(s['headline'], 'ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ')
        self.assertEqual(s['source_urls'], ['https://www.example.com/udupi-rain-warning'])
        self.assertEqual(s['category'], 'weather')
        self.assertIn('ತಗ್ಗು ಪ್ರದೇಶ ಜಲಾವೃತ', s['points'])

    def test_verified_by_is_never_set(self):
        """The one field only a person may fill in (D59) — a script that set
        it would make its own draft look like a checked fact."""
        self.write_tips([tip('ಉಡುಪಿಯಲ್ಲಿ ಹೊಸ ಸೇತುವೆ ಉದ್ಘಾಟನೆ',
                             'https://www.example.com/bridge-opens')])
        stories, _ = de.build('2026-09-17', 4)
        self.assertNotIn('verified_by', stories[0])
        self.assertNotIn('verified_at', stories[0])


class SkippedRatherThanGuessed(WithInbox):

    def test_a_guilt_asserting_crime_headline_is_skipped_with_a_note(self):
        """BNS §356: a headline that states guilt as fact is not something
        this script may soften into an allegation — that is writing."""
        self.write_tips([tip('ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ',
                             'https://www.example.com/case-1', risk='crime')])
        stories, notes = de.build('2026-09-17', 4)
        self.assertEqual(stories, [])
        self.assertTrue(any('needs a human rewrite' in n for n in notes))

    def test_a_headline_too_long_for_the_render_is_skipped_with_a_note(self):
        """A lead sentence copied verbatim can be a fine sentence and a
        broken headline — render.py's preflight hard-fails past ~113 chars."""
        long_headline = 'ಉಡುಪಿ ಜಿಲ್ಲೆಯ ಕುಂದಾಪುರ ತಾಲೂಕಿನ ಹೆಮ್ಮಾಡಿ ಗ್ರಾಮದಲ್ಲಿ ' * 3
        self.write_tips([tip(long_headline.strip(),
                             'https://www.example.com/long-lead')])
        stories, notes = de.build('2026-09-17', 4)
        self.assertEqual(stories, [])
        self.assertTrue(any('would fail the render as-is' in n for n in notes))

    def test_an_english_only_tip_is_left_for_a_person(self):
        """This is a Kannada brand — an English lead is not this script's to
        translate, which would be writing, not copying."""
        self.write_tips([tip('New flyover opens in Udupi today',
                             'https://www.example.com/flyover')])
        stories, notes = de.build('2026-09-17', 4)
        self.assertEqual(stories, [])

    def test_nothing_safe_gives_one_clear_note_not_silence(self):
        self.write_tips([tip('Nothing here is in Kannada at all',
                             'https://www.example.com/x')])
        stories, notes = de.build('2026-09-17', 4)
        self.assertEqual(stories, [])
        self.assertTrue(any('nothing in the tip sheet safely auto-drafted' in n
                            for n in notes))


class SharedUrlsAreListingPagesNotArticles(WithInbox):

    def test_a_source_url_two_tips_share_is_excluded_from_drafting(self):
        """D75 found this bug in body-fetching; the same reasoning applies to
        drafting a story's source_url — a listing page is not something a
        person can reopen and confirm one specific fact against."""
        generic = 'https://www.example.com/district-news'
        self.write_tips([
            tip('ಉಡುಪಿಯಲ್ಲಿ ಸುದ್ದಿ ಒಂದು', generic, taluk='ಉಡುಪಿ'),
            tip('ಕುಂದಾಪುರದಲ್ಲಿ ಸುದ್ದಿ ಎರಡು', generic, taluk='ಕುಂದಾಪುರ'),
            tip('ಕಾರ್ಕಳದಲ್ಲಿ ನಿಜವಾದ ಸುದ್ದಿ', 'https://www.example.com/karkala-real',
               taluk='ಕಾರ್ಕಳ'),
        ])
        stories, notes = de.build('2026-09-17', 4)
        urls = [u for s in stories for u in s['source_urls']]
        self.assertNotIn(generic, urls)
        self.assertIn('https://www.example.com/karkala-real', urls)


class OneStoryPerTaluk(WithInbox):

    def test_a_second_tip_from_the_same_taluk_is_left_out_of_the_draft(self):
        """So the morning brief is not four Byndoor stories — a human can
        always add more by hand."""
        self.write_tips([
            tip('ಉಡುಪಿ ಸುದ್ದಿ ಒಂದು', 'https://www.example.com/u1', taluk='ಉಡುಪಿ'),
            tip('ಉಡುಪಿ ಸುದ್ದಿ ಎರಡು', 'https://www.example.com/u2', taluk='ಉಡುಪಿ'),
        ])
        stories, _ = de.build('2026-09-17', 4)
        self.assertEqual(len(stories), 1)


class MaxStoriesIsRespected(WithInbox):

    def test_build_never_returns_more_than_max(self):
        places = ['ಉಡುಪಿ', 'ಕುಂದಾಪುರ', 'ಕಾರ್ಕಳ', 'ಕಾಪು', 'ಹೆಬ್ರಿ', 'ಬೈಂದೂರು']
        self.write_tips([
            tip(f'{p} ಸುದ್ದಿ', f'https://www.example.com/{i}', taluk=p)
            for i, p in enumerate(places)
        ])
        stories, _ = de.build('2026-09-17', 3)
        self.assertEqual(len(stories), 3)


class RiskFlagsCarryForward(WithInbox):

    def test_minor_risk_sets_involves_minor_defaulting_to_caution(self):
        self.write_tips([tip('ಬಾಲಕನ ಶೋಧ ಕಾರ್ಯಾಚರಣೆ ಮುಂದುವರಿಕೆ',
                             'https://www.example.com/minor-case', risk='minor')])
        stories, _ = de.build('2026-09-17', 4)
        self.assertEqual(len(stories), 1)
        self.assertTrue(stories[0].get('involves_minor'))

    def test_a_sexual_offence_keyword_sets_the_flag(self):
        self.write_tips([tip('ಮಹಿಳೆಗೆ ಲೈಂಗಿಕ ಕಿರುಕುಳ ಪ್ರಕರಣ ದಾಖಲು',
                             'https://www.example.com/case-2', risk='crime')])
        stories, notes = de.build('2026-09-17', 4)
        self.assertEqual(len(stories), 1, notes)
        self.assertTrue(stories[0].get('sexual_offence'))


class EveryDraftedStoryActuallyValidates(WithInbox):
    """build() already filters through Story.validate() and preflight(); this
    just pins that nothing slips past both into the written file."""

    def test_every_story_build_returns_survives_validate_and_preflight(self):
        from brand.qa import preflight
        self.write_tips([
            tip('ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', 'https://www.example.com/a', taluk='ಉಡುಪಿ'),
            tip('ಕುಂದಾಪುರದಲ್ಲಿ ಜಾತ್ರೆ ಸಂಭ್ರಮ', 'https://www.example.com/b',
               taluk='ಕುಂದಾಪುರ'),
        ])
        stories, _ = de.build('2026-09-17', 4)
        self.assertTrue(stories)
        for d in stories:
            story = Story.from_dict(d).validate()
            self.assertFalse(preflight(story, 'post').fail)


if __name__ == '__main__':
    unittest.main()
