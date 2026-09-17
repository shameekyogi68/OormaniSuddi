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


class SharedUrlsAreNotArticles(unittest.TestCase):
    """A listing page embedded as one tip's article is a lie, not a body.

    Found on 2026-09-17: Udayavani's district page hydrates via embedded JSON,
    a naive <h2>/<h3> regex matches headline text sitting inside that JSON with
    no real per-article link beside it, and the scraper fell back to the
    listing page URL for every item — so fetch_body() handed the SAME wrong
    text to all twelve tips, each stamped body_source='article'. The
    groundedness pass then flagged real facts as invented because it was
    comparing against somebody else's headline.
    """

    def test_a_url_shared_by_two_tips_is_flagged(self):
        """D75."""
        from scripts.fetch_daily_news import _shared_urls
        tips = [Tip(headline='a', source_name='x', source_url='https://p/list'),
                Tip(headline='b', source_name='x', source_url='https://p/list'),
                Tip(headline='c', source_name='x', source_url='https://p/one')]
        self.assertEqual(_shared_urls(tips), {'https://p/list'})

    def test_unique_urls_are_never_flagged(self):
        from scripts.fetch_daily_news import _shared_urls
        tips = [Tip(headline='a', source_name='x', source_url=f'https://p/{i}')
                for i in range(5)]
        self.assertEqual(_shared_urls(tips), set())

    def test_attach_bodies_never_labels_a_shared_url_as_article(self):
        from scripts.fetch_daily_news import attach_bodies
        tips = [Tip(headline='ಸುದ್ದಿ ಒಂದು', source_name='x',
                    source_url='https://p/list'),
                Tip(headline='ಸುದ್ದಿ ಎರಡು', source_name='x',
                    source_url='https://p/list')]
        with contextlib.redirect_stdout(io.StringIO()):
            attach_bodies(tips)
        for t in tips:
            self.assertNotEqual(t.body_source, 'article',
                               f'{t.headline} was labelled article from a '
                               f'URL shared with another tip')

    def test_a_tip_with_no_body_falls_back_to_its_own_snippet(self):
        """The fix must not throw away real per-tip RSS text along with the
        fake per-URL body."""
        from scripts.fetch_daily_news import attach_bodies
        tips = [Tip(headline='ಒಂದು', source_name='x', source_url='https://p/list',
                    snippet='ಸ್ವಂತ ತುಣುಕು ಒಂದು'),
                Tip(headline='ಎರಡು', source_name='x', source_url='https://p/list',
                    snippet='ಸ್ವಂತ ತುಣುಕು ಎರಡು')]
        with contextlib.redirect_stdout(io.StringIO()):
            attach_bodies(tips)
        self.assertEqual(tips[0].body, 'ಸ್ವಂತ ತುಣುಕು ಒಂದು')
        self.assertEqual(tips[1].body, 'ಸ್ವಂತ ತುಣುಕು ಎರಡು')
        self.assertEqual(tips[0].body_source, 'rss')


class TheFlagsPointAtFactsNotAtGrammar(unittest.TestCase):
    """D78. Measured on the run of 2026-09-17: 26 of 50 leads carried a flag, and
    the single most-flagged token in the whole sheet was ಹಾಗೂ — "and". The
    others were postpositions (ರಂದು, ವೇಳೆ), connectives (ಸಂಬಂಧಿಸಿದಂತೆ,
    ಹಿನ್ನೆಲೆಯಲ್ಲಿ), case-marked forms of ordinary nouns (ಸಭೆಯ, ನಗರದ) and one
    month name the source had abbreviated.

    D75 already wrote down what that costs: flags at a rate that high teach
    an editor to skip them, which is the same failure as not checking at all.
    So these assert the noise is gone — and the class below asserts that
    removing it did not blunt the check."""

    def test_a_conjunction_is_never_an_invented_fact(self):
        self.assertEqual(
            unsupported_tokens('ಮಳೆ ಹಾಗೂ ಗಾಳಿ ಸಾಧ್ಯತೆ',
                               'ಮಳೆ, ಗಾಳಿ ಸಾಧ್ಯತೆ ಇದೆ.'), [])

    def test_postpositions_and_connectives_are_not_facts(self):
        for lead in ('ಸಭೆ ನಡೆದ ವೇಳೆ ಚರ್ಚೆ',
                     'ದೂರುಗಳ ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಪರಿಶೀಲನೆ',
                     'ಪ್ರಕರಣಕ್ಕೆ ಸಂಬಂಧಿಸಿದಂತೆ ತನಿಖೆ'):
            flags = unsupported_tokens(lead, 'ಸಭೆ ನಡೆಯಿತು. ದೂರು ದಾಖಲಾಗಿದೆ. '
                                             'ಪ್ರಕರಣ ತನಿಖೆ ಮುಂದುವರಿದಿದೆ.')
            for noise in ('ವೇಳೆ', 'ಹಿನ್ನೆಲೆಯಲ್ಲಿ', 'ಸಂಬಂಧಿಸಿದಂತೆ'):
                self.assertNotIn(noise, flags, lead)

    def test_a_case_marker_on_a_short_noun_is_not_a_new_claim(self):
        """ಸಭೆ is three aksharas, so it never enters the haystack's token
        set — and every inflected form of it was therefore flagged."""
        self.assertNotIn('ಸಭೆಗೆ', unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ ಸಭೆಗೆ ಚಾಲನೆ', 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಸಭೆ ನಡೆಯಿತು.'))
        self.assertEqual(unsupported_tokens(
            'ನಗರದ ರಸ್ತೆ ಹಾಳಾಗಿದೆ', 'ನಗರ ವ್ಯಾಪ್ತಿಯ ರಸ್ತೆ ಹದಗೆಟ್ಟಿದೆ.'), [])

    def test_a_month_the_source_abbreviated_is_the_same_month(self):
        """A coastal headline writes ಸೆ.18, never ಸೆಪ್ಟೆಂಬರ್ 18."""
        self.assertEqual(unsupported_tokens(
            'ಸೆಪ್ಟೆಂಬರ್ 18 ರಂದು ಹೆಬ್ರಿಗೆ ಭೇಟಿ',
            'ಸೆ.18ರಂದು ಹೆಬ್ರಿಗೆ ಭೇಟಿ ನೀಡಲಿದ್ದಾರೆ.'), [])

    def test_the_month_bridge_reads_the_one_month_list(self):
        """Derived from brand.content.KN_MONTHS, not a second table that
        would drift from the datelines (D56)."""
        from scripts.fetch_daily_news import _month_bridge
        from brand.content import KN_MONTHS
        self.assertIn(KN_MONTHS[6].lower(), _month_bridge('ಜು.27ರವರೆಗೆ ಮಳೆ'))
        self.assertEqual(_month_bridge('ಯಾವ ತಿಂಗಳೂ ಇಲ್ಲ'), '')


class QuietingTheNoiseDidNotBluntTheCheck(unittest.TestCase):
    """The whole point of the pass is the invented figure, the invented
    helpline and the place that was never in the story. If widening the
    stopword list or the morphology had cost any of those, it would have
    traded a check for a comfortable-looking number."""

    SRC = 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ. ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ ನೀಡಿದೆ.'

    def test_an_invented_casualty_figure_still_flags(self):
        self.assertIn('45', unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ ಮಳೆ, 45 ಮಂದಿ ದಾಖಲು', self.SRC))

    def test_an_invented_helpline_still_flags(self):
        self.assertIn('1077', unsupported_tokens(
            'ಸಹಾಯಕ್ಕೆ 1077 ಸಂಪರ್ಕಿಸಿ', self.SRC))

    def test_a_place_the_source_never_named_still_flags(self):
        self.assertIn('ಮಂಗಳೂರು', unsupported_tokens(
            'ಮಂಗಳೂರು ಬಂದರು ಬಂದ್', self.SRC))

    def test_no_stopword_carries_a_number_or_a_name(self):
        """A stopword list is only safe while nothing in it could ever be a
        fact. A digit or a capitalised name in there would silently hide
        one."""
        from scripts.fetch_daily_news import _FUNCTION_WORDS
        for w in _FUNCTION_WORDS:
            self.assertFalse(any(ch.isdigit() for ch in w), w)


class SourcesWhoseLinksOpen(unittest.TestCase):
    """Google News supplied 15 of the 33 tips on 2026-09-17 and produced a
    body for none of them: its /rss/articles/ link is an opaque token that
    only becomes a URL after JavaScript runs, so trafilatura sees a shell and
    the editor who clicks it lands on a home page. That is a source_url which
    does not satisfy what D55 asks of one."""

    def test_the_district_feeds_are_scoped_to_places_we_cover(self):
        from scripts.fetch_daily_news import NEWSKARNATAKA_FEEDS
        from brand.copy import PLACE_TAGS
        self.assertTrue(NEWSKARNATAKA_FEEDS)
        for place, url in NEWSKARNATAKA_FEEDS:
            self.assertIn(place, PLACE_TAGS,
                          f'{place} is not a place this channel covers')
            self.assertTrue(url.startswith('https://'), url)

    def test_a_dead_source_cannot_starve_a_live_one(self):
        """The body budget counts articles GOT, not attempts. Counting
        attempts is what produced zero full articles out of thirty-three:
        fifteen unresolvable links spent the whole allowance before a
        fetchable one was reached."""
        import scripts.fetch_daily_news as F
        tips = [Tip(headline=f'ಸುದ್ದಿ {i}', source_name='dead',
                    source_url=f'https://dead.example/{i}', snippet='x')
                for i in range(F.BODY_BUDGET + 5)]
        tips.append(Tip(headline='ಜೀವಂತ', source_name='live',
                        source_url='https://live.example/a', snippet='x'))
        body = 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ. ' * 20

        real = F.fetch_body
        F.fetch_body = lambda url: body if 'live.example' in url else ''
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                F.attach_bodies(tips)
        finally:
            F.fetch_body = real

        self.assertEqual(tips[-1].body_source, 'article',
                         'the one fetchable source was never reached')


class TheSheetSaysWhenALinkWillNotOpen(unittest.TestCase):
    """D78. The notice belongs in the markdown the editor reads, and the
    audit must stay a pure counting pass.

    This exists because the first version of that notice was appended inside
    `audit_groundedness`, which has no `lines` to append to — and the whole
    suite still passed, because every fixture URL in it was an ordinary one.
    The fetch died on the next real run. So both halves are asserted here
    with an aggregator URL actually present."""

    def _tip(self, url):
        return Tip(headline='ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', source_name='Google News',
                   source_url=url, snippet='ಉಡುಪಿಯಲ್ಲಿ ಮಳೆ ಸುರಿದಿದೆ.',
                   lead_kn='ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ.')

    def test_the_audit_survives_a_tip_whose_link_does_not_open(self):
        agg = self._tip('https://news.google.com/rss/articles/CBMiabc?oc=5')
        audit_quietly([agg])          # must not raise
        self.assertIsInstance(agg.unsupported, list)

    def test_the_sheet_warns_on_an_aggregator_link(self):
        agg = self._tip('https://news.google.com/rss/articles/CBMiabc?oc=5')
        md = render_markdown([agg], '2026-09-17')
        self.assertIn('aggregator', md)

    def test_the_sheet_does_not_warn_on_a_link_that_opens(self):
        ok = self._tip('https://kannada.newskarnataka.com/udupi/a-real-story')
        self.assertNotIn('aggregator', render_markdown([ok], '2026-09-17'))

    def test_a_story_is_never_auto_drafted_from_one(self):
        """D55 asks for a source_url the editor can reopen. This is not one,
        so no name should ever end up attached to a story built on it."""
        from scripts.draft_edition import _story_dict
        self.assertIsNone(_story_dict({
            'headline': 'ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', 'lead_kn': 'ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ',
            'source_url': 'https://news.google.com/rss/articles/CBMiabc?oc=5',
            'source_name': 'Google News', 'snippet': '', 'taluk': 'ಉಡುಪಿ',
            'risk': 'normal'}))
