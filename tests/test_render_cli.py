"""
render.py at the command line — the workspace guard. D127.
===========================================================
`render.py --out` writes more bytes than any other script, and it was the
one path-taking script whose writes were not guarded: `--out` was used
verbatim, so a mistyped or model-proposed output path could land anywhere on
disk. Rule 10 (workspace isolation) was code-enforced everywhere else and
convention-enforced here.

These tests pin the guard at the CLI: outside the workspace is a refused
run with the reason printed, not a silent write somewhere else. Rendering
itself is pinned by the golden suite — this file owns only the gate.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import render

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, 'fixture_edition.json')


def cli(argv):
    out = io.StringIO()
    with mock.patch('sys.argv', ['render.py'] + argv), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = render.main()
    return rc, out.getvalue()


class OutStaysInsideTheWorkspace(unittest.TestCase):

    def test_an_outside_path_is_refused_before_anything_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = os.path.join(tmp, 'elsewhere')
            rc, out = cli([FIXTURE, '--out', outside, '--check'])
        self.assertEqual(rc, 1, out)
        self.assertIn('✗', out)

    def test_path_traversal_out_is_refused(self):
        rc, out = cli([FIXTURE, '--out', '../../outside', '--check'])
        self.assertEqual(rc, 1, out)

    def test_an_inside_path_passes_the_guard(self):
        # --check stops before any pixel work; reaching a non-guard exit
        # code proves the guard did not refuse an in-workspace path.
        rc, out = cli([FIXTURE, '--out', 'out/_cli_guard_check', '--check'])
        self.assertNotEqual(rc, 1)
        self.assertNotIn('outside the workspace', out)


if __name__ == '__main__':
    unittest.main()
