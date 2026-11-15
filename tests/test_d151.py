"""D151 — four faults every reviewer passed on 2026-11-15, each closed where it was made.

  * a borrowed word fused with its Kannada ending ("ಪಂಚಾಯತ್ನಲ್ಲಿ") on the screen and in every caption;
  * the WhatsApp digest saying the town twice on four lines and with no bold town on a fifth;
  * the frames a reviewer is told to open landing in a transition, so the follow card was never seen;
  * run_report.md saying "Failed … no APPROVAL.md" beside an APPROVAL.md, after a re-check.

(The fifth — a front-page row cut to its tail — needs Chrome: tests/test_saara_reel_layout.py.)
"""
import datetime
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from brand import copy as C                                    # noqa: E402
from brand import kannada_check as K                           # noqa: E402
from brand import reel_speech as RS                            # noqa: E402
from brand import review as RV                                 # noqa: E402
from brand.content import Edition, Story                       # noqa: E402
from brand.dispatch import copy_hash, fact_hash                # noqa: E402

J = K.ZWNJ
TMP = os.path.join(ROOT, 'build')          # inside the repository: nothing here writes outside it
os.makedirs(TMP, exist_ok=True)


def _read(p):
    with open(p, encoding='utf-8') as fh:
        return fh.read()


class ABorrowedWordTakesItsEndingAfterAJoiner(unittest.TestCase):
    WRONG = {'ಪಂಚಾಯತ್ನಲ್ಲಿ': f'ಪಂಚಾಯತ್{J}ನಲ್ಲಿ', 'ಪಂಚಾಯತ್ನ': f'ಪಂಚಾಯತ್{J}ನ', 'ಕಾಂಗ್ರೆಸ್ನ': f'ಕಾಂಗ್ರೆಸ್{J}ನ',
             'ಬ್ಯಾಂಕ್ಗೆ': f'ಬ್ಯಾಂಕ್{J}ಗೆ', 'ಸ್ಟೀವನ್ಗೆ': f'ಸ್ಟೀವನ್{J}ಗೆ', 'ಬಸ್ನಲ್ಲಿ': f'ಬಸ್{J}ನಲ್ಲಿ',
             'ಕಾರ್ಗಳು': f'ಕಾರ್{J}ಗಳು', 'ಕೋರ್ಟ್ನಿಂದ': f'ಕೋರ್ಟ್{J}ನಿಂದ', 'ಹೋಟೆಲ್ಗಳಲ್ಲಿ': f'ಹೋಟೆಲ್{J}ಗಳಲ್ಲಿ',
             'ಜಂಕ್ಷನ್ಗಳಲ್ಲಿ': f'ಜಂಕ್ಷನ್{J}ಗಳಲ್ಲಿ', 'ರಾಡ್ನಿಂದ': f'ರಾಡ್{J}ನಿಂದ', 'ಮೊಬೈಲ್ಗೆ': f'ಮೊಬೈಲ್{J}ಗೆ'}
    # native words with the same letters: none may be touched
    RIGHT = ('ರತ್ನ ಪ್ರಯತ್ನ ಯತ್ನ ಬಗ್ಗೆ ದುರ್ಗೆ ತನ್ನಲ್ಲಿ ನನ್ನ ನಿನ್ನೆ ಚಿನ್ನ ಸ್ನಾನ ಸ್ನೇಹ ಸ್ವಪ್ನ ನಿಮ್ನ ಮಾರ್ಗ ಮಾರ್ಗಗಳ ವರ್ಗಗಳು ಸ್ವರ್ಗ '
             'ಅಗ್ನಿಯಿಂದ ಪತ್ನಿಗೆ ಪ್ರಶ್ನೆ ವಿಘ್ನ ಲಗ್ನ ಕೃಷ್ಣ ಪೂರ್ಣ ಮಕ್ಕಳಿಗೆ ಹಳ್ಳಿಗೆ ಅಕ್ಕನ ಕಲ್ಲಿನ ಬೆಳಗ್ಗೆ ಉತ್ಸವ ಸಂಸ್ಕೃತಿ ಕಾರ್ಯಕ್ರಮ '
             'ನಿರ್ಗಮನ ಶಿಲ್ಪಗಳು ಮೃತಪಟ್ಟಿದ್ದಾರೆ ಅದ್ಧೂರಿ ದುರ್ಬಳಕೆ ಲೋಕಾಯುಕ್ತಕ್ಕೆ ಗಂಗೊಳ್ಳಿ ಕೊಲ್ಲೂರಿನಲ್ಲಿ ವಾಸ್ತವ್ಯ').split()

    def test_the_ending_is_joined(self):
        for wrong, right in self.WRONG.items():
            self.assertEqual(K.join_endings(wrong), right, wrong)

    def test_a_native_word_is_left_alone(self):
        for w in self.RIGHT:
            self.assertEqual(K.join_endings(w), w, w)

    def test_it_is_safe_to_do_twice(self):
        for right in self.WRONG.values():
            self.assertEqual(K.join_endings(right), right)

    def test_the_voice_and_the_screen_use_the_one_rule(self):
        self.assertEqual(RS.join_endings('ಪಂಚಾಯತ್ನಲ್ಲಿ ಹಣ'), f'ಪಂಚಾಯತ್{J}ನಲ್ಲಿ ಹಣ')

    def test_unjoined_names_the_words(self):
        self.assertEqual(K.unjoined('ಹೆಬ್ರಿ. ಗ್ರಾಮ ಪಂಚಾಯತ್ನಲ್ಲಿ ಹಣ ದುರ್ಬಳಕೆ'), ['ಪಂಚಾಯತ್ನಲ್ಲಿ'])

    def test_a_story_is_joined_as_it_is_loaded(self):
        raw = dict(headline='ಹೆಬ್ರಿ. ಗ್ರಾಮ ಪಂಚಾಯತ್ನಲ್ಲಿ ಹಣ ದುರ್ಬಳಕೆ ಆರೋಪ', reel_line='ಪಂಚಾಯತ್ನಲ್ಲಿ ಹಣ ದುರ್ಬಳಕೆ ಆರೋಪ',
                   deck='ಹೆಬ್ರಿ ಗ್ರಾಮ ಪಂಚಾಯತ್ನ ಗ್ರಾಮಸಭೆಯಲ್ಲಿ ಆರೋಪ.', points=['ಬ್ಯಾಂಕ್ಗೆ ಮನವಿ.'], location='ಹೆಬ್ರಿ')
        before = (copy_hash(raw), fact_hash(raw))
        st = Story.from_dict(raw)
        self.assertIn(f'ಪಂಚಾಯತ್{J}ನಲ್ಲಿ', st.headline)
        self.assertIn(f'ಪಂಚಾಯತ್{J}ನಲ್ಲಿ', st.reel_line)
        self.assertIn(f'ಪಂಚಾಯತ್{J}ನ ', st.deck)
        self.assertEqual(st.points, [f'ಬ್ಯಾಂಕ್{J}ಗೆ ಮನವಿ.'])
        # the desks' receipts are stamped on the file as written: a spelling joiner must not void them
        self.assertEqual((copy_hash(raw), fact_hash(raw)), before)
        self.assertEqual(Story.from_dict(st.to_dict()).headline, st.headline)


class TheWhatsAppDigestSaysTheTownOnce(unittest.TestCase):
    def digest(self, *pairs):
        ed = Edition(stories=[Story(headline=h, location=loc, category='civic', segment='saara', sources=['Udayavani'])
                              for h, loc in pairs], date=datetime.datetime(2026, 11, 15, 9, 0))
        text = C.edition_whatsapp(ed)
        return [ln for ln in text.splitlines() if ln[:1].isdigit() or '️⃣' in ln[:4]]

    def test_every_form_a_headline_opens_on_its_town(self):
        lines = self.digest(('ಬೈಂದೂರು. ವಂದೇ ಭಾರತ್ ರೈಲಿಗೆ ಸ್ವಾಗತ', 'ಬೈಂದೂರು'),
                            ('ಹೆಬ್ರಿ. ಪಂಚಾಯತ್‌ನಲ್ಲಿ ಹಣ ದುರ್ಬಳಕೆ ಆರೋಪ: ಆಕ್ರೋಶ', 'ಹೆಬ್ರಿ'),
                            ('ಕೋಟ: ಕೆರೆಯಲ್ಲಿ ಮುಳುಗಿ ದುರ್ಮರಣ', 'ಕೋಟ'),
                            ('ರಸ್ತೆ ಕಾಮಗಾರಿ ಆರಂಭ', 'ತ್ರಾಸಿ'),
                            ('ಕುಂದಾಪುರದಲ್ಲಿ ರಕ್ತದಾನ ಶಿಬಿರ', 'ಕುಂದಾಪುರ'))
        self.assertEqual(len(lines), 5)
        towns = ('ಬೈಂದೂರು', 'ಹೆಬ್ರಿ', 'ಕೋಟ', 'ತ್ರಾಸಿ', 'ಕುಂದಾಪುರ')
        for ln, town in zip(lines, towns):
            self.assertIn(f'*{town}*: ', ln)                  # every line opens on its town, in bold
        for ln, town in zip(lines[:4], towns):
            self.assertEqual(ln.count(town), 1, ln)           # and does not say it again
        self.assertIn('ಕುಂದಾಪುರದಲ್ಲಿ ರಕ್ತದಾನ', lines[4])           # a town inside a word is the headline's own
        self.assertTrue(lines[1].endswith('ಆರೋಪ: ಆಕ್ರೋಶ'), lines[1])


class TheFramesAReviewerOpensAreFinishedCards(unittest.TestCase):
    REPORT = dict(seconds=55.324, outro=51.624, pressAt=53.924,
                  beats=[dict(B=b) for b in (5.083, 13.77, 21.185, 28.923, 36.203, 44.123)])

    def times(self, rep, duration=55.4):
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            p = os.path.join(d, 'r.json')
            if rep is not None:
                with open(p, 'w', encoding='utf-8') as fh:
                    json.dump(rep, fh)
            return RV._settled_times(p, duration)

    def test_one_frame_per_story_and_the_close(self):
        t = self.times(self.REPORT)
        beats = [b['B'] for b in self.REPORT['beats']]
        self.assertEqual(len(t), len(beats) + 1)
        for i, b in enumerate(beats):
            end = (beats + [self.REPORT['outro']])[i + 1]
            self.assertTrue(b <= t[i] < end, (i, t[i]))
            self.assertLessEqual(end - t[i], 1.0)             # the card whole, just before it leaves
        self.assertGreater(t[-1], self.REPORT['pressAt'])     # the follow card, after its button has pressed
        self.assertLess(t[-1], 55.4)

    def test_no_report_or_a_wrong_one_falls_back(self):
        self.assertEqual(self.times(None), [])
        self.assertEqual(self.times({'beats': []}), [])
        self.assertEqual(self.times(dict(self.REPORT, outro=99)), [])


class ARecheckSaysSoAtTheTopOfTheRunReport(unittest.TestCase):
    def test_the_note_is_first_and_is_replaced_not_stacked(self):
        import regate

        class Rep:
            fail = ['fact-checker story 5: not yet checked in this form.']
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            p = os.path.join(d, 'run_report.md')
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write('# Build report\n\n## Failed\n\n- **finish** — 7 blocking fault(s) — no APPROVAL.md written\n')
            regate._note_run_report(d, Rep, False)
            held = _read(p)
            self.assertTrue(held.startswith('> **Gate re-checked'))
            self.assertIn('HELD on 1 fault(s)', held)
            self.assertIn('fact-checker story 5', held)
            Rep.fail = []
            regate._note_run_report(d, Rep, True)
            clean = _read(p)
            self.assertEqual(clean.count(regate.MARK), 1)
            self.assertIn('mechanically clean', clean)
            self.assertNotIn('HELD on', clean)
            self.assertIn('# Build report', clean)
            self.assertIn('is from then, not now', clean)

    def test_no_run_report_is_not_an_error(self):
        import regate
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            regate._note_run_report(d, type('R', (), {'fail': []}), True)
            self.assertEqual(os.listdir(d), [])


if __name__ == '__main__':
    unittest.main()
