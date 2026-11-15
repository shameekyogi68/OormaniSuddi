"""D147 — a name the voice says wrong is held, not shipped; a town with no proven way of saying it is held.

Every transcript below is a real one, from the reels that went out on 2026-10-31 and 2026-11-01 (both posted, both
passed by the D146 ear). The owner heard both wrong:

  * 2026-11-01, story 5: ಬ್ರಹ್ಮಾವರ. The first take was heard by Whisper as "ಬ್ರಮ್ಹಾವರ" (the way it is said) and failed;
    the third take was handed the respelling "ಬರಹಮಾವರ" (brand/lexicon.py dropped the virama), the voice said
    "ಬರ-ಹ-ಮಾವರ", Whisper wrote "ಬರಹ ಮಾವರ", and the ear — which compared consonants only — called it ಬ್ರಹ್ಮಾವರ and kept it.
    The Gemini ear wrote "ಬ್ರಹ್ಮಾವರ" on all three takes: on a name it knows, it writes the name, not the sound.
  * 2026-10-31, story 1: only the most lenient Gemini ear was left (the strict ones were spent the afternoon before). It
    heard the headline end without its last word, ಗಾಯ — the cut had put it on the card, which began "ಗಾಯ ಗಾಯಗೊಂಡ…"
    (what the owner heard as a strange name). Whisper had looped ("…ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ…") and its noise
    "found" the word, and an ordinary word was failed only if EVERY ear failed it — so the loop outvoted the ear.

No network, no Chrome, no Gemini key.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brand import copy as C
from brand import ear, lexicon
from brand import town_clips as T
from brand.tokens import Limits

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'build').mkdir(exist_ok=True)

BRAHMAVARA = 'ಬ್ರಹ್ಮಾವರ ಕೊರಗ ಸಮುದಾಯದ ಗಾಯಕಿ ಅಶ್ವಿನಿ ನಿಧನ'
NAMES = ('ಬ್ರಹ್ಮಾವರ',)
H0_31 = 'ಕುಂದಾಪುರ ಟಿಪ್ಪರ್ ಡಿಕ್ಕಿ ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಗಾಯ'
H0_31_GEMINI = 'ಕುಂದಾಪುರ ಟಿಪ್ಪರ್ ಡಿಕ್ಕಿ ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ'                       # gemini-3.1-flash-lite, the only one left
H0_31_WHISPER = ('ಕುಂದಾಪುರ ಟಿಪ್ಪರ ಡಿಕ್ಕಿ ವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ '
                 'ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ಗೇವಿದ್ಯಾರ್ತಿಗಳಿ�')


class ANameIsHeardWithItsVowels(unittest.TestCase):
    """The consonant skeleton cannot tell ಬ್ರ from ಬರ. A name is held to its clusters."""

    def test_the_shipped_take_of_brahmavara_is_wrong(self):
        v = ear.judge(BRAHMAVARA, 'ಬರಹ ಮಾವರ ಕೊರಗ ಸಮುದಾಯದ ಗಾಯಕಿ ಅಶ್ವಿನಿ ನಿಧನ.', NAMES, edges=True, lenient=True)
        self.assertFalse(v['ok'])
        self.assertIn('ಬ್ರಹ್ಮಾವರ', v['lost'] + v['changed'])

    def test_brahmavara_said_the_way_people_say_it_is_right(self):
        for heard in ('ಬ್ರಮ್ಹಾವರ ಕೊರಗ ಸಮುದಾಯದ ಗಾಯಕಿ ಅಶ್ವಿನಿ ನಿಧನ', 'ಬ್ರಹ್ಮಾವರ ಕೊರಗ ಸಮುದಾಯದ ಗಾಯಕಿ ಅಶ್ವಿನಿ ನಿಧನ.'):
            for lenient in (True, False):
                self.assertTrue(ear.judge(BRAHMAVARA, heard, NAMES, edges=True, lenient=lenient)['ok'], (heard, lenient))

    def test_a_vowel_put_inside_a_towns_cluster_is_wrong(self):
        hook = 'ಕುಂದಾಪುರ ಮಂದಾರ್ತಿ ಕೋಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ'
        names = ('ಕುಂದಾಪುರ', 'ಮಂದಾರ್ತಿ', 'ಕೋಡಿ')
        v = ear.judge(hook, 'ಕುಂದಾಪುರ ಮಂದಾರತಿ ಕೂಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ.', names)     # flash-lite, 2026-10-31
        self.assertIn('ಮಂದಾರ್ತಿ', v['lost'] + v['changed'])
        ok = ear.judge(hook, 'ಕುಂದಾಪುರ ಮನ್ದಾರ್ತಿ ಕೋಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ.', names, lenient=True)
        self.assertTrue(ok['ok'])                                    # a nasal written out is the same sound

    def test_a_doubled_consonant_in_a_name_must_be_heard_doubled_by_a_strict_ear(self):
        v = ear.judge('ಹೆಮ್ಮಾಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ', 'ಹೇಮಾಡಿ ಸೇರಿದಂತೆ ಇಂದಿನ ಸುದ್ದಿ', ('ಹೆಮ್ಮಾಡಿ',))
        self.assertFalse(v['ok'])


class NoRespellingChangesTheSoundOfAName(unittest.TestCase):
    def test_the_respelling_that_shipped_is_never_offered(self):
        self.assertNotIn('ಬರಹಮಾವರ', lexicon.candidates('ಬ್ರಹ್ಮಾವರ'))

    def test_every_candidate_for_every_town_keeps_its_clusters(self):
        for town in C.PLACE_TAGS:
            for c in lexicon.candidates(town):
                self.assertEqual(ear.shape(c), ear.shape(town), (town, c))


class AWeakEarCannotOutvoteTheEar(unittest.TestCase):
    def test_a_looping_whisper_is_not_an_ear(self):
        self.assertTrue(ear.looping(H0_31_WHISPER))
        self.assertFalse(ear.looping('ಕುಂದಾಪುರ ಟಿಪ್ಪರ ಡಿಕ್ಕಿ ವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ಗಾಯಾ.'))
        self.assertFalse(ear.looping('ಕುಂದಾಪುರ ಹಾಗು ಬೈಂದೂರು ನಿಲ್ದಾಣಗಳಲ್ಲಿ ನಿಲ್ಲುಗಡೆ ಖಚಿತಪಟ್ಟಿದೆ.'))

    def test_the_headline_of_31_october_is_held_and_its_cut_is_moved(self):
        v = ear.combine([ear.judge(H0_31, H0_31_GEMINI, ('ಕುಂದಾಪುರ',), True),
                         ear.judge(H0_31, H0_31_WHISPER, ('ಕುಂದಾಪುರ',), True, lenient=True)], ('ಕುಂದಾಪುರ',))
        self.assertFalse(v['ok'])
        self.assertTrue(v['last_lost'])                             # the cut fell inside the headline's last word

    def test_whisper_alone_cannot_rescue_a_word_a_kannada_ear_heard_missing(self):
        script = 'ಕಾಮಗಾರಿ ತಕ್ಷಣ ನಿಲ್ಲಿಸಲು ಆಗ್ರಹಿಸಿ ದೂರು ಸಲ್ಲಿಸಲಾಗಿದೆ'
        gem = ear.judge(script, 'ಕಾಮಗಾರಿ ತಕ್ಷಣ ನಿಲ್ಲಿಸಲು ಆಗ್ರಹಿಸಿ ದೂರು', edges=True)
        wh = ear.judge(script, 'ಕಾಮಗಾರಿ ತಕ್ಷಣ ನಿಲ್ಲಿಸಲು ಆಗ್ರಹಿಸಿ ದೂರು ಸಲ್ಲಿಸಲಾಗಿದೆ.', edges=True, lenient=True)
        self.assertFalse(ear.combine([gem, wh])['ok'])

    def test_a_name_no_kannada_ear_heard_is_said_so(self):
        with mock.patch.object(ear, 'hear', side_effect=ear.EarUnavailable('every listener is spent for today')):
            v = ear.listen(BRAHMAVARA, ROOT / 'nothing.wav', NAMES, True, whisper='ಬ್ರಹ್ಮಾವರ ಕೊರಗ ಸಮುದಾಯದ ಗಾಯಕಿ ಅಶ್ವಿನಿ ನಿಧನ')
        self.assertEqual(v['names_unheard'], ['ಬ್ರಹ್ಮಾವರ'])


class TheGazetteer(unittest.TestCase):
    """Every town has a proven way of being said — a spelling heard right on its last Limits.town_verify_takes takes, or a
    recorded clip a person approved — or the reel is held."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(self.d, ignore_errors=True))
        reg = self.d / 'towns.json'
        reg.write_text('{}', encoding='utf-8')
        for p in (mock.patch.object(T, 'REGISTRY', reg), mock.patch.object(T, 'DIR', self.d / 'towns')):
            p.start()
            self.addCleanup(p.stop)

    def take(self, town, right, spelling=None):
        T.record(town, dict(spelling=spelling or T.spelling(town), right=right, heard_by={'g': 'x', 'whisper': 'y'},
                            source='test', on='2026-11-01'))

    def test_a_town_never_heard_is_not_left_to_the_voice(self):
        self.assertEqual(T.status('ಹೊಸೂರು'), 'unverified')

    def test_heard_right_on_every_one_of_the_last_takes_is_verified(self):
        for _ in range(Limits.town_verify_takes - 1):
            self.take('ಕೋಡಿ', True)
        self.assertEqual(T.status('ಕೋಡಿ'), 'unverified')
        self.take('ಕೋಡಿ', True)
        self.assertEqual(T.status('ಕೋಡಿ'), 'say')

    def test_one_wrong_take_undoes_it_until_it_is_proved_again(self):
        for _ in range(Limits.town_verify_takes):
            self.take('ಬ್ರಹ್ಮಾವರ', True)
        self.take('ಬ್ರಹ್ಮಾವರ', False)
        self.assertEqual(T.status('ಬ್ರಹ್ಮಾವರ'), 'unverified')

    def test_a_take_of_another_spelling_proves_nothing_about_this_one(self):
        for _ in range(Limits.town_verify_takes):
            self.take('ಬ್ರಹ್ಮಾವರ', True, spelling='ಬರಹಮಾವರ')
        self.assertEqual(T.status('ಬ್ರಹ್ಮಾವರ'), 'unverified')

    def test_the_gate_holds_a_town_with_no_proven_way_of_being_said(self):
        from brand.review import ReviewReport, _check_ear
        r = ReviewReport()
        _check_ear(dict(voice_engine='gemini', ear={'h4': dict(ok=True, lost=[], changed=[], weak=[], takes=1,
                                                              town_unverified='ಬ್ರಹ್ಮಾವರ')}), r)
        self.assertIn(('SND-09', 'fail'), {(f.code, f.severity) for f in r.findings})

    def test_the_gate_holds_a_name_no_kannada_ear_heard(self):
        from brand.review import ReviewReport, _check_ear
        r = ReviewReport()
        _check_ear(dict(voice_engine='gemini', ear={'h4': dict(ok=True, lost=[], changed=[], weak=[], takes=1,
                                                              names_unheard=['ಬ್ರಹ್ಮಾವರ'], unavailable='spent')}), r)
        self.assertIn(('SND-09', 'fail'), {(f.code, f.severity) for f in r.findings})

    def test_a_name_heard_but_not_cleanly_fails(self):
        from brand.review import ReviewReport, _check_ear
        r = ReviewReport()
        _check_ear(dict(voice_engine='gemini', ear={'h4': dict(ok=True, lost=[], changed=[], weak=['ಬ್ರಹ್ಮಾವರ'], takes=1,
                                                              names=['ಬ್ರಹ್ಮಾವರ'])}), r)
        self.assertIn(('SND-09', 'fail'), {(f.code, f.severity) for f in r.findings})


class TheRenderProvesOrHolds(TheGazetteer):
    """reel_listen.vet_towns with the voice and the ears replaced."""

    COPIES = [dict(place_short='ಬ್ರಹ್ಮಾವರ', say_head='ಬ್ರಹ್ಮಾವರ. ಗಾಯಕಿ ಅಶ್ವಿನಿ ನಿಧನ', body='ಚಿಕಿತ್ಸೆ ಫಲಿಸದೆ ನಿಧನರಾಗಿದ್ದಾರೆ.',
                   voice_town='unverified')]
    RIGHT = {'gemini-3-flash-preview': 'ಬ್ರಹ್ಮಾವರ. ಇಂದಿನ ಸುದ್ದಿ.', 'whisper': 'ಬ್ರಮ್ಹಾವರ ಇಂದಿನ ಸುದ್ದಿ.'}
    WRONG = {'gemini-3-flash-preview': 'ಬ್ರಹ್ಮಾವರ. ಇಂದಿನ ಸುದ್ದಿ.', 'whisper': 'ಬರಹ ಮಾವರ ಇಂದಿನ ಸುದ್ದಿ.'}

    def vet(self, probes, log):
        from brand import reel_listen
        asked = []
        heard = iter(probes)
        report = {'intro': {}, 'h0': {}, 'b0': {}, 'outro': {}}
        with mock.patch.object(reel_listen, 'hear_rows', lambda tmp, rs: {r['key']: dict(heard_by=next(heard)) for r in rs}):
            out = reel_listen.vet_towns(self.d, self.COPIES, 'ಇಂದಿನ ಸುದ್ದಿ, ಕರಾವಳಿ.', report, log,
                                        lambda text, key: asked.append(text) or 1.0, source='reel test')
        return out, report, asked

    def test_the_take_that_shipped_on_1_november_holds_the_reel_unless_probes_prove_it(self):
        log = [('ಬ್ರಹ್ಮಾವರ', T.spelling('ಬ್ರಹ್ಮಾವರ'), self.WRONG, 'story 1 headline')]
        out, report, asked = self.vet([self.WRONG, self.RIGHT], log)
        self.assertEqual(len(asked), Limits.town_verify_takes)          # never more probes than that
        self.assertEqual(out['ಬ್ರಹ್ಮಾವರ'], 'unverified')
        self.assertEqual(report['h0']['town_unverified'], 'ಬ್ರಹ್ಮಾವರ')

    def test_a_town_heard_right_on_its_probes_is_proved_and_kept(self):
        out, report, asked = self.vet([self.RIGHT, self.RIGHT], [('ಬ್ರಹ್ಮಾವರ', T.spelling('ಬ್ರಹ್ಮಾವರ'), self.RIGHT, 'story 1 headline')])
        self.assertEqual(out['ಬ್ರಹ್ಮಾವರ'], 'say')
        self.assertEqual(len(asked), 1)                                 # the reel's own take counted as the first
        self.assertNotIn('town_unverified', report['h0'])

    def test_no_probe_is_spent_while_nobody_who_can_tell_is_listening(self):
        out, report, asked = self.vet([{'whisper': 'ಬ್ರಹ್ಮಾವರ ಇಂದಿನ ಸುದ್ದಿ'}] * 3, [])
        self.assertEqual(len(asked), 1)
        self.assertEqual(report['h0']['town_unverified'], 'ಬ್ರಹ್ಮಾವರ')


class TheRealGazetteer(unittest.TestCase):
    def test_every_town_we_cover_is_in_it(self):
        reg = T.registry()
        missing = [t for t in C.PLACE_TAGS if t not in reg]
        self.assertEqual(missing, [])

    def test_brahmavara_is_not_proved_by_the_take_that_shipped(self):
        takes = (T.registry().get('ಬ್ರಹ್ಮಾವರ') or {}).get('takes') or []
        shipped = [t for t in takes if t.get('source', '').startswith('reel 2026-11-01')]
        if shipped:
            self.assertTrue(all(not t['right'] for t in shipped))


if __name__ == '__main__':
    unittest.main()
