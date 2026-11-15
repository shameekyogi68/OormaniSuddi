"""D152 — six faults in the ಮುಖ್ಯ ಸುದ್ದಿ package and the reel caption that every reviewer passed.

  * the picture's honesty label cut to "ಎಐ ರಚಿತ ಚಿತ್ರ …" on the cover and the source slide;
  * a clock time split from its AM/PM across two lines of a slide;
  * the schedule telling the editor to post "1 separate videos" when there are three;
  * a warning sign in front of a takeaway that warns of nothing;
  * a silent carousel's caption saying "this voice is computer-made";
  * the reel — which IS read by a computer voice — not saying so anywhere.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from brand import copy as C                                    # noqa: E402
from brand import paper as PP                                  # noqa: E402
from brand import typo                                         # noqa: E402
from brand.content import Edition, Photo, Story, OWN_REPORTING  # noqa: E402
from brand.tokens import Brand                                 # noqa: E402

LONG = 'ಕರಾವಳಿಯ ಹಸಿರು ಪ್ರಕೃತಿಯ ನಡುವೆ ಸಂಚರಿಸುತ್ತಿರುವ ವಂದೇ ಭಾರತ್ ಎಕ್ಸ್‌ಪ್ರೆಸ್ ರೈಲು'


def story(**kw) -> Story:
    base = dict(
        headline='ಬೆಂಗಳೂರು-ಗೋವಾ ವಂದೇ ಭಾರತ್: ಕರಾವಳಿ ಮಾರ್ಗದ ವೇಳಾಪಟ್ಟಿ ಪ್ರಕಟ',
        category='civic', location='ಕುಂದಾಪುರ',
        points=['ವಾರದಲ್ಲಿ 6 ದಿನ ಸಂಚಾರ.'],
        takeaway='ಕರಾವಳಿ ಹಾಗೂ ಬೆಂಗಳೂರು ನಡುವೆ ಅತ್ಯಂತ ವೇಗದ ರೈಲು ಸಂಪರ್ಕ.',
        sources=[OWN_REPORTING], verified_by='Gautam Paduvari',
        photo=Photo('x.jpg', nature='ai', credit='ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own',
                    caption=LONG, approved_by='Gautam Paduvari'))
    base.update(kw)
    return Story(**base)


class APictureLabelIsNeverCutToDots(unittest.TestCase):

    def test_the_forms_go_from_everything_to_the_bare_label(self):
        d = story().photo.disclosures
        self.assertEqual(d[0], story().photo.disclosure)
        self.assertEqual(d[-1], 'ಎಐ ರಚಿತ ಚಿತ್ರ')
        self.assertIn('ಎಐ ರಚಿತ ಚಿತ್ರ  •  ಕೃಪೆ: ಊರ್ಮನಿ ಸುದ್ದಿ', d)
        for form in d:
            self.assertTrue(form.startswith('ಎಐ ರಚಿತ ಚಿತ್ರ'), form)

    def test_what_fits_is_shown_whole(self):
        ph = story().photo
        f = typo.font_for(ph.disclosure, 'kn_var', 52, weight=600)
        full = typo.text_width(ph.disclosure, f)
        for room in (full + 1, full * 0.6, full * 0.3, full * 0.16):
            got = PP.fit_disclosure(ph.disclosures, f, room)
            self.assertNotIn('…', got, room)
            self.assertIn(got, ph.disclosures)
            self.assertLessEqual(typo.text_width(got, f), room)
        self.assertEqual(PP.fit_disclosure(ph.disclosures, f, full + 1), ph.disclosure)


class AClockTimeStaysWithItsAmPm(unittest.TestCase):
    LINE = ('ಸಂಖ್ಯೆ 26655 ಯಶವಂತಪುರದಿಂದ 7:35 AM ಹೊರಟು ಮಂಗಳೂರು (3:05 PM), ಉಡುಪಿ (4:20 PM), '
            'ಕುಂದಾಪುರ (4:38 PM), ಬೈಂದೂರು (5:20 PM) ಮಾರ್ಗವಾಗಿ 8:55 PM ಮಡಗಾಂವ್ ತಲುಪಲಿದೆ.')

    def test_no_line_ends_on_a_bare_time_at_any_width(self):
        f = typo.font('kn_var', 60, weight=600)
        for w in range(700, 2400, 37):
            for balance in (True, False):
                lines = typo.wrap(self.LINE, f, w, balance=balance)
                self.assertEqual(' '.join(lines), self.LINE)       # nothing lost, nothing added
                for ln in lines[:-1]:
                    self.assertNotRegex(ln, r'\d{1,2}:\d{2}$', (w, lines))
                for ln in lines:
                    self.assertNotRegex(ln, r'^(AM|PM)\b', (w, lines))


class TheScheduleCountsTheSlides(unittest.TestCase):

    def test_three_slides_are_three_videos(self):
        plan = C.publishing_plan(mukhya=[(1, False, 'mukhya_1_03_source.jpg')], animated=True)
        text = C.plan_text(plan)
        self.assertIn('ONE carousel post of 3 separate videos', text)
        self.assertNotIn('of 1 separate', text)

    def test_the_second_set_of_the_day_is_counted_the_same(self):
        plan = C.publishing_plan(mukhya=[(2, False, 'mukhya_2_03_source.jpg')], animated=True)
        self.assertIn('of 3 separate videos', C.plan_text(plan))


class TheCaptionSaysOnlyWhatIsTrue(unittest.TestCase):

    def test_a_takeaway_is_pointed_to_not_warned_about(self):
        cap = C.instagram_caption(story())
        self.assertNotIn('⚠', cap)
        self.assertIn('👉 ಕರಾವಳಿ ಹಾಗೂ ಬೆಂಗಳೂರು', cap)

    def test_a_silent_carousel_does_not_claim_a_voice(self):
        self.assertNotIn(Brand.voice_disclosure_kn, C.instagram_caption(story()))
        self.assertNotIn(Brand.voice_disclosure_kn, C.for_story(story()).instagram)
        self.assertIn(Brand.voice_disclosure_kn, C.instagram_caption(story(), voiced=True))

    def test_the_reel_says_its_voice_is_computer_made(self):
        names = [n for n in sorted(os.listdir(os.path.join(ROOT, 'editions')))
                 if n.startswith('2026-') and n.endswith('.json')]
        seen = 0
        for name in names[-12:]:
            with open(os.path.join(ROOT, 'editions', name), encoding='utf-8') as fh:
                ed = Edition.from_dict(json.load(fh))
            saara = [s for s in ed.stories if s.segment == 'saara']
            if len(saara) < 2:
                continue
            ed.stories = saara
            cap = C.for_saara_reel(ed).instagram
            self.assertIn(Brand.voice_disclosure_kn, cap, name)
            self.assertLess(cap.index(Brand.voice_disclosure_kn), cap.index('#'), name)
            seen += 1
        self.assertGreater(seen, 5)


if __name__ == '__main__':
    unittest.main()
