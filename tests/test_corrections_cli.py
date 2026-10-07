"""
The corrections desk's own command runs.
========================================
D116. D88 and the corrections-officer's instructions log an error the
newsroom found itself with `correction.py new --channel desk`; the script
refused `desk`, so the documented command failed and the known 23–24 Sept
errata went unlogged while the dispatcher kept asking for them.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from brand import corrections as C
from brand import dispatch as D
from scripts import correction as cli


class TheDeskChannelIsAccepted(unittest.TestCase):

    def setUp(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        p = mock.patch.object(C, 'LEDGER', os.path.join(d, 'corrections.jsonl'))
        p.start()
        self.addCleanup(p.stop)

    def run_cli(self, *argv) -> int:
        with mock.patch('sys.argv', ['correction.py', *argv]), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                return cli.main() or 0
            except SystemExit as e:
                return e.code or 0

    def test_the_documented_command_logs_a_case(self):
        rc = self.run_cli('new', '--about', '2026-09-23', '--channel', 'desk',
                          '--from', 'Desk: fact-check agents',
                          '--summary', 'found by the fact desk (D88)')
        self.assertEqual(rc, 0)
        self.assertEqual(len(C.current()), 1)

    def test_the_agent_brief_uses_only_channels_the_script_accepts(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, '.claude', 'agents', 'corrections-officer.md'),
                  encoding='utf-8') as fh:
            brief = fh.read()
        import re
        for ch in re.findall(r'--channel (\w+)', brief):
            self.assertEqual(self.run_cli('new', '--about', '2026-09-24',
                                          '--channel', ch, '--summary', 'x'), 0, ch)

    def test_a_logged_case_clears_the_errata_from_the_board(self):
        self.run_cli('new', '--about', '2026-09-23', '--channel', 'desk', '--summary', 'x')
        self.run_cli('new', '--about', '2026-09-24', '--channel', 'desk', '--summary', 'x')
        rows = C.current()
        for r in rows.values():
            r['state'] = 'closed'
        with mock.patch.object(C, 'current', lambda: rows), \
                mock.patch.object(C, 'overdue', lambda: {}):
            p = D.Plan(day='2026-10-07')
            D._corrections_tasks(p)
        self.assertFalse([t for t in p.tasks if 'unsupported claims' in t.reason])


if __name__ == '__main__':
    unittest.main()
