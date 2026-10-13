"""
whats_on.py — the calendar, the reviews, the scaffold. D92, D113.
=================================================================
Not calendar.py, and this suite is part of why: the name shadows the stdlib
for anything run from scripts/. These tests pin the desk-facing contract
against a temp calendar and the frozen clock: scaffolds validate and never
overwrite, review marks land in the state ledger, and the window view
distinguishes dated observances from lunar months.

The real observance list is data, not logic — it lives in
editions/greetings/calendar.json and is exercised here through a minimal
fixture so a festival edit can never break the suite.
"""

# Enforces D125 — see docs/DECISIONS.md.
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from scripts import whats_on
from brand.content import frozen

CAL = {
    'observances': [
        {'id': 'deepavali', 'kn': 'ದೀಪಾವಳಿ', 'en': 'Deepavali',
         'when': 'fixed', 'date': '11-08', 'month': 11, 'theme': 'sacred lights',
         'note': '', 'weight': 'high'},
        {'id': 'ugadi', 'kn': 'ಉಗಾದಿ', 'en': 'Ugadi',
         # The fixture month is chosen to fall inside the test window, not to
         # match the real festival — the suite tests the logic, not the data.
         'when': 'lunar', 'month': 11, 'theme': 'harvest',
         'note': '', 'weight': 'medium'},
    ],
    'seasons': [],
    'recurring_reviews': [
        {'id': 'backup-restore', 'every_days': 30, 'weight': 'highest',
         'what': 'Restore one archived day from .backups and read it back.'},
    ],
}


def quietly(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = fn(*a, **kw)
    return rc, out.getvalue()


def cli(argv: list[str]) -> tuple[int, str]:
    """These scripts parse sys.argv directly (no argv parameter), so the
    tests drive them the way a desk does: by setting the arguments."""
    out = io.StringIO()
    with mock.patch('sys.argv', ['tool'] + argv), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = whats_on.main()
    return rc, out.getvalue()


class AgainstATempCalendar(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cal = os.path.join(self.tmp.name, 'calendar.json')
        with open(self.cal, 'w', encoding='utf-8') as fh:
            json.dump(CAL, fh, ensure_ascii=False)
        self.state = os.path.join(self.tmp.name, 'calendar_state.json')
        # ROOT too: --scaffold writes editions/greetings/<id>.json under it,
        # and the real repo must never be the test's scratch pad. (The real
        # greetings dir exists on disk; a scratch root needs it made.)
        os.makedirs(os.path.join(self.tmp.name, 'editions', 'greetings'))
        p = mock.patch.multiple(whats_on, CAL=self.cal, STATE=self.state,
                                ROOT=self.tmp.name)
        p.start()
        self.addCleanup(p.stop)
        # A fixed "today" inside the frozen-clock pattern the codebase uses.
        self._ctx = frozen('2026-10-13T09:00:00+05:30')
        self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)

    def test_scaffold_writes_a_valid_greeting_shape(self):
        rc, out = cli(['--scaffold', 'deepavali'])
        self.assertEqual(rc, 0, out)
        out_path = os.path.join(self.tmp.name, 'editions', 'greetings',
                                'deepavali.json')
        with open(out_path, encoding='utf-8') as fh:
            doc = json.load(fh)
        self.assertEqual(doc['kind'], 'greeting')
        self.assertEqual(doc['date'], '2026-11-08')

    def test_scaffold_never_overwrites_an_existing_greeting(self):
        cli(['--scaffold', 'deepavali'])
        out_path = os.path.join(self.tmp.name, 'editions', 'greetings',
                                'deepavali.json')
        before = open(out_path, encoding='utf-8').read()
        rc, out = cli(['--scaffold', 'deepavali'])
        self.assertEqual(rc, 1)
        self.assertIn('not overwriting', out)
        self.assertEqual(open(out_path, encoding='utf-8').read(), before)

    def test_scaffold_refuses_an_unknown_observance(self):
        rc, _ = cli(['--scaffold', 'not-a-festival'])
        self.assertEqual(rc, 1)

    def test_scaffold_marks_a_lunar_date_as_unconfirmed(self):
        rc, out = cli(['--scaffold', 'ugadi'])
        self.assertEqual(rc, 0, out)
        out_path = os.path.join(self.tmp.name, 'editions', 'greetings',
                                'ugadi.json')
        with open(out_path, encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['date'], 'CONFIRM-FROM-PANCHANGA')

    def test_marking_a_review_done_lands_in_the_state_ledger(self):
        rc, _ = cli(['--reviews', '--done', 'backup-restore'])
        self.assertEqual(rc, 0)
        with open(self.state, encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['backup-restore'], '2026-10-13')

    def test_marking_an_unknown_review_is_an_error(self):
        rc, _ = cli(['--reviews', '--done', 'nope'])
        self.assertEqual(rc, 1)

    def test_the_window_names_dated_observances_safely_schedulable(self):
        rc, out = cli(['--days', '60'])
        self.assertEqual(rc, 0, out)
        self.assertIn('DATED', out)
        self.assertIn('ದೀಪಾವಳಿ', out)
        self.assertIn('LUNAR', out)          # Ugadi's month surfaces, day never


if __name__ == '__main__':
    unittest.main()
