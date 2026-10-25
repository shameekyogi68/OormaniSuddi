"""D132, D133 — the ಸುದ್ದಿ ಸಾರ reel: the default product, cut from its own voice, inside the
Reels chrome, no lines, and never an empty day.

These run without Chrome or the network: they hold the timeline arithmetic, the
copy each slot takes, how a figure is spoken, how words are placed inside a clip,
the safe-zone geometry the page is built on, the gate that reads the reel's own
report, and the wiring that makes the reel what `/daily-saara` produces. The page
itself is exercised by scripts/reel_check.py and reviewed as stills (D132).
"""
import contextlib
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import soundfile as sf

from brand import reel_speech as RS
from brand import saara_reel as R
from brand.content import ContentError, Edition, Story
from brand.tokens import CATEGORIES, Limits, Motion as M, ReelsChrome as RC

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'brand/saara_reel.html').read_text(encoding='utf-8')
(ROOT / 'build').mkdir(exist_ok=True)


def px(rule: str, prop: str) -> float:
    m = re.search(re.escape(rule) + r'\s*\{[^}]*?\b' + prop + r':\s*(-?\d+)px', PAGE)
    assert m, f'{rule} {prop} not found'
    return float(m.group(1))


def durs(n, head=3.0, body=5.0, intro=3.0, outro=2.5):
    d = {'intro': intro, 'outro': outro}
    for i in range(n):
        d[f'h{i}'], d[f'b{i}'] = head, body
    return d


class CutFromTheVoice(unittest.TestCase):
    def test_each_story_runs_from_its_change_to_the_end_of_its_read_line(self):
        d = {'intro': 3.0, 'outro': 2.5, 'h0': 2.0, 'b0': 8.0, 'h1': 3.0, 'b1': 9.5}
        tl = R._timeline(d, 2)
        s0, s1 = tl['stories']
        self.assertAlmostEqual(s0['B'], max(M.saara_reel_intro, M.saara_reel_hook_at + 3.0 + M.saara_reel_hook_hold), places=3)
        self.assertAlmostEqual(s0['headAt'], s0['B'] + M.saara_reel_lead, places=3)
        self.assertAlmostEqual(s0['bodyAt'], s0['headAt'] + 2.0 + M.saara_reel_gap, places=3)
        self.assertAlmostEqual(s1['B'], s0['bodyAt'] + 8.0 + M.saara_reel_tail, places=3)
        self.assertGreaterEqual(tl['T'], tl['outro'] + 0.55 + 2.5 + 0.6 - 1e-6)    # the last word ends before the fold
        self.assertEqual(tl['compress'], 0)

    def test_a_long_day_tightens_the_pauses_never_the_speech(self):
        n = 6
        natural = R._timeline(durs(n, 3.0, 5.2), n, cap=999)
        tight = R._timeline(durs(n, 3.0, 5.2), n, cap=Limits.saara_reel_max_seconds)
        self.assertEqual(natural['compress'], 0)
        self.assertGreater(natural['T'], Limits.saara_reel_max_seconds)
        self.assertEqual(tight['compress'], 1)
        self.assertLess(tight['T'], natural['T'])
        for s in tight['stories']:                              # the speech is exactly as long as measured
            self.assertEqual(s['bodyDur'], 5.2)
        # …and when even that is not enough the overage is reported, not hidden
        huge = R._timeline(durs(n, 5.0, 9.0), n, cap=Limits.saara_reel_max_seconds)
        self.assertGreater(huge['over'], 0)

    def test_a_row_lights_when_its_town_is_said(self):
        words = {'intro': [[0.0, 0.6], [0.6, 1.0], [1.2, 2.0], [2.0, 2.6]], 'intro_text': ['ಇಂದಿನ', 'ಸುದ್ದಿ,', 'ಕುಂದಾಪುರ', 'ಬೈಂದೂರು.']}
        tl = R._timeline(durs(3), 3, words, ['ಕುಂದಾಪುರ', 'ಬೈಂದೂರು', 'ಕಳವಾಡಿ'])
        self.assertAlmostEqual(tl['rowAt'][0], M.saara_reel_hook_at + 1.2, places=3)
        self.assertAlmostEqual(tl['rowAt'][1], M.saara_reel_hook_at + 2.0, places=3)
        self.assertGreater(tl['rowAt'][2], tl['rowAt'][1] - 1e-9)     # a town not in the hook still lights, after


class TheBudget(unittest.TestCase):
    def test_more_stories_get_less_each(self):
        self.assertGreater(R.budget(3)['support_chars'], R.budget(5)['support_chars'])
        self.assertGreater(R.budget(5)['support_chars'], R.budget(6)['support_chars'])
        self.assertGreaterEqual(R.budget(6)['support_words'], 5)

    def test_a_third_headline_line_is_warned_never_cut(self):
        copies = [dict(place_short='ಬೈಂದೂರು', head='x' * 40, body='ಒಂದು', notes=[]),
                  dict(place_short='ಕಳವಾಡಿ', head='y' * 20, body='ಒಂದು', notes=[])]
        w = R._warnings(copies, {'lines': [3, 2]})
        self.assertEqual(len(w), 1)
        self.assertIn('ಬೈಂದೂರು', w[0])
        self.assertIn(str(Limits.saara_reel_line_chars), w[0])

    def test_a_sentence_too_long_for_the_clock_is_named(self):
        copies = [dict(place_short='ಬೈಂದೂರು', head='ಚಿಕ್ಕ', body='ಅ ' * 90, notes=[])] * 5
        self.assertTrue(any('card sentence' in w for w in R._warnings(copies, {'lines': [2] * 5})))

    def test_an_over_cap_film_names_the_longest_story(self):
        copies = [dict(place_short=f'ಊರು{i}', say_head='ಅ' * 20, body='ಅ' * (10 if i != 2 else 90), head='ಅ', notes=[])
                  for i in range(4)]
        w = R._warnings(copies, {'lines': [2] * 4}, dict(over=6.0, seconds=65.0, compress=1, natural=70.0, timing=[]))
        self.assertTrue(any('story 3' in x and 'Shorten' in x for x in w))

    def test_the_limits_agree_with_the_house(self):
        self.assertLess(Limits.saara_reel_max_seconds, Limits.reel_fail_seconds)
        self.assertFalse(Limits.saara_carousel_default)


class WhatEachSlotSays(unittest.TestCase):
    def test_reel_line_is_shown_and_reel_support_is_read(self):
        st = Story(headline='ಉದ್ದದ ಮುದ್ರಣ ಶೀರ್ಷಿಕೆ', reel_line='ಚಿಕ್ಕ ಸಾಲು', deck='ಉದ್ದದ ವಿವರ.',
                   reel_support='ಒಂದು ಪೂರ್ಣ ವಾಕ್ಯ.', location='ಬೈಂದೂರು', category='sport', segment='saara')
        c = R._story_copy(st)
        self.assertEqual(c['head'], 'ಚಿಕ್ಕ ಸಾಲು')
        self.assertEqual(c['body'], 'ಒಂದು ಪೂರ್ಣ ವಾಕ್ಯ.')
        self.assertTrue(c['say_head'].startswith('ಬೈಂದೂರು'))           # the voice names the town
        self.assertEqual(c['tone'], R.TONES['ember'])

    def test_without_reel_fields_the_story_own_sentences_are_used_and_the_gap_is_said(self):
        st = Story(headline='ಬೈಂದೂರು: ಕಡಲ್ಕೊರೆತ ತಡೆಗೆ ತುರ್ತು ಕ್ರಮ', location='ಬೈಂದೂರು', segment='saara', category='fisheries',
                   deck='ಕಡಲ್ಕೊರೆತ ತಡೆಯಲು ತುರ್ತು ಕ್ರಮ ಕೈಗೊಳ್ಳಲಾಗಿದೆ. ಮೀನುಗಾರರಿಗೆ ಎಚ್ಚರಿಕೆ ನೀಡಲಾಗಿದೆ.')
        c = R._copies([st, st])[0]
        self.assertEqual(c['head'], 'ಕಡಲ್ಕೊರೆತ ತಡೆಗೆ ತುರ್ತು ಕ್ರಮ')       # the town is the tag's job, not the headline's
        self.assertIn('ಕಡಲ್ಕೊರೆತ', c['body'])
        self.assertTrue(any('reel_line' in n for n in c['notes']))
        self.assertTrue(any('reel_support' in n for n in c['notes']))

    def test_the_card_takes_the_longest_sentence_that_fits_the_clock(self):
        short, long_ = 'ಮೆರವಣಿಗೆಯ ಶಾಂತಿ ಕಾಪಾಡಲು ಈ ಆದೇಶ ಹೊರಡಿಸಲಾಗಿದೆ.', 'ಅ' * 400
        st = Story(headline='ಊರು: ಸುದ್ದಿ', reel_line='ಚಿಕ್ಕ', location='ಊರು', segment='saara', deck=long_ + '.', points=[short, 'ಇನ್ನೊಂದು ಸಣ್ಣ ವಾಕ್ಯ ಇಲ್ಲಿದೆ.'])
        c = R._copies([st] * 5)[0]
        self.assertEqual(c['body'], short)                              # the longest of the ones that fit
        self.assertNotEqual(c['body'], long_ + '.')

    def test_every_category_has_a_tint(self):
        self.assertFalse(set(CATEGORIES) - set(R.CATEGORY_TONE) - {'culture'})

    def test_a_town_comes_from_location_then_the_headline_then_the_coast(self):
        self.assertEqual(R._place(Story(headline='x', location='ಕುಂದಾಪುರ, ಗಂಗೊಳ್ಳಿ, ಉಡುಪಿ')), ('ಕುಂದಾಪುರ · ಗಂಗೊಳ್ಳಿ', 'ಕುಂದಾಪುರ'))
        self.assertEqual(R._place(Story(headline='ಕೋಟ: ಸುದ್ದಿ'))[1], 'ಕೋಟ')
        self.assertEqual(R._place(Story(headline='ಸುದ್ದಿ ಮಾತ್ರ'))[1], 'ಕರಾವಳಿ')


class TheEditorIsAsked(unittest.TestCase):
    def test_a_weekday_that_is_not_the_editions_is_raised_never_rewritten(self):
        import datetime
        thursday = datetime.datetime(2026, 10, 22, 9, 0)          # a Thursday
        old = Story(headline='ಕುಂದಾಪುರ: ಮಂಗಳವಾರದ ಮೆರವಣಿಗೆ', location='ಕುಂದಾಪುರ', segment='saara')
        same = Story(headline='ಉಡುಪಿ: ಗುರುವಾರದ ಸಭೆ', location='ಉಡುಪಿ', segment='saara')
        none = Story(headline='ಕೋಟ: ಸುದ್ದಿ', location='ಕೋಟ', segment='saara')
        q = R.editor_questions(Edition(stories=[old, same, none], date=thursday))
        self.assertEqual(len(q), 1)
        self.assertIn('story 1', q[0])
        self.assertIn('ಮಂಗಳವಾರ', q[0])
        self.assertEqual(old.headline, 'ಕುಂದಾಪುರ: ಮಂಗಳವಾರದ ಮೆರವಣಿಗೆ')   # the copy is left exactly as the paste has it


class SpokenRight(unittest.TestCase):
    TABLE = {1: 'ಒಂದು', 7: 'ಏಳು', 10: 'ಹತ್ತು', 11: 'ಹನ್ನೊಂದು', 19: 'ಹತ್ತೊಂಬತ್ತು', 20: 'ಇಪ್ಪತ್ತು',
             21: 'ಇಪ್ಪತ್ತೊಂದು', 22: 'ಇಪ್ಪತ್ತೆರಡು', 23: 'ಇಪ್ಪತ್ತಮೂರು', 25: 'ಇಪ್ಪತ್ತೈದು', 26: 'ಇಪ್ಪತ್ತಾರು',
             27: 'ಇಪ್ಪತ್ತೇಳು', 28: 'ಇಪ್ಪತ್ತೆಂಟು', 29: 'ಇಪ್ಪತ್ತೊಂಬತ್ತು', 33: 'ಮೂವತ್ತಮೂರು', 48: 'ನಲವತ್ತೆಂಟು',
             99: 'ತೊಂಬತ್ತೊಂಬತ್ತು', 100: 'ನೂರು', 120: 'ನೂರ ಇಪ್ಪತ್ತು', 305: 'ಮುನ್ನೂರ ಐದು',
             2026: 'ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು', 5000: 'ಐದು ಸಾವಿರ'}

    def test_a_figure_and_its_ending_are_one_word_even_with_a_space_between(self):
        # a real day's headline: "ಹೆದ್ದಾರಿ 66 ರಲ್ಲಿ" was read "ಅರವತ್ತಾರು ರಲ್ಲಿ" — two words
        self.assertEqual(RS.spoken('ಹೆದ್ದಾರಿ 66 ರಲ್ಲಿ ಲಾರಿ'), RS.spoken('ಹೆದ್ದಾರಿ 66ರಲ್ಲಿ ಲಾರಿ'))
        self.assertIn('ಅರವತ್ತಾರರಲ್ಲಿ', RS.spoken('ಹೆದ್ದಾರಿ 66 ರಲ್ಲಿ'))
        self.assertEqual(RS.spoken('5 ಜನ'), 'ಐದು ಜನ.')                # not an ending: a word of its own

    def test_a_name_ending_in_a_consonant_gets_its_ending_after_a_joiner(self):
        self.assertEqual(RS.spoken('ಸ್ಟೀವನ್ಗೆ ದೀಕ್ಷೆ'), 'ಸ್ಟೀವನ್\u200cಗೆ ದೀಕ್ಷೆ.')
        self.assertEqual(RS.spoken('ಮಾರ್ಗಗಳು ಮತ್ತು ದುರ್ಗ'), 'ಮಾರ್ಗಗಳು ಮತ್ತು ದುರ್ಗ.')     # real conjuncts untouched

    def test_a_figure_is_said_as_kannada_words(self):
        for n, w in self.TABLE.items():
            self.assertEqual(RS.number_words(n), w, n)
        self.assertIsNone(RS.number_words(RS.MAX_NUMBER + 1))

    def test_a_suffix_joins_the_number_the_way_the_language_does(self):
        self.assertEqual(RS.spoken('33ನೇ ಶಾರದೋತ್ಸವ'), 'ಮೂವತ್ತಮೂರನೇ ಶಾರದೋತ್ಸವ.')
        self.assertEqual(RS.spoken('22ರಂದು ನಡೆಯಲಿದೆ'), 'ಇಪ್ಪತ್ತೆರಡರಂದು ನಡೆಯಲಿದೆ.')
        self.assertEqual(RS.spoken('5ಕ್ಕೆ ಸಭೆ'), 'ಐದಕ್ಕೆ ಸಭೆ.')
        self.assertEqual(RS.spoken('5 ಗ್ರಾಮ'), 'ಐದು ಗ್ರಾಮ.')
        self.assertEqual(RS.spoken('₹500 ದಂಡ'), 'ಐನೂರು ರೂಪಾಯಿ ದಂಡ.')

    def test_an_initial_ending_in_a_virama_loses_its_dot(self):
        from brand import voice
        self.assertEqual(voice._spoken('ಸಚಿವ ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ'), 'ಸಚಿವ ಎಚ್ ಸಿ ಬಾಲಕೃಷ್ಣ.')
        self.assertIn('ಇದೆ. ಎಚ್ಚರ', voice._spoken('ಮಳೆ ಇದೆ. ಎಚ್ಚರ'))      # a sentence end stays

    def test_what_may_still_be_misread_is_listed(self):
        self.assertEqual(RS.lint('33ನೇ ಶಾರದೋತ್ಸವ, ₹500 ದಂಡ, ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ'), [])
        self.assertIn('XYZ', RS.lint('ಇದು XYZ ಯೋಜನೆ'))             # an unknown Latin word is named
        self.assertTrue(RS.lint('ಇದು 123456789 ರೂಪಾಯಿ'))           # a figure past the table is named

    def test_words_are_weighed_by_what_is_spoken(self):
        self.assertEqual(RS.syllables('ಕ್ರಮ'), 2.0)                   # a conjunct is one beat
        self.assertGreater(RS.syllables('ಅನ್ನಸಂತರ್ಪಣೆ'), RS.syllables('ಹಾಗೂ'))
        self.assertGreater(RS.weight('22ರಂದು'), RS.weight('ರಂದು'))     # printed short, said long
        self.assertGreater(RS.weight('ಎಚ್.ಸಿ.'), 2.5)                 # said as two letters


class HearingTheVoiceBack(unittest.TestCase):
    """brand/reel_audit.py — Whisper writes Kannada its own way, so the comparison is on a phonetic skeleton."""

    def test_a_right_voice_scores_high_despite_the_transcribers_spelling(self):
        from brand import reel_audit as A
        said = 'ಮೂರು ದಿನ ಪೂಜೆ ಭಜನೆ ಹಾಗೂ ಅನ್ನಸಂತರ್ಪಣೆ ಶ್ರದ್ಧೆಯಿಂದ ನೆರವೇರಿತು'
        heard = 'ಮೂರು ದಿನ ಪೋಜೆ ಭಜನೆ ಹಾಗು ಅನ್ನ ಸಂತರ್ಪಣೆ ಶ್ರದ್ಧಿ ಇಂದ ನಿರವೇರಿತು'      # as Whisper actually wrote it
        r = A.compare(said, heard)
        self.assertGreaterEqual(r['similarity'], Limits.saara_reel_voice_warn)
        self.assertEqual(r['suspects'], [])

    def test_the_wrong_audio_scores_far_below_the_floors(self):
        from brand import reel_audit as A
        r = A.compare('ಗಣೇಶ್ ಪೂಜಾರಿ ಅವರ ಕೋಣಗಳು ಚಿನ್ನ ಗೆದ್ದಿವೆ', 'ಮೂರು ದಿನ ಪೋಜೆ ಭಜನೆ')
        self.assertLess(r['similarity'], Limits.saara_reel_voice_fail)
        self.assertGreaterEqual(len(r['suspects']), 3)

    def test_a_dropped_word_is_named(self):
        from brand import reel_audit as A
        r = A.compare('ಸಚಿವ ಬಾಲಕೃಷ್ಣ ಭರವಸೆ ನೀಡಿದ್ದಾರೆ', 'ಸಚಿವ ಭರವಸೆ ನೀಡಿದ್ದಾರೆ')
        self.assertIn('ಬಾಲಕೃಷ್ಣ', r['suspects'])

    def test_a_checker_that_is_away_never_holds_a_day(self):
        with mock.patch('importlib.util.find_spec', return_value=None):
            self.assertIn('unavailable', RS.audit([dict(label='x', wav='/nope.wav', text='ಅ')]))


class WordTimes(unittest.TestCase):
    SR = 48000

    def clip(self, parts):
        """parts: [(seconds, voiced?)] → a mono wav of noise bursts and silence."""
        rng = np.random.default_rng(3)
        x = np.concatenate([rng.standard_normal(int(self.SR * s)) * (0.2 if v else 0.0) for s, v in parts])
        fd, name = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        sf.write(name, x, self.SR)
        self.addCleanup(os.unlink, name)
        return Path(name)

    def test_the_pause_belongs_to_the_comma_and_the_words_split_there(self):
        wav = self.clip([(0.9, True), (0.3, False), (0.9, True)])
        t, how = RS.word_times(wav, 'ಕಕಕ ಕಕ, ಕಕಕ ಕಕ.')
        self.assertEqual(how, 'measured')
        self.assertLess(t[1][1], 1.0)                                    # "…ಕಕ," ends before the pause
        self.assertGreater(t[2][0], 1.15)                                # the next word starts after it
        self.assertTrue(all(b > a for a, b in t))
        self.assertTrue(all(t[k][1] <= t[k + 1][0] + 1e-6 for k in range(3)))

    def test_a_pause_that_is_not_where_the_words_say_falls_back_to_an_even_split_of_the_speech(self):
        wav = self.clip([(1.8, True), (0.3, False), (0.1, True)])        # the "pause" is at the very end
        t, how = RS.word_times(wav, 'ಕಕ, ಕಕ ಕಕ ಕಕ ಕಕ ಕಕ ಕಕ ಕಕ.')
        self.assertTrue(all(b > a for a, b in t))                        # still a clean, ordered timeline
        self.assertLessEqual(t[-1][1], 2.3)

    def test_silence_is_not_trusted(self):
        wav = self.clip([(2.0, False)])
        t, how = RS.word_times(wav, 'ಕಕ ಕಕ ಕಕ')
        self.assertEqual(how, 'even')
        self.assertEqual(len(t), 3)


class Guards(unittest.TestCase):
    def test_the_card_sentence_is_read_alone_so_it_is_guarded_alone(self):
        kw = dict(category='crime', segment='saara', location='ಬ್ರಹ್ಮಾವರ', sources=['x'], source_urls=['https://x.in/a'])
        with self.assertRaises(ContentError) as cx:
            Story(headline='ಬ್ರಹ್ಮಾವರ: ಆರೋಪಿ ಬಂಧನ', reel_line='ಆರೋಪಿ ಬಂಧನ', reel_support='ಅವನು ಹೆತ್ತವರನ್ನು ಕೊಂದ.', **kw).validate()
        self.assertIn('reel_support', str(cx.exception))
        with self.assertRaises(ContentError):                           # and under any other category
            Story(headline='ಉಡುಪಿ: ಸುದ್ದಿ', reel_line='ಸುದ್ದಿ', reel_support='ಅವನು ಲಂಚ ಪಡೆದ.', category='civic',
                  segment='saara', location='ಉಡುಪಿ', sources=['x'], source_urls=['https://x.in/a']).validate()

    def test_the_fact_and_copy_desks_read_the_card_sentence(self):
        from brand import dispatch, factcheck
        self.assertIn('reel_support', factcheck.FIELDS)
        self.assertIn('reel_support', dispatch.FACT_FIELDS)

    def test_the_gate_checks_the_card_sentence_for_glyphs_and_markers(self):
        src = (ROOT / 'brand/review.py').read_text(encoding='utf-8')
        self.assertIn("('reel_support', st.reel_support)", src)


class InsideTheReelsChrome(unittest.TestCase):
    def test_nothing_readable_under_the_header_the_rail_or_the_caption(self):
        self.assertGreaterEqual(px('#mast', 'top'), RC.top)
        self.assertGreaterEqual(px('.chip', 'top'), RC.top)
        self.assertLessEqual(px('#card', 'left') + px('#card', 'width'), RC.rail_x)
        self.assertLessEqual(Limits.saara_reel_line_chars, Limits.reel_line_chars)
        self.assertIn('SAFE_BOTTOM = 1480', PAGE)
        self.assertLess(1480, RC.bottom)
        self.assertIn('x: 220, y: 1016, w: 640', PAGE)                  # the follow button: 220 + 640 < rail
        self.assertLessEqual(220 + 640, RC.rail_x)
        # a headline that runs below the rail's top is set narrower, so it clears the rail
        self.assertIn('[110, 3, 848]', PAGE)
        self.assertLessEqual(px('.head', 'left') + 848, RC.rail_x)
        self.assertIn('RAIL_Y = 856', PAGE)
        self.assertLessEqual(856, RC.rail_top)

    def test_the_page_reports_what_does_not_fit(self):
        for must in ('does not fit above the card', 'runs under the Reels caption area',
                     'wider than the card', 'title is not inside its frame', 'wider than the frame'):
            self.assertIn(must, PAGE)

    def test_the_cover_scales_to_the_number_of_stories(self):
        self.assertIn('layoutCover(k)', PAGE)
        self.assertIn('var(--k, 1)', PAGE)


class NoLines(unittest.TestCase):
    def test_no_rules_borders_or_underlines(self):                       # D128: the owner's rule
        css = PAGE.split('<style>')[1].split('</style>')[0]
        for bad in ('border:', 'border-top', 'border-bottom', 'border-left', 'text-decoration', '<hr'):
            self.assertNotIn(bad, css + PAGE.split('</style>')[1].split('<script>')[0])


class TheSounds(unittest.TestCase):
    def test_every_effect_the_reel_plays_is_registered_and_the_house_set_is_always_there(self):
        # the house set is the fallback (D135): it must exist and be allowed; a licensed slot must be allowed too
        from brand import music
        allowed = music.allowed_paths('sfx')
        for name in ('whoosh', 'tick', 'open', 'outro', 'pop', 'press'):
            self.assertTrue((ROOT / 'assets/sfx' / f'{name}.wav').exists(), name)
            self.assertIn(f'assets/sfx/{name}.wav', allowed, name)
            path, _ = R._sfx(name)
            self.assertIn(str(path.relative_to(ROOT)), allowed, name)
        src = (ROOT / 'brand/saara_reel.py').read_text(encoding='utf-8')
        for name in ('pop', 'press', 'tick', 'whoosh'):
            self.assertIn(f"fx_add('{name}'", src)

    def test_the_set_is_rebuilt_to_the_same_bytes(self):
        from brand import sfx
        left, right = sfx.pop()
        again, _ = sfx.pop()
        self.assertTrue(np.array_equal(left, again))


class Wired(unittest.TestCase):
    def test_render_makes_the_reel_by_default_and_the_carousel_only_when_asked(self):
        src = (ROOT / 'render.py').read_text(encoding='utf-8')
        self.assertIn("'--carousel'", src)
        self.assertIn('saara_reel.make(sub, outdir)', src)
        self.assertIn('Limits.saara_carousel_default', src)
        from render import FORMAT_FILES
        for name in ('reel_saara.mp4', 'reel_saara_cover.jpg', 'reel_saara_youtube.txt', 'saara_01_cover.mp4', 'saara_caption.txt'):
            self.assertTrue(FORMAT_FILES['saara'].search(name), name)

    def _edition(self):
        ed = Edition.load(str(ROOT / 'tests/fixture_edition.json'))
        from dataclasses import replace
        return replace(ed, stories=ed.segment('saara'))

    def _run(self, make):
        import render
        ed = self._edition()
        calls = []
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as out, \
                mock.patch.object(render.TP, 'render', side_effect=lambda *a, **k: calls.append(a) or []), \
                mock.patch('brand.saara_reel.make', side_effect=make), contextlib.redirect_stdout(io.StringIO()):
            render.render_edition(ed, out, ['saara'], animate=True)
            files = sorted(os.listdir(out))
        return calls, files

    def test_a_reel_that_cannot_be_made_never_leaves_an_empty_day(self):
        def boom(*a, **k):
            raise R.ReelError('the google voice failed 3 times')
        calls, files = self._run(boom)
        self.assertEqual(len(calls), 1)                                  # the carousel was made instead
        self.assertIn('saara_caption.txt', files)

    def test_a_reel_that_is_made_means_no_carousel(self):
        ok = lambda *a, **k: dict(seconds=50.0, render_seconds=1.0, warnings=[], pronunciation={})   # noqa: E731
        calls, files = self._run(ok)
        self.assertEqual(calls, [])
        self.assertIn('reel_saara_youtube.txt', files)

    def test_the_plan_lists_the_reel_and_the_morning_is_its_own(self):
        from brand.copy import publishing_plan
        alone = publishing_plan(has_saara_reel=True, animated=True)
        self.assertEqual(alone[0].asset.split()[0], 'reel_saara.mp4')
        self.assertEqual(alone[0].at, Limits.saara_reel_slot)
        self.assertIn('YouTube Shorts', alone[0].platform)
        both = publishing_plan(has_saara=True, saara_last='saara_05_sources.jpg', animated=True, has_saara_reel=True)
        self.assertIn('saara_01_cover', both[0].asset)                   # the carousel keeps the morning
        self.assertEqual([s for s in both if s.asset.startswith('reel_saara')][0].at, Limits.saara_reel_slot_with_carousel)

    def test_only_what_a_person_looks_at_makes_a_format_due_for_inspection(self):
        from brand import dispatch
        with tempfile.TemporaryDirectory() as d:
            for n in ('saara_caption.txt', 'saara_copy.json', 'reel_saara.mp4', 'reel_saara_youtube.txt', 'roundup.mp4'):
                Path(d, n).write_text('x')
            self.assertEqual(sorted(dispatch.formats_in(d)), ['reel_saara', 'roundup'])
        self.assertTrue(dispatch._FORMAT_FILE.match('reel_saara_cover.jpg'))


class TheFilmSurvivesItsBrowser(unittest.TestCase):
    """Chrome is a browser on a busy Mac: closed under memory pressure, or crashed. Every frame is a pure
    function of its time, so a fresh Chrome picks up at the next frame and the film is the same film (D133)."""

    def render_with(self, die_after, fit_issue=None, forever=False, seconds=1.0):
        import asyncio, io
        from PIL import Image
        calls = []
        buf = io.BytesIO()
        Image.new('RGB', (64, 64), (10, 20, 30)).save(buf, 'PNG')
        png = buf.getvalue()

        async def fake_drive(page, profile, work, gate=None):
            calls.append(profile.name)
            me = len(calls)
            seen = {'n': 0}

            async def frame(t, fmt='png', quality=100):
                seen['n'] += 1
                if die_after is not None and (forever or me == 1) and seen['n'] > die_after:
                    raise RuntimeError('no close frame received or sent')
                return png
            laid = {'lines': [2], 'issues': [fit_issue] if fit_issue else []}
            if gate:
                gate(laid)
            return laid, await work(frame)

        def fake_build(edition, tmp, engine):
            tl = {'T': seconds, 'stories': [], 'outro': 0.2, 'compress': 0, 'natural': seconds, 'over': 0.0}
            return dict(copies=[], tl=tl, durs={}, timing=[], pron={}, hook='', page=tmp / 'x.html')

        def fake_mix(tl, clips, out):
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=%s' % seconds,
                            str(out)], check=True)

        d = tempfile.mkdtemp(dir=ROOT / 'build')
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        with mock.patch.object(R, '_drive', fake_drive), mock.patch.object(R, '_build', fake_build), \
                mock.patch.object(R, '_mix', fake_mix), mock.patch.object(R.time, 'sleep'), \
                contextlib.redirect_stdout(io.StringIO()):
            res = R.render(Edition(stories=[], date=__import__('datetime').datetime(2026, 1, 1)), os.path.join(d, 'r.mp4'))
        return calls, res, os.path.join(d, 'r.mp4')

    def test_a_chrome_that_dies_mid_film_is_replaced_and_the_film_is_whole(self):
        calls, res, mp4 = self.render_with(die_after=12)
        self.assertEqual(len(calls), 2)                                  # one fresh Chrome
        self.assertEqual(res['frames'], 30)
        n = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                            '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', mp4],
                           capture_output=True, text=True).stdout.strip()
        self.assertEqual(n, '30')                                        # not one frame lost or doubled

    def test_a_long_film_is_drawn_by_several_chromes_and_joined_whole(self):
        # 12 s → 360 frames → three stretches (Limits.saara_reel_workers); one Chrome dies in its stretch
        calls, res, mp4 = self.render_with(die_after=20, seconds=12.0)
        self.assertEqual(len(calls), 3 + 1)                              # three workers + one replacement
        self.assertEqual(res['frames'], 360)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                                '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', mp4],
                               capture_output=True, text=True).stdout.strip()
        self.assertEqual(probe, '360')                                   # joined without a frame lost or doubled

    def test_a_healthy_chrome_is_used_once(self):
        calls, _res, _mp4 = self.render_with(die_after=None)
        self.assertEqual(len(calls), 1)

    def test_copy_that_does_not_fit_is_never_retried(self):
        with self.assertRaises(R.ReelFitError):
            self.render_with(die_after=None, fit_issue='story 1: the headline does not fit above the card even at 60px')

    def test_a_browser_that_keeps_dying_is_named_not_looped_on(self):
        with self.assertRaises(R.ReelError) as cx:
            self.render_with(die_after=5, forever=True)
        self.assertIn('Chrome failed 3 times', str(cx.exception))
        self.assertNotIsInstance(cx.exception, R.ReelFitError)


class TheWrittenGrammar(unittest.TestCase):
    """D134: lines nobody reads before the voice says them are checked for what is certainly a mistake."""

    def test_each_certain_mistake_is_named(self):
        self.assertTrue(RS.grammar('ಇಂದಿನ ಸುದ್ದಿ, ಕೊಲ್ಲೂರು ಸೇರಿದಂತೆ.'))                 # ends on a connective
        self.assertTrue(RS.grammar('ಹೆದ್ದಾರಿ 66 ರಲ್ಲಿ ಲಾರಿ ಡಿಕ್ಕಿ'))                      # figure and ending apart
        self.assertTrue(RS.grammar('ಉಡುಪಿ ನಲ್ಲಿ ಸಭೆ'))                                     # an ending on its own
        self.assertTrue(RS.grammar('ಸಭೆ ಸಭೆ ನಡೆಯಿತು'))                                    # a word twice

    def test_a_name_in_u_before_ge_is_named(self):
        self.assertTrue(RS.grammar('ಕೋಟ, ಬರಗೂರುಗೆ ಕಾರಂತ ಪ್ರಶಸ್ತಿ ಪ್ರದಾನ'))          # ಬರಗೂರಿಗೆ
        self.assertEqual(RS.grammar('ಬರಗೂರಿಗೆ ಪ್ರಶಸ್ತಿ ಪ್ರದಾನ'), [])

    def test_good_lines_raise_nothing(self):
        for t in ('ಹೆದ್ದಾರಿ 66ರಲ್ಲಿ ಲಾರಿ ಡಿಕ್ಕಿ: ಸಾವು', 'ಕೊಲ್ಲೂರು ಮತ್ತು ಬೈಂದೂರು ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ.',
                  'ಗ್ರಾಮಸ್ಥರು ಹಾಗೂ ಪೋಷಕರು ಸನ್ಮಾನಿಸಿದರು.'):
            self.assertEqual(RS.grammar(t), [], t)

    def test_the_opening_and_every_line_go_through_it_and_are_printed(self):
        copies = [dict(place_short='ಅ', say_head='ಅ, ಹೆದ್ದಾರಿ 66 ರಲ್ಲಿ ಅಪಘಾತ', body='ಸಭೆ ನಡೆಯಿತು.', head='x', place='ಅ', notes=[])]
        self.assertEqual(R.spoken_script(copies)[0][0], 'the opening')
        self.assertTrue(any('grammar, story 1 headline' in w for w in R._warnings(copies, {'lines': [2]}, {})))


class OneRequestTwoClips(unittest.TestCase):
    """D134: a headline and its card asked for together (Gemini's free tier is 10 requests a day) and cut at the pause."""

    def pair(self, gap):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        rng = np.random.default_rng(3)
        x = np.concatenate([rng.normal(0, .2, int(48000 * 1.6)), np.zeros(int(48000 * gap)), rng.normal(0, .2, int(48000 * 1.2))])
        sf.write(d / 'src.wav', x, 48000)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(d / 'src.wav'), str(d / 'src.mp3')], check=True)

        def fake(text, out, engine, name, key):
            __import__('shutil').copy(d / 'src.mp3', out)
        with mock.patch.object(RS.voice, '_synth_one', fake), mock.patch.object(RS, 'audit', return_value={'unavailable': 'test'}):
            return RS.clip_pair('ಒಂದು ಎರಡು ಮೂರು ನಾಲ್ಕು', 'ಐದು ಆರು ಏಳು', d / 'h.wav', d / 'b.wav')

    def test_it_is_cut_at_the_pause(self):
        a, b = self.pair(0.45)
        self.assertAlmostEqual(a, 1.6, delta=0.25)
        self.assertAlmostEqual(b, 1.2, delta=0.25)

    def test_with_hardly_a_pause_it_still_cuts_near_the_boundary(self):
        a, b = self.pair(0.05)
        self.assertGreater(a, 1.0)
        self.assertGreater(b, 0.8)


class TheDatelineAndTheLastSlide(unittest.TestCase):
    """D141: a full stop after the town, and the follow button pressed as the words are said."""

    def test_the_town_is_a_sentence_of_its_own(self):
        c = R._story_copy(Story(headline='ಬೈಂದೂರು: ಮೊಬೈಲ್ ಕಳವು', reel_line='ಮೊಬೈಲ್ ಕದ್ದು ಹಣ ವರ್ಗಾಯಿಸಿದ ಆರೋಪ', location='ಬೈಂದೂರು',
                                category='civic', segment='saara'))
        self.assertTrue(c['say_head'].startswith('ಬೈಂದೂರು. ಮೊಬೈಲ್'))

    def test_the_press_lands_on_the_last_spoken_word(self):
        durs = {'intro': 3.0, 'outro': 2.6, 'h0': 3.0, 'b0': 3.0}
        words = {'outro': [[0.0, 0.5], [0.6, 1.2], [1.7, 2.1]]}                # the last word starts 1.7 s into the clip
        tl = R._timeline(durs, 1, words)
        self.assertAlmostEqual(tl['pressAt'], tl['outro'] + 0.55 + 1.7 - 0.12, places=2)
        self.assertAlmostEqual(R._timeline(durs, 1)['pressAt'], R._timeline(durs, 1)['outro'] + 1.7, places=2)   # unmeasured

    def test_a_clip_that_is_out_of_step_is_measured_and_named(self):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        rng = np.random.default_rng(9)
        clip = rng.normal(0, .2, 48000)
        sf.write(d / 'intro.wav', clip, 48000)
        mix = np.zeros(48000 * 4)
        mix[int(48000 * 0.55):int(48000 * 0.55) + 48000] = clip                  # sits at 0.55 s; the timeline says 0.30
        sf.write(d / 'mix.wav', mix, 48000)
        tl = {'stories': [], 'outro': 99.0}
        res = R._sync_check(tl, d, d / 'mix.wav')
        self.assertAlmostEqual(res['offsets_ms']['intro'], 250, delta=5)
        self.assertGreater(res['worst_ms'], 120)

    def test_the_gate_fails_a_reel_whose_audio_is_out_of_step(self):
        from brand.review import review
        g = TheGate()
        g.addCleanup = lambda *a, **k: None
        d = g.folder(dict(seconds=8.0, issues=[], pronunciation={}, timing=['measured'], sync=dict(worst_ms=300, offsets_ms={'outro': 300})))
        try:
            found = {f.code: f for f in review(d).findings}
        finally:
            __import__('shutil').rmtree(d, ignore_errors=True)
        self.assertEqual(found['VID-08'].severity, 'fail')


class TheBoundaryComesFromTheWords(unittest.TestCase):
    """D140: the cut between a headline and its card was the first long silence, which fell after the card's first words."""

    def test_the_words_not_the_first_pause_place_the_cut(self):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        rng = np.random.default_rng(4)
        # 0–1.6 s headline | 0.16 s thin gap | 1.76–2.6 s "name," | 0.45 s CLEAR gap | 3.05–5 s the rest of the card
        x = np.concatenate([rng.normal(0, .2, int(48000 * 1.6)), np.zeros(int(48000 * .16)), rng.normal(0, .2, int(48000 * .84)),
                            np.zeros(int(48000 * .45)), rng.normal(0, .2, int(48000 * 1.95))])
        full = d / 'p.wav'
        sf.write(full, x, 48000)
        a, b = 'ಒಂದು ಎರಡು ಮೂರು ನಾಲ್ಕು', 'ಡಾಕ್ಟರ್ ರಾಜೇಶ್ ಐದು ಆರು ಏಳು ಎಂಟು'
        words = [['ಒಂದು', 0, .4], ['ಎರಡು', .4, .8], ['ಮೂರು', .8, 1.2], ['ನಾಲ್ಕು', 1.2, 1.6], ['ಡಾಕ್ಟರ್', 1.76, 2.2], ['ರಾಜೇಶ್', 2.2, 2.6],
                 ['ಐದು', 3.05, 3.5], ['ಆರು', 3.5, 4.0], ['ಏಳು', 4.0, 4.5], ['ಎಂಟು', 4.5, 5.0]]
        with mock.patch.object(RS, 'audit', return_value={'pair': {'words': words}}):
            cut = RS._pair_boundary(full, a, b, len(x) / 48000)
        self.assertAlmostEqual(cut, 1.68, delta=0.12)               # the thin gap after the headline — not the clear one at 2.8

    def test_without_the_speech_model_it_still_cuts_near_the_weights_guess(self):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        rng = np.random.default_rng(4)
        x = np.concatenate([rng.normal(0, .2, 48000 * 2), np.zeros(int(48000 * .3)), rng.normal(0, .2, 48000 * 2)])
        sf.write(d / 'p.wav', x, 48000)
        with mock.patch.object(RS, 'audit', return_value={'unavailable': 'test'}):
            cut = RS._pair_boundary(d / 'p.wav', 'ಒಂದು ಎರಡು', 'ಮೂರು ನಾಲ್ಕು', len(x) / 48000)
        self.assertAlmostEqual(cut, 2.15, delta=0.3)


class TheVoiceFallsBackWhole(unittest.TestCase):
    """D134: a better voice may be asked for, but a day is never lost, and never spoken in two voices."""

    def made(self, first_error):
        calls = []

        def fake_render(edition, out_path, stills=None, engine='google'):
            calls.append(engine)
            if engine == 'gemini' and first_error:
                raise first_error
            return dict(seconds=1.0, timeline=dict(stories=[], outro=0.1, compress=0), warnings=[], clips={})
        d = tempfile.mkdtemp(dir=ROOT / 'build')
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        with mock.patch.object(R, 'render', fake_render), contextlib.redirect_stdout(io.StringIO()):
            res = R.make(Edition(stories=[], date=__import__('datetime').datetime(2026, 1, 1)), d, engine='gemini')
        return calls, res

    def test_a_voice_that_cannot_be_had_means_the_whole_reel_in_google(self):
        calls, res = self.made(R.ReelError('the gemini voice failed 3 times: Gemini daily quota exhausted'))
        self.assertEqual(calls, ['gemini', 'google'])
        self.assertEqual(res['voice_engine'], 'google')
        self.assertTrue(any('fell back' in w for w in res['warnings']))

    def test_a_healthy_voice_is_used_once(self):
        calls, res = self.made(None)
        self.assertEqual(calls, ['gemini'])
        self.assertEqual(res['voice_engine'], 'gemini')

    def test_copy_that_does_not_fit_is_not_blamed_on_the_voice(self):
        with self.assertRaises(R.ReelFitError):
            self.made(R.ReelFitError('too long'))


class TheSoundEffectsSet(unittest.TestCase):
    """D135: licensed effects where they exist, the house set where they do not — slot by slot, never silence."""

    def test_a_missing_licensed_file_falls_back_to_the_house_one(self):
        with mock.patch.object(R, 'BASE', Path(tempfile.mkdtemp())):
            (R.BASE / 'assets/sfx').mkdir(parents=True)
            path, shift = R._sfx('whoosh')
        self.assertEqual(path.parent.name, 'sfx')
        self.assertEqual(shift, 0.0)

    def test_the_house_set_is_used_when_asked_for(self):
        with mock.patch.object(Limits, 'saara_reel_sfx', 'house'):
            self.assertEqual(R._sfx('pop')[0], ROOT / 'assets/sfx/pop.wav')

    @unittest.skipUnless((ROOT / 'assets/sfx/pro/whoosh.wav').exists(), 'the licensed set lives only on the owner\'s Mac')
    def test_a_licensed_whoosh_peaks_where_the_house_one_did(self):
        path, shift = R._sfx('whoosh')
        self.assertIn('pro', str(path))
        self.assertAlmostEqual(R._peak_at(path) + shift, R._peak_at(ROOT / 'assets/sfx/whoosh.wav'), places=3)

    def test_every_licensed_effect_on_disk_is_in_the_register(self):
        from brand import music
        self.assertEqual([p for p in music.audit() if 'sfx' in p], [])


class TheKannadaSpellingWatch(unittest.TestCase):
    """D136: Kannada changes meaning with one sound, and the voice reads exactly the letters it is given."""

    def test_words_one_sound_from_another_word_are_listed(self):
        from brand import kannada_check as K
        hits = {h['word']: h for h in K.meaning_pairs('ಕೊಲೆ ಪ್ರಕರಣ, ಮಳೆಯಲ್ಲಿ ಕಲ್ಲು ಮತ್ತು ಅನ್ನ ಅಣ್ಣ')}
        self.assertEqual(hits['ಕೊಲೆ']['vs'], 'ಕೊಳೆ')
        self.assertEqual(hits['ಮಳೆಯಲ್ಲಿ']['vs'], 'ಮಲೆ')                 # an inflected form is still the word
        self.assertEqual(hits['ಕಲ್ಲು']['vs'], 'ಕಳ್ಳ')
        self.assertIn('ಅಣ್ಣ', hits)

    def test_a_longer_word_that_merely_starts_like_one_is_not(self):
        from brand import kannada_check as K
        self.assertEqual(K.meaning_pairs('ಕರೆಯಲಾಗಿದೆ ಕಲಾವಿದರು ಮನೆಮನೆಗೆ'), [])       # ಕರೆ+ಯಲಾಗಿದೆ, ಕಲಾ…, ಮನೆ+ಮನೆಗೆ

    def test_a_word_no_newspaper_spelled_is_listed_and_a_printed_one_is_not(self):
        from brand import kannada_check as K
        with mock.patch.object(K, '_corpus', return_value=frozenset({'ಬರಗೂರು', 'ಪ್ರಶಸ್ತಿ', 'ಪ್ರದಾನ'})):
            self.assertEqual(K.unseen_spellings('ಬರಗೂರಿಗೆ ಪ್ರಶಸ್ತಿ ಪ್ರದಾನ'), [])        # ು→ಇ before an ending
            self.assertEqual(K.unseen_spellings('ಬರಗೂರಿಗೆ ಪ್ರಶಸ್ತೀ'), ['ಪ್ರಶಸ್ತೀ'])      # a changed vowel length is caught

    def test_the_gate_names_them_and_the_voice_is_told_to_keep_the_sounds_apart(self):
        from brand.tokens import Limits
        self.assertIn('short and long vowels distinct', Limits.saara_reel_gemini_style)
        d = TheGate.folder(self_ := TheGate(), dict(seconds=8.0, issues=[], pronunciation={}, timing=['measured'],
                           watch=dict(pairs=[dict(word='ಕೊಲೆ', means='murder', vs='ಕೊಳೆ', vs_means='dirt', where='story 1 headline')],
                                      unseen=[dict(word='ಪ್ರಶಸ್ತೀ', where='story 3 card')]))) if False else None


class TheSecondGeminiKey(unittest.TestCase):
    """D134: a second key (its own free daily quota) carries on where the first one's runs out."""

    def run_synth(self, first_spent):
        import io, urllib.error
        from brand import voice
        used = []

        def fake_fetch(req, timeout):
            key = req.get_header('X-goog-api-key')
            used.append(key)
            if key == 'KEY1' and first_spent:
                raise urllib.error.HTTPError(req.full_url, 429, 'x', {}, io.BytesIO(
                    b'{"error":{"message":"limit: 10 ... per day ... Please retry in 2h30m10.5s."}}'))
            import base64, json
            return json.dumps({'candidates': [{'content': {'parts': [{'inlineData': {'data': base64.b64encode(b'\0\0' * 2400).decode()}}]}}]}).encode()
        d = tempfile.mkdtemp(dir=ROOT / 'build')
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        state = os.path.join(d, 'state.json')
        with mock.patch.object(voice, 'load_gemini_keys', return_value=['KEY1', 'KEY2']), \
                mock.patch.object(voice, '_fetch', fake_fetch), mock.patch.object(voice, '_KEY_STATE', state):
            voice._gemini_tts_synthesize('x', os.path.join(d, 'o.mp3'), voice='Kore')
            voice._gemini_tts_synthesize('y', os.path.join(d, 'o2.mp3'), voice='Kore')
        return used

    def test_the_second_key_is_used_when_the_first_is_spent_and_the_first_is_not_asked_again(self):
        self.assertEqual(self.run_synth(True), ['KEY1', 'KEY2', 'KEY2'])        # one refusal, then straight to KEY2

    def test_the_first_key_is_used_while_it_lasts(self):
        self.assertEqual(self.run_synth(False), ['KEY1', 'KEY1'])


class TheCardAddsToTheHeadline(unittest.TestCase):
    """D139: a card that says the headline's words again wastes the one sentence the viewer reads and hears."""

    def test_the_card_that_repeated_the_headline_is_named(self):
        self.assertTrue(R._repeats('ಮೊಬೈಲ್ ಕಳವು ಮಾಡಿ ಹಣ ವರ್ಗಾವಣೆ', 'ಮೊಬೈಲ್ ಕಳವು ಮಾಡಿ ಹಣ ವರ್ಗಾವಣೆ ನಡೆದಿದೆ.'))

    def test_a_card_that_tells_more_is_not(self):
        self.assertEqual(R._repeats('ಮೊಬೈಲ್ ಕಳವು ಮಾಡಿ ಹಣ ವರ್ಗಾವಣೆ', 'ಬೈಂದೂರು ಠಾಣೆಯಲ್ಲಿ ಪ್ರಕರಣ ದಾಖಲಾಗಿದ್ದು, ಪೊಲೀಸರು ತನಿಖೆ ಆರಂಭಿಸಿದ್ದಾರೆ.'), [])

    def test_the_town_gets_its_pause(self):
        p = Path(tempfile.mkdtemp(dir=ROOT / 'build')) / 'h.wav'
        self.addCleanup(lambda: __import__('shutil').rmtree(p.parent, ignore_errors=True))
        rng = np.random.default_rng(1)
        sf.write(p, np.concatenate([rng.normal(0, .2, 24000), np.zeros(1500), rng.normal(0, .2, 48000)]), 48000)
        before = len(sf.read(p)[0]) / 48000
        after = RS.pause_at(p, 0.53, Limits.saara_reel_town_pause)
        self.assertAlmostEqual(after - before, Limits.saara_reel_town_pause - 1500 / 48000, delta=0.02)
        self.assertEqual(RS.pause_at(p, 0.53, 0.1), after)           # a pause already long enough is left alone


class WhenTheVoiceStutters(unittest.TestCase):
    """D138: Kore said "ಕಡಲಿನಲ್ಲಿ" as "ಕಡಲಿ ನಲ್ಲಿ ನಲ್ಲಿ" and the audit scored it 0.94 — a pass."""

    def test_a_syllable_said_twice_that_the_script_says_once_is_found(self):
        from brand import reel_audit as A
        heard = [['ಕುಂದಾಪುರ', 0, .56], ['ಕಡಲಿ', .56, 1.04], ['ನಲಿ', 1.04, 1.26], ['ನಲಿ', 1.26, 1.48], ['ಬಿರುಗಾಳಿ', 1.48, 2.02]]
        self.assertEqual(A.stutters('ಕುಂದಾಪುರ, ಕಡಲಿನಲ್ಲಿ ಬಿರುಗಾಳಿ', heard), [[1.26, 1.48]])

    def test_a_repeat_the_script_really_has_is_not_one(self):
        from brand import reel_audit as A
        self.assertEqual(A.stutters('ಇಬ್ಬರು ಇಬ್ಬರು ಬಂದರು', [['ಇಬ್ಬರು', 0, 1], ['ಇಬ್ಬರು', 1, 2], ['ಬಂದರು', 2, 3]]), [])

    def test_the_repeat_is_cut_out_and_the_rest_joined(self):
        p = Path(tempfile.mkdtemp(dir=ROOT / 'build')) / 'c.wav'
        self.addCleanup(lambda: __import__('shutil').rmtree(p.parent, ignore_errors=True))
        sf.write(p, np.random.default_rng(2).normal(0, .1, 48000 * 3), 48000)
        new = RS.cut_out(p, [[1.0, 1.4]])
        self.assertAlmostEqual(new, 2.6, delta=0.03)
        self.assertAlmostEqual(len(sf.read(p)[0]) / 48000, new, places=2)


class TheVoiceIsEven(unittest.TestCase):
    """D137: every clip is a separate request at its own level; the listener must not hear the voice change mood."""

    def wav(self, amp, name):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        rng = np.random.default_rng(5)
        x = np.concatenate([np.zeros(4800), rng.normal(0, amp, 48000 * 2), np.zeros(4800)])
        p = d / name
        sf.write(p, x, 48000)
        return p

    def lufs(self, p):
        err = subprocess.run(['ffmpeg', '-nostats', '-i', str(p), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
        return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', err)[-1])

    def test_a_quiet_and_a_loud_clip_come_to_the_same_level(self):
        quiet, loud = self.wav(0.05, 'q.wav'), self.wav(0.25, 'l.wav')   # ±10 dB is as far as the gain goes
        RS.level(quiet)
        RS.level(loud)
        self.assertAlmostEqual(self.lufs(quiet), Limits.saara_reel_speech_lufs, delta=0.6)
        self.assertAlmostEqual(self.lufs(loud), Limits.saara_reel_speech_lufs, delta=0.6)

    def test_silence_is_left_alone(self):
        p = self.wav(0.0, 's.wav')
        self.assertEqual(RS.level(p), 0.0)

    def test_the_trim_keeps_the_edges_of_the_sound(self):
        p = self.wav(0.1, 'e.wav')
        out = p.with_name('t.wav')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(p), '-af', RS.TRIM, str(out)], check=True)
        x, sr = sf.read(out)
        self.assertGreater(len(x) / sr, 2.0)                  # the 2 s of sound is all there
        self.assertLess(len(x) / sr, 2.0 + 0.08 + 0.14 + 0.05)  # plus no more than the lead-in and tail kept



    def hook(self, *towns):
        return R._hook_text([dict(place_short=t) for t in towns])

    def test_towns_are_listed_the_way_kannada_lists_them(self):
        self.assertEqual(self.hook('ಕೊಲ್ಲೂರು'), 'ಇಂದಿನ ಸುದ್ದಿ, ಕೊಲ್ಲೂರು.')
        self.assertEqual(self.hook('ಕೊಲ್ಲೂರು', 'ಬೈಂದೂರು'), 'ಇಂದಿನ ಸುದ್ದಿ, ಕೊಲ್ಲೂರು ಮತ್ತು ಬೈಂದೂರು.')
        self.assertEqual(self.hook('ಕೊಲ್ಲೂರು', 'ಕುಂದಾಪುರ', 'ಬೈಂದೂರು'), 'ಇಂದಿನ ಸುದ್ದಿ, ಕೊಲ್ಲೂರು, ಕುಂದಾಪುರ ಮತ್ತು ಬೈಂದೂರು.')

    def test_more_towns_than_are_named_says_so(self):
        self.assertEqual(self.hook('ಅ', 'ಆ', 'ಇ', 'ಈ'), 'ಅ, ಆ, ಇ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ.')
        self.assertEqual(self.hook('ಬೈಂದೂರು', 'ಬೈಂದೂರು'), 'ಇಂದಿನ ಸುದ್ದಿ, ಬೈಂದೂರು.')       # a town twice is one town


class WhenTheDayIsOneWordTooLong(unittest.TestCase):
    """D134: pauses first, then the speech by the smallest step that fits — never 'REEL NOT MADE' for a second."""

    def clips(self, per_clip):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        n = 6
        durs = {'intro': per_clip, 'outro': 2.6}
        for i in range(n):
            durs[f'h{i}'] = durs[f'b{i}'] = per_clip
        for k, v in durs.items():
            sf.write(d / f'{k}.wav', np.random.default_rng(1).normal(0, 0.05, int(48000 * v)), 48000)
        return d, durs, n

    def test_a_reel_just_over_the_fail_line_is_sped_up_not_refused(self):
        d, durs, n = self.clips(4.1)                                   # tightest cut ≈ 60.5 s
        copies = [dict(body='ಒಂದು ಎರಡು ಮೂರು', place_short='ಉಡುಪಿ') for _ in range(n)]
        tl0 = R._timeline(durs, n)
        self.assertGreater(tl0['T'], Limits.reel_fail_seconds)
        tl, new, _w, _t = R._speed_up(d, copies, 'ಉಡುಪಿ ಉಡುಪಿ', durs, ['ಉಡುಪಿ'] * n, tl0)
        self.assertLessEqual(tl['T'], Limits.reel_fail_seconds)
        self.assertGreater(tl['speedup'], 1.0)
        self.assertLessEqual(tl['speedup'], Limits.saara_reel_speedup_max)
        self.assertLess(new['h0'], durs['h0'])                         # the clip on disk really is shorter

    def test_a_reel_far_over_is_still_refused_naming_the_story(self):
        d, durs, n = self.clips(5.2)
        copies = [dict(body='ಒಂದು', place_short='ಉಡುಪಿ') for _ in range(n)]
        tl, *_ = R._speed_up(d, copies, 'ಉಡುಪಿ', durs, ['ಉಡುಪಿ'] * n, R._timeline(durs, n))
        self.assertGreater(tl['T'], Limits.reel_fail_seconds)          # _build raises ReelFitError on this


class TheGate(unittest.TestCase):
    """review() reads the reel's own report against the film."""

    def folder(self, report, seconds=8.0, talk=True):
        d = tempfile.mkdtemp(dir=ROOT / 'build')
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        audio = ['-f', 'lavfi', '-i', 'sine=frequency=300:duration=%s' % seconds] if talk else ['-an']
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc=s=540x960:d={seconds}:r=10',
                        *audio, '-pix_fmt', 'yuv420p', '-shortest', os.path.join(d, 'reel_saara.mp4')], check=True)
        os.makedirs(os.path.join(d, '_review'))
        if report is not None:
            Path(d, '_review', 'reel_saara_report.json').write_text(json.dumps(report))
        return d

    def codes(self, d):
        from brand.review import review
        rep = review(d)
        return {f.code: f for f in rep.findings}

    def test_a_clean_report_raises_nothing_about_the_reel(self):
        c = self.codes(self.folder(dict(seconds=8.0, issues=[], pronunciation={}, timing=['measured'])))
        for code in ('VID-07', 'VID-08', 'SND-08'):
            self.assertNotIn(code, c)

    def test_a_reel_made_from_earlier_wording_is_refused_until_it_is_made_again(self):
        # D134: a desk edits a headline after the render; the gate sees it without anyone remembering
        import datetime
        from brand.review import review
        st = Story(headline='ಕಂಪನಿ: ಹೊಸ ಯೋಜನೆ', reel_line='ಹೊಸ ಯೋಜನೆ ಆರಂಭ', reel_support='ಯೋಜನೆ ಸೋಮವಾರ ಆರಂಭ.',
                   location='ಉಡುಪಿ', category='civic', segment='saara')
        ed = Edition(stories=[st], date=datetime.datetime(2026, 10, 24, 9, 0))
        made = R.copies_hash(R._copies(ed.segment('saara')))
        d = self.folder(dict(seconds=8.0, issues=[], pronunciation={}, timing=['measured'], copies_hash=made))
        self.assertNotIn('VID-08', {f.code for f in review(d, ed).findings})
        st.reel_line = 'ಹೊಸ ಯೋಜನೆ ಸ್ಥಗಿತ'                                   # a desk's edit, after the render
        found = {f.code: f for f in review(d, ed).findings}
        self.assertEqual(found['VID-08'].severity, 'fail')
        self.assertIn('earlier wording', found['VID-08'].message)

    def test_text_that_does_not_fit_holds_the_package(self):
        c = self.codes(self.folder(dict(seconds=8.0, issues=['story 1: the headline does not fit above the card even at 60px'])))
        self.assertEqual(c['VID-07'].severity, 'fail')

    def test_a_truncated_film_holds_the_package(self):
        c = self.codes(self.folder(dict(seconds=9.2, issues=[])))         # cut for 9.2s, the file runs 8.0
        self.assertEqual(c['VID-08'].severity, 'fail')

    def test_a_word_the_voice_may_misread_is_named(self):
        c = self.codes(self.folder(dict(seconds=8.0, issues=[], pronunciation={'story 2': ['XYZ']})))
        self.assertEqual(c['SND-08'].severity, 'warn')

    def test_a_reel_with_no_report_was_not_made_by_the_render(self):
        c = self.codes(self.folder(None))
        self.assertEqual(c['VID-08'].severity, 'warn')

    def test_a_voice_that_does_not_say_its_words_holds_the_package(self):
        bad = {'story 2 card': dict(similarity=0.2, suspects=['ಅ'], heard='ಏನೋ ಬೇರೆ')}
        c = self.codes(self.folder(dict(seconds=8.0, issues=[], voice_audit=bad)))
        self.assertEqual(c['SND-06'].severity, 'fail')

    def test_a_middling_score_warns_and_a_good_score_only_names_words_to_listen_for(self):
        mid = self.codes(self.folder(dict(seconds=8.0, issues=[], voice_audit={'hook': dict(similarity=0.7, suspects=[], heard='x')})))
        self.assertEqual(mid['SND-06'].severity, 'warn')
        ok = self.codes(self.folder(dict(seconds=8.0, issues=[], voice_audit={'hook': dict(similarity=0.97, suspects=['ಬೈಂದೂರು'], heard='x')})))
        self.assertEqual(ok['SND-06'].severity, 'warn')
        self.assertIn('listen for', ok['SND-06'].message)
        clean = self.codes(self.folder(dict(seconds=8.0, issues=[], voice_audit={'hook': dict(similarity=0.99, suspects=[], heard='x')})))
        self.assertNotIn('SND-06', clean)

    def test_a_voice_that_could_not_be_heard_back_is_said(self):
        c = self.codes(self.folder(dict(seconds=8.0, issues=[], voice_audit={'unavailable': 'mlx-whisper is not installed'})))
        self.assertEqual(c['SND-06'].severity, 'warn')

    def test_a_silent_reel_is_held(self):
        c = self.codes(self.folder(dict(seconds=8.0, issues=[]), talk=False))
        self.assertEqual(c['SND-01'].severity, 'fail')

    def test_over_the_house_cap_is_held_and_just_under_it_is_only_a_warning(self):
        self.assertEqual(self.codes(self.folder(dict(seconds=62.0, issues=[]), seconds=62.0))['VID-01'].severity, 'fail')
        c = self.codes(self.folder(dict(seconds=59.6, issues=[]), seconds=59.6))
        self.assertEqual(c['VID-01'].severity, 'warn')


if __name__ == '__main__':
    unittest.main()
