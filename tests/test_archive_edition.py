"""Stop keeps the files a phone posts from, and cannot leave the repo.

D106. `archive_edition.py` deletes the heavy renders. The town forwards,
the Facebook posts and REACH.md are the circulation record — they used to
be deleted with the mp4s. A date that is not YYYY-MM-DD is refused before
any directory is created.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import unittest

from scripts import archive_edition as ae
from scripts.daily_flow import sign_off_hint

ROOT = ae.ROOT
FAKE_DATE = '2099-11-30'


def quietly(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **kw)


def run(*args):
    import sys
    old_argv = sys.argv
    sys.argv = ['archive_edition.py', *args]
    try:
        return quietly(ae.main)
    finally:
        sys.argv = old_argv


class ArchiveKeepsTheCirculationFiles(unittest.TestCase):

    def setUp(self):
        self.out = os.path.join(ROOT, 'out', FAKE_DATE)
        self.dest = os.path.join(ROOT, 'archive', FAKE_DATE)
        self._cleanup()
        os.makedirs(self.out, exist_ok=True)
        for name in ('facebook_group_1.txt', 'forward_kundapura.txt',
                     'REACH.md', 'saara_caption.txt', 'MASTER_COPY.md',
                     'throwaway.mp4'):
            with open(os.path.join(self.out, name), 'w', encoding='utf-8') as fh:
                fh.write(name + '\n')

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        for d in (self.out, self.dest):
            if os.path.isdir(d):
                shutil.rmtree(d)

    def test_the_phone_files_survive_and_the_render_does_not(self):
        rc = run(FAKE_DATE)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.isdir(self.out))
        kept = set(os.listdir(self.dest))
        self.assertIn('facebook_group_1.txt', kept)
        self.assertIn('forward_kundapura.txt', kept)
        self.assertIn('REACH.md', kept)
        self.assertIn('saara_caption.txt', kept)
        self.assertIn('MASTER_COPY.md', kept)
        self.assertNotIn('throwaway.mp4', kept)

    def test_a_path_is_refused_before_anything_is_created(self):
        parent = os.path.dirname(ROOT)
        marker = os.path.join(parent, 'out')
        existed = os.path.isdir(marker)
        rc = run('../not-a-day')
        self.assertEqual(rc, 2)
        self.assertTrue(os.path.isdir(self.out))
        if not existed:
            self.assertFalse(os.path.isdir(marker))

    def test_the_sign_off_hint_does_not_invent_a_name(self):
        hint = sign_off_hint(FAKE_DATE, None)
        self.assertIn('<name>', hint)
        self.assertNotIn('Editor', hint)
        self.assertIn('Gautam', sign_off_hint(FAKE_DATE, 'Gautam'))


if __name__ == '__main__':
    unittest.main()
