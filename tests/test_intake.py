"""
Paste-first intake. D92.
========================
News comes in because the editor pasted it; the scraper, the automatic draft
and their schedule are deleted. What is left has two jobs and this suite pins
both:

  * **The pasted text is the source.** `save_pasted()` keeps it exactly where
    the fact desk (FACT-01/FACT-03) looks it up, so every figure published is
    checked against what the editor gave us.
  * **Nothing runs twice.** `published_before()` finds a story that already
    ran on an earlier day — the same source URL, or the same headline
    reworded — so DUP-01 can refuse it unless it is a real follow-up.

The groundedness tests that lived here moved to tests/test_grounding.py.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from brand import factcheck as F
from brand import intake as I
from brand.content import Story


def _edition(root, name, date, stories, where='editions'):
    d = os.path.join(root, where) if where == 'editions' else \
        os.path.join(root, 'archive', where)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
        json.dump({'date': date, 'stories': stories}, fh, ensure_ascii=False)


URL = 'https://www.udayavani.com/udupi/voters-list-10-lakh'
OLD = {'headline': 'ಉಡುಪಿ: 10.01 ಲಕ್ಷ ಮತದಾರರು, ಅಕ್ಟೋಬರ್ 27ಕ್ಕೆ ಅಂತಿಮ ಪಟ್ಟಿ',
       'source_urls': [URL]}
RAIN = {'headline': 'ಬೈಂದೂರು ಕುಂದಾಪುರದಲ್ಲಿ ಭಾರಿ ಮಳೆ ಶಾಲೆಗಳಿಗೆ ರಜೆ ಘೋಷಣೆ',
        'source_urls': ['https://example.org/rain']}


class ThePastedTextIsTheSource(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(F, 'SOURCES_DIR', os.path.join(self.tmp.name, 's'))
        p.start()
        self.addCleanup(p.stop)

    def test_a_pasted_article_lands_where_the_fact_desk_reads_it(self):
        path = I.save_pasted('Byndoor recorded 82.9 mm of rain.', url=URL)
        self.assertEqual(path, F.cache_path(URL))
        st = Story(headline='ಬೈಂದೂರಿನಲ್ಲಿ 82.9 ಮಿ.ಮೀ ಮಳೆ', sources=['Udayavani'],
                   source_urls=[URL])
        text, missing = F.source_text(st)
        self.assertIn('82.9 mm', text)
        self.assertEqual(missing, [])
        self.assertEqual(F.check(st).figures, [])

    def test_the_outlet_is_kept_with_the_text(self):
        path = I.save_pasted('Some news.', url=URL, outlet='Udayavani')
        with open(path, encoding='utf-8') as fh:
            body = fh.read()
        self.assertTrue(body.startswith(URL))
        self.assertIn('Outlet: Udayavani', body)

    def test_own_reporting_is_kept_without_a_url(self):
        path = I.save_pasted('ನಮ್ಮ ವರದಿಗಾರರ ಟಿಪ್ಪಣಿ', outlet='ಊರ್ಮನಿ ಸುದ್ದಿ')
        self.assertTrue(os.path.basename(path).startswith('own_'))
        self.assertTrue(path.startswith(F.SOURCES_DIR))
        # the same paste twice is the same file, not a second copy
        self.assertEqual(path, I.save_pasted('ನಮ್ಮ ವರದಿಗಾರರ ಟಿಪ್ಪಣಿ'))

    def test_an_empty_paste_is_refused(self):
        with self.assertRaises(ValueError):
            I.save_pasted('   \n ', url=URL)


class NothingRunsTwice(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        _edition(self.root, '2026-09-24.json', '2026-09-24T08:00:00+05:30',
                 [RAIN, OLD])

    def test_the_same_source_url_on_an_earlier_day_is_found(self):
        st = {'headline': 'ಮತದಾರರ ಪಟ್ಟಿ ಪರಿಷ್ಕರಣೆ', 'source_urls': [URL + '/']}
        out = I.published_before(st, dt.date(2026, 9, 25), root=self.root)
        self.assertEqual(len(out), 1)
        self.assertIn('same source URL as 2026-09-24 story 2', out[0])
        self.assertTrue(I.url_repeat(out))

    def test_a_story_object_works_as_well_as_a_dict(self):
        st = Story(headline='ಮತದಾರರ ಪಟ್ಟಿ', source_urls=[URL])
        self.assertTrue(I.published_before(st, dt.date(2026, 9, 25),
                                           root=self.root))

    def test_a_reworded_headline_is_the_same_story(self):
        st = {'headline': 'ಬೈಂದೂರು ಕುಂದಾಪುರದಲ್ಲಿ ಭಾರಿ ಮಳೆ: ಶಾಲೆಗಳಿಗೆ ರಜೆ',
              'source_urls': ['https://example.org/another-url']}
        out = I.published_before(st, dt.date(2026, 9, 25), root=self.root)
        self.assertEqual(len(out), 1)
        self.assertIn('2026-09-24 story 1', out[0])
        self.assertFalse(I.url_repeat(out))

    def test_a_different_story_in_the_same_town_is_new(self):
        st = {'headline': 'ಕುಂದಾಪುರ ಬಂದರು ಕಾಮಗಾರಿ ಪೂರ್ಣ',
              'source_urls': ['https://example.org/port']}
        self.assertEqual(I.published_before(st, dt.date(2026, 9, 25),
                                            root=self.root), [])

    def test_the_same_day_and_later_days_do_not_count(self):
        st = dict(OLD)
        self.assertEqual(I.published_before(st, dt.date(2026, 9, 24),
                                            root=self.root), [])
        self.assertEqual(I.published_before(st, dt.date(2026, 9, 1),
                                            root=self.root), [])

    def test_the_archive_counts_and_is_not_double_reported(self):
        _edition(self.root, '2026-09-24.json', '2026-09-24T08:00:00+05:30',
                 [RAIN, OLD], where='2026-09-24')
        _edition(self.root, '2026-09-20.json', '2026-09-20T08:00:00+05:30',
                 [OLD], where='2026-09-20')
        out = I.published_before(dict(OLD), dt.date(2026, 9, 25),
                                 root=self.root)
        self.assertEqual(len(out), 2, out)       # 20th and 24th, once each

    def test_an_unreadable_edition_is_skipped(self):
        with open(os.path.join(self.root, 'editions', 'broken.json'), 'w') as fh:
            fh.write('{not json')
        _edition(self.root, 'x.json', None, [OLD], where='weird')
        self.assertTrue(I.published_before(dict(OLD), dt.date(2026, 9, 25),
                                           root=self.root))

    def test_a_new_edition_file_is_seen_without_restarting(self):
        """Cached per root, but the cache notices a new file."""
        st = {'headline': 'ಹೊಸ ಕಥೆ ಮಲ್ಪೆ ಬಂದರು', 'source_urls': ['https://e.org/m']}
        self.assertEqual(I.published_before(st, dt.date(2026, 9, 27),
                                            root=self.root), [])
        _edition(self.root, '2026-09-26.json', '2026-09-26T08:00:00+05:30', [st])
        self.assertTrue(I.published_before(st, dt.date(2026, 9, 27),
                                           root=self.root))

    def test_town_names_count_toward_the_overlap(self):
        a = I.headline_words('ಉಡುಪಿ ಬೈಂದೂರು ಮಳೆ')
        self.assertIn('ಉಡುಪಿ', a)
        self.assertIn('ಬೈಂದೂರು', a)


class TheCommandLine(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        _edition(self.root, '2026-09-24.json', '2026-09-24T08:00:00+05:30', [OLD])

    def _seen(self, stories):
        path = os.path.join(self.root, 'today.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({'date': '2026-09-25T08:00:00+05:30', 'stories': stories},
                      fh, ensure_ascii=False)
        from scripts import intake as cli
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli.main(['seen', path, '--root', self.root])
        return rc, out.getvalue()

    def test_a_url_repeat_fails_the_check(self):
        rc, out = self._seen([dict(OLD)])
        self.assertEqual(rc, 1)
        self.assertIn('REFUSE', out)

    def test_a_marked_follow_up_passes_but_is_questioned(self):
        rc, out = self._seen([dict(OLD, follows_up='2026-09-24')])
        self.assertEqual(rc, 0)
        self.assertIn('what is NEW', out)

    def test_a_new_edition_passes(self):
        rc, _ = self._seen([{'headline': 'ಮಲ್ಪೆ ಬಂದರು ಹೂಳೆತ್ತುವ ಕಾಮಗಾರಿ',
                             'source_urls': ['https://e.org/malpe']}])
        self.assertEqual(rc, 0)

    def test_source_reads_a_file(self):
        with mock.patch.object(F, 'SOURCES_DIR', os.path.join(self.root, 's')):
            src = os.path.join(self.root, 'paste.txt')
            with open(src, 'w', encoding='utf-8') as fh:
                fh.write('Byndoor recorded 82.9 mm.')
            from scripts import intake as cli
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cli.main(['source', '--url', URL, '--file', src])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(F.cache_path(URL)))


class TheScraperIsGone(unittest.TestCase):
    """D92: nothing fetches news on a schedule any more."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_the_morning_pipeline_is_deleted(self):
        for rel in ('scripts/fetch_daily_news.py', 'scripts/draft_edition.py',
                    'scripts/morning.sh', 'scripts/install_launchd.sh',
                    'scripts/trending_tags.py', 'scripts/launchd'):
            self.assertFalse(os.path.exists(os.path.join(self.ROOT, rel)), rel)

    def test_intake_and_fact_desk_never_open_a_socket(self):
        for rel in ('brand/intake.py', 'brand/grounding.py',
                    'brand/factcheck.py', 'scripts/intake.py',
                    'scripts/fact_check.py'):
            with open(os.path.join(self.ROOT, rel), encoding='utf-8') as fh:
                src = fh.read()
            for net in ('urllib.request', 'requests', 'http.client', 'socket'):
                self.assertNotIn(f'import {net}', src, rel)


class NoScriptSplitsAPasteOrGuessesAnOutlet(unittest.TestCase):
    """D111: `daily_flow.py intake` split a paste line by line and credited any
    link it did not recognise to ಉದಯವಾಣಿ. Splitting and crediting are the
    intake desk's; the script now refuses and points at intake.py source."""

    def test_the_batch_intake_refuses_and_saves_nothing(self):
        from scripts import daily_flow
        before = set(os.listdir(F.SOURCES_DIR)) if os.path.isdir(F.SOURCES_DIR) else set()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = daily_flow.cmd_intake(None)
        self.assertEqual(rc, 2)
        self.assertIn('intake.py source', err.getvalue())
        after = set(os.listdir(F.SOURCES_DIR)) if os.path.isdir(F.SOURCES_DIR) else set()
        self.assertEqual(before, after)

    def test_no_script_defaults_an_outlet(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in ('scripts/daily_flow.py', 'scripts/intake.py', 'brand/intake.py'):
            with open(os.path.join(root, rel), encoding='utf-8') as fh:
                src = fh.read()
            self.assertNotIn("else 'ಉದಯವಾಣಿ'", src, rel)


if __name__ == '__main__':
    unittest.main()
