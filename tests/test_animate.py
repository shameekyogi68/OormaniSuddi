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
from brand.tokens import C as PALETTE, Motion, Paper as P  # noqa: E402

P_RED = PALETTE.red_500
M_OUT = Motion.anim_out

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

    def test_a_slide_is_never_blank_and_never_fully_there_at_frame_zero(self):
        """A slide after the cover opens as paper, the chrome and a faint
        pencil outline of its layout (D101): the ink is not there yet, and the
        page is not empty either."""
        name = 'saara_02'
        f0 = np.asarray(frame_at(self.path(name + '.mp4'), 0.0)).astype(int)
        info, _tl = self.info(name)
        paper = np.array(info['paper'])
        for b in info['bands']:
            if b.rule:
                continue
            diff = np.abs(f0[b.y0:b.y1, b.x0:b.x1] - paper).sum(axis=2)
            self.assertLess((diff > 200).mean(), 0.02, f'ink already at y={b.y0}')
            self.assertGreater((diff > 12).mean(), 0.005, f'no pencil outline at y={b.y0}')

    def test_a_cover_is_the_finished_slide_from_the_first_frame(self):
        """Instagram takes the post's thumbnail from the first video, so the
        cover must be whole at frame 0 — and from then on nothing passes over
        it but the running order behind its teasers (D104)."""
        for name in ('saara_01_cover', 'mukhya_1_01_cover'):
            info, tl = self.info(name)
            mp4 = self.path(name + '.mp4')
            still = np.asarray(frame_at(mp4, 0.5)).astype(int)
            lit = np.zeros(still.shape[:2], bool)
            for y0, y1, x0 in info['teasers']:
                lit[y0:y1, max(0, x0 - 22):] = True
            for t in (0.0, 1.0, 1.8, 3.0, 5.0):
                f = np.asarray(frame_at(mp4, t)).astype(int)
                d = np.abs(f - still).sum(axis=2)
                self.assertLess(d[~lit].mean(), 1.5, f'{name} at {t:.1f}s: something passed over it')
                # and no line of text is thinner than it should be
                for b in info['bands']:
                    if b.rule:
                        continue
                    ink_f = (np.abs(f[b.y0:b.y1, b.x0:b.x1] - np.array(info['paper'])).sum(axis=2) > 200).mean()
                    ink_s = (np.abs(still[b.y0:b.y1, b.x0:b.x1] - np.array(info['paper'])).sum(axis=2) > 200).mean()
                    self.assertGreater(ink_f, ink_s * 0.9, f'{name} at {t:.1f}s, y={b.y0}')

    def test_the_running_order_lights_one_teaser_at_a_time(self):
        """D104 — the ಸುದ್ದಿ ಸಾರ cover: a gold underlay and a red tick step down
        the teasers, one each turn, in order; the lead is never lit; the
        loop comes round in step."""
        name = 'saara_01_cover'
        info, tl = self.info(name)
        n_saara = len(Edition.load(FIXTURE).segment('saara'))
        self.assertEqual(len(info['teasers']), n_saara - 1)
        order = tl['order']
        self.assertIsNotNone(order)
        mp4 = self.path(name + '.mp4')
        rest = np.asarray(frame_at(mp4, 0.5)).astype(int)
        gold = np.array(PALETTE.gold_500)
        lead_bottom = min(y0 for y0, _y1, _x in info['teasers'])
        for k in range(len(info['teasers'])):
            t = order['start'] + (k + 0.5) * order['step']    # the middle of turn k
            f = np.asarray(frame_at(mp4, t)).astype(int)
            for j, (y0, y1, x0) in enumerate(info['teasers']):
                warm = (np.abs(f[y0:y1, x0:x0 + 900] - rest[y0:y1, x0:x0 + 900]).sum(axis=2) > 25).mean()
                if j == k:
                    self.assertGreater(warm, 0.3, f'turn {k}: teaser {j} is not lit')
                else:
                    self.assertLess(warm, 0.02, f'turn {k}: teaser {j} is lit too')
            # the lead, its kicker and the masthead are never touched
            self.assertLess(np.abs(f[:lead_bottom - 10] - rest[:lead_bottom - 10]).mean(), 1.0)
        # the rest beat, and whole rounds: the last frame is the first
        rnd = (len(info['teasers']) + 1) * order['step']
        self.assertAlmostEqual((order['end'] - order['start']) / rnd,
                               round((order['end'] - order['start']) / rnd), places=6)
        first = np.asarray(frame_at(mp4, 0.0)).astype(int)
        last = np.asarray(frame_at(mp4, duration(mp4) - 0.05)).astype(int)
        self.assertLess(np.abs(first - last).mean(), 1.5)

    def test_a_cover_with_no_teasers_keeps_the_swipe_nudge(self):
        """The ಮುಖ್ಯ ಸುದ್ದಿ cover has no teasers: no running order, and its
        chevrons still ask for the swipe."""
        info, tl = self.info('mukhya_1_01_cover')
        self.assertEqual(info['teasers'], [])
        self.assertIsNone(tl['order'])
        self.assertTrue(tl['nudges'])

    def test_any_frame_you_could_pick_as_a_thumbnail_is_finished(self):
        """The cover picker lets the editor scrub to any frame. From the end
        of the reveal to the start of the loop dissolve, every slide is its
        finished self, so one choice of frame is safe for all of them."""
        for slides in self.carousels():
            for j in slides:
                name = j[:-4]
                _i, tl = self.info(name)
                mp4 = self.path(name + '.mp4')
                still = np.asarray(Image.open(self.path(j)).convert('RGB')).astype(int)
                safe_from = tl['reveal'] + 0.1
                safe_to = tl['total'] - M_OUT - 0.1
                self.assertLessEqual(safe_from, 4.0, name)       # early enough to pick
                for t in (safe_from, (safe_from + safe_to) / 2, safe_to - 0.2):
                    f = np.asarray(frame_at(mp4, t)).astype(int)
                    self.assertLess(np.abs(f - still).mean(), 3.5, f'{name} at {t:.1f}s')

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

    def carousels(self):
        saara = sorted(f for f in self.files if f.startswith('saara_') and f.endswith('.jpg'))
        mukhya = sorted(f for f in self.files if f.startswith('mukhya_1_') and f.endswith('.jpg'))
        return [saara, mukhya]

    def test_a_carousel_is_separate_slides_not_one_video(self):
        """D100: one .mp4 per slide, each a single 4:5 slide of its own —
        Instagram does the swipe between them."""
        for slides in self.carousels():
            self.assertGreaterEqual(len(slides), 3)
            for j in slides:
                mp4 = self.path(j[:-4] + '.mp4')
                r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                    '-show_entries', 'stream=width,height', '-of', 'csv=p=0',
                                    mp4], capture_output=True, text=True)
                self.assertEqual(r.stdout.strip(), '1080,1350', j)
                self.assertLessEqual(duration(mp4), Motion.anim_reveal_max
                                     + Motion.anim_hold_max + Motion.anim_out + 0.5, j)

    def test_every_seam_is_continuous_across_a_swipe(self):
        """D100: mid-swipe, slide N's right edge sits against slide N+1's left
        edge. There they must agree — the footer hairline runs on, and the
        edge tab meets the landing mark as one pill — on the stills and on the
        video frame the reader swipes into."""
        for slides in self.carousels():
            for left, right in zip(slides, slides[1:]):
                a = np.asarray(Image.open(self.path(left)).convert('RGB')).astype(int)
                info = A.analyse(Image.open(self.path(left)))
                y0 = info['photo_end']            # a photograph has its own edge
                for b, what in (
                        (np.asarray(Image.open(self.path(right)).convert('RGB')).astype(int), 'still'),
                        (np.asarray(frame_at(self.path(right[:-4] + '.mp4'), 0.0)).astype(int),
                         'frame 0')):
                    ea, eb = a[y0:, -1], b[y0:, 0]
                    self.assertLess(np.abs(ea - eb).mean(), 4.0, f'{left} → {right} ({what})')
                    red = np.array(P_RED)          # the pill: over the full height
                    ra = np.abs(a[:, -1] - red).sum(axis=1) < 90
                    rb = np.abs(b[:, 0] - red).sum(axis=1) < 90
                    self.assertTrue(ra.any() and rb.any(), f'{left} → {right}: no tab / landing')
                    self.assertLessEqual(np.logical_xor(ra, rb).sum(), 4,
                                         f'{left} → {right} ({what}): the pill does not meet')
            # The first slide's left edge and the last slide's right edge are margins.
            first = np.asarray(Image.open(self.path(slides[0])).convert('RGB')).astype(int)
            last = np.asarray(Image.open(self.path(slides[-1])).convert('RGB')).astype(int)
            fy = A.analyse(Image.open(self.path(slides[0])))['photo_end']
            for col in (first[fy:, 0], last[:, -1]):
                self.assertLess((np.abs(col - col[-20]).sum(axis=1) > 60).mean(), 0.01)

    def test_the_schedule_names_the_videos(self):
        with frozen(NOW):
            from brand import copy as C
            plan = C.publishing_plan(has_saara=True, saara_last='saara_05_sources.jpg',
                                     animated=True)
        self.assertIn('saara_01_cover.mp4', plan[0].asset)
        self.assertIn('saara_05_sources.mp4', plan[0].asset)
        self.assertIn('ONE carousel post of 5 separate videos', plan[0].what)
        self.assertIn('Never join them', plan[0].what)
        self.assertIn('THUMBNAIL', plan[0].what)


if __name__ == '__main__':
    unittest.main()


class TheDeliveryFolder(unittest.TestCase):
    """D102 — what the editor opens after a real render: the .mp4 slides to
    post; every finished still kept in _review/ for the inspector; and a
    render that cannot hang, however it was started."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, 'out')
        ed = Edition.load(FIXTURE)
        cls.ed = os.path.join(cls.tmp.name, 'ed.json')
        with open(FIXTURE, encoding='utf-8') as fh:
            data = fh.read()
        with open(cls.ed, 'w', encoding='utf-8') as fh:
            fh.write(data)
        cls.r = subprocess.run(
            [sys.executable, 'render.py', cls.ed, '--only', 'saara', '--out', cls.out,
             '--at', NOW],
            cwd=_ROOT, capture_output=True, text=True, timeout=900)
        cls.n_stories = len(ed.segment('saara'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_folder_holds_the_videos_to_post_not_the_stills(self):
        files = os.listdir(self.out)
        mp4 = sorted(f for f in files if f.startswith('saara_') and f.endswith('.mp4'))
        self.assertGreaterEqual(len(mp4), 3, self.r.stdout[-600:] + self.r.stderr[-600:])
        self.assertFalse([f for f in files if f.startswith('saara_') and f.endswith('.jpg')])

    def test_every_finished_still_is_kept_for_the_inspector(self):
        review = os.path.join(self.out, '_review')
        for f in os.listdir(self.out):
            if f.startswith('saara_') and f.endswith('.mp4'):
                still = os.path.join(review, f[:-4] + '.jpg')
                self.assertTrue(os.path.exists(still), f)
                # the still is the FINISHED slide: it matches the held frame
                info = A.analyse(Image.open(still), cover='_cover' in f)
                tl = A.plan(info, cover='_cover' in f)
                held = np.asarray(frame_at(os.path.join(self.out, f), tl['reveal'] + 0.3)).astype(int)
                s = np.asarray(Image.open(still).convert('RGB')).astype(int)
                self.assertLess(np.abs(held - s).mean(), 3.0, f)

    def test_the_schedule_points_at_the_videos(self):
        with open(os.path.join(self.out, 'schedule.txt'), encoding='utf-8') as fh:
            text = fh.read()
        self.assertIn('saara_01_cover.mp4', text)
        self.assertIn('separate videos', text)
        self.assertIn('THUMBNAIL', text)

    def test_a_render_started_from_stdin_does_not_hang(self):
        """2026-10-04: a render typed into `python3 -` spawned workers that
        could not re-import their parent, died, and were replaced for ten
        minutes. It now falls back to one slide at a time."""
        import shutil
        srcs = []
        for k, name in enumerate(('saara_02.jpg', 'saara_03.jpg')):   # two: the pool's path
            dst = os.path.join(self.tmp.name, f'stdin_{k}.jpg')
            shutil.copy(os.path.join(self.out, '_review', name), dst)
            srcs.append(dst)
        code = (f'import sys; sys.path.insert(0, {_ROOT!r})\n'
                f'from brand.animate import animate_all\n'
                f'print(animate_all({srcs!r}))\n')
        r = subprocess.run([sys.executable, '-'], input=code, cwd=_ROOT,
                           capture_output=True, text=True, timeout=240)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        for p_ in srcs:
            self.assertTrue(os.path.exists(p_[:-4] + '.mp4'), p_)
