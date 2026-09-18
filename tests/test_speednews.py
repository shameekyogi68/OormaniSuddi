"""
ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — the quick-news reel, and the faults it was built to end. D81.
==============================================================================
The first speed-news reel was a side script. Watched frame by frame it had
fourteen faults, and most of them were invisible to every check this project
already had — which is the reason each one is asserted here rather than
trusted to the next render:

  * the wipe sliced Kannada headlines mid-akshara on every cut
  * it was laid out in the STORIES safe zone, so headlines ran under the
    like/comment/share rail and the footer sat under the caption
  * the anchor's words skipped the pronunciation normaliser (D53)
  * it held every story for a floor, then closed on eight seconds of logo
  * a duration cap shorter than the narration put two voices on at once
  * it mastered to −11.8 LUFS against a house −14
  * the Chief Editor gate never saw the file, because of its name
  * its caption was typed into the script, and said "swipe" on a video
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest

from brand import speednews as sn
from brand.content import Story, Edition, Photo, OWN_REPORTING
from brand.tokens import Motion, Limits, fmt


def story(headline='ಬೇಳೂರು ಗ್ರಾಮ ಪಂಚಾಯಿತಿಗೆ ಲೋಕಾಯುಕ್ತ ಅಧಿಕಾರಿಗಳ ದಾಳಿ',
          location='ಕುಂದಾಪುರ', **kw) -> Story:
    base = dict(headline=headline, category='civic', location=location,
                sources=[OWN_REPORTING], verified_by='Gautam Paduvari')
    base.update(kw)
    return Story(**base)


def _size():
    F = fmt('reel')
    return F.w, F.h


class NoWipeEverCutsAHeadline(unittest.TestCase):

    def setUp(self):
        W, H = _size()
        ed = Edition(stories=[story() for _ in range(4)], edition_no=1)
        self.tl = sn.Timeline(sn.items_for(ed), [4.0] * 4, Motion.speed_end,
                              ed.date_kn, W, H)

    def test_story_text_is_gone_for_the_whole_of_every_wipe(self):
        XF = Motion.speed_cross
        for s0 in self.tl.starts[1:]:
            for k in range(11):
                t = s0 + XF * k / 10
                self.assertEqual(self.tl.text_opacity(t), 0.0,
                                 f'story text on screen mid-wipe at {t:.2f}s')

    def test_the_first_headline_is_up_on_frame_zero(self):
        """D39: the news is on frame 0, not a build that starts from blank."""
        self.assertEqual(self.tl.text_opacity(0.0), 1.0)

    def test_each_later_headline_is_fully_up_while_its_story_is_on(self):
        for i, s0 in enumerate(self.tl.starts[1:-1], 1):
            self.assertEqual(self.tl.text_opacity(s0 + 1.5), 1.0, f'story {i + 1}')


class ItLivesInTheReelsSafeZone(unittest.TestCase):

    def test_the_story_block_clears_the_action_rail_and_the_caption(self):
        W, H = _size()
        sl, st, sr, sb = fmt('reel').safe
        L = sn.Layout(W, H)
        long = ('ಉಡುಪಿ ಜಿಲ್ಲೆಯ ಕುಂದಾಪುರ ತಾಲೂಕಿನ ಬೇಳೂರು ಗ್ರಾಮ ಪಂಚಾಯಿತಿ '
                'ಕಚೇರಿಗೆ ಲೋಕಾಯುಕ್ತ ಅಧಿಕಾರಿಗಳ ತಂಡ ದಾಳಿ ನಡೆಸಿದೆ')
        it = sn.items_for(Edition(stories=[story(long)], edition_no=1))[0]
        sl_ = sn.StorySlate(it, L, 0, 4.0)
        x, y = sl_.block_xy
        self.assertLessEqual(x + sl_.block.width, W - sr,
                             'the headline runs under the like/share rail')
        self.assertLessEqual(y + sl_.block.height, H - sb,
                             'the story block sits under the caption overlay')
        self.assertGreaterEqual(y, st)

    def test_it_is_the_reel_format_not_the_story_format(self):
        """fmt('story') has a 72px right margin — the first cut used it."""
        L = sn.Layout(*_size())
        self.assertEqual(L.W - L.x1, fmt('reel').safe[2])
        self.assertGreater(fmt('reel').safe[2], fmt('story').safe[2])


class TheAnchorsWordsAreNormalised(unittest.TestCase):

    def test_what_is_said_goes_through_the_house_normaliser(self):
        """D53. The first version called the TTS engine raw."""
        said = sn.spoken_text('ಉಡುಪಿ', 'ಲಕ್ಷಾಂತರ ರೂ. ವಂಚನೆ')
        self.assertNotIn('ರೂ.', said)

    def test_the_place_is_not_said_twice(self):
        said = sn.spoken_text('ಉಡುಪಿ', 'ಉಡುಪಿ ಕಾಂಗ್ರೆಸ್ ಅಧ್ಯಕ್ಷರ ಅಧಿಕಾರ ಸ್ವೀಕಾರ')
        self.assertEqual(said.count('ಉಡುಪಿ'), 1)

    def test_a_latin_dateline_is_not_put_on_screen(self):
        """The chip already says the place; "Karkala:" is a pasted title."""
        st = story('Karkala: ಜ್ವರದಿಂದ ವ್ಯಕ್ತಿ ಸಾವು', 'ಕಾರ್ಕಳ')
        self.assertEqual(sn.screen_line(st), 'ಜ್ವರದಿಂದ ವ್ಯಕ್ತಿ ಸಾವು')

    def test_a_reel_line_wins_over_the_headline(self):
        st = story(reel_line='ಬೇಳೂರು ಪಂಚಾಯಿತಿಗೆ ಲೋಕಾಯುಕ್ತ ದಾಳಿ')
        self.assertEqual(sn.screen_line(st), 'ಬೇಳೂರು ಪಂಚಾಯಿತಿಗೆ ಲೋಕಾಯುಕ್ತ ದಾಳಿ')


class ItIsQuickAndItNeverTalksOverItself(unittest.TestCase):

    def test_a_story_is_never_shorter_than_its_own_narration(self):
        """A cap below the narration started the next story's voice on top
        of this one's, on the first real render."""
        XF = Motion.speed_cross
        for i, vo in enumerate([2.0, 4.8, 6.2, 8.5]):
            d = sn.story_seconds(i, vo)
            lead = sn.LEAD_FIRST if i == 0 else sn.LEAD_NEXT
            this_voice_ends = lead + vo
            next_voice_starts = d - XF + sn.LEAD_NEXT
            self.assertGreater(next_voice_starts, this_voice_ends + 0.2, vo)

    def test_the_day_is_held_under_the_reel_cap_by_leaving_out_the_tail(self):
        durs, end, n = sn.plan([5.5] * 12, 1.8)
        total = sum(durs) + end - n * Motion.speed_cross
        self.assertLessEqual(total, Limits.reel_target_max)
        self.assertLess(n, 12)
        self.assertEqual(len(durs), n)

    def test_a_short_day_keeps_every_story(self):
        durs, end, n = sn.plan([4.0] * 5, 1.8)
        self.assertEqual(n, 5)

    def test_the_end_card_is_a_follow_not_a_speech(self):
        _d, end, _n = sn.plan([4.0] * 3, 1.6)
        self.assertLessEqual(end, 2.5)


class TheAudioIsMasteredToTheHouseLevel(unittest.TestCase):

    def _tone(self, path, seconds=6, vol=0.9, tail=0.0):
        af = f'sine=frequency=440:duration={seconds},volume={vol}'
        if tail:
            af += f',apad=pad_dur={tail}'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                        '-i', af, '-ar', '48000', path], check=True)

    def _lufs(self, path):
        out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path,
                              '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr
        import re
        return float(re.findall(r'I:\s+(-?[\d.]+)\s+LUFS', out)[-1])

    def test_two_pass_lands_on_minus_fourteen(self):
        """Single-pass loudnorm on the first reel landed at −11.8."""
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, 'a.wav'), os.path.join(d, 'b.wav')
            self._tone(src)
            sn.master_loudness(src, dst)
            self.assertAlmostEqual(self._lufs(dst), Limits.lufs, delta=0.6)

    def test_the_tts_padding_at_the_end_of_a_clip_is_trimmed(self):
        from brand.voice import get_audio_duration
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, 'a.wav'), os.path.join(d, 'b.wav')
            self._tone(src, seconds=2, tail=0.6)
            sn.tighten(src, dst, tempo=1.0)
            self.assertLess(get_audio_duration(dst), 2.25)


class TheGateActuallyReviewsIt(unittest.TestCase):

    def test_roundup_mp4_is_checked_like_any_other_reel(self):
        """It was once rendered as roundup_reel_9x16.mp4, a name the gate's
        pattern never matched, and cleared with no video check at all."""
        from brand import review as R
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                            '-i', 'color=c=black:s=108x192:d=1', '-c:v',
                            'libx264', os.path.join(d, 'roundup.mp4')], check=True)
            rep = R.review(d)
            hit = [f for f in rep.findings if f.where == 'roundup.mp4']
            self.assertTrue(hit, 'the gate did not look at roundup.mp4')
            self.assertIn('SND-01', {f.code for f in hit})


class TheCaptionFitsAVideo(unittest.TestCase):

    def setUp(self):
        from brand import copy as C
        ed = Edition(stories=[story(), story('ಬಂಟಕಲ್ಲು ವಿದ್ಯಾರ್ಥಿಗೆ ಕರಾಟೆ ಸ್ವರ್ಣ', 'ಕಾಪು'),
                              story('ಮಲ್ಪೆ ಬಂದರು ಪರಿಶೀಲನೆ', 'ಉಡುಪಿ')], edition_no=1)
        self.cap = C.for_roundup(ed, 38.2).instagram

    def test_it_does_not_tell_anyone_to_swipe_a_video(self):
        self.assertNotIn('ಸ್ವೈಪ್', self.cap)

    def test_it_discloses_the_synthetic_anchor(self):
        from brand.tokens import Brand
        self.assertIn(Brand.voice_disclosure_kn, self.cap)

    def test_every_story_is_listed_with_its_place(self):
        for place in ('ಕುಂದಾಪುರ', 'ಕಾಪು', 'ಉಡುಪಿ'):
            self.assertIn(place, self.cap)


class ItIsTheDailyReel(unittest.TestCase):

    def _formats(self, n):
        import json
        from scripts.pick_formats import formats_for_edition
        data = {'date': '2026-09-18T08:00:00+05:30', 'edition_no': 1,
                'stories': [{'headline': 'ಉಡುಪಿಯಲ್ಲಿ ಭಾರಿ ಮಳೆ', 'category': 'civic',
                             'location': 'ಉಡುಪಿ', 'sources': ['ಉದಯವಾಣಿ'],
                             'source_urls': ['https://example.com/x']}] * n}
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                         encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        try:
            return formats_for_edition(fh.name)[0]
        finally:
            os.unlink(fh.name)

    def test_three_or_more_stories_go_out_as_speed_news(self):
        self.assertEqual(self._formats(3), ['carousel', 'roundup'])

    def test_a_thin_day_does_not_get_a_one_story_roundup(self):
        self.assertNotIn('roundup', self._formats(2))

    def test_the_schedule_carries_it_and_keeps_the_reel_gap(self):
        from brand import copy as C
        plan = C.publishing_plan(n_reels=1, has_roundup=True,
                                 has_story_card=False, has_broadsheet=False)
        assets = [s.asset for s in plan]
        self.assertTrue(any('roundup.mp4' in a for a in assets))
        times = [s.at for s in plan if s.platform == 'Instagram Reels']
        self.assertEqual(len(times), len(set(times)), 'two reels at one time')


if __name__ == '__main__':
    unittest.main()
