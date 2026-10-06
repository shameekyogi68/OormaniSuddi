"""
A render folder holds this render, and a signature holds this package.
=====================================================================
D107: re-rendering a day with one story fewer used to leave the previous
render's last slides in the folder, and schedule.txt — derived from the folder
— told the editor to post them. Each format now clears its own output first,
and the gate refuses a carousel that is not one clean sequence (PKG-06).

D108: SIGNOFF.json used to survive a re-render, so APPROVAL.md read "Signed.
Cleared to publish." over slides nobody had looked at. A signature now carries
the fingerprint of what gets posted.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest

import render
from brand import review as R


def touch(folder: str, *names: str, body: bytes = b'x') -> None:
    for n in names:
        path = os.path.join(folder, n)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as fh:
            fh.write(body)


class ACarouselIsOneCleanSequence(unittest.TestCase):

    def test_a_clean_render_passes(self):
        files = ['saara_01_cover.mp4', 'saara_02.mp4', 'saara_03.mp4',
                 'saara_04_sources.mp4', 'mukhya_1_01_cover.mp4',
                 'mukhya_1_02_points.mp4', 'mukhya_1_03_source.mp4']
        self.assertEqual(R.carousel_sequence_problems(files), [])

    def test_slides_left_over_from_a_longer_render_are_caught(self):
        # Exactly what a six-story day re-rendered as five left behind.
        files = ['saara_01_cover.mp4', 'saara_02.mp4', 'saara_03.mp4',
                 'saara_04.mp4', 'saara_05.mp4', 'saara_05_sources.mp4',
                 'saara_06_sources.mp4']
        self.assertTrue(R.carousel_sequence_problems(files))

    def test_a_gap_is_caught(self):
        files = ['saara_01_cover.jpg', 'saara_03.jpg', 'saara_04_sources.jpg']
        self.assertTrue(R.carousel_sequence_problems(files))

    def test_a_slide_after_the_closing_slide_is_caught(self):
        files = ['mukhya_1_01_cover.mp4', 'mukhya_1_02_source.mp4',
                 'mukhya_1_03_points.mp4']
        self.assertTrue(R.carousel_sequence_problems(files))

    def test_the_gate_raises_pkg_06(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        touch(d, 'saara_01_cover.mp4', 'saara_02_sources.mp4', 'saara_03.mp4')
        codes = {f.code for f in R.review(d).findings}
        self.assertIn('PKG-06', codes)


class AReRenderClearsItsOwnFormatOnly(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        touch(self.d, 'saara_01_cover.mp4', 'saara_07.mp4', 'saara_caption.txt',
              '_review/saara_07.jpg', '_review/feed_sizes.jpg',
              'mukhya_1_01_cover.mp4', 'facebook_group_1.txt',
              'roundup.mp4', 'roundup_cover.jpg', 'SIGNOFF.json', '.edition')

    def left(self) -> set[str]:
        out = set(os.listdir(self.d))
        return out | {f'_review/{f}' for f in os.listdir(os.path.join(self.d, '_review'))}

    def test_rendering_saara_clears_saara_and_nothing_else(self):
        render.clear_previous(self.d, ['saara'])
        left = self.left()
        for gone in ('saara_01_cover.mp4', 'saara_07.mp4', 'saara_caption.txt',
                     '_review/saara_07.jpg', '_review/feed_sizes.jpg'):
            self.assertNotIn(gone, left)
        for kept in ('mukhya_1_01_cover.mp4', 'facebook_group_1.txt',
                     'roundup.mp4', 'roundup_cover.jpg', 'SIGNOFF.json', '.edition'):
            self.assertIn(kept, left)

    def test_a_full_render_clears_a_format_the_day_no_longer_has(self):
        render.clear_previous(self.d, list(render.FORMAT_FILES))
        left = self.left()
        self.assertFalse({'roundup.mp4', 'mukhya_1_01_cover.mp4',
                          'facebook_group_1.txt'} & left)
        self.assertIn('SIGNOFF.json', left)

    def test_every_daily_format_has_a_pattern(self):
        from brand.tokens import Limits
        self.assertEqual(set(render.FORMAT_FILES), set(Limits.daily_templates))

    def test_town_forwards_are_edition_files(self):
        for f in ('forward_Byndoor.txt', 'whatsapp_kundapura_byndoor.txt'):
            self.assertTrue(render.EDITION_FILES.match(f), f)
        for f in ('saara_whatsapp.txt', 'mukhya_1_whatsapp.txt', 'schedule.txt'):
            self.assertFalse(render.EDITION_FILES.match(f), f)


class ASignatureCoversThePackageItWasGivenFor(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        touch(self.d, 'saara_01_cover.mp4', 'saara_02_sources.mp4',
              'saara_caption.txt', 'review_report.json')

    def test_signing_clears_the_package(self):
        R.sign(self.d, 'Gautam Paduvari')
        self.assertTrue(R.is_signed(self.d))

    def test_a_changed_slide_needs_a_new_signature(self):
        R.sign(self.d, 'Gautam Paduvari')
        touch(self.d, 'saara_02_sources.mp4', body=b'a different render')
        self.assertFalse(R.is_signed(self.d))
        self.assertEqual(R.signed_seats(self.d), {})

    def test_a_new_slide_needs_a_new_signature(self):
        R.sign(self.d, 'Gautam Paduvari')
        touch(self.d, 'saara_03.mp4')
        self.assertFalse(R.is_signed(self.d))

    def test_the_gates_own_bookkeeping_does_not_unsign(self):
        R.sign(self.d, 'Gautam Paduvari')
        touch(self.d, 'review_report.json', 'APPROVAL.md', 'build.log',
              body=b'rewritten')
        self.assertTrue(R.is_signed(self.d))

    def test_seats_signed_for_an_earlier_render_do_not_carry_over(self):
        R.sign(self.d, 'Shameek', ('culture',))
        touch(self.d, 'saara_02_sources.mp4', body=b'changed')
        R.sign(self.d, 'Gautam Paduvari', ('taste', 'news'))
        self.assertFalse(R.is_signed(self.d),
                         'culture was signed for slides that no longer exist')
        self.assertNotIn('culture', R.signed_seats(self.d))

    def test_a_signature_from_before_fingerprints_counts_only_if_newer(self):
        state = {s: 'Gautam Paduvari' for s in R.JUDGEMENT_SEATS}
        path = os.path.join(self.d, R.SIGN_FILE)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(state, fh)
        self.assertTrue(R.is_signed(self.d))
        later = time.time() + 60
        os.utime(os.path.join(self.d, 'saara_01_cover.mp4'), (later, later))
        self.assertFalse(R.is_signed(self.d))

    def test_approval_says_the_old_signature_is_stale(self):
        R.sign(self.d, 'Gautam Paduvari')
        touch(self.d, 'saara_02_sources.mp4', body=b'changed')
        body = '\n'.join(R._judgement_block(self.d))
        self.assertIn('different render', body)
        self.assertNotIn('Cleared to publish', body)


if __name__ == '__main__':
    unittest.main()
