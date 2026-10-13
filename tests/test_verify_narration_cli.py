"""
verify_narration.py — the round trip, without ears.
====================================================
Whisper is optional on purpose: an absent engine must not fail a morning.
These tests therefore pin the parts that are pure — the word/stem
comparison, the script extraction from *_copy.json files, the per-file
verdict — by mocking `transcribe`, and pin the no-engine morning at the CLI.
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

from scripts import verify_narration as vn


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
        rc = vn.main()
    return rc, out.getvalue()


SCRIPT = ('ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಇಂದು ಮತ್ತು ನಾಳೆ ಭಾರೀ ಮಳೆ ಸಾಧ್ಯತೆ '
          'ಹವಾಮಾನ ಇಲಾಖೆ ಮೂಲಕ ತಿಳಿದುಬಂದಿದೆ')


class CompareIsAPureFunction(unittest.TestCase):

    def test_identical_text_loses_nothing(self):
        res = vn.compare(SCRIPT, SCRIPT)
        self.assertEqual(res['similarity'], 1.0)
        self.assertEqual(res['word_loss'], 0.0)
        self.assertEqual(res['missing'], [])

    def test_a_dropped_word_is_reported_as_a_loss(self):
        heard = SCRIPT.replace('ಭಾರೀ', '')
        res = vn.compare(SCRIPT, heard)
        self.assertIn('ಭಾರೀ', res['missing'])
        self.assertGreater(res['word_loss'], 0)

    def test_case_endings_do_not_count_as_loss(self):
        # Agglutination: ಉಡುಪಿ vs ಉಡುಪಿಯಲ್ಲಿ share the stem ಉಡುಪಿ.
        # Morphology is not a mispronunciation (module docstring).
        heard = SCRIPT.replace('ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ', 'ಉಡುಪಿಯಲ್ಲಿ ಜಿಲ್ಲೆ')
        res = vn.compare(SCRIPT, heard)
        self.assertEqual(res['missing'], [])


class CheckFileWithAMockedTranscriber(unittest.TestCase):

    def test_hearing_the_script_passes(self):
        with mock.patch.object(vn, 'transcribe', return_value=SCRIPT):
            res = vn.check_file('voiceover.mp3', SCRIPT)
        self.assertTrue(res['pass'], res)

    def test_a_transcript_that_lost_words_fails(self):
        with mock.patch.object(vn, 'transcribe',
                               return_value='ಉಡುಪಿ ಮಳೆ ಇಲಾಖೆ'):
            res = vn.check_file('voiceover.mp3', SCRIPT)
        self.assertFalse(res['pass'])
        self.assertTrue(res['missing'])

    def test_no_transcript_is_a_skip_not_a_failure(self):
        with mock.patch.object(vn, 'transcribe', return_value=''):
            res = vn.check_file('voiceover.mp3', SCRIPT)
        self.assertIn('skipped', res)


class ScriptsInReadsTheCopyFiles(unittest.TestCase):

    def test_voiceover_script_maps_to_its_mp3(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'roundup_copy.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump({'voiceover_script': SCRIPT}, fh, ensure_ascii=False)
            with open(os.path.join(tmp, 'saara_copy.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump({'no_script_here': 1}, fh)
            self.assertEqual(vn.scripts_in(tmp),
                             {'roundup_voiceover.mp3': SCRIPT})


class NoEngineIsAGracefulMorning(unittest.TestCase):

    def test_without_whisper_it_explains_and_exits_0(self):
        with mock.patch.object(vn, 'engine', return_value=''):
            rc, out = cli(['out/whatever'])
        self.assertEqual(rc, 0, out)
        self.assertIn('Whisper is not installed', out)

    def test_a_single_file_needs_the_intended_script(self):
        with mock.patch.object(vn, 'engine', return_value='mlx_whisper'):
            rc, _ = cli(['voiceover.mp3'])
        self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()
