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
                                      unsupported_tokens, EXTRACT_PROMPT)


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


if __name__ == '__main__':
    unittest.main()
