"""
Reach is people who can use the post, not tags on it. D84, D86, D87.
==============================================================
  * Instagram reads five hashtags on a post or Reel since December 2025.
    Every caption this system writes stays inside that, and the towns that
    do not fit in five tags are still in the caption as searchable words.
  * A trend goes on a post only when the post is about it. An unrelated
    trend is misleading metadata on YouTube and a swipe-past on Instagram.
  * Every figure published is in the source it cites, and a source page that
    does not carry the story is caught before anyone reads it as evidence.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from brand import copy as C
from brand import factcheck as F
from brand import trends as T
from brand.content import Story, Edition, OWN_REPORTING
from brand.tokens import Limits


def story(headline='ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', location='ಉಡುಪಿ', category='weather',
          **kw):
    base = dict(headline=headline, location=location, category=category,
                sources=[OWN_REPORTING], verified_by='Gautam Paduvari')
    base.update(kw)
    return Story(**base)


TREND_FARM = {'term': 'ರೈತ', 'tag': 'ರೈತ', 'match': ['ರೈತ'], 'rank': 1,
              'platforms': ['instagram', 'youtube']}
TREND_TV = {'term': 'ಬಿಗ್ ಬಾಸ್ ಕನ್ನಡ', 'tag': 'ಬಿಗ್ಬಾಸ್ಕನ್ನಡ',
            'match': ['ಬಿಗ್ ಬಾಸ್ ಕನ್ನಡ', 'ಬಿಗ್', 'ಬಾಸ್', 'ಕನ್ನಡ'], 'rank': 2,
            'platforms': ['instagram', 'youtube']}


class FiveTagsAndTheRestAsWords(unittest.TestCase):

    def setUp(self):
        p = mock.patch.object(T, 'load', return_value=[])
        p.start()
        self.addCleanup(p.stop)

    def test_every_caption_stays_inside_the_platform_limit(self):
        ed = Edition(stories=[story(location=l) for l in
                              ('ಉಡುಪಿ', 'ಕುಂದಾಪುರ', 'ಬೈಂದೂರು', 'ಕಾರ್ಕಳ',
                               'ಮಲ್ಪೆ', 'ಹೆಬ್ರಿ')], edition_no=1)
        for c in (C.for_story(ed.stories[0]), C.for_edition(ed),
                  C.for_roundup(ed)):
            last = c.instagram.strip().split('\n')[-1]
            self.assertLessEqual(last.count('#'), Limits.ig_hashtags_max, last)

    def test_towns_that_miss_the_tags_are_still_searchable(self):
        towns = ('ಉಡುಪಿ', 'ಕುಂದಾಪುರ', 'ಬೈಂದೂರು', 'ಕಾರ್ಕಳ', 'ಮಲ್ಪೆ', 'ಹೆಬ್ರಿ')
        ed = Edition(stories=[story(location=l) for l in towns], edition_no=1)
        cap = C.for_edition(ed).instagram
        for kn in towns:
            self.assertIn(kn, cap)
        for en in ('Udupi', 'Kundapura', 'Byndoor', 'Karkala', 'Malpe', 'Hebri'):
            self.assertIn(en, cap)

    def test_youtube_tags_fit_the_field(self):
        ed = Edition(stories=[story(location=l) for l in
                              ('ಉಡುಪಿ', 'ಕುಂದಾಪುರ', 'ಬೈಂದೂರು')], edition_no=1)
        tags = C.youtube_tags(ed)
        self.assertLessEqual(len(', '.join(tags)), Limits.yt_tags_chars)
        self.assertIn('Udupi', tags)


class ATrendOnlyWhenItIsTheStory(unittest.TestCase):

    def test_a_story_about_the_trend_carries_it(self):
        s = story('ಕುಂದಾಪುರ: ಅಡಿಕೆ ಬೆಲೆ ಕುಸಿತ, ರೈತರ ಆತಂಕ', 'ಕುಂದಾಪುರ', 'farm')
        self.assertEqual(T.for_story(s, items=[TREND_FARM, TREND_TV]), ['ರೈತ'])

    def test_one_shared_common_word_is_not_the_story(self):
        """ದಕ್ಷಿಣ ಕನ್ನಡ has ಕನ್ನಡ in it. That does not make a flood story
        about a reality show."""
        s = story('ದಕ್ಷಿಣ ಕನ್ನಡದಲ್ಲಿ ಭಾರಿ ಮಳೆ', 'ದಕ್ಷಿಣ ಕನ್ನಡ')
        self.assertEqual(T.for_story(s, items=[TREND_TV]), [])

    def test_an_unrelated_trend_never_reaches_a_caption(self):
        with mock.patch.object(T, 'load', return_value=[TREND_TV]):
            tags = C.hashtags(story())
        self.assertNotIn('ಬಿಗ್ಬಾಸ್ಕನ್ನಡ', tags)

    def test_a_related_trend_takes_a_slot_and_the_cap_holds(self):
        s = story('ಕುಂದಾಪುರ: ಅಡಿಕೆ ಬೆಲೆ ಕುಸಿತ, ರೈತರ ಆತಂಕ', 'ಕುಂದಾಪುರ', 'farm')
        with mock.patch.object(T, 'load', return_value=[TREND_FARM]):
            tags = C.hashtags(s)
        self.assertIn('ರೈತ', tags)
        self.assertLessEqual(len(tags), Limits.ig_hashtags_max)


class EveryFigureIsInTheSource(unittest.TestCase):

    URL = 'https://example.org/udupi-rain'
    SOURCE = ('Udupi: The IMD has issued an orange alert for 3 districts. '
              'Schools in Udupi will remain closed on Thursday.')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, val in (('SOURCES_DIR', os.path.join(self.tmp.name, 's')),
                          ('LEDGER_DIR', os.path.join(self.tmp.name, 'l')),
                          ('TIP_SHEET', os.path.join(self.tmp.name, 'x.json'))):
            p = mock.patch.object(F, name, val)
            p.start()
            self.addCleanup(p.stop)
        F.save_source(self.URL, self.SOURCE)

    def sourced(self, **kw):
        return story(sources=['IMD'], source_urls=[self.URL], **kw)

    def test_a_figure_in_the_source_passes(self):
        r = F.check(self.sourced(headline='ಉಡುಪಿ ಸೇರಿ 3 ಜಿಲ್ಲೆಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್'))
        self.assertEqual(r.figures, [])

    def test_an_invented_figure_blocks(self):
        """A helpline, a death toll, a rupee amount: the words a model adds."""
        r = F.check(self.sourced(takeaway='ಸಹಾಯವಾಣಿ 1077 ಸಂಪರ್ಕಿಸಿ'))
        self.assertIn(('takeaway', '1077'), r.figures)
        self.assertTrue(r.blocking)

    def test_a_quote_that_is_in_the_source_proves_a_figure(self):
        claims = [{'url': self.URL, 'token': '2',
                   'quote': 'Schools in Udupi will remain closed'}]
        r = F.check(self.sourced(deck='2 ದಿನ ಶಾಲೆಗಳಿಗೆ ರಜೆ'), claims)
        self.assertEqual(r.figures, [])

    def test_a_quote_that_is_not_in_the_source_proves_nothing(self):
        claims = [{'url': self.URL, 'token': '2',
                   'quote': 'schools closed for two days'}]
        r = F.check(self.sourced(deck='2 ದಿನ ಶಾಲೆಗಳಿಗೆ ರಜೆ'), claims)
        self.assertIn(('deck', '2'), r.figures)

    def test_a_page_that_does_not_carry_the_story_is_not_evidence(self):
        """2026-09-24: six model-written URLs served a sidebar of other
        headlines. Keeping that page as the 'source' would pass nothing and
        prove nothing."""
        s = self.sourced(headline='ಮಲ್ಪೆ ಬಂದರು: ಸಮುದ್ರಕ್ಕೆ ಬಿದ್ದು ಮೀನುಗಾರ ಸಾವು',
                         deck='ಮೀನುಗಾರಿಕೆ ದೋಣಿಯಿಂದ ಆಕಸ್ಮಿಕವಾಗಿ ಬಿದ್ದ ಕಾರ್ಮಿಕನ ಶವ ಪತ್ತೆ')
        sidebar = ('ಪ್ರಧಾನಿ ನರೇಂದ್ರ ಮೋದಿ ಭೇಟಿಯಾದ ಪೇಜಾವರ ಶ್ರೀಗಳು ಇಂದಿರಾ ನಗರ '
                   'ಅಂಗನವಾಡಿಗೆ ಬೇಕಿದೆ ತುರ್ತು ಕಾಯಕಲ್ಪ ಪ್ರವಾಸೋದ್ಯಮ ನೀತಿ')
        self.assertFalse(F.carries(s, sidebar))

    def test_own_reporting_is_the_reporters_word(self):
        self.assertEqual(F.check(story()).state, 'own')


class TheTeamKnowsItsLimits(unittest.TestCase):
    """D87. Each agent is jailed to this repository and none of them can do
    what a person is responsible for."""

    AGENTS = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), '.claude', 'agents')

    def test_the_four_desks_exist_and_are_jailed(self):
        for name in ('fact-checker', 'picture-editor', 'social-writer',
                     'trend-scout'):
            with open(os.path.join(self.AGENTS, f'{name}.md'),
                      encoding='utf-8') as fh:
                body = fh.read()
            self.assertIn(f'name: {name}', body)
            self.assertIn('Workspace jail', body, name)

    def test_the_fact_desk_cannot_verify_on_a_persons_behalf(self):
        with open(os.path.join(self.AGENTS, 'fact-checker.md'),
                  encoding='utf-8') as fh:
            self.assertIn('write `verified_by`', fh.read())


if __name__ == '__main__':
    unittest.main()
