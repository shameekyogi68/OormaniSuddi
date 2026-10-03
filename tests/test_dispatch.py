"""
The team: every agent exists, is jailed, files receipts, and is called when —
and only when — there is work for it. D89, D92.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest
from unittest import mock

from brand import dispatch as D
from brand import codes

AGENTS = D.AGENTS_DIR


def story(**kw):
    s = {'headline': 'ಉಡುಪಿಯಲ್ಲಿ ಹೊಸ ಸೇತುವೆ ಉದ್ಘಾಟನೆ', 'category': 'civic',
         'location': 'ಉಡುಪಿ', 'sources': ['ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ'],
         'deck': 'ಸೇತುವೆ ಉದ್ಘಾಟನೆಯಾಗಿದೆ.', 'verified_by': '',
         'segment': 'saara', 'photo_plan': ''}
    s.update(kw)
    return s


def photo(**kw):
    p = {'path': 'assets/daily/x.jpg', 'nature': 'actual', 'credit': 'ಸಂಪಾದಕ',
         'licence': 'own', 'caption': 'ಸೇತುವೆ'}
    p.update(kw)
    return p


def cli():
    spec = importlib.util.spec_from_file_location(
        'dispatch_cli', os.path.join(D.ROOT, 'scripts', 'dispatch.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def agent_files() -> set[str]:
    return {f[:-3] for f in os.listdir(AGENTS)
            if f.endswith('.md') and f != D.CONVENTIONS}


def body_of(name: str) -> str:
    with open(os.path.join(AGENTS, f'{name}.md'), encoding='utf-8') as fh:
        return fh.read()


def frontmatter(name: str) -> dict:
    head = body_of(name).split('---')[1]
    return dict(line.split(': ', 1) for line in head.strip().split('\n'))


class TheRosterIsTheTeam(unittest.TestCase):

    def test_every_roster_agent_has_a_definition_and_back(self):
        self.assertEqual(set(D.ROSTER), agent_files())

    def test_the_conventions_file_is_not_an_agent(self):
        self.assertTrue(os.path.exists(os.path.join(AGENTS, D.CONVENTIONS)))
        self.assertNotIn(D.CONVENTIONS[:-3], D.ROSTER)
        with open(os.path.join(AGENTS, D.CONVENTIONS), encoding='utf-8') as fh:
            conv = fh.read()
        self.assertFalse(conv.startswith('---'), 'no agent frontmatter')
        for rule in ('Workspace jail', 'dispatch.py receipt', 'verified_by',
                     'story by story, in batches'):
            self.assertIn(rule, conv)

    def test_the_scouts_are_gone(self):
        """D92: pasted news in, no scraping, no trend scraper."""
        for gone in ('news-scout', 'trend-scout'):
            self.assertNotIn(gone, D.ROSTER)
            self.assertFalse(os.path.exists(os.path.join(AGENTS, f'{gone}.md')))

    def test_every_agent_is_jailed_named_and_reads_the_conventions(self):
        for name in D.ROSTER:
            body = body_of(name)
            self.assertIn(f'name: {name}\n', body)
            self.assertIn('Workspace jail', body, name)
            self.assertIn('Read `.claude/agents/_CONVENTIONS.md` first', body, name)
            self.assertRegex(body, r'description: .{80,}', name)
            self.assertIn('proactively', frontmatter(name)['description'], name)

    def test_no_agent_scrapes(self):
        """Intake is paste-only (D92). No desk needs the web."""
        for name in D.ROSTER:
            tools = frontmatter(name)['tools']
            self.assertNotIn('WebFetch', tools, name)
            self.assertNotIn('WebSearch', tools, name)

    def test_models(self):
        # D97: every agent pins its model, so what a run costs never depends
        # on which model the chat happens to be using.
        for name in D.ROSTER:
            self.assertEqual(frontmatter(name).get('model'), 'sonnet', name)

    def test_nothing_names_the_stock_library_as_a_source_of_pictures(self):
        for name in D.ROSTER:
            self.assertNotIn('brand.stock', body_of(name), name)

    def test_ops_are_not_production(self):
        self.assertEqual({n for n, r in D.ROSTER.items() if r['kind'] == 'ops'},
                         {'planning-editor', 'systems-steward'})

    def test_an_agent_the_dispatcher_waits_on_files_a_receipt(self):
        """planning-editor and systems-steward write their own dated file."""
        for name in set(D.ROSTER) - {'planning-editor', 'systems-steward'}:
            self.assertIn('dispatch.py receipt', body_of(name), name)

    def test_every_gate_code_family_has_an_agent(self):
        families = {c.split('-')[0] for c in codes.CODES}
        self.assertEqual(families - set(D.CODE_AGENT), set())
        for agent in D.CODE_AGENT.values():
            self.assertIn(agent, D.ROSTER)

    def test_no_agent_may_verify_or_sign(self):
        """What is never automated stays that way (RUNBOOK)."""
        for name in D.ROSTER:
            body = body_of(name)
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

    def test_the_fact_hash_ignores_segment_photo_and_plan(self):
        """D92: choosing the format or adding a picture is not a fact."""
        base = D.fact_hash(story())
        for change in ({'segment': 'mukhya'}, {'photo_plan': 'ai'},
                       {'photo': photo()}, {'hook': 'ಹೊಸ ಹುಕ್'},
                       {'verified_by': 'X'}, {'template': 'saara'}):
            self.assertEqual(D.fact_hash(story(**change)), base, change)

    def test_the_fact_hash_sees_every_fact_bearing_field(self):
        base = D.fact_hash(story())
        for change in ({'headline': 'ಬೇರೆ'}, {'deck': 'ಬೇರೆ'},
                       {'points': ['1 ಸಾವು']}, {'reel_line': 'ಬೇರೆ'},
                       {'sources': ['ಉದಯವಾಣಿ']}, {'location': 'ಕುಂದಾಪುರ'},
                       {'involves_minor': True}, {'numbers': [['3', 'ಜನ']]}):
            self.assertNotEqual(D.fact_hash(story(**change)), base, change)

    def test_a_fact_receipt_survives_a_segment_and_a_photo(self):
        D.write_receipt('fact-checker', self.ed, 'PASS', 'ok', story=1)
        self.write([story(segment='mukhya', photo_plan='real', photo=photo())])
        p = D.Plan('2026-09-30'); D._edition_tasks(p, self.ed)
        self.assertNotIn(('fact-checker', 1),
                         {(t.agent, t.story) for t in p.tasks})

    def test_a_copy_edit_sends_it_back(self):
        D.write_receipt('fact-checker', self.ed, 'PASS', 'ok', story=1)
        self.write([story(headline='ಉಡುಪಿ: ಸೇತುವೆ ಲೋಕಾರ್ಪಣೆ')])
        p = D.Plan('2026-09-30'); D._edition_tasks(p, self.ed)
        self.assertIn(('fact-checker', 1), {(t.agent, t.story) for t in p.tasks})

    def test_a_receipt_is_current_until_the_story_changes(self):
        D.write_receipt('fact-checker', self.ed, 'PASS', 'ok', story=1)
        self.assertTrue(D._receipt_current(
            'fact-checker', '2026-09-30', D.fact_hash(story()), 1))
        self.assertFalse(D._receipt_current(
            'fact-checker', '2026-09-30', D.fact_hash(story(deck='x')), 1))

    def test_a_format_receipt(self):
        out = os.path.join(self.tmp.name, 'out', '2026-09-30')
        D.write_receipt('package-inspector', out, 'PASS', 'ok', part='mukhya_2')
        self.assertEqual(D.read_receipt('package-inspector', '2026-09-30',
                                        0, 'mukhya_2')['verdict'], 'PASS')
        with self.assertRaises(ValueError):
            D.write_receipt('package-inspector', out, 'PASS', 'x', part='carousel')

    def test_nonsense_is_refused(self):
        with self.assertRaises(ValueError):
            D.write_receipt('nobody', self.ed, 'PASS', 'x', story=1)
        with self.assertRaises(ValueError):
            D.write_receipt('news-scout', self.ed, 'PASS', 'x', story=1)
        with self.assertRaises(ValueError):
            D.write_receipt('fact-checker', self.ed, 'LGTM', 'x', story=1)
        with self.assertRaises(ValueError):
            D.write_receipt('fact-checker', self.ed, 'PASS', 'x', story=9)


class _Newsroom(unittest.TestCase):

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

    def plan_for(self, stories):
        path = self.edition(stories)
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        return p, path

    @staticmethod
    def of(p, agent):
        return [t for t in p.tasks + p.ops if t.agent == agent]


class TheRightAgentIsCalled(_Newsroom):

    def test_an_unchecked_story_goes_to_the_fact_desk_then_stops(self):
        p, path = self.plan_for([story()])
        self.assertTrue(self.of(p, 'fact-checker'))
        D.write_receipt('fact-checker', path, 'PASS', 'ok', story=1)
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertFalse(self.of(p, 'fact-checker'))

    def test_a_death_story_goes_to_legal_and_a_bridge_does_not(self):
        p, _ = self.plan_for([story(), story(headline='ಮಲ್ಪೆ: ಮೀನುಗಾರ ಸಾವು')])
        self.assertEqual([t.story for t in self.of(p, 'legal-standards')], [2])

    def test_verification_is_left_to_a_person(self):
        p, _ = self.plan_for([story()])
        self.assertTrue(any('verify.py' in x for x in p.person))
        self.assertFalse(any('verify' in t.agent for t in p.tasks))

    def test_the_kannada_desk_is_one_instance_per_story(self):
        p, _ = self.plan_for([story(), story(segment='speed')])
        self.assertEqual(sorted(t.story for t in self.of(p, 'kannada-editor')),
                         [1, 2])

    def test_waves(self):
        p, _ = self.plan_for([story(segment=''),
                              story(headline='ಮಲ್ಪೆ: ಮೀನುಗಾರ ಸಾವು',
                                    segment='mukhya', photo_plan='ai')])
        wave = {t.agent: t.wave for t in p.tasks}
        self.assertEqual(wave['intake-editor'], 0)
        self.assertEqual(wave['fact-checker'], 1)
        self.assertEqual(wave['legal-standards'], 1)
        self.assertEqual(wave['kannada-editor'], 2)
        self.assertEqual(wave['picture-editor'], 2)

    def test_the_brief_says_to_run_a_wave_in_parallel(self):
        p = D.Plan('2026-09-30')
        p.add('fact-checker', 'reactive', 1, 'x', 'e.json', story=1)
        p.add('fact-checker', 'reactive', 1, 'x', 'e.json', story=2)
        self.assertIn('ONE message', D.brief(p))
        self.assertEqual(len(p.waves()[1]), 2)


class SegmentlessStoriesGoToIntake(_Newsroom):
    """D92: the editor pastes; the intake desk splits, sources and proposes
    a format. A story with no segment has not been through intake."""

    def test_a_story_with_no_segment_calls_intake_once(self):
        p, _ = self.plan_for([story(segment=''), {**story(), 'segment': None},
                              story()])
        intake = self.of(p, 'intake-editor')
        self.assertEqual(len(intake), 1)
        self.assertEqual(intake[0].wave, 0)
        self.assertIn('2 of 3', intake[0].reason)

    def test_every_story_segmented_means_no_intake(self):
        p, _ = self.plan_for([story(), story(segment='speed'),
                              story(segment='mukhya', photo_plan='real')])
        self.assertFalse(self.of(p, 'intake-editor'))

    def test_a_missing_segment_is_not_a_fault_for_the_doctor(self):
        p, _ = self.plan_for([story(segment='')])
        self.assertFalse(self.of(p, 'gate-doctor'))

    def test_a_segmentless_story_still_gets_its_fact_check(self):
        p, _ = self.plan_for([story(segment='')])
        self.assertTrue(self.of(p, 'fact-checker'))
        self.assertFalse(self.of(p, 'picture-editor'))
        self.assertFalse(self.of(p, 'kannada-editor'))

    def test_the_day_with_no_edition_asks_for_the_paste(self):
        with mock.patch.object(D, '_editions_for', return_value=[]):
            p = D.plan('2031-01-01', include_ops=False)
        self.assertFalse(p.tasks)
        self.assertTrue(any('paste' in x for x in p.person))


class RealPhotosFirst(_Newsroom):
    """D92 point 3: nobody generates a picture the editor was not asked about."""

    def pic(self, p):
        return [t for t in p.tasks if t.agent == 'picture-editor']

    def test_an_unasked_mukhya_is_a_question_for_the_editor(self):
        p, _ = self.plan_for([story(segment='mukhya', photo_plan='')])
        self.assertFalse(self.pic(p))
        self.assertTrue(any('real photo, or generate?' in x for x in p.person))

    def test_an_unasked_speed_story_is_asked_too_but_optional(self):
        p, _ = self.plan_for([story(segment='speed', photo_plan='')])
        self.assertFalse(self.pic(p))
        ask = [x for x in p.person if 'real photo, or generate?' in x]
        self.assertTrue(ask and 'optional' in ask[0])

    def test_generate_goes_to_the_picture_desk(self):
        p, _ = self.plan_for([story(segment='mukhya', photo_plan='ai')])
        self.assertEqual([t.story for t in self.pic(p)], [1])
        self.assertIn('brief', self.pic(p)[0].reason)

    def test_real_waits_for_the_editor(self):
        p, _ = self.plan_for([story(segment='mukhya', photo_plan='real')])
        self.assertFalse(self.pic(p))
        self.assertTrue(any('waiting for the editor' in x for x in p.person))

    def test_a_real_photo_is_checked_then_left_alone(self):
        p, path = self.plan_for([story(segment='mukhya', photo_plan='real',
                                       photo=photo())])
        self.assertIn('crops', self.pic(p)[0].reason)
        D.write_receipt('picture-editor', path, 'PASS', 'ok', story=1)
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertFalse(self.pic(p))

    def test_a_brief_filed_then_the_picture_arrives(self):
        p, path = self.plan_for([story(segment='mukhya', photo_plan='ai')])
        D.write_receipt('picture-editor', path, 'PASS', 'brief', story=1)
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertFalse(self.pic(p))
        self.edition([story(segment='mukhya', photo_plan='ai',
                            photo=photo(nature='ai', approved_by='Gautam'))])
        p = D.Plan('2026-09-30'); D._edition_tasks(p, path)
        self.assertIn('generated', self.pic(p)[0].reason)

    def test_saara_never_needs_a_picture(self):
        p, _ = self.plan_for([story(segment='saara', photo_plan='')])
        self.assertFalse(self.pic(p))
        self.assertFalse(any('generate' in x for x in p.person))


class AfterTheRender(_Newsroom):

    def outdir(self, findings=(), files=()):
        out = os.path.join(self.tmp.name, 'out', '2026-09-30')
        os.makedirs(os.path.join(out, '_review'), exist_ok=True)
        with open(os.path.join(out, 'review_report.json'), 'w') as fh:
            json.dump({'findings': list(findings)}, fh)
        for f in files:
            with open(os.path.join(out, f), 'w') as fh:
                fh.write('x')
        return out

    def test_one_inspector_per_format(self):
        out = self.outdir(files=('roundup.mp4', 'roundup_cover.jpg',
                                 'saara_01.jpg', 'saara_02.jpg',
                                 'mukhya_1_01.jpg', 'mukhya_3_01.jpg',
                                 '_review/roundup_t07.jpg', 'build.log'))
        p = D.Plan('2026-09-30'); D._package_tasks(p, out)
        parts = sorted(t.part for t in self.of(p, 'package-inspector'))
        self.assertEqual(parts, ['mukhya_1', 'mukhya_3', 'roundup', 'saara'])
        self.assertTrue(all(t.wave == 3 for t in p.tasks))
        D.write_receipt('package-inspector', out, 'PASS', 'ok', part='saara')
        p = D.Plan('2026-09-30'); D._package_tasks(p, out)
        self.assertNotIn('saara', [t.part for t in self.of(p, 'package-inspector')])

    def test_the_caption_desk_audits_after_render_only(self):
        p, _ = self.plan_for([story()])
        self.assertFalse(self.of(p, 'social-writer'))
        out = self.outdir(files=('saara_caption.txt',))
        p = D.Plan('2026-09-30'); D._package_tasks(p, out)
        self.assertEqual(len(self.of(p, 'social-writer')), 1)

    def test_a_held_gate_calls_the_doctor_who_names_the_owners(self):
        out = self.outdir(findings=[
            {'code': 'LAW-01', 'severity': 'fail'},
            {'code': 'IMG-04', 'severity': 'fail'},
            {'code': 'PUB-08', 'severity': 'warn'}], files=('saara_01.jpg',))
        p = D.Plan('2026-09-30'); D._package_tasks(p, out)
        doc = self.of(p, 'gate-doctor')
        self.assertEqual(len(doc), 1)
        self.assertTrue(doc[0].urgent)
        self.assertIn('legal-standards', doc[0].reason)
        self.assertIn('picture-editor', doc[0].reason)
        # the owners are not launched in the same wave as the doctor
        self.assertFalse(self.of(p, 'legal-standards'))
        self.assertFalse(self.of(p, 'picture-editor'))
        self.assertFalse(any('sign_off' in x for x in p.person))

    def test_a_clean_gate_asks_for_the_sign_off(self):
        out = self.outdir(files=('saara_01.jpg',))
        p = D.Plan('2026-09-30'); D._package_tasks(p, out)
        self.assertFalse(self.of(p, 'gate-doctor'))
        self.assertTrue(any('sign_off.py' in x for x in p.person))


class OpsAreNotProduction(_Newsroom):

    def test_ops_never_enter_a_wave(self):
        p = D.Plan('2026-09-30')
        p.add('systems-steward', 'ops', 0, 'weekly', 'logs/x.md')
        p.add('planning-editor', 'ops', 0, 'weekly', 'inbox/w.md')
        p.add('fact-checker', 'reactive', 1, 'x', 'e.json', story=1)
        self.assertEqual([t.agent for w in p.waves().values() for t in w],
                         ['fact-checker'])
        self.assertEqual(len(p.ops), 2)
        self.assertIn('ops (not on the production path', D.brief(p))


class TheCorrectionsDeskRemembers(_Newsroom):

    def test_the_uncorrected_september_days_are_raised(self):
        from brand import corrections
        with mock.patch.object(corrections, 'overdue', return_value={}), \
                mock.patch.object(corrections, 'current', return_value={}):
            p = D.Plan('2026-09-30'); D._corrections_tasks(p)
        co = self.of(p, 'corrections-officer')
        self.assertTrue(co and '2026-09-23' in co[0].reason and co[0].wave == 0)
        logged = {f'c{i}': {'id': f'c{i}', 'about': d, 'state': 'published'}
                  for i, d in enumerate(D.KNOWN_ERRATA)}
        with mock.patch.object(corrections, 'overdue', return_value={}), \
                mock.patch.object(corrections, 'current', return_value=logged):
            p = D.Plan('2026-09-30'); D._corrections_tasks(p)
        self.assertFalse(self.of(p, 'corrections-officer'))
        self.assertIn('corrections-officer', body_of('corrections-officer'))
        self.assertIn('23 and 24 Sept 2026', body_of('corrections-officer'))


class WhichEditionsAreTheDays(unittest.TestCase):

    def test_greetings_and_series_are_not_the_days_news(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in ('editions/2026-09-30.json',
                        'editions/2026-09-30_evening.json',
                        'editions/special/2026-09-30.json',
                        'editions/greetings/2026-09-30.json',
                        'editions/kanoonu_kavacha/01_x.json',
                        'editions/2026-09-29.json'):
                os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
                open(os.path.join(tmp, rel), 'w').close()
            with mock.patch.object(D, 'ROOT', tmp):
                got = [os.path.relpath(p, tmp) for p in D._editions_for('2026-09-30')]
        self.assertEqual(sorted(got), ['editions/2026-09-30.json',
                                       'editions/2026-09-30_evening.json',
                                       'editions/special/2026-09-30.json'])


class TheReactiveHookFiresOnRealRunsOnly(unittest.TestCase):
    """It fired on a heredoc that merely mentioned verify.py, the first day
    it was live. A reactive trigger that cries wolf gets ignored."""

    def test_runs_and_mentions(self):
        m = cli()
        cases = {
            'cd "/x" && python3 render.py editions/a.json --only saara': True,
            'python3 scripts/fact_check.py editions/a.json': True,
            'python3 scripts/verify.py editions/a.json --story 1 --by X': True,
            'python3 scripts/intake.py source editions/a.json --story 1': True,
            'python3 scripts/fetch_daily_news.py': False,
            'python3 scripts/draft_edition.py': False,
            'python3 render.py --check editions/a.json': False,
            "cat > t.py <<'EOF'\nverify.py render.py\nEOF": False,
            'grep -n render.py docs/x.md': False,
            'python3 scripts/correction.py status': False,
            'python3 -m unittest tests.test_dispatch': False,
        }
        for cmd, want in cases.items():
            self.assertEqual(m.ran_pipeline(cmd), want, cmd)


class TheHookSpeaksOnlyWhenTheBoardMoved(unittest.TestCase):
    """Exit 2 on every render interrupted the work to repeat the same list."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(D, 'RECEIPTS', os.path.join(self.tmp.name, 'r'))
        p.start()
        self.addCleanup(p.stop)
        self.m = cli()

    def run_hook(self, tasks):
        plan = D.Plan('2026-09-30')
        plan.tasks = list(tasks)
        event = json.dumps({'tool_input': {
            'command': 'python3 scripts/fact_check.py editions/a.json'}})
        err = io.StringIO()
        with mock.patch.object(self.m.D, 'plan', return_value=plan), \
                mock.patch.object(sys, 'stdin', io.StringIO(event)), \
                mock.patch.object(sys, 'stderr', err):
            return self.m._hook_post_bash(), err.getvalue()

    def test_same_board_twice_is_silent(self):
        t = D.Task('fact-checker', 'reactive', 1, 'x', 'e.json', 1)
        self.assertEqual(self.run_hook([t])[0], 2)
        self.assertEqual(self.run_hook([t]), (0, ''))
        self.assertTrue(os.path.exists(os.path.join(D.RECEIPTS, '.last_hook')))

    def test_a_new_task_speaks_again(self):
        a = D.Task('fact-checker', 'reactive', 1, 'x', 'e.json', 1)
        b = D.Task('legal-standards', 'reactive', 1, 'x', 'e.json', 1)
        self.assertEqual(self.run_hook([a])[0], 2)
        code, msg = self.run_hook([a, b])
        self.assertEqual(code, 2)
        self.assertIn('legal-standards', msg)

    def test_an_empty_board_is_silent_and_resets(self):
        a = D.Task('fact-checker', 'reactive', 1, 'x', 'e.json', 1)
        self.assertEqual(self.run_hook([a])[0], 2)
        self.assertEqual(self.run_hook([])[0], 0)
        self.assertEqual(self.run_hook([a])[0], 2)


class ARenderNeverOverwritesAnotherEdition(unittest.TestCase):
    """2026-09-25: the ಕಾನೂನು ಕವಚ explainer, dated the same day, rendered into
    out/2026-09-25 and replaced that day's news carousel. D90."""

    def test_a_folder_stamped_for_another_edition_is_refused(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            ed = os.path.join(tmp, 'ed.json')
            with open(ed, 'w', encoding='utf-8') as fh:
                json.dump({'schema_version': 4,
                           'date': '2026-09-30T07:00:00+05:30', 'edition_no': 1,
                           'stories': [dict(story(verified_by='Test Editor'),
                                            segment='saara')] * 2},
                          fh, ensure_ascii=False)
            out = os.path.join(tmp, 'out')
            os.makedirs(out)
            with open(os.path.join(out, '.edition'), 'w') as fh:
                fh.write('editions/some_other_edition.json\n')
            r = subprocess.run(
                [sys.executable, 'render.py', ed, '--out', out, '--still'],
                cwd=D.ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 1, r.stdout[-400:] + r.stderr[-400:])
            self.assertIn('would overwrite', r.stderr)
            self.assertFalse(any(f.endswith(('.jpg', '.mp4')) for f in os.listdir(out)))

    def test_the_dispatcher_does_not_inspect_a_foreign_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, '.edition'), 'w') as fh:
                fh.write('editions/x.json\n')
            self.assertEqual(D.owner_of(tmp), 'editions/x.json')


if __name__ == '__main__':
    unittest.main()


class TheDesksAreNotOptional(unittest.TestCase):
    """D95. 2026-09-27: the first ಸುದ್ದಿ ಸಾರ was approved with no desk having
    read it, and shipped a death in red, three wrong categories and two
    wording slips. The waves were advice; now the gate and the sign-off ask."""

    def setUp(self):
        import shutil
        self.stem = f'zz_d95_{os.getpid()}'
        self.tmp = tempfile.mkdtemp()
        self.ed = os.path.join(self.tmp, f'{self.stem}.json')
        st = dict(story(verified_by='Test Editor'), segment='saara',
                  category='civic')
        with open(self.ed, 'w', encoding='utf-8') as fh:
            json.dump({'schema_version': 4, 'date': '2026-09-30T07:00:00+05:30',
                       'edition_no': 1, 'stories': [st, dict(st)]}, fh,
                      ensure_ascii=False)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(shutil.rmtree, os.path.join(D.RECEIPTS, self.stem),
                        ignore_errors=True)

    def test_an_unread_edition_has_gaps_and_a_read_one_has_none(self):
        gaps = D.desk_gaps(self.ed)
        self.assertTrue(any(g.startswith('kannada-editor') for g in gaps), gaps)
        with open(self.ed, encoding='utf-8') as fh:
            stories = json.load(fh)['stories']
        for i, _ in enumerate(stories, 1):
            for agent in ('fact-checker', 'kannada-editor'):
                D.write_receipt(agent, self.ed, 'PASS', 'read', story=i)
        D.write_receipt('instagram-strategist', self.ed, 'PASS', 'plan')
        self.assertEqual(D.desk_gaps(self.ed), [])

    def test_changing_the_wording_reopens_the_kannada_desk(self):
        with open(self.ed, encoding='utf-8') as fh:
            data = json.load(fh)
        for i, _ in enumerate(data['stories'], 1):
            for agent in ('fact-checker', 'kannada-editor'):
                D.write_receipt(agent, self.ed, 'PASS', 'read', story=i)
        D.write_receipt('instagram-strategist', self.ed, 'PASS', 'plan')
        data['stories'][0]['headline'] += ' ಇಂದು'
        with open(self.ed, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        self.assertTrue(any('story 1' in g for g in D.desk_gaps(self.ed)))

    def test_nobody_signs_an_uninspected_package(self):
        import subprocess
        out = os.path.join(self.tmp, 'out')
        os.makedirs(out)
        for n in ('saara_01_cover.jpg', 'APPROVAL.md'):
            open(os.path.join(out, n), 'w').close()
        with open(os.path.join(out, 'review_report.json'), 'w') as fh:
            json.dump({'findings': []}, fh)
        self.assertTrue(D.inspection_gaps(out))
        r = subprocess.run([sys.executable, 'scripts/sign_off.py', out,
                            '--by', 'Test Editor'], cwd=D.ROOT,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('not been looked at', r.stderr)


class TheTeamRunsInBatchesAndTheReachDeskIsHeard(unittest.TestCase):
    """D97: fewer agent runs for the same checking, and one reach desk."""

    def setUp(self):
        import shutil
        self.stem = f'zz_d97_{os.getpid()}'
        self.tmp = tempfile.mkdtemp()
        self.ed = os.path.join(self.tmp, f'{self.stem}.json')
        st = dict(story(verified_by='Test Editor'), segment='saara',
                  category='civic')
        self.write([dict(st, headline=f'ಕುಂದಾಪುರ: ಸುದ್ದಿ {i}') for i in range(6)])
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(shutil.rmtree, os.path.join(D.RECEIPTS, self.stem),
                        ignore_errors=True)

    def write(self, stories):
        with open(self.ed, 'w', encoding='utf-8') as fh:
            json.dump({'schema_version': 4, 'date': '2026-09-30T07:00:00+05:30',
                       'edition_no': 1, 'stories': stories}, fh,
                      ensure_ascii=False)

    def plan(self):
        p = D.Plan(day='')
        D._edition_tasks(p, self.ed)
        return p

    def test_six_stories_are_one_run_per_desk_not_six(self):
        p = self.plan()
        runs = [r for rs in p.launches().values() for r in rs]
        fact = [r for r in runs if r['agent'] == 'fact-checker']
        kn = [r for r in runs if r['agent'] == 'kannada-editor']
        self.assertEqual(len(fact), 1)
        self.assertEqual(fact[0]['stories'], [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(kn), 1)
        # …but the gate still asks the per-story question
        self.assertEqual(len([t for t in p.tasks if t.agent == 'fact-checker']), 6)

    def test_a_batch_never_exceeds_the_limit(self):
        from brand.tokens import Limits
        st = json.load(open(self.ed, encoding='utf-8'))['stories'][0]
        self.write([dict(st, headline=f'ಕುಂದಾಪುರ: ಸುದ್ದಿ {i}')
                    for i in range(Limits.agent_batch_max + 2)])
        runs = [r for rs in self.plan().launches().values() for r in rs
                if r['agent'] == 'fact-checker']
        self.assertEqual(len(runs), 2)
        self.assertLessEqual(max(len(r['stories']) for r in runs),
                             Limits.agent_batch_max)

    def test_one_command_files_a_receipt_for_each_story_in_a_batch(self):
        import subprocess
        r = subprocess.run([sys.executable, 'scripts/dispatch.py', 'receipt',
                            '--agent', 'fact-checker', '--edition', self.ed,
                            '--story', '1', '2', '3', '--verdict', 'PASS',
                            '--file', '-'], cwd=D.ROOT, input='read',
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count('receipt filed'), 3)

    def test_the_reach_desk_is_due_once_and_a_copy_edit_does_not_reopen_it(self):
        def due():
            return [t for t in self.plan().tasks if t.agent == 'instagram-strategist']
        self.assertEqual(len(due()), 1)
        D.write_receipt('instagram-strategist', self.ed, 'PASS', 'plan')
        self.assertEqual(due(), [])
        data = json.load(open(self.ed, encoding='utf-8'))
        data['stories'][0]['headline'] += ' ಇಂದು'          # wording only
        self.write(data['stories'])
        self.assertEqual(due(), [], 'a Kannada edit must not send it round again')
        data['stories'][0]['segment'] = 'mukhya'            # a format change
        self.write(data['stories'])
        self.assertEqual(len(due()), 1)

    def test_it_waits_until_every_story_has_a_format(self):
        data = json.load(open(self.ed, encoding='utf-8'))
        data['stories'][0]['segment'] = ''
        self.write(data['stories'])
        self.assertEqual([t for t in self.plan().tasks
                          if t.agent == 'instagram-strategist'], [])
