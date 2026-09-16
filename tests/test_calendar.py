"""
The year, and the reviews nobody decides to skip.
=================================================
D69 and D70. Two small suites for two things that are easy to get subtly wrong
and expensive to notice late.

The season wrap is the one worth having a test for: Kambala and Yakshagana run
November to March, and the obvious `from <= today <= to` comparison reports
them as not running for the whole of December, January and February — which is
the entire season.

And the lunar rule is asserted rather than trusted: the calendar must not carry
a day for a festival that moves, because a greeting on the wrong day is worse
than no greeting and a helpful-looking placeholder is exactly how one gets
posted.
"""
from __future__ import annotations

import json
import os
import unittest
from datetime import date

from brand.content import frozen
from brand.tokens import Limits

import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'os_whats_on', os.path.join(ROOT, 'scripts', 'whats_on.py'))
CAL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CAL)


class TheCalendarIsHonestAboutWhatItKnows(unittest.TestCase):

    def test_no_lunar_observance_carries_a_day(self):
        """The whole rule. A month is knowledge; a day would be a guess."""
        for o in CAL.load()['observances']:
            if o['when'] == 'lunar':
                self.assertNotIn(
                    'date', o,
                    f'{o["id"]} is lunar but carries a fixed date. Its day '
                    f'moves every year — recording one invites a greeting on '
                    f'the wrong day, which is worse than none.')
                self.assertIn('month', o)

    def test_every_fixed_observance_parses_as_a_real_date(self):
        for o in CAL.load()['observances']:
            if o['when'] != 'fixed':
                continue
            m, d = (int(x) for x in o['date'].split('-'))
            date(2027, m, d)      # raises on a nonsense date

    def test_a_scaffold_validates_against_the_greeting_contract(self):
        """A scaffold that does not validate wastes the first two minutes of
        every festival, which is when there is least time to spare."""
        from templates.greeting import Greeting
        for o in CAL.load()['observances'][:6]:
            doc = {'kind': 'greeting', 'occasion': o['kn'], 'theme': o['theme'],
                   'salutation': '', 'wish': '', 'blessing': '',
                   'date': '2026-11-01', 'slug': o['id'], 'tags': []}
            Greeting.from_dict(doc)     # raises on an unknown field

    def test_every_theme_named_is_a_theme_that_exists(self):
        from templates.greeting import THEMES
        for o in CAL.load()['observances']:
            self.assertIn(o['theme'], THEMES,
                          f'{o["id"]} asks for theme {o["theme"]!r}')

    def test_the_coastal_entries_a_generic_calendar_would_miss_are_present(self):
        """These are what make it this channel's calendar rather than anybody's."""
        ids = {o['id'] for o in CAL.load()['observances']}
        ids |= {s['id'] for s in CAL.load()['seasons']}
        for needed in ('bisu', 'aati', 'janmashtami', 'kambala', 'yakshagana',
                       'fishing_ban'):
            self.assertIn(needed, ids)


class SeasonsThatWrapTheNewYear(unittest.TestCase):

    def test_kambala_is_running_in_january(self):
        """November to March. The naive comparison says no for three months."""
        with frozen('2027-01-15T09:00:00+05:30'):
            _d, _l, seasons = CAL.upcoming(7)
        running = {s[2]['id'] for s in seasons if s[3] == 'running'}
        self.assertIn('kambala', running)

    def test_kambala_is_not_running_in_july(self):
        with frozen('2027-07-15T09:00:00+05:30'):
            _d, _l, seasons = CAL.upcoming(7)
        running = {s[2]['id'] for s in seasons if s[3] == 'running'}
        self.assertNotIn('kambala', running)

    def test_the_monsoon_is_running_in_july(self):
        with frozen('2027-07-15T09:00:00+05:30'):
            _d, _l, seasons = CAL.upcoming(7)
        running = {s[2]['id'] for s in seasons if s[3] == 'running'}
        self.assertIn('sw_monsoon', running)

    def test_rajyotsava_is_found_from_the_middle_of_the_year(self):
        with frozen('2026-09-16T09:00:00+05:30'):
            dated, _l, _s = CAL.upcoming(60)
        self.assertIn('rajyotsava', {o[2]['id'] for o in dated})

    def test_a_date_already_past_rolls_to_next_year(self):
        d = CAL.next_occurrence('01-26', date(2026, 9, 16))
        self.assertEqual(d, date(2027, 1, 26))


class TheRecurringReviews(unittest.TestCase):

    def test_the_restore_test_is_the_highest_weighted_one(self):
        """A backup nobody has restored is a hope."""
        rs = {r['id']: r for r in CAL.load()['recurring_reviews']}
        self.assertEqual(rs['backup_restore_test']['weight'], 'highest')

    def test_the_law_review_actually_names_the_decisions_to_re_read(self):
        rs = {r['id']: r for r in CAL.load()['recurring_reviews']}
        what = rs['law_review']['what']
        for d in ('D29', 'D49', 'D59'):
            self.assertIn(d, what)

    def test_every_review_has_an_interval_and_an_instruction(self):
        for r in CAL.load()['recurring_reviews']:
            self.assertGreater(int(r['every_days']), 0)
            self.assertGreater(len(r['what']), 40,
                               f'{r["id"]} says too little to act on')


class TheMinimumViableDay(unittest.TestCase):
    """D69: what ships when there are four hours instead of ten."""

    def test_the_daily_path_is_the_four_that_matter(self):
        self.assertEqual(set(Limits.daily_templates),
                         {'carousel', 'story_card', 'broadsheet', 'reel'})

    def test_the_bulletin_is_not_in_the_daily_path(self):
        """It is off by default and is not going to YouTube (Rule 7)."""
        self.assertNotIn('bulletin', Limits.daily_templates)

    def test_minimal_maps_onto_the_same_constant_render_uses(self):
        import render
        self.assertIs(render.Limits, Limits)


if __name__ == '__main__':
    unittest.main()
