"""
metrics.py against a scratch database.
======================================
The numbers desk types what the app shows, once a week. These tests pin the
CLI contract: a recording lands in SQLite (and re-recording the same asset
updates rather than duplicates), the report survives the pre-revenue case
with grace, and nothing writes outside the temp root the test controls.
"""

# Enforces D125 — see docs/DECISIONS.md.
from __future__ import annotations

import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from scripts import metrics


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
        rc = metrics.main()
    return rc, out.getvalue()


ADD = ['add', '--date', '2026-10-06', '--asset', 'reel_01.mp4',
       '--format', 'roundup', '--category', 'civic', '--at', '18:30',
       '--views', '412', '--reach', '380', '--saves', '9', '--shares', '14',
       '--watch', '62']


class AgainstATempDatabase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, 'metrics.db')
        p = mock.patch.multiple(metrics, DB=self.db,
                                ROOT=self.tmp.name)
        p.start()
        self.addCleanup(p.stop)

    def rows(self):
        con = sqlite3.connect(self.db)
        try:
            return con.execute('SELECT * FROM posts').fetchall()
        finally:
            con.close()

    def test_a_recording_lands_once(self):
        rc, out = cli(ADD)
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.rows()), 1)
        self.assertIn('recorded', out)

    def test_recording_the_same_asset_again_updates_not_duplicates(self):
        cli(ADD)
        again = [a for a in ADD]
        again[again.index('412')] = '500'       # same post, corrected views
        rc, _ = cli(again)
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.rows()), 1)
        con = sqlite3.connect(self.db)
        try:
            views = con.execute('SELECT views FROM posts').fetchone()[0]
        finally:
            con.close()
        self.assertEqual(views, 500)

    def test_report_with_no_posts_says_how_to_start(self):
        rc, out = cli(['report'])
        self.assertEqual(rc, 0, out)
        self.assertIn('No posts logged yet', out)

    def test_report_with_one_post_hedges_until_twenty(self):
        cli(ADD)
        rc, out = cli(['report'])
        self.assertEqual(rc, 0, out)
        self.assertIn('astrology', out)
        report = os.path.join(self.tmp.name, 'archive', 'metrics_report.md')
        self.assertTrue(os.path.exists(report))
        with open(report, encoding='utf-8') as fh:
            self.assertIn('Local penetration', fh.read())


if __name__ == '__main__':
    unittest.main()
