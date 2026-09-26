"""
Every figure and name we publish is in the text we were given. D63, D78, D84.
==========================================================================
`brand/grounding.py` is the comparison the fact desk runs between a line we
publish and the source text the editor pasted (D92). It does not establish
truth — nothing here can — but it points the editor at the two words that
are not in anything we hold, which is where an invented helpline number or
hospital name lives.

These tests moved here from the old intake suite when the scraper was
deleted; the comparison is the part worth keeping.
"""
from __future__ import annotations

import unittest

from brand.grounding import (unsupported_tokens, canon_figure, source_figures,
                             UNCHECKABLE, _PLACES, _FUNCTION_WORDS,
                             _month_bridge)


SOURCE = ('ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ. ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ ನೀಡಿದೆ. '
          'ತಗ್ಗು ಪ್ರದೇಶಗಳಲ್ಲಿ ನೀರು ನಿಂತಿದೆ.')


class TheGroundednessPass(unittest.TestCase):

    def test_an_invented_casualty_figure_is_flagged(self):
        """The most dangerous thing a model can supply is a number."""
        self.assertIn('45', unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ, 45 ಮಂದಿ ದಾಖಲು', SOURCE))

    def test_an_invented_helpline_number_is_flagged(self):
        self.assertIn('1077', unsupported_tokens('ಸಹಾಯಕ್ಕೆ 1077 ಸಂಪರ್ಕಿಸಿ', SOURCE))

    def test_an_invented_official_is_flagged(self):
        self.assertIn('Rajendra', unsupported_tokens(
            'Heavy rain in Udupi, SP Rajendra said',
            'Heavy rain lashed Udupi district on Tuesday.'))

    def test_a_case_ending_is_grammar_not_an_invented_fact(self):
        self.assertEqual(unsupported_tokens('ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', SOURCE), [])
        self.assertEqual(unsupported_tokens('ಜಿಲ್ಲಾಡಳಿತದ ಎಚ್ಚರಿಕೆ', SOURCE), [])

    def test_a_figure_that_is_in_the_source_survives(self):
        self.assertEqual(unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ 45 mm ಮಳೆ', 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ 45 mm ಮಳೆ ದಾಖಲಾಗಿದೆ'), [])

    def test_a_short_stem_cannot_match_everything(self):
        self.assertTrue(unsupported_tokens('ಮಂಗಳೂರು ಬಂದರು', SOURCE))

    def test_nothing_is_flagged_when_there_is_no_source(self):
        self.assertEqual(unsupported_tokens('ಯಾವುದೋ ಸುದ್ದಿ', ''), [])


class ItFlagsFactsAndNotGrammar(unittest.TestCase):

    def test_a_derived_verb_and_a_spelled_abbreviation(self):
        self.assertEqual(unsupported_tokens(
            'ಲಕ್ಷಾಂತರ ರೂಪಾಯಿ ವಂಚಿಸಲಾಗಿದೆ', 'ಅಧಿಕ ಲಾಭದ ಆಮಿಷ: ಲಕ್ಷಾಂತರ ರೂ. ವಂಚನೆ'), [])

    def test_a_compound_built_on_a_source_word(self):
        self.assertEqual(unsupported_tokens(
            'ಗಾಳಿ ಸಹಿತ ಮಳೆಯಾಗುವ ಸಾಧ್ಯತೆ', 'ಕರಾವಳಿಯಲ್ಲಿ ಗಾಳಿ ಸಹಿತ ಮಳೆ ಸಾಧ್ಯತೆ'), [])

    def test_a_latin_place_name_supports_its_kannada_spelling(self):
        self.assertEqual(unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ ವಂಚನೆ', 'Udupi: ಅಧಿಕ ಲಾಭದ ಆಮಿಷ ವಂಚನೆ'), [])

    def test_the_place_bridge_reuses_the_tts_lexicon(self):
        self.assertTrue(_PLACES)
        for latin in ('udupi', 'kundapura', 'byndoor'):
            self.assertIn(latin, _PLACES)

    def test_a_kannada_line_on_an_english_source_says_it_cannot_be_checked(self):
        out = unsupported_tokens(
            'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಭಾರಿ ಮಳೆ ಸುರಿದಿದೆ ಎಂದು ವರದಿಯಾಗಿದೆ',
            'Heavy rain lashed the district through Tuesday, officials said.')
        self.assertEqual(out, [UNCHECKABLE])

    def test_conjunctions_and_postpositions_are_not_facts(self):
        self.assertEqual(unsupported_tokens(
            'ಮಳೆ ಹಾಗೂ ಗಾಳಿ ಸಾಧ್ಯತೆ', 'ಮಳೆ, ಗಾಳಿ ಸಾಧ್ಯತೆ ಇದೆ.'), [])

    def test_a_case_marker_on_a_short_noun_is_not_a_new_claim(self):
        self.assertNotIn('ಸಭೆಗೆ', unsupported_tokens(
            'ಉಡುಪಿಯಲ್ಲಿ ಸಭೆಗೆ ಚಾಲನೆ', 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ ಸಭೆ ನಡೆಯಿತು.'))

    def test_a_month_the_source_abbreviated_is_the_same_month(self):
        self.assertEqual(unsupported_tokens(
            'ಸೆಪ್ಟೆಂಬರ್ 18 ರಂದು ಹೆಬ್ರಿಗೆ ಭೇಟಿ',
            'ಸೆ.18ರಂದು ಹೆಬ್ರಿಗೆ ಭೇಟಿ ನೀಡಲಿದ್ದಾರೆ.'), [])

    def test_the_month_bridge_reads_the_one_month_list(self):
        from brand.content import KN_MONTHS
        self.assertIn(KN_MONTHS[6].lower(), _month_bridge('ಜು.27ರವರೆಗೆ ಮಳೆ'))
        self.assertEqual(_month_bridge('ಯಾವ ತಿಂಗಳೂ ಇಲ್ಲ'), '')

    def test_no_stopword_carries_a_number(self):
        for w in _FUNCTION_WORDS:
            self.assertFalse(any(ch.isdigit() for ch in w), w)


class FiguresAreComparedAsFigures(unittest.TestCase):
    """2026-09-27. The fact desk BLOCKed "82.9" on the 26 Sept rain story
    although the kept source said "Byndoor recorded the highest rainfall at
    82.9 mm". Root cause: the source was normalised by turning punctuation
    into spaces, so the haystack held "82 9" and never "82.9"; every decimal
    and every Indian-grouped figure (10,00,754) failed the same way. The
    converse bug hid behind it: a bare figure passed as a SUBSTRING, so "5"
    was supported by "45"."""

    BYNDOOR = ('Over the last 24 hours, Byndoor recorded the highest rainfall '
               'at 82.9 mm, closely followed by Kundapur with 73.9 mm. Hebri '
               'received moderate rainfall of 45.1 mm.')

    def test_a_decimal_in_an_english_source_supports_a_kannada_line(self):
        out = unsupported_tokens(
            'ಉಡುಪಿ ಜಿಲ್ಲೆಯ ಬೈಂದೂರಿನಲ್ಲಿ ಗರಿಷ್ಠ 82.9 ಮಿ.ಮೀ ಮಳೆ ದಾಖಲಾಗಿದೆ.',
            self.BYNDOOR)
        self.assertNotIn('82.9', out)

    def test_a_decimal_in_a_same_script_source(self):
        self.assertEqual(unsupported_tokens(
            'Byndoor 82.9 mm', self.BYNDOOR), [])

    def test_indian_grouping_and_thousands_commas(self):
        src = 'Udupi has 10,00,754 voters, of whom 4,84,236 are men.'
        self.assertEqual(unsupported_tokens('Udupi 10,00,754 voters', src), [])
        self.assertEqual(unsupported_tokens('Udupi 1000754 voters', src), [])

    def test_kannada_digits_are_the_same_figure(self):
        self.assertEqual(unsupported_tokens('Byndoor ೮೨.೯ mm', self.BYNDOOR), [])

    def test_a_figure_inside_a_longer_number_is_not_support(self):
        self.assertIn('5', unsupported_tokens('Hebri 5 mm', self.BYNDOOR))
        self.assertIn('82', unsupported_tokens('Byndoor 82 mm', self.BYNDOOR))

    def test_a_rounded_figure_still_needs_a_quote(self):
        """10.01 ಲಕ್ಷ is a rounding of 10,00,754 — the fact ledger's job."""
        self.assertIn('10.01', unsupported_tokens(
            'Udupi 10.01 lakh voters', 'Udupi has 10,00,754 voters.'))

    def test_a_spelled_number_is_the_same_figure(self):
        src = 'Rain is predicted for the next four to five days.'
        self.assertEqual(unsupported_tokens('Rain for 4 to 5 days', src), [])

    def test_canonical_forms(self):
        self.assertEqual(canon_figure('82.90'), '82.9')
        self.assertEqual(canon_figure('09'), '9')
        self.assertEqual(canon_figure('1,20,000'), '120000')
        self.assertEqual(canon_figure('೨೦೨೬'), '2026')
        self.assertIn('9', source_figures('on 25.09.2026'))


if __name__ == '__main__':
    unittest.main()
