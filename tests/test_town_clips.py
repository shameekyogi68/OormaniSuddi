"""D146 — a town the voice cannot say is never left to it, and is never published wrong.

Measured 2026-10-30: ವಂಡ್ಸೆ and ಯಡ್ತರೆ could not be got out of Gemini Kore in any spelling, in a list, in a phrase or after a
carrier word; a spelling heard right once was wrong on the next take. So such a town is a recorded clip a person has
approved — or the reel is held.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import soundfile as sf

from brand import saara_reel as R
from brand import town_clips as T

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'build').mkdir(exist_ok=True)


class Registry(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=ROOT / 'build'))
        self.addCleanup(lambda: __import__('shutil').rmtree(self.d, ignore_errors=True))
        reg = self.d / 'towns.json'
        reg.write_text(json.dumps({'ವಂಡ್ಸೆ': dict(say_inline=False, why='measured', clip=None, approved_by='', approved_on='')},
                                  ensure_ascii=False), encoding='utf-8')
        for p in (mock.patch.object(T, 'REGISTRY', reg), mock.patch.object(T, 'DIR', self.d / 'towns')):
            p.start()
            self.addCleanup(p.stop)

    def recording(self, seconds=0.6):
        rng = np.random.default_rng(1)
        x = np.concatenate([np.zeros(24000), rng.normal(0, .2, int(24000 * seconds)), np.zeros(24000)])
        path = self.d / 'rec.wav'
        sf.write(path, x, 24000)
        return path

    def test_a_flagged_town_with_no_clip_is_missing_and_a_free_one_is_not_left_to_the_voice_until_proved(self):
        self.assertEqual(T.status('ವಂಡ್ಸೆ'), 'missing')
        self.assertEqual(T.status('ಬೈಂದೂರು'), 'unverified')               # D147: never heard yet, so not proved
        self.assertEqual(T.unsayable(), {'ವಂಡ್ಸೆ'})

    def test_a_recording_is_not_used_until_a_person_approves_it(self):
        out = T.add('ವಂಡ್ಸೆ', self.recording(), 'recorded by the editor')
        self.assertTrue(out.exists())
        self.assertEqual(T.status('ವಂಡ್ಸೆ'), 'missing')                  # kept, not yet approved
        T.approve('ವಂಡ್ಸೆ', 'Gautam Paduvari')
        self.assertEqual(T.status('ವಂಡ್ಸೆ'), 'clip')
        self.assertEqual(T.clip_for('ವಂಡ್ಸೆ'), out)

    def test_approval_needs_a_name_and_a_clip(self):
        with self.assertRaises(ValueError):
            T.add('ವಂಡ್ಸೆ', self.recording(), 'x')
            T.approve('ವಂಡ್ಸೆ', '  ')
        with self.assertRaises(KeyError):
            T.approve('ಯಡ್ತರೆ', 'someone')

    def test_the_clip_is_trimmed_to_its_sound_and_spliced_in_front_of_the_headline(self):
        out = T.add('ವಂಡ್ಸೆ', self.recording(0.6), 'x')
        town, sr = sf.read(str(out))
        self.assertLess(len(town) / sr, 1.2)                              # the 0.5 s of silence either side is gone
        rest = self.d / 'rest.wav'
        sf.write(rest, np.random.default_rng(2).normal(0, .2, sr * 2), sr)
        seconds = T.splice(out, rest, pause=0.36)
        self.assertAlmostEqual(seconds, len(town) / sr + 0.36 + 2.0, delta=0.02)

    def test_the_headline_is_asked_of_the_voice_without_its_town(self):
        self.assertEqual(T.without_town('ವಂಡ್ಸೆ. ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು', 'ವಂಡ್ಸೆ'), 'ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ ಬಂಗಾರದ ಹುಳು')
        self.assertEqual(T.without_town('ಬೈಂದೂರು. ವಂದೇ ಭಾರತ್', 'ವಂಡ್ಸೆ'), 'ಬೈಂದೂರು. ವಂದೇ ಭಾರತ್')

    def test_the_opening_never_names_a_town_the_voice_cannot_say(self):
        copies = [dict(place_short=t) for t in ('ಬೈಂದೂರು', 'ವಂಡ್ಸೆ', 'ಹೆಮ್ಮಾಡಿ')]
        hook = R._hook_text(copies)
        self.assertNotIn('ವಂಡ್ಸೆ', hook)
        self.assertIn('ಸೇರಿದಂತೆ', hook)                                  # "…among others": it does not claim to be the whole list
        self.assertIn('ಬೈಂದೂರು', hook)
        self.assertEqual(R._hook_text([dict(place_short='ವಂಡ್ಸೆ')]), 'ಇಂದಿನ ಸುದ್ದಿ, ಕರಾವಳಿ.')

    def test_the_real_registry_flags_what_was_measured(self):
        real = json.loads((ROOT / 'assets/voice/towns.json').read_text(encoding='utf-8'))
        self.assertIn('ವಂಡ್ಸೆ', real)
        self.assertIn('ಯಡ್ತರೆ', real)
        self.assertIsNot(real.get('ಉಪ್ಪುಂದ', {}).get('say_inline'), False)    # said right in every phrase tested
        for v in real.values():
            if v.get('say_inline') is False:
                self.assertIn('Measured', v['why'])                      # a flag is evidence, never a hunch


if __name__ == '__main__':
    unittest.main()
