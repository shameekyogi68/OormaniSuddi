"""
Verification is one command, and it fails loud if the name is missing. D76.
=============================================================================
`scripts/verify.py` exists to make the one thing a person must do before
publication (D59) take five seconds instead of hand-editing JSON. This suite
pins the two ways that could quietly stop being true:

  * `--by ""` (or omitted) must never write `verified_by` — an empty string
    reads as "verified" to `Edition.load()`'s own truthiness check just as
    easily as a real name would, so the refusal has to happen here.
  * verifying one story must never touch another story's `verified_by`.
"""

# Enforces D126 — see docs/DECISIONS.md.
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from scripts import verify as v

VERIFY_CLI = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scripts', 'verify.py')


def edition(*headlines):
    return {
        'date': '2026-09-17T08:00:00+05:30',
        'edition_no': 1,
        'stories': [
            {
                'headline': h,
                'category': 'civic',
                'points': ['ಒಂದು ಅಂಶ'],
                'location': 'ಉಡುಪಿ',
                'sources': ['ಉದಯವಾಣಿ'],
                'source_urls': ['https://www.example.com/x'],
                'status': 'developing',
                'is_reel': False,
            }
            for h in headlines
        ],
    }


def quietly(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **kw)


class WithAnEditionFile(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, 'edition.json')

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, data):
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)

    def read(self):
        with open(self.path, encoding='utf-8') as fh:
            return json.load(fh)


class AnEmptyNameIsRefused(WithAnEditionFile):

    def test_verify_refuses_an_empty_by(self):
        self.write(edition('ಒಂದು ಸುದ್ದಿ'))
        rc = quietly(v.cmd_verify, self.path, '', None)
        self.assertEqual(rc, 1)
        self.assertEqual(self.read()['stories'][0].get('verified_by', ''), '')

    def test_verify_refuses_whitespace_only_by(self):
        self.write(edition('ಒಂದು ಸುದ್ದಿ'))
        rc = quietly(v.cmd_verify, self.path, '   ', None)
        self.assertEqual(rc, 1)
        self.assertEqual(self.read()['stories'][0].get('verified_by', ''), '')


class VerifyingOneStoryLeavesOthersAlone(WithAnEditionFile):

    def test_story_2_verified_does_not_touch_story_1(self):
        self.write(edition('ಸುದ್ದಿ ಒಂದು', 'ಸುದ್ದಿ ಎರಡು'))
        rc = quietly(v.cmd_verify, self.path, 'Gautam Paduvari', 2)
        self.assertEqual(rc, 0)
        data = self.read()
        self.assertEqual(data['stories'][0].get('verified_by', ''), '')
        self.assertEqual(data['stories'][1]['verified_by'], 'Gautam Paduvari')
        self.assertIn('verified_at', data['stories'][1])

    def test_all_verifies_every_story_with_the_same_name(self):
        self.write(edition('ಸುದ್ದಿ ಒಂದು', 'ಸುದ್ದಿ ಎರಡು', 'ಸುದ್ದಿ ಮೂರು'))
        rc = quietly(v.cmd_verify, self.path, 'Gautam Paduvari', None)
        self.assertEqual(rc, 0)
        data = self.read()
        self.assertTrue(all(s['verified_by'] == 'Gautam Paduvari'
                            for s in data['stories']))

    def test_an_out_of_range_story_number_is_refused_and_changes_nothing(self):
        self.write(edition('ಸುದ್ದಿ ಒಂದು'))
        rc = quietly(v.cmd_verify, self.path, 'Gautam Paduvari', 5)
        self.assertEqual(rc, 1)
        self.assertEqual(self.read()['stories'][0].get('verified_by', ''), '')


class StatusNeverWrites(WithAnEditionFile):

    def test_status_leaves_the_file_byte_for_byte_unchanged(self):
        self.write(edition('ಸುದ್ದಿ ಒಂದು'))
        with open(self.path, encoding='utf-8') as fh:
            before = fh.read()
        quietly(v.cmd_status, self.path)
        with open(self.path, encoding='utf-8') as fh:
            after = fh.read()
        self.assertEqual(before, after)


class TheCliNormalisesTheByName(WithAnEditionFile):
    """Pinned through the command line, not cmd_verify — the contract is
    what a desk actually types. A name pasted with stray whitespace comes
    from a hurried editor, not a second person; it collapses to one clean
    name so every edition carries the same spelling of the same verifier.
    """

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, VERIFY_CLI, self.path, *args],
            capture_output=True, text=True)

    def test_runs_of_whitespace_in_by_collapse_when_written(self):
        self.write(edition('ಸುದ್ದಿ ಒಂದು'))
        res = self.cli('--all', '--by', '  goutham   paduvari  ')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.read()['stories'][0]['verified_by'],
                         'goutham paduvari')

    def test_a_clean_name_is_written_verbatim(self):
        self.write(edition('ಸುದ್ದಿ ಒಂದು'))
        res = self.cli('--all', '--by', 'Gautam Paduvari')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.read()['stories'][0]['verified_by'],
                         'Gautam Paduvari')


if __name__ == '__main__':
    unittest.main()
