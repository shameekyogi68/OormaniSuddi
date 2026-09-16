"""
The BNS §356 guard, measured instead of assumed.
================================================
Section 21 of the system book says the legal detection is word-based and
incomplete. That was an honest admission with no number behind it — nobody knew
whether it missed one phrasing in fifty or one in three.

`tests/legal_corpus.json` is the number. Every row is a headline as a coastal
desk would really write it, labelled by hand. This suite asserts every one, and
prints the false-negative rate when something slips, so the admission in
Section 21 can be stated as a measurement rather than a feeling. See D61.

When a near-miss turns up in production, add it here FIRST, watch it fail, then
widen `content.GUILT_ASSERTING`. A corpus that only ever grows with successes
measures nothing.
"""
from __future__ import annotations

import json
import os
import unittest

from brand.content import (Story, Photo, ContentError, asserts_guilt,
                           OWN_REPORTING)

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'legal_corpus.json')


def load_cases() -> list[dict]:
    with open(CORPUS, encoding='utf-8') as fh:
        return json.load(fh)['cases']


def crime_story(headline: str, convicted: bool) -> Story:
    return Story(
        headline=headline,
        category='crime',
        deck='',
        convicted=convicted,
        sources=[OWN_REPORTING],
        photo=Photo('x.jpg', nature='representative',
                    credit='ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own'),
    )


class TheGuiltGuardIsMeasured(unittest.TestCase):

    def test_every_corpus_case_lands_where_it_is_labelled(self):
        missed: list[str] = []
        over: list[str] = []
        for case in load_cases():
            st = crime_story(case['headline'], case.get('convicted', False))
            try:
                st.validate()
                refused = False
            except ContentError:
                refused = True
            if case['blocks'] and not refused:
                missed.append(f"{case['id']}: {case['headline']}  ({case['why']})")
            if not case['blocks'] and refused:
                over.append(f"{case['id']}: {case['headline']}  ({case['why']})")

        total = len(load_cases())
        blocking = sum(1 for c in load_cases() if c['blocks'])
        msg = []
        if missed:
            rate = len(missed) / blocking
            msg.append(
                f'\nFALSE NEGATIVES — {len(missed)}/{blocking} '
                f'({rate:.0%}) of guilt-asserting lines were NOT refused:\n  '
                + '\n  '.join(missed)
                + '\n\nAdd the missing form to content.GUILT_ASSERTING. Do not '
                  'delete the corpus row.')
        if over:
            msg.append(
                f'\nFALSE POSITIVES — {len(over)} safe lines were refused:\n  '
                + '\n  '.join(over)
                + '\n\nAn over-eager guard costs a rewrite, which is cheap, but '
                  'a guard that refuses "ಆರೋಪ" copy trains editors to work '
                  'around it, which is not.')
        self.assertFalse(msg, ''.join(msg) + f'\n\n({total} cases)')

    def test_the_corpus_is_big_enough_to_mean_something(self):
        cases = load_cases()
        self.assertGreaterEqual(
            len(cases), 30,
            'a corpus this small cannot measure a false-negative rate')
        self.assertGreaterEqual(
            sum(1 for c in cases if c['blocks']), 15,
            'most of the value is in the lines that MUST be refused')
        self.assertGreaterEqual(
            sum(1 for c in cases if not c['blocks']), 10,
            'without safe lines the corpus cannot catch an over-eager guard')

    def test_every_case_has_a_reason_written_down(self):
        for c in load_cases():
            self.assertTrue(c.get('why', '').strip(),
                            f"{c['id']} has no 'why'; an unlabelled corpus row "
                            f'is a number nobody can argue with')

    def test_a_marker_clears_only_the_field_it_is_in(self):
        """The rule D29 rests on, asserted directly rather than by implication."""
        self.assertEqual(asserts_guilt('ಕೊಲೆ ಆರೋಪಿ ಬಂಧನ'), [])
        self.assertTrue(asserts_guilt('ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ'))

    def test_the_guard_covers_more_than_one_form_of_each_verb(self):
        """A word list carrying only the bare past is a list with a hole in it."""
        from brand.content import GUILT_ASSERTING
        for stem, forms in (('ಕೊಂದ', ('ಕೊಂದ', 'ಕೊಂದು')),
                            ('ಕದ್ದ', ('ಕದ್ದ',)),
                            ('ಹಲ್ಲೆ', ('ಹಲ್ಲೆ ಮಾಡಿದ', 'ಹಲ್ಲೆಗೈದ'))):
            for f in forms:
                self.assertIn(f, GUILT_ASSERTING,
                              f'{f!r} is a form a desk writes and the guard '
                              f'does not carry')


if __name__ == '__main__':
    unittest.main()
