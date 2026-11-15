"""D146 — the reel's voice, heard back by a Kannada-capable ear, word by word.

Every transcript below is a real one, written down on 2026-10-30 about the reel that went out that night: by
Gemini's audio models (blind — never shown the script) and by the reel's own Whisper. The checks that ran that night
scored these clips 0.87–0.98 and asked the editor to "listen for" the town. These tests pin that they HOLD now.

No network, no Chrome, no Gemini key: the ear's verdicts are computed from the transcripts.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import soundfile as sf

from brand import ear, lexicon, reel_listen
from brand import reel_speech as RS
from brand import voice
from brand.tokens import Limits

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'build').mkdir(exist_ok=True)

# (script, names, edges, what a strict Gemini ear wrote, what the reel's Whisper wrote)
PUBLISHED = {
    'story 2 headline — the town was never said':
        ('ವಂಡ್ಸೆ. ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು', ('ವಂಡ್ಸೆ',), True,
         'ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು', 'ಹಸಿಕಿಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು.'),
    'story 2 card — the first word was cut into':
        ('ಕಪ್ಪು ಸೈನಿಕ ನೊಣದ ಲಾರ್ವಾಗಳಿಂದ ಗೊಬ್ಬರ ತಯಾರಿಸಲಾಗುತ್ತಿದೆ', (), True,
         'ಹೂ ಸೈನಿಕ ನೊಣದ ಲಾರ್ವಾಗಳಿಂದ ಗೊಬ್ಬರ ತಯಾರಿಸಲಾಗುತ್ತಿದೆ', 'ಪು ಸೈಯನಿಕ ನೊಣದಲ್ ಆರ್ವಾಗಳಿಂದ ಗೊಬ್ಬರ ತೈಯಾರಿಸಲ್ ಆಗುತ್ತಿದೆ.'),
    'the hook — two towns said wrongly':
        ('ಬೈಂದೂರು, ವಂಡ್ಸೆ, ಹೆಮ್ಮಾಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ', ('ಬೈಂದೂರು', 'ವಂಡ್ಸೆ', 'ಹೆಮ್ಮಾಡಿ'), False,
         'ಬೈಂದೂರು ಒನ್ ಸೇ ಹೇಮಾಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ', 'ಬೈಂದೂರು ವನ್ಸೇ ಹೆಂಮಾಡಿ ಸೇರಿಡಂಟೆ ಇಂದಿನ ಸುದ್ದಿ.'),
}
RIGHT = {
    'story 1 headline': ('ಬೈಂದೂರು. ಬೆಂಗಳೂರು-ಕಾರವಾರ ವಂದೇ ಭಾರತ್ ಆರಂಭ', ('ಬೈಂದೂರು',), True,
                         'ಬೈಂದೂರು / ಬೆಂಗಳೂರು ಕಾರವಾರ ವಂದೇ ಭಾರತ್ ಆರಂಭ', 'ಬಯಿಂದುರು ಬೆಂಗಳುರು ಕಾರವಾರ ವಂದೆ ಭಾರತ ಆರಂಭಾ.'),
    'story 3 card (a listener may join or split words, and spell its own way)':
        ('ಅಂಧ ತಿರುವಿನಲ್ಲಿ ಮೂವತ್ತಕ್ಕೂ ಹೆಚ್ಚು ಅಪಘಾತಗಳು ನಡೆದಿವೆ', (), True,
         'ಅಂಧತಿರುವಿನಲ್ಲಿ ಮೂವತ್ತಕ್ಕೂ ಹೆಚ್ಚು ಅಪಘಾತಗಳು ನಡೆದಿವೆ', 'ಅಂಧಾ ತಿರುವಿನಲಿ ಮೂವತ್ತಕು ಹೆಚ್ಚು ಆಪಗಾತಗಳು ನಡದಿವೆ.'),
    'story 5 card (a figure said as words)':
        ('ಆರೋಪಿ ಸಹೋದರರಿಗೆ ನ್ಯಾಯಾಲಯ ಹದಿನಾಲ್ಕು ದಿನ ನ್ಯಾಯಾಂಗ ಬಂಧನ ವಿಧಿಸಿದೆ', (), True,
         'ಆರೋಪಿ ಸಹೋದರರಿಗೆ ನ್ಯಾಯಾಲಯ ಹದಿನಾಲ್ಕು ದಿನ ನ್ಯಾಯಾಂಗ ಬಂಧನ ವಿಧಿಸಿದೆ', 'ಆರೋಪಿ ಸಹೋದರರಿಗೆ ನ್ಯಾಯಾಲಯ ಹಡಿನಾಲ್ಕುದಿನ ನ್ಯಾಯಾಂಗ ಬಂಧನ ವಿದಿಸಿದೆ.'),
}


def verdict(script, names, edges, gem, whisper):
    return ear.combine([ear.judge(script, gem, names, edges), ear.judge(script, whisper, names, edges, lenient=True)], names)


class TheEarHoldsWhatWhisperLet(unittest.TestCase):
    def test_every_fault_in_the_published_reel_is_held(self):
        for label, (script, names, edges, gem, whisper) in PUBLISHED.items():
            with self.subTest(label):
                v = verdict(script, names, edges, gem, whisper)
                self.assertFalse(v['ok'], f'{label} passed: {v}')

    def test_the_town_that_was_never_said_is_named(self):
        script, names, edges, gem, whisper = PUBLISHED['story 2 headline — the town was never said']
        self.assertIn('ವಂಡ್ಸೆ', verdict(script, names, edges, gem, whisper)['lost'])

    def test_a_clipped_first_word_is_a_first_word_fault_so_the_cut_is_moved(self):
        script, names, edges, gem, whisper = PUBLISHED['story 2 card — the first word was cut into']
        v = verdict(script, names, edges, gem, whisper)
        self.assertTrue(v['first_lost'])
        self.assertIn('ಕಪ್ಪು', v['lost'] + v['changed'])

    def test_a_town_said_as_another_word_is_held_even_when_a_lenient_ear_called_it_right(self):
        # gemini-3.5-flash wrote ವಂದ್ಸೆ for what Whisper and gemini-3.8 heard as "ಒನ್ ಸೇ"; ವಂಡ್ಸೆ has a ಡ the first one smoothed over
        script, names = 'ಬೈಂದೂರು, ವಂಡ್ಸೆ, ಹೆಮ್ಮಾಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ', ('ಬೈಂದೂರು', 'ವಂಡ್ಸೆ', 'ಹೆಮ್ಮಾಡಿ')
        lenient = ear.judge(script, 'ಬೈಂದೂರು, ವಂದ್ಸೆ, ಹೆಮ್ಮಾಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ.', names)
        self.assertFalse(lenient['ok'])
        right_elsewhere = ear.judge(script, script, names)
        self.assertTrue(ear.combine([right_elsewhere, lenient], names)['ok'] is False)      # a name any ear fails is failed

    def test_the_clips_that_were_right_still_pass(self):
        for label, (script, names, edges, gem, whisper) in RIGHT.items():
            with self.subTest(label):
                v = verdict(script, names, edges, gem, whisper)
                self.assertTrue(v['ok'], f'{label} was held: {v}')

    def test_a_word_one_weak_ear_cannot_find_is_not_a_re_take(self):
        # each re-take is one of the day's ten voice requests: a noisy ear alone must not spend them
        script = 'ಕಂದಾಯ ವ್ಯಾಜ್ಯಗಳ ಇತ್ಯರ್ಥಕ್ಕೆ ಮೊದಲ ಆದ್ಯತೆ ನೀಡುವುದಾಗಿ ತಿಳಿಸಿದ್ದಾರೆ'
        good = ear.judge(script, script)
        noisy = ear.judge(script, 'ಕಂದಾಯ ಮೊದಲ ಆದ್ಯತೆ ನೀಡುವುದಾಗಿ ತಿಳಿಸಿದ್ದಾರೆ', lenient=False)
        self.assertFalse(noisy['ok'])
        self.assertTrue(ear.combine([good, noisy])['ok'])

    def test_a_headline_that_carries_the_cards_words_is_too_long(self):
        script = 'ಕುಂದಾಪುರ. ಮಹೇಶ್ ಪಿ ಎಸ್ ಅಧಿಕಾರ ಸ್ವೀಕಾರ'
        v = ear.judge(script, script + ' ಕಂದಾಯ ವ್ಯಾಜ್ಯಗಳ ಇತ್ಯರ್ಥಕ್ಕೆ ಮೊದಲ ಆದ್ಯತೆ ನೀಡುವುದಾಗಿ', ('ಕುಂದಾಪುರ',), True)
        self.assertTrue(v['extra'])
        self.assertFalse(v['ok'])

    def test_a_name_with_an_ending_on_it_is_still_the_name(self):
        self.assertTrue(ear._is_name('ಬೈಂದೂರಿನಲ್ಲಿ', ('ಬೈಂದೂರು',)))
        self.assertFalse(ear._is_name('ಬೆಂಗಳೂರು', ('ಬೈಂದೂರು',)))

    def test_nobody_listening_is_said_not_passed(self):
        with mock.patch.object(ear, 'hear', side_effect=ear.EarUnavailable('every listener is spent')):
            r = ear.listen('ಬೈಂದೂರು. ಆರಂಭ', '/nope.wav', ('ಬೈಂದೂರು',), True, whisper=None)
        self.assertIn('every listener is spent', r['unavailable'])
        with mock.patch.object(ear, 'hear', side_effect=ear.EarUnavailable('spent')):
            r = ear.listen('ವಂಡ್ಸೆ. ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು', '/nope.wav', ('ವಂಡ್ಸೆ',), True,
                           whisper='ಹಸಿಕಿಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು.')
        self.assertFalse(r['ok'])                       # Whisper alone is enough to hold a town that was not said
        self.assertEqual(r['ears'], ['whisper'])
        self.assertTrue(r['unavailable'])


class TheTextTheVoiceIsGiven(unittest.TestCase):
    def test_the_letters_of_a_name_run_together(self):
        # 2026-10-30: "ಪಿ.ಎಸ್:" kept its dot, was read as two sentences, and left 0.65 s of silence inside a man's name
        self.assertEqual(voice._spoken('ಕುಂದಾಪುರ. ಮಹೇಶ್ ಪಿ.ಎಸ್: ಎಸಿ ಅಧಿಕಾರ ಸ್ವೀಕಾರ'),
                         'ಕುಂದಾಪುರ. ಮಹೇಶ್ ಪಿ ಎಸ್, ಎಸಿ ಅಧಿಕಾರ ಸ್ವೀಕಾರ.')
        self.assertEqual(voice._spoken('ಮಹೇಶ್ ಪಿ.ಎಸ್ ಅಧಿಕಾರ'), 'ಮಹೇಶ್ ಪಿ ಎಸ್ ಅಧಿಕಾರ.')
        self.assertEqual(voice._spoken('ಕೆ.ಜೆ. ಜಾರ್ಜ್ ತಿಳಿಸಿದರು'), 'ಕೆ ಜೆ ಜಾರ್ಜ್ ತಿಳಿಸಿದರು.')

    def test_a_real_sentence_end_is_not_mistaken_for_an_initial(self):
        self.assertIn('ಇದೆ. ಎಚ್ಚರ', voice._spoken('ಮಳೆ ಇದೆ. ಎಚ್ಚರ'))
        self.assertIn('ನೀರು. ಬೆಲೆ', voice._spoken('ಇದು ನೀರು.ಬೆಲೆ ಏರಿಕೆ'))
        self.assertIn('ಡಾಕ್ಟರ್ ರಮೇಶ್', voice._spoken('ಡಾ. ರಮೇಶ್'))

    def test_a_headlines_colon_is_a_breath_not_the_end_of_a_sentence(self):
        said = voice._spoken('ಸುಜಿತ್ ಹತ್ಯೆ: ಆರೋಪಿಗಳು ಜೈಲಿಗೆ')
        self.assertEqual(said, 'ಸುಜಿತ್ ಹತ್ಯೆ, ಆರೋಪಿಗಳು ಜೈಲಿಗೆ.')
        self.assertNotIn(':', said)

    def test_a_clock_time_is_still_a_time(self):
        self.assertIn('9 ಗಂಟೆ 15 ನಿಮಿಷ', voice._spoken('ಬೆಳಿಗ್ಗೆ 9:15 ಕ್ಕೆ ಸಭೆ'))

    def test_the_ear_compares_with_what_was_meant_not_the_respelling(self):
        with mock.patch.object(voice, '_pronunciation_map', return_value={'ವಂಡ್ಸೆ': 'ವಂಡ್‌ಸೆ'}):
            self.assertIn('‌', RS.spoken('ವಂಡ್ಸೆ. ಹಸಿ ಕಸ'))
            self.assertNotIn('‌', RS.spoken('ವಂಡ್ಸೆ. ಹಸಿ ಕಸ', respell=False))

    def test_a_trial_spelling_lasts_one_take_and_is_then_forgotten(self):
        with voice.trial_respelling({'ಉಪ್ಪುಂದ': 'ಉಪ್ಪುನ್ದ'}):
            self.assertIn('ಉಪ್ಪುನ್ದ', RS.spoken('ಉಪ್ಪುಂದ. ಸುದ್ದಿ'))
        self.assertIn('ಉಪ್ಪುಂದ', RS.spoken('ಉಪ್ಪುಂದ. ಸುದ್ದಿ'))


class OtherSpellings(unittest.TestCase):
    def test_a_candidate_is_never_the_word_and_never_breaks_a_doubled_consonant(self):
        for w in ('ವಂಡ್ಸೆ', 'ಉಪ್ಪುಂದ', 'ಯಡ್ತರೆ', 'ಹೆಮ್ಮಾಡಿ', 'ಬೈಂದೂರು'):
            for c in lexicon.candidates(w):
                self.assertNotEqual(c, w)
        self.assertEqual(lexicon.candidates('ಹೆಮ್ಮಾಡಿ'), [])
        self.assertTrue(all('ಪ್ಪ' in c for c in lexicon.candidates('ಉಪ್ಪುಂದ')))
        self.assertIn('ಉಪ್ಪುನ್ದ', lexicon.candidates('ಉಪ್ಪುಂದ'))
        self.assertIn('ವಂಡ್‌ಸೆ', lexicon.candidates('ವಂಡ್ಸೆ'))


class SilenceInsideTheSpeech(unittest.TestCase):
    def wav(self, parts, sr=48000):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        rng = np.random.default_rng(7)
        x = np.concatenate([rng.normal(0, .2, int(sr * s)) if loud else np.zeros(int(sr * s)) for loud, s in parts])
        path = d / 'c.wav'
        sf.write(path, x, sr)
        return path

    def test_a_long_silence_inside_the_speech_is_shortened_to_a_breath(self):
        w = self.wav([(0, .3), (1, 1.0), (0, 1.0), (1, 1.0), (0, .3)])
        before = RS.voice.get_audio_duration(str(w))
        after = RS.tighten(w)
        self.assertAlmostEqual(before - after, 1.0 - Limits.ear_pause_max, delta=0.08)
        self.assertEqual([s for s in RS.silences(w) if s[1] - s[0] > Limits.ear_pause_max + 0.08], [])

    def test_a_natural_pause_and_the_edges_are_left_alone(self):
        w = self.wav([(0, .6), (1, 1.0), (0, .4), (1, 1.0), (0, .6)])
        before = RS.voice.get_audio_duration(str(w))
        self.assertAlmostEqual(RS.tighten(w), before, delta=0.02)

    def test_a_pair_can_be_cut_at_any_of_its_silences(self):
        w = self.wav([(1, 1.0), (0, .5), (1, 1.0), (0, .7), (1, 1.0), (0, .3), (1, 1.0)])
        cuts = RS.other_cuts(w, 3.2, near=0.2)
        self.assertEqual(len(cuts), 3)                               # every silence in the middle, nearest the first cut first
        self.assertAlmostEqual(cuts[0], 2.85, delta=0.1)
        self.assertAlmostEqual(cuts[-1], 1.25, delta=0.1)
        a, b = RS.cut_pair(w, w.with_name('h.wav'), w.with_name('b.wav'), 1.25)
        self.assertGreater(a, 0.8)
        self.assertAlmostEqual(float(w.with_suffix('.cut').read_text()), 1.25, delta=0.001)


class PuttingAClipRight(unittest.TestCase):
    """reel_listen.run with the listening and the voice replaced: the ORDER of the repairs, and what is kept."""

    COPIES = [dict(place_short='ವಂಡ್ಸೆ', say_head='ವಂಡ್ಸೆ. ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು', body='ಕಪ್ಪು ಸೈನಿಕ ನೊಣದ ಲಾರ್ವಾಗಳಿಂದ ಗೊಬ್ಬರ ತಯಾರಿಸಲಾಗುತ್ತಿದೆ.')]

    def ok(self, **kw):
        base = dict(ok=True, lost=[], changed=[], weak=[], extra=False, first_lost=False, last_lost=False, score=1.0,
                    heard='x', ears=['g'], heard_by={})
        return base | kw

    def bad(self, words, **kw):
        return self.ok(ok=False, lost=words, score=0.5, **kw)

    def run_with(self, script_of_verdicts):
        d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(d, ignore_errors=True))
        for k in ('intro', 'outro', 'h0', 'b0'):
            sf.write(d / f'{k}.wav', np.zeros(4800), 48000)
        sf.write(d / 'h0.pair.wav', np.zeros(48000), 48000)
        (d / 'h0.pair.cut').write_text('0.500')
        verdicts = iter(script_of_verdicts)
        asked = []

        def fake_hear(tmp, rs):
            return {r['key']: next(verdicts) for r in rs}

        def ask_pair(i, trial):
            asked.append(('pair', trial))
            return 1.0, 1.0

        def ask_single(key, trial):
            asked.append((key, trial))
            return 1.0
        durs = {}
        with mock.patch.object(reel_listen, 'hear_rows', fake_hear), \
                mock.patch.object(RS, 'other_cuts', return_value=[0.3, 0.7]), \
                mock.patch.object(RS, 'cut_pair', return_value=(1.0, 1.0)) as cut:
            rep = reel_listen.run(d, self.COPIES, 'ಹುಕ್', 'ಮುಗಿತಾಯ', durs, ask_pair, ask_single)
        return rep, asked, cut

    def test_a_clean_reel_asks_for_nothing(self):
        rep, asked, cut = self.run_with([self.ok()] * 4)           # the hook, headline, card, the follow card
        self.assertEqual(asked, [])
        cut.assert_not_called()
        self.assertTrue(all(v['ok'] for v in rep.values()))

    def test_a_cut_that_ate_a_word_is_moved_before_any_voice_request_is_spent(self):
        first = [self.ok(), self.ok(), self.bad(['ಕಪ್ಪು'], first_lost=True), self.ok()]
        again = [self.ok(), self.ok()]                              # after moving the cut: headline and card heard again
        rep, asked, cut = self.run_with(first + again)
        self.assertEqual(asked, [])
        cut.assert_called_once()
        self.assertLess(cut.call_args[0][3], 0.5)                   # a late cut moves EARLIER
        self.assertTrue(rep['b0']['ok'])

    def test_a_town_the_voice_will_not_say_is_asked_for_again_with_another_spelling_then_held(self):
        town = self.bad(['ವಂಡ್ಸೆ'])
        script = [self.ok(), town, self.ok(), self.ok()]            # first look
        script += [town, self.ok()] * (Limits.ear_takes - 1)        # every new take is no better
        rep, asked, cut = self.run_with(script)
        self.assertEqual(len(asked), Limits.ear_takes - 1)
        self.assertIn('ವಂಡ್ಸೆ', asked[0][1])                      # the failing word is respelled for the next take
        self.assertNotEqual(asked[0][1]['ವಂಡ್ಸೆ'], 'ವಂಡ್ಸೆ')
        self.assertNotEqual(asked[0][1]['ವಂಡ್ಸೆ'], asked[1][1]['ವಂಡ್ಸೆ'])    # …and differently each time
        self.assertFalse(rep['h0']['ok'])
        self.assertEqual(rep['h0']['takes'], Limits.ear_takes)
        self.assertEqual(rep['h0']['lost'], ['ವಂಡ್ಸೆ'])

    def test_a_town_that_is_said_on_the_second_take_is_kept(self):
        rep, asked, _ = self.run_with([self.ok(), self.bad(['ವಂಡ್ಸೆ']), self.ok(), self.ok(), self.ok(), self.ok()])
        self.assertEqual(len(asked), 1)
        self.assertTrue(rep['h0']['ok'])
        self.assertEqual(rep['h0']['takes'], 2)

    def test_the_hook_is_asked_for_again_too(self):
        rep, asked, _ = self.run_with([self.bad(['ವಂಡ್ಸೆ']), self.ok(), self.ok(), self.ok()] + [self.ok()] * 3)
        self.assertEqual(asked[0][0], 'intro')


class TheGateHoldsAMissingWord(unittest.TestCase):
    def codes(self, report):
        from brand.review import ReviewReport, _check_ear
        r = ReviewReport()
        _check_ear(report, r)
        return {(f.code, f.severity) for f in r.findings}, r

    def test_a_word_the_voice_did_not_say_holds_the_package(self):
        found, r = self.codes(dict(voice_engine='gemini', ear={
            'h1': dict(ok=False, lost=['ವಂಡ್ಸೆ'], changed=[], weak=[], extra=False, takes=3, heard='ಹಸಿ ಕಸ', ears=['g'])}))
        self.assertIn(('SND-09', 'fail'), found)
        self.assertIn('story 2 headline', r.findings[0].message)
        self.assertIn('ವಂಡ್ಸೆ', r.findings[0].message)

    def test_a_clean_listen_raises_nothing(self):
        found, _ = self.codes(dict(voice_engine='gemini', ear={'h0': dict(ok=True, lost=[], changed=[], weak=[], takes=1)}))
        self.assertEqual(found, set())

    def test_a_word_heard_but_not_cleanly_is_named_for_the_editors_one_listen(self):
        found, _ = self.codes(dict(voice_engine='gemini', ear={'b3': dict(ok=True, lost=[], changed=[], weak=['ನೀಡುವುದಾಗಿ'], takes=1)}))
        self.assertEqual(found, {('SND-09', 'warn')})

    def test_a_quiet_ear_is_reported_never_passed_silently(self):
        found, _ = self.codes(dict(voice_engine='gemini', ear={
            'h0': dict(ok=True, lost=[], changed=[], weak=[], takes=1, unavailable='every listener is spent for today')}))
        self.assertEqual(found, {('SND-09', 'warn')})

    def test_a_gemini_reel_with_no_record_of_being_heard_is_warned(self):
        found, _ = self.codes(dict(voice_engine='gemini'))
        self.assertEqual(found, {('SND-09', 'warn')})
        found, _ = self.codes(dict(voice_engine='google'))
        self.assertEqual(found, set())


if __name__ == '__main__':
    unittest.main()
