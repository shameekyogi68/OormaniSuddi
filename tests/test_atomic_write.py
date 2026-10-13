"""
A torn write must never stand in for a good file.
=================================================
`brand.atomic.write_json` replaces a JSON file via a flushed, fsynced
`path + '.part'` and `os.replace`. The promise a caller relies on: the
target is either the fully-written new content or the untouched old
content — never a truncated in-between. These tests prove the old content
survives an interruption at the replace step, that the temp file is
cleaned up, and that each caller's byte format (indent, ensure_ascii,
trailing newline) is preserved.
"""

# Enforces D122 — see docs/DECISIONS.md.
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

from brand.atomic import write_json

ORIGINAL = '{"good": true, "kn": "ಊರ್ಮನಿ"}\n'


class InterruptedWrite(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, 'state.json')
        with open(self.path, 'w', encoding='utf-8') as fh:
            fh.write(ORIGINAL)

    def tearDown(self):
        self._tmp.cleanup()

    def _part(self) -> str:
        return self.path + '.part'

    def test_happy_path_replaces_content_and_leaves_no_temp(self):
        write_json(self.path, {'good': False})
        with open(self.path, encoding='utf-8') as fh:
            self.assertEqual(json.load(fh), {'good': False})
        self.assertFalse(os.path.exists(self._part()))

    def test_failed_replace_preserves_original_and_cleans_temp(self):
        # The crash moment: the .part is fully written, os.replace never
        # lands. The original file must read exactly as before.
        with mock.patch('brand.atomic.os.replace',
                        side_effect=OSError('power cut')):
            with self.assertRaises(OSError):
                write_json(self.path, {'good': False})
        with open(self.path, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), ORIGINAL)
        self.assertFalse(os.path.exists(self._part()),
                         'a dead .part could be mistaken for the real file '
                         'by anything globbing the directory')

    def test_failed_serialisation_preserves_original_and_cleans_temp(self):
        # A value that cannot serialise fails INSIDE the temp write; the
        # caller must still see the old file intact.
        with self.assertRaises(TypeError):
            write_json(self.path, {'x': object()})
        with open(self.path, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), ORIGINAL)
        self.assertFalse(os.path.exists(self._part()))

    def test_bytes_match_house_format(self):
        # Every adoption site used indent=2, ensure_ascii=False and a
        # trailing newline; the helper must reproduce those bytes exactly.
        write_json(self.path, {'kn': 'ಊರ್ಮನಿ'})
        expected = json.dumps({'kn': 'ಊರ್ಮನಿ'}, indent=2,
                              ensure_ascii=False) + '\n'
        with open(self.path, encoding='utf-8') as fh:
            self.assertEqual(fh.read(), expected)

    def test_ensure_ascii_is_respected(self):
        write_json(self.path, {'kn': 'ಊರ್ಮನಿ'}, ensure_ascii=True)
        with open(self.path, encoding='utf-8') as fh:
            self.assertEqual(fh.read(),
                             json.dumps({'kn': 'ಊರ್ಮನಿ'}, indent=2,
                                        ensure_ascii=True) + '\n')


if __name__ == '__main__':
    unittest.main()
