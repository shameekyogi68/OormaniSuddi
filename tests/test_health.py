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

    def test_missing_fonttools_needs_attention(self):
        # D114: without it typo._coverage fails open and the empty-box guard
        # is silently off — which is how CI was red for three weeks.
        import importlib.util
        real = importlib.util.find_spec
        with mock.patch.object(importlib.util, 'find_spec',
                               lambda n, *a: None if n == 'fontTools' else real(n, *a)):
            lines = health.check_tools()
        self.assertTrue(any(l.startswith(health.BAD) and 'fontTools' in l for l in lines))

    def test_fonttools_is_a_listed_requirement(self):
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'requirements.txt'), encoding='utf-8') as fh:
            reqs = fh.read().lower()
        self.assertIn('fonttools', reqs)

    def test_a_missing_latin_face_is_worth_a_look(self):
        from brand import tokens
        with mock.patch.dict(tokens.FONTS, {'latin': '/nowhere/SFNS.ttf'}):
            lines = health.check_tools()
        self.assertTrue(any(l.startswith(health.WARN) and 'SFNS' in l for l in lines))

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
