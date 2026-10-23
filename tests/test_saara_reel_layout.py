"""D133 — the reel's page fits itself on days nobody has seen.

Each case lays the REAL page out in headless Chrome (a few seconds, no voice, no film) and
asserts it reports nothing that does not fit — or, for copy that cannot fit at all, that it SAYS so
rather than overflowing. Skipped where Chrome is not installed (health.py names that).
"""
import datetime
import unittest

from brand import saara_reel as R
from brand.content import Edition, Story

DAY = datetime.datetime(2026, 10, 23, 9, 0)


def S(head, support='', loc='ಕುಂದಾಪುರ', cat='civic', deck='', reel=True):
    return Story(headline=head, reel_line=head if reel else '', reel_support=support, deck=deck,
                 location=loc, category=cat, segment='saara')


FIVE = [
    S('ಮದ್ಯ ಮಾರಾಟ ನಿಷೇಧ, ಒಣದಿನ ಘೋಷಣೆ', 'ಮೆರವಣಿಗೆಯ ಶಾಂತಿ ಕಾಪಾಡಲು ಮುನ್ನೆಚ್ಚರಿಕಾ ಕ್ರಮವಾಗಿ ಈ ನಿರ್ಧಾರ.', 'ಕುಂದಾಪುರ, ಗಂಗೊಳ್ಳಿ'),
    S('ದಸರಾ ಕಂಬಳದಲ್ಲಿ ಕೋಣಗಳಿಗೆ ಚಿನ್ನ', 'ಗಣೇಶ್ ಪೂಜಾರಿ ಅವರ ಕೋಣಗಳು ಪ್ರಥಮ ಸ್ಥಾನದೊಂದಿಗೆ ಚಿನ್ನ ಗೆದ್ದಿವೆ.', 'ಬೈಂದೂರು', 'sport'),
    S('ಮಾರಿಕಾಂಬ ದೇವಸ್ಥಾನದಲ್ಲಿ 33ನೇ ಶಾರದೋತ್ಸವ', 'ಮೂರು ದಿನ ಪೂಜೆ, ಭಜನೆ ಹಾಗೂ ಅನ್ನಸಂತರ್ಪಣೆ ಶ್ರದ್ಧೆಯಿಂದ ನೆರವೇರಿತು.', 'ಕಳವಾಡಿ', 'culture'),
    S('ಐದು ಗ್ರಾಮ ಕೈಬಿಡಲು ಸಚಿವರಿಗೆ ಮನವಿ', 'ಸೂಕ್ತ ಕಾನೂನು ಕ್ರಮದ ಭರವಸೆ ನೀಡಿದ ಸಚಿವ ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ.', 'ಬೈಂದೂರು'),
    S('ಅಂಗನವಾಡಿ ಶಿಕ್ಷಕಿಗೆ ಭಾವನಾತ್ಮಕ ವಿದಾಯ', 'ಗ್ರಾಮಸ್ಥರು ಹಾಗೂ ಪೋಷಕರು ಸನ್ಮಾನಿಸಿ ಪ್ರೀತಿಯ ವಿದಾಯ ಕೋರಿದರು.', 'ಕಳವಾಡಿ, ಕುಂದಾಪುರ', 'education'),
]
SIXTH = S('ರಸ್ತೆ ಕಾಮಗಾರಿ ಆರಂಭ', 'ಹೆದ್ದಾರಿ ಅಗಲೀಕರಣ ಕಾಮಗಾರಿ ಸೋಮವಾರ ಆರಂಭವಾಗಲಿದೆ.', 'ತ್ರಾಸಿ')


def check(stories):
    return R.check(Edition(stories=stories, date=DAY))


@unittest.skipUnless(R.available(), 'Google Chrome is not installed')
class ThePageFitsItself(unittest.TestCase):
    def test_every_number_of_stories_the_format_takes(self):
        for n in range(2, 7):
            r = check((FIVE + [SIXTH])[:n])
            self.assertEqual(r['issues'], [], n)
            self.assertEqual(max(r['lines']), 2, n)
            top, bottom = r['cover']['top'], r['cover']['bottom']
            self.assertLessEqual(bottom, 1480, n)                       # clear of the Reels caption
            self.assertGreaterEqual(top, 800, n)                       # below the count and the title

    def test_a_long_headline_takes_a_third_line_and_is_warned_not_cut(self):
        r = check([S('ಉಡುಪಿ ಜಿಲ್ಲೆಯ ಎಲ್ಲ ಸರ್ಕಾರಿ ಶಾಲೆಗಳಲ್ಲಿ ಮಧ್ಯಾಹ್ನದ ಬಿಸಿಯೂಟಕ್ಕೆ ಹೊಸ ವ್ಯವಸ್ಥೆ ಜಾರಿ',
                     'ಹೊಸ ಮೆನು ಸೋಮವಾರದಿಂದ ಜಾರಿಗೆ ಬರಲಿದೆ.', 'ಉಡುಪಿ', 'education'), FIVE[1]])
        self.assertEqual(r['issues'], [])
        self.assertEqual(r['lines'][0], 3)
        self.assertTrue(any('reel_line runs to 3 lines' in w for w in r['warnings']))

    def test_a_headline_no_size_can_hold_is_reported_as_not_fitting(self):
        r = check([S('ಕರಾವಳಿ ಕರ್ನಾಟಕದ ಬಂದರುಗಳ ಅಭಿವೃದ್ಧಿಗಾಗಿ ಕೇಂದ್ರ ಸರ್ಕಾರ ಮಂಜೂರು ಮಾಡಿದ ಹೊಸ ಯೋಜನೆಯ ಕಾಮಗಾರಿ ಮುಂದಿನ ತಿಂಗಳಿನಿಂದ ಆರಂಭ',
                     'ಯೋಜನೆಗೆ ನೂರ ಇಪ್ಪತ್ತು ಕೋಟಿ ರೂಪಾಯಿ ಮಂಜೂರಾಗಿದೆ.', 'ಮಂಗಳೂರು', 'fisheries'), FIVE[1]])
        self.assertTrue(any('does not fit above the card' in i for i in r['issues']))

    def test_markup_in_the_copy_is_text(self):
        r = check([S('ಕಂಪನಿ A&B <ಹೊಸ> ಯೋಜನೆ</script>', 'ಎ&ಬಿ ಕಂಪನಿ <b>ಹೊಸ</b> ಯೋಜನೆ ಆರಂಭ.', 'ಉಡುಪಿ & ಮಣಿಪಾಲ'), FIVE[1]])
        self.assertEqual(r['issues'], [])
        self.assertEqual(r['copies'][0]['place'], 'ಉಡುಪಿ · ಮಣಿಪಾಲ')

    def test_one_enormous_word_shrinks_to_fit(self):
        r = check([S('ಸ್ವಾತಂತ್ರ್ಯೋತ್ಸವಾಚರಣೆಯ ಸಂಭ್ರಮಾಚರಣೆ', 'ಸ್ವಾತಂತ್ರ್ಯೋತ್ಸವಾಚರಣೆಯ ಸಂಭ್ರಮ ಎಲ್ಲೆಡೆ ಕಂಡುಬಂದಿತು.', 'ಕಾರ್ಕಳ', 'culture'), FIVE[1]])
        self.assertEqual(r['issues'], [])

    def test_a_card_sentence_longer_than_three_lines_rolls_and_still_fits(self):
        long_ = ('ಜಿಲ್ಲಾಡಳಿತದ ಆದೇಶದಂತೆ ಎಲ್ಲ ಮದ್ಯದಂಗಡಿಗಳು ಹಾಗೂ ಬಾರ್‌ಗಳನ್ನು ಮುಚ್ಚುವಂತೆ ಕಟ್ಟುನಿಟ್ಟಿನ ಸೂಚನೆ '
                 'ನೀಡಲಾಗಿದೆ ಎಂದು ಅಧಿಕಾರಿಗಳು ತಿಳಿಸಿದ್ದಾರೆ.')
        r = check([S('ಒಣದಿನ ಘೋಷಣೆ', long_, 'ಕುಂದಾಪುರ'), FIVE[1], FIVE[2]])
        self.assertEqual(r['issues'], [])

    def test_a_day_written_for_the_carousel_still_lays_out_and_says_what_it_lacks(self):
        r = check([S('ಬೈಂದೂರು: ಕಡಲ್ಕೊರೆತ ತಡೆಗೆ ತುರ್ತು ಕ್ರಮ', '', 'ಬೈಂದೂರು', 'fisheries',
                     deck='ಕಡಲ್ಕೊರೆತ ತಡೆಯಲು ತುರ್ತು ಕ್ರಮ ಕೈಗೊಳ್ಳಲಾಗಿದೆ. ಮೀನುಗಾರರಿಗೆ ಎಚ್ಚರಿಕೆ ನೀಡಲಾಗಿದೆ.', reel=False), FIVE[1]])
        self.assertEqual(r['issues'], [])
        self.assertTrue(any('no reel_line' in w for w in r['warnings']))
        self.assertTrue(any('no reel_support' in w for w in r['warnings']))
        self.assertIn('ಕಡಲ್ಕೊರೆತ', r['copies'][0]['body'])


if __name__ == '__main__':
    unittest.main()
