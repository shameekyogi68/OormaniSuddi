"""
Health says when the Mac itself is the problem.
===============================================
D113. A year left alone, the likeliest failures are not in this repo: the disk
fills, a system update removes ffmpeg, a Pillow upgrade arrives without raqm
and every Kannada conjunct renders broken. `scripts/health.py` names each.
"""
from __future__ import annotations

import shutil
import unittest
from collections import namedtuple
from unittest import mock

from brand.tokens import Limits
from scripts import health

Usage = namedtuple('Usage', 'total used free')


def disk(gb: float):
    return mock.patch.object(health.shutil, 'disk_usage',
                             lambda _p: Usage(0, 0, gb * 1e9))


class TheDiskIsWatched(unittest.TestCase):

    def test_plenty_of_room_is_fine(self):
        with disk(Limits.disk_warn_gb + 50):
            self.assertTrue(health.check_disk()[0].startswith(health.OK))

    def test_getting_full_is_worth_a_look(self):
        with disk((Limits.disk_warn_gb + Limits.disk_min_gb) / 2):
            self.assertTrue(health.check_disk()[0].startswith(health.WARN))

    def test_nearly_full_needs_attention(self):
        with disk(Limits.disk_min_gb / 2):
            self.assertTrue(health.check_disk()[0].startswith(health.BAD))


class TheRenderToolsAreWatched(unittest.TestCase):

    def test_missing_ffmpeg_needs_attention(self):
        with mock.patch.object(health.shutil, 'which', lambda _t: None):
            lines = health.check_tools()
        self.assertTrue(any(l.startswith(health.BAD) and 'ffmpeg' in l for l in lines))

    def test_pillow_without_raqm_needs_attention(self):
        from PIL import features
        with mock.patch.object(features, 'check_feature', lambda _f: False):
            lines = health.check_tools()
        self.assertTrue(any(l.startswith(health.BAD) and 'raqm' in l for l in lines))

    def test_the_tests_it_runs_are_the_fast_suites(self):
        calls = []

        def fake(cmd, **_k):
            calls.append(cmd)
            return mock.Mock(returncode=0, stdout='', stderr='OK')
        with mock.patch.object(health.subprocess, 'run', fake):
            health.check_tests()
        suites = calls[0]
        self.assertIn('tests.test_contract', suites)
        self.assertIn('tests.test_legal_corpus', suites)
        self.assertNotIn('tests.test_golden', suites)


if __name__ == '__main__':
    unittest.main()
