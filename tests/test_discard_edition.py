"""
"Stop" undoes a day that never got posted — and refuses one that did.
=======================================================================
`discard_edition.py` is the mirror of `archive_edition.py`: instead of
keeping the editorial record and deleting throwaway media, it deletes
everything about a day that was drafted and then abandoned before anyone
signed it off. The one thing it must never do is quietly delete a day that
was actually published — this suite pins that refusal, and that the
evergreen stock library is never in its blast radius regardless.

Runs against a fake date under the real project paths (never a real
calendar day) so the deletion logic exercises the actual ROOT-relative
paths the script uses, with tearDown guaranteeing cleanup either way.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import unittest

from scripts import discard_edition as de

ROOT = de.ROOT
FAKE_DATE = '2099-12-31'


def quietly(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **kw)


def run(*args):
    import sys
    old_argv = sys.argv
    sys.argv = ['discard_edition.py', *args]
    try:
        return quietly(de.main)
    finally:
        sys.argv = old_argv


class WithAFakeDay(unittest.TestCase):
    """Everything scoped to FAKE_DATE, never a real calendar day, and always
    cleaned up — the paths this test touches are exactly the ones the
    script would touch for a real one."""

    def setUp(self):
        self.edition = os.path.join(ROOT, 'editions', f'{FAKE_DATE}.json')
        self.checklist = os.path.join(ROOT, 'inbox', f'checklist_{FAKE_DATE}.md')
        self.out = os.path.join(ROOT, 'out', FAKE_DATE)
        self.daily = os.path.join(ROOT, 'assets', 'daily', FAKE_DATE)
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        for p in (self.edition, self.checklist):
            if os.path.exists(p):
                os.remove(p)
        for d in (self.out, self.daily):
            if os.path.isdir(d):
                shutil.rmtree(d)

    def make_edition(self):
        os.makedirs(os.path.dirname(self.edition), exist_ok=True)
        with open(self.edition, 'w', encoding='utf-8') as fh:
            json.dump({'date': f'{FAKE_DATE}T08:00:00+05:30', 'stories': []},
                     fh)

    def make_out(self, *, signed=False):
        os.makedirs(self.out, exist_ok=True)
        with open(os.path.join(self.out, 'placeholder.jpg'), 'w') as fh:
            fh.write('x')
        if signed:
            with open(os.path.join(self.out, 'SIGNOFF.json'), 'w') as fh:
                json.dump({'taste': 'Gautam', 'culture': 'Gautam',
                          'news': 'Gautam'}, fh)

    def make_daily_assets(self, *names):
        os.makedirs(self.daily, exist_ok=True)
        for n in names:
            with open(os.path.join(self.daily, n), 'w') as fh:
                fh.write('x')


class AnAbandonedDayIsFullyUndone(WithAFakeDay):

    def test_edition_checklist_and_out_are_all_removed(self):
        self.make_edition()
        os.makedirs(os.path.dirname(self.checklist), exist_ok=True)
        with open(self.checklist, 'w', encoding='utf-8') as fh:
            fh.write('# checklist')
        self.make_out(signed=False)

        rc = run(FAKE_DATE)

        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.edition))
        self.assertFalse(os.path.exists(self.checklist))
        self.assertFalse(os.path.isdir(self.out))

    def test_nothing_to_discard_is_not_an_error(self):
        rc = run(FAKE_DATE)
        self.assertEqual(rc, 0)


class ASignedOffDayIsNeverTouched(WithAFakeDay):

    def test_a_published_day_is_refused_and_left_intact(self):
        """The one case this script must never silently do the wrong thing
        on: a day that actually went out under someone's name."""
        self.make_edition()
        self.make_out(signed=True)

        rc = run(FAKE_DATE)

        self.assertEqual(rc, 1)
        self.assertTrue(os.path.exists(self.edition),
                        'a signed-off edition must survive a discard attempt')
        self.assertTrue(os.path.isdir(self.out),
                        'a signed-off render must survive a discard attempt')


class DailyAssetsNeedTheForceFlag(WithAFakeDay):

    def test_daily_assets_survive_without_force_assets(self):
        self.make_daily_assets('scene_1.jpg', 'scene_2.jpg')
        rc = run(FAKE_DATE)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isdir(self.daily))
        self.assertEqual(sorted(os.listdir(self.daily)),
                         ['scene_1.jpg', 'scene_2.jpg'])

    def test_daily_assets_are_removed_with_force_assets(self):
        self.make_daily_assets('scene_1.jpg')
        rc = run(FAKE_DATE, '--force-assets')
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.isdir(self.daily))

    def test_the_evergreen_stock_library_is_never_touched(self):
        stock = os.path.join(ROOT, 'assets', 'stock')
        before = set(os.listdir(stock)) if os.path.isdir(stock) else set()
        self.make_edition()
        self.make_daily_assets('scene_1.jpg')
        run(FAKE_DATE, '--force-assets')
        after = set(os.listdir(stock)) if os.path.isdir(stock) else set()
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
