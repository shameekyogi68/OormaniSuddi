"""D128 — luxury: paper to read, ink to watch, and no lines anywhere.

A decorative line is easy to add back without noticing — one `_rect` two
pixels tall. These look at what the shared chrome actually draws and fail if
a rule reappears, so the owner's "no lines" is a test, not a memory.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import numpy as np

from brand import paper as pp
from brand.legibility import ratio
from brand.surface import Surface, medallion
from brand.tokens import C, Limits


def _rules(img, ground, min_cover=0.5, max_h=6):
    """Horizontal runs of non-ground rows no taller than `max_h` px that span
    at least `min_cover` of the width — what a rule looks like."""
    a = np.asarray(img.convert('RGB')).astype(int)
    off = np.abs(a - np.array(ground)).sum(axis=2) > 24
    cover = off.mean(axis=1)
    rows = cover >= min_cover
    out, y = [], 0
    while y < len(rows):
        if rows[y]:
            y0 = y
            while y < len(rows) and rows[y]:
                y += 1
            if y - y0 <= max_h:
                out.append((y0, y))
        y += 1
    return out


class NoLinesInTheChrome(unittest.TestCase):

    def test_the_footer_draws_no_hairline(self):
        sf = pp.page(1080, 1350)
        pp.footer(sf, '2/5', 'ಮುಂದೆ: ಉಡುಪಿ', seam=(True, True))
        self.assertEqual(_rules(sf.finish(), C.paper_50), [])

    def test_the_saara_running_head_has_no_rule_under_it(self):
        from templates.saara import _header
        sf = pp.page(1080, 1350)
        _header(sf, '25 ಆಗಸ್ಟ್ 2026')
        self.assertEqual(_rules(sf.finish(), C.paper_50), [])

    def test_the_bug_is_the_medallion_not_a_red_block(self):
        sf = pp.page(1080, 400)
        pp.bug(sf, 64, 44)
        a = np.asarray(sf.finish()).astype(int)
        red = (np.abs(a - np.array(C.red_500)).sum(axis=2) < 40).mean()
        gold = (np.abs(a - np.array(C.gold_500)).sum(axis=2) < 90).sum()
        self.assertLess(red, 0.002, 'a red block round the name is back')
        self.assertGreater(gold, 200, 'no gold ring: the medallion is missing')

    def test_the_reel_ground_is_ink(self):
        from brand.speednews import ink_ground
        g = np.asarray(ink_ground(108, 192).convert('RGB')).astype(int)
        self.assertLess(g.mean(), 40, 'the watched formats are ink (D128)')
        self.assertEqual(_rules(ink_ground(1080, 400), tuple(g[100, 54])), [])


class TheMedallion(unittest.TestCase):

    def test_it_is_one_mark_with_room_for_its_light(self):
        m = medallion(200)
        self.assertEqual(m.size[0], m.size[1])
        self.assertGreater(m.size[0], 200)
        self.assertEqual(m.getpixel((0, 0))[3], 0, 'the corners are clear')


class InkPairsPass(unittest.TestCase):

    def test_the_news_red_on_ink_is_red_400(self):
        """The reel's red category label is body-size type: it needs the body
        floor. red_500 on ink is 3.3:1 — a pass for display type only."""
        self.assertGreaterEqual(ratio(C.red_400, C.ink_850), Limits.contrast_min)
        self.assertLess(ratio(C.red_500, C.ink_850), Limits.contrast_min,
                        'if red_500 passes on ink now, D128 can use it again')


if __name__ == '__main__':
    unittest.main()
