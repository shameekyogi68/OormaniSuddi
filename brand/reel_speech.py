"""
ಊರ್ಮನಿ ಸುದ್ದಿ — what the ಸುದ್ದಿ ಸಾರ reel says, and where each word falls (D132)
=============================================================================
The reel is cut from its own voice, so everything here has to be right on a
day nobody has seen yet:

  spoken()      the house normaliser (brand/voice.py) first, then every figure
                that is left becomes Kannada words — "33ನೇ" is read as
                ಮೂವತ್ತಮೂರನೇ whatever the engine would have made of "33".
  lint()        what could still be misread, said before the render, never
                guessed at after it.
  clip()        one clip, in ONE voice. The house chain falls back to another
                engine when Google fails, and a reel whose voice changes
                between stories is worse than no reel; so Google is asked
                three times, and then the render stops and says why.
  word_times()  where each word falls inside its clip, measured from the audio.
                Whisper cannot read Kannada (2026-10-23: a clean clip came back
                as noise), so: the real pauses are matched to the punctuation
                only where they fall near where the words say they should, the
                words between share the voiced time by akshara, and each
                boundary snaps to the dip in the voice. If anything looks wrong
                it falls back to an even split and says so.
"""
from __future__ import annotations

import contextlib
import re
import subprocess
import time
from pathlib import Path

from . import voice
from .tokens import Motion as M


class ReelError(RuntimeError):
    """The reel cannot be made right. The caller falls back, and says so."""


# ── figures, as words ────────────────────────────────────────────────────
_ONES = ('ಸೊನ್ನೆ', 'ಒಂದು', 'ಎರಡು', 'ಮೂರು', 'ನಾಲ್ಕು', 'ಐದು', 'ಆರು', 'ಏಳು', 'ಎಂಟು', 'ಒಂಬತ್ತು')
_TEEN = {10: 'ಹತ್ತು', 11: 'ಹನ್ನೊಂದು', 12: 'ಹನ್ನೆರಡು', 13: 'ಹದಿಮೂರು', 14: 'ಹದಿನಾಲ್ಕು',
         15: 'ಹದಿನೈದು', 16: 'ಹದಿನಾರು', 17: 'ಹದಿನೇಳು', 18: 'ಹದಿನೆಂಟು', 19: 'ಹತ್ತೊಂಬತ್ತು'}
_TENS = {2: 'ಇಪ್ಪತ್ತು', 3: 'ಮೂವತ್ತು', 4: 'ನಲವತ್ತು', 5: 'ಐವತ್ತು', 6: 'ಅರವತ್ತು',
         7: 'ಎಪ್ಪತ್ತು', 8: 'ಎಂಬತ್ತು', 9: 'ತೊಂಬತ್ತು'}
_HUND = {1: 'ನೂರು', 2: 'ಇನ್ನೂರು', 3: 'ಮುನ್ನೂರು', 4: 'ನಾನೂರು', 5: 'ಐನೂರು',
         6: 'ಆರುನೂರು', 7: 'ಏಳುನೂರು', 8: 'ಎಂಟುನೂರು', 9: 'ಒಂಬೈನೂರು'}
# A tens word loses its final ು and takes the unit: ಇಪ್ಪತ್ತ + ಒಂದು → ಇಪ್ಪತ್ತೊಂದು.
_MATRA = {'ಒ': 'ೊ', 'ಎ': 'ೆ', 'ಐ': 'ೈ', 'ಆ': 'ಾ', 'ಏ': 'ೇ'}
MAX_NUMBER = 99999                       # past this the voice's own reading is left to it


def number_words(n: int) -> str | None:
    """A whole number as Kannada words, 0–99 999; None beyond."""
    if n < 0 or n > MAX_NUMBER:
        return None
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEEN[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        if not unit:
            return _TENS[tens]
        stem, u = _TENS[tens][:-1], _ONES[unit]
        return stem + _MATRA[u[0]] + u[1:] if u[0] in _MATRA else stem + u
    if n < 1000:
        h, r = divmod(n, 100)
        return _HUND[h] if not r else _HUND[h][:-1] + ' ' + number_words(r)
    t, r = divmod(n, 1000)
    head = number_words(t) + ' ಸಾವಿರ'
    return head if not r else head + 'ದ ' + number_words(r)


# What may follow a figure directly. Each begins with a consonant, so the number
# word's final ು is dropped before it: ಐದು + ಕ್ಕೆ → ಐದಕ್ಕೆ, ಮೂವತ್ತಮೂರು + ನೇ → ಮೂವತ್ತಮೂರನೇ.
_SUFFIXES = sorted(['ನೇ', 'ನೆಯ', 'ರಂದು', 'ರಲ್ಲಿ', 'ರಿಂದ', 'ರವರೆಗೆ', 'ರೊಳಗೆ', 'ರ', 'ಕ್ಕೆ',
                    'ಕ್ಕೂ', 'ಕ್ಕಿಂತ', 'ಕ್ಕಾಗಿ', 'ರಷ್ಟು'], key=len, reverse=True)
_KN = 'ಀ-೿'
_WITH_SUFFIX = re.compile(r'(?<![\d.])(\d{1,5})(' + '|'.join(_SUFFIXES) + r')(?![' + _KN + r'\d])')
_PLAIN = re.compile(r'(?<![\d.])(\d{1,5})(?!\d)')


def _attach(word: str, suffix: str) -> str:
    return (word[:-1] if word.endswith('ು') else word) + suffix


def numbers_to_words(text: str) -> str:
    def with_suffix(m):
        w = number_words(int(m.group(1)))
        return m.group(0) if w is None else _attach(w, m.group(2))

    def plain(m):
        w = number_words(int(m.group(1)))
        return m.group(0) if w is None else w
    text = _WITH_SUFFIX.sub(with_suffix, text)
    # a figure with some other Kannada word stuck to it ("5ಜನ") is read as two words
    text = re.sub(r'(\d)(?=[' + _KN + r'])', r'\1 ', text)
    return _PLAIN.sub(plain, text)


def spoken(text: str) -> str:
    """Exactly what the voice is given: the house normaliser, then figures as words."""
    t = numbers_to_words(voice._spoken(text))
    return re.sub(r'\s+', ' ', t).strip()


_HAZARD = re.compile(r'[A-Za-z]+|\d+|[%₹@#&/+=*<>_|\\~^]')


def lint(text: str) -> list[str]:
    """What in `text` the voice may still misread, after normalising it. Latin
    letters (an English word, an initialism) and figures the words could not
    carry. Respell a name in assets/pronunciation.json and it is fixed for
    every format."""
    return sorted(set(_HAZARD.findall(spoken(text))))


# ── one clip, one voice ──────────────────────────────────────────────────
TRIM = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,'
        'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,'
        f'atempo={M.saara_reel_tempo}')


@contextlib.contextmanager
def _one_engine(engine: str):
    """voice._synth_one falls back google → edge → gemini; a reel must not."""
    old = voice.FALLBACK_ORDER.get(engine)
    voice.FALLBACK_ORDER[engine] = (engine,)
    try:
        yield
    finally:
        if old is None:
            voice.FALLBACK_ORDER.pop(engine, None)
        else:
            voice.FALLBACK_ORDER[engine] = old


def clip(text: str, wav: Path, engine: str = 'google', tries: int = 3) -> float:
    """Synthesise `text` as `wav` (trimmed, 48k mono). Returns its seconds."""
    raw = wav.with_suffix('.mp3')
    said = spoken(text)
    last: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            with _one_engine(engine):
                voice._synth_one(said, str(raw), engine, None, None)
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(raw), '-af', TRIM,
                            '-ar', '48000', '-ac', '1', str(wav)], check=True)
            d = voice.get_audio_duration(str(wav))
            floor = 0.35 + 0.03 * len(said)
            if d < min(floor, 1.2):
                raise ReelError(f'the clip for {said[:30]!r} is only {d:.2f}s — the voice returned silence')
            return round(d, 3)
        except Exception as e:      # noqa: BLE001 — every engine fails its own way
            last = e
            raw.unlink(missing_ok=True)
            wav.unlink(missing_ok=True)
            # a cached bad clip would be handed back every time
            with contextlib.suppress(Exception):
                import os
                key = voice._cache_key(said, engine, None)
                cached = os.path.join(voice.TTS_CACHE, f'{key}.mp3')
                if os.path.exists(cached) and os.path.getsize(cached) <= 512:
                    os.remove(cached)
            time.sleep(1.5 * attempt)
    raise ReelError(f'the {engine} voice failed {tries} times for {said[:40]!r}: {last}')


# ── where each word falls in its clip ────────────────────────────────────
_LONG = set('ಾೀೂೇೋೈೌ')


def syllables(word: str) -> float:
    """Aksharas, not code points: a conjunct is one beat, a figure is a word."""
    n, after_virama = 0.0, False
    for ch in word:
        o = ord(ch)
        if 0x0C95 <= o <= 0x0CB9 or o == 0x0CDE:
            if not after_virama:
                n += 1
            after_virama = False
        elif 0x0C85 <= o <= 0x0C94:
            n += 1
            after_virama = False
        elif o == 0x0CCD:
            after_virama = True
        elif ch.isdigit():
            n += 2.2
            after_virama = False
        else:
            if ch in _LONG:
                n += 0.25
            elif o in (0x0C82, 0x0C83):
                n += 0.3
            after_virama = False
    if word.rstrip('.,;:!?').endswith('್'):
        n += 0.4                           # a closing consonant still sounds
    return max(n, 1.0)


def weight(word: str) -> float:
    """How long a word on the screen takes to SAY. The screen shows "22ರಂದು" and
    "ಎಚ್.ಸಿ."; the voice says ಇಪ್ಪತ್ತೆರಡರಂದು and ಎಚ್ ಸಿ — so the beat is weighed on
    what is spoken, not on what is printed."""
    return max(1.0, sum(syllables(t) for t in spoken(word).split()))


def _even(words: list[str], start: float, end: float) -> list[list[float]]:
    wts = [weight(w) for w in words]
    tot, acc, out = sum(wts), 0.0, []
    for w in wts:
        a = start + (end - start) * acc / tot
        acc += w
        out.append([round(a, 3), round(start + (end - start) * acc / tot, 3)])
    return out


def word_times(wav: Path, text: str) -> tuple[list[list[float]], str]:
    """(times, how): `how` is 'measured' or 'even' when the audio could not be trusted."""
    import numpy as np
    import soundfile as sf
    words = text.split()
    x, sr = sf.read(str(wav))
    if x.ndim > 1:
        x = x.mean(axis=1)
    total_s = len(x) / sr
    if not words:
        return [], 'measured'
    hop = int(sr * 0.01)
    fr = len(x) // hop
    if fr < 3 * len(words):
        return _even(words, 0.0, total_s), 'even'
    rms = np.sqrt(np.mean(x[:fr * hop].reshape(fr, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    voiced = (db > db.max() - 32) & (db > -60)        # louder than the best, and louder than a hiss
    if not voiced.any():
        return _even(words, 0.0, total_s), 'even'
    first_v = int(np.argmax(voiced))
    last_v = fr - int(np.argmax(voiced[::-1]))
    span = max(1, last_v - first_v)
    wts = [weight(w) for w in words]
    tot = sum(wts)
    cum = np.cumsum(wts)

    pauses, i = [], 0
    while i < fr:
        if not voiced[i]:
            j = i
            while j < fr and not voiced[j]:
                j += 1
            if i > first_v and j <= last_v and j - i >= 9:       # 90 ms inside the speech
                pauses.append((i, j))
            i = j
        else:
            i += 1

    # a pause is the punctuation's only if it falls where the words say it should
    slots = [k for k, w in enumerate(words[:-1]) if w[-1] in ',;:.!?']
    chosen: list[tuple[int, tuple[int, int]]] = []
    floor_frame = first_v
    window = max(30, int(0.18 * span))
    for k in slots:
        pred = first_v + span * cum[k] / tot
        cands = [p for p in pauses if p[0] > floor_frame and abs((p[0] + p[1]) / 2 - pred) <= window]
        if cands:
            p = max(cands, key=lambda q: (q[1] - q[0]) - 0.05 * abs((q[0] + q[1]) / 2 - pred))
            chosen.append((k, p))
            floor_frame = p[1]

    bounds, a_frame, a_word = [], first_v, 0
    for k, p in chosen:
        bounds.append((a_word, k, a_frame, p[0]))
        a_frame, a_word = p[1], k + 1
    bounds.append((a_word, len(words) - 1, a_frame, last_v))

    starts, ends = [0.0] * len(words), [0.0] * len(words)
    for w0, w1, f0, f1 in bounds:
        if f1 - f0 < 2 * (w1 - w0 + 1):
            return _even(words, first_v * 0.01, last_v * 0.01), 'even'
        seg = voiced[f0:f1]
        csum = np.concatenate([[0], np.cumsum(seg)])
        ws = wts[w0:w1 + 1]
        t_seg, acc, edges = sum(ws), 0.0, [f0]
        for wt in ws[:-1]:
            acc += wt
            f = f0 + int(np.searchsorted(csum, csum[-1] * acc / t_seg))
            lo, hi = max(edges[-1] + 2, f - 6), min(f1 - 1, f + 6)
            if hi > lo:
                f = lo + int(np.argmin(db[lo:hi]))        # the dip between two words
            edges.append(max(f, edges[-1] + 2))
        edges.append(f1)
        for k in range(len(ws)):
            starts[w0 + k], ends[w0 + k] = edges[k] * 0.01, edges[k + 1] * 0.01

    out = [[round(s, 3), round(e, 3)] for s, e in zip(starts, ends)]
    ok = all(e - s >= 0.06 for s, e in out) and all(out[k][1] <= out[k + 1][0] + 1e-6 for k in range(len(out) - 1))
    if not ok or out[-1][1] > total_s + 0.05:
        return _even(words, first_v * 0.01, last_v * 0.01), 'even'
    return out, 'measured'
