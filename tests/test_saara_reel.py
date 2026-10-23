"""D132 — the ಸುದ್ದಿ ಸಾರ reel: cut from the voice, inside the Reels chrome, no lines.

These run without Chrome: they hold the timeline arithmetic, the copy each slot
takes, the safe-zone geometry the page is built on and the house rule against
decorative lines. The page itself is reviewed as stills (D132).
"""
import re
import unittest
from pathlib import Path

from brand import saara_reel as R
from brand.content import Story
from brand.tokens import Limits, Motion as M, ReelsChrome as RC

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'brand/saara_reel.html').read_text(encoding='utf-8')


def px(rule: str, prop: str) -> float:
    m = re.search(re.escape(rule) + r'\s*\{[^}]*?\b' + prop + r':\s*(-?\d+)px', PAGE)
    assert m, f'{rule} {prop} not found'
    return float(m.group(1))


class CutFromTheVoice(unittest.TestCase):
    def test_each_story_runs_from_its_change_to_the_end_of_its_read_line(self):
        durs = {'intro': 3.0, 'h0': 2.0, 'b0': 8.0, 'h1': 3.0, 'b1': 9.5}
        tl = R._timeline(durs, 2)
        s0, s1 = tl['stories']
        self.assertAlmostEqual(s0['B'], max(M.saara_reel_intro, M.saara_reel_hook_at + 3.0 + 0.45), places=3)
        self.assertAlmostEqual(s0['headAt'], s0['B'] + M.saara_reel_lead, places=3)
        self.assertAlmostEqual(s0['bodyAt'], s0['headAt'] + 2.0 + M.saara_reel_gap, places=3)
        self.assertAlmostEqual(s1['B'], s0['bodyAt'] + 8.0 + M.saara_reel_tail, places=3)
        self.assertAlmostEqual(tl['T'], tl['outro'] + M.saara_reel_close, places=3)

    def test_words_are_weighed_by_akshara_not_by_code_point(self):
        # ಕ್ರ is one beat although it is three code points; a figure is read out
        self.assertEqual(R._syllables('ಕ್ರಮ'), 2.0)
        self.assertGreater(R._syllables('ಅನ್ನಸಂತರ್ಪಣೆ'), R._syllables('ಹಾಗೂ'))
        self.assertGreater(R._syllables('33ನೇ'), 4)

    def test_a_third_headline_line_is_warned_never_cut(self):
        copies = [dict(place_short='ಬೈಂದೂರು', head='x' * 40), dict(place_short='ಕಳವಾಡಿ', head='y' * 20)]
        w = R._warnings(copies, {'lines': [3, 2]})
        self.assertEqual(len(w), 1)
        self.assertIn('ಬೈಂದೂರು', w[0])
        self.assertIn(str(Limits.saara_reel_line_chars), w[0])


class WhatEachSlotSays(unittest.TestCase):
    def test_reel_line_is_shown_and_the_deck_is_read(self):
        st = Story(headline='ಉದ್ದದ ಮುದ್ರಣ ಶೀರ್ಷಿಕೆ', reel_line='ಚಿಕ್ಕ ಸಾಲು', deck='ವಿವರದ ಸಾಲು.',
                   location='ಬೈಂದೂರು', category='sport', segment='saara')
        c = R._story_copy(st)
        self.assertEqual(c['head'], 'ಚಿಕ್ಕ ಸಾಲು')
        self.assertEqual(c['body'], 'ವಿವರದ ಸಾಲು.')
        self.assertTrue(c['say_head'].startswith('ಬೈಂದೂರು'))     # the voice names the town
        self.assertEqual(c['tone'], R.TONES['ember'])

    def test_a_sentence_written_for_the_reel_wins_over_the_deck(self):
        st = Story(headline='ಶೀರ್ಷಿಕೆ', deck='ಉದ್ದದ ವಿವರ.', reel_support='ಒಂದು ಪೂರ್ಣ ವಾಕ್ಯ.', segment='saara')
        self.assertEqual(R._story_copy(st)['body'], 'ಒಂದು ಪೂರ್ಣ ವಾಕ್ಯ.')

    def test_every_category_has_a_tint(self):
        from brand.tokens import CATEGORIES
        self.assertFalse(set(CATEGORIES) - set(R.CATEGORY_TONE) - {'culture'})


class InsideTheReelsChrome(unittest.TestCase):
    def test_nothing_readable_under_the_header_the_rail_or_the_caption(self):
        self.assertGreaterEqual(px('#mast', 'top'), RC.top)
        self.assertGreaterEqual(px('.chip', 'top'), RC.top)
        card_right = px('#card', 'left') + px('#card', 'width')
        self.assertLessEqual(card_right, RC.rail_x)
        self.assertLessEqual(R.Limits.saara_reel_line_chars, Limits.reel_line_chars)
        self.assertIn('SAFE_BOTTOM = 1480', PAGE)
        self.assertLess(1480, RC.bottom)
        self.assertIn('x: 220, y: 1016, w: 640', PAGE)        # the follow button: 220 + 640 < rail
        self.assertLessEqual(220 + 640, RC.rail_x)
        # a third headline line falls below the rail's top, so it is set narrower
        self.assertIn('[110, 3, 848]', PAGE)
        self.assertLessEqual(px('.head', 'left') + 848, RC.rail_x)


class NoLines(unittest.TestCase):
    def test_no_rules_borders_or_underlines(self):       # D128: the owner's rule
        css = PAGE.split('<style>')[1].split('</style>')[0]
        for bad in ('border:', 'border-top', 'border-bottom', 'border-left', 'text-decoration', '<hr'):
            self.assertNotIn(bad, css + PAGE.split('</style>')[1].split('<script>')[0])


class Wired(unittest.TestCase):
    def test_render_makes_it_beside_the_carousel_and_clears_it_with_saara(self):
        src = (ROOT / 'render.py').read_text(encoding='utf-8')
        self.assertIn("reel_saara.mp4", src)
        from render import FORMAT_FILES
        self.assertTrue(FORMAT_FILES['saara'].search('reel_saara.mp4'))
        self.assertTrue(FORMAT_FILES['saara'].search('saara_01_cover.mp4'))


if __name__ == '__main__':
    unittest.main()
