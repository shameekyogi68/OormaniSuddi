"""
D98, D99 — the scan wipe: every carousel slide has an animated twin.
====================================================================
The animation is built from the finished slide, so these hold for every
slide the engine makes: a cover is never blank, nothing else shows before it
is revealed, the held frame is the slide itself, the chrome never moves, the
held slide asks to be swiped, and the loop has no seam.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import render  # noqa: E402
from brand import animate as A  # noqa: E402
from brand.content import Edition, frozen  # noqa: E402
from brand.tokens import Motion, Paper as P  # noqa: E402

FIXTURE = 'tests/fixture_edition.json'
NOW = '2026-08-25T09:40:00+05:30'


def frame_at(mp4, t):
    out = mp4 + f'.{t}.png'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(t), '-i', mp4,
                    '-frames:v', '1', out], check=True)
    return Image.open(out).convert('RGB')


def duration(mp4):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', mp4], capture_output=True, text=True)
    return float(r.stdout.strip())


class TheScanWipe(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with frozen(NOW):
            render.render_edition(Edition.load(FIXTURE), cls.tmp.name,
                                  ['saara', 'mukhya'], animate=True)
        cls.files = sorted(os.listdir(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def test_every_slide_has_a_video_twin(self):
        jpgs = [f for f in self.files if f.endswith('.jpg') and f.startswith(('saara_', 'mukhya_'))]
        self.assertTrue(jpgs)
        for j in jpgs:
            self.assertIn(j[:-4] + '.mp4', self.files, j)

    def info(self, name):
        cover = '_cover' in name
        i = A.analyse(Image.open(self.path(name + '.jpg')), cover=cover)
        return i, A.plan(i, cover=cover)

    def test_the_held_frame_is_the_slide_itself(self):
        for name in ('saara_02', 'mukhya_1_02_points', 'mukhya_1_01_cover', 'saara_01_cover'):
            _i, tl = self.info(name)
            still = np.asarray(Image.open(self.path(name + '.jpg')).convert('RGB')).astype(int)
            held = np.asarray(frame_at(self.path(name + '.mp4'), tl['reveal'] + 0.3)).astype(int)
            self.assertLess(np.abs(still - held).mean(), 3.0, name)

    def test_nothing_is_readable_before_it_is_revealed(self):
        """A story slide's frame zero shows the chrome only."""
        name = 'saara_02'
        f0 = np.asarray(frame_at(self.path(name + '.mp4'), 0.0))
        info, _tl = self.info(name)
        paper = np.array(info['paper'])
        for b in info['bands']:
            zone = f0[b.y0:b.y1, b.x0:b.x1].astype(int)
            share = (np.abs(zone - paper).sum(axis=2) > 60).mean()
            self.assertLess(share, 0.02, f'band at y={b.y0} is already visible')

    def test_a_cover_is_never_blank(self):
        """The feed and the grid see frame 0: the photograph and the headline
        are there; what follows them is not yet."""
        for name in ('saara_01_cover', 'mukhya_1_01_cover'):
            info, tl = self.info(name)
            self.assertTrue(info['static'], name)
            # Against the held frame, not the JPEG: video softens red type
            # the same amount in both, and only the difference matters here.
            still = np.asarray(frame_at(self.path(name + '.mp4'), tl['reveal'] + 0.3)).astype(int)
            f0 = np.asarray(frame_at(self.path(name + '.mp4'), 0.0)).astype(int)
            for i in info['static']:
                b = info['bands'][i]
                d = np.abs(f0[b.y0:b.y1, b.x0:b.x1] - still[b.y0:b.y1, b.x0:b.x1]).mean()
                self.assertLess(d, 1.5, f'{name}: the headline is not there at frame 0')
            later = [b for k, b in enumerate(info['bands'])
                     if k not in info['static'] and not b.rule]
            self.assertTrue(later, name)
            b = later[-1]
            zone = f0[b.y0:b.y1, b.x0:b.x1]
            self.assertLess((np.abs(zone - np.array(info['paper'])).sum(axis=2) > 60).mean(),
                            0.02, f'{name}: the last line is already there')
            if info['photo_end']:
                d = np.abs(f0[:info['photo_end'] - 20] - still[:info['photo_end'] - 20]).mean()
                self.assertLess(d, 1.5, f'{name}: the photograph is not there at frame 0')

    def test_the_loop_has_no_seam(self):
        name = 'saara_02'
        mp4 = self.path(name + '.mp4')
        first = np.asarray(frame_at(mp4, 0.0)).astype(int)
        last = np.asarray(frame_at(mp4, duration(mp4) - 0.05)).astype(int)
        self.assertLess(np.abs(first - last).mean(), 3.0)

    def test_the_chrome_never_moves(self):
        name = 'saara_02'
        _i, tl = self.info(name)
        a = frame_at(self.path(name + '.mp4'), 0.0)
        b = frame_at(self.path(name + '.mp4'), tl['reveal'] + 0.3)
        H = a.height
        for box in ((0, 0, a.width, A.TOP_STATIC), (0, H - P.footer_h, a.width, H)):
            d = np.abs(np.asarray(a.crop(box)).astype(int) - np.asarray(b.crop(box)).astype(int))
            self.assertLess(d.mean(), 4.0, box)

    def test_the_held_slide_asks_to_be_swiped(self):
        """The chevrons nudge right while the slide holds, and come back."""
        name = 'saara_02'
        info, tl = self.info(name)
        self.assertTrue(tl['nudges'])
        mp4 = self.path(name + '.mp4')
        rest = np.asarray(frame_at(mp4, tl['reveal'] + 0.3)).astype(int)
        peak = np.asarray(frame_at(mp4, tl['nudges'][0] + 0.18)).astype(int)
        for key in ('tab_chevron', 'footer_chevron'):
            x0, y0, x1, y1 = info[key]
            self.assertGreater(np.abs(peak[y0:y1, x0:x1] - rest[y0:y1, x0:x1]).mean(), 3.0, key)
        # Everything else is still.
        x0, y0, x1, y1 = info['tab']
        peak[y0:y1, x0:x1] = rest[y0:y1, x0:x1]
        x0, y0, x1, y1 = info['footer_chevron']
        peak[y0:y1, x0:x1] = rest[y0:y1, x0:x1]
        self.assertLess(np.abs(peak - rest).mean(), 0.5)

    def test_a_photograph_stays_out_of_the_wipe(self):
        info, tl = self.info('mukhya_1_01_cover')
        self.assertGreater(info['photo_end'], 600)
        self.assertIsNotNone(info['sun'])          # the gold sunline draws itself
        self.assertLess(len(info['bands']), 8)     # the text below it, not the photo

    def test_the_reveal_is_quick_and_the_hold_reads(self):
        for name in ('saara_01_cover', 'saara_02', 'mukhya_1_02_points', 'saara_05_sources'):
            info, tl = self.info(name)
            self.assertLessEqual(tl['reveal'], Motion.anim_reveal_max + 0.01, name)
            self.assertGreaterEqual(tl['hold'], Motion.anim_hold, name)
            self.assertLessEqual(tl['hold'], Motion.anim_hold_max, name)
            self.assertAlmostEqual(duration(self.path(name + '.mp4')), tl['total'], delta=0.3)
        # More type, a longer hold — up to the ceiling.
        short = {'chars': 30, 'bands': [], 'static': [], 'photo_end': 0, 'sun': None,
                 'size': (1080, 1350)}
        self.assertEqual(A.plan(short)['hold'], Motion.anim_hold)

    def test_the_schedule_names_the_videos(self):
        with frozen(NOW):
            from brand import copy as C
            plan = C.publishing_plan(has_saara=True, saara_last='saara_05_sources.jpg',
                                     animated=True)
        self.assertIn('saara_01_cover.mp4', plan[0].asset)
        self.assertIn('saara_05_sources.mp4', plan[0].asset)


if __name__ == '__main__':
    unittest.main()
