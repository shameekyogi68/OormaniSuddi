"""D133 — own-reporting stories are compared with the editor's kept paste, not waved through.

Found by the 2026-10-23 dress rehearsal: a story with no URL was marked 'own' and its figures were
never compared with anything, although the paste sat in inbox/sources/own_*.txt.
"""
import os
import tempfile
import unittest
from unittest import mock

from brand import factcheck as F
from brand.content import OWN_REPORTING, Story

PASTE = ('own reporting / press release — no URL\n\n'
         'ಕಳವಾಡಿ — ಈಶ್ವರ ಮಾರಿಕಾಂಬ ದೇವಸ್ಥಾನದಲ್ಲಿ ವಿಜೃಂಭಣೆಯಿಂದ ಸಂಪನ್ನಗೊಂಡ 33ನೇ ಶಾರದೋತ್ಸವ\n'
         'ಮೂರು ದಿನಗಳ ಕಾಲ ಪೂಜಾ ಕೈಂಕರ್ಯಗಳು, ಭಜನಾ ಕಾರ್ಯಕ್ರಮಗಳು ಹಾಗೂ ಅನ್ನಸಂತರ್ಪಣೆ ನೆರವೇರಿತು.\n'
         'ಬೈಂದೂರು: ಪಟ್ಟಣ ಪಂಚಾಯತ್‌ನಿಂದ ಗ್ರಾಮೀಣ ಭಾಗ ಕೈಬಿಡಲು ಸಚಿವರಿಗೆ ಮನವಿ ಮಾಡಲಾಗಿದೆ.\n')


def story(**kw):
    base = dict(headline='ಕಳವಾಡಿ: ಈಶ್ವರ ಮಾರಿಕಾಂಬ ದೇವಸ್ಥಾನದಲ್ಲಿ 33ನೇ ಶಾರದೋತ್ಸವ ಸಂಪನ್ನ',
                deck='ಮೂರು ದಿನಗಳ ಕಾಲ ಪೂಜಾ ಕೈಂಕರ್ಯಗಳು, ಭಜನಾ ಕಾರ್ಯಕ್ರಮಗಳು ನೆರವೇರಿತು.',
                sources=[OWN_REPORTING], location='ಕಳವಾಡಿ', category='culture',
                segment='saara')
    base.update(kw)
    return Story(**base)


class OwnReporting(unittest.TestCase):
    def run_check(self, s, paste=PASTE):
        with tempfile.TemporaryDirectory() as tmp:
            if paste is not None:
                with open(os.path.join(tmp, 'own_abc.txt'), 'w', encoding='utf-8') as fh:
                    fh.write(paste)
            with mock.patch.object(F, 'SOURCES_DIR', tmp):
                return F.check(s)

    def test_a_figure_the_paste_never_says_is_caught(self):
        r = self.run_check(story(headline='ಕಳವಾಡಿ: ಈಶ್ವರ ಮಾರಿಕಾಂಬ ದೇವಸ್ಥಾನದಲ್ಲಿ 44ನೇ ಶಾರದೋತ್ಸವ ಸಂಪನ್ನ'))
        self.assertTrue(r.kept_paste)
        self.assertTrue(r.figures)

    def test_the_paste_that_carries_it_passes(self):
        r = self.run_check(story())
        self.assertTrue(r.kept_paste)
        self.assertEqual(r.figures, [])

    def test_no_kept_paste_leaves_it_own_as_before(self):
        self.assertEqual(self.run_check(story(), paste=None).state, 'own')

    def test_a_suffix_after_a_zero_width_joiner_is_not_a_word_of_its_own(self):
        s = story(headline='ಬೈಂದೂರು: ಪಟ್ಟಣ ಪಂಚಾಯತ್‌ನಿಂದ ಗ್ರಾಮೀಣ ಭಾಗ ಕೈಬಿಡಲು ಸಚಿವರಿಗೆ ಮನವಿ', deck='')
        r = self.run_check(s, paste=PASTE.replace('‌', ''))        # the paste lost its joiner
        self.assertEqual(r.names, [])


if __name__ == '__main__':
    unittest.main()
