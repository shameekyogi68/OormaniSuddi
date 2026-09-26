"""
ಊರ್ಮನಿ ಸುದ್ದಿ — "ಕರಾವಳಿ 2050" brand promo, built end to end in one place.
===========================================================================
Replaces the fourteen one-off scripts that built earlier cuts at the repo root.
What those cuts got wrong, and what this does instead:

  * Subtitles sat at y≈1490 — under Instagram's caption block (Format 'reel'
    keeps critical content above y=1440 and left of x=860). Every overlay here
    is laid out inside that box and `qc()` measures it on rendered frames.
  * Music: the owner's chosen track (BED), cut to the picture — its opening
    to the beat before the logo, a quarter-second of silence, then its biggest
    drop (DROP_AT) under the logo. Every cut sits on its 0.8s beat grid. It is
    still BLOCKED in assets/LICENCES.json; the build says so every run. `score()`
    is an owned, synthesised alternative kept for when that matters.
  * Voice: Google Kannada, performed phrase by phrase to the owner's direction
    (VO_PLAN: pauses, stress, pace). By ear the owner rejected Edge twice and
    SYSPIN's male voice once, on pronunciation. Clips play at 0.88x so the
    script fits at the channel's normal Google pace.
  * SFX came from `sfx/pro_*.wav`, which D82 says have no provenance. The sound
    design here (impacts, reverse swells, doppler whooshes, shimmer, digital
    glitches) is synthesised in `sound_design()`, cue-for-cue with the picture.
  * The Gemini ✦ stays visible (the owner decided an emblem over it was not
    needed; COVER_WATERMARK). `ಎಐ ರಚಿತ ದೃಶ್ಯಗಳು` is on screen throughout.
  * "ಅಧಿಕೃತ ಮಾಧ್ಯಮ" (official media) was a claim the channel cannot make.
  * 17 inputs through `amix` (which divides each by N) then single-pass
    loudnorm, with step-function ducking → a limp, pumping mix. Here the mix is
    summed at unity in numpy, ducked by a smoothed voice key, and normalised
    mastered (glue, gain, 4x-oversampled limiter) to tokens.Limits.lufs /
    true_peak_dbtp.
  * Hard cuts, a static frame, a 36px caption. Here: slow push-ins, motion-
    blurred whips and zoom-throughs on every cut, a title hook, phrase-timed
    subtitles with held gold emphasis, an animated end card. Every line of the
    script describes the shot it plays over.

    python3 scripts/build_promo.py            # full build + QC
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import maximum_filter1d
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from brand.tokens import Brand, C, FORMATS, Limits  # noqa: E402

os.chdir(ROOT)
BUILD = 'build/promo_v3'
OUT = 'out/promo_karavali_2050'
FINAL = (f'{OUT}/promo_karavali_2050_no_voice.mp4' if os.environ.get('PROMO_NO_VOICE') == '1'
         else f'{OUT}/promo_karavali_2050_final.mp4'
         if os.environ.get('PROMO_VOICE', 'google') == 'google'
         else f'{OUT}/promo_karavali_2050_{os.environ["PROMO_VOICE"]}voice.mp4')

W, H, FPS, SR = 1080, 1920, 24, 48000
FMT = FORMATS['reel']
SAFE_L, SAFE_T = FMT.safe[0], FMT.safe[1]
SAFE_R, SAFE_B = W - FMT.safe[2], H - FMT.safe[3]        # 860, 1440
SEED = 20260922

# The bed runs at 75 BPM (0.8s a beat, measured) and its strong hits fall on
# multiples of 0.8s — so every cut, and the logo, sits on one.
BEAT = 0.8
# Slow motion: each 6s clip plays at 0.88x (frame-blended), so a shot holds 8
# beats (6.4s) instead of 7 — room for the directed script at a natural pace,
# and the grander feel a trailer wants.
SPEEDS = [0.88, 0.88, 0.88, 0.88, 0.81]
CLIP_SRC, XF = 6.0, 0.4
CLIP_LENS = [CLIP_SRC / sp for sp in SPEEDS]
CLIP_LEN = CLIP_LENS[0]                 # the common case; scene 5 is longer
FONT_KN = 'fonts/NotoSansKannada-Bold.ttf'
FONT_KN_SERIF = 'fonts/NotoSerifKannada-Bold.ttf'
FONT_LATIN = '/System/Library/Fonts/Supplemental/Georgia.ttf'
FONT_LATIN_BOLD = '/System/Library/Fonts/Supplemental/Georgia Bold.ttf'
FONT_LATIN_SANS = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
VOICE = 'kn-IN-GaganNeural'

AI_LABEL = 'ಎಐ ರಚಿತ ದೃಶ್ಯಗಳು  •  ಕಾಲ್ಪನಿಕ ಚಿತ್ರಣ'
# The voice disclosure is true only while the narration is synthesised. With a
# human read (PROMO_VO_WAV) it would be a false statement, so it comes off.
END_DISCLOSURE = ('ಎಐ ರಚಿತ ದೃಶ್ಯಗಳು  •  ಕಾಲ್ಪನಿಕ ಚಿತ್ರಣ' if os.environ.get('PROMO_VO_WAV')
                  else 'ಎಐ ರಚಿತ ದೃಶ್ಯಗಳು  •  ಧ್ವನಿ ಕಂಪ್ಯೂಟರ್-ನಿರ್ಮಿತ')

# (clip, kicker, spoken line, transition INTO the next scene)
SCENES = [
    ('Hover_boats_at_fishing_port_20260922123710.mp4', 'ಬಂದರು  ·  2050',
     'ಕಾಲ ಬದಲಾಗಬಹುದು, | ಕಡಲ ತೀರವೇ *ಬದಲಾಗಬಹುದು.', 'whip'),
    ('Man_racing_buffaloes_in_mud_20260922123746.mp4', 'ಕಂಬಳ  ·  2050',
     'ಆದರೆ ಕರಾವಳಿಯ ಕೆಸರುಗದ್ದೆಯ | ಈ *ಕಿಚ್ಚು, ಈ *ಗತ್ತು, | ಎಂದಿಗೂ *ಕುಗ್ಗದು!', 'zoom'),
    ('Drone_tracks_magnetic_bullet_train_20260922123741.mp4', 'ಪಶ್ಚಿಮ ಘಟ್ಟ  ·  2050',
     'ಘಟ್ಟಗಳನ್ನು ದಾಟಿ | ಜಗತ್ತು ಎಷ್ಟೇ ಮುನ್ನುಗ್ಗಲಿ, | ನಮ್ಮ ಮಣ್ಣಿನ *ನಂಟು | ಎಂದಿಗೂ *ಕಳಚದು.', 'leak'),
    ('Artist_holding_glowing_digital_s…_20260922123740.mp4', 'ಯಕ್ಷಗಾನ  ·  2050',
     'ಇದು ತಲೆಮಾರುಗಳ *ಪರಂಪರೆ. | ಹೊಸ ಯುಗದಲ್ಲೂ ಮೊಳಗುವ | ಗಂಡುಕಲೆಯ *ಕಹಳೆ!', 'whip'),
    ('Hands_holding_futuristic_black_s…_20260922123733.mp4', 'ಇಂದು  ·  ನಿಮ್ಮ ಕೈಯಲ್ಲಿ',
     'ಭವಿಷ್ಯ ಎಷ್ಟೇ ಮುಂದುವರಿಯಲಿ, | ನಮ್ಮೂರಿನ ನೈಜ ಸುದ್ದಿ | ಈಗ ನಿಮ್ಮ *ಅಂಗೈಯಲ್ಲಿ.', None),
]

# The owner's voice direction, performed: each line is voiced phrase by phrase
# (text, silence after in seconds, stressed) at the scene's own pace. The words
# must be the line's words in order — voice() checks.
VO_PLAN = [
    (0.96, [('ಕಾಲ ಬದಲಾಗಬಹುದು', 0.4, False), ('ಕಡಲ ತೀರವೇ ಬದಲಾಗಬಹುದು', 0, True)]),
    (1.03, [('ಆದರೆ ಕರಾವಳಿಯ ಕೆಸರುಗದ್ದೆಯ ಈ ಕಿಚ್ಚು', 0.2, True), ('ಈ ಗತ್ತು', 0.3, True),
            ('ಎಂದಿಗೂ ಕುಗ್ಗದು!', 0, True)]),
    (1.04, [('ಘಟ್ಟಗಳನ್ನು ದಾಟಿ ಜಗತ್ತು ಎಷ್ಟೇ ಮುನ್ನುಗ್ಗಲಿ', 0.3, False), ('ನಮ್ಮ ಮಣ್ಣಿನ ನಂಟು', 0.15, True),
            ('ಎಂದಿಗೂ ಕಳಚದು', 0, True)]),
    (0.98, [('ಇದು ತಲೆಮಾರುಗಳ ಪರಂಪರೆ', 0.4, True), ('ಹೊಸ ಯುಗದಲ್ಲೂ ಮೊಳಗುವ', 0.1, False),
            ('ಗಂಡುಕಲೆಯ ಕಹಳೆ!', 0, True)]),
    (1.02, [('ಭವಿಷ್ಯ ಎಷ್ಟೇ ಮುಂದುವರಿಯಲಿ', 0.25, False),
            ('ನಮ್ಮೂರಿನ ನೈಜ ಸುದ್ದಿ ಈಗ ನಿಮ್ಮ ಅಂಗೈಯಲ್ಲಿ', 0, True)]),
    (0.97, [('ಊರ್ಮನಿ ಸುದ್ದಿ', 0.4, True), ('ನಮ್ಮ ಊರು, ನಮ್ಮ ಧ್ವನಿ', 0, False)]),
]
STRESS_DB = 1.8


# Real, published, sourced stories — official status, named verifier, source
# on file — arriving on the phone as the line says the news is in your hand.
# The stamp is the story's date, not "now": the promo outlives the day.
NEWS = [('editions/2026-09-20.json', 'ಹಡಗು ನಿರ್ಮಾಣ', 'ಸೆ. 20'),
        ('editions/2026-09-20.json', 'ಮಾಲ್ಪೆ ಬೀಚ್', 'ಸೆ. 20')]


def news_items():
    items = []
    for path, needle, stamp in NEWS:
        story = next(x for x in json.load(open(path))['stories'] if needle in x['headline'])
        assert story.get('source_urls') and story.get('verified_by'), f'unsourced: {needle}'
        items.append((story['reel_line'], stamp))
    return items


def spoken(text):
    """Script markup off: '|' is a line break, '*' holds a word in gold."""
    return ' '.join(text.replace('|', ' ').replace('*', '').split())


SIGN_OFF = 'ಊರ್ಮನಿ ಸುದ್ದಿ. ನಮ್ಮ ಊರು, ನಮ್ಮ ಧ್ವನಿ.'

# The bed's first hit is 0.39s in; it is trimmed so that hit IS frame 0 — the
# hook. Its beat grid (multiples of 0.8s in track time) moves with it.
BED_OFFSET = 0.39
CUTS = [BEAT * 8 * (i + 1) - BED_OFFSET for i in range(len(SCENES) - 1)]
BASE_END = BEAT * 41 - BED_OFFSET                                    # the logo
STARTS = [0.0] + [c - XF / 2 for c in CUTS]
assert all(STARTS[i] + CLIP_LENS[i] >= e + XF / 2 - 1e-9
           for i, e in enumerate(CUTS + [BASE_END - XF / 2])), 'a clip is too short for its shot'
WINDOWS = list(zip([0.0] + CUTS, CUTS + [BASE_END]))                # what each line may fill


def rgb(c):
    return tuple(int(v) for v in c[:3])


GOLD, GOLD_HI, INK = rgb(C.gold_400), rgb(C.gold_300), rgb(C.ink_950)


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def ease_io(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def ease_back(u, s=1.6):
    u = min(max(u, 0.0), 1.0) - 1
    return 1 + (s + 1) * u ** 3 + s * u ** 2


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  VOICE — synthesised with word boundaries, fitted to its scene
# ─────────────────────────────────────────────────────────────────────────────

def _speech_spans(x, floor_db=-40.0, min_gap=0.1):
    """(start, end) seconds of each run of speech in mono `x`."""
    hop = int(SR * 0.01)
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    on = db > floor_db
    spans, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and (on[j] or (j + int(min_gap * 100) < n and on[j:j + int(min_gap * 100)].any())):
                j += 1
            spans.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return spans


def _google(text, wav, tempo):
    """Google's Kannada voice — the one this channel's owner chose by ear over
    Edge (brand/voice.py, DEFAULT_ENGINE). Edge read this promo in the last cut
    and the pronunciation was rejected again."""
    from brand.voice import _google_tts_synthesize
    mp3 = wav + '.mp3'
    _google_tts_synthesize(text, mp3, tempo=tempo)
    run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-ac', '1', '-ar', str(SR), wav])
    return decode(wav, ch=1)[:, 0]


SYSPIN = 'build/voice_models/syspin_kn_male'
# Google Kannada — the owner's ear chose it over Edge AND over SYSPIN (whose
# pronunciation was rejected, 2026-09-22). SYSPIN stays as PROMO_VOICE=syspin.
VOICE_ENGINE = os.environ.get('PROMO_VOICE', 'google')
# PROMO_NO_VOICE=1 delivers the picture with the bed ALREADY DUCKED where the
# lines go, so a human voice-over drops straight into the pockets.
NO_VOICE = os.environ.get('PROMO_NO_VOICE') == '1'
# PROMO_VO_WAV=<file> uses a human recording (voice only, full length, silence
# between lines — a soloed GarageBand export) instead of any TTS.
HUMAN_VO = os.environ.get('PROMO_VO_WAV')
GOOGLE_BASE = 1.12        # the channel's reels run Google at 1.15 (brand/voice.py)


def _syspin(text, wav, tempo):
    """SYSPIN Kannada male VITS (IISc Bangalore, SPIRE Lab; CC-BY-4.0 — the
    credit line is in the post copy). A male narrator trained on 30 hours of a
    native speaker; Google's voice is accurate but light and flat for a
    trailer. Fetched once into build/ — see SYSPIN/synth.py."""
    raw = wav + '.22k.wav'
    run(['python3', f'{SYSPIN}/synth.py', raw, text], capture_output=True)
    af = f'aresample={SR}' + (f',atempo={tempo}' if abs(tempo - 1) > 1e-3 else '')
    run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', af, '-ac', '1', wav])
    return decode(wav, ch=1)[:, 0]


def _align(words, spans):
    """Split `words` (in order) across speech runs so each run's share of the
    characters best matches its share of the speaking time. Exact DP."""
    L = [_syllables(w) for w in words]
    n, m = len(words), len(spans)
    tot_c = sum(L)
    tot_t = sum(b - a for a, b in spans)
    pre = np.concatenate([[0], np.cumsum(L)])
    INF = float('inf')
    cost = np.full((m + 1, n + 1), INF)
    back = np.zeros((m + 1, n + 1), int)
    cost[0, 0] = 0
    for j in range(1, m + 1):
        want = (spans[j - 1][1] - spans[j - 1][0]) / tot_t
        for i in range(j, n - (m - j) + 1):
            for k in range(j - 1, i):
                c = cost[j - 1, k] + ((pre[i] - pre[k]) / tot_c - want) ** 2
                if c < cost[j, i]:
                    cost[j, i], back[j, i] = c, k
    cuts, i = [], n
    for j in range(m, 0, -1):
        cuts.append((back[j, i], i))
        i = back[j, i]
    return [words[a:b] for a, b in reversed(cuts)]


def word_times(text, x):
    """Word timings from the voice's own pauses: each run of speech gets the
    words that best fill it (by length), and inside a run the words share its
    time by length. Returns (offset, duration, word) from the first sound, and
    the trim point."""
    spans = [s for s in _speech_spans(x) if s[1] - s[0] >= 0.06]
    t0 = spans[0][0]
    words = text.split()
    while len(spans) > len(words):                     # merge across the shortest gap
        g = min(range(len(spans) - 1), key=lambda k: spans[k + 1][0] - spans[k][1])
        spans[g:g + 2] = [(spans[g][0], spans[g + 1][1])]
    ons = onsets(x)
    out = []
    for (a, b), g in zip(spans, _align(words, spans)):
        Lg = sum(_syllables(w) for w in g)
        t = a
        starts = []
        for w in g:
            starts.append(t)
            t += (b - a) * _syllables(w) / Lg
        # snap each word (not the first: the run already starts there) onto the
        # nearest real onset, keeping the order and never crossing a neighbour
        for k in range(1, len(starts)):
            near = ons[(ons > starts[k] - 0.14) & (ons < starts[k] + 0.14)]
            if len(near):
                cand = float(near[np.argmin(np.abs(near - starts[k]))])
                if starts[k - 1] + 0.08 < cand < (starts[k + 1] if k + 1 < len(starts) else b) - 0.08:
                    starts[k] = cand
        for k, w in enumerate(g):
            end = starts[k + 1] if k + 1 < len(starts) else b
            out.append((starts[k] - t0, end - starts[k], w))
    return out, t0


VO_CHAIN = ('highpass=f=75,equalizer=f=140:t=q:w=0.8:g=1.5,'
            'equalizer=f=380:t=q:w=1.2:g=-2,equalizer=f=4200:t=q:w=1.1:g=2.5,'
            'treble=g=1.5:f=10000,deesser=i=0.35,'
            'acompressor=threshold=-21dB:ratio=3:attack=6:release=90:makeup=2.5')


def decode(path, af=None, ch=2):
    cmd = ['ffmpeg', '-v', 'error', '-i', path]
    if af:
        cmd += ['-af', af]
    cmd += ['-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-']
    raw = run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).astype(np.float64)


def _phrase(text, key):
    """One phrase in the promo voice, as a file. Cached per engine."""
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()[:10]
    if VOICE_ENGINE == 'google':
        from brand.voice import _google_tts_synthesize
        os.makedirs(f'{BUILD}/vo_g', exist_ok=True)
        mp3 = f'{BUILD}/vo_g/{h}.mp3'
        if not os.path.exists(mp3):
            _google_tts_synthesize(text, mp3, tempo=1.0)
        return mp3
    raw = f'{BUILD}/vo/ph_{h}.wav'
    if not os.path.exists(raw):
        run(['python3', f'{SYSPIN}/synth.py', raw, text], capture_output=True)
    return raw


def performed(i, fit):
    """Line i voiced to its VO_PLAN at pace base*fit: phrases, exact silences,
    stress. Returns audio, word times, pace, speech length."""
    base, plan = VO_PLAN[i]
    pace = base * fit * (GOOGLE_BASE if VOICE_ENGINE == 'google' else 1.0)
    parts, words, t = [], [], 0.0
    for text, pause, stress in plan:
        x = decode(_phrase(text, i), f'aresample={SR},atempo={pace:.4f}', ch=1)[:, 0]
        sp = _speech_spans(x)
        x = x[int(SR * max(sp[0][0] - 0.02, 0)):int(SR * (sp[-1][1] + 0.04))]
        if stress:
            x = x * 10 ** (STRESS_DB / 20)
        f = int(SR * 0.008)
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
        ws = text.split()
        L = sum(len(w) for w in ws)
        dur = len(x) / SR
        tt = t
        for w in ws:
            d = dur * len(w) / L
            words.append((tt, d, w))
            tt += d
        parts += [x, np.zeros(int(SR * pause))]
        t += dur + pause
    return np.concatenate(parts), words, pace, t - plan[-1][1]


# Trailer scheduling: the voice may lead a cut by a hair (it rides the whoosh)
# and spill past the next one — the way VO is cut against picture — so the
# owner's pauses keep their full length instead of every line being squeezed
# into its own shot.
VO_LEAD, VO_SPILL, VO_GAP = 0.1, 0.6, 0.2


def schedule(lengths):
    """Earliest-start packing. Returns starts, or None if it cannot fit."""
    starts, prev_end = [], -1.0
    for i, L in enumerate(lengths):
        w0, w1 = WINDOWS[i]
        st = max(0.6 if i == 0 else w0 - VO_LEAD, prev_end + VO_GAP)
        limit = BASE_END - 0.28 if i == len(lengths) - 1 else w1 + VO_SPILL
        if st + L > limit:
            return None
        starts.append(st)
        prev_end = st + L
    return starts


def _syllables(t):
    """Kannada aksharas: an independent vowel, or a consonant not killed by a
    virama. Close enough to syllable count to time words and match takes."""
    t = ''.join(c for c in t if '\u0c80' <= c <= '\u0cff')
    out, i = 0, 0
    while i < len(t):
        c = t[i]
        if '\u0c85' <= c <= '\u0c94':
            out += 1
        elif '\u0c95' <= c <= '\u0cb9' and not (i + 1 < len(t) and t[i + 1] == '\u0ccd'):
            out += 1
        i += 1
    return max(out, 1)


def onsets(x, floor=0.06):
    """Times of syllable onsets — spectral flux peaks. Used to snap subtitle
    words onto the sound that actually starts them."""
    from scipy.signal import stft, find_peaks
    _f, t, Z = stft(x, fs=SR, nperseg=1024, noverlap=768)
    mag = np.abs(Z)
    flux = np.maximum(np.diff(mag, axis=1, prepend=mag[:, :1]), 0).sum(0)
    flux /= flux.max() + 1e-9
    pk, _ = find_peaks(flux, height=floor, distance=6)
    return t[pk]


def clean_voice(x):
    """Take the ROOM out of a home recording: spectral noise subtraction plus
    de-reverberation (each frame has the decayed tail of the frames before it
    subtracted). Gains are smoothed in time and frequency so it does not
    shimmer, and nothing is gated to silence.

    This is what an untreated room needs; a broadband denoiser alone leaves the
    reflections, which is what makes a voice sound 'in a bedroom'.
    """
    from scipy.signal import stft, istft
    from scipy.ndimage import uniform_filter
    f, t, Z = stft(x, fs=SR, nperseg=2048, noverlap=1536)
    mag, phase = np.abs(Z), np.angle(Z)
    noise = np.percentile(mag, 12, axis=1, keepdims=True)          # the room, per bin
    tail = np.zeros_like(mag)
    for k in range(1, 9):                                          # its decay, ~0.6/frame
        tail[:, k:] = np.maximum(tail[:, k:], mag[:, :-k] * (0.62 ** k))
    clean = mag - 1.7 * noise - 0.5 * tail
    gain = np.clip(clean, 0.06 * mag, None) / (mag + 1e-12)
    gain = uniform_filter(gain, size=(3, 3))
    _t, y = istft(mag * gain * np.exp(1j * phase), fs=SR, nperseg=2048, noverlap=1536)
    return y[:len(x)]


# A broadcast voice-over's long-term spectrum: flat through the chest, the
# room region pulled back, then a steady ~4dB/octave fall above 250Hz. Hand-set
# EQ points cannot hit this on an unknown mic in an unknown room — measuring
# the take and correcting towards the curve can, and it is checkable.
VO_TARGET_TILT_DB = -15.0        # 2-6kHz against 150-600Hz, measured


def _ltas(x, nfft=4096):
    """Long-term average spectrum over the speech only."""
    from scipy.signal import stft
    f, _t, Z = stft(x, fs=SR, nperseg=nfft, noverlap=nfft // 2)
    mag = np.abs(Z)
    lvl = 20 * np.log10(mag.mean(0) + 1e-12)
    keep = lvl > lvl.max() - 25
    return f, mag[:, keep].mean(1) + 1e-12


def _target_curve(f):
    """A voice's own shape: peak around 250Hz, falling either side — -7dB/oct
    below (where a close mic over-gives) and -6.2dB/oct above."""
    t = np.zeros_like(f)
    lo = f < 250                              # a close mic over-gives here
    t[lo] = np.maximum(-3.2 * np.log2(250 / np.maximum(f[lo], 35)), -10)
    hi = f > 250
    t[hi] = -6.2 * np.log2(f[hi] / 250)       # swept against the measured tilt
    return t


def match_eq(x, limit=12.0):
    """Correct the voice towards VO_TARGET: a smoothed, bounded, zero-phase
    correction filter derived from this take's own spectrum."""
    from scipy.signal import firwin2, filtfilt
    from scipy.ndimage import uniform_filter1d
    f, ltas = _ltas(x)
    meas = 20 * np.log10(ltas)
    ref = (f >= 150) & (f < 600)
    meas -= meas[ref].mean()
    corr = _target_curve(f) - meas
    # smooth in log-frequency so the filter is gentle, and bound it
    idx = np.clip((np.log2(np.maximum(f, 20) / 20) * 24).astype(int), 0, None)
    sm = np.zeros_like(corr)
    for k in range(idx.max() + 1):
        m = idx == k
        if m.any():
            sm[m] = corr[m].mean()
    sm = uniform_filter1d(sm, 9)
    sm = np.clip(sm, -limit, limit)
    sm[f < 60] = min(sm[(f >= 60) & (f < 90)].mean(), 0)      # no sub boost
    gains = 10 ** (sm / 20)
    freqs = np.concatenate([[0.0], f / (SR / 2), [1.0]])
    gains = np.concatenate([[gains[0]], gains, [gains[-1]]])
    keep = np.concatenate([[True], np.diff(freqs) > 0])
    taps = firwin2(1025, freqs[keep], gains[keep])
    return filtfilt(taps, [1.0], x)


def de_plosive(x):
    """Duck 20-120Hz only on the frames where a P or B blast makes it spike —
    a dynamic low cut, so the chest stays on every other word."""
    from scipy.signal import stft, istft
    f, _t, Z = stft(x, fs=SR, nperseg=1024, noverlap=768)
    mag = np.abs(Z)
    low = (f >= 20) & (f < 120)
    mid = (f >= 300) & (f < 3000)
    ratio = mag[low].mean(0) / (mag[mid].mean(0) + 1e-9)
    over = np.clip(ratio / 2.0, 1.0, None)                    # 1 = fine, >1 = blast
    gain = np.ones_like(mag)
    gain[low] = 1.0 / over
    _tt, y = istft(Z * gain, fs=SR, nperseg=1024, noverlap=768)
    return y[:len(x)]


# ── The voice-over chain, for a voice recorded in an untreated room ─────────
# Measured on the take: dual mono, peak -0.1dBFS, room floor ≈ -38dB, a little
# 50Hz hum, 60–300Hz room build-up, and 3–10kHz some 30dB down (dull). So:
# clean first (hum, rumble, broadband room noise, the tail between words), then
# shape — cut the mud, restore the missing presence and air, add weight low
# down — then control the dynamics and warm it, the way a dub stage does.
# Chosen by the owner's ear in an A/B of four treatments (2026-09-23): light.
# What was rejected, and why it is not coming back: spectral de-reverberation
# and noise SUBTRACTION leave vowels watery and gated; a per-line match EQ of
# ±12dB shifts the timbre line to line and lifts room hiss with the clarity; an
# exciter over two compressors and a limiter goes harsh. Measurements improved
# while the voice got worse. Keep this chain gentle — one EQ move per problem,
# one compressor, and nothing that works by taking energy away.
# Chosen by the owner's ear, 2026-09-24, from seven full-read versions:
# room resonances notched out, then the light chain, a short dub-stage plate,
# and parallel compression for weight. The notches are measured from the take
# (164Hz +6.2dB and 451Hz +2.1dB above the voice's own curve) — that 164Hz peak
# is the "small room at home" signature. The plate replaces the bedroom with a
# designed space; the parallel path adds density without squashing the read.
# Rejected earlier and not to be reinstated: spectral de-reverb / noise
# subtraction (watery vowels) and per-line match EQ (timbre drifts line to line).
VO_ROOM_NOTCH = ('equalizer=f=164:width_type=q:w=4:g=-5,'
                 'equalizer=f=451:width_type=q:w=4:g=-2.5')
VO_PLATE = 'aecho=0.9:0.82:23|31:0.05|0.038'
# The parallel path is what lifted the room between words (it was threshold
# -30dB with +6dB makeup — it amplified exactly the quiet parts). It now starts
# well above the noise, and an expander in front of the plate and the parallel
# path means neither ever sees room tone.
VO_DENSITY = ('asplit[vdry][vsq];'
              '[vsq]acompressor=threshold=-24dB:ratio=4:attack=5:release=140:makeup=4[vpar];'
              '[vdry][vpar]amix=inputs=2:weights=1 0.22')
HUMAN_CHAIN = ','.join([
    VO_ROOM_NOTCH,
    'aformat=channel_layouts=mono',
    'highpass=f=70:poles=2',                                   # lower, to keep weight
    'afftdn=nr=14:nf={nf:.0f}:tn=1',                           # to the measured floor
    'agate=threshold={gate:.4f}:ratio=3:attack=4:release=260:knee=6',   # room tone, not the voice
    'equalizer=f=300:width_type=q:w=1.1:g=-2.5',               # boxy room
    'bass=g=4:f=105:width_type=q:w=0.7',                       # weight, under the 164Hz notch
    'equalizer=f=3200:width_type=q:w=1.0:g=3',                 # presence / diction
    'treble=g=2.5:f=9000:width_type=q:w=0.8',                  # air
    'deesser=i=0.3:m=0.5:f=0.4',
    'acompressor=threshold=-19dB:ratio=2.2:attack=10:release=150:makeup=2',
    VO_PLATE,
    VO_DENSITY,
])


def repair(path):
    """What a take needs before any treatment: de-clip (VC 2 was loudness
    maximised — 1734 clipped runs) and de-click. Measures the room floor so the
    denoiser is set to this take, not to a guess."""
    out = f'{BUILD}/vo/source_repaired.wav'
    run(['ffmpeg', '-v', 'error', '-y', '-i', path,
         '-af', 'aformat=channel_layouts=mono,adeclip=window=55:overlap=75,'
                'adeclick=window=55:overlap=75:arorder=2:threshold=2',
         '-ar', str(SR), out])
    x = decode(out, ch=1)[:, 0]
    sp = [t for t in _speech_spans(x, -38.0, 0.25) if t[1] - t[0] > 0.4]
    gaps = [(sp[i][1] + 0.08, sp[i + 1][0] - 0.08) for i in range(len(sp) - 1)
            if sp[i + 1][0] - sp[i][1] > 0.3]
    floor = float(np.mean([rms_db(x[int(SR * a):int(SR * b)]) for a, b in gaps])) if gaps else -42.0
    clipped = int((np.abs(decode(path, ch=1)[:, 0]) >= 0.985).sum())
    print(f'  take repaired: {clipped} clipped samples restored, room floor {floor:.1f} dB')
    return out, floor


def human_read(lines):
    """A human voice-over: one voice-only file the length of the promo.

    Which burst is which line is decided by measurement, not by guessing at
    gaps: the syllable count of each written line is matched against the
    syllable nuclei heard in the take (energy peaks), and the split that fits
    best across the whole recording wins. Then each line is cleaned and shaped
    by HUMAN_CHAIN, and the subtitles are timed to what was actually said.
    """
    # -ac 1 SUMS a dual-mono file (+6dB, and it merges bursts under the
    # detector). Average the channels instead.
    src, floor = repair(HUMAN_VO)
    chain = HUMAN_CHAIN.format(nf=max(min(floor, -25.0), -50.0),
                               gate=10 ** ((floor + 10) / 20))
    x = decode(src, ch=1)[:, 0]
    groups = fit_lines(x, [spoken(t) for t in lines], floor + 8)
    placed = []
    for i, ((a, b_), text) in enumerate(zip(groups, lines)):
        seg = x[int(SR * max(a - 0.08, 0)):int(SR * (b_ + 0.15))]
        raw = f'{BUILD}/vo/human{i + 1}_raw.wav'
        out = f'{BUILD}/vo/human{i + 1}.wav'
        write_mono(raw, seg / (np.max(np.abs(seg)) + 1e-9) * 0.9)
        flag = '-filter_complex' if 'asplit' in chain else '-af'
        run(['ffmpeg', '-v', 'error', '-y', '-i', raw, flag, chain, '-ac', '1', out])
        y = decode(out, ch=1)[:, 0]
        words, t0 = word_times(spoken(text), y)
        y = y[int(SR * max(t0 - 0.04, 0)):]
        f = int(SR * 0.01)
        y[:f] *= np.linspace(0, 1, f)
        write_mono(out, y)
        length = words[-1][0] + words[-1][1]
        placed.append(dict(text=text, start=0.0, words=words, audio=decode(out, ch=2),
                           end=length, rate='human', speech=y))
        print(f'  vo{i + 1}  your take {a:5.2f}→{b_:5.2f}s  ({length:.2f}s spoken)  {spoken(text)[:44]}')
    # One level for the whole read: a line that sits 2 LU back reads as a
    # different take. Match each to the median of the speech in all of them.
    lv = [rms_db(p['speech'][np.abs(p['speech']) > 10 ** (-40 / 20)]) for p in placed]
    ref = float(np.median(lv))
    for p, l in zip(placed, lv):
        p['audio'] = p['audio'] * 10 ** ((ref - l) / 20)
    print(f'  levelled the read: was {max(lv) - min(lv):.1f} LU apart, now matched to {ref:.1f} dB')

    starts = schedule([p['end'] for p in placed[:len(SCENES)]])
    if not starts:
        raise SystemExit('your read is longer than the picture — tell me and I will stretch the shots')
    starts.append(BASE_END + 0.45)
    for p, st in zip(placed, starts):
        p['start'], p['end'] = st, st + p['end']
        print(f"    placed at {st:5.2f} → {p['end']:5.2f}s")
    return placed


def fit_lines(x, texts, gate_db=-45.0):
    """Split a take into one span per written line, by syllable count. The gate
    follows the take's own floor: a loudness-maximised file (VC 2, floor -42dB)
    is one continuous sound to a fixed -45dB gate."""
    from scipy.signal import find_peaks
    from scipy.ndimage import uniform_filter1d
    hop = int(SR * 0.01)
    n = len(x) // hop
    env = uniform_filter1d(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)), 7)
    env = env / (env.max() + 1e-9)
    pk, _ = find_peaks(env, height=0.045, distance=8, prominence=0.02)
    pkt = pk * 0.01
    runs = [r for r in _speech_spans(x, gate_db, 0.12) if r[1] - r[0] > 0.15]
    lvl = [rms_db(x[int(SR * a):int(SR * b)]) for a, b in runs]
    keep = np.median(lvl) - 12                      # room noise, not a spoken word
    runs = [r for r, l in zip(runs, lvl) if l > keep]
    per = [int(((pkt >= a) & (pkt <= b)).sum()) for a, b in runs]

    want = [_syllables(t) for t in texts]
    G, R = len(texts), len(runs)
    if R < G:
        raise SystemExit(f'only {R} spoken runs in {HUMAN_VO} for {G} lines')
    INF = float('inf')
    cost = np.full((G + 1, R + 1), INF)
    back = np.zeros((G + 1, R + 1), int)
    cost[0, 0] = 0
    for g in range(1, G + 1):
        for i in range(g, R - (G - g) + 1):
            for k in range(g - 1, i):
                d = abs(sum(per[k:i]) - want[g - 1])
                c = cost[g - 1, k] + d ** 1.5 + 0.6 * d
                if c < cost[g, i]:
                    cost[g, i], back[g, i] = c, k
    cuts, i = [], R
    for g in range(G, 0, -1):
        cuts.append((back[g, i], i))
        i = back[g, i]
    spans = [(runs[a][0], runs[b - 1][1]) for a, b in reversed(cuts)]
    for (a, b), w, t in zip(spans, want, texts):
        heard = sum(p for r, p in zip(runs, per) if a <= r[0] and r[1] <= b)
        if abs(heard - w) > max(4, 0.25 * w):
            print(f'  ! line "{t[:30]}…": heard ~{heard} syllables, script has {w} — check the take')
    return spans


def read_naturally(lines):
    """Each line read as written: one whole sentence to the voice, its own
    rhythm, pauses only where the punctuation puts them, one steady pace for
    the whole promo (the gentlest that fits the picture). The subtitle shows
    exactly the text that is read."""
    from brand.voice import _google_tts_synthesize
    import hashlib
    os.makedirs(f'{BUILD}/vo_g', exist_ok=True)
    raws = []
    for text in lines:
        t = spoken(text)
        mp3 = f'{BUILD}/vo_g/line_{hashlib.md5(t.encode()).hexdigest()[:10]}.mp3'
        if not os.path.exists(mp3):
            _google_tts_synthesize(t, mp3, tempo=1.0)
        raws.append((t, mp3))

    def take(i, pace):
        t, mp3 = raws[i]
        x = decode(mp3, f'aresample={SR},atempo={pace:.4f}', ch=1)[:, 0]
        words, t0 = word_times(t, x)
        x = x[int(SR * max(t0 - 0.03, 0)):]
        f = int(SR * 0.01)
        x[:f] *= np.linspace(0, 1, f)
        return x, words, words[-1][0] + words[-1][1]

    for pace in (1.10, 1.12, 1.14, 1.16, 1.18, 1.20, 1.22, 1.24):
        takes = [take(i, pace) for i in range(len(SCENES))]
        starts = schedule([tk[2] for tk in takes])
        if starts:
            break
    else:
        raise SystemExit('the script will not fit the picture at a natural reading pace')
    takes.append(take(len(SCENES), pace))
    starts.append(BASE_END + 0.5)
    placed = []
    for i, ((x, words, length), start) in enumerate(zip(takes, starts)):
        wav = f'{BUILD}/vo/line{i + 1}_read.wav'
        write_mono(wav, x)
        placed.append(dict(text=lines[i], start=start, words=words, audio=decode(wav, VO_CHAIN),
                           end=start + length, rate=f'google x{pace:.2f}'))
        print(f'  vo{i + 1}  {start:5.2f} → {start + length:5.2f}s  pace {pace:.2f}  {spoken(lines[i])}')
    return placed


def voice():
    """Every line placed. SYSPIN: performed to VO_PLAN, scheduled together at
    the gentlest pace that fits. Google: fitted per scene (fallback)."""
    os.makedirs(f'{BUILD}/vo', exist_ok=True)
    lines = [s[2] for s in SCENES] + [SIGN_OFF]
    placed = []
    if HUMAN_VO:
        return human_read(lines)
    if VOICE_ENGINE == 'google':
        return read_naturally(lines)
    if VOICE_ENGINE == 'syspin':
        strip = lambda w: ''.join(c for c in w if c not in '.,!?')
        for i, text in enumerate(lines):
            said = [w for p in VO_PLAN[i][1] for w in p[0].split()]
            assert [strip(w) for w in spoken(text).split()] == [strip(w) for w in said], \
                f'VO_PLAN {i + 1} does not say the line on screen'
        # Every line at every pace, then the schedule whose fastest line is
        # nearest natural (ties: least total speed-up). Exhaustive — it's small.
        import itertools
        FITS = (1.0, 1.02, 1.04, 1.06, 1.08, 1.1, 1.12, 1.14, 1.16, 1.18)
        takes_at = {(i, f): performed(i, f) for i in range(len(SCENES)) for f in FITS}
        best = None
        for combo in itertools.product(FITS, repeat=len(SCENES)):
            starts = schedule([takes_at[(i, f)][3] for i, f in enumerate(combo)])
            if starts:
                key = (max(combo), sum(combo))
                if best is None or key < best[0]:
                    best = (key, combo, starts)
        if best is None:
            raise SystemExit('the script will not fit the picture even at the fastest pace')
        _, combo, starts = best
        takes = [takes_at[(i, f)] for i, f in enumerate(combo)]
        takes.append(performed(len(SCENES), 1.0))
        starts.append(BASE_END + 0.5)
        for i, ((x, words, pace, length), start) in enumerate(zip(takes, starts)):
            wav = f'{BUILD}/vo/line{i + 1}_trim.wav'
            write_mono(wav, x)
            placed.append(dict(text=lines[i], start=start, words=words,
                               audio=decode(wav, VO_CHAIN), end=start + length,
                               rate=f'{VOICE_ENGINE} x{pace:.2f}'))
            print(f'  vo{i + 1}  {start:5.2f} → {start + length:5.2f}s  pace {pace:.2f}  {spoken(lines[i])}')
        return placed
    for i, text in enumerate(lines):
        if i < len(SCENES):
            w0, w1 = WINDOWS[i]
            start = w0 + (0.6 if i == 0 else 0.3)
            room = w1 - 0.25 - start
        else:
            start, room = BASE_END + 0.5, 3.4
        for tempo in (1.04, 1.08, 1.12, 1.16, 1.2):
            wav = f'{BUILD}/vo/line{i + 1}.wav'
            x = _google(spoken(text), wav, tempo)
            words, t0 = word_times(spoken(text), x)
            speech_end = words[-1][0] + words[-1][1]
            if speech_end <= room:
                break
        else:
            raise SystemExit(f'line {i + 1} will not fit its scene: {speech_end:.2f}s > {room:.2f}s')
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(t0 - 0.03, 0):.3f}', '-i', wav,
             '-af', 'afade=t=in:d=0.02', f'{wav[:-4]}_trim.wav'])
        placed.append(dict(text=text, start=start, words=words, audio=decode(f'{wav[:-4]}_trim.wav', VO_CHAIN),
                           end=start + speech_end, rate=f'google x{tempo}'))
        print(f'  vo{i + 1}  {start:5.2f} → {start + speech_end:5.2f}s  tempo {tempo}  {spoken(text)}')
    return placed


# ─────────────────────────────────────────────────────────────────────────────
#  SCORE — owned, seed-fixed, cut to the picture
# ─────────────────────────────────────────────────────────────────────────────

def _sos(kind, fc):
    return butter(2, fc, kind, fs=SR, output='sos')


def lp(x, fc):
    return sosfilt(_sos('low', fc), x)


def lp_sweep(x, fc, block=256):
    """Low-pass whose cutoff follows the per-sample array `fc`."""
    fc = np.broadcast_to(fc, x.shape)
    out, zi = np.empty_like(x), np.zeros((1, 2))
    for s in range(0, len(x), block):
        sos = _sos('low', float(min(np.mean(fc[s:s + block]), SR * 0.45)))
        out[s:s + block], zi = sosfilt(sos, x[s:s + block], zi=zi)
    return out


def hp(x, fc):
    return sosfilt(_sos('high', fc), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def reverb(x, seconds, rng, bright=3200.0):
    n = int(SR * seconds)
    out = []
    for _ in range(2):
        ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * seconds / 6.5))
        ir = lp(ir, bright)
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out.append(fftconvolve(x, ir)[:len(x)])
    return np.stack(out, 1)


def reverb2(x, seconds, rng, bright=3200.0):
    """Stereo hall: each channel through its own decorrelated IR."""
    n = int(SR * seconds)
    out = np.zeros_like(x)
    for c in range(2):
        ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * seconds / 6.5))
        ir = lp(ir, bright)
        ir[:int(SR * 0.012)] = 0                               # pre-delay
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out[:, c] = fftconvolve(x[:, c], ir)[:len(x)]
    return out


class Bus:
    """A stereo bus with a reverb send. put() takes a mono signal."""

    def __init__(self, total):
        self.N = int(SR * total)
        self.dry = np.zeros((self.N, 2))
        self.send = np.zeros((self.N, 2))

    def put(self, sig, t0, gain=1.0, pan=0.0, send=0.0, width=0.0):
        a = int(round(SR * t0))
        if a < 0:
            sig, a = sig[-a:], 0
        if a >= self.N or not len(sig):
            return
        sig = sig[:self.N - a] * gain
        l = math.cos((pan + 1) * math.pi / 4) * 1.414
        r = math.sin((pan + 1) * math.pi / 4) * 1.414
        L, R = sig * l, sig * r
        d = int(SR * 0.014 * width)
        if d:
            R = np.concatenate([np.zeros(d), R[:-d]])
        self.dry[a:a + len(sig), 0] += L
        self.dry[a:a + len(sig), 1] += R
        self.send[a:a + len(sig), 0] += L * send
        self.send[a:a + len(sig), 1] += R * send

    def render(self, rng, seconds=2.8, wet=0.32):
        return self.dry + reverb2(self.send, seconds, rng) * wet


def _env(n, att, rel, shape=2.0):
    e = np.ones(n)
    a, r = max(1, int(SR * att)), max(1, int(SR * rel))
    e[:a] = np.linspace(0, 1, a) ** shape
    e[-r:] *= np.linspace(1, 0, r) ** 1.5
    return e


def _vib_saw(f, n, rng, det=0.0, vib=0.004, rate=5.2):
    t = np.arange(n) / SR
    inst = f * (1 + det + vib * np.sin(2 * np.pi * rate * t + rng.random() * 6.28))
    ph = np.cumsum(inst) / SR + rng.random()
    return 2 * (ph % 1.0) - 1


# Chords, voiced low → high.
DM = [73.42, 110.0, 146.83, 174.61, 220.0]
BB = [58.27, 87.31, 116.54, 146.83, 174.61]
FM = [87.31, 130.81, 174.61, 220.0, 261.63]
CM = [65.41, 98.0, 130.81, 164.81, 196.0]
DMAJ = [73.42, 110.0, 146.83, 185.0, 220.0, 293.66]
CHORDS = [DM, BB, FM, CM, DM]


BED = 'assets/bgm_options/04_High_Impact_Epic_Alert.mp3'
DROP_AT = 32.8          # the bed's biggest hit (onset analysis) — goes under the logo


def bed(total):
    """The owner's chosen track, cut to the picture: its own opening to the
    beat before the logo, a quarter-second of nothing, then its drop."""
    reg = json.load(open('assets/LICENCES.json'))['tracks']
    row = next((r for r in reg if r['path'] == BED), {})
    if row.get('status') != 'allowed':
        print(f"  ! BED {BED} is '{row.get('status')}' in LICENCES.json — no licence on "
              f"record; a Content ID claim on this promo could not be answered")
    x = decode(BED)[int(SR * BED_OFFSET):]
    N = int(SR * total)
    out = np.zeros((N, 2))
    # The hold before the logo is a BREATH, not a hole: the bed dips fast and
    # keeps playing underneath. Cutting everything to silence read as a
    # dropout (measured -44dB) rather than as a moment of tension.
    cut = int(SR * BASE_END)
    dip0 = int(SR * (BASE_END - 0.16))
    a = x[:cut].copy()
    a[dip0:] *= np.linspace(1.0, 0.22, cut - dip0)[:, None] ** 1.5
    out[:cut] = a
    b = x[int(SR * (DROP_AT - 0.01)):][:N - int(SR * BASE_END)].copy()
    b[:int(SR * 0.004)] *= np.linspace(0, 1, int(SR * 0.004))[:, None]
    tail = int(SR * 1.6)
    b[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.5
    out[int(SR * BASE_END):int(SR * BASE_END) + len(b)] = b
    return out


def score(total):
    """The bed: dark D-minor opening, taiko from the kambala on, strings and a
    horn theme building through the ghats and yakshagana, a riser, a
    quarter-second of nothing, and D major under the logo."""
    rng = np.random.default_rng(SEED)
    bus = Bus(total)
    bounds = [0.0] + CUTS + [BASE_END]
    beat = (CUTS[1] - CUTS[0]) / 8
    end_music = BASE_END - 0.25                       # the suck-out

    # ── Pad strings: every scene, opening up.
    bright = [650, 1000, 1500, 2000, 2600]
    for k, chord in enumerate(CHORDS):
        t0, t1 = bounds[k], bounds[k + 1]
        n = int(SR * (t1 - t0 + 1.0))
        for f in chord:
            for det, pan in ((-0.004, -0.7), (0.0, 0.0), (0.0045, 0.7)):
                v = lp(_vib_saw(f, n, rng, det, 0.002), bright[k]) * _env(n, 0.5 if k else 1.4, 1.0)
                bus.put(v, t0 - (0.35 if k else 0), 0.05, pan, 0.45)

    # ── Choir "aah": formant-filtered voices an octave up. Enters in scene 1.
    def choir(f, n, open_=1.0):
        v = sum(_vib_saw(f, n, rng, d, 0.006) for d in (-0.006, 0.0, 0.006))
        form = (bp(v, 620, 820) + 0.55 * bp(v, 1050, 1300) * open_ +
                0.2 * bp(v, 2400, 2900) * open_ + 0.35 * lp(v, 450))
        return form / 3

    for k, chord in enumerate(CHORDS):
        t0 = bounds[k] + (2.4 if k == 0 else -0.3)
        n = int(SR * (bounds[k + 1] - t0 + 0.9))
        for j, f in enumerate(chord[1:]):
            bus.put(choir(f * 2, n, 0.5 + 0.12 * k) * _env(n, 0.9, 0.9), t0,
                    0.05 + 0.012 * k, (-0.5, 0.5)[j % 2], 0.7, 0.6)

    # ── Low pulse: 16ths on the cut grid, from the kambala.
    six = beat / 4
    for k in range(1, 5):
        t, j = bounds[k], 0
        while t < min(bounds[k + 1], end_music) - 1e-6:
            n = int(SR * six * 1.3)
            v = lp(saw(CHORDS[k][0] * 2, n) + 0.5 * saw(CHORDS[k][0], n), 500 + 220 * k)
            v *= np.exp(-np.arange(n) / (SR * 0.07))
            bus.put(v, t, 0.11 * (1.0 if j % 4 == 0 else 0.6), 0.0, 0.05)
            t += six
            j += 1

    # ── Heartbeat sub under the opening, quickening to the first cut.
    t, gap = 0.9, 1.1
    while t < bounds[1] - 0.3:
        for off, g in ((0, 1.0), (0.16, 0.6)):
            n = int(SR * 0.4)
            tt = np.arange(n) / SR
            v = np.sin(2 * np.pi * np.cumsum(48 + 30 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 9)
            bus.put(v, t + off, 0.35 * g * (0.6 + 0.4 * t / bounds[1]))
        t += gap
        gap = max(0.62, gap * 0.9)

    # ── Clock: the first line is about time.
    t, j = bounds[1] - beat / 2, 0
    ticks = []
    while t > 0.25:
        ticks.append(t)
        t -= beat / 2
    for j, t in enumerate(sorted(ticks)):
        n = int(SR * 0.09)
        tt = np.arange(n) / SR
        f = 2100 if j % 2 else 1650
        v = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 70) + \
            hp(rng.standard_normal(n), 3000) * np.exp(-tt * 300) * 0.4
        bus.put(v, t, 0.055, 0.3 if j % 2 else -0.3, 0.5)

    # ── Taiko ensemble.
    def taiko(g, t0, pan=0.0, pitch=1.0, big=False):
        n = int(SR * (1.4 if big else 0.9))
        tt = np.arange(n) / SR
        f = (44 if big else 56) * pitch + 110 * pitch * np.exp(-tt * 20)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * (3.2 if big else 5.5))
        skin = bp(rng.standard_normal(n), 120, 1100) * np.exp(-tt * 26) * 0.5
        slap = hp(rng.standard_normal(n), 2500) * np.exp(-tt * 180) * 0.25
        bus.put(np.tanh((body + skin + slap) * 1.8), t0, g, pan, 0.4)

    patterns = {1: [0, 3, 4, 6], 2: [0, 2, 3, 4, 6, 7], 3: list(range(8)), 4: list(range(8))}
    for k, pat in patterns.items():
        for bar in range(2):
            t_bar = bounds[k] + bar * 4 * beat
            taiko(0.42, t_bar, 0.0, 0.8, big=True)                   # o-daiko downbeat
            for b in pat:
                t = t_bar + b * beat / 2
                if t < end_music - 0.05:
                    acc = 1.0 if b in (0, 4) else 0.7
                    taiko((0.2 + 0.035 * k) * acc, t, (-0.35, 0.35)[b % 2], 1.0 + 0.1 * (b % 3))
            if k >= 3:                                                # 16th pickups
                for s in (3.5, 3.75):
                    taiko(0.14, t_bar + s * beat, 0.2, 1.3)
    t, step = BASE_END - 1.45, 0.13                                   # roll into the card
    while t < end_music - 0.03:
        u = (t - (BASE_END - 1.45)) / 1.2
        taiko(0.12 + 0.2 * u, t, rng.uniform(-.5, .5), 1.1 + 0.3 * u)
        step *= 0.87
        t += max(step, 0.034)

    # ── Strings ostinato: 8ths in the ghats, 16ths from the yakshagana on.
    for k in (2, 3, 4):
        notes = [f * 2 for f in CHORDS[k][1:4]]
        seq = [0, 1, 2, 1, 2, 0, 1, 2]
        dt = beat / 2 if k == 2 else beat / 4
        t, j = bounds[k], 0
        while t < min(bounds[k + 1], end_music) - 1e-6:
            f = notes[seq[j % 8]] * (2 if k == 4 and (j // 8) % 2 else 1)
            n = int(SR * dt * 1.6)
            v = lp(saw(f, n, rng.random()) + saw(f * 1.004, n, rng.random()), 3200)
            v *= np.exp(-np.arange(n) / (SR * 0.11)) * (1 - np.exp(-np.arange(n) / (SR * 0.004)))
            bus.put(v, t, 0.045, (-0.45, 0.45)[j % 2], 0.35)
            t += dt
            j += 1

    # ── Horn theme over the last two scenes.
    def horn(f, t0, dur, g):
        n = int(SR * (dur + 0.35))
        tt = np.arange(n) / SR
        v = sum(_vib_saw(f, n, rng, d, 0.003, 5.0) for d in (-0.003, 0.0, 0.003))
        cut = 350 + 2300 * (1 - np.exp(-tt / 0.12)) * np.exp(-np.maximum(tt - dur, 0) * 6)
        v = np.tanh(lp_sweep(v, cut) * 1.2) * _env(n, 0.07, 0.35)
        bus.put(v, t0, g, -0.15, 0.55, 0.5)
        bus.put(v, t0, g * 0.5, 0.15, 0.55)

    theme = {3: [(196.0, 1), (261.63, 1.5), (293.66, .5), (329.63, 2), (293.66, 1), (261.63, 1), (293.66, 1)],
             4: [(293.66, 1), (349.23, 1.5), (392.0, .5), (440.0, 3), (392.0, .5), (349.23, .5), (440.0, 1)]}
    for k, line in theme.items():
        t = bounds[k]
        for f, b in line:
            dur = min(b * beat, end_music - t) - 0.04
            if dur > 0.05:
                horn(f, t, dur, 0.07)
                horn(f / 2, t, dur, 0.05)
            t += b * beat

    # ── Braam on every cut.
    def braam(chord, t0, g, dur=2.8):
        n = int(SR * dur)
        tt = np.arange(n) / SR
        x = sum(_vib_saw(f / 2, n, rng, d, 0.001) for f in chord[:3] for d in (-0.003, 0.003))
        mixk = np.exp(-tt * 2.2)
        x = lp(x, 3000) * mixk + lp(x, 300) * (1 - mixk)
        x = np.tanh(x * 1.1) * np.exp(-tt * 1.1) * (1 - np.exp(-tt * 250))
        bus.put(x, t0, g, 0.0, 0.6, 0.8)

    for k, t in enumerate(CUTS):
        braam(CHORDS[k + 1], t, 0.2)

    # ── Riser into the end card.
    r0, r1 = BASE_END - 3.6, BASE_END - 0.02
    n = int(SR * (r1 - r0))
    u = np.arange(n) / n
    noise = rng.standard_normal(n)
    riser = (lp_sweep(noise, 700 + 8000 * u ** 2) - lp_sweep(noise, 250 + 1800 * u)) * u ** 2
    gliss = sum(np.sin(2 * np.pi * np.cumsum(f0 * (1 + 3 * u ** 2)) / SR) for f0 in (147, 220, 294)) / 3
    trem = 0.55 + 0.45 * np.sin(2 * np.pi * np.cumsum(3 + 22 * u) / SR)
    bus.put((riser * 0.8 + gliss * u ** 2.5 * 0.35) * trem, r0, 0.33, 0.0, 0.4)

    # ── The landing.
    braam(DMAJ, BASE_END, 0.34, 4.0)
    for p, pan in ((0.75, 0.0), (0.9, -0.5), (1.0, 0.5)):
        taiko(0.5, BASE_END + rng.uniform(0, .015), pan, p, big=True)
    n = int(SR * (total - BASE_END + 0.4))
    for f in DMAJ:
        for det, pan in ((-0.003, -0.6), (0.003, 0.6)):
            v = lp(_vib_saw(f, n, rng, det, 0.002), 2400) * _env(n, 0.2, 1.8)
            bus.put(v, BASE_END, 0.05, pan, 0.6)
    for j, f in enumerate(DMAJ[2:]):
        bus.put(choir(f * 2, n, 1.0) * _env(n, 0.35, 1.8), BASE_END + 0.05, 0.08, (-0.5, 0.5)[j % 2], 0.8, 0.6)
    for f in (293.66, 369.99, 440.0):
        horn(f, BASE_END + 0.02, 2.4, 0.06)
    for j, f in enumerate((587.33, 739.99, 880.0, 1174.66)):
        m = int(SR * 2.4)
        tt = np.arange(m) / SR
        bell = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 4)
                + 0.15 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 8))
        bell *= np.exp(-tt * 1.6) * (1 - np.exp(-tt * 800))
        bus.put(bell, BASE_END + 0.35 + 0.11 * j, 0.075, (-0.45, 0.45)[j % 2], 0.7)

    out = bus.render(rng, 2.8, 0.34)
    a, b = int(SR * end_music), int(SR * BASE_END)
    f = int(SR * 0.025)
    out[a - f:a] *= np.linspace(1, 0, f)[:, None]
    out[a:b] *= 0.04                                  # near-silence; the tail breathes
    tail = int(SR * 0.7)
    out[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.6
    return out / (np.max(np.abs(out)) + 1e-9) * 0.9


# ─────────────────────────────────────────────────────────────────────────────
#  SOUND DESIGN — the hits, swooshes and sparkle, synthesised and owned
# ─────────────────────────────────────────────────────────────────────────────

def sound_design(total):
    rng = np.random.default_rng(SEED + 5)
    bus = Bus(total)

    def impact(t, g, depth=1.0):
        n = int(SR * 2.4)
        tt = np.arange(n) / SR
        sub = np.sin(2 * np.pi * np.cumsum(28 + 70 * depth * np.exp(-tt * 5)) / SR) * np.exp(-tt * 1.6)
        thump = np.sin(2 * np.pi * 110 * tt) * np.exp(-tt * 14) * 0.6
        crack = bp(rng.standard_normal(n), 700, 5500) * np.exp(-tt * 45) * 0.8
        ring = sum(np.sin(2 * np.pi * fr * tt) * np.exp(-tt * (2.5 + k)) / (k + 1)
                   for k, fr in enumerate((196, 331, 523, 787, 1109))) * 0.18
        x = np.tanh((sub * 1.3 + thump + crack + ring) * 1.5)
        bus.put(x, t, g, 0.0, 0.35, 0.3)

    def whoosh(center, dur=0.9, g=0.5, direction=1):
        n = int(SR * dur)
        u = np.arange(n) / n
        bell = np.sin(np.pi * u) ** 2.4
        noise = rng.standard_normal(n)
        air = lp_sweep(noise, 500 + 6500 * bell) - lp_sweep(noise, 180 + 900 * bell)
        rumble = lp(rng.standard_normal(n), 160) * bell * 1.5
        x = (air * bell + rumble)
        pan = (u * 2 - 1) * direction
        L = x * np.cos((pan + 1) * np.pi / 4)
        R = x * np.sin((pan + 1) * np.pi / 4)
        a = int(SR * (center - dur * 0.55))
        seg = np.stack([L, R], 1)[:bus.N - a] * g * 1.4
        bus.dry[a:a + len(seg)] += seg
        bus.send[a:a + len(seg)] += seg * 0.25

    def reverse_swell(t_hit, dur=1.3, g=0.28):
        n = int(SR * dur)
        tt = np.arange(n) / SR
        tail = lp(rng.standard_normal(n), 3500) * np.exp(-tt * 3.2)
        tail += sum(np.sin(2 * np.pi * f * tt) for f in (147, 220, 294)) * np.exp(-tt * 2.5) * 0.08
        bus.put(tail[::-1] * np.linspace(0.2, 1, n), t_hit - dur, g, 0.0, 0.3, 0.7)

    def shimmer(t, dur=0.8, g=0.1, lo=2500, hi=7500):
        for j in range(28):
            tj = t + dur * j / 28
            f = lo + (hi - lo) * (j / 28) + rng.uniform(-300, 300)
            m = int(SR * 0.35)
            tt = np.arange(m) / SR
            v = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 14) * (1 - np.exp(-tt * 2000))
            bus.put(v, tj, g * (0.5 + 0.5 * math.sin(math.pi * j / 28)), rng.uniform(-.8, .8), 0.8)

    def digital(t, dur=0.45, g=0.07):
        k = t
        while k < t + dur:
            m = int(SR * rng.uniform(0.02, 0.05))
            tt = np.arange(m) / SR
            f = rng.choice([880, 1320, 1760, 2640])
            v = np.sign(np.sin(2 * np.pi * f * tt)) * np.exp(-tt * 40)
            bus.put(lp(v, 6000), k, g, rng.uniform(-.6, .6), 0.3)
            k += m / SR + rng.uniform(0.01, 0.04)

    def tock(t, g=0.12, f=900):
        m = int(SR * 0.12)
        tt = np.arange(m) / SR
        v = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 60) + np.sin(2 * np.pi * f * 1.5 * tt) * np.exp(-tt * 90) * 0.4
        bus.put(v, t, g, 0.0, 0.3)

    impact(0.0, 0.9, 1.2)                                  # frame 0, with the bed's hit
    shimmer(0.12, 0.9, 0.08)                               # 2050 lands
    whoosh(2.75, 0.8, 0.35, -1)                            # title leaves
    for k, t in enumerate(CUTS):
        reverse_swell(t)
        whoosh(t, 0.9, 0.55, (1, -1)[k % 2])
        impact(t, 0.55)
        tock(t + 0.1, 0.07, 1100)                          # kicker lands
    digital(CUTS[-1] + 0.1)                                # the phone wakes

    def chime(t, g=0.16):
        for j, f in enumerate((1318.5, 1760.0)):
            m = int(SR * 0.6)
            tt = np.arange(m) / SR
            v = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) \
                * np.exp(-tt * 7) * (1 - np.exp(-tt * 1500))
            bus.put(v, t + 0.09 * j, g, (-0.2, 0.2)[j], 0.5)

    chime(CUTS[-1] + BEAT * 2)                             # the real headlines land
    chime(CUTS[-1] + BEAT * 3, 0.13)
    # A rising sub bridges the hold before the logo, so the dip reads as a
    # breath rather than as the audio dropping out.
    n = int(SR * 1.0)
    tt = np.arange(n) / SR
    bus.put(np.sin(2 * np.pi * np.cumsum(36 + 18 * tt) / SR) * (tt / 1.0) ** 1.6,
            BASE_END - 1.0, 0.3, 0.0, 0.15)
    impact(BASE_END, 1.0, 1.4)                             # the logo
    shimmer(BASE_END + 0.3, 0.6, 0.09, 3000, 8000)
    tock(BASE_END + 0.6, 0.08, 1300)                       # rule draws
    shimmer(BASE_END + 1.1, 0.8, 0.1, 2000, 6500)          # the name's sweep
    whoosh(BASE_END + 1.05, 0.5, 0.18)                     # CTA pops
    tock(BASE_END + 1.1, 0.1, 700)
    out = bus.render(rng, 3.0, 0.3)
    return out / (np.max(np.abs(out)) + 1e-9) * 0.95


# ─────────────────────────────────────────────────────────────────────────────
#  MIX
# ─────────────────────────────────────────────────────────────────────────────

def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


VOICE_OVER_MUSIC_DB = 8.0          # trailer mix: the bed is big, the voice still reads


def mix(total, vo):
    N = int(SR * total)
    rng = np.random.default_rng(SEED + 1)
    voice_bus = np.zeros((N, 2))
    for v in vo:
        a = int(SR * v['start'])
        seg = v['audio'][:N - a]
        voice_bus[a:a + len(seg)] += seg
    if not HUMAN_VO:                   # a synthetic read needs a room; a real one has its own
        voice_bus += reverb2(voice_bus, 0.8, rng, 2600) * 0.07
    speech = np.abs(voice_bus).max(1) > 1e-3
    voice_bus *= 10 ** ((-16 - rms_db(voice_bus[speech])) / 20)

    music = bed(total)
    music *= 10 ** ((-12.0 - rms_db(music[:int(SR * BASE_END)])) / 20)

    # Duck to a TARGET, not by a fixed amount: under words the bed is pulled to
    # VOICE_OVER_MUSIC_DB + 3 below the voice however loud that bar of the track
    # is, and left at full size in the gaps. Held and smoothed, so it breathes
    # rather than pumps.
    key = np.abs(voice_bus).max(1) > 10 ** (-40 / 20)
    key = maximum_filter1d(key.astype(float), int(SR * 0.3))
    shift = int(SR * 0.08)
    key = np.concatenate([key[shift:], np.zeros(shift)])
    win = int(SR * 0.15)
    m_env = np.sqrt(np.convolve(music.mean(1) ** 2, np.ones(win) / win, 'same'))
    m_env = maximum_filter1d(m_env, int(SR * 0.4))
    target = -16.0 - (VOICE_OVER_MUSIC_DB + 3)
    need = np.clip(target - 20 * np.log10(m_env + 1e-9), -18.0, -3.0)
    a = math.exp(-1 / (SR * 0.1))
    gain_db = lfilter([1 - a], [1, -a], key * need)
    gain_db[int(SR * (BASE_END - 0.05)):int(SR * (BASE_END + 0.4))] = 0
    duck = (10 ** (gain_db / 20))[:, None]
    music *= duck

    fx = sound_design(total)
    fx *= 10 ** ((-9.0 - 20 * np.log10(np.max(np.abs(fx)))) / 20)     # under the bed's own hits
    fx *= 10 ** (gain_db * 1.1 / 20)[:, None]

    amb = np.zeros((N, 2))
    for i, (clip, *_rest) in enumerate(SCENES):
        x = decode(clip, f'atempo={SPEEDS[i]},highpass=f=110,lowpass=f=9000')[:int(SR * CLIP_LENS[i])]
        f = int(SR * XF)
        x[:f] *= np.linspace(0, 1, f)[:, None]
        x[-f:] *= np.linspace(1, 0, f)[:, None]
        a0 = int(SR * STARTS[i])
        amb[a0:a0 + len(x)] += x[:N - a0]
    amb *= 10 ** ((-32 - rms_db(amb)) / 20) * duck

    if NO_VOICE:
        # The duck stays: the gaps are exactly where the narration belongs.
        print('  no-voice bed: music + sound design + location sound, ducked for the VO')
        return music + fx + amb
    bus = voice_bus + music + fx + amb
    speech = np.abs(voice_bus).max(1) > 10 ** (-35 / 20)
    margin = rms_db(voice_bus[speech]) - rms_db((music + fx)[speech])
    gaps = ~speech
    gaps[int(SR * BASE_END):] = False
    print(f'  levels  voice {rms_db(voice_bus[speech]):.1f}  music in gaps {rms_db(music[gaps]):.1f}  '
          f'under voice {rms_db(music[speech]):.1f}  fx peak {20 * np.log10(np.abs(fx).max()):.1f} dBFS')
    print(f'  voice over bed under speech: {margin:+.1f} dB (floor {VOICE_OVER_MUSIC_DB})')
    if margin < VOICE_OVER_MUSIC_DB:
        raise SystemExit('voice would not sit clear of the music')
    return bus


def write_mono(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_f32(path, x):
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', '-',
         '-c:a', 'pcm_f32le', path], input=x.astype('<f4').tobytes())


def _integrated(path, af):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', f'{af},ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    s = r[r.rindex('Summary:'):]
    return float(s.split('I:')[1].split('LUFS')[0]), float(s.split('Peak:')[1].split('dBFS')[0])


GLUE = 'acompressor=threshold=-18dB:ratio=2:attack=25:release=250:knee=6'


def master(src, dst):
    """Glue, gain to Limits.lufs, then a 4x-oversampled limiter at the true-peak
    ceiling. Two passes so the limiter's own loss is measured, not guessed."""
    # Headroom under the ceiling for what AAC adds back: the promo opens on a
    # hit at sample 0, and the encoder overshoots an instant transient. The
    # 10ms fade gives that first hit an attack the encoder can follow.
    ceiling = 10 ** ((Limits.true_peak_dbtp - 1.2) / 20)
    lim = (f'aresample=192000,alimiter=limit={ceiling:.4f}:attack=1:release=60:level=0,'
           f'aresample={SR},afade=t=in:d=0.01')
    gain = Limits.lufs - _integrated(src, GLUE)[0]
    for _ in range(3):
        chain = f'{GLUE},volume={gain:.2f}dB,{lim}'
        i_lufs, _tp = _integrated(src, chain)
        if abs(i_lufs - Limits.lufs) < 0.2:
            break
        gain += Limits.lufs - i_lufs
    run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', chain, '-c:a', 'pcm_s16le', dst])


# ─────────────────────────────────────────────────────────────────────────────
#  TYPE
# ─────────────────────────────────────────────────────────────────────────────

_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[k]


def text_layer(text, fnt, fill, shadow=0.6, blur=7, pad=30, tracking=0):
    """RGBA image of `text` with a soft shadow. Returns (img, baseline_y, pad)."""
    asc, desc = fnt.getmetrics()
    if tracking:
        widths = [fnt.getlength(ch) for ch in text]
        tw = int(sum(widths) + tracking * (len(text) - 1))
    else:
        tw = int(fnt.getlength(text))
    w, h = tw + pad * 2, asc + desc + pad * 2
    glyphs = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glyphs)
    if tracking:
        x = pad
        for ch, cw in zip(text, widths):
            d.text((x, pad + asc), ch, font=fnt, fill=fill, anchor='ls')
            x += cw + tracking
    else:
        d.text((pad, pad + asc), text, font=fnt, fill=fill, anchor='ls')
    if shadow:
        a = glyphs.split()[3].filter(ImageFilter.GaussianBlur(blur))
        a = a.point(lambda v: int(v * shadow))
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sh.putalpha(a)
        base = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        base.alpha_composite(sh, (0, 3))
        base.alpha_composite(glyphs)
        glyphs = base
    return glyphs, pad + asc, pad


def with_alpha(img, k):
    if k >= 0.999:
        return img
    r, g, b, a = img.split()
    return Image.merge('RGBA', (r, g, b, a.point(lambda v: int(v * max(k, 0)))))


def put_layer(canvas, img, x, y, alpha=1.0):
    if alpha <= 0.003:
        return
    canvas.alpha_composite(with_alpha(img, alpha), (int(round(x)), int(round(y))))


class Subtitle:
    """One spoken line, revealed word by word on the engine's own timings."""
    SIZE, LEAD, X = 52, 78, SAFE_L + 24

    def __init__(self, vo, kicker, t_out):
        self.t_in, self.t_out = vo['start'], t_out
        fnt = font(FONT_KN, self.SIZE)
        marked = [ln.split() for ln in vo['text'].split('|')]
        words = [w.lstrip('*') for ln in marked for w in ln]
        hold = [w.startswith('*') for ln in marked for w in ln]
        spoken = vo['words']
        strip = lambda s: ''.join(ch for ch in s if ch not in '.,!?—…')
        self.matched = [strip(w) for w in words] == [strip(w[2]) for w in spoken]
        if self.matched:
            times = [(vo['start'] + o, d) for o, d, _ in spoken]
        else:  # fall back to spreading the words over the speech
            span = vo['end'] - vo['start']
            times = [(vo['start'] + span * i / len(words), span / len(words))
                     for i in range(len(words))]
        space = fnt.getlength(' ')
        max_w = SAFE_R - self.X - 10
        lines = []
        for ln in marked:                      # the script's own phrase breaks,
            cur, cur_w = [], 0                 # wrapped again only if one overflows
            for w in (x.lstrip('*') for x in ln):
                ww = fnt.getlength(w)
                if cur and cur_w + space + ww > max_w:
                    lines.append(cur)
                    cur, cur_w = [], 0
                cur_w += (space if cur else 0) + ww
                cur.append(w)
            lines.append(cur)
        if len(lines) != len(marked):
            raise SystemExit(f'a phrase line overflows the safe width and would re-wrap: {vo["text"]}')
        n_lines = len(lines)
        bottom = SAFE_B - 60
        top = bottom - n_lines * self.LEAD
        self.words = []
        k = 0
        for li, line in enumerate(lines):
            x = self.X
            base_y = top + (li + 1) * self.LEAD - 22
            for w in line:
                white, by, pad = text_layer(w, fnt, (255, 255, 255, 255), 0.75, 8)
                gold, _, _ = text_layer(w, fnt, GOLD + (255,), 0.75, 8)
                self.words.append(dict(white=white, gold=gold, x=x - pad, y=base_y - by,
                                       t=times[k][0], d=times[k][1], hold=hold[k]))
                x += fnt.getlength(w) + space
                k += 1
        self.rule = (SAFE_L, top + 14, bottom - 4)
        self.kicker, kb, kp = text_layer(kicker, font(FONT_KN, 32), GOLD + (255,), 0.85, 6)
        self.kicker_pos = (self.X - kp, top - 18 - kb)

    def draw(self, cv, t):
        if not (self.t_in - 0.3 <= t <= self.t_out + 0.01):
            return
        out = 1 - ease_io((t - (self.t_out - 0.3)) / 0.3)
        grow = ease_out((t - (self.t_in - 0.3)) / 0.45)
        x, y0, y1 = self.rule
        if grow * out > 0:
            d = ImageDraw.Draw(cv)
            yb = y0 + (y1 - y0) * grow
            d.rectangle([x, y0, x + 5, yb], fill=GOLD + (int(255 * out),))
        ka = ease_out((t - (self.t_in - 0.25)) / 0.35) * out
        put_layer(cv, self.kicker, self.kicker_pos[0] + 12 * (1 - ka), self.kicker_pos[1], ka)
        for w in self.words:
            u = (t - (w['t'] - 0.08)) / 0.18
            if u <= 0:
                continue
            a = ease_out(u) * out
            dy = 16 * (1 - ease_out(u))
            hot = 1.0 if w['hold'] else 1 - ease_io((t - (w['t'] + w['d'] + 0.05)) / 0.25)
            put_layer(cv, w['white'], w['x'], w['y'] + dy, a * (1 - hot))
            put_layer(cv, w['gold'], w['x'], w['y'] + dy, a * hot)


def logo_circle(size):
    lg = Image.open('assets/logo_clean_circle.png').convert('RGBA')
    return lg.resize((size, size), Image.Resampling.LANCZOS)


def build_bug():
    """Top-left brand bug + the synthetic-imagery label, inside the safe box."""
    cv = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lg = logo_circle(92)
    sh = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((24, 26, 116, 118), fill=(0, 0, 0, 150))
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), (SAFE_L - 24, SAFE_T + 10 - 24))
    cv.alpha_composite(lg, (SAFE_L, SAFE_T + 10))
    name, nb, np_ = text_layer(Brand.name, font(FONT_KN, 40), (255, 255, 255, 255), 0.8, 7)
    put_layer(cv, name, SAFE_L + 92 + 18 - np_, SAFE_T + 10 + 50 - nb)
    lab_f = font(FONT_KN, 22)
    lw = int(lab_f.getlength(AI_LABEL))
    x0, y0 = SAFE_L + 92 + 18, SAFE_T + 10 + 62
    pill = Image.new('RGBA', (lw + 28, 38), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, lw + 27, 37), 19, fill=rgb(C.ink_900) + (175,),
                                           outline=GOLD + (120,), width=1)
    cv.alpha_composite(pill, (x0, y0))
    ImageDraw.Draw(cv).text((x0 + 14, y0 + 19), AI_LABEL, font=lab_f,
                            fill=(255, 255, 255, 225), anchor='lm')
    return cv


def build_notification(line, stamp):
    """A push notification from the channel, carrying a real headline."""
    w = SAFE_R - SAFE_L - 60
    head_f = font(FONT_KN, 30)
    body_f = font(FONT_KN, 36)
    avail = w - (26 + 84 + 24) - 40                  # logo column + right padding
    while body_f.getlength(line) > avail and body_f.size > 26:
        body_f = font(FONT_KN, body_f.size - 2)
    h = 150
    img = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 38, w + 30, h + 38), 34, fill=(0, 0, 0, 150))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 30, w + 30, h + 30), 34, fill=rgb(C.ink_850) + (228,),
                        outline=GOLD + (110,), width=2)
    img.alpha_composite(logo_circle(84), (56, 30 + (h - 84) // 2))
    x = 56 + 84 + 24
    d.text((x, 30 + 50), Brand.name, font=head_f, fill=GOLD + (255,), anchor='ls')
    nw = head_f.getlength(Brand.name)
    d.text((x + nw + 14, 30 + 50), f'·  {stamp}', font=font(FONT_KN, 24),
           fill=(255, 255, 255, 150), anchor='ls')
    d.text((x, 30 + 112), line, font=body_f, fill=(255, 255, 255, 255), anchor='ls')
    return img


def build_title():
    """The hook: ಕರಾವಳಿ / 2050."""
    big, bb, bp_ = text_layer('ಕರಾವಳಿ', font(FONT_KN_SERIF, 176), (255, 255, 255, 255), 0.7, 14)
    yr, yb, yp = text_layer('2050', font(FONT_LATIN_BOLD, 104), GOLD + (255,), 0.75, 10, tracking=14)
    rule_w = 300
    w = max(big.width, yr.width)
    h = big.height + yr.height - 40
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    img.alpha_composite(big, ((w - big.width) // 2, 0))
    img.alpha_composite(yr, ((w - yr.width) // 2, big.height - 40))
    d = ImageDraw.Draw(img)
    ry = big.height - 34
    for side in (-1, 1):
        x_in = w // 2 + side * (yr.width // 2 - 10)
        x_out = x_in + side * (rule_w // 2 - 40)
        d.line([(min(x_in, x_out), ry + yr.height // 2 - 8), (max(x_in, x_out), ry + yr.height // 2 - 8)],
               fill=GOLD + (200,), width=3)
    return img


# ─────────────────────────────────────────────────────────────────────────────
#  PICTURE
# ─────────────────────────────────────────────────────────────────────────────

GRADE = ('colorbalance=rs=-0.02:bs=0.035:rh=0.035:gh=0.008:bh=-0.03,'
         'eq=contrast=1.05:saturation=1.06:gamma=0.98,unsharp=5:5:0.35:5:5:0')


# The owner's agency mark sits over the Gemini ✦ (same place in every clip:
# centre 900,1740, ~75px). Pasted onto the SOURCE frame, so it rides every
# push-in, whip and zoom exactly as the star did. Disclosure is not carried by
# the star: `ಎಐ ರಚಿತ ದೃಶ್ಯಗಳು` is on screen for the whole promo.
COVER_WATERMARK = False      # owner, 2026-09-22: not needed — the Gemini ✦ stays
WM_CENTRE = (900, 1740)
EMBLEM = 'assets/bark_brand_emblem_cutout.png'      # background removed
EMBLEM_W, EMBLEM_ANCHOR = 150, (69, 68)             # anchor: fully opaque over the star


def build_emblem():
    em = Image.open(EMBLEM).convert('RGBA')
    em = em.resize((EMBLEM_W, round(em.height * EMBLEM_W / em.width)), Image.Resampling.LANCZOS)
    pad = 24
    out = Image.new('RGBA', (em.width + pad * 2, em.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new('RGBA', out.size, (0, 0, 0, 0))
    sh.putalpha(Image.new('L', out.size, 0))
    a = Image.new('L', out.size, 0)
    a.paste(em.getchannel('A'), (pad, pad + 3))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.65)))
    out.alpha_composite(sh)
    out.alpha_composite(em, (pad, pad))
    x = WM_CENTRE[0] - EMBLEM_ANCHOR[0] - pad
    y = WM_CENTRE[1] - EMBLEM_ANCHOR[1] - pad
    return out, (x, y)


_EMBLEM = None


_SHADE = None


def over_watermark(frame):
    """Shade the footage (vignette + subtitle scrim), THEN lay the emblem on
    it — so the mark stays at full brightness instead of being dimmed with the
    picture under it."""
    global _EMBLEM, _SHADE
    if _EMBLEM is None:
        _EMBLEM = build_emblem()
        _SHADE = vignette() * scrim()
    shaded = np.clip(np.asarray(frame, np.float32) * _SHADE, 0, 255).astype(np.uint8)
    if not COVER_WATERMARK:
        return Image.fromarray(shaded)
    img, pos = _EMBLEM
    f = Image.fromarray(shaded).convert('RGBA')
    f.alpha_composite(img, pos)
    return f.convert('RGB')


class Reader:
    def __init__(self, path, speed=SPEEDS[0]):
        slow = (f'setpts=PTS/{speed},'
                f'framerate=fps={FPS}:interp_start=0:interp_end=255:scene=100,')
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', slow + GRADE,
                                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.n, self.last = -1, None

    def frame(self, idx):
        while self.n < idx:
            raw = self.p.stdout.read(W * H * 3)
            if len(raw) < W * H * 3:
                break
            self.last = over_watermark(Image.frombuffer('RGB', (W, H), raw, 'raw', 'RGB', 0, 1))
            self.n += 1
        return self.last

    def close(self):
        self.p.kill()
        self.p.stdout.close()
        self.p.wait()


DRIFT = [(0.0, -0.02), (0.0, 0.03), (0.02, 0.0), (0.0, -0.03), (0.0, 0.0)]


def framed(img, i, local, extra=1.0, dx=0.0):
    """Slow push-in, sub-pixel exact (PIL resize with a float box)."""
    u = local / CLIP_LENS[i]
    s = (1.0 + 0.075 * ease_io(u)) * extra
    ddx, ddy = DRIFT[i]
    cx = W / 2 + ddx * W * u
    cy = H / 2 + ddy * H * u
    bw, bh = W / s, H / s
    x0 = min(max(cx - bw / 2, 0), W - bw)
    y0 = min(max(cy - bh / 2, 0), H - bh)
    out = img.resize((W, H), Image.Resampling.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh))
    if dx:
        cv = Image.new('RGB', (W, H))
        cv.paste(out, (int(round(dx)), 0))
        return cv
    return out


def scrim():
    """Lower-third darkening so white type holds over any picture."""
    y = np.arange(H, dtype=np.float32)
    k = np.clip((y - 820) / 560, 0, 1) ** 1.3 * 0.74
    k[int(SAFE_B + 80):] *= np.linspace(1, 0.6, H - int(SAFE_B + 80))
    return (1 - k)[:, None, None]


def vignette():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    v = 1 - 0.38 * np.clip(r - 0.35, 0, 1) ** 1.6
    return v[..., None].astype(np.float32)


def leak(p):
    """A warm light leak drifting across the frame."""
    y, x = np.mgrid[0:H:4, 0:W:4]
    cx = -0.2 * W + 1.4 * W * p
    g = np.exp(-(((x - cx) / (W * 0.45)) ** 2 + ((y - H * 0.45) / (H * 0.5)) ** 2))
    g = np.repeat(np.repeat(g, 4, 0), 4, 1)[:H, :W]
    col = np.array([255, 196, 110], np.float32)
    return g[..., None] * col * math.sin(math.pi * p)


def hblur(arr, k):
    """Horizontal box blur of length k (motion blur along the whip)."""
    if k < 2:
        return arr
    pad = np.pad(arr, ((0, 0), (k, k), (0, 0)), mode='edge')
    cs = np.cumsum(pad, axis=1, dtype=np.float64)
    out = (cs[:, k:-k] - cs[:, :-2 * k]) / k
    return out.astype(np.float32)


def transition(kind, a_at, b_at, p):
    """a_at / b_at: callables (extra_zoom, dx) → Image, for outgoing / incoming."""
    e = ease_io(p)
    if kind == 'whip':
        # One composite at the true offset, then a real directional blur whose
        # length follows the speed of the move — no discrete ghost copies.
        dx = -W * e
        A = np.asarray(a_at(1.0, dx), np.float32)
        B = np.asarray(b_at(1.0, dx + W), np.float32)
        edge = int(round(dx + W))
        out = A.copy()
        out[:, max(edge, 0):] = B[:, max(edge, 0):]
        speed = 6 * p * (1 - p)                     # derivative of smoothstep
        return hblur(out, int(W * speed * 0.09))
    if kind == 'zoom':
        sub = 4
        acc = np.zeros((H, W, 3), np.float32)
        for s in range(sub):
            q = min(1, max(0, p + (s - sub / 2) * 0.03))
            A = np.asarray(a_at(1 + 0.35 * ease_io(q) ** 2, 0), np.float32)
            B = np.asarray(b_at(1.25 - 0.25 * ease_out(q), 0), np.float32)
            acc += A * (1 - ease_io(q)) + B * ease_io(q)
        out = acc / sub
        return out + 255 * 0.35 * math.sin(math.pi * p) ** 2
    # leak
    A = np.asarray(a_at(1.0, 0), np.float32)
    B = np.asarray(b_at(1.0, 0), np.float32)
    return A * (1 - e) + B * e + leak(p)


def end_card(bg_src):
    """Returns draw(τ) → RGB Image for the closing lockup."""
    bg = bg_src.filter(ImageFilter.GaussianBlur(38))
    y, x = np.mgrid[0:H, 0:W]
    top, bot = np.array(rgb(C.ink_800), np.float32), np.array(rgb(C.ink_950), np.float32)
    ground = top + (bot - top) * (y / H)[..., None]
    arr = ground * 0.8 + np.asarray(bg, np.float32) * 0.12
    glow = np.exp(-(((x - W / 2) / 460) ** 2 + ((y - 630) / 520) ** 2))[..., None]
    arr = arr + glow * np.array(rgb(C.gold_600), np.float32) * 0.16
    arr *= vignette()
    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')

    L = 300
    ring = Image.new('RGBA', (L + 80, L + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    d.ellipse((40 - 8, 40 - 8, 40 + L + 8, 40 + L + 8), outline=GOLD + (255,), width=4)
    halo = Image.new('RGBA', ring.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((24, 24, L + 56, L + 56), fill=GOLD + (140,))
    halo = halo.filter(ImageFilter.GaussianBlur(26))
    logo = Image.new('RGBA', ring.size, (0, 0, 0, 0))
    logo.alpha_composite(halo)
    logo.alpha_composite(logo_circle(L), (40, 40))
    logo.alpha_composite(ring)

    name_f = font(FONT_KN_SERIF, 112)
    while name_f.getlength(Brand.name) > 620:
        name_f = font(FONT_KN_SERIF, name_f.size - 4)
    name, nb, _ = text_layer(Brand.name, name_f, (255, 255, 255, 255), 0.0)
    # Gold gradient fill, then a shadow under it.
    grad = np.linspace(0, 1, name.height)[:, None, None]
    col = (1 - grad) * np.array(GOLD_HI, np.float32) + grad * np.array(rgb(C.gold_500), np.float32)
    rgba = np.dstack([np.broadcast_to(col, (name.height, name.width, 3)),
                      np.asarray(name.split()[3], np.float32)[..., None]])
    name_gold = Image.fromarray(rgba.astype(np.uint8), 'RGBA')
    sh = Image.new('RGBA', name.size, (0, 0, 0, 0))
    sh.putalpha(name.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .7)))
    name_img = Image.new('RGBA', name.size, (0, 0, 0, 0))
    name_img.alpha_composite(sh, (0, 4))
    name_img.alpha_composite(name_gold)
    name_mask = np.asarray(name.split()[3], np.float32) / 255

    tag, tb, _ = text_layer(Brand.tagline, font(FONT_KN, 44), (255, 255, 255, 235), 0.7, 6)
    cta_f = font(FONT_KN, 36)
    cta_txt = f'ಫಾಲೋ ಮಾಡಿ   {Brand.handle}'
    cw = int(cta_f.getlength(cta_txt)) + 72
    cta = Image.new('RGBA', (cw + 40, 118), (0, 0, 0, 0))
    ImageDraw.Draw(cta).rounded_rectangle((20, 26, cw + 20, 104), 39, fill=(0, 0, 0, 120))
    cta = cta.filter(ImageFilter.GaussianBlur(9))
    ImageDraw.Draw(cta).rounded_rectangle((20, 20, cw + 20, 96), 38, fill=GOLD + (255,))
    ImageDraw.Draw(cta).text((20 + cw // 2, 58), cta_txt, font=cta_f, fill=INK + (255,), anchor='mm')

    bark = Image.open('a4a98d98-82fd-47df-b965-f88b072f95b3.png' if os.path.exists(
        'a4a98d98-82fd-47df-b965-f88b072f95b3.png') else 'assets/bark_brand_logo.jpg').convert('RGB')
    s = bark.width / 1254
    bark = bark.crop((int(285 * s), int(205 * s), int(1000 * s), int(860 * s)))
    bark = bark.resize((56, 56), Image.Resampling.LANCZOS).convert('RGBA')
    m = Image.new('L', (56, 56), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 55, 55), 12, fill=255)
    bark.putalpha(m)
    cred_f = font(FONT_LATIN_SANS, 22)
    cred_txt = 'CREATIVE  ·  BARK & BRAND LABS'
    credw = int(cred_f.getlength(cred_txt)) + 70
    cred = Image.new('RGBA', (credw, 56), (0, 0, 0, 0))
    cred.alpha_composite(bark, (0, 0))
    ImageDraw.Draw(cred).text((70, 28), cred_txt, font=cred_f, fill=(255, 255, 255, 190), anchor='lm')
    disc, db, _ = text_layer(END_DISCLOSURE, font(FONT_KN, 22), (255, 255, 255, 170), 0.6, 4)

    cx = W // 2

    # Slow god-rays behind the logo, and gold dust drifting up through the card.
    R = 1500
    yy, xx = np.mgrid[0:R, 0:R] - R / 2
    ang = np.arctan2(yy, xx)
    rad = np.sqrt(xx ** 2 + yy ** 2) / (R / 2)
    rays = (0.5 + 0.5 * np.cos(ang * 14)) ** 6 * np.clip(1 - rad, 0, 1) ** 1.8
    rays_img = Image.new('RGBA', (R, R), GOLD_HI + (0,))
    rays_img.putalpha(Image.fromarray((rays * 70).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)))
    prng = np.random.default_rng(SEED + 9)
    dust = [(prng.uniform(80, W - 80), prng.uniform(300, 1500), prng.uniform(25, 70),
             prng.uniform(1.5, 4.5), prng.uniform(0, 6.28)) for _ in range(46)]

    def draw(tau):
        cv = bg.copy()
        ra = ease_out(tau / 0.8)
        if ra > 0:
            rot = rays_img.rotate(tau * 7, resample=Image.Resampling.BILINEAR)
            put_layer(cv, rot, cx - R / 2, 630 - R / 2, ra)
        dl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dl)
        for (px, py, sp, r, ph) in dust:
            y_ = py - sp * tau
            a_ = int(200 * ra * (0.5 + 0.5 * math.sin(ph + tau * 2.2)))
            dd.ellipse((px - r, y_ - r, px + r, y_ + r), fill=GOLD_HI + (a_,))
        cv.alpha_composite(dl.filter(ImageFilter.GaussianBlur(1.6)))
        # logo
        u = ease_back(tau / 0.6)
        a = ease_out(tau / 0.3)
        if a > 0:
            sc = 0.55 + 0.45 * u
            sz = max(1, int(logo.width * sc))
            lg = logo.resize((sz, sz), Image.Resampling.BICUBIC)
            put_layer(cv, lg, cx - sz / 2, 630 - sz / 2, a)
        # name, rising, with a shimmer sweep
        u = ease_out((tau - 0.3) / 0.55)
        if u > 0:
            img = name_img
            if 1.1 < tau < 1.9:
                p = (tau - 1.1) / 0.8
                xx = np.arange(img.width)[None, :] + np.arange(img.height)[:, None] * 0.4
                band = np.exp(-((xx - (-120 + (img.width + 240) * p)) / 45) ** 2)
                hi = np.clip(band * name_mask * 200, 0, 255).astype(np.uint8)
                shine = Image.new('RGBA', img.size, (255, 255, 255, 0))
                shine.putalpha(Image.fromarray(hi))
                img = img.copy()
                img.alpha_composite(shine)
            put_layer(cv, img, cx - img.width / 2, 938 - nb + 34 * (1 - u), u)
        # rule
        u = ease_io((tau - 0.6) / 0.45)
        if u > 0:
            half = 190 * u
            ImageDraw.Draw(cv).rectangle([cx - half, 990, cx + half, 993], fill=GOLD + (230,))
        u = ease_out((tau - 0.7) / 0.5)
        put_layer(cv, tag, cx - tag.width / 2, 1062 - tb + 20 * (1 - u), u)
        u = ease_back((tau - 1.0) / 0.45, 2.0)
        a = ease_out((tau - 1.0) / 0.25)
        if a > 0:
            sc = 0.8 + 0.2 * u
            c2 = cta.resize((int(cta.width * sc), int(cta.height * sc)), Image.Resampling.BICUBIC)
            put_layer(cv, c2, cx - c2.width / 2, 1196 - c2.height / 2, a)
        u = ease_out((tau - 1.35) / 0.5)
        put_layer(cv, cred, cx - cred.width / 2, 1296, u)
        put_layer(cv, disc, cx - disc.width / 2, 1392 - db, u)
        return cv.convert('RGB')

    return draw


def safe_check(bug, subs):
    """Every critical overlay inside Format 'reel' safe box, or no render."""
    solid = lambda im: im.getchannel('A').point(lambda v: 255 if v > 128 else 0).getbbox()
    boxes = [('bug', solid(bug))]
    for k, sub in enumerate(subs):
        if not sub.matched:
            print(f'  ! line {k + 1}: word timings fell back to even spacing')
        for w in sub.words:
            b = w['white'].getchannel('A').point(lambda v: 255 if v > 128 else 0).getbbox()
            boxes.append((f'line {k + 1} word', (w['x'] + b[0], w['y'] + b[1], w['x'] + b[2], w['y'] + b[3])))
    bad = [(n, b) for n, b in boxes
           if b[0] < SAFE_L or b[1] < SAFE_T or b[2] > SAFE_R or b[3] > SAFE_B]
    if bad:
        raise SystemExit(f'outside the reel safe zone: {bad[:3]}')
    print(f'  safe zone: {len(boxes)} overlays inside ({SAFE_L},{SAFE_T})–({SAFE_R},{SAFE_B})')


def picture(total, vo, audio_path):
    os.makedirs(OUT, exist_ok=True)
    n_frames = int(round(total * FPS))
    readers = [Reader(s[0], SPEEDS[i]) for i, s in enumerate(SCENES)]
    vig = vignette() * scrim()
    bug = build_bug()
    title = build_title()
    notes = [build_notification(*n) for n in news_items()]
    for im in notes:
        b = im.getchannel('A').point(lambda v: 255 if v > 128 else 0).getbbox()
        assert SAFE_L <= SAFE_L + b[0] and SAFE_L + b[2] <= SAFE_R, 'notification outside safe zone'
    note_t = [CUTS[-1] + BEAT * 2, CUTS[-1] + BEAT * 3]      # on the beat, as the line lands
    note_out = BASE_END - 0.45
    subs = []
    for i, v in enumerate(vo[:len(SCENES)]):
        nxt = vo[i + 1]['start'] if i + 1 < len(SCENES) else BASE_END
        t_out = min(v['end'] + 0.6, nxt - 0.12, BASE_END - 0.3)
        subs.append(Subtitle(v, SCENES[i][1], t_out))
    card = None
    safe_check(bug, subs)

    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-i', audio_path,
        # Fully tagged BT.709 (matrix AND primaries AND transfer — an untagged
        # file gets guessed at by phones and shifts colour), and a delivery
        # bitrate the platforms will not fight: they re-encode anyway.
        '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,noise=c0s=3:c0f=t,'
               'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-profile:v', 'high',
        '-tune', 'film', '-g', str(FPS * 2), '-bf', '2',
        '-maxrate', '18M', '-bufsize', '36M',
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
        '-color_range', 'tv',
        # The promo opens on a hit at sample 0. Handed that, ffmpeg's AAC
        # encoder reconstructs +2dB over the ceiling however hard the master is
        # limited — measured. A 40ms fade gives the transient an attack the
        # encoder can follow (inaudible on a boom), the high-pass drops the
        # subsonics phones cannot play, and the limiter is the last word.
        '-af', 'afade=t=in:d=0.04,highpass=f=30:poles=2,'
               f'alimiter=limit={10 ** ((Limits.true_peak_dbtp - 0.5) / 20):.4f}:attack=1:release=60:level=0',
        '-c:a', 'aac', '-b:a', '256k', '-ar', str(SR),
        '-movflags', '+faststart', '-shortest', FINAL], stdin=subprocess.PIPE)

    def clip_frame(i, t):
        local = t - STARTS[i]
        idx = min(int(round(local * FPS)), int(CLIP_LENS[i] * FPS) - 1)
        return readers[i].frame(idx), local

    last_clip_img = None
    for fi in range(n_frames):
        t = fi / FPS
        if t < BASE_END:
            i = max(k for k in range(len(SCENES)) if t >= STARTS[k] - 1e-9)
            in_xf = i > 0 and (t - STARTS[i]) < XF
            if in_xf:
                p = (t - STARTS[i]) / XF
                a_img, a_loc = clip_frame(i - 1, t)
                b_img, b_loc = clip_frame(i, t)
                arr = transition(SCENES[i - 1][3],
                                 lambda z, dx: framed(a_img, i - 1, a_loc, z, dx),
                                 lambda z, dx: framed(b_img, i, b_loc, z, dx), p)
            else:
                img, loc = clip_frame(i, t)
                # Let the outgoing clip's reader also advance past overlap frames.
                extra = 1.0
                if t > BASE_END - 0.3:                       # push into the card
                    extra = 1 + 0.08 * ease_io((t - (BASE_END - 0.3)) / 0.3) ** 2
                framed_img = framed(img, i, loc, extra)
                if i == len(SCENES) - 1:
                    last_clip_img = img
                arr = np.asarray(framed_img, np.float32)
                if t > BASE_END - 0.3:
                    arr = arr * (1 + 0.9 * ease_io((t - (BASE_END - 0.3)) / 0.3) ** 2)
            if t < 0.35:                                     # the hit: flash + shake
                k = (1 - t / 0.35) ** 2
                sx, sy = int(14 * k * math.sin(t * 90)), int(10 * k * math.cos(t * 70))
                arr = np.roll(np.roll(arr, sx, 1), sy, 0)
                arr = arr + (255 - arr) * 0.55 * k
            arr = np.clip(arr, 0, 255).astype(np.uint8)      # shading is applied at source
            cv = Image.fromarray(arr).convert('RGBA')
            put_layer(cv, bug, 0, 0, ease_out((t - 0.35) / 0.4))
            ta = ease_out(t / 0.08) * (1 - ease_io((t - 2.55) / 0.4))
            if ta > 0:
                sc = 1.0 + 0.32 * (1 - ease_out(t / 0.3)) - 0.03 * ease_out(t / 2.5) \
                    + 0.03 * ease_io((t - 2.55) / 0.4)
                tw, th = int(title.width * sc), int(title.height * sc)
                ti = title.resize((tw, th), Image.Resampling.BICUBIC)
                put_layer(cv, ti, W / 2 - tw / 2, 780 - th / 2, ta)
            for s in subs:
                s.draw(cv, t)
            for k, (img, t_in) in enumerate(zip(notes, note_t)):
                u = (t - t_in) / 0.45
                if u <= 0 or t > note_out + 0.3:
                    continue
                out_k = 1 - ease_io((t - note_out) / 0.3)
                # the newer one arrives on top and pushes the older down
                slot = sum(1 for tj in note_t[k + 1:] if t > tj) * (ease_out((t - note_t[k + 1]) / 0.35) if k + 1 < len(note_t) else 0)
                y = SAFE_T + 150 + 175 * slot - 70 * (1 - ease_back(u, 1.4))
                put_layer(cv, img, SAFE_L + 30 - 30, y, min(1.0, ease_out(u * 1.6)) * out_k)
            frame = cv.convert('RGB')
        else:
            if card is None:
                card = end_card(last_clip_img)
            tau = t - BASE_END
            frame = card(tau)
            flash = max(0.0, 1 - tau / 0.4) ** 2
            if flash > 0:
                arr = np.asarray(frame, np.float32)
                arr = arr + (np.array([255, 236, 190], np.float32) - arr) * flash * 0.85
                frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        enc.stdin.write(frame.tobytes())
        if fi % 48 == 0:
            print(f'  frame {fi}/{n_frames}', end='\r', flush=True)
    enc.stdin.close()
    enc.wait()
    for r in readers:
        r.close()
    if enc.returncode:
        raise SystemExit('encode failed')
    print(f'\n  ✓ {FINAL}')


# ─────────────────────────────────────────────────────────────────────────────
#  QC
# ─────────────────────────────────────────────────────────────────────────────

def qc(total, vo):
    problems = []
    probe = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
                            FINAL], capture_output=True, text=True).stdout)
    v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    au = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    dur = float(probe['format']['duration'])
    fmt = probe['format']
    mb = int(fmt['size']) / 1e6
    mbps = int(fmt['bit_rate']) / 1e6
    # What Instagram Reels and YouTube Shorts actually require of a file.
    if v['width'] * 16 != v['height'] * 9:
        problems.append('not 9:16')
    if not (3 <= dur <= 90):
        problems.append(f'{dur:.1f}s is outside Reels 3–90s')
    if v.get('pix_fmt') != 'yuv420p' or v.get('profile') not in ('High', 'Main'):
        problems.append(f"{v.get('profile')}/{v.get('pix_fmt')} — phones need High/yuv420p")
    for tag in ('color_space', 'color_primaries', 'color_transfer'):
        if v.get(tag) != 'bt709':
            problems.append(f'{tag} is {v.get(tag)}, not bt709 — colour will shift')
    if mbps > 25:
        problems.append(f'{mbps:.1f} Mb/s is heavier than the platforms want')
    if au.get('codec_name') != 'aac' or int(au['sample_rate']) != 48000 or au['channels'] != 2:
        problems.append(f"audio {au.get('codec_name')} {au['sample_rate']}Hz {au['channels']}ch")
    if b'moov' not in open(FINAL, 'rb').read(8192):
        problems.append('not faststart — it will not stream while loading')
    # No black first or last frame: the cover and the loop both live there.
    for t, name in ((0, 'first'), (dur - 0.1, 'last')):
        raw = run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', FINAL, '-frames:v', '1',
                   '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
        if np.frombuffer(raw, np.uint8).mean() < 12:
            problems.append(f'{name} frame is black')
    if (v['width'], v['height']) != (W, H):
        problems.append(f"size {v['width']}x{v['height']}")
    if abs(dur - total) > 0.1:
        problems.append(f'duration {dur:.2f}s, expected {total:.2f}s')
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', FINAL, '-af', 'ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    summ = r[r.rindex('Summary:'):]
    i_lufs = float(summ.split('I:')[1].split('LUFS')[0])
    tp = float(summ.split('Peak:')[1].split('dBFS')[0])
    if abs(i_lufs - Limits.lufs) > 1.0:
        problems.append(f'loudness {i_lufs} LUFS')
    if tp > Limits.true_peak_dbtp + 0.3:
        problems.append(f'true peak {tp} dBTP')
    for x in vo:
        if x['end'] > total:
            problems.append(f"voice line runs past the end: {x['text']}")
    # Contact sheet for eyes.
    run(['ffmpeg', '-v', 'error', '-y', '-i', FINAL, '-vf',
         f'fps=1/{total / 12:.4f},scale=270:-1,tile=6x2', '-frames:v', '1',
         f'{OUT}/review_final_contact.jpg'])
    print(f'  QC  {W}x{H} {v["r_frame_rate"]}fps  {dur:.2f}s  {mb:.0f}MB  {mbps:.1f}Mb/s  '
          f'{i_lufs:.1f} LUFS  {tp:.1f} dBTP  bt709  faststart')
    for p in problems:
        print('  ✗', p)
    return not problems


def voice_pack(total, vo):
    """For recording a human voice-over: a reference track of the read at the
    exact times, and the cue sheet to record against."""
    N = int(SR * total)
    guide = np.zeros((N, 2))
    for v in vo:
        a = int(SR * v['start'])
        seg = v['audio'][:N - a]
        guide[a:a + len(seg)] += seg
    guide *= 0.8 / (np.max(np.abs(guide)) + 1e-9)
    write_wav(f'{BUILD}/guide.wav', guide)
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{BUILD}/guide.wav', '-b:a', '192k',
         f'{OUT}/voice_guide.mp3'])
    rows = ['| # | In | Out | Line |', '|---|---|---|---|']
    for i, v in enumerate(vo):
        rows.append(f"| {i + 1} | {v['start']:.2f}s | {v['end']:.2f}s | {spoken(v['text'])} |")
    with open(f'{OUT}/VOICE_OVER_CUES.md', 'w') as f:
        f.write(f"""# Voice-over cue sheet — ಕರಾವಳಿ 2050

Record against `promo_karavali_2050_no_voice.mp4` ({total:.1f}s). The music in
that file is already dipped where each line goes, so your voice sits in the
gap without any further mixing.

{chr(10).join(rows)}

`voice_guide.mp3` is the same read as a reference track at the same times —
use it to hear the timing, not the tone.

## In GarageBand

1. New project → drag `promo_karavali_2050_no_voice.mp4` in (it becomes the
   movie track with its audio).
2. Optionally drag `voice_guide.mp3` in as a second track, then mute it once
   you know the timings.
3. Record your lines on a new track at the times above. Leave the music track
   untouched — it is already mixed and ducked.
4. **Solo your voice track** (so the music is not in the export), then
   Share → Export Song to Disk → **WAV, 48 kHz, 24-bit**, the full length of
   the video. Silence between the lines is what I need — do not trim it.
5. Send me that file. I rebuild with
   `PROMO_VO_WAV=<file> python3 scripts/build_promo.py`, which finds each line
   in your recording, re-times the subtitles to your read, and re-does the
   music ducking around your voice.

If a line runs long, tell me and I will restretch the picture for it rather
than have you rush.
""")
    print(f'  ✓ {OUT}/voice_guide.mp3 and VOICE_OVER_CUES.md')


def cover():
    """The Reel cover — the title frame, which is what the profile grid shows."""
    r = Reader(SCENES[0][0], SPEEDS[0])
    img = r.frame(int(2.2 * FPS))
    r.close()
    cv = Image.fromarray(np.asarray(framed(img, 0, 2.2), np.uint8)).convert('RGBA')
    cv.alpha_composite(build_bug())
    t = build_title()
    cv.alpha_composite(t, (W // 2 - t.width // 2, 780 - t.height // 2))
    out = f'{OUT}/promo_karavali_2050_cover.jpg'
    cv.convert('RGB').save(out, quality=94)
    # the grid crops it to 3:4 centred — check the title survives that
    box = cv.crop((0, (H - 1440) // 2, W, (H + 1440) // 2))
    assert np.asarray(box.convert('L')).mean() > 15
    print(f'  ✓ {out}')


def main():
    os.makedirs(BUILD, exist_ok=True)
    print('voice')
    vo = voice()
    total = round(max(BASE_END + 3.6, vo[-1]['end'] + 0.9) * FPS) / FPS
    print(f'mix  ({total:.2f}s)')
    bus = mix(total, vo)
    write_f32(f'{BUILD}/mix_raw.wav', bus)
    master(f'{BUILD}/mix_raw.wav', f'{BUILD}/mix.wav')
    print('picture')
    picture(total, vo, f'{BUILD}/mix.wav')
    cover()
    if not NO_VOICE:
        voice_pack(total, vo)
    ok = qc(total, vo)
    json.dump([{k: v[k] for k in ('text', 'start', 'end', 'rate')} for v in vo],
              open(f'{BUILD}/timeline.json', 'w'), ensure_ascii=False, indent=1)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
