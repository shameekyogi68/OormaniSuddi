"""
D98 — the scan wipe: every carousel slide has an animated twin.
===============================================================
The animation is built from the finished slide, so these hold for every
slide the engine makes: nothing shows before it is revealed, the last frame is
the slide itself, the footer never moves, and a photograph fades instead of
being wiped.
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

    def test_the_last_frame_is_the_slide_itself(self):
        for name in ('saara_02', 'mukhya_1_02_points', 'mukhya_1_01_cover'):
            still = np.asarray(Image.open(self.path(name + '.jpg')).convert('RGB')).astype(int)
            last = np.asarray(frame_at(self.path(name + '.mp4'),
                                       duration(self.path(name + '.mp4')) - 0.4)).astype(int)
            self.assertLess(np.abs(still - last).mean(), 6.0, name)

    def test_nothing_is_readable_before_it_is_revealed(self):
        """Frame zero shows the chrome only — no headline, no points."""
        name = 'saara_02'
        f0 = np.asarray(frame_at(self.path(name + '.mp4'), 0.0))
        info = A.analyse(Image.open(self.path(name + '.jpg')))
        paper = np.array(info['paper'])
        for b in info['bands']:
            zone = f0[b.y0:b.y1, b.x0:b.x1].astype(int)
            share = (np.abs(zone - paper).sum(axis=2) > 60).mean()
            self.assertLess(share, 0.02, f'band at y={b.y0} is already visible')

    def test_the_chrome_and_footer_never_move(self):
        name = 'saara_02'
        a, b = frame_at(self.path(name + '.mp4'), 0.0), frame_at(self.path(name + '.mp4'), 6.0)
        H = a.height
        for box in ((0, 0, a.width, A.TOP_STATIC), (0, H - P.footer_h, a.width, H)):
            d = np.abs(np.asarray(a.crop(box)).astype(int) - np.asarray(b.crop(box)).astype(int))
            self.assertLess(d.mean(), 4.0, box)

    def test_a_photograph_is_faded_not_wiped(self):
        info = A.analyse(Image.open(self.path('mukhya_1_01_cover.jpg')))
        self.assertGreater(info['photo_end'], 600)
        self.assertLess(len(info['bands']), 8)     # the text below it, not the photo

    def test_the_reveal_is_quick_and_the_hold_is_long_enough_to_read(self):
        for name in ('saara_01_cover', 'saara_02', 'mukhya_1_02_points'):
            total = duration(self.path(name + '.mp4'))
            self.assertGreaterEqual(total, Motion.anim_hold + 1.5, name)
            self.assertLessEqual(total, Motion.anim_hold + Motion.anim_reveal_max
                                 + Motion.anim_start + Motion.anim_line_max + 1, name)

    def test_the_schedule_names_the_videos(self):
        with frozen(NOW):
            from brand import copy as C
            plan = C.publishing_plan(has_saara=True, saara_last='saara_05_sources.jpg',
                                     animated=True)
        self.assertIn('saara_01_cover.mp4', plan[0].asset)
        self.assertIn('saara_05_sources.mp4', plan[0].asset)


if __name__ == '__main__':
    unittest.main()
