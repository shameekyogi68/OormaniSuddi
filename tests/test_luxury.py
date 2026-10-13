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


class TheLogoAsItIs(unittest.TestCase):
    """D129 — "let the logo be round and as it is": nothing drawn round it."""

    def test_nothing_is_drawn_outside_the_logo(self):
        d = 300
        m = np.asarray(medallion(d, shadow=0.0))[..., 3]
        ys, xs = np.nonzero(m > 200)
        self.assertLessEqual(xs.max() - xs.min() + 1, d + 2, 'a ring round the logo is back')

    def test_the_reel_headline_reveals_left_to_right(self):
        """D129 — the one motion signature: lines wipe in from the left."""
        from PIL import Image
        from brand.speednews import _scan, SCAN_START, SCAN_LINE
        tile = Image.new('RGBA', (600, 80), (255, 255, 255, 255))
        mid = np.asarray(_scan(tile, [(0, 80)], SCAN_START + SCAN_LINE * 0.35))[..., 3]
        self.assertGreater(mid[:, 20].mean(), 200)     # the left is in
        self.assertLess(mid[:, 580].mean(), 20)        # the right is still to come
        done = np.asarray(_scan(tile, [(0, 80)], SCAN_START + SCAN_LINE * 1.1))[..., 3]
        self.assertGreater(done.mean(), 250)


class AnimationIsGuaranteed(unittest.TestCase):
    """D130 — a carousel that is not animated, or only pretends to be, is held.
    The pipeline animates by default; nothing used to CHECK, so a failed encode
    or a --still folder looked finished and static pictures got posted."""

    @staticmethod
    def _video(path, moving: bool):
        import subprocess
        src = ('testsrc2=s=216x270:r=30:d=3' if moving
               else 'color=c=white:s=216x270:r=30:d=3')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', src,
                        '-pix_fmt', 'yuv420p', path], check=True)

    def _folder(self, files):
        import tempfile
        d = tempfile.mkdtemp()
        for name, moving in files:
            path = os.path.join(d, name)
            if name.endswith('.mp4'):
                self._video(path, moving)
            else:
                with open(path, 'wb') as fh:
                    fh.write(b'x')
        return d

    def _codes(self, d, draft=False):
        from brand.review import review
        rep = review(d, draft=draft)
        return ([f.code for f in rep.findings if f.severity == 'fail'],
                [f.code for f in rep.findings if f.severity != 'fail'])

    def test_a_slide_with_no_video_is_held(self):
        d = self._folder([('saara_01_cover.jpg', 0)])
        fails, _ = self._codes(d)
        self.assertIn('VID-05', fails)

    def test_a_still_draft_warns_instead_of_holding(self):
        d = self._folder([('saara_01_cover.jpg', 0)])
        fails, warns = self._codes(d, draft=True)
        self.assertNotIn('VID-05', fails)
        self.assertIn('VID-05', warns)

    def test_a_video_that_does_not_move_is_held(self):
        d = self._folder([('saara_01_cover.mp4', False)])
        fails, _ = self._codes(d)
        self.assertIn('VID-06', fails)

    def test_a_video_that_moves_passes_both(self):
        d = self._folder([('saara_01_cover.mp4', True)])
        fails, _ = self._codes(d)
        self.assertNotIn('VID-05', fails)
        self.assertNotIn('VID-06', fails)

    def test_an_animated_slide_whose_still_moved_to_review_is_fine(self):
        d = self._folder([('saara_01_cover.mp4', True)])
        os.makedirs(os.path.join(d, '_review'))
        with open(os.path.join(d, '_review', 'saara_01_cover.jpg'), 'wb') as fh:
            fh.write(b'x')
        fails, _ = self._codes(d)
        self.assertNotIn('VID-05', fails)

    def test_every_render_says_which_design_made_it(self):
        from brand.provenance import design_stamp
        st = design_stamp()
        self.assertRegex(st['decision'], r'^D\d+$')
        self.assertIn('dirty', st)


class TypeOnAPhotographHolds(unittest.TestCase):
    """D131 — the disclosure sits on a solid ink pill, so it reads over a
    white wall or white clothes, not only over a dark picture."""

    def test_the_credit_reads_on_a_white_picture(self):
        sf = Surface(1080, 720, 2, bg=(255, 255, 255, 255))
        pp.credit(sf, 'ಕೃಪೆ: ಊರ್ಮನಿ ಸುದ್ದಿ', (0, 0, 1080, 720))
        a = np.asarray(sf.finish()).astype(int)
        ys, xs = np.nonzero(a.mean(axis=2) < 80)
        self.assertTrue(len(ys), 'no solid label under the credit')
        pill = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        self.assertGreater((pill.mean(axis=2) < 80).mean(), 0.5, 'the label is not solid')
        self.assertGreater(ys.min(), 600, 'the label left the foot of the picture')
        self.assertGreater(xs.min(), 540, 'the label left the right-hand corner')


class InkPairsPass(unittest.TestCase):

    def test_the_news_red_on_ink_is_red_400(self):
        """The reel's red category label is body-size type: it needs the body
        floor. red_500 on ink is 3.3:1 — a pass for display type only."""
        self.assertGreaterEqual(ratio(C.red_400, C.ink_850), Limits.contrast_min)
        self.assertLess(ratio(C.red_500, C.ink_850), Limits.contrast_min,
                        'if red_500 passes on ink now, D128 can use it again')


if __name__ == '__main__':
    unittest.main()
