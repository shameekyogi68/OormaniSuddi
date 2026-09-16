"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Voice & Narration Engine
========================================
Generates broadcast-grade Kannada voiceover narration for news reels using:
1. Microsoft Neural Edge-TTS (kn-IN-GaganNeural - Male, kn-IN-SapnaNeural - Female)
   -> Free, unlimited, native Kannada prosody and flawless local pronunciation.
2. Google Gemini Flash TTS (using Gemini API Key with gemini-2.5-flash-preview-tts)
   -> Generative multimodal audio with prebuilt voices.

THE NARRATION IS SEGMENTED, AND THAT IS THE WHOLE POINT
-------------------------------------------------------
`synthesize_track()` does not render one long MP3. It renders one clip per
BEAT — the greeting, the lead, the context, each fact, the advisory, the
sign-off — measures each, and returns exactly where every beat begins in the
concatenated master.

The reel engine then cuts the picture from those measurements, so the card on
screen is always the sentence being spoken. Before this existed the engine
guessed: it took the total duration, divided it into equal chapters, and hoped.
On a real 70.5s edition the fact-one card appeared at 17.6s while the voice did
not reach that fact until 33.1s — fifteen seconds of reading one thing while
hearing another — and the sign-off was spoken over a fact card while the outro
played in silence. No amount of tuning fixes that, because a total duration
does not contain the information needed to place a cut. Segment boundaries do.
"""
from __future__ import annotations

import os
import re
import json
import base64
import shutil
import asyncio
import subprocess
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

from .content import Story
from .tokens import Motion

def load_gemini_key(kind: str = 'voice') -> str:
    """Load a Gemini key. Prefer a split key, then the shared one.

    `kind='voice'` reads GEMINI_API_KEY_VOICE then GEMINI_API_KEY.
    `kind='text'`  reads GEMINI_API_KEY_TEXT then GEMINI_API_KEY.
    The Gemini key is reserved for TTS first. Text fetch should use
    GEMINI_API_KEY_TEXT when it exists so a busy morning cannot starve voice.
    """
    names = {
        'voice': ('GEMINI_API_KEY_VOICE', 'GEMINI_API_KEY'),
        'text': ('GEMINI_API_KEY_TEXT', 'GEMINI_API_KEY'),
    }.get(kind, ('GEMINI_API_KEY',))
    for name in names:
        key = os.environ.get(name)
        if key and key.strip():
            return key.strip()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for filename in ['.env', '.gemini_key']:
        p = os.path.join(base_dir, filename)
        if not os.path.exists(p):
            continue
        try:
            with open(p, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for name in names:
                for line in lines:
                    line = line.strip()
                    if line.startswith(name + '='):
                        val = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            if kind == 'voice':
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and len(line) > 20 and '=' not in line:
                        return line
        except Exception:
            pass
    return ''

DEFAULT_GEMINI_KEY = load_gemini_key()

# Industry-standard Kannada newsreader voices:
# kn-IN-SapnaNeural: Articulate, clear, authoritative female television news anchor (Default)
# kn-IN-GaganNeural: Authoritative baritone male news anchor
VOICE_SAPNA = 'kn-IN-SapnaNeural'
VOICE_GAGAN = 'kn-IN-GaganNeural'
DEFAULT_VOICE = VOICE_SAPNA

# ── the anchor's delivery ────────────────────────────────────────────────────
# edge-tts takes no SSML, so these three plus the punctuation written by
# _anchor_cadence() ARE the performance.
#
#   rate   A newsreader reads faster than conversation and slower than
#          urgency. +9% off Sapna's baseline lands at roughly the pace of a
#          Kannada evening bulletin; past about +15% the conjuncts blur.
#   pitch  Down slightly. The stock voice is tagged "Friendly, Positive",
#          which is a customer-service register, not a news one; a small drop
#          reads as composed and authoritative without sounding artificial.
#   volume A touch up, so the anchor sits confidently over the bed rather
#          than being lifted there by the mix alone.
ANCHOR_RATE = '+9%'
ANCHOR_PITCH = '-4Hz'
ANCHOR_VOLUME = '+8%'

# Google's Kannada voice. This is a DELIBERATE default, reverted after being
# switched away and judged worse by a native ear.
#
# The argument for switching to edge/kn-IN-SapnaNeural was that it is a real
# neural voice rather than translate.google.com's pronunciation endpoint, and
# that it sits in a lower register (183Hz against 238Hz measured on the same
# sentence). Both of those are true and neither turned out to matter: the
# owner of this channel listened to the two side by side and the Edge voice
# was markedly worse for Kannada.
#
# The lesson is worth keeping, because it is easy to make again: pitch
# statistics and "neural beats concatenative" are proxies. Whether a Kannada
# newsreader sounds right is not a measurable property, and it is not one this
# repository's author can evaluate. On voice, the native ear decides and
# nothing else gets a vote.
#
# Edge remains one setting away — OORMANI_TTS_ENGINE=edge, or engine='edge' —
# for anyone who wants to compare again.
DEFAULT_ENGINE = 'google'


# ─────────────────────────────────────────────────────────────────────────────
#  BROADCAST SPEECH NORMALISATION
#
#  Print copy and spoken copy are not the same language. A Kannada news anchor
#  says "ಗಂಟೆಗೆ 25 ರಿಂದ 35 ಕಿಲೋಮೀಟರ್", never "25 hyphen ಕಿ dot ಮೀ"; says
#  "1.1 ಲಕ್ಷ ರೂಪಾಯಿ", never "rupee-sign 1.1 ಲಕ್ಷ"; and says "ಶೇಕಡಾ 40", with
#  the word BEFORE the number, where print writes "40%".
#
#  A TTS engine handed the print form reads the print form. That was the last
#  ten percent: the delivery was fine, the words were wrong. Everything here
#  converts written Kannada journalism into what a newsreader says out loud.
# ─────────────────────────────────────────────────────────────────────────────

# Abbreviations a reader expands silently and an engine spells out letter by
# letter. Matched longest-first so "ಕಿ.ಮೀ" wins over "ಮೀ".
SPOKEN_ABBREV = {
    'ಚ.ಕಿ.ಮೀ': 'ಚದರ ಕಿಲೋಮೀಟರ್',
    'ಕಿ.ಮೀ': 'ಕಿಲೋಮೀಟರ್', 'ಕಿ.ಮಿ': 'ಕಿಲೋಮೀಟರ್',
    'ಮಿ.ಮೀ': 'ಮಿಲಿಮೀಟರ್', 'ಸೆ.ಮೀ': 'ಸೆಂಟಿಮೀಟರ್',
    'ಡಾ.': 'ಡಾಕ್ಟರ್ ', 'ಶ್ರೀ.': 'ಶ್ರೀ ',
    'ಸಂ.': 'ಸಂಖ್ಯೆ ', 'ನಂ.': 'ನಂಬರ್ ', 'ರೂ.': 'ರೂಪಾಯಿ ',
}
_ABBREV_RE = re.compile('|'.join(
    re.escape(k) for k in sorted(SPOKEN_ABBREV, key=len, reverse=True)))

# Latin acronyms a Kannada anchor pronounces in Kannada. Left in Latin, the
# engine either spells them in English or skips them entirely.
LATIN_SAY = {
    'CCTV': 'ಸಿಸಿಟಿವಿ', 'KSRTC': 'ಕೆಎಸ್ಆರ್‌ಟಿಸಿ', 'FIR': 'ಎಫ್ಐಆರ್',
    'PSI': 'ಪಿಎಸ್ಐ', 'NH': 'ಎನ್ಎಚ್', 'SP': 'ಎಸ್ಪಿ', 'DC': 'ಡಿಸಿ',
    'AI': 'ಎಐ', 'ATM': 'ಎಟಿಎಂ', 'GST': 'ಜಿಎಸ್ಟಿ',
}

# A decimal point is not a sentence boundary. Protected through the whole
# pipeline and restored last, because the sentence-spacing pass at the end
# would otherwise turn "1.1 ಲಕ್ಷ" into "1. 1 ಲಕ್ಷ" — which an engine reads as
# two separate numbers, and a listener hears as a different amount entirely.
_DECIMAL = ''


# ── how a Kannada anchor says a figure ───────────────────────────────────────
# A decimal point is punctuation to a TTS engine, not a number. Sent "1.10
# ಲಕ್ಷ" the engine stops at the dot and reads "one" … "ten lakh" — a different
# amount, delivered with a pause in the middle of it. Sent "ಕೆ. ಜೆ. ಜಾರ್ಜ್" it
# treats each initial as a finished sentence and leaves a long gap between the
# letters of a man's name.
#
# Neither is fixable downstream: by the time the text reaches the engine the
# dots are indistinguishable from full stops. So the figures and the initials
# are written out here the way they are SAID, and no dot survives that is not
# the end of a sentence.

# (next scale down, how many of it make one of this scale, genitive linker)
_KN_SCALE_DOWN = {
    'ಕೋಟಿ':  ('ಲಕ್ಷ',   100, 'ಕೋಟಿಯ'),
    'ಲಕ್ಷ':   ('ಸಾವಿರ', 100, 'ಲಕ್ಷದ'),
    'ಸಾವಿರ': ('ನೂರು',   10, 'ಸಾವಿರದ'),
}


def _say_scaled(whole: str, frac: str, scale: str) -> str:
    """"1.10 ಲಕ್ಷ" → "1 ಲಕ್ಷದ 10 ಸಾವಿರ" — what a newsreader actually says.

    Kannada money is spoken in whole units of the next scale down, never as a
    decimal. ₹1.10 ಲಕ್ಷ is one lakh and ten thousand rupees, and that is how a
    bulletin reads it out.

    The fraction is a fraction OF THE SCALE, so it is converted through the
    ratio between the two scales — a lakh is 100 thousand, a thousand is only
    10 hundred. Multiplying the hundredths by a flat ten (the first cut of
    this) turned 1.10 ಲಕ್ಷ into "1 ಲಕ್ಷದ 100 ಸಾವಿರ", which is eleven lakh.
    """
    step = _KN_SCALE_DOWN.get(scale)
    if not step:
        return f'{whole} ಪಾಯಿಂಟ್ {frac} {scale}'
    below, ratio, linker = step
    hundredths = int(frac.ljust(2, '0')[:2])
    sub = hundredths * ratio // 100
    if sub == 0:
        return f'{whole} {scale}'
    return f'{whole} {linker} {sub} {below}'


def _speech_normalise(text: str) -> str:
    """Turn written Kannada news copy into what an anchor would say aloud."""
    t = text

    # Abbreviations BEFORE initials. "ಡಾ." is two Kannada letters and a dot,
    # which is exactly the shape of an initial, so the initials rule would
    # otherwise strip its dot and leave "ಡಾ ರಮೇಶ್" instead of "ಡಾಕ್ಟರ್ ರಮೇಶ್".
    t = _ABBREV_RE.sub(lambda m: SPOKEN_ABBREV[m.group(0)], t)

    # Initials: "ಕೆ.ಜೆ. ಜಾರ್ಜ್" / "ಕೆ. ಜೆ. ಜಾರ್ಜ್" → "ಕೆ ಜೆ ಜಾರ್ಜ್".
    # The dots make an engine treat each letter as a finished sentence and
    # leave a long gap inside a person's name. Read without them the letters
    # run together exactly as they are spoken.
    t = re.sub(r'(?:^|\s)([A-Za-z\u0C80-\u0CFF]{1,2})\.\s*(?=[A-Za-z\u0C80-\u0CFF]{1,2}\.)',
               r' \1 ', t)
    t = re.sub(r'(?:^|\s)([A-Za-z\u0C80-\u0CFF]{1,2})\.\s+(?=[A-Za-z\u0C80-\u0CFF])',
               r' \1 ', t)

    # Money with a scale word is spoken in whole units of the scale below.
    # The ₹ is consumed here, so ರೂಪಾಯಿ has to be re-attached — it is what
    # the symbol MEANT, and dropping it leaves an amount with no currency.
    t = re.sub(r'(₹)?\s*(\d+)\.(\d{1,2})\s*(ಕೋಟಿ|ಲಕ್ಷ|ಸಾವಿರ)',
               lambda m: _say_scaled(m.group(2), m.group(3), m.group(4))
               + (' ರೂಪಾಯಿ' if m.group(1) else ''), t)

    # Any decimal left over is read "ಪಾಯಿಂಟ್", never as a stop.
    t = re.sub(r'(\d+)\.(\d+)', r'\1 ಪಾಯಿಂಟ್ \2', t)

    # Thousands separators: "1,25,000" read around its commas is nonsense.
    t = re.sub(r'(?<=\d),(?=\d)', '', t)

    # Currency. Kannada puts ರೂಪಾಯಿ AFTER the amount and after the scale word,
    # so "₹1.1 ಲಕ್ಷ" is "1.1 ಲಕ್ಷ ರೂಪಾಯಿ", not "ರೂಪಾಯಿ 1.1 ಲಕ್ಷ".
    num = r'[\d' + _DECIMAL + r']+'
    t = re.sub(r'₹\s*(' + num + r')\s*(ಲಕ್ಷ|ಕೋಟಿ|ಸಾವಿರ)',
               lambda m: f'{m.group(1)} {m.group(2)} ರೂಪಾಯಿ', t)
    t = re.sub(r'₹\s*(' + num + r')', lambda m: f'{m.group(1)} ರೂಪಾಯಿ', t)
    t = re.sub(r'\bRs\.?\s*(' + num + r')',
               lambda m: f'{m.group(1)} ರೂಪಾಯಿ', t)

    # Percentages: ಶೇಕಡಾ leads the figure in Kannada. An existing ಶೇ / ಶೇಕಡಾ
    # prefix is absorbed rather than doubled — "ಶೇ 40%" is one statement of
    # the fact, not two.
    t = re.sub(r'(?:ಶೇಕಡಾ|ಶೇ\.?)\s*(' + num + r')\s*%', r'ಶೇಕಡಾ \1', t)
    t = re.sub(r'(' + num + r')\s*%', r'ಶೇಕಡಾ \1', t)

    # A hyphen between two figures is "ರಿಂದ" (from…to), never a dash.
    t = re.sub(r'(?<=\d)\s*[-–—]\s*(?=\d)', ' ರಿಂದ ', t)

    # Clock times. A trailing dative in the copy — "9:15 ಕ್ಕೆ" — is CONSUMED,
    # because the spoken form carries its own ("ನಿಮಿಷಕ್ಕೆ"). Leaving it gave
    # "9 ಗಂಟೆ 15 ನಿಮಿಷಕ್ಕೆ ಕ್ಕೆ", which the engine dutifully read aloud.
    def _time(m):
        h, mi, case = int(m.group(1)), int(m.group(2)), m.group(3)
        # The case particle is re-attached in the form the STEM takes, not the
        # form the digits took. ಗಂಟೆ ends in ೆ and takes ಗೆ / ಯ; ನಿಮಿಷ ends in
        # ಅ and takes ಕ್ಕೆ / ದ. Carrying the written particle across unchanged
        # produced "10 ಗಂಟೆಕ್ಕೆ", which is not Kannada.
        if mi == 0:
            stem, dative, genitive = f'{h} ಗಂಟೆ', 'ಗೆ', 'ಯ'
        else:
            stem, dative, genitive = f'{h} ಗಂಟೆ {mi} ನಿಮಿಷ', 'ಕ್ಕೆ', 'ದ'
        if case in ('ಕ್ಕೆ', 'ಗೆ'):
            return stem + dative
        if case == 'ರ':
            return stem + genitive
        return stem
    t = re.sub(r'(\d{1,2}):(\d{2})(?:\s+(ಕ್ಕೆ|ಗೆ|ರ))?(?=\s|[,.]|$)', _time, t)

    # Temperature.
    t = re.sub(r'(' + num + r')\s*°\s*(?:C|ಸಿ)?',
               lambda m: f'{m.group(1)} ಡಿಗ್ರಿ ಸೆಲ್ಸಿಯಸ್', t)

    t = _ABBREV_RE.sub(lambda m: SPOKEN_ABBREV[m.group(0)], t)
    for k, v in LATIN_SAY.items():
        t = re.sub(r'\b' + k + r'\b', v, t)

    return t


def _anchor_cadence(text: str) -> str:
    """Punctuate for the ear rather than the eye.

    edge-tts accepts no SSML, so every pause an anchor makes has to be written
    into the text as punctuation. This is where delivery stops sounding like a
    document being read aloud and starts sounding like someone presenting it:
    a beat after the dateline, a beat around an attribution, and a full stop
    that genuinely lands at the end of every sentence — which is what produces
    the falling final intonation. Without it the engine trails off flat.
    """
    t = text
    # A dateline is announced, then held for a beat.
    t = re.sub(r'^(\S{3,24}(?:ದಲ್ಲಿ|ನಲ್ಲಿ|ಯಲ್ಲಿ|ಬಳಿ|ಸಮೀಪ))\s+(?![,.])',
               r'\1, ', t)
    # Attributions take a breath either side, the way a newsreader separates
    # the claim from whoever made it.
    for cue in ('ಪೊಲೀಸರ ಪ್ರಕಾರ', 'ಮೂಲಗಳ ಪ್ರಕಾರ', 'ವರದಿಗಳ ಪ್ರಕಾರ',
                'ಅಧಿಕಾರಿಗಳ ಪ್ರಕಾರ', 'ಸ್ಥಳೀಯರ ಪ್ರಕಾರ',
                'ಸ್ಥಳೀಯ ವರದಿಗಳ ಪ್ರಕಾರ'):
        t = re.sub(r'(?<![,ಀ-೿])\s' + cue + r'(?![,ಀ-೿])',
                   f', {cue},', t)
    t = re.sub(r',\s*,+', ',', t)
    t = re.sub(r',\s*\.', '.', t)
    t = re.sub(r'\s+([,.])', r'\1', t)
    t = t.strip()
    if t and t[-1] not in '.!?':
        t += '.'
    return t


def _pronunciation_map() -> dict[str, str]:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'assets', 'pronunciation.json')
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        return {str(k): str(v) for k, v in data.items() if k and v}
    except Exception:
        return {}


def _spoken(text: str) -> str:
    """Normalise one beat into something a TTS engine reads like an anchor."""
    t = re.sub(r'[\r\n\t]+', ' ', text)
    for src, dst in _pronunciation_map().items():
        t = t.replace(src, dst)
    # Bullets and dashes are typography, not speech. Left in, the engine either
    # pronounces them or stalls on them.
    t = t.replace('▪', '').replace('•', '').replace('·', ',')
    t = t.replace('—', ', ').replace('–', ', ')
    t = _speech_normalise(t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\s*,\s*', ', ', t)
    t = re.sub(r'\s*\.\s*', '. ', t)
    t = _anchor_cadence(t.strip())
    return t.replace(_DECIMAL, '.')


# Phrases that identify a beat regardless of where a script puts it. Used only
# to place an editor's own narration_script onto the right cards.
SIGNOFF_MARKERS = ('ಫಾಲೋ ಮಾಡಿ', 'ನಮ್ಮ ಧ್ವನಿ', 'ಸುದ್ದಿಗಳಿಗಾಗಿ', 'ಸಬ್‌ಸ್ಕ್ರೈಬ್')
ADVISORY_MARKERS = ('ಸಾರ್ವಜನಿಕರ ಗಮನಕ್ಕೆ', 'ಗಮನಿಸಿ:', 'ಎಚ್ಚರಿಕೆ', 'ಸೂಚನೆ:')


def card_keys(story: Story) -> list[str]:
    """The cards this story will show, in order — the visual spine of the reel.

    Both the narration and the picture are built from this one list, which is
    what makes them impossible to get out of step: a story with three facts
    has five cards and five spoken beats, always.
    """
    keys = ['lead']
    keys += [f'fact{i}' for i, p in enumerate(story.points) if p.strip()]
    if (story.takeaway or '').strip():
        keys.append('advisory')
    keys.append('signoff')
    return keys


def _fit_script_to_cards(script: str, keys: list[str]) -> list[tuple[str, str]]:
    """Distribute an editor's own script across the cards the story will show.

    An override script is the SPEECH; the cards still come from the story. So
    the sentences are grouped — in order, never reordered — into as many
    contiguous runs as there are cards, balanced by length so no card is left
    holding "ನಮಸ್ಕಾರ." on its own for four seconds while the next one races
    through three sentences.
    """
    # Protect initials and honorifics with dots (e.g. "ಕೆ.ಜೆ.", "ಕೆ. ಜೆ.", "ಡಾ.", "K.J.")
    cleaned = re.sub(r'(^|\s)([A-Za-z\u0C80-\u0CFF]{1,2})\.\s*', r'\1\2__DOT__ ', script)
    cleaned = re.sub(r'__DOT__\s*([A-Za-z\u0C80-\u0CFF]{1,2})\.\s*', r'__DOT__\1__DOT__ ', cleaned)
    sents = [re.sub(r'__DOT__', '.', s).strip() for s in re.split(r'(?<=[.!?।])\s+', cleaned) if s.strip()]
    if not sents:
        return []

    # ── Anchor the beats that are recognisable by their words ─────────────
    # Balancing alone gets these wrong, and wrongly in the most visible place:
    # on real copy the sign-off landed on a fact card and the advisory landed
    # on the outro. Length says nothing about meaning, so the sentences that
    # announce what they are get claimed first, and only the rest are balanced.
    out: list[tuple[str, str]] = []
    keys = list(keys)

    tail: list[tuple[str, str]] = []
    if 'signoff' in keys:
        sign = []
        while sents and any(m in sents[-1] for m in SIGNOFF_MARKERS):
            sign.insert(0, sents.pop())
        if sign:
            tail.insert(0, ('signoff', _spoken(' '.join(sign))))
            keys.remove('signoff')

    if 'advisory' in keys:
        idx = next((i for i, s in enumerate(sents)
                    if any(m in s for m in ADVISORY_MARKERS)), None)
        if idx is not None:
            tail.insert(0, ('advisory', _spoken(' '.join(sents[idx:]))))
            sents = sents[:idx]
            keys.remove('advisory')

    n = len(keys)
    if not sents or n == 0:
        return out + tail
    if len(sents) <= n:
        # Fewer sentences than cards: one each, and the cards with nothing to
        # say are dropped rather than shown in silence.
        return [(keys[i], _spoken(s)) for i, s in enumerate(sents)] + tail

    # Balanced contiguous partition into n runs, by character length.
    costs = [len(s) for s in sents]
    total = sum(costs)
    target = total / n
    groups: list[list[str]] = []
    cur: list[str] = []
    acc = 0.0
    for i, s in enumerate(sents):
        remaining_sents = len(sents) - i
        remaining_groups = n - len(groups)
        cur.append(s)
        acc += costs[i]
        # Close this run when it has reached its share, but never so late that
        # the remaining sentences cannot fill the remaining cards.
        must_close = remaining_sents - 1 < remaining_groups - 1 + 1
        if (acc >= target and remaining_groups > 1) or must_close:
            if remaining_groups > 1:
                groups.append(cur)
                cur = []
                acc = 0.0
    if cur:
        groups.append(cur)
    while len(groups) > n:                     # merge any overflow into the last
        groups[-2].extend(groups.pop())
    while len(groups) < n and any(len(g) > 1 for g in groups):
        big = max(range(len(groups)), key=lambda i: len(groups[i]))
        half = len(groups[big]) // 2
        groups.insert(big + 1, groups[big][half:])
        groups[big] = groups[big][:half]

    return [(keys[i], _spoken(' '.join(g))) for i, g in enumerate(groups) if g] + tail


def narration_beats(story: Story) -> list[tuple[str, str]]:
    """The narration as (beat_key, text) — the seams the picture is cut on.

    A beat is one spoken unit that owns one visual: `lead` is the headline
    card, `fact0` is the first fact card, `signoff` is the outro. The reel
    engine matches these keys to scenes, so adding a beat here adds a scene
    there and the two cannot drift apart.

    `narration_script` on the Story overrides the whole thing, and is split on
    sentence boundaries — an editor who writes their own script gets it read
    verbatim, and the picture still follows the sentences.
    """
    override = (getattr(story, 'narration_script', '') or '').strip()
    if override:
        return _fit_script_to_cards(override, card_keys(story))

    beats: list[tuple[str, str]] = []

    # 1. Open on the news. A ನಮಸ್ಕಾರ greeting costs the first 1.5 seconds
    #    that decide whether the reel is swiped. D58.
    hl = (story.reel_line or story.headline or '').strip()
    if hl:
        if ':' in hl:
            prefix, rest = [p.strip() for p in hl.split(':', 1)]
            hl_spoken = f'{prefix}, {rest}'
        else:
            hl_spoken = hl
        hl_spoken = hl_spoken.rstrip('.!?;:') + '.'
    else:
        hl_spoken = ''

    # Ground context (deck) only joins if headline is missing or very brief.
    deck = (story.deck or '').strip()
    if deck and not hl:
        deck_spoken = (deck.replace(';', ', ಹಾಗೂ').rstrip('.!?;:') + '.')
    else:
        deck_spoken = ''

    beats.append(('lead', _spoken(' '.join(x for x in (hl_spoken, deck_spoken) if x))))

    # 4. Facts — one beat, one card, each (capped at 3 for reel pacing & retention).
    transitions = ['ಇನ್ನು, ', 'ಇದೇ ವೇಳೆ, ', 'ಸ್ಥಳೀಯ ವರದಿಗಳ ಪ್ರಕಾರ, ']
    for idx, pt in enumerate(story.points[:3]):
        p_clean = pt.strip().rstrip('.!?;:')
        if not p_clean:
            continue
        if idx > 0 and idx - 1 < len(transitions):
            if not any(p_clean.startswith(t) for t in ('ಇನ್ನು', 'ಇದೇ', 'ಆದರೆ', 'ಸ್ಥಳ')):
                p_clean = transitions[idx - 1] + p_clean
        beats.append((f'fact{idx}', _spoken(p_clean + '.')))

    # 5. Public advisory.
    if story.takeaway:
        tk = story.takeaway.strip().replace(';', ',').rstrip('.!?;:')
        if tk:
            beats.append(('advisory', _spoken(f'ಸಾರ್ವಜನಿಕರ ಗಮನಕ್ಕೆ: {tk}.')))

    # 6. Sign-off — this beat IS the outro card, which is why the outro can no
    #    longer play in silence after the voice has already finished.
    beats.append(('signoff', _spoken(
        'ಕ್ಷಣ ಕ್ಷಣದ ನಿಖರ ಕರಾವಳಿ ಸುದ್ದಿಗಳಿಗಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿ ಫಾಲೋ ಮಾಡಿ — '
        'ಇದು ನಮ್ಮ ಊರು, ನಮ್ಮ ಧ್ವನಿ.')))

    return [(k, t) for k, t in beats if t]


def build_narration_script(story: Story) -> str:
    """The full narration as one string — for the copy sheet, not for timing."""
    return ' '.join(t for _k, t in narration_beats(story))


async def _edge_tts_synthesize(text: str, out_path: str,
                               voice: str = VOICE_SAPNA,
                               rate: str = ANCHOR_RATE,
                               pitch: str = ANCHOR_PITCH,
                               volume: str = ANCHOR_VOLUME) -> str:
    """Synthesize one beat in the neural Kannada news-anchor voice.

    The three prosody settings are the delivery. edge-tts accepts no SSML, so
    rate / pitch / volume plus the punctuation written by `_anchor_cadence`
    are the whole instrument — see ANCHOR_RATE for why each value is what it
    is.
    """
    import edge_tts
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch,
                                volume=volume)
    await comm.save(out_path)
    return out_path


def _google_tts_synthesize(text: str, out_path: str, tempo: float = 1.15) -> str:
    """Synthesize speech using Google's native Indic Kannada voice engine."""
    # Split on SENTENCE ends only — a stop followed by whitespace or the end
    # of the text. The old pattern split on every '.', including the one in
    # "1.10" and the ones in "ಕೆ. ಜೆ. ಜಾರ್ಜ್", and because each chunk is a
    # separate HTTP request and a separate MP3 that is then concatenated,
    # every one of those became an audible gap in the middle of a number or a
    # person's name. `_speech_normalise` now removes both kinds of dot before
    # this runs; this is the second line of defence, so a dot that slips
    # through can no longer cut the audio in half.
    # The endpoint refuses anything much past 200 characters, so a sentence
    # longer than the budget is broken further — at a comma, and failing that
    # at a space. Never mid-token: a split is a separate request and a
    # separate MP3, so it is an audible gap wherever it lands.
    LIMIT = 180

    def _split_long(seg: str) -> list[str]:
        if len(seg) <= LIMIT:
            return [seg]
        out, cur = [], ''
        for piece in re.split(r'(?<=,)\s*', seg):
            if cur and len(cur) + len(piece) > LIMIT:
                out.append(cur.strip())
                cur = piece
            else:
                cur += (' ' if cur and not cur.endswith(' ') else '') + piece
        if cur.strip():
            out.append(cur.strip())
        # Still too long (a sentence with no commas) — fall back to words.
        final = []
        for c in out:
            if len(c) <= LIMIT:
                final.append(c)
                continue
            cur = ''
            for w in c.split():
                if cur and len(cur) + len(w) + 1 > LIMIT:
                    final.append(cur)
                    cur = w
                else:
                    cur = f'{cur} {w}'.strip()
            if cur:
                final.append(cur)
        return final

    chunks, curr = [], ''
    for part in re.split(r'(?<=[.!?।])(?=\s|$)', text):
        if not part.strip():
            continue
        for seg in _split_long(part.strip()):
            if curr and len(curr) + len(seg) + 1 > LIMIT:
                chunks.append(curr.strip())
                curr = seg
            else:
                curr = f'{curr} {seg}'.strip()
    if curr.strip():
        chunks.append(curr.strip())
    chunks = [c for c in chunks if c.strip()]

    temp_dir = out_path + '_gchunks'
    os.makedirs(temp_dir, exist_ok=True)
    temp_files = []

    for i, c in enumerate(chunks):
        enc = urllib.parse.quote(c)
        url = f'https://translate.google.com/translate_tts?ie=UTF-8&q={enc}&tl=kn&total={len(chunks)}&idx={i}&textlen={len(c)}&client=tw-ob'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        tmp_f = os.path.join(temp_dir, f'part_{i:03d}.mp3')
        with urllib.request.urlopen(req, timeout=20) as resp, open(tmp_f, 'wb') as out_f:
            out_f.write(resp.read())
        temp_files.append(tmp_f)

    list_path = os.path.join(temp_dir, 'list.txt')
    with open(list_path, 'w', encoding='utf-8') as lf:
        for f in temp_files:
            lf.write(f"file '{os.path.abspath(f)}'\n")

    raw_concat = os.path.join(temp_dir, 'concat.mp3')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list_path, '-c', 'copy', raw_concat], check=True)

    # Apply news anchor broadcast tempo (tempo=1.15)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw_concat, '-filter:a', f'atempo={tempo}', '-b:a', '192k', out_path], check=True)

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    return out_path


def _gemini_tts_synthesize(text: str, out_path: str, voice: str = 'Puck', api_key: str | None = None) -> str:
    """Synthesize speech using Google Gemini Flash TTS."""
    key = api_key or DEFAULT_GEMINI_KEY
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={key}'
    payload = {
        'contents': [{'parts': [{'text': text}]}],
        'generationConfig': {
            'responseModalities': ['AUDIO'],
            'speechConfig': {
                'voiceConfig': {
                    'prebuiltVoiceConfig': {
                        'voiceName': voice
                    }
                }
            }
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        part = res['candidates'][0]['content']['parts'][0]
        b64_pcm = part['inlineData']['data']
        raw_pcm = base64.b64decode(b64_pcm)

    pcm_tmp = out_path + '.raw.pcm'
    with open(pcm_tmp, 'wb') as f:
        f.write(raw_pcm)

    # Convert 24kHz mono PCM into MP3
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', pcm_tmp,
        '-b:a', '192k', out_path
    ], check=True)
    if os.path.exists(pcm_tmp):
        os.remove(pcm_tmp)
    return out_path


def get_audio_duration(path: str) -> float:
    """Measure exact audio duration in seconds using ffprobe."""
    if not os.path.exists(path):
        return 0.0
    try:
        p = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', path
        ], capture_output=True, text=True, check=True)
        return float(p.stdout.strip())
    except Exception:
        return 0.0


@dataclass
class VoiceSegment:
    """One spoken beat, and exactly where it sits in the master track."""
    key: str          # 'lead' | 'fact0' | … | 'advisory' | 'signoff'
    text: str
    path: str
    speech: float     # seconds of actual speech
    start: float = 0.0    # where the speech begins in the master
    gap: float = 0.0      # silence after it, before the next beat
    short_by: float = 0.0 # seconds its card needed that the cap would not give

    @property
    def span(self) -> float:
        """Speech plus its trailing silence — the beat's full share of time."""
        return self.speech + self.gap


@dataclass
class VoiceTrack:
    """A narration whose seams are known to the frame."""
    path: str
    duration: float
    lead_in: float                 # silence before the first word
    segments: list[VoiceSegment] = field(default_factory=list)
    script: str = ''

    def by_key(self, key: str) -> VoiceSegment | None:
        return next((s for s in self.segments if s.key == key), None)


# ── the synthesis cache ──────────────────────────────────────────────────────
# A beat is synthesised from exactly three things: the normalised text, the
# engine, and the voice. Nothing else can change its audio. So a re-render
# after a typo fix in story 3 has no business paying for story 1's narration
# again — on a morning with four reels that is most of the wait, and on a
# metered API it is most of the bill.
#
# Keyed on the content, so a changed word misses and an unchanged one hits.
# Delete the folder to invalidate; nothing else needs to know it exists.
TTS_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'build', 'tts_cache')


def _cache_key(text: str, engine: str, voice: str | None) -> str:
    import hashlib
    blob = f'{engine}\x00{voice or ""}\x00{text}'.encode('utf-8')
    return hashlib.sha256(blob).hexdigest()[:24]


def cache_enabled() -> bool:
    return os.environ.get('OORMANI_TTS_CACHE', '1') not in ('0', 'off', 'no')


# The order a failing engine falls through. The native ear chose Google; edge
# is the neural voice it rejected, which makes it a poor default and a
# perfectly good lifeboat. A whole day's package must not be lost to one
# engine having a bad morning — but the fallback is RECORDED, not silent,
# because a reel narrated by the rejected voice is something the editor has to
# know about before it goes out.
FALLBACK_ORDER = {
    'google': ('google', 'edge', 'gemini'),
    'edge':   ('edge', 'google', 'gemini'),
    'gemini': ('gemini', 'google', 'edge'),
}

# Filled by _synth_one whenever a beat did not come from the chosen engine.
FALLBACKS_USED: list[tuple[str, str, str]] = []   # (from, to, why)


def _synth_with(eng: str, text: str, out_path: str,
                voice: str | None, api_key: str | None) -> None:
    if eng == 'gemini':
        _gemini_tts_synthesize(text, out_path, voice=voice or 'Aoede',
                               api_key=api_key)
    elif eng == 'google':
        _google_tts_synthesize(text, out_path, tempo=1.15)
    else:
        asyncio.run(_edge_tts_synthesize(text, out_path,
                                         voice=voice or DEFAULT_VOICE))


def _synth_one(text: str, out_path: str, engine: str,
               voice: str | None, api_key: str | None) -> str:
    """Render one beat with the selected engine, falling back gracefully.

    Three behaviours the caller does not have to think about: the cache, the
    fallback chain, and the record of which engine actually spoke.
    """
    eng = (os.environ.get('OORMANI_TTS_ENGINE') or engine).lower()

    if cache_enabled():
        key = _cache_key(text, eng, voice)
        cached = os.path.join(TTS_CACHE, f'{key}{os.path.splitext(out_path)[1] or ".mp3"}')
        if os.path.exists(cached) and os.path.getsize(cached) > 512:
            shutil.copy2(cached, out_path)
            return out_path
    else:
        cached = ''

    chain = FALLBACK_ORDER.get(eng, (eng,))
    last: Exception | None = None
    for i, candidate in enumerate(chain):
        try:
            _synth_with(candidate, text, out_path, voice, api_key)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 512:
                if i:
                    FALLBACKS_USED.append((eng, candidate, str(last)))
                    print(f'      ! TTS fell back {eng} → {candidate} ({last})')
                if cached:
                    try:
                        os.makedirs(TTS_CACHE, exist_ok=True)
                        shutil.copy2(out_path, cached)
                    except OSError:
                        pass
                return out_path
            last = RuntimeError(f'{candidate} produced an empty file')
        except Exception as e:      # noqa: BLE001 — every engine fails its own way
            last = e
    raise RuntimeError(
        f'every TTS engine failed for this beat; last was {last}') from last


# One PCM format for every piece that goes into the master. The concat
# demuxer does not resample or re-timestamp: fed a mix of 24kHz mono MP3 from
# one engine and 48kHz WAV silence, it emits a file whose header duration is
# nonsense — the first build of this reported a 27s master for 70s of speech,
# and every cut computed from it would have been wrong. Normalising every
# piece to identical PCM first makes the concatenation exact by construction.
PCM = ('-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le')


def _to_pcm(src: str, dst: str) -> str:
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src,
                    *PCM, dst], check=True)
    return dst


def _silence(path: str, seconds: float) -> str:
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', 'anullsrc=r=48000:cl=mono', '-t', f'{seconds:.3f}',
                    *PCM, path], check=True)
    return path


def synthesize_track(story: Story, out_path: str,
                     engine: str = DEFAULT_ENGINE,
                     voice: str | None = None,
                     api_key: str | None = None,
                     lead_in: float = Motion.vo_lead,
                     gap: float = Motion.vo_gap,
                     tail: float = Motion.vo_tail,
                     max_hold: float = Motion.vo_hold_max,
                     min_span: dict[str, float] | None = None) -> VoiceTrack:
    """Synthesize the narration beat by beat and report where each one lands.

    `min_span` lets the caller lengthen a beat's share of time — the reel
    engine passes the seconds each card actually takes to READ, because a TTS
    voice reads Kannada considerably faster than a viewer meeting the sentence
    for the first time on a moving picture. The extra time becomes silence
    AFTER the beat, so the voice stays natural and the card simply holds. The
    alternative — cutting when the voice stops — is the thing that made these
    reels feel rushed even when they were in sync.

    `lead_in` is silence before the first word, so the opening card is up and
    its type has settled before anyone speaks. `gap` is the beat between
    cards: the cut lands inside it, which is why the transitions stop
    clipping syllables.
    """
    beats = narration_beats(story)
    work = os.path.join(os.path.dirname(os.path.abspath(out_path)), '_vo_parts')
    os.makedirs(work, exist_ok=True)
    min_span = min_span or {}

    segs: list[VoiceSegment] = []
    for i, (key, text) in enumerate(beats):
        raw = os.path.join(work, f'{i:02d}_{key}.mp3')
        _synth_one(text, raw, engine, voice, api_key)
        # Measured AFTER normalising, because the measurement and the master
        # have to describe the same audio.
        part = _to_pcm(raw, os.path.join(work, f'{i:02d}_{key}.wav'))
        segs.append(VoiceSegment(key=key, text=text, path=part,
                                 speech=get_audio_duration(part)))

    # Give every beat its silence, then stretch any beat whose card needs
    # longer on screen than its sentence takes to say — up to a limit.
    #
    # The cap matters. Uncapped, a card carrying more copy than its narration
    # covers asked for six and a half seconds of held picture and silence in
    # the middle of the reel, which reads as the video having stalled. Past
    # about two and a half seconds the honest reading is not "hold longer" but
    # "this card says more than the voice does", and that is an editorial
    # problem the renderer should report rather than absorb.
    for i, s in enumerate(segs):
        base = tail if i == len(segs) - 1 else gap
        s.gap = base
        want = min_span.get(s.key, 0.0)
        if want > s.span:
            s.gap = min(want - s.speech, base + max_hold)
            s.short_by = max(0.0, want - s.span)

    over = [s for s in segs if s.short_by > 0.05]
    for s in over:
        print(f'    ⚠ card "{s.key}" holds {s.span:.1f}s but its Kannada needs '
              f'{s.span + s.short_by:.1f}s to read — {s.short_by:.1f}s short. '
              f'The card carries more copy than the narration covers: shorten '
              f'the point, or say more about it in the script.')

    # Lay them out on the master timeline.
    t = lead_in
    for s in segs:
        s.start = t
        t += s.span

    # Concatenate: lead-in silence, then each beat followed by its own gap.
    pieces = [_silence(os.path.join(work, 'lead.wav'), lead_in)]
    for i, s in enumerate(segs):
        pieces.append(s.path)
        pieces.append(_silence(os.path.join(work, f'gap{i:02d}.wav'), s.gap))

    listing = os.path.join(work, 'concat.txt')
    with open(listing, 'w', encoding='utf-8') as lf:
        for p in pieces:
            lf.write(f"file '{os.path.abspath(p)}'\n")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
    # Every piece is already identical PCM, so the concatenation is sample
    # exact and the master's duration is the sum of the parts by construction.
    master_wav = os.path.join(work, 'master.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat',
                    '-safe', '0', '-i', listing, *PCM, master_wav], check=True)

    expect = lead_in + sum(s.span for s in segs)
    got = get_audio_duration(master_wav)
    if abs(got - expect) > 0.25:
        # The segment starts are the only thing the picture is cut from. If
        # the master does not agree with them, every cut in the reel is wrong,
        # and a reel that is silently out of sync is exactly what this rewrite
        # exists to stop shipping. Fail loudly instead.
        raise RuntimeError(
            f'narration master is {got:.2f}s but its measured beats sum to '
            f'{expect:.2f}s. The reel is cut from those beats, so a '
            f'mismatch would put every card off its sentence.')

    # Delivered as MP3 for the copy folder; the WAV is what was measured.
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', master_wav,
                    '-ar', '48000', '-ac', '1', '-b:a', '192k', out_path],
                   check=True)

    # The measured WAV is a working file, not a deliverable: it is what the
    # audio master and the sync audit read, and it is ~8MB per reel. It goes
    # to build/, never next to the artwork — the output folder carries only
    # what an editor actually publishes.
    build = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'build')
    os.makedirs(build, exist_ok=True)
    keep = os.path.join(build, os.path.splitext(os.path.basename(out_path))[0]
                        + '.master.wav')
    shutil.copy2(master_wav, keep)
    track = VoiceTrack(path=keep, duration=got, lead_in=lead_in,
                       segments=segs, script=' '.join(s.text for s in segs))
    shutil.rmtree(work, ignore_errors=True)
    return track


def synthesize_narration(story: Story, out_path: str,
                         engine: str = DEFAULT_ENGINE,
                         voice: str | None = None,
                         script: str | None = None,
                         api_key: str | None = None) -> tuple[str, float, str]:
    """Generate audio voiceover for a news story.
    
    Supported engines:
      - 'google': Google's native Indic Kannada TTS voice (tuned to broadcast tempo)
      - 'edge': Microsoft Neural kn-IN-SapnaNeural (Female TV Anchor) / kn-IN-GaganNeural (Male)
      - 'gemini': Google Gemini Flash TTS
      
    Returns: (audio_path, duration_seconds, script_text)
    """
    text = script or build_narration_script(story)
    
    eng = (os.environ.get('OORMANI_TTS_ENGINE') or engine).lower()
    
    if eng == 'gemini':
        v = voice or 'Aoede'
        _gemini_tts_synthesize(text, out_path, voice=v, api_key=api_key)
    elif eng == 'edge':
        v = voice or DEFAULT_VOICE
        asyncio.run(_edge_tts_synthesize(text, out_path, voice=v, rate='+5%'))
    else:
        # Default: Google native Indic Kannada voice
        try:
            _google_tts_synthesize(text, out_path, tempo=1.15)
        except Exception:
            # Fallback to Edge-TTS neural if network glitch
            v = voice or DEFAULT_VOICE
            asyncio.run(_edge_tts_synthesize(text, out_path, voice=v, rate='+5%'))
        
    dur = get_audio_duration(out_path)
    return out_path, dur, text
