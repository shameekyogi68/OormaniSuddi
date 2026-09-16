"""
The intake is a retriever, not a generator.
===========================================
Issue #2 of the board sheet, and the one every reviewer put first: the fetch
used to send bare headlines to a model and ask for three to five journalistic
sentences, which is a request to invent. D55 turned it into a tip sheet. This
suite asserts the two things that keep it one.

  * **Bodies.** Where a publisher serves the article, we fetch it, so the model
    is condensing five paragraphs rather than expanding a headline. Where it
    does not, the sheet SAYS "headline only" instead of quietly producing
    something that reads complete.

  * **Groundedness.** Every number, place and proper noun in a generated lead
    is checked against the text it was written from. This does not establish
    truth — nothing here can — but it points the editor at the two words that
    are not in anything we fetched, which is where an invented helpline number
    or hospital name lives.

See D59 and D63.
"""
from __future__ import annotations

import unittest

import contextlib
import io

from scripts.fetch_daily_news import (Tip, audit_groundedness, render_markdown,
                                      unsupported_tokens, EXTRACT_PROMPT,
                                      UNCHECKABLE, TEXT_MODEL, _PLACES)


def audit_quietly(tips):
    """audit_groundedness() reports to the editor's terminal, which is right
    in production and noise in a test run."""
    with contextlib.redirect_stdout(io.StringIO()):
        return audit_groundedness(tips)


SOURCE = ('ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ. ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ ನೀಡಿದೆ. '
          'ತಗ್ಗು ಪ್ರದೇಶಗಳಲ್ಲಿ ನೀರು ನಿಂತಿದೆ.')


class TheGroundednessPass(unittest.TestCase):

    def test_an_invented_casualty_figure_is_flagged(self):
        """The most dangerous thing a model can supply is a number."""
        flags = unsupported_tokens('ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ, 45 ಮಂದಿ ದಾಖಲು', SOURCE)
        self.assertIn('45', flags)

    def test_an_invented_helpline_number_is_flagged(self):
        """A reader in Byndoor rings whatever number the card prints."""
        flags = unsupported_tokens('ಸಹಾಯಕ್ಕೆ 1077 ಸಂಪರ್ಕಿಸಿ', SOURCE)
        self.assertIn('1077', flags)

    def test_an_invented_official_is_flagged(self):
        flags = unsupported_tokens('Heavy rain in Udupi, SP Rajendra said',
                                   'Heavy rain lashed Udupi district on Tuesday.')
        self.assertIn('Rajendra', flags)

    def test_a_case_ending_is_grammar_not_an_invented_fact(self):
        """Kannada agglutinates: the source says ಉಡುಪಿ, the lead says ಉಡುಪಿಯಲ್ಲಿ."""
        self.assertEqual(unsupported_tokens('ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', SOURCE), [])
        self.assertEqual(unsupported_tokens('ಜಿಲ್ಲಾಡಳಿತದ ಎಚ್ಚರಿಕೆ', SOURCE), [])

    def test_a_faithful_lead_is_not_flagged(self):
        self.assertEqual(
            unsupported_tokens('ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ',
                               SOURCE), [])

    def test_a_figure_that_is_in_the_source_survives(self):
        self.assertEqual(
            unsupported_tokens('ಉಡುಪಿಯಲ್ಲಿ 45 mm ಮಳೆ',
                               'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ 45 mm ಮಳೆ ದಾಖಲಾಗಿದೆ'), [])

    def test_a_short_stem_cannot_match_everything(self):
        """Below four characters a 'stem' matches anything and the check dies."""
        flags = unsupported_tokens('ಮಂಗಳೂರು ಬಂದರು', SOURCE)
        self.assertTrue(flags, 'a place the source never mentions slipped through')

    def test_nothing_is_flagged_when_there_is_no_source_to_check_against(self):
        """Silence is honest. A flag against nothing is noise."""
        self.assertEqual(unsupported_tokens('ಯಾವುದೋ ಸುದ್ದಿ', ''), [])


class TheTipSheetSaysWhatItHas(unittest.TestCase):

    def _tip(self, **kw) -> Tip:
        base = dict(headline='ಉಡುಪಿಯಲ್ಲಿ ಮಳೆ', source_name='ಉದಯವಾಣಿ',
                    source_url='https://example.test/a')
        base.update(kw)
        return Tip(**base)

    def test_a_headline_only_tip_admits_it(self):
        md = render_markdown([self._tip()], '2026-09-16')
        self.assertIn('HEADLINE ONLY', md)

    def test_a_full_article_tip_says_so_and_quotes_it(self):
        md = render_markdown(
            [self._tip(body=SOURCE, body_source='article')], '2026-09-16')
        self.assertIn('full article text', md)
        self.assertIn('From the article', md)

    def test_an_unsupported_word_reaches_the_editor_as_a_verify_flag(self):
        t = self._tip(body=SOURCE, body_source='article',
                      lead_kn='ಉಡುಪಿಯಲ್ಲಿ ಮಳೆ, 45 ಮಂದಿ ದಾಖಲು')
        audit_quietly([t])
        md = render_markdown([t], '2026-09-16')
        self.assertIn('VERIFY', md)
        self.assertIn('45', md)

    def test_the_sheet_never_calls_itself_copy(self):
        md = render_markdown([self._tip()], '2026-09-16')
        self.assertIn('TIPS, not copy', md)
        self.assertIn('verified_by', md,
                      'the sheet must point at the gate that will refuse it')

    def test_a_lead_identical_to_the_headline_is_not_audited(self):
        """Nothing was generated, so there is nothing to be ungrounded about."""
        t = self._tip(body=SOURCE, body_source='article',
                      lead_kn='ಉಡುಪಿಯಲ್ಲಿ ಮಳೆ')
        audit_quietly([t])
        self.assertEqual(t.unsupported, [])


class ThePromptCannotAskForInvention(unittest.TestCase):

    def test_the_prompt_forbids_supplying_what_the_text_lacks(self):
        p = EXTRACT_PROMPT.lower()
        for phrase in ('omit', 'do not supply', 'traceable'):
            self.assertIn(phrase, p,
                          f'the extraction prompt no longer says {phrase!r}; '
                          f'this is the instruction issue #2 was about')

    def test_the_prompt_handles_the_empty_text_case_explicitly(self):
        """The headline-only case is the one the whole design exists for."""
        self.assertIn('empty', EXTRACT_PROMPT.lower())
        self.assertIn('unchanged', EXTRACT_PROMPT.lower())

    def test_the_prompt_never_asks_for_journalistic_paragraphs(self):
        banned = ('5 ws', 'five ws', 'background causes', 'official statement',
                  'journalistic sentences', 'police findings')
        low = EXTRACT_PROMPT.lower()
        for b in banned:
            self.assertNotIn(b, low,
                             f'{b!r} is back in the prompt — that is issue #2')


class ItFlagsFactsAndNotGrammar(unittest.TestCase):
    """The first real run flagged 30 leads out of 32.

    Every one of those was Kannada grammar — a verb the lead used to say the
    thing, a case ending, a compound. A check that fires on everything is a
    check the editor stops reading, and then it protects nothing. These are
    the four causes, each asserted.
    """

    def test_a_derived_verb_is_not_an_invented_fact(self):
        """ವಂಚನೆ in the source, ವಂಚಿಸಲಾಗಿದೆ in the lead — and ರೂ. in the
        source, ರೂಪಾಯಿ in the lead, which is the same fact spelled out."""
        self.assertEqual(
            unsupported_tokens('ಲಕ್ಷಾಂತರ ರೂಪಾಯಿ ವಂಚಿಸಲಾಗಿದೆ',
                               'ಅಧಿಕ ಲಾಭದ ಆಮಿಷ: ಲಕ್ಷಾಂತರ ರೂ. ವಂಚನೆ'), [])

    def test_a_compound_built_on_a_source_word_is_supported(self):
        """ಮಳೆ in the source, ಮಳೆಯಾಗುವ in the lead."""
        self.assertEqual(
            unsupported_tokens('ಗಾಳಿ ಸಹಿತ ಮಳೆಯಾಗುವ ಸಾಧ್ಯತೆ',
                               'ಕರಾವಳಿಯಲ್ಲಿ ಗಾಳಿ ಸಹಿತ ಮಳೆ ಸಾಧ್ಯತೆ'), [])

    def test_a_latin_place_name_supports_its_kannada_spelling(self):
        """Coastal headlines are mixed script: "Udupi: ಅಧಿಕ ಲಾಭದ ಆಮಿಷ"."""
        self.assertEqual(
            unsupported_tokens('ಉಡುಪಿಯಲ್ಲಿ ವಂಚನೆ',
                               'Udupi: ಅಧಿಕ ಲಾಭದ ಆಮಿಷ ವಂಚನೆ'), [])

    def test_the_place_bridge_reuses_the_tts_lexicon(self):
        """One file, two uses — the TTS engine needed the same mapping."""
        self.assertTrue(_PLACES)
        for latin in ('udupi', 'kundapura', 'byndoor'):
            self.assertIn(latin, _PLACES)

    def test_a_kannada_lead_on_an_english_source_says_it_cannot_be_checked(self):
        """Google News hands us English. Flagging every Kannada word is true
        and useless; saying so points at the right action."""
        out = unsupported_tokens(
            'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ ಎಂದು ವರದಿಯಾಗಿದೆ',
            'Heavy rain lashed the district through Tuesday, officials said.')
        self.assertEqual(out, [UNCHECKABLE])

    def test_an_invented_fact_still_gets_through_all_of_that(self):
        """None of the softening may cost the thing this exists to catch."""
        src = 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ. ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ ನೀಡಿದೆ.'
        flags = unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಸಹಾಯಕ್ಕೆ 1077 ಸಂಪರ್ಕಿಸಿ', src)
        self.assertIn('1077', flags)

    def test_the_uncheckable_marker_is_not_counted_as_a_flag(self):
        t = Tip(headline='Heavy rain in Udupi', source_name='Google News',
                source_url='https://example.test/a',
                body='Heavy rain lashed the district on Tuesday.',
                body_source='article',
                lead_kn='ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ ಎಂದು ವರದಿ')
        audit_quietly([t])
        md = render_markdown([t], '2026-09-16')
        self.assertIn('Cannot be checked here', md)
        # "VERIFY" also appears in the standing instructions at the foot of
        # every sheet, so the assertion has to be about the TIP, not the file.
        tip = md.split('## 1.', 1)[1].split('---', 1)[0]
        self.assertNotIn('VERIFY', tip)


class TheModelIsNamedAndItsDeathIsLoud(unittest.TestCase):
    """gemini-2.5-flash was retired while this pipeline asked for it every
    morning. The only sign was one line in a log nobody reads, and the sheet
    looked completely normal while carrying no Kannada leads at all."""

    def test_the_model_is_configurable_without_editing_code(self):
        import os
        self.assertTrue(TEXT_MODEL)
        self.assertEqual(
            TEXT_MODEL, os.environ.get('OORMANI_TEXT_MODEL', TEXT_MODEL))

    def test_a_sheet_with_no_leads_says_so(self):
        import scripts.fetch_daily_news as F
        was = dict(F._EXTRACT_STATE)
        try:
            F._EXTRACT_STATE.update({'ran': False, 'error': 'model is retired'})
            md = render_markdown(
                [Tip(headline='ಪರೀಕ್ಷೆ', source_name='ಉದಯವಾಣಿ',
                     source_url='https://example.test/a')], '2026-09-16')
            self.assertIn('No Kannada leads were written', md)
            self.assertIn('model is retired', md)
        finally:
            F._EXTRACT_STATE.clear()
            F._EXTRACT_STATE.update(was)

    def test_a_sheet_with_leads_does_not_carry_the_warning(self):
        import scripts.fetch_daily_news as F
        was = dict(F._EXTRACT_STATE)
        try:
            F._EXTRACT_STATE.update({'ran': True, 'error': ''})
            md = render_markdown(
                [Tip(headline='ಪರೀಕ್ಷೆ', source_name='ಉದಯವಾಣಿ',
                     source_url='https://example.test/a',
                     lead_kn='ಪರೀಕ್ಷಾ ಸುದ್ದಿ')], '2026-09-16')
            self.assertNotIn('No Kannada leads were written', md)
        finally:
            F._EXTRACT_STATE.clear()
            F._EXTRACT_STATE.update(was)


if __name__ == '__main__':
    unittest.main()


class TheHeartbeat(unittest.TestCase):
    """D71: the scheduler is not ours to own, so the script records itself.

    The 06:05 job on this machine runs a script outside the repository. That
    is fine — what matters is not who starts the fetch but whether anybody
    finds out when it stops. The heartbeat is written by fetch_daily_news.py
    itself, so it works for a launchd job, a cron line, a manual run, or a
    replacement written next year by somebody who never read this file.
    """

    def setUp(self):
        import tempfile
        import scripts.fetch_daily_news as F
        self.F = F
        self.dir = tempfile.mkdtemp()
        self.was = F.HEARTBEAT
        F.HEARTBEAT = __import__('os').path.join(self.dir, 'last_fetch.json')

    def tearDown(self):
        import shutil
        self.F.HEARTBEAT = self.was
        shutil.rmtree(self.dir, ignore_errors=True)

    def _read(self):
        import json
        with open(self.F.HEARTBEAT, encoding='utf-8') as fh:
            return json.load(fh)

    def test_a_success_is_recorded_with_what_it_produced(self):
        self.F._heartbeat(True, counts={'tips': 32, 'full_articles': 12})
        d = self._read()
        self.assertTrue(d['ok'])
        self.assertEqual(d['counts']['tips'], 32)
        self.assertIn('at', d)

    def test_a_failure_is_recorded_with_why(self):
        self.F._heartbeat(False, reason='Only 2 tips (need 3+)')
        d = self._read()
        self.assertFalse(d['ok'])
        self.assertIn('need 3', d['reason'])

    def test_it_records_whether_leads_were_actually_written(self):
        """A sheet of raw headlines and a sheet of written leads look the same
        from outside. The heartbeat is where the difference is visible."""
        was = dict(self.F._EXTRACT_STATE)
        try:
            self.F._EXTRACT_STATE.update({'ran': False, 'error': 'retired'})
            self.F._heartbeat(True, counts={'tips': 5})
            self.assertFalse(self._read()['leads_written'])
            self.F._EXTRACT_STATE.update({'ran': True, 'error': ''})
            self.F._heartbeat(True, counts={'tips': 5})
            self.assertTrue(self._read()['leads_written'])
        finally:
            self.F._EXTRACT_STATE.clear()
            self.F._EXTRACT_STATE.update(was)

    def test_it_names_the_model_so_a_retirement_is_diagnosable(self):
        self.F._heartbeat(True, counts={})
        self.assertEqual(self._read()['text_model'], self.F.TEXT_MODEL)

    def test_it_never_raises_when_it_cannot_write(self):
        """A heartbeat that can fail a morning is worse than no heartbeat."""
        self.F.HEARTBEAT = '/nonexistent-root-dir/x/last_fetch.json'
        self.F._heartbeat(True, counts={})      # must not raise


class TheSchedulerIsNotOurs(unittest.TestCase):
    """D71, asserted as a property of the shipped scripts."""

    def test_the_installer_refuses_a_time_collision_by_default(self):
        import os
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'install_launchd.sh'), encoding='utf-8').read()
        self.assertIn('--force', src)
        self.assertIn('exit 1', src)

    def test_the_installer_reads_nothing_outside_the_repo(self):
        """AGENTS rule 8 is fail-closed. The collision check compares labels
        and schedules from launchctl and LaunchAgents, never a foreign script."""
        import os
        src = open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'install_launchd.sh'), encoding='utf-8').read()
        self.assertNotIn('run_oormani', src,
                         'the installer must not reach for a script outside '
                         'this repository, even to read it')
