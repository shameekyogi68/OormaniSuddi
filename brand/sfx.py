"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the house sound effects, made here and owned outright.
======================================================================
A sound effect gets a Content ID claim exactly like a music bed does, and
D74 already found one live exposure on music. The engine's reels were
reaching first for `sfx/pro_*.wav`, which have no licence record anywhere —
they sit beside a deleted `sfx/downloaded/` folder of numbered third-party
files, and nothing says which of those they were cut from. A hit nobody can
account for is a claim nobody can answer.

So the set is synthesised here, from a fixed seed: the same bytes every time,
licence `own`, registered in `assets/LICENCES.json` with `kind: sfx`, and
nothing outside the register is ever played.

    python3 -m brand.sfx          # (re)build assets/sfx/*.wav

What each one is FOR, which is most of the design:

  whoosh  0.42s  the picture wipe. Air, moving left to right with the wipe,
                 centred on it. Band-limited so it never fights the voice.
  tick    0.14s  a headline landing. A dry, woody tock — felt more than
                 heard, under the anchor's first syllable.
  open    0.90s  frame 0. A low, short news hit; the voice starts on top of
                 it, so it is mostly sub and body with almost no top end.
  outro   1.60s  the follow card. A warm three-note ident over a soft hit —
                 the one moment the reel is allowed to be musical.
"""
from __future__ import annotations

import os
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'sfx')
SR = 48000
SEED = 20260918


def _t(dur: float) -> np.ndarray:
    return np.arange(int(SR * dur)) / SR


def _onepole_lp(x: np.ndarray, cutoff) -> np.ndarray:
    """One-pole low-pass; `cutoff` may be a per-sample array (Hz)."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
    a = np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def _bandpass(x, lo, hi):
    return _onepole_lp(x, hi) - _onepole_lp(_onepole_lp(x, hi), lo)


def _room(x: np.ndarray, seconds: float = 0.9, mix: float = 0.18,
          rng=None) -> np.ndarray:
    """A small, dark room: convolution with decaying filtered noise."""
    rng = rng or np.random.default_rng(SEED + 7)
    n = int(SR * seconds)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * seconds / 5.5))
    ir = _onepole_lp(ir, 2600.0)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    wet = np.convolve(x, ir)                     # len(x) + n - 1
    dry = np.concatenate([x, np.zeros(n - 1)])
    return dry * (1 - mix) + wet * mix


def _fade(x: np.ndarray, attack: float = 0.004, release: float = 0.03):
    a, r = int(SR * attack), int(SR * release)
    env = np.ones(len(x))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return x * env


def whoosh() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED + 1)
    dur = 0.42
    t = _t(dur)
    u = t / dur
    env = np.sin(np.pi * u) ** 2.2
    noise = rng.standard_normal(len(t))
    # The sweep rises into the centre of the wipe and falls away after it.
    hi = 700 + 5200 * np.sin(np.pi * u) ** 1.5
    air = _bandpass(noise, 260.0, hi) * env
    body = np.sin(2 * np.pi * (90 + 60 * u) * t) * env * 0.18
    mono = air + body
    pan = np.clip(u * 1.1 - 0.05, 0, 1)            # left → right, with the wipe
    return _fade(mono * np.cos(pan * np.pi / 2), 0.01, 0.06), \
        _fade(mono * np.sin(pan * np.pi / 2), 0.01, 0.06)


def tick() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED + 2)
    t = _t(0.14)
    tock = (np.sin(2 * np.pi * 740 * t) * np.exp(-t * 55)
            + np.sin(2 * np.pi * 1110 * t) * np.exp(-t * 80) * 0.45)
    click = _onepole_lp(rng.standard_normal(len(t)), 3800.0) * np.exp(-t * 400) * 0.6
    x = _fade(tock + click, 0.0005, 0.02)
    return x, x


def open_hit() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED + 3)
    t = _t(0.9)
    f = 95 * np.exp(-t * 2.4) + 42                  # a drop, not a boom
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.2)
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 16) * 0.35
    snap = _onepole_lp(rng.standard_normal(len(t)), 1800.0) * np.exp(-t * 60) * 0.5
    x = _room(sub + body + snap, 0.7, 0.14)[:len(t) + int(SR * 0.2)]
    return _fade(x, 0.002, 0.2), _fade(x, 0.002, 0.2)


def outro() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED + 4)
    t = _t(1.6)
    notes = (440.0, 554.37, 659.25)                  # A major, gold not tinsel
    tone = np.zeros(len(t))
    for k, f in enumerate(notes):
        start = int(SR * 0.05 * k)
        tt = t[:len(t) - start]
        v = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt))
        v *= (1 - np.exp(-tt * 40)) * np.exp(-tt * 2.1)
        tone[start:] += v * (0.34 - 0.05 * k)
    thump = np.sin(2 * np.pi * (70 * np.exp(-t * 3) + 40) * t) * np.exp(-t * 5) * 0.5
    air = _onepole_lp(rng.standard_normal(len(t)), 2400.0) * np.exp(-t * 30) * 0.2
    x = _room(tone + thump + air, 1.2, 0.22)[:len(t) + int(SR * 0.3)]
    # A touch of width on the notes only.
    d = int(SR * 0.009)
    right = np.concatenate([np.zeros(d), x[:-d]])
    return _fade(x, 0.003, 0.35), _fade(0.8 * x + 0.2 * right, 0.003, 0.35)


SET = {'whoosh': whoosh, 'tick': tick, 'open': open_hit, 'outro': outro}


def _write(path: str, left: np.ndarray, right: np.ndarray, peak_db: float):
    st = np.stack([left, right], axis=1)
    st = st / (np.max(np.abs(st)) + 1e-9) * (10 ** (peak_db / 20))
    pcm = (st * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def path(name: str) -> str:
    return os.path.join(OUT, f'{name}.wav')


def build() -> list[str]:
    os.makedirs(OUT, exist_ok=True)
    made = []
    for name, fn in SET.items():
        left, right = fn()
        _write(path(name), left, right, -3.0)
        made.append(path(name))
    return made


if __name__ == '__main__':
    for p in build():
        print('  ✓', os.path.relpath(p, ROOT))
