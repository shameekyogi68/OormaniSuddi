"""
Legibility, asserted.
=====================
`tokens.Limits.contrast_min = 4.5` sat in the file with nothing reading it, and
`19px minimum type` was a rule about the canvas rather than about the screen.
Both are now arithmetic, and arithmetic can be tested. See D60.

The one that matters most is `test_gold_is_never_legible_on_paper`: gold 500 on
paper measures about 1.7:1, and nothing in the token system stopped a template
reaching for `Role.accent` on a light greeting ground. It would have shipped
eventually, on a festival poster, where nobody would have called it a bug.
"""
from __future__ import annotations

import unittest

from brand import legibility as L
from brand.tokens import C, Role, T, Limits, FORMATS


class ContrastIsEnforcedNotHoped(unittest.TestCase):

    def test_every_house_pair_clears_its_floor(self):
        failures = L.audit_tokens()
        self.assertFalse(
            failures,
            '\n  ' + '\n  '.join(failures)
            + '\n\nThese are the colour pairs templates are allowed to set. '
              'A pair below the floor is not a taste question.')

    def test_the_ratio_matches_the_wcag_worked_example(self):
        """White on black is 21:1. If this drifts, the formula is wrong."""
        self.assertAlmostEqual(L.ratio((255, 255, 255), (0, 0, 0)), 21.0, places=2)
        self.assertAlmostEqual(L.ratio((0, 0, 0), (0, 0, 0)), 1.0, places=2)

    def test_order_does_not_change_the_ratio(self):
        a, b = Role.text_hi, Role.page
        self.assertAlmostEqual(L.ratio(a, b), L.ratio(b, a), places=6)

    def test_gold_is_never_legible_on_paper(self):
        """The pair the bronze token exists for."""
        self.assertLess(
            L.ratio(Role.accent, C.paper_50), 2.0,
            'gold on paper has become readable — if the gold changed, the '
            'whole accent decision needs revisiting deliberately')
        self.assertGreaterEqual(
            L.ratio(Role.accent_on_paper, C.paper_50), Limits.contrast_min,
            'Role.accent_on_paper is the ONLY accent allowed on a light '
            'ground; it must clear the body floor')

    def test_translucent_colours_are_measured_after_compositing(self):
        """A hairline at 14% is not a 14%-contrast colour."""
        raw = Role.hairline
        self.assertEqual(len(raw), 4, 'hairline is meant to be translucent')
        composited = L.over(raw, Role.page)
        self.assertEqual(len(composited), 3)
        # Compositing a light colour at low alpha over ink must land near ink.
        self.assertLess(sum(composited), sum(C.paper_50))

    def test_alert_red_clears_the_display_floor_on_the_page(self):
        self.assertGreaterEqual(L.ratio(Role.alert, Role.page),
                                Limits.gold_on_light_min)


class SizeIsMeasuredWhereItIsRead(unittest.TestCase):

    def test_every_format_has_a_feed_width_and_a_primary_step(self):
        for key in FORMATS:
            self.assertIn(key, L.FEED_WIDTH,
                          f'{key} has no first-sight width; add one, because '
                          f'"designed at 1080" is not a viewing condition')
            self.assertIn(key, L.PRIMARY_STEP,
                          f'{key} does not declare which step sells the post')

    def test_the_line_that_sells_the_post_survives_first_sight(self):
        bad = []
        for key in FORMATS:
            msgs = L.audit_sizes(key)
            bad.extend(msgs)
        self.assertFalse(bad, '\n  ' + '\n  '.join(bad))

    def test_effective_size_shrinks_with_the_viewing_width(self):
        # A carousel slide seen in a 150px profile grid loses far more than a
        # 4:5 post seen at 420px. If this inverts, the maths is backwards.
        self.assertLess(L.effective_px(T.h1[0], 'square'),
                        L.effective_px(T.h1[0], 'post'))

    def test_a_provenance_line_is_not_readable_in_a_profile_grid(self):
        """Stated as a fact, so nobody relies on the frame alone for disclosure.

        This is WHY Photo.disclosure also goes into the caption: at 150px the
        credit strip is under 3px tall and is not a disclosure to anyone.
        """
        self.assertLess(L.effective_px(T.micro[0], 'square'),
                        Limits.min_effective_px)

    def test_the_4k_bulletin_is_not_penalised_for_being_4k(self):
        """Same design at twice the size must not read as half as legible."""
        a = L.effective_px(T.h1[0], 'bulletin')
        b = L.effective_px(T.h1[0] * 2, 'bulletin_4k')
        self.assertAlmostEqual(a, b, places=3)


if __name__ == '__main__':
    unittest.main()
