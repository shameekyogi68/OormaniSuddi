"""The genuineness contract.

If any of these stop failing, the system has quietly become able to publish
something dishonest. See docs/DECISIONS.md D19.
"""
import os
import sys

# Bootstrap without a relative import, so this file works under every
# invocation: `python3 -m unittest discover tests`, `discover -s tests -t .`,
# `python3 -m tests.test_contract`, and running the file directly.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)   # so relative asset paths in the content resolve as at render time
import unittest
from datetime import datetime, timedelta

from brand.content import (Story, Photo, ContentError, frozen, IST,
                           BREAKING_WINDOW_H)
from brand.qa import preflight


def base(**kw):
    d = dict(headline='ಪರೀಕ್ಷಾ ಶೀರ್ಷಿಕೆ', sources=['ಪರೀಕ್ಷಾ ಮೂಲ'],
             published_at=datetime(2026, 8, 25, 8, 0, tzinfo=IST))
    d.update(kw)
    return Story(**d)


def pic(**kw):
    d = dict(path='assets/monsoon_alert.jpg', credit='ವರದಿಗಾರರಿಂದ', licence='own')
    d.update(kw)
    return Photo(**d)


class Provenance(unittest.TestCase):

    def test_photo_without_credit_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'credit'):
            base(photo=pic(credit='')).validate()

    def test_actual_photo_without_caption_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'caption'):
            base(photo=pic(nature='actual')).validate()

    def test_story_without_sources_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'source'):
            Story(headline='x', sources=[]).validate()

    def test_representative_photo_is_labelled_on_the_card(self):
        s = base(photo=pic(nature='representative', credit='ಸಂಗ್ರಹ')).validate()
        self.assertIn('ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ', s.credit_line)

    def test_unknown_nature_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'nature'):
            base(photo=pic(nature='stock')).validate()


class NotAssertable(unittest.TestCase):

    def test_live_badge_requires_a_real_url(self):
        with self.assertRaisesRegex(ContentError, 'live_url'):
            base(live_url='soon').validate()

    def test_breaking_decays_and_cannot_be_asserted(self):
        with frozen('2026-08-25T10:00+05:30'):
            s = base(category='breaking')
            self.assertTrue(s.is_breaking)
            self.assertEqual(s.validate().category, 'breaking')
        with frozen('2026-08-26T10:00+05:30'):
            s = base(category='breaking')
            self.assertFalse(s.is_breaking)
            self.assertEqual(s.validate().category, 'explainer')  # demoted

    def test_status_is_printed_as_it_stands(self):
        self.assertEqual(base(status='unconfirmed').validate().status_kn,
                         'ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ')


class JsonDoor(unittest.TestCase):

    def test_unknown_field_is_refused_not_ignored(self):
        # A typo'd `source` would otherwise leave `sources` empty and render an
        # unattributed card.
        with self.assertRaisesRegex(ContentError, 'unknown field'):
            Story.from_dict({'headline': 'x', 'source': ['a']})

    def test_round_trip_is_stable(self):
        s = base(deck='ಪರೀಕ್ಷೆ', points=['ಒಂದು', 'ಎರಡು'], photo=pic(credit='ಸಂಗ್ರಹ'))
        again = Story.from_dict(s.to_dict())
        self.assertEqual(again.headline, s.headline)
        self.assertEqual(again.points, s.points)
        self.assertEqual(again.photo.credit, s.photo.credit)
        self.assertEqual(again.published_at, s.published_at)


class Preflight(unittest.TestCase):

    def test_mixed_numerals_fail(self):
        s = base(headline='೨೫ ಜನರಿಗೆ 40 ಕೋಟಿ ರೂ. ಪರಿಹಾರ')
        self.assertTrue(any('numeral' in m for m in preflight(s).fail))

    def test_overlong_headline_fails_for_a_thumbnail(self):
        s = base(headline='ಬ್ರಹ್ಮಾವರ: ಕ್ಷುಲ್ಲಕ ಜಗಳಕ್ಕೆ ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ')
        self.assertTrue(preflight(s, 'thumb').fail)
        self.assertFalse(preflight(s, 'thumb', hook='ಪುತ್ರ ಬಂಧನ').fail)

    def test_clean_story_is_clean(self):
        s = base(deck='ಸಣ್ಣ ಪರಿಚಯ.', location='ಉಡುಪಿ',
                 points=['ಒಂದು ಅಂಶ.', 'ಎರಡನೇ ಅಂಶ.'])
        self.assertEqual(preflight(s).fail, [])


class Licensing(unittest.TestCase):

    def test_photo_without_licence_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'licence'):
            base(photo=Photo(path='a.jpg', credit='X')).validate()

    def test_non_own_licence_needs_a_source(self):
        with self.assertRaisesRegex(ContentError, 'source_url'):
            base(photo=Photo(path='a.jpg', credit='X', licence='cc')).validate()

    def test_own_photo_needs_no_source(self):
        base(photo=pic()).validate()


class CriminalReporting(unittest.TestCase):
    """India: BNS §356, JJ Act 2015 §74, POCSO §23, BNS §72."""

    def test_guilt_cannot_be_asserted_before_conviction(self):
        with self.assertRaisesRegex(ContentError, 'guilt'):
            base(headline='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ', category='crime').validate()

    def test_alleged_framing_is_allowed(self):
        base(headline='ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ: ಪುತ್ರನ ಬಂಧನ', category='crime').validate()

    def test_conviction_allows_plain_past_tense(self):
        base(headline='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರನಿಗೆ ಜೀವಾವಧಿ ಶಿಕ್ಷೆ',
             category='crime', convicted=True).validate()

    def test_non_crime_categories_are_unaffected(self):
        base(headline='ಹಳೆ ಸೇತುವೆ ಕೆಡವಿದ ಪಾಲಿಕೆ', category='civic').validate()

    def test_a_marker_in_the_deck_does_not_clear_the_headline(self):
        """The headline travels alone — a thumbnail, a forward, a screenshot.
        A qualifier in the deck never reaches the reader who only sees it."""
        with self.assertRaisesRegex(ContentError, 'headline'):
            base(headline='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ', category='crime',
                 deck='ಆರೋಪಿ ಪುತ್ರನನ್ನು ವಶಕ್ಕೆ ಪಡೆದ ಪೊಲೀಸರು.').validate()

    def test_a_marker_elsewhere_does_not_clear_the_reel_line(self):
        """reel_line is the only text on its scene, so it must self-qualify."""
        with self.assertRaisesRegex(ContentError, 'reel_line'):
            base(headline='ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ', category='crime',
                 reel_line='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ').validate()

    def test_a_thumbnail_hook_cannot_assert_guilt(self):
        """`hook` replaces the headline on the thumbnail, so it carries the
        headline's exposure. Story.validate() cannot see it — it is not a Story
        field — so the template enforces it on the same terms. Without this the
        guard is one `--hook` away from being decoration."""
        import tempfile
        from templates.youtube_thumb import youtube_thumb
        st = base(headline='ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ', category='crime')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ContentError, 'hook'):
                youtube_thumb(st, os.path.join(d, 't.jpg'),
                              hook='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ')

    def test_ageing_out_of_breaking_does_not_relax_the_guilt_guard(self):
        """Demotion is a presentation decision. It must not turn a defamation
        exposure into a clean render just because the story got older."""
        pinned = datetime(2026, 8, 25, 9, 40, tzinfo=IST)
        stale = pinned - timedelta(hours=BREAKING_WINDOW_H + 8)
        with frozen(pinned):
            with self.assertRaisesRegex(ContentError, 'guilt'):
                base(headline='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ', category='breaking',
                     published_at=stale).validate()

    def test_minor_blocks_an_actual_scene_photo(self):
        with self.assertRaisesRegex(ContentError, 'involves_minor'):
            base(headline='ಪ್ರಕರಣ ದಾಖಲು', category='crime', involves_minor=True,
                 photo=pic(nature='actual', caption='c')).validate()

    def test_minor_blocks_names_with_ages(self):
        with self.assertRaisesRegex(ContentError, 'involves_minor'):
            base(headline='ಪ್ರಕರಣ ದಾಖಲು', category='crime', involves_minor=True,
                 points=['ಬಾಲಕ ರಮೇಶ್ (14) ನಿವಾಸಿ.']).validate()

    def test_sexual_offence_blocks_granular_location(self):
        with self.assertRaisesRegex(ContentError, 'sexual_offence'):
            base(headline='ಪ್ರಕರಣ ದಾಖಲು', category='crime', sexual_offence=True,
                 location='ಗಾಂಧಿನಗರ').validate()

    def test_sexual_offence_allows_district_level_location(self):
        base(headline='ಪ್ರಕರಣ ದಾಖಲು', category='crime', sexual_offence=True,
             location='ಉಡುಪಿ ಜಿಲ್ಲೆ').validate()


class Copy(unittest.TestCase):
    """The copy engine must work for ANY story, not today's."""

    def setUp(self):
        import brand.copy as C
        self.C = C

    # ── Kannada case marking ────────────────────────────────────────────
    # Case markers are bound morphemes. "ಉಡುಪಿ ನಲ್ಲಿ" is "Udupi in", and it
    # was going out on the first comment of every weather post.

    def test_locative_agglutinates_and_never_leaves_a_loose_suffix(self):
        for place, want in [
                ('ಉಡುಪಿ', 'ಉಡುಪಿಯಲ್ಲಿ'),            # ends -i  → ಯ
                ('ಮಲ್ಪೆ', 'ಮಲ್ಪೆಯಲ್ಲಿ'),            # ends -e  → ಯ
                ('ಮಂಗಳೂರು', 'ಮಂಗಳೂರಿನಲ್ಲಿ'),        # ends -u  → ಿನ
                ('ಬೈಂದೂರು', 'ಬೈಂದೂರಿನಲ್ಲಿ'),
                ('ಕುಂದಾಪುರ', 'ಕುಂದಾಪುರದಲ್ಲಿ'),      # inherent -a → ದ
                ('ಕುಮಟಾ', 'ಕುಮಟಾದಲ್ಲಿ'),            # ends -aa → ದ
                ('ಉಡುಪಿ ಜಿಲ್ಲೆ', 'ಉಡುಪಿ ಜಿಲ್ಲೆಯಲ್ಲಿ'),   # last word only
        ]:
            got = self.C.locative(place)
            self.assertEqual(got, want, f'{place} → {got}')
            self.assertNotIn(' ನಲ್ಲಿ', got)
            self.assertNotIn(' ಯಲ್ಲಿ', got)

    def test_inflection_refuses_a_name_it_cannot_analyse(self):
        """Better a plainer sentence than invented Kannada morphology."""
        for bad in ('Udupi', 'Mangaluru', '', '2026'):
            self.assertEqual(self.C.locative(bad), '')
            self.assertEqual(self.C.belonging(bad), '')

    def test_first_comment_is_grammatical_for_every_place_we_cover(self):
        for place in list(self.C.PLACE_TAGS) + ['ಕರಾವಳಿ']:
            for cat in ('weather', 'civic', 'crime'):
                fc = self.C.first_comment(
                    base(category=cat, location=place,
                         headline='ಪ್ರಕರಣ ದಾಖಲು' if cat == 'crime' else 'ಸುದ್ದಿ'))
                self.assertTrue(fc)
                # a case marker stranded as its own word is the bug
                for loose in (' ನಲ್ಲಿ', ' ನಿಂದ', ' ಯಲ್ಲಿ', ' ದಲ್ಲಿ', ' ವರಾ'):
                    self.assertNotIn(loose, fc, f'{place}/{cat}: {fc}')

    # ── Publishing plan ─────────────────────────────────────────────────

    def test_plan_never_lists_an_asset_that_was_not_rendered(self):
        plan = self.C.publishing_plan(n_reels=0, has_bulletin=False,
                                      has_carousel=False, has_story_card=False,
                                      has_broadsheet=True)
        assets = ' '.join(s.asset for s in plan)
        self.assertIn('broadsheet', assets)
        for absent in ('bulletin.mp4', 'carousel', 'reel_', 'story_9x16'):
            self.assertNotIn(absent, assets)

    def test_plan_spaces_reels_so_they_do_not_compete_with_each_other(self):
        plan = self.C.publishing_plan(n_reels=4)
        mins = sorted(int(s.at[:2]) * 60 + int(s.at[3:])
                      for s in plan if 'Reels' in s.platform)
        self.assertEqual(len(mins), 4)
        for a, b in zip(mins, mins[1:]):
            self.assertGreaterEqual(b - a, 150, 'reels closer than 2.5h')

    def test_the_long_form_bulletin_is_scheduled_before_the_shorts(self):
        """It is the only asset on the 4,000-hour path, so it gets the day."""
        plan = self.C.publishing_plan(n_reels=3)
        bulletin = next(s for s in plan if 'bulletin.mp4' in s.asset)
        reels = [s for s in plan if 'Reels' in s.platform]
        self.assertTrue(all(bulletin.at < r.at for r in reels))

    def test_hook_stays_inside_the_instagram_fold(self):
        s = base(headline='ಅ' * 400)
        self.assertLessEqual(len(self.C.hook(s)), self.C.FOLD + 1)

    def test_caption_carries_sources_and_disclosure(self):
        s = base(location='ಉಡುಪಿ', photo=pic(nature='representative')).validate()
        cap = self.C.instagram_caption(s)
        self.assertIn('ಮೂಲ:', cap)
        self.assertIn('ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ', cap)
        self.assertLessEqual(len(cap), self.C.IG_CAPTION_MAX)

    def test_place_is_not_duplicated(self):
        s = base(headline='ಕುಂದಾಪುರ: ಬಂದರು ಕಾಮಗಾರಿ', location='ಕುಂದಾಪುರ').validate()
        self.assertEqual(self.C.x_post(s).count('ಕುಂದಾಪುರ'), 1)

    def test_x_post_fits(self):
        s = base(headline='ಅ' * 400, location='ಉಡುಪಿ')
        self.assertLessEqual(len(self.C.x_post(s)), self.C.X_MAX)

    def test_youtube_title_fits(self):
        s = base(headline='ಅ' * 400, location='ಉಡುಪಿ')
        self.assertLessEqual(len(self.C.youtube_title(s)), self.C.YT_TITLE_MAX)

    def test_hashtags_are_deduplicated_and_capped(self):
        s = base(location='ಉಡುಪಿ', category='weather').validate()
        tags = self.C.hashtags(s, limit=12)
        self.assertLessEqual(len(tags), 12)
        self.assertEqual(len(tags), len({t.lower() for t in tags}))

    def test_hashtags_lead_with_the_place_not_a_mega_tag(self):
        """A 15-day-old account cannot win #Karnataka. Place first."""
        s = base(location='ಉಡುಪಿ', category='weather').validate()
        tags = self.C.hashtags(s)
        self.assertIn('Udupi', tags)
        self.assertIn('UdupiNews', tags)
        self.assertLess(tags.index('Udupi'), tags.index('OormaniSuddi'))

    def test_caption_opens_on_the_news_and_asks_for_a_signal(self):
        s = base(location='ಉಡುಪಿ', category='weather',
                 reel_line='ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್').validate()
        cap = self.C.instagram_caption(s)
        self.assertTrue(cap.startswith('ಉಡುಪಿ: ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್')
                        or cap.startswith('ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್'))
        self.assertTrue('ಕಾಮೆಂಟ್' in cap or 'ಶೇರ್' in cap or 'ಫಾಲೋ' in cap)

    def test_edition_caption_does_not_open_on_the_date(self):
        from brand.content import Edition
        ed = Edition.load('tests/fixture_edition.json')
        cap = self.C.for_edition(ed).instagram
        self.assertFalse(cap.startswith(ed.date_kn))
        self.assertIn('ಸ್ವೈಪ್', cap)

    def test_youtube_title_does_not_append_shorts(self):
        s = base(location='ಉಡುಪಿ', reel_line='ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್').validate()
        title = self.C.youtube_title(s, 'short')
        self.assertNotIn('#Shorts', title)
        self.assertNotIn('#shorts', title.lower())

    def test_youtube_description_opens_on_the_story_not_the_brand(self):
        s = base(location='ಉಡುಪಿ', reel_line='ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್',
                 deck='ಜಿಲ್ಲೆಗೆ ಎಚ್ಚರಿಕೆ.').validate()
        desc = self.C.youtube_description(s)
        self.assertNotEqual(desc.split('\n', 1)[0],
                            'ಊರ್ಮನಿ ಸುದ್ದಿ · ನಮ್ಮ ಊರು  •  ನಮ್ಮ ಧ್ವನಿ')
        self.assertIn('ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್', desc.split('\n', 1)[0])

    def test_story_with_no_photo_still_discloses(self):
        s = base().validate()
        self.assertIn('ಗ್ರಾಫಿಕ್ಸ್', self.C.instagram_caption(s))

    def test_copy_dictionary_only_has_instagram_and_youtube(self):
        s = base().validate()
        copy = self.C.for_story(s)
        d = copy.to_dict()
        self.assertEqual(set(d.keys()), {'instagram', 'youtube_title', 'youtube_description', 'youtube_tags'})
        self.assertNotIn('whatsapp', d)
        self.assertNotIn('x_post', d)
        self.assertNotIn('alt_text', d)

    def test_write_copy_text_only_contains_instagram_and_youtube(self):
        import tempfile
        import render
        s = base().validate()
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = render.write_copy(s, tmpdir, 'test_copy')
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('═══ INSTAGRAM CAPTION ═══', content)
            self.assertIn('═══ INSTAGRAM FIRST COMMENT', content)
            self.assertIn('═══ YOUTUBE TITLE ═══', content)
            self.assertIn('═══ YOUTUBE DESCRIPTION ═══', content)
            self.assertIn('═══ YOUTUBE TAGS ═══', content)
            self.assertNotIn('WHATSAPP', content)
            self.assertNotIn('X / TWITTER', content)
            self.assertNotIn('ALT TEXT', content)



class BulletinPacing(unittest.TestCase):
    """The 16:9 bulletin is a different viewing contract from the reel.

    A reel is glanced at in a vertical feed; a bulletin was opened on purpose
    on YouTube. The bulletin therefore carries the deck and lets a scene run
    longer — but it must never pad to reach a length, and never compress below
    reading speed. See docs/DECISIONS.md D37.
    """

    @classmethod
    def setUpClass(cls):
        from brand.content import Edition
        from brand import motion as M
        cls.M = M
        cls.ed = Edition.load('tests/fixture_edition.json')

    def test_a_bulletin_scene_carries_the_deck_and_a_reel_scene_does_not(self):
        """The whole reason the bulletin reaches long-form length."""
        st = next(s for s in self.ed.stories if s.deck)
        _d, _h, reel_body = self.M.scene_seconds(st, self.M.REEL)
        _d, _h, bull_body = self.M.scene_seconds(st, self.M.BULLETIN)
        self.assertIn(st.deck.strip(), bull_body)
        self.assertNotEqual(reel_body, bull_body)

    def test_the_bulletin_shows_the_print_headline_not_the_reel_line(self):
        """A 16:9 frame has the column for the full headline, and those extra
        words are information the viewer opened a long-form video to get."""
        st = base(headline='ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್: ಇಂದು ಭಾರಿ ಮಳೆ ಸಾಧ್ಯತೆ',
                  reel_line='ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್').validate()
        self.assertEqual(self.M.head_line(st, self.M.BULLETIN), st.headline)
        self.assertEqual(self.M.head_line(st, self.M.REEL), st.reel_line)
        self.assertNotEqual(st.headline, st.reel_line)

    def test_no_bulletin_scene_is_cut_below_its_reading_time(self):
        """The failure this module exists to prevent, at the new ceiling."""
        for st in self.ed.stories:
            need = self.M.scene_need(st, self.M.BULLETIN)
            shown = self.M.scene_seconds(st, self.M.BULLETIN)[0]
            self.assertGreaterEqual(
                shown + 0.05, need,
                f'{st.headline[:30]!r} is cut {need - shown:.1f}s short')

    def test_a_bulletin_target_is_a_ceiling_not_a_quota(self):
        """`--bulletin-seconds` must drop stories, never rescale scenes.

        This path had no test, and a proportional-scaling version of
        plan_bulletin was wrong in both directions: at 60s it cut every scene
        below its reading time, at 120s it padded every scene by 65%. Both are
        the failure the whole module exists to prevent. See DECISIONS.md D44.
        """
        for target in (60, 90, 120):
            pace, i, holds, o, used, _t = self.M.plan_bulletin(
                self.ed, target=target)
            for st, shown in zip(self.ed.stories[:used], holds):
                need = self.M.scene_need(st, pace)
                # never longer than the copy needs — that is padding
                self.assertLessEqual(
                    shown, need + 0.05,
                    f'target={target}: scene padded to {shown:.1f}s for '
                    f'{need:.1f}s of copy')
                # and never shorter, unless it is the documented hold_max
                # backstop, which the renderer reports rather than hides
                if shown + 0.05 < need:
                    self.assertAlmostEqual(shown, pace.hold_max, delta=0.05)

    def test_length_is_derived_from_the_copy_and_never_padded(self):
        """A thin edition must come out short and say so, not be inflated."""
        from brand.content import Edition
        thin = Edition.load('tests/fixture_edition.json')
        thin.stories = thin.stories[:1]
        _p, i, holds, o, _u, total = self.M.plan_bulletin(thin)
        self.assertAlmostEqual(total, i + sum(holds) + o, places=6)
        self.assertLess(total, self.M.Motion.bulletin_floor,
                        'a one-story bulletin should fall short, not be padded')

    def test_the_reel_pace_is_left_exactly_as_it_was(self):
        """The bulletin must not change a single reel frame — the golden test
        pins those, and a reel regression would show up there far too late."""
        self.assertEqual(self.M.REEL.hold_max, self.M.Motion.hold_max)
        self.assertFalse(self.M.REEL.full_headline)
        for st in self.ed.stories:
            self.assertEqual(self.M.head_line(st, self.M.REEL),
                             self.M.reel_line(st))

    def test_a_reel_opens_on_the_story_not_a_sting(self):
        """D39: logo sting is a scroll cue. Bulletin still has one."""
        self.assertEqual(self.M.Motion.reel_intro, 0.0)
        self.assertLess(self.M.Motion.reel_outro, 3.0)


if __name__ == '__main__':
    unittest.main()
