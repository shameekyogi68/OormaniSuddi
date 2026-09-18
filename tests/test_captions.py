"""
One file per post, and nothing in it but the caption. House rule
2026-09-17-06.
=============================================================================
Every render already wrote a `_copy.txt` carrying the caption, the first
comment, the WhatsApp forward and the YouTube fields under banner headings.
That is a working sheet, and it is the right shape for reading. It is the
wrong shape for the two seconds in which somebody on a phone selects all and
pastes into Instagram — which is what these files are for.

So the thing worth asserting is a negative: the caption file must not
contain the neighbouring copy. A first comment pasted into the caption is a
caption with a duplicate call-to-action in it, and nobody proof-reads a
paste.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import render
from brand import copy as C
from brand.content import Story, Edition, Photo, OWN_REPORTING


def story(**kw) -> Story:
    base = dict(
        headline='ಬೈಂದೂರಿನಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ',
        category='weather', location='ಬೈಂದೂರು',
        points=['ತಗ್ಗು ಪ್ರದೇಶಗಳಲ್ಲಿ ನೀರು ನಿಂತಿದೆ.'],
        takeaway='ತುರ್ತು ಸಹಾಯಕ್ಕೆ 1077 ಸಂಪರ್ಕಿಸಿ.',
        sources=[OWN_REPORTING], verified_by='Gautam Paduvari',
        photo=Photo('x.jpg', nature='representative',
                    credit='ಊರ್ಮನಿ ಸುದ್ದಿ', licence='own'))
    base.update(kw)
    return Story(**base)


class WhichPlatformAPostBelongsTo(unittest.TestCase):

    def test_the_bulletin_and_its_thumbnail_are_youtube(self):
        for name in ('bulletin', 'bulletin_copy', 'youtube_thumb', 'yt_thumb'):
            self.assertEqual(C.platform_of(name), 'youtube', name)

    def test_cards_and_reels_are_instagram(self):
        """AI-card reels are Instagram's — AGENTS rule 7."""
        for name in ('carousel', 'reel', 'reel_01', 'post_01', 'story_card',
                    'broadsheet'):
            self.assertEqual(C.platform_of(name), 'instagram', name)


class TheCaptionFileHoldsOnlyTheCaption(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        render.write_copy(story(), self.tmp.name, 'carousel_copy')
        with open(os.path.join(self.tmp.name, 'carousel_caption.txt'),
                  encoding='utf-8') as fh:
            self.cap = fh.read()

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_file_is_named_for_the_post_not_for_the_copy_sheet(self):
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp.name, 'carousel_caption.txt')))

    def test_it_carries_no_banner_headings(self):
        """A heading in the file is a heading somebody pastes."""
        self.assertNotIn('═', self.cap)
        self.assertNotIn('INSTAGRAM CAPTION', self.cap)

    def test_it_does_not_carry_the_first_comment(self):
        c = C.for_story(story())
        self.assertTrue(c.first_comment, 'fixture should have a first comment')
        self.assertNotIn(c.first_comment.strip(), self.cap)

    def test_it_does_not_carry_the_whatsapp_forward_or_youtube_fields(self):
        c = C.for_story(story())
        self.assertNotIn(c.youtube_title.strip(), self.cap)
        self.assertNotIn('YOUTUBE', self.cap)
        # The WhatsApp forward opens with the headline in bold markers; that
        # asterisked form appearing here means the forward was pasted in.
        self.assertNotIn('*' + story().headline.strip() + '*', self.cap)

    def test_it_is_the_instagram_caption_verbatim(self):
        c = C.for_story(story())
        self.assertEqual(self.cap.strip(), c.instagram.strip())

    def test_it_still_ends_on_the_hashtags(self):
        """Hashtags are part of the caption, not an extra — they go in the
        same paste."""
        self.assertIn('#', self.cap.strip().split('\n')[-1])

    def test_the_working_sheet_is_untouched(self):
        """This is additive. `_copy.txt` is read by review.py and by
        MASTER_COPY, and it keeps its shape."""
        with open(os.path.join(self.tmp.name, 'carousel_copy.txt'),
                  encoding='utf-8') as fh:
            sheet = fh.read()
        self.assertIn('INSTAGRAM CAPTION', sheet)
        self.assertIn('WHATSAPP FORWARD', sheet)


class AYouTubePostGetsYouTubeFields(unittest.TestCase):

    def test_title_description_and_tags_each_labelled(self):
        """A title cannot be pasted into a description box, so this one post
        type needs its three fields named — and only those three."""
        with tempfile.TemporaryDirectory() as tmp:
            ed = Edition(stories=[story()], edition_no=1)
            render.write_copy(ed, tmp, 'bulletin_copy')
            with open(os.path.join(tmp, 'bulletin_caption.txt'),
                      encoding='utf-8') as fh:
                cap = fh.read()
        self.assertIn('TITLE', cap)
        self.assertIn('DESCRIPTION', cap)
        self.assertIn('TAGS', cap)
        self.assertNotIn('═', cap)
        self.assertNotIn('WHATSAPP', cap)

    def test_an_instagram_post_never_gets_the_youtube_shape(self):
        c = C.for_story(story())
        self.assertNotIn('TITLE', C.caption_text(c, 'instagram'))


class EveryPostKindGetsOne(unittest.TestCase):

    def test_each_render_name_produces_its_own_caption_file(self):
        names = ('carousel_copy', 'reel_copy', 'reel_01_copy', 'post_01_copy',
                'bulletin_copy')
        with tempfile.TemporaryDirectory() as tmp:
            ed = Edition(stories=[story()], edition_no=1)
            for n in names:
                render.write_copy(ed if 'carousel' in n or 'bulletin' in n
                                 else story(), tmp, n)
            made = sorted(f for f in os.listdir(tmp)
                         if f.endswith('_caption.txt'))
        self.assertEqual(made, ['bulletin_caption.txt', 'carousel_caption.txt',
                                'post_01_caption.txt', 'reel_01_caption.txt',
                                'reel_caption.txt'])


class WhatsAppGroupDigestFormat(unittest.TestCase):
    """House rule 2026-09-17-08: tailored WhatsApp digest for the daily edition."""

    def setUp(self):
        self.st1 = story(headline='ಬೈಂದೂರಿನಲ್ಲಿ ಭಾರಿ ಮಳೆ, ಜಿಲ್ಲಾಡಳಿತ ಎಚ್ಚರಿಕೆ', location='ಬೈಂದೂರು')
        self.st2 = story(headline='ಉಡುಪಿಯಲ್ಲಿ ಕರಾವಳಿ ಉತ್ಸವಕ್ಕೆ ದಿನಾಂಕ ನಿಗದಿ', location='ಉಡುಪಿ')
        self.ed = Edition(stories=[self.st1, self.st2], edition_no=1)

    def test_format_has_brand_tagline_and_numbered_emojis(self):
        w = C.edition_whatsapp(self.ed)
        self.assertIn('🌾 *ಊರ್ಮನಿ ಸುದ್ದಿ ·', w)
        self.assertIn('ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ', w)
        self.assertIn('1️⃣ *ಬೈಂದೂರು*: ಬೈಂದೂರಿನಲ್ಲಿ ಭಾರಿ ಮಳೆ', w)
        self.assertIn('2️⃣ *ಉಡುಪಿ*: ಉಡುಪಿಯಲ್ಲಿ ಕರಾವಳಿ ಉತ್ಸವಕ್ಕೆ', w)
        self.assertIn('📲 *ಪೂರ್ಣ ವರದಿ ಹಾಗೂ ವಿವರಣೆಗಾಗಿ ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಲಿಂಕ್ ನೋಡಿ:*', w)
        self.assertIn('👉 [ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಪೋಸ್ಟ್ ಲಿಂಕ್]', w)
        self.assertIn('📌 ಮೂಲ:', w)
        self.assertNotIn('ಫೋಟೋಗಳು', w)
        self.assertNotIn('photos', w.lower())

    def test_custom_instagram_link_substitution(self):
        w = C.edition_whatsapp(self.ed, instagram_url='https://instagram.com/p/test123')
        self.assertIn('👉 https://instagram.com/p/test123', w)

    def test_carousel_render_writes_whatsapp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            render.write_copy(self.ed, tmp, 'carousel_copy')
            w_path = os.path.join(tmp, 'carousel_whatsapp.txt')
            self.assertTrue(os.path.exists(w_path))
            with open(w_path, encoding='utf-8') as f:
                content = f.read()
            self.assertIn('1️⃣ *ಬೈಂದೂರು*:', content)
            self.assertNotIn('═', content)


if __name__ == '__main__':
    unittest.main()
