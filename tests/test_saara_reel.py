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


class SpokenRight(unittest.TestCase):
    TABLE = {1: 'ಒಂದು', 7: 'ಏಳು', 10: 'ಹತ್ತು', 11: 'ಹನ್ನೊಂದು', 19: 'ಹತ್ತೊಂಬತ್ತು', 20: 'ಇಪ್ಪತ್ತು',
             21: 'ಇಪ್ಪತ್ತೊಂದು', 22: 'ಇಪ್ಪತ್ತೆರಡು', 23: 'ಇಪ್ಪತ್ತಮೂರು', 25: 'ಇಪ್ಪತ್ತೈದು', 26: 'ಇಪ್ಪತ್ತಾರು',
             27: 'ಇಪ್ಪತ್ತೇಳು', 28: 'ಇಪ್ಪತ್ತೆಂಟು', 29: 'ಇಪ್ಪತ್ತೊಂಬತ್ತು', 33: 'ಮೂವತ್ತಮೂರು', 48: 'ನಲವತ್ತೆಂಟು',
             99: 'ತೊಂಬತ್ತೊಂಬತ್ತು', 100: 'ನೂರು', 120: 'ನೂರ ಇಪ್ಪತ್ತು', 305: 'ಮುನ್ನೂರ ಐದು',
             2026: 'ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು', 5000: 'ಐದು ಸಾವಿರ'}

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
    def test_every_effect_the_reel_plays_is_house_made_and_registered(self):
        from brand import music
        allowed = music.allowed_paths('sfx')
        for name in ('whoosh', 'tick', 'open', 'outro', 'pop', 'press'):
            self.assertTrue((ROOT / 'assets/sfx' / f'{name}.wav').exists(), name)
            self.assertIn(f'assets/sfx/{name}.wav', allowed, name)
        src = (ROOT / 'brand/saara_reel.py').read_text(encoding='utf-8')
        for name in ('pop', 'press', 'tick', 'whoosh'):
            self.assertIn(f"sfx / '{name}.wav'", src)

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

    def render_with(self, die_after, fit_issue=None, forever=False):
        import asyncio, io
        from PIL import Image
        calls = []
        buf = io.BytesIO()
        Image.new('RGB', (64, 64), (10, 20, 30)).save(buf, 'PNG')
        png = buf.getvalue()

        async def fake_drive(page, profile, work, gate=None):
            calls.append(profile.name)
            seen = {'n': 0}

            async def frame(t):
                seen['n'] += 1
                if die_after is not None and (forever or len(calls) == 1) and seen['n'] > die_after:
                    raise RuntimeError('no close frame received or sent')
                return png
            laid = {'lines': [2], 'issues': [fit_issue] if fit_issue else []}
            if gate:
                gate(laid)
            return laid, await work(frame)

        def fake_build(edition, tmp, engine):
            tl = {'T': 1.0, 'stories': [], 'outro': 0.2, 'compress': 0, 'natural': 1.0, 'over': 0.0}
            return dict(copies=[], tl=tl, durs={}, timing=[], pron={}, hook='', page=tmp / 'x.html')

        def fake_mix(tl, clips, out):
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=1',
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

    def test_a_silent_reel_is_held(self):
        c = self.codes(self.folder(dict(seconds=8.0, issues=[]), talk=False))
        self.assertEqual(c['SND-01'].severity, 'fail')

    def test_over_the_house_cap_is_held_and_just_under_it_is_only_a_warning(self):
        self.assertEqual(self.codes(self.folder(dict(seconds=62.0, issues=[]), seconds=62.0))['VID-01'].severity, 'fail')
        c = self.codes(self.folder(dict(seconds=59.6, issues=[]), seconds=59.6))
        self.assertEqual(c['VID-01'].severity, 'warn')


if __name__ == '__main__':
    unittest.main()
