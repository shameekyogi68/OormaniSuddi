"""
The three judgement seats, at the command line. D62, D95, D108.
================================================================
`scripts/sign_off.py` is the only thing that fills the seats
`brand/review.py` deliberately leaves empty, and it is a person-shaped
hole: a name can be asked about afterwards and a score out of ten cannot.
This suite pins the four ways that could quietly stop being true:

  * no APPROVAL.md → nothing to sign; the mechanical checks never passed.
  * an inspector has not read THIS package → sign anyway and a broken frame
    ships with a name on it (D95).
  * a named person signs → SIGNOFF.json carries every seat and APPROVAL.md
    is re-stamped so the folder never disagrees with itself.
  * the package changed after signing → the old signature no longer counts
    (D108); signing again writes the new fingerprint.

The gap check is mocked at `brand.dispatch.inspection_gaps` — the seam the
script itself imports — because the real one reads the live inbox receipts.
"""

# Enforces D125 — see docs/DECISIONS.md.
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from scripts import sign_off as so
from brand.review import (SIGN_FILE, is_signed, package_fingerprint,
                          signed_seats, signoff_state)


def quietly(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = fn(*a, **kw)
    return rc, out.getvalue()


class WithAPackage(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.outdir = os.path.join(self._tmp.name, 'out-2026-10-13')
        os.makedirs(os.path.join(self.outdir, '_review'))
        # The mechanical green signal, with the block _restamp() rewrites.
        with open(os.path.join(self.outdir, 'APPROVAL.md'), 'w',
                  encoding='utf-8') as fh:
            fh.write('# ಮುಖ್ಯ ಸಂಪಾದಕರ ಪರಿಶೀಲನೆ\n\n## Human judgement\n\n'
                     '🟡 mechanically clean, not yet signed\n')
        # Something a person posts: a posted file feeds the fingerprint.
        with open(os.path.join(self.outdir, 'reel_01.mp4'), 'wb') as fh:
            fh.write(b'fake-but-bytes')
        with open(os.path.join(self.outdir, '_review', 'frame.jpg'), 'wb') as fh:
            fh.write(b'evidence')
        self._gaps = mock.patch('brand.dispatch.inspection_gaps',
                                return_value=[])
        self._gaps.start()
        self.addCleanup(self._gaps.stop)

    def run_cli(self, *argv):
        with mock.patch.object(sys, 'argv', ['sign_off.py', *argv]):
            return quietly(so.main)


class NothingToSignYet(WithAPackage):

    def test_no_approval_md_is_refused(self):
        os.remove(os.path.join(self.outdir, 'APPROVAL.md'))
        rc, out = self.run_cli(self.outdir, '--by', 'Gautam Paduvari')
        self.assertEqual(rc, 1)
        self.assertIn('does not exist', out)
        self.assertFalse(os.path.exists(os.path.join(self.outdir, SIGN_FILE)))

    def test_unread_package_is_refused(self):
        """D95: signing first and looking later is how a broken frame ships
        with a name on it."""
        self._gaps.stop()
        with mock.patch('brand.dispatch.inspection_gaps',
                        return_value=['package-inspector: render not read']):
            rc, out = self.run_cli(self.outdir, '--by', 'Gautam Paduvari')
        self.assertEqual(rc, 1)
        self.assertIn('not yet', out)
        self.assertFalse(os.path.exists(os.path.join(self.outdir, SIGN_FILE)))

    def test_no_name_is_refused_and_signs_nothing(self):
        rc, _out = self.run_cli(self.outdir, '--by', '')
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(self.outdir, SIGN_FILE)))


class ANamedPersonSigns(WithAPackage):

    def test_signing_writes_every_seat_and_restamps_approval(self):
        rc, out = self.run_cli(self.outdir, '--by', 'Gautam Paduvari')
        self.assertEqual(rc, 0)
        self.assertIn('signed by Gautam Paduvari', out)
        state = signoff_state(self.outdir)
        for seat in ('taste', 'culture', 'news'):
            self.assertEqual(state.get(seat), 'Gautam Paduvari')
        self.assertTrue(is_signed(self.outdir))
        with open(os.path.join(self.outdir, 'APPROVAL.md'),
                  encoding='utf-8') as fh:
            self.assertIn('Cleared to publish', fh.read())

    def test_one_seat_leaves_the_other_two_open(self):
        rc, _out = self.run_cli(self.outdir, '--by', 'Gautam Paduvari',
                                '--seat', 'news')
        self.assertEqual(rc, 0)
        self.assertEqual(signed_seats(self.outdir), {'news': 'Gautam Paduvari'})
        self.assertFalse(is_signed(self.outdir))


class ThePackageChangedUnderTheSignature(WithAPackage):

    def test_a_changed_package_invalidates_the_signature(self):
        """D108: a re-render after signing must not keep the old clearance."""
        rc, _out = self.run_cli(self.outdir, '--by', 'Gautam Paduvari')
        self.assertEqual(rc, 0)
        old_fp = package_fingerprint(self.outdir)
        # The render changes: the posted bytes are not what was signed.
        with open(os.path.join(self.outdir, 'reel_01.mp4'), 'ab') as fh:
            fh.write(b'-re-rendered')
        self.assertNotEqual(package_fingerprint(self.outdir), old_fp)
        self.assertEqual(signed_seats(self.outdir), {})
        self.assertFalse(is_signed(self.outdir))
        rc, out = self.run_cli(self.outdir, '--status')
        self.assertEqual(rc, 0)
        self.assertIn('signed earlier for a different render', out)

    def test_signing_again_covers_the_new_package(self):
        rc, _out = self.run_cli(self.outdir, '--by', 'Gautam Paduvari')
        self.assertEqual(rc, 0)
        with open(os.path.join(self.outdir, 'reel_01.mp4'), 'ab') as fh:
            fh.write(b'-re-rendered')
        rc, out = self.run_cli(self.outdir, '--by', 'Shameek')
        self.assertEqual(rc, 0)
        self.assertTrue(is_signed(self.outdir))
        state = signoff_state(self.outdir)
        self.assertEqual(state['package'], package_fingerprint(self.outdir))
        with open(os.path.join(self.outdir, SIGN_FILE), encoding='utf-8') as fh:
            saved = json.load(fh)
        self.assertNotEqual(saved.get('package'), None)


if __name__ == '__main__':
    unittest.main()
