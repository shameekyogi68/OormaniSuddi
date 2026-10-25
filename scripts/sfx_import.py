#!/usr/bin/env python3
"""
Bring licensed sound effects into the ಸುದ್ದಿ ಸಾರ reel, made to sit where the house set sat (D135).

    python3 scripts/sfx_import.py            # assets/sfx/incoming/* → assets/sfx/pro/<slot>.wav (+ a report)

The house set (brand/sfx.py, synthesised, licence `own`) stays as it is and stays the fallback. Each licensed file
is fitted to its slot so the mix's timing and balance — tuned against the house set — still hold:

  * cut to the sound itself (leading/trailing silence off, a 15 ms fade so nothing clicks);
  * never cut into: a whoosh keeps its rise and the bells their first strike. Instead the mix places each sound so
    its loudest instant falls where the house sound's did (saara_reel._mix), and a whoosh still peaks as the
    picture wipes and a tick still lands on its row;
  * matched in loudness (EBU R128 momentary max, K-weighted — how loud it SOUNDS, not its peak) to the house sound
    it replaces, so the volumes in saara_reel._mix still mean what they meant;
  * high-passed off the voice's low end (not the opening hit, whose weight is the point) and peak-limited.

The files are third-party: Mixkit's and Pixabay's licences allow them in our videos but NOT redistributed as files,
so assets/sfx/incoming/ and assets/sfx/pro/ are git-ignored (the repo is public) and carried by scripts/backup.sh.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
INCOMING, PRO, HOUSE = ROOT / 'assets/sfx/incoming', ROOT / 'assets/sfx/pro', ROOT / 'assets/sfx'
SR = 48000

MIXKIT = 'https://mixkit.co/license/#sfxFree'
PIXABAY = 'https://pixabay.com/service/license-summary/'

# slot → (file, licence page, source page, why this one)
CHOICE = {
    'whoosh': ('mixkit-fast-whoosh-transition-1490.wav', MIXKIT, 'https://mixkit.co/free-sound-effects/whoosh/',
               'airy, soft (−25 dB RMS), centred 4.5 kHz — above the voice; the swipe-zoom was harder and lower'),
    'tick':   ('mixkit-modern-technology-select-3124.wav', MIXKIT, 'https://mixkit.co/free-sound-effects/click/',
               'a 30 ms bright tick — six of them run under the opening line, so it has to be tiny'),
    'pop':    ('mixkit-dry-pop-up-notification-alert-2356.wav', MIXKIT, 'https://mixkit.co/free-sound-effects/pop/',
               'dry, 3.4 kHz; the bubble pop (8 kHz) read as a cartoon'),
    'press':  ('mixkit-select-click-1109.wav', MIXKIT, 'https://mixkit.co/free-sound-effects/click/',
               'a crisp two-stage click for the follow button'),
    'outro':  ('mixkit-happy-bells-notification-937.wav', MIXKIT, 'https://mixkit.co/free-sound-effects/notification/',
               'warm bells for the follow card; the only outro candidate'),
    'open':   ('soundreality-kick-drum-acoustic-sample-455285.mp3', PIXABAY,
               'https://pixabay.com/sound-effects/kick-drum-acoustic-sample-455285/',
               'a short acoustic kick: weight on frame 0 without a cinematic boom; the floor tom rang on'),
}
HIGHPASS = {'open': 30}                      # every other slot: 110 Hz, off the voice's chest


def load(path: Path) -> np.ndarray:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def momentary_max(x: np.ndarray) -> float:
    pad = np.concatenate([np.zeros((SR // 2, 2)), x, np.zeros((SR // 2, 2))])
    tmp = ROOT / 'build' / '_sfx_m.wav'
    tmp.parent.mkdir(exist_ok=True)
    sf.write(tmp, pad, SR)
    err = subprocess.run(['ffmpeg', '-nostats', '-i', str(tmp), '-af', 'ebur128', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    vals = [float(v) for v in re.findall(r' M:\s*(-?[\d.]+)', err)]
    return max(vals) if vals else -70.0


def peak_time(x: np.ndarray) -> float:
    env = np.abs(x).max(axis=1)
    hop = int(0.005 * SR)
    sm = np.convolve(env, np.ones(hop) / hop, mode='same')
    return float(np.argmax(sm)) / SR


def fit(slot: str, src: Path) -> tuple[np.ndarray, dict]:
    house = load(HOUSE / f'{slot}.wav')
    x = load(src)
    env = np.abs(x).max(axis=1)
    on = np.where(env > env.max() * 10 ** (-50 / 20))[0]
    x = x[on[0]:on[-1] + 1]
    hp = HIGHPASS.get(slot, 110)
    tmp_in, tmp_out = ROOT / 'build' / '_sfx_in.wav', ROOT / 'build' / '_sfx_out.wav'
    sf.write(tmp_in, x, SR)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(tmp_in), '-af', f'highpass=f={hp}:p=2', str(tmp_out)], check=True)
    x, _ = sf.read(tmp_out)
    n = int(0.015 * SR)
    x[-n:] *= np.linspace(1, 0, n)[:, None]
    # as loud as the house sound it replaces, as heard
    gain = momentary_max(house) - momentary_max(x)
    x = x * 10 ** (gain / 20)
    pk = np.abs(x).max()
    if pk > 10 ** (-1 / 20):
        x *= 10 ** (-1 / 20) / pk
    return x, dict(seconds=round(len(x) / SR, 3), gain_db=round(gain, 1), peak_at_s=round(peak_time(x), 3),
                  house_peak_at_s=round(peak_time(house), 3), highpass_hz=hp)


def main() -> int:
    PRO.mkdir(parents=True, exist_ok=True)
    report = {}
    for slot, (name, licence, page, why) in CHOICE.items():
        src = INCOMING / name
        if not src.exists():
            print(f'✗ {slot}: {name} is not in {INCOMING.relative_to(ROOT)}', file=sys.stderr)
            return 1
        x, info = fit(slot, src)
        sf.write(PRO / f'{slot}.wav', x.astype(np.float32), SR, subtype='PCM_24')
        report[slot] = dict(source=name, licence_url=licence, source_url=page, why=why, **info)
        print(f'✓ {slot:<7} ← {name}  {info}')
    (PRO / 'IMPORT.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
