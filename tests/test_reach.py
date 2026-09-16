"""
Reach, as arithmetic rather than hope.
======================================
D72. The production system was good and the distribution system was a posting
schedule. These assert the four things the reach layer actually claims.

The one to read first is `test_the_place_registry_is_not_duplicated`. Every
place name in this project lives in `copy.PLACE_TAGS` and nowhere else — a
second list of towns inside the reach module would drift from the first within
a month, and then the hashtags, the forwards and the relevance score would
disagree about where Byndoor is. Same rule as `tokens.Limits` for numbers.
"""
from __future__ import annotations

import unittest

from brand import reach
from brand.content import Story, Photo, Edition, now, OWN_REPORTING
from brand.copy import PLACE_TAGS, FOLD, instagram_caption, taluk_forwards
from brand.tokens import Limits


def story(**kw) -> Story:
    base = dict(
        headline='ಪರೀಕ್ಷಾ ಶೀರ್ಷಿಕೆ', category='civic', location='ಬೈಂದೂರು',
        sources=[OWN_REPORTING], verified_by='Gautam Paduvari',
        photo=Photo('x.jpg', nature='representative',
                    credit='ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own'))
    base.update(kw)
    return Story(**base)


class ThePlaceRegistryIsTheOnlyOne(unittest.TestCase):

    def test_the_place_registry_is_not_duplicated(self):
        """reach.py must own no place names of its own."""
        import inspect
        src = inspect.getsource(reach)
        for kn in list(PLACE_TAGS)[:12]:
            self.assertNotIn(
                kn, src,
                f'{kn} is hard-coded in brand/reach.py. Places live in '
                f'copy.PLACE_TAGS and nowhere else — two lists drift, and then '
                f'the hashtags and the forwards disagree about where it is.')

    def test_it_resolves_places_through_the_existing_registry(self):
        self.assertEqual(reach.place_of(story(location='ಬೈಂದೂರು')), 'ಬೈಂದೂರು')
        self.assertEqual(reach.place_of(story(location='ಉಡುಪಿ ಜಿಲ್ಲೆ')), 'ಉಡುಪಿ')

    def test_a_story_with_no_location_has_no_place(self):
        self.assertEqual(reach.place_of(story(location='')), '')


class LocalRelevance(unittest.TestCase):

    def test_a_placed_actionable_weather_story_scores_high(self):
        r = reach.relevance(story(
            category='weather', location='ಬೈಂದೂರು',
            takeaway='ತುರ್ತು ಸಹಾಯಕ್ಕೆ 1077 ಸಂಪರ್ಕಿಸಿ.'))
        self.assertEqual(r.band, 'high')
        self.assertTrue(r.actionable)

    def test_a_story_with_no_place_is_penalised_and_says_why(self):
        placed = reach.relevance(story(category='weather'))
        unplaced = reach.relevance(story(category='weather', location=''))
        self.assertLess(unplaced.score, placed.score)
        self.assertTrue(any('NO PLACE' in w for w in unplaced.why))

    def test_actionable_copy_beats_the_same_story_without_it(self):
        plain = reach.relevance(story(category='civic'))
        useful = reach.relevance(story(
            category='civic', takeaway='ಅರ್ಜಿ ಸಲ್ಲಿಸಲು ಕೊನೆಯ ದಿನ ಆಗಸ್ಟ್ 31.'))
        self.assertGreater(useful.score, plain.score)

    def test_it_is_deterministic(self):
        """This feeds a format decision. One that changes between runs is a bug."""
        s = story(category='weather', takeaway='1077 ಸಂಪರ್ಕಿಸಿ')
        self.assertEqual(reach.relevance(s).score, reach.relevance(s).score)

    def test_crime_does_not_outrank_civic_on_usefulness(self):
        """Crime wins every engagement signal. This scores usefulness, not
        attention — otherwise the reach layer becomes the thing D68 caps."""
        crime = reach.relevance(story(category='crime',
                                      headline='ಕಳವು ಆರೋಪ: ಬಂಧನ'))
        civic = reach.relevance(story(
            category='civic', takeaway='ಕೊನೆಯ ದಿನ ಆಗಸ್ಟ್ 31, ಅರ್ಜಿ ಸಲ್ಲಿಸಿ.'))
        self.assertGreater(civic.score, crime.score)


class FormatFollowsTheStory(unittest.TestCase):

    def test_a_government_notice_is_a_card_not_a_reel(self):
        ok, why = reach.should_be_reel(story(category='civic'))
        self.assertFalse(ok)
        self.assertIn('card', why)

    def test_weather_earns_a_reel(self):
        ok, _why = reach.should_be_reel(story(
            category='weather', takeaway='1077 ಸಂಪರ್ಕಿಸಿ'))
        self.assertTrue(ok)

    def test_an_obituary_gets_no_reel_and_no_hook(self):
        """Dignity is a format decision too."""
        self.assertEqual(reach.formats_for(story(category='obituary')), ())

    def test_a_story_with_no_place_never_earns_a_reel(self):
        ok, why = reach.should_be_reel(story(category='weather', location=''))
        self.assertFalse(ok)
        self.assertIn('place', why)


class TheFold(unittest.TestCase):

    def test_the_town_name_lands_before_the_fold(self):
        s = story(category='weather', location='ಬೈಂದೂರು',
                  headline='ಭಾರಿ ಮಳೆ ಸಾಧ್ಯತೆ, ಮೀನುಗಾರರಿಗೆ ಎಚ್ಚರಿಕೆ')
        ok, why = reach.place_before_fold(s, instagram_caption(s))
        self.assertTrue(ok, why)

    def test_a_town_past_the_fold_is_reported_with_its_position(self):
        s = story(location='ಬೈಂದೂರು')
        caption = 'x' * (FOLD + 40) + ' ಬೈಂದೂರು'
        ok, why = reach.place_before_fold(s, caption)
        self.assertFalse(ok)
        self.assertIn(str(FOLD), why)

    def test_no_place_at_all_is_distinguished_from_a_late_place(self):
        ok, why = reach.place_before_fold(story(location=''), 'anything')
        self.assertFalse(ok)
        self.assertIn('no place', why)


class TalukForwards(unittest.TestCase):
    """The change every reviewer converged on. People forward what is theirs;
    nobody forwards a seven-taluk digest, because it belongs in no group."""

    def _edition(self):
        return Edition(stories=[
            story(headline='ಬೈಂದೂರಿನಲ್ಲಿ ರಸ್ತೆ ಬಂದ್', location='ಬೈಂದೂರು'),
            story(headline='ಕುಂದಾಪುರದಲ್ಲಿ ಶಿಬಿರ', location='ಕುಂದಾಪುರ'),
            story(headline='ಬೈಂದೂರಿನಲ್ಲಿ ಪರೀಕ್ಷೆ', location='ಬೈಂದೂರು'),
        ], date=now(), edition_no=1)

    def test_one_forward_per_town_covered(self):
        f = taluk_forwards(self._edition())
        self.assertEqual(set(f), {'ಬೈಂದೂರು', 'ಕುಂದಾಪುರ'})

    def test_each_forward_opens_on_its_own_town(self):
        f = taluk_forwards(self._edition())
        for place, text in f.items():
            self.assertTrue(text.startswith(f'*{place}'),
                            f'{place} forward does not open on {place}')

    def test_a_forward_carries_only_its_own_towns_stories(self):
        f = taluk_forwards(self._edition())
        self.assertIn('ರಸ್ತೆ ಬಂದ್', f['ಬೈಂದೂರು'])
        self.assertNotIn('ಶಿಬಿರ', f['ಬೈಂದೂರು'])

    def test_every_forward_keeps_the_sourcing_and_the_grievance_route(self):
        """A re-cut for a town is still a published thing."""
        from brand.tokens import Brand
        for text in taluk_forwards(self._edition()).values():
            self.assertIn('ಮೂಲ:', text)
            self.assertIn(Brand.handle, text)
            self.assertIn(Brand.grievance_officer, text)

    def test_an_edition_with_no_places_yields_no_forwards(self):
        ed = Edition(stories=[story(location='')], date=now(), edition_no=1)
        self.assertEqual(taluk_forwards(ed), {})


class TheDayIsSized(unittest.TestCase):

    def test_the_reel_target_is_two(self):
        """Six posts a day does not reach six times as many people: each goes
        to a small test slice, and splitting the audience makes all of them
        look average."""
        self.assertEqual(Limits.reels_per_day_target, 2)

    def test_the_plan_counts_what_is_earned_against_what_is_marked(self):
        ed = Edition(stories=[
            story(category='weather', takeaway='1077 ಸಂಪರ್ಕಿಸಿ', is_reel=True),
            story(category='civic', is_reel=True),
        ], date=now(), edition_no=1)
        p = reach.plan(ed)
        self.assertEqual(p['reels_marked'], 2)
        self.assertEqual(p['reels_earned'], 1)

    def test_the_report_names_a_story_marked_reel_that_is_not_one(self):
        ed = Edition(stories=[story(category='civic', is_reel=True)],
                     date=now(), edition_no=1)
        self.assertIn('marked `is_reel`', reach.report(ed))


class Continuity(unittest.TestCase):

    def test_a_follow_up_says_so_in_the_caption(self):
        s = story(follows_up='2026-09-14')
        self.assertIn('ಮುಂದುವರಿಕೆ', instagram_caption(s))

    def test_a_story_that_follows_nothing_says_nothing(self):
        self.assertNotIn('ಮುಂದುವರಿಕೆ', instagram_caption(story()))


if __name__ == '__main__':
    unittest.main()
