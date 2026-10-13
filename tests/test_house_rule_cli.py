"""
house_rule.py at the command line. D73.
========================================
A house rule applies from the moment it is added, every run, until retired,
and it cannot switch a check off. These tests pin the CLI wiring: add →
list → retire round-trips against a temp ledger, `where` routes a request
to one of the four places changes belong (and refuses a waiver), and a
check-switching rule never enters the ledger.

`brand.house` owns the ledger's logic (tests/test_house.py); this suite owns
what a desk actually types.
"""

# Enforces D125, D73 — see docs/DECISIONS.md.
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from scripts import house_rule as hr
from brand import house


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
        rc = hr.main()
    return rc, out.getvalue()


class CliAgainstATempLedger(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = os.path.join(self.tmp.name, 'HOUSE_RULES.json')
        self.rendered = os.path.join(self.tmp.name, 'HOUSE_RULES.md')
        # The CLI calls brand.house's module-level paths — patch where it reads.
        p = mock.patch.multiple(house, LEDGER=self.ledger, RENDERED=self.rendered)
        p.start()
        self.addCleanup(p.stop)

    def test_add_list_retire_round_trip(self):
        rc, out = cli(['add', 'ಗಣೇಶ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ',
                                    '--scope', 'picture',
                                    '--why', 'organisers reshare when credited',
                                    '--by', 'Gautam'])
        self.assertEqual(rc, 0, out)
        with open(self.ledger, encoding='utf-8') as fh:
            live = [r for r in json.load(fh)['rules'] if not r.get('retired')]
        self.assertEqual(len(live), 1)
        rule_id = live[0]['id']

        rc, out = cli(['list'])
        self.assertEqual(rc, 0)
        self.assertIn('ಸಂಘಟಕರ ಹೆಸರು', out)

        rc, out = cli(['retire', rule_id, '--why', 'season over'])
        self.assertEqual(rc, 0, out)
        rc, out = cli(['list'])
        self.assertNotIn('ಸಂಘಟಕರ ಹೆಸರು', out)

    def test_retiring_an_unknown_id_is_an_error(self):
        rc, _ = cli(['retire', '1999-01-01-01'])
        self.assertEqual(rc, 1)

    def test_add_refuses_a_rule_that_switches_a_check_off(self):
        with mock.patch.object(house, 'looks_like_a_waiver', return_value='waive'):
            rc, out = cli(['add', 'waive the PUB-10 gate today',
                                        '--scope', 'gate'])
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self.ledger),
                         'a refused rule must not reach the ledger')


class WhereRoutesTheRequest(unittest.TestCase):

    def test_a_number_belongs_in_limits_not_here(self):
        rc, out = cli(['where', 'reels should be 30 seconds'])
        self.assertEqual(rc, 0)
        self.assertIn('Limits', out)

    def test_a_legal_rule_belongs_in_content_code(self):
        rc, out = cli(['where', 'headlines must not assert guilt'])
        self.assertEqual(rc, 0)
        self.assertIn('content', out)

    def test_a_place_belongs_in_place_tags(self):
        rc, out = cli(['where', 'the hashtag for Kundapura'])
        self.assertEqual(rc, 0)
        self.assertIn('PLACE_TAGS', out)

    def test_a_waiver_is_refused_with_the_reason(self):
        with mock.patch.object(house, 'looks_like_a_waiver', return_value='waive'):
            rc, out = cli(['where', 'waive the fact check for this'])
        self.assertEqual(rc, 1)
        self.assertIn('cannot switch a check off', out)


if __name__ == '__main__':
    unittest.main()
