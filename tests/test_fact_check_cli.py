"""
fact_check.py at the command line. D84.
======================================
The offline figure check runs BEFORE render because fixing a figure here
costs a line and fixing it at the FACT-01 gate costs a re-render. These tests
pin the contract a desk relies on: exit 0 only when nothing blocks, exit 1
with a named reason when a figure or a whole pasted article is wrong.

`kept_but_wrong` is exercised for real (a wrong paste is detected); the
figure ledger is mocked, because the ledger's own logic belongs to
tests/test_grounding.py — this suite owns the CLI's exit codes and messages.
"""

# Enforces D125, D84 — see docs/DECISIONS.md.
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from scripts import fact_check as fc

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, 'fixture_edition.json')


def quietly(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = fn(*a, **kw)
    return rc, out.getvalue()


def clean_results(**over):
    base = SimpleNamespace(figures=[], state='ok', missing_sources=[])
    for k, v in over.items():
        setattr(base, k, v)
    return [base]


@mock.patch('scripts.fact_check.kept_but_wrong', return_value=[])
@mock.patch('brand.factcheck.report', return_value='the ledger')
@mock.patch('brand.factcheck.check_edition')
class ExitCodes(unittest.TestCase):

    def test_everything_checks_exits_0(self, check, _report, _wrong):
        check.return_value = clean_results()
        rc, out = quietly(fc.main, [FIXTURE])
        self.assertEqual(rc, 0, out)
        self.assertIn('the ledger', out)

    def test_a_figure_not_in_the_source_exits_1(self, check, _report, _wrong):
        check.return_value = clean_results(figures=['3 ಲಕ್ಷ'])
        rc, out = quietly(fc.main, [FIXTURE])
        self.assertEqual(rc, 1, out)
        self.assertIn('1 figure(s) not in the source', out)

    def test_a_kept_file_that_is_the_wrong_article_exits_1(self, check,
                                                           _report, wrong):
        check.return_value = clean_results()
        wrong.return_value = ['https://example.com/wrong-article']
        rc, out = quietly(fc.main, [FIXTURE])
        self.assertEqual(rc, 1, out)
        self.assertIn('BLOCK', out)
        self.assertIn('wrong article', out)


class KeptButWrongIsReal(unittest.TestCase):
    """The wrong-paste detector itself: a kept file that does not carry its
    story is evidence of nothing and must be named."""

    def test_unrelated_text_is_flagged(self):
        from brand import factcheck as F
        ed = fc.Edition.load(FIXTURE)
        # The paste must be Kannada (a Latin-script body is "uncheckable",
        # cross-script, and honestly deferred to the figure check) but share
        # NO token with any story's headline+deck.
        line_toks: set = set()
        for st in ed.stories:
            line = ' '.join(filter(None, [st.headline, st.deck]))
            line_toks |= set(F._TOKEN.findall(line))
        filler = [w for w in ('ಶಾಲೆ ಕಾಲೇಜು ವಿದ್ಯಾರ್ಥಿ ಶಿಕ್ಷಕ ಪಾಠ ಪುಸ್ತಕ '
                              'ಬಸ್ ರಸ್ತೆ ಗುರಿ ಪ್ರಶಸ್ತಿ') if w not in line_toks]
        self.assertGreaterEqual(len(filler), 3)
        with tempfile.TemporaryDirectory() as tmp:
            body = os.path.join(tmp, 'kept.txt')
            with open(body, 'w', encoding='utf-8') as fh:
                fh.write(' '.join(filler))
            with mock.patch('brand.factcheck.cache_path', return_value=body):
                wrong = fc.kept_but_wrong(ed)
        self.assertTrue(wrong, 'an unrelated paste was not flagged')

    def test_a_missing_kept_file_is_skipped_not_flagged(self):
        ed = fc.Edition.load(FIXTURE)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch('brand.factcheck.cache_path',
                            return_value=os.path.join(tmp, 'absent.txt')):
                self.assertEqual(fc.kept_but_wrong(ed), [])


if __name__ == '__main__':
    unittest.main()
