"""
The team: every agent exists, is jailed, files receipts, and is called when —
and only when — there is work for it. D89.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from unittest import mock

from brand import dispatch as D
from brand import codes

AGENTS = D.AGENTS_DIR


def story(**kw):
    s = {'headline': 'ಉಡುಪಿಯಲ್ಲಿ ಹೊಸ ಸೇತುವೆ ಉದ್ಘಾಟನೆ', 'category': 'civic',
         'location': 'ಉಡುಪಿ', 'sources': ['ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ'],
         'deck': 'ಸೇತುವೆ ಉದ್ಘಾಟನೆಯಾಗಿದೆ.', 'verified_by': ''}
    s.update(kw)
    return s


class TheRosterIsTheTeam(unittest.TestCase):

    def test_every_roster_agent_has_a_definition_and_back(self):
        files = {f[:-3] for f in os.listdir(AGENTS) if f.endswith('.md')}
        self.assertEqual(set(D.ROSTER), files)

    def test_every_agent_is_jailed_and_named(self):
        for name in D.ROSTER:
            with open(os.path.join(AGENTS, f'{name}.md'), encoding='utf-8') as fh:
                body = fh.read()
            self.assertIn(f'name: {name}\n', body)
            self.assertIn('Workspace jail', body, name)
            self.assertRegex(body, r'description: .{80,}', name)

    def test_an_agent_the_dispatcher_waits_on_files_a_receipt(self):
        """planning-editor and systems-steward write their own dated file;
        news-scout's result is the edition itself."""
        own_file = {'planning-editor', 'systems-steward', 'news-scout'}
        for name in set(D.ROSTER) - own_file:
            with open(os.path.join(AGENTS, f'{name}.md'), encoding='utf-8') as fh:
                self.assertIn('dispatch.py receipt', fh.read(), name)

    def test_every_gate_code_family_has_an_agent(self):
        families = {c.split('-')[0] for c in codes.CODES}
        self.assertEqual(families - set(D.CODE_AGENT), set())
        for agent in D.CODE_AGENT.values():
            self.assertIn(agent, D.ROSTER)

    def test_no_agent_may_verify_or_sign(self):
        """What is never automated stays that way (RUNBOOK)."""
        for name in D.ROSTER:
            with open(os.path.join(AGENTS, f'{name}.md'), encoding='utf-8') as fh:
                body = fh.read()
            self.assertIsNone(re.search(r'scripts/sign_off\.py .*--by', body), name)
            self.assertNotIn('verify.py --story', body, name)


class Receipts(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(D, 'RECEIPTS', os.path.join(self.tmp.name, 'r'))
        p.start()
        self.addCleanup(p.stop)
        self.ed = os.path.join(self.tmp.name, '2026-09-30.json')
        self.write([story()])

    def write(self, stories):
        with open(self.ed, 'w', encoding='utf-8') as fh:
            json.dump({'date': '2026-09-30T07:00:00+05:30', 'edition_no': 1,
                       'stories': stories}, fh, ensure_ascii=False)

    def test_a_signature_does_not_make_the_work_due_again(self):
        self.assertEqual(D.story_hash(story()),
                         D.story_hash(story(verified_by='Gautam Paduvari')))

    def test_an_edit_does(self):
        self.assertNotEqual(D.story_hash(story()),
                            D.story_hash(story(headline='ಬೇರೆ ಶೀರ್ಷಿಕೆ')))

    def test_a_receipt_is_current_until_the_story_changes(self):
        D.write_receipt('fact-checker', self.ed, 'PASS', 'ok', story=1)
        h = D.story_hash(story())
        self.assertTrue(D._receipt_current('fact-checker', '2026-09-30', h, 1))
        self.assertFalse(D._receipt_current(
            'fact-checker', '2026-09-30', D.story_hash(story(deck='x')), 1))

    def test_nonsense_is_refused(self):
        with self.assertRaises(ValueError):
            D.write_receipt('nobody', self.ed, 'PASS', 'x', story=1)
        with self.assertRaises(ValueError):
            D.write_receipt('fact-checker', self.ed, 'LGTM', 'x', story=1)
        with self.assertRaises(ValueError):
            D.write_receipt('fact-checker', self.ed, 'PASS', 'x', story=9)


class TheRightAgentIsCalled(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(D, 'RECEIPTS', os.path.join(self.tmp.name, 'r'))
        p.start()
        self.addCleanup(p.stop)

    def edition(self, stories, name='2026-09-30.json'):
        path = os.path.join(self.tmp.name, name)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({'date': '2026-09-30T07:00:00+05:30', 'edition_no': 1,
                       'stories': stories}, fh, ensure_ascii=False)
        return path

    def test_an_unchecked_story_goes_to_the_fact_desk_then_stops(self):
        path = self.edition([story()])
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertIn('fact-checker', [t.agent for t in p.tasks])
        D.write_receipt('fact-checker', path, 'PASS', 'ok', story=1)
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertNotIn('fact-checker', [t.agent for t in p.tasks])

    def test_a_death_story_goes_to_legal_and_a_bridge_does_not(self):
        path = self.edition([story(), story(headline='ಮಲ್ಪೆ: ಮೀನುಗಾರ ಸಾವು')])
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        legal = [t.story for t in p.tasks if t.agent == 'legal-standards']
        self.assertEqual(legal, [2])

    def test_verification_is_left_to_a_person(self):
        path = self.edition([story()])
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertTrue(any('verify.py' in x for x in p.person))
        self.assertFalse(any('verify' in t.agent for t in p.tasks))

    def test_a_held_gate_calls_the_doctor_and_the_owners(self):
        out = os.path.join(self.tmp.name, 'out', '2026-09-30')
        os.makedirs(out)
        with open(os.path.join(out, 'review_report.json'), 'w') as fh:
            json.dump({'findings': [
                {'code': 'LAW-01', 'severity': 'fail'},
                {'code': 'IMG-04', 'severity': 'fail'},
                {'code': 'PUB-08', 'severity': 'warn'}]}, fh)
        p = D.Plan('2026-09-30'); D._package_tasks(p, out)
        agents = {t.agent for t in p.tasks}
        self.assertTrue({'gate-doctor', 'legal-standards', 'picture-editor',
                         'package-inspector'} <= agents)
        self.assertNotIn('social-writer',
                         {t.agent for t in p.tasks if 'owns' in t.reason})

    def test_the_brief_says_to_run_a_wave_in_parallel(self):
        p = D.Plan('2026-09-30')
        p.add('fact-checker', 'reactive', 1, 'x', 'e.json', story=1)
        p.add('fact-checker', 'reactive', 1, 'x', 'e.json', story=2)
        self.assertIn('ONE message', D.brief(p))
        self.assertEqual(len(p.waves()[1]), 2)


class TheReactiveHookFiresOnRealRunsOnly(unittest.TestCase):
    """It fired on a heredoc that merely mentioned verify.py, the first day
    it was live. A reactive trigger that cries wolf gets ignored."""

    def test_runs_and_mentions(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'dispatch_cli', os.path.join(os.path.dirname(D.ROOT),
                                         os.path.basename(D.ROOT), 'scripts', 'dispatch.py'))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        cases = {
            'cd "/x" && python3 render.py editions/a.json --only carousel': True,
            'python3 scripts/fact_check.py editions/a.json': True,
            'python3 scripts/verify.py editions/a.json --story 1 --by X': True,
            'python3 render.py --check editions/a.json': False,
            "cat > t.py <<'EOF'\nverify.py render.py\nEOF": False,
            'grep -n render.py docs/x.md': False,
            'python3 scripts/correction.py status': False,
            'python3 -m unittest tests.test_dispatch': False,
        }
        for cmd, want in cases.items():
            self.assertEqual(m.ran_pipeline(cmd), want, cmd)


if __name__ == '__main__':
    unittest.main()


class ARenderNeverOverwritesAnotherEdition(unittest.TestCase):
    """2026-09-25: the ಕಾನೂನು ಕವಚ explainer, dated the same day, rendered into
    out/2026-09-25 and replaced that day's news carousel. D90."""

    def test_a_folder_stamped_for_another_edition_is_refused(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, '.edition'), 'w') as fh:
                fh.write('editions/some_other_edition.json\n')
            r = subprocess.run(
                [sys.executable, 'render.py', 'editions/2026-09-22.json',
                 '--only', 'carousel', '--out', tmp],
                cwd=D.ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 1)
            self.assertIn('would overwrite', r.stderr)
            self.assertFalse(any(f.endswith('.jpg') for f in os.listdir(tmp)))

    def test_the_dispatcher_does_not_inspect_a_foreign_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, '.edition'), 'w') as fh:
                fh.write('editions/x.json\n')
            self.assertEqual(D.owner_of(tmp), 'editions/x.json')
