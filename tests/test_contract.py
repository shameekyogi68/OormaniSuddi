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
             source_urls=['https://example.test/fixture'],
             published_at=datetime(2026, 8, 25, 8, 0, tzinfo=IST))
    d.update(kw)
    return Story(**d)


def pic(**kw):
    d = dict(path='assets/udupi_coastal_storm.jpg', credit='ವರದಿಗಾರರಿಂದ', licence='own')
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
        """D22, D23: derived from an injectable clock, never asserted."""
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
        s = base(deck='ಪರೀಕ್ಷೆ', points=['ಒಂದು', 'ಎರಡು'], photo=pic(credit='ಸಂಗ್ರಹ'), is_reel=False)
        again = Story.from_dict(s.to_dict())
        self.assertEqual(again.headline, s.headline)
        self.assertEqual(again.points, s.points)
        self.assertEqual(again.photo.credit, s.photo.credit)
        self.assertEqual(again.published_at, s.published_at)
        self.assertEqual(again.is_reel, False)

    def test_is_reel_default_and_aliases(self):
        s_default = Story.from_dict({'headline': 'ಪರೀಕ್ಷೆ', 'sources': ['ಮೂಲ']})
        self.assertTrue(s_default.is_reel)

        s_false = Story.from_dict({'headline': 'ಪರೀಕ್ಷೆ', 'sources': ['ಮೂಲ'], 'is_reel': False})
        self.assertFalse(s_false.is_reel)

        s_alias = Story.from_dict({'headline': 'ಪರೀಕ್ಷೆ', 'sources': ['ಮೂಲ'], 'reel': False})
        self.assertFalse(s_alias.is_reel)


class Preflight(unittest.TestCase):

    def test_mixed_numerals_fail(self):
        """D20: Latin numerals, and never both systems on one card."""
        s = base(headline='೨೫ ಜನರಿಗೆ 40 ಕೋಟಿ ರೂ. ಪರಿಹಾರ')
        self.assertTrue(any('numeral' in m for m in preflight(s).fail))

    def test_overlong_headline_fails_for_a_thumbnail(self):
        """D18: the budget is structural, not advisory."""
        s = base(headline='ಬ್ರಹ್ಮಾವರ: ಕ್ಷುಲ್ಲಕ ಜಗಳಕ್ಕೆ ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ')
        self.assertTrue(preflight(s, 'thumb').fail)
        self.assertFalse(preflight(s, 'thumb', hook='ಪುತ್ರ ಬಂಧನ').fail)

    def test_clean_story_is_clean(self):
        s = base(deck='ಸಣ್ಣ ಪರಿಚಯ.', location='ಉಡುಪಿ',
                 points=['ಒಂದು ಅಂಶ.', 'ಎರಡನೇ ಅಂಶ.'])
        self.assertEqual(preflight(s).fail, [])


class Licensing(unittest.TestCase):

    def test_photo_without_licence_is_refused(self):
        """D30: a credit is not a licence."""
        with self.assertRaisesRegex(ContentError, 'licence'):
            base(photo=Photo(path='a.jpg', credit='X')).validate()

    def test_non_own_licence_needs_a_source(self):
        """D30: anything not our own says where it came from."""
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
        """D41: the hook is guarded exactly like a headline."""
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
        """D42: the case markers we generate are checked."""
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
        """D43: the plan is derived from what was actually made."""
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

    def test_ai_bulletin_is_off_by_default_and_held_off_youtube(self):
        plan = self.C.publishing_plan(n_reels=3)
        self.assertFalse(any('bulletin.mp4' in s.asset for s in plan))
        held = self.C.publishing_plan(n_reels=1, has_bulletin=True)
        bulletin = next(s for s in held if 'bulletin.mp4' in s.asset)
        self.assertIn('HOLD', bulletin.platform)
        self.assertNotEqual(bulletin.platform, 'YouTube')
        footage = self.C.publishing_plan(
            n_reels=1, has_bulletin=True, bulletin_is_footage=True)
        yt = next(s for s in footage if 'bulletin.mp4' in s.asset)
        self.assertEqual(yt.platform, 'YouTube')

    def test_ai_reels_are_instagram_only(self):
        plan = self.C.publishing_plan(n_reels=2)
        reels = [s for s in plan if 'reel_' in s.asset]
        self.assertTrue(reels)
        for s in reels:
            self.assertEqual(s.platform, 'Instagram Reels')
            self.assertNotIn('YouTube', s.platform)

    def test_hook_stays_inside_the_instagram_fold(self):
        s = base(headline='ಅ' * 400)
        self.assertLessEqual(len(self.C.hook(s)), self.C.FOLD + 1)

    def test_caption_carries_sources_and_disclosure(self):
        """D27, D49: standing copy comes from tokens, disclosure from the photo."""
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
        self.assertLess(tags.index('Udupi'), tags.index('oormanisuddi'))

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
        """D32: the platform decides what is a Short, not our title."""
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
        """D25: no photo still means a visual, and still means a disclosure."""
        s = base().validate()
        self.assertIn('ಗ್ರಾಫಿಕ್ಸ್', self.C.instagram_caption(s))

    def test_copy_dictionary_exports_whatsapp_and_youtube(self):
        """D31: the system emits copy, not just artwork."""
        s = base().validate()
        copy = self.C.for_story(s)
        d = copy.to_dict()
        self.assertIn('instagram', d)
        self.assertIn('whatsapp', d)
        self.assertIn('youtube_title', d)
        self.assertIn('youtube_description', d)
        self.assertIn('first_comment', d)
        self.assertTrue(copy.whatsapp)
        self.assertNotIn('x_post', d)

    def test_write_copy_includes_whatsapp_forward(self):
        """D31: every render ships the text you paste, not only a JPEG."""
        import tempfile
        import render
        s = base().validate()
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = render.write_copy(s, tmpdir, 'test_copy')
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('═══ INSTAGRAM CAPTION', content)
            self.assertIn('═══ INSTAGRAM FIRST COMMENT', content)
            self.assertIn('═══ WHATSAPP FORWARD', content)
            self.assertIn('═══ YOUTUBE TITLE', content)
            self.assertIn('═══ YOUTUBE DESCRIPTION', content)
            self.assertIn('═══ YOUTUBE TAGS', content)
            self.assertNotIn('X / TWITTER', content)



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
        """D37: the bulletin's payload is the deck."""
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
        """D15, D26: a scene is never compressed below its reading time."""
        """The failure this module exists to prevent, at the new ceiling."""
        for st in self.ed.stories:
            need = self.M.scene_need(st, self.M.BULLETIN)
            shown = self.M.scene_seconds(st, self.M.BULLETIN)[0]
            self.assertGreaterEqual(
                shown + 0.05, need,
                f'{st.headline[:30]!r} is cut {need - shown:.1f}s short')

    def test_a_bulletin_target_is_a_ceiling_not_a_quota(self):
        """D44: a target drops stories; it never rescales scenes."""
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
        """D37: the length is derived, not chosen."""
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
        """D39: no logo sting in the first 1.5 seconds."""
        """D39: logo sting is a scroll cue. Bulletin still has one."""
        self.assertEqual(self.M.Motion.reel_intro, 0.0)
        self.assertLess(self.M.Motion.reel_outro, 3.0)


class NarrationLockedReel(unittest.TestCase):
    """D45: the picture is cut from the speech, so the two cannot drift.

    These are the invariants that made the drift possible. The old timeline
    put the fact-one card on screen 15.5 seconds before the voice reached that
    fact, and no test could have caught it, because nothing tied the two
    together at all.
    """

    @classmethod
    def setUpClass(cls):
        from brand import motion as M
        from brand import voice as V
        from brand.content import Edition
        cls.M, cls.V = M, V
        cls.ed = Edition.load('tests/fixture_edition.json')

    def test_every_story_has_one_spoken_beat_per_card(self):
        """The single invariant the whole design rests on."""
        for st in self.ed.stories:
            cards = [c.key for c in self.M.reel_cards(st)]
            beats = [k for k, _t in self.V.narration_beats(st)]
            self.assertEqual(cards, self.V.card_keys(st),
                             'reel_cards and card_keys disagree')
            self.assertEqual(beats, cards,
                             f'{st.headline[:30]}: narration beats {beats} do '
                             f'not match cards {cards} — the voice would play '
                             f'over the wrong picture')

    def test_a_cards_text_is_what_its_beat_talks_about(self):
        """D45, D47: one beat, one card, set at news size."""
        """A fact card must carry the fact its beat was built from."""
        for st in self.ed.stories:
            cards = {c.key: c for c in self.M.reel_cards(st)}
            for i, p in enumerate([x for x in st.points if x.strip()]):
                self.assertEqual(cards[f'fact{i}'].text, p)
            if (st.takeaway or '').strip():
                self.assertEqual(cards['advisory'].text, st.takeaway.strip())
                self.assertTrue(cards['advisory'].is_alert)

    def test_the_gap_between_cards_outlasts_the_picture_lead(self):
        """D45, D48: the cut lands inside the gap, and the bed ducks once."""
        """The cut is made inside the silence between two sentences.

        The picture leads the audio by vo_lead, so the next cut falls
        (vo_gap - vo_lead) after a sentence ends. If the gap ever drops to the
        lead, every transition clips a syllable.
        """
        Mo = self.M.Motion
        self.assertGreater(Mo.vo_gap, Mo.vo_lead + 0.2)
        self.assertGreater(Mo.vo_tail, Mo.vo_lead)

    def test_a_card_is_never_shorter_than_its_kannada_takes_to_read(self):
        """D15 and D26: duration follows reading time, honestly measured."""
        for st in self.ed.stories:
            for c in self.M.reel_cards(st):
                if c.kind == 'outro':
                    continue
                self.assertGreaterEqual(
                    self.M.card_read_seconds(c),
                    self.M.reading_seconds(c.text) * Mo_ease(self.M),
                    'a card may not be given less time than its copy needs')

    def test_an_override_script_still_lands_on_the_right_cards(self):
        """An editor's own narration is speech; the cards come from the story.

        Balancing by length alone put the sign-off on a fact card and the
        advisory on the outro, which is worse than the automatic path.
        """
        st = next(s for s in self.ed.stories if s.points)
        keys = self.V.card_keys(st)
        script = ('ನಮಸ್ಕಾರ. ಮೊದಲ ವಾಕ್ಯ. ಎರಡನೇ ವಾಕ್ಯ. ಮೂರನೇ ವಾಕ್ಯ. '
                  'ನಾಲ್ಕನೇ ವಾಕ್ಯ. ಐದನೇ ವಾಕ್ಯ. ಆರನೇ ವಾಕ್ಯ. '
                  'ಕ್ಷಣ ಕ್ಷಣದ ಸುದ್ದಿಗಳಿಗಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿ ಫಾಲೋ ಮಾಡಿ.')
        beats = self.V._fit_script_to_cards(script, keys)
        self.assertEqual([k for k, _ in beats], keys)
        self.assertIn('ಫಾಲೋ ಮಾಡಿ', dict(beats)['signoff'],
                      'the sign-off must land on the outro card')


def Mo_ease(M):
    return M.Motion.reel_read_ease


class GlyphsThatCannotBeSet(unittest.TestCase):
    """D46: a codepoint no face carries used to ship as an empty box."""

    @classmethod
    def setUpClass(cls):
        from brand import typo
        cls.typo = typo

    def test_the_characters_that_shipped_as_boxes_are_now_substituted(self):
        for fam in ('kn', 'kn_var', 'kn_serif'):
            f = self.typo.font(fam, 40)
            self.assertNotIn('\u25aa', self.typo.safe('▪ ಪರೀಕ್ಷೆ', f))
            self.assertNotIn('\u26a0', self.typo.safe('⚠ ಪರೀಕ್ಷೆ', f))

    def test_no_reel_badge_contains_an_unsettable_character(self):
        """The badges are the copy that actually broke."""
        from brand import motion as M
        from brand.content import Edition
        ed = Edition.load('tests/fixture_edition.json')
        for st in ed.stories:
            for c in M.reel_cards(st):
                if not c.badge:
                    continue
                f = self.typo.font_for(c.badge, 'kn_var', 30)
                self.assertEqual(self.typo.safe(c.badge, f), c.badge,
                                 f'badge {c.badge!r} is not renderable as written')
                self.assertEqual(self.typo.missing_glyphs(c.badge, f), ())

    def test_designed_whitespace_survives(self):
        """Only whitespace the sanitizer creates may be closed up.

        Collapsing the double space either side of the tagline's bullet moved
        every still in the house the first time this was written.
        """
        f = self.typo.font('kn_var', 40)
        for s in ('ನಮ್ಮ ಊರು  •  ನಮ್ಮ ಧ್ವನಿ', '  ಪೂರ್ವ  ', 'a  b'):
            self.assertEqual(self.typo.safe(s, f), s)

    def test_a_missing_letter_is_reported_and_never_dropped(self):
        """D46: a glyph the face lacks is a fault, not a substitution."""
        """Dropping a letter changes what a sentence says; that is worse."""
        f = self.typo.font('latin', 40)          # SF has no Kannada
        out = self.typo.safe('ಪರೀಕ್ಷೆ', f)
        self.assertTrue(out, 'Kannada must not be silently deleted')
        self.assertTrue(self.typo.missing_glyphs('ಪರೀಕ್ಷೆ', f),
                        'a face that cannot set this must say so')

    def test_decoration_is_dropped_but_a_letter_is_escalated(self):
        """The split that makes silent substitution safe.

        An emoji is decoration: dropping it costs nothing and beats a box. A
        letter from a script the face does not carry cannot be dropped — that
        would change what the sentence says — so it survives to be reported.
        """
        f = self.typo.font('kn_var', 40)
        self.assertEqual(self.typo.safe('ಪ \U0001F600 ಪ', f), 'ಪ ಪ')
        self.assertEqual(self.typo.missing_glyphs('ಪ \U0001F600 ಪ', f), ())
        self.assertIn('அ', self.typo.safe('ಪ அ ಪ', f))
        self.assertEqual(self.typo.missing_glyphs('ಪ அ ಪ', f), ('அ',))

    def test_preflight_fails_copy_that_cannot_be_set(self):
        from brand.qa import preflight
        from brand.content import Story
        s = Story(headline='ಪರೀಕ್ಷೆ அ ಪರೀಕ್ಷೆ', sources=['ಮೂಲ'])
        r = preflight(s, 'reel')
        self.assertTrue(any('empty boxes' in m for m in r.fail),
                        'an unsettable letter must fail preflight')


class EveryImageOnScreenIsDisclosed(unittest.TestCase):
    """D49: the label travels with the IMAGE, not with the story.

    Only the lead card used to disclose anything, because `credit_line` read
    `story.photo`. A reel's fact cards are drawn from the gallery and its end
    card from the hero, so an AI-generated picture could hold the frame for
    twenty seconds with nothing on screen saying so.
    """

    @classmethod
    def setUpClass(cls):
        from brand.content import Edition
        from brand import motion as M
        cls.M = M
        cls.ed = Edition.load('tests/fixture_edition.json')

    def test_every_photo_can_state_its_own_provenance(self):
        """D49: the label travels with the image, not with the story."""
        for st in self.ed.stories:
            for p in st.all_photos:
                self.assertTrue(p.disclosure.strip(),
                                f'{p.path} would appear with no disclosure')

    def test_the_hero_line_and_the_per_photo_line_are_the_same_code(self):
        """A gallery frame and the hero must not be labelled by two rules."""
        for st in self.ed.stories:
            if st.photo:
                self.assertEqual(st.credit_line, st.photo.disclosure)

    def test_a_generated_image_says_so(self):
        from brand.content import Photo
        p = Photo(path='x.jpg', nature='ai', credit='ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own')
        self.assertIn('ಎಐ ರಚಿತ ಚಿತ್ರ', p.disclosure)
        self.assertTrue(p.is_synthetic)

    def test_every_card_that_shows_a_picture_knows_which_one(self):
        """ChapterScene.shown is what makes the label match the picture."""
        from brand.tokens import fmt
        from dataclasses import replace
        import copy, os
        F = fmt('reel')
        # Built here rather than taken from the fixture: the fixture has no
        # gallery, and this invariant is about the gallery path specifically.
        base = next(s for s in self.ed.stories if s.photo and s.points)
        # The fixture's photo paths do not exist on disk (the golden renders
        # draw the editorial plate instead), and this invariant only means
        # anything when there IS a file to show — so point at a real one.
        real = 'assets/logo.png'
        self.assertTrue(os.path.exists(real))
        second = copy.deepcopy(base.photo)
        second.path = real
        second.caption = 'ಎರಡನೇ ಚಿತ್ರ'
        st = replace(base, gallery=[second])
        cards = [c for c in self.M.reel_cards(st) if c.kind in ('fact', 'advisory')]
        card = next(c for c in cards if c.photo is not None)
        sc = self.M.ChapterScene(
            st, F.w, F.h, F.ss, 8.0, badge=card.badge, text=card.text,
            chapter_idx=1, total_chapters=4, safe=F.safe, pace=self.M.REEL,
            photo_path=card.photo.path, photo=card.photo)
        self.assertIsNotNone(sc.shown)
        self.assertEqual(sc.shown.path, card.photo.path,
                         'the card labels a different image than it shows')

    def test_preflight_checks_the_gallery_not_just_the_hero(self):
        """D49, D51: every frame that reaches the screen is checked."""
        from brand.qa import preflight
        from brand.content import Story, Photo
        good = Photo(path='a.jpg', nature='ai', credit='X', licence='own')
        bare = Photo(path='b.jpg', nature='actual', credit='', licence='own')
        s = Story(headline='ಪರೀಕ್ಷೆ', sources=['ಮೂಲ'], photo=good, gallery=[bare])
        r = preflight(s, 'reel')
        self.assertTrue(any('no disclosure' in m for m in r.fail),
                        'an undisclosed gallery image must fail preflight')

    def test_story_chapter_defs_produces_safe_badges_and_structure(self):
        """D46: multi-chapter breakdown builds clean badges without tofu glyphs."""
        base = next(s for s in self.ed.stories if s.points and s.takeaway)
        defs = self.M._story_chapter_defs(base)
        self.assertGreaterEqual(len(defs), 2)
        for name, badge, text, is_alert in defs:
            self.assertTrue(name.strip())
            self.assertTrue(badge.strip())
            self.assertTrue(text.strip())
            # D46: no raw bullet ▪ or warning ⚠ glyphs in badge text (drawn vectorially)
            self.assertNotIn('▪', badge)
            self.assertNotIn('⚠', badge)



class TheAnchorSpeaksKannada(unittest.TestCase):
    """D50: print copy and spoken copy are not the same language."""

    @classmethod
    def setUpClass(cls):
        from brand import voice as V
        cls.V = V

    def test_units_and_abbreviations_are_spoken_not_spelled(self):
        self.assertIn('ಕಿಲೋಮೀಟರ್', self.V._spoken('ವೇಗ 40 ಕಿ.ಮೀ ಆಗಿದೆ'))
        self.assertIn('ಡಾಕ್ಟರ್', self.V._spoken('ಡಾ. ರಮೇಶ್ ತಿಳಿಸಿದ್ದಾರೆ'))
        self.assertIn('ಸಿಸಿಟಿವಿ', self.V._spoken('CCTV ದೃಶ್ಯ ಪರಿಶೀಲನೆ'))

    def test_no_decimal_point_survives_into_the_engine(self):
        """A dot between digits is read as a full stop, so none may reach it.

        Superseding an earlier version of this test that only required the
        decimal to survive intact: intact is not enough, because the engine
        stops on it. It has to be gone.
        """
        out = self.V._spoken('₹1.1 ಲಕ್ಷ ನಷ್ಟ')
        self.assertNotIn('1.1', out)
        self.assertNotIn('1. 1', out)
        self.assertIn('ಲಕ್ಷದ', out)
        self.assertNotIn('29.6', self.V._spoken('ತಾಪಮಾನ 29.6 ಡಿಗ್ರಿ'))

    def test_currency_follows_the_amount_as_kannada_does(self):
        out = self.V._spoken('₹5 ಲಕ್ಷ ಮೌಲ್ಯದ ಕಳವು')
        self.assertIn('ಲಕ್ಷ ರೂಪಾಯಿ', out)
        self.assertNotIn('₹', out)
        # …and a scaled amount keeps its currency after being expanded.
        self.assertIn('ರೂಪಾಯಿ', self.V._spoken('₹1.10 ಲಕ್ಷ ಕಳವು'))

    def test_percent_leads_the_figure_as_kannada_does(self):
        self.assertIn('ಶೇಕಡಾ 40', self.V._spoken('40% ಏರಿಕೆ'))
        # …and an existing ಶೇ prefix is absorbed, never doubled.
        self.assertNotIn('ಶೇ ಶೇಕಡಾ', self.V._spoken('ಶೇ 40% ಏರಿಕೆ'))

    def test_a_numeric_range_is_read_as_a_range(self):
        self.assertIn('25 ರಿಂದ 35', self.V._spoken('25-35 ಕಿ.ಮೀ ವೇಗ'))

    def test_a_hyphenated_place_name_is_not_a_range(self):
        """ತ್ರಾಸಿ-ಮರವಂತೆ is one place, not "ತ್ರಾಸಿ ರಿಂದ ಮರವಂತೆ"."""
        self.assertNotIn('ರಿಂದ', self.V._spoken('ತ್ರಾಸಿ-ಮರವಂತೆ ಕಡಲತೀರ'))

    def test_a_clock_time_takes_the_case_its_stem_takes(self):
        """ಗಂಟೆ takes ಗೆ; ನಿಮಿಷ takes ಕ್ಕೆ. Carrying the written particle
        across unchanged produced "10 ಗಂಟೆಕ್ಕೆ", which is not Kannada."""
        self.assertIn('10 ಗಂಟೆಗೆ', self.V._spoken('ರಾತ್ರಿ 10:00 ಗೆ ಮುಕ್ತಾಯ'))
        self.assertIn('15 ನಿಮಿಷಕ್ಕೆ', self.V._spoken('ಬೆಳಿಗ್ಗೆ 9:15 ಕ್ಕೆ ಘಟನೆ'))
        self.assertIn('30 ನಿಮಿಷದ', self.V._spoken('ಸಂಜೆ 6:30 ರ ಸುಮಾರಿಗೆ'))
        # and never doubled
        self.assertNotIn('ಕ್ಕೆ ಕ್ಕೆ', self.V._spoken('ಬೆಳಿಗ್ಗೆ 9:15 ಕ್ಕೆ ಘಟನೆ'))

    def test_every_beat_ends_on_a_full_stop(self):
        """The falling final intonation comes from the full stop. Without one
        the engine trails off flat."""
        from brand.content import Edition
        ed = Edition.load('tests/fixture_edition.json')
        for st in ed.stories:
            for _k, t in self.V.narration_beats(st):
                self.assertTrue(t.rstrip()[-1] in '.!?',
                                f'beat does not land on a stop: {t[-40:]!r}')

    def test_the_default_engine_is_the_one_the_native_ear_chose(self):
        """D17 lives in Limits with this; the voice was chosen by ear."""
        """Pinned deliberately, and NOT to be "improved" on measurements.

        This was switched to edge/kn-IN-SapnaNeural on the reasoning that a
        neural voice beats a pronunciation endpoint, backed by pitch
        statistics. The channel's owner listened to both and the Edge voice
        was markedly worse for Kannada. Whether a Kannada newsreader sounds
        right is not a measurable property; on voice the native ear decides.
        """
        self.assertEqual(self.V.DEFAULT_ENGINE, 'google')



class TheChiefEditorsGate(unittest.TestCase):
    """D52: the green signal is established, not asserted.

    A prose checklist is unenforceable — a reviewer can write ✅ against
    "watch the full reel" having looked at nothing, and the failure is
    invisible precisely because nobody downstream checks again. These are the
    facts the gate establishes on its own.
    """

    @classmethod
    def setUpClass(cls):
        from brand import review as R
        cls.R = R

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, body):
        import os
        with open(os.path.join(self.dir, name), 'w', encoding='utf-8') as f:
            f.write(body)

    def test_an_empty_folder_is_never_approved(self):
        rep = self.R.review(self.dir)
        self.assertFalse(rep.clean)
        self.assertIsNone(self.R.approve(self.dir, rep))

    def test_a_miscapitalised_handle_blocks_the_package(self):
        """One wrong capital points every caption at an account that does
        not exist. It is the most-repeated string in the package."""
        from brand.tokens import Brand
        wrong = '@' + Brand.handle[1].upper() + Brand.handle[2:]
        self._write('reel_copy.txt', f'ಪರೀಕ್ಷೆ {wrong} ಪರೀಕ್ಷೆ')
        rep = self.R.review(self.dir)
        self.assertTrue(any('handle is written' in m for m in rep.fail))

    def test_the_correct_handle_passes(self):
        from brand.tokens import Brand
        self._write('reel_copy.txt', f'ಪರೀಕ್ಷೆ {Brand.handle} ಪರೀಕ್ಷೆ')
        rep = self.R.review(self.dir)
        self.assertFalse(any('handle is written' in m for m in rep.fail))

    def test_copy_that_promises_a_file_that_does_not_exist_blocks(self):
        self._write('MASTER_COPY.md', 'post `reel_99.mp4` at 18:00')
        rep = self.R.review(self.dir)
        self.assertTrue(any('reel_99.mp4' in m for m in rep.fail))

    def test_a_range_ellipsis_is_not_read_as_a_filename(self):
        """"carousel_01_cover.jpg … carousel_08_sources.jpg" names two real
        files; the ellipsis must not manufacture a third."""
        import os
        for n in ('carousel_01_cover.jpg', 'carousel_08_sources.jpg'):
            open(os.path.join(self.dir, n), 'wb').close()
        self._write('MASTER_COPY.md',
                    '`carousel_01_cover.jpg` … `carousel_08_sources.jpg`')
        rep = self.R.review(self.dir)
        self.assertFalse([m for m in rep.fail if 'points at' in m], rep.fail)

    def test_crime_copy_without_an_allegation_marker_blocks(self):
        from brand.content import Story, Edition, now
        s = Story(headline='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ', category='crime',
                  sources=['ಮೂಲ'], reel_line='ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ')
        ed = Edition(stories=[s], date=now(), edition_no=1)
        rep = self.R.review(self.dir, ed)
        self.assertTrue(any('allegation marker' in m for m in rep.fail))

    def test_approve_refuses_while_anything_fails_and_clears_a_stale_pass(self):
        import os
        from brand.tokens import Brand
        good = os.path.join(self.dir, 'reel_copy.txt')
        self._write('reel_copy.txt', Brand.handle)
        open(os.path.join(self.dir, 'carousel_01_cover.jpg'), 'wb').close()
        rep = self.R.review(self.dir)
        self.assertTrue(rep.clean, rep.fail)
        path = self.R.approve(self.dir, rep)
        self.assertTrue(path and os.path.exists(path))

        # Now break it. A stale approval must not survive over a failing package.
        self._write('MASTER_COPY.md', 'post `missing_file.mp4`')
        rep2 = self.R.review(self.dir)
        self.assertFalse(rep2.clean)
        self.assertIsNone(self.R.approve(self.dir, rep2))
        self.assertFalse(os.path.exists(path),
                         'a stale APPROVAL.md was left over a failing package')

    # ── D59: no human verification, no publication ────────────────────────

    def test_an_unverified_story_blocks_the_package(self):
        """The second half of D55, which had been written and not enforced."""
        from brand.content import Story, Edition, now, OWN_REPORTING
        s = Story(headline='ಪರೀಕ್ಷಾ ಶೀರ್ಷಿಕೆ', category='civic',
                  sources=[OWN_REPORTING])
        ed = Edition(stories=[s], date=now(), edition_no=1)
        rep = self.R.review(self.dir, ed)
        self.assertTrue(any('verified_by' in m for m in rep.fail),
                        'a story nobody checked was cleared to publish')
        self.assertIn('SRC-02', [f.code for f in rep.findings])

    def test_a_verified_story_clears_that_check(self):
        from brand.content import Story, Edition, now, OWN_REPORTING
        s = Story(headline='ಪರೀಕ್ಷಾ ಶೀರ್ಷಿಕೆ', category='civic',
                  sources=[OWN_REPORTING], verified_by='Gautam Paduvari')
        ed = Edition(stories=[s], date=now(), edition_no=1)
        rep = self.R.review(self.dir, ed)
        self.assertFalse([m for m in rep.fail if 'verified_by' in m])

    def test_verification_is_not_inferred_from_status(self):
        """'confirmed' is what the CARD says. A model can write that."""
        from brand.content import Story, OWN_REPORTING
        s = Story(headline='ಪರೀಕ್ಷೆ', category='civic', status='confirmed',
                  sources=[OWN_REPORTING])
        self.assertFalse(s.is_verified)

    # ── the machine-readable twin ─────────────────────────────────────────

    def test_every_finding_carries_a_registered_code(self):
        """D62: a finding that cannot be routed is a finding nobody owns."""
        from brand import codes
        rep = self.R.review(self.dir)
        self.assertTrue(rep.findings)
        for f in rep.findings:
            self.assertTrue(codes.valid(f.code),
                            f'{f.code!r} is not in brand/codes.py, so nothing '
                            f'can route it back to a step')
            self.assertNotEqual(codes.owner(f.code), 'unassigned')

    def test_a_failed_review_still_writes_the_machine_readable_report(self):
        """A notifier most needs to read the review that FAILED."""
        import json, os
        rep = self.R.review(self.dir)
        self.assertFalse(rep.clean)
        self.assertIsNone(self.R.approve(self.dir, rep))
        p = os.path.join(self.dir, 'review_report.json')
        self.assertTrue(os.path.exists(p))
        with open(p, encoding='utf-8') as fh:
            data = json.load(fh)
        self.assertFalse(data['clean'])
        self.assertTrue(data['findings'])
        self.assertIn('owner', data['findings'][0])

    # ── the seats a machine cannot sit in ─────────────────────────────────

    def test_approval_does_not_claim_a_judgement_it_cannot_make(self):
        """D62: the file records what a machine established, no more."""
        import os
        from brand.tokens import Brand
        self._write('reel_copy.txt', Brand.handle)
        open(os.path.join(self.dir, 'carousel_01_cover.jpg'), 'wb').close()
        rep = self.R.review(self.dir)
        path = self.R.approve(self.dir, rep)
        with open(path, encoding='utf-8') as fh:
            body = fh.read()
        self.assertIn('NOT yet cleared to publish', body)
        self.assertNotIn('post without watching', body,
                         'the gate must not tell a publisher it can skip '
                         'looking; no check here establishes taste')
        for seat in self.R.JUDGEMENT_SEATS:
            self.assertIn(seat, body)
        self.assertFalse(self.R.is_signed(self.dir))

    def test_signing_every_seat_clears_the_package(self):
        import os
        from brand.tokens import Brand
        self._write('reel_copy.txt', Brand.handle)
        open(os.path.join(self.dir, 'carousel_01_cover.jpg'), 'wb').close()
        rep = self.R.review(self.dir)
        path = self.R.approve(self.dir, rep)
        self.R.sign(self.dir, 'Gautam Paduvari')
        self.assertTrue(self.R.is_signed(self.dir))
        with open(path, encoding='utf-8') as fh:
            body = fh.read()
        self.assertIn('Cleared to publish', body)
        self.assertIn('Gautam Paduvari', body)

    def test_one_seat_is_not_all_three(self):
        import os
        from brand.tokens import Brand
        self._write('reel_copy.txt', Brand.handle)
        open(os.path.join(self.dir, 'carousel_01_cover.jpg'), 'wb').close()
        self.R.approve(self.dir, self.R.review(self.dir))
        self.R.sign(self.dir, 'Shameek', ('culture',))
        self.assertFalse(self.R.is_signed(self.dir))

    def test_an_unnamed_signature_is_refused(self):
        with self.assertRaises(ValueError):
            self.R.sign(self.dir, '   ')

    def test_an_unknown_seat_is_refused(self):
        with self.assertRaises(ValueError):
            self.R.sign(self.dir, 'Somebody', ('vibes',))


class ThingsTheEngineReadsAsAFullStop(unittest.TestCase):
    """D53: a dot that is not a sentence end is heard, never seen.

    Two of these shipped and a listener caught them, not the pipeline:
    "₹1.10 ಲಕ್ಷ" was read as "one" … "ten lakh" — a different amount with a
    pause inside it — and "ಕೆ. ಜೆ. ಜಾರ್ಜ್" was read with a long gap between
    the letters of a man's name.
    """

    @classmethod
    def setUpClass(cls):
        from brand import voice as V
        from brand import review as R
        cls.V, cls.R = V, R

    def test_initials_lose_their_dots(self):
        for src in ('ಸಚಿವ ಕೆ.ಜೆ. ಜಾರ್ಜ್ ಅವರು', 'ಸಚಿವ ಕೆ. ಜೆ. ಜಾರ್ಜ್ ಅವರು'):
            out = self.V._spoken(src)
            self.assertIn('ಕೆ ಜೆ ಜಾರ್ಜ್', out, out)
            self.assertNotIn('ಕೆ.', out)

    def test_an_abbreviation_is_not_mistaken_for_an_initial(self):
        """ಡಾ. is two letters and a dot — the same shape as an initial."""
        self.assertIn('ಡಾಕ್ಟರ್', self.V._spoken('ಡಾ. ರಮೇಶ್ ತಿಳಿಸಿದರು'))

    def test_money_is_spoken_in_whole_units_of_the_scale_below(self):
        """₹1.10 ಲಕ್ಷ is one lakh and ten thousand, and is said that way."""
        out = self.V._spoken('ಅಂಗಡಿಯಲ್ಲಿದ್ದ ₹1.10 ಲಕ್ಷ ಕಳವು')
        self.assertIn('1 ಲಕ್ಷದ 10 ಸಾವಿರ', out)
        self.assertIn('ರೂಪಾಯಿ', out)
        self.assertNotIn('1.10', out)

    def test_the_scale_ratio_is_respected(self):
        """A lakh is 100 thousand; a thousand is only 10 hundred."""
        self.assertIn('2 ಕೋಟಿಯ 50 ಲಕ್ಷ', self.V._spoken('₹2.5 ಕೋಟಿ'))
        self.assertIn('1 ಸಾವಿರದ 5 ನೂರು', self.V._spoken('1.5 ಸಾವಿರ ಜನ'))
        # the first cut multiplied by a flat ten and turned 1.10 lakh into
        # eleven lakh
        self.assertNotIn('100 ಸಾವಿರ', self.V._spoken('₹1.10 ಲಕ್ಷ'))

    def test_a_bare_decimal_becomes_a_spoken_point(self):
        self.assertIn('29 ಪಾಯಿಂಟ್ 6', self.V._spoken('ತಾಪಮಾನ 29.6 ಡಿಗ್ರಿ'))

    def test_no_beat_of_a_real_edition_carries_a_tts_hazard(self):
        from brand.content import Edition
        ed = Edition.load('tests/fixture_edition.json')
        for i, st in enumerate(ed.stories, 1):
            bad = self.R.check_narration(st, self.V.narration_beats(st))
            self.assertEqual(bad, [], f'story {i}: {bad}')

    def test_the_gate_objects_to_every_hazard(self):
        beats = [('lead', 'ಕೆ. ಜೆ. ಜಾರ್ಜ್ ₹1.10 ಲಕ್ಷ 9:15 40%')]
        found = self.R.check_narration(None, beats)
        self.assertEqual(len(found), 5, found)

    def test_the_chunker_never_splits_inside_a_number_or_a_name(self):
        """Each chunk is a separate request and a separate MP3, so a split is
        an audible gap. It used to split on every '.'."""
        import re
        text = 'ನಮಸ್ಕಾರ. ಕೆ ಜೆ ಜಾರ್ಜ್ 1 ಲಕ್ಷದ 10 ಸಾವಿರ ರೂಪಾಯಿ. ಮುಂದಿನ ಸುದ್ದಿ.'
        parts = [p for p in re.split(r'(?<=[.!?।])(?=\s|$)', text) if p.strip()]
        self.assertEqual(len(parts), 3)
        self.assertTrue(any('ಕೆ ಜೆ ಜಾರ್ಜ್' in p and 'ಸಾವಿರ' in p for p in parts),
                        'a name and its figure were split across requests')



class GreetingContract(unittest.TestCase):
    """D54: a festival wish is its own genre, with its own guards."""

    @classmethod
    def setUpClass(cls):
        from templates import greeting as G
        from brand.content import Photo, ContentError
        cls.G, cls.Photo, cls.CE = G, Photo, ContentError

    def _photo(self):
        return self.Photo(path='assets/logo.png', nature='ai',
                          credit='AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own')

    def test_a_photograph_must_declare_where_the_deity_is(self):
        g = self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ', photo=self._photo())
        with self.assertRaisesRegex(self.CE, 'keep_clear'):
            g.validate()
        self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ', photo=self._photo(),
                        keep_clear=(0.3, 0.66)).validate()

    def test_an_inverted_or_out_of_range_band_is_refused(self):
        for band in ((0.7, 0.3), (-0.1, 0.5), (0.2, 1.4)):
            with self.assertRaises(self.CE, msg=band):
                self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ', photo=self._photo(),
                                keep_clear=band).validate()

    def test_poster_copy_has_poster_limits(self):
        with self.assertRaisesRegex(self.CE, 'blessing'):
            self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ',
                            blessing='ಅ' * 97).validate()
        with self.assertRaisesRegex(self.CE, 'occasion'):
            self.G.Greeting(occasion='ಅ' * 31).validate()

    def test_an_unknown_theme_is_refused(self):
        with self.assertRaisesRegex(self.CE, 'theme'):
            self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ', theme='neon').validate()

    def test_a_greeting_is_not_a_story(self):
        """News fields on a greeting are a mistake, not extra data."""
        with self.assertRaisesRegex(self.CE, 'unknown greeting field'):
            self.G.Greeting.from_dict({'kind': 'greeting',
                                       'occasion': 'ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ',
                                       'headline': 'ಸುದ್ದಿ'})

    def test_render_py_routes_a_greeting_away_from_the_story_path(self):
        import json
        import os
        import tempfile
        import render
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                         encoding='utf-8') as f:
            json.dump({'kind': 'greeting', 'occasion': 'ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ'}, f,
                      ensure_ascii=False)
        try:
            kind, g = render.load(f.name)
        finally:
            os.remove(f.name)
        self.assertEqual(kind, 'greeting')
        self.assertIsInstance(g, self.G.Greeting)

    def test_the_disclosure_travels_with_the_poster_and_the_caption(self):
        g = self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ', photo=self._photo(),
                            keep_clear=(0.3, 0.66))
        self.assertEqual(self.G.disclosure_label(g.photo), 'ಎಐ ರಚಿತ ಚಿತ್ರ')
        c = self.G.greeting_copy(g)
        self.assertIn('ಎಐ ರಚಿತ ಚಿತ್ರ', c['instagram'])
        self.assertIn('ಎಐ ರಚಿತ ಚಿತ್ರ', c['whatsapp'])

    def test_the_caption_carries_the_handle_exactly(self):
        from brand.tokens import Brand
        c = self.G.greeting_copy(self.G.Greeting(occasion='ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ'))
        self.assertIn(Brand.handle, c['instagram'])
        self.assertIn(Brand.handle, c['whatsapp'])


class LockV10(unittest.TestCase):
    """D55 — no source, no claim. Generated pictures say they are generated."""

    def test_grievance_officer_is_named_with_a_watched_contact(self):
        from brand.tokens import Brand
        self.assertTrue(Brand.grievance_named())
        line = Brand.grievance_line()
        self.assertIn('Gautam Paduvari', line)
        self.assertIn('96117', line)
        self.assertIn('oormanisuddi@gmail.com', line)
        self.assertNotIn('Instagram DM', line)
        ch = Brand.channels_block()
        self.assertIn('youtube.com/@oormanisuddi', ch)
        self.assertIn('instagram.com/oormanisuddi', ch)
        self.assertIn('chat.whatsapp.com/', ch)
        self.assertIn('9611756514', ch)

    def test_sourced_story_without_url_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'source_url'):
            base(source_urls=[]).validate()

    def test_own_reporting_needs_no_url(self):
        base(sources=['ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ'], source_urls=[]).validate()

    def test_unknown_category_is_refused(self):
        with self.assertRaisesRegex(ContentError, 'unknown category'):
            base(category='governance').validate()

    def test_ai_credit_cannot_wear_representative(self):
        """D57: a credit naming an AI image cannot wear 'representative'."""
        with self.assertRaisesRegex(ContentError, "nature='ai'"):
            base(photo=pic(nature='representative',
                           credit='AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ')).validate()

    def test_generated_stock_is_labelled_ai(self):
        """D57: reused stock is still generated, so it still says so."""
        s = base(photo=pic(nature='ai', credit='AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ',
                           caption='ಪೊಲೀಸ್ ದಳ')).validate()
        self.assertIn('ಎಐ ರಚಿತ', s.credit_line)

    def test_obituary_needs_two_sources(self):
        with self.assertRaisesRegex(ContentError, 'obituary'):
            base(category='obituary', sources=['ಒಂದು ಮೂಲ'],
                 source_urls=['https://example.test/obit']).validate()
        base(category='obituary',
             sources=['ಮೂಲ ಒಂದು', 'ಮೂಲ ಎರಡು'],
             source_urls=['https://example.test/a', 'https://example.test/b']
             ).validate()

    def test_limits_are_the_single_source(self):
        """D56: one set of numbers, quoted everywhere else by name."""
        from brand.tokens import Limits, Motion
        self.assertEqual(Motion.reel_line_budget, Limits.reel_line_chars)
        self.assertEqual(Motion.reel_fail_seconds, Limits.reel_fail_seconds)

    def test_reel_opens_on_the_news_not_a_greeting(self):
        """D58, and D39 before it: the first beat is the hook."""
        from brand.voice import narration_beats
        beats = dict(narration_beats(base(headline='ಕುಂದಾಪುರದಲ್ಲಿ ಭಾರಿ ಮಳೆ',
                                          reel_line='ಕುಂದಾಪುರಕ್ಕೆ ಭಾರಿ ಮಳೆ')))
        self.assertNotIn('ನಮಸ್ಕಾರ', beats['lead'])
        self.assertIn('ಮಳೆ', beats['lead'])

    def test_tip_sheet_does_not_invent_copy(self):
        from scripts.fetch_daily_news import Tip, render_markdown
        md = render_markdown([
            Tip(headline='Udupi rain', source_name='ಉದಯವಾಣಿ',
                source_url='https://example.test/u', snippet='40 mm',
                taluk='ಉಡುಪಿ', risk='normal'),
        ], '2026-09-16')
        self.assertIn('TIPS, not copy', md)
        self.assertIn('https://example.test/u', md)
        self.assertNotIn('official statement', md.lower())


if __name__ == '__main__':
    unittest.main()


class EveryDecisionIsAccountedFor(unittest.TestCase):
    """D67: a decision with nothing behind it is a paragraph, not a rule.

    `docs/TRACEABILITY.md` is generated, so it cannot drift — but nothing
    stopped somebody adding a D-number and no enforcement. This is the check
    that makes "we write decisions down" mean something. The bar is not "every
    decision has a unit test": some are guarded by the golden fingerprints and
    two are honestly untestable. The bar is that every decision is in ONE of
    those three buckets, deliberately, with a reason.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        spec = importlib.util.spec_from_file_location(
            'traceability', os.path.join(root, 'docs', '_build_traceability.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls.T = mod

    def test_no_decision_is_enforced_by_nothing(self):
        _body, unenforced = self.T.build()
        self.assertFalse(
            unenforced,
            f'{len(unenforced)} decision(s) are enforced by nothing: '
            f'{", ".join(unenforced)}.\n'
            f'Write a test that names the number, or add it to '
            f'GOLDEN_GUARDED / UNTESTABLE in docs/_build_traceability.py '
            f'with a reason somebody would defend.')

    def test_decision_numbers_are_unique(self):
        """Two D29s made "see D29" ambiguous in four files for months."""
        import re, os, collections
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'docs', 'DECISIONS.md'),
                  encoding='utf-8') as fh:
            nums = re.findall(r'^##\s+(D\d+)\s*[·•\-—]', fh.read(), re.M)
        dupes = [n for n, c in collections.Counter(nums).items() if c > 1]
        self.assertFalse(dupes, f'duplicate decision number(s): {dupes}. '
                                f'A decision number is a reference; two of '
                                f'them is a broken link.')

    def test_the_exemption_lists_only_name_real_decisions(self):
        """An exemption for a decision that does not exist hides a gap."""
        known = {n for n, _t in self.T.decisions()}
        for name, table in (('UNTESTABLE', self.T.UNTESTABLE),
                            ('GOLDEN_GUARDED', self.T.GOLDEN_GUARDED)):
            stale = sorted(set(table) - known)
            self.assertFalse(stale, f'{name} names decisions that no longer '
                                    f'exist: {stale}')

    def test_every_exemption_carries_a_reason(self):
        for name, table in (('UNTESTABLE', self.T.UNTESTABLE),
                            ('GOLDEN_GUARDED', self.T.GOLDEN_GUARDED)):
            for num, why in table.items():
                self.assertTrue(
                    why and len(why) > 10,
                    f'{name}[{num}] has no reason; an exemption list nobody '
                    f'defends is a way to make the number look better')


class EditorialDriftIsNoticed(unittest.TestCase):
    """D68: crime wins the reel gate every time, so the gate cannot limit it.

    Step 2's reel test is "drama, public stakes, shareability". Crime scores
    highest on all three, every day. Add a metrics loop that rewards what
    performs and the channel walks into being a crime channel — which is
    exactly where every legal exposure in this system lives, and where local
    outlets reliably end up. Nobody decides that; it just happens.
    """

    @classmethod
    def setUpClass(cls):
        from brand import review as R
        cls.R = R

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _edition(self, categories, reels=()):
        from brand.content import Story, Edition, Photo, now, OWN_REPORTING
        stories = []
        for i, c in enumerate(categories):
            head = ('ಕಳವು ಆರೋಪ: ಬಂಧನ' if c == 'crime'
                    else f'ಪರೀಕ್ಷಾ ಶೀರ್ಷಿಕೆ {i}')
            stories.append(Story(
                headline=head, category=c, sources=[OWN_REPORTING],
                verified_by='Gautam Paduvari', is_reel=(i in reels),
                photo=Photo('x.jpg', nature='representative',
                            credit='ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own')))
        return Edition(stories=stories, date=now(), edition_no=1)

    def test_two_crime_reels_in_one_day_is_flagged(self):
        from brand.tokens import Limits
        ed = self._edition(['crime', 'crime', 'civic'], reels=(0, 1))
        rep = self.R.review(self.dir, ed)
        self.assertIn('PUB-04', [f.code for f in rep.findings])
        self.assertTrue(any('crime reels' in w for w in rep.warn))
        self.assertEqual(Limits.crime_reels_per_day, 1)

    def test_one_crime_reel_is_a_normal_day(self):
        ed = self._edition(['crime', 'civic', 'weather'], reels=(0,))
        rep = self.R.review(self.dir, ed)
        self.assertFalse([w for w in rep.warn if 'crime reels' in w])

    def test_an_edition_that_is_mostly_crime_is_flagged(self):
        ed = self._edition(['crime', 'crime', 'crime', 'civic'])
        rep = self.R.review(self.dir, ed)
        self.assertTrue(any('are crime' in w for w in rep.warn))

    def test_a_balanced_edition_is_not_flagged(self):
        ed = self._edition(['crime', 'civic', 'weather', 'health'])
        rep = self.R.review(self.dir, ed)
        self.assertFalse([w for w in rep.warn if 'are crime' in w])

    def test_it_warns_and_never_blocks(self):
        """A real crime day is a real crime day. This is a direction check,
        not a legal one, and blocking it would be the system overruling an
        editor on news judgement — which is the one thing it must not do."""
        ed = self._edition(['crime', 'crime', 'crime'], reels=(0, 1, 2))
        rep = self.R.review(self.dir, ed)
        self.assertFalse([f for f in rep.findings
                          if f.code == 'PUB-04' and f.severity == 'fail'])


class AMusicLicenceMustBeProducible(unittest.TestCase):
    """D74: a licence you cannot point at is one you cannot produce.

    'recorded-in-project' is not a licence. It is a note saying the terms were
    written down somewhere — which is exactly what nobody can find eighteen
    months later, when a Content ID claim lands on a film that has been up
    since Ganesha. The quarterly audit found one of these already marked
    allowed and in use.
    """

    def test_the_register_and_the_disk_agree(self):
        from brand import music
        problems = [m for m in music.audit()
                    if 'on disk and not in the register' in m
                    or 'registered and not on disk' in m]
        self.assertFalse(problems, '\n  ' + '\n  '.join(problems))

    def test_every_allowed_third_party_bed_can_be_produced(self):
        from brand import music
        gaps = [m for m in music.audit() if 'source_url' in m]
        self.assertFalse(
            gaps,
            '\n  ' + '\n  '.join(gaps)
            + '\n\nEither paste the licence page into assets/LICENCES.json, '
              'or set the track to blocked until somebody can.')

    def test_a_self_made_bed_needs_no_url(self):
        """You cannot link to the licence for something you made yourself."""
        from brand import music
        self.assertIsNone(music.check_path('assets/news_bgm.mp3'))

    def test_an_unregistered_bed_is_refused(self):
        from brand import music
        err = music.check_path('assets/bgm_options/does_not_exist.mp3')
        self.assertTrue(err)
        self.assertIn('licence register', err)

    def test_blocked_tracks_stay_on_disk(self):
        """Deleting the evidence of what was used is worse than blocking it."""
        import json, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'assets', 'LICENCES.json'),
                  encoding='utf-8') as fh:
            reg = json.load(fh)
        blocked = [r for r in reg['tracks'] if r.get('status') == 'blocked']
        self.assertTrue(blocked, 'the register has stopped recording refusals')
        for r in blocked[:3]:
            self.assertTrue(os.path.exists(os.path.join(root, r['path'])),
                            f'{r["path"]} was deleted rather than blocked')


class EveryCarouselSlideCarriesAPhotograph(unittest.TestCase):
    """House rule 2026-09-17-03, enforced as IMG-04.

    It blocks rather than warns, on purpose. A warning is a line you scroll
    past at 08:00 with a bulletin due, which is exactly the morning a slide
    ships with a blank plate where a picture should be. The fix costs
    seconds — assets/stock/ is right there, and CATALOG.md says what is in
    it — so the block is cheap to clear and the warning was not cheap to
    ignore.
    """

    def setUp(self):
        import tempfile
        from brand import review as R
        from brand.content import Story, Edition, Photo, OWN_REPORTING
        self.R, self.dir = R, tempfile.mkdtemp()
        self.Story, self.Edition, self.Photo = Story, Edition, Photo
        self.OWN = OWN_REPORTING
        import os
        for n in ('carousel_01_cover.jpg', 'carousel_02.jpg'):
            open(os.path.join(self.dir, n), 'wb').close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _story(self, photo):
        return self.Story(
            headline='ಬೈಂದೂರಿನಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ',
            category='weather', location='ಬೈಂದೂರು',
            sources=[self.OWN], verified_by='Gautam Paduvari', photo=photo)

    def _stock(self):
        return self.Photo('assets/stock/coastal_nh66_highway_traffic.jpg',
                          nature='ai', credit='AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ',
                          licence='own', caption='ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ')

    def _codes(self, ed):
        rep = self.R.review(self.dir, ed)
        return {f.code for f in rep.findings if f.severity == 'fail'}

    def test_a_slide_with_no_photograph_blocks_the_package(self):
        ed = self.Edition(stories=[self._story(self._stock()),
                                   self._story(None)], edition_no=1)
        self.assertIn('IMG-04', self._codes(ed))

    def test_every_slide_illustrated_clears_this_check(self):
        ed = self.Edition(stories=[self._story(self._stock()),
                                   self._story(self._stock())], edition_no=1)
        self.assertNotIn('IMG-04', self._codes(ed))

    def test_the_code_means_what_the_registry_says_it_means(self):
        """It had been raised as IMG-01, which the registry defines as a
        missing disclosure line — a different failure entirely. Two faults
        sharing one code is a code that cannot be looked up."""
        from brand.codes import CODES
        self.assertIn('IMG-04', CODES)
        self.assertIn('carousel', CODES['IMG-04'])
        self.assertIn('disclosure', CODES['IMG-01'])
