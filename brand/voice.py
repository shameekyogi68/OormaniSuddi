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

def load_gemini_key() -> str:
    """Load Gemini API key from environment or local untracked secret files (.env, .gemini_key)."""
    key = os.environ.get('GEMINI_API_KEY')
    if key and key.strip():
        return key.strip()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for filename in ['.env', '.gemini_key']:
        p = os.path.join(base_dir, filename)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('GEMINI_API_KEY='):
                            val = line.split('=', 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
                        elif line and not line.startswith('#') and len(line) > 20 and '=' not in line:
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


def _spoken(text: str) -> str:
    """Normalise one beat into something a TTS engine reads cleanly."""
    t = re.sub(r'[\r\n\t]+', ' ', text)
    # Bullets and dashes are typography, not speech. Left in, the engine either
    # pronounces them or stalls on them.
    t = t.replace('▪', '').replace('•', '').replace('·', ',')
    t = t.replace('—', ', ').replace('–', ', ')
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\s*,\s*', ', ', t)
    t = re.sub(r'\s*\.\s*', '. ', t)
    return t.strip()


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
    sents = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', script) if s.strip()]
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

    # 1. Anchor hook. Rides the headline card with the lead, so it is part of
    #    the same beat rather than a scene of its own — a greeting with no
    #    picture behind it is dead air at exactly the moment the platform is
    #    deciding whether to distribute this at all.
    is_urgent = any(k in story.headline or k in (story.deck or '')
                    for k in ['ಅಪಘಾತ', 'ಸಾವು', 'ಕಳವು', 'ಪೊಲೀಸ್', 'ಬಂಧನ',
                              'ದಾಳಿ', 'ಪಲ್ಟಿ', 'ದುರಂತ'])
    hook = ('ನಮಸ್ಕಾರ, ಊರ್ಮನಿ ಸುದ್ದಿಯ ಪ್ರಮುಖ ಸುದ್ದಿ.' if is_urgent
            else 'ನಮಸ್ಕಾರ, ಊರ್ಮನಿ ಸುದ್ದಿಯ ಕರಾವಳಿ ವಿಶೇಷ ವರದಿಗೆ ಸ್ವಾಗತ.')

    # 2. Spoken headline. A print headline is punctuated for the eye; read
    #    aloud, a colon becomes a stumble.
    hl = (story.headline or '').strip()
    if hl:
        if ':' in hl:
            prefix, rest = [p.strip() for p in hl.split(':', 1)]
            if any(k in rest for k in ['ಅಪಘಾತ', 'ಸಾವು', 'ಪಲ್ಟಿ']):
                hl_spoken = f'{prefix} ಬಳಿ ಭೀಕರ ಅಪಘಾತ ಸಂಭವಿಸಿದ್ದು, {rest}'
            else:
                hl_spoken = f'{prefix}ದಲ್ಲಿ {rest}'
        else:
            hl_spoken = hl
        hl_spoken = hl_spoken.rstrip('.!?;:') + '.'
    else:
        hl_spoken = ''

    # 3. Ground context (deck) joins the lead beat: both belong to the
    #    headline card, and splitting them would put a cut mid-thought.
    deck = (story.deck or '').strip()
    deck_spoken = (deck.replace(';', ', ಹಾಗೂ').rstrip('.!?;:') + '.') if deck else ''

    beats.append(('lead', _spoken(' '.join(x for x in (hook, hl_spoken, deck_spoken) if x))))

    # 4. Facts — one beat, one card, each.
    transitions = ['ಇನ್ನು, ', 'ಇದೇ ವೇಳೆ, ', 'ಸ್ಥಳೀಯ ವರದಿಗಳ ಪ್ರಕಾರ, ']
    for idx, pt in enumerate(story.points):
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


async def _edge_tts_synthesize(text: str, out_path: str, voice: str = VOICE_SAPNA, rate: str = '+5%') -> str:
    """Synthesize speech using Edge-TTS neural Kannada female news anchor voice."""
    import edge_tts
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(out_path)
    return out_path


def _google_tts_synthesize(text: str, out_path: str, tempo: float = 1.15) -> str:
    """Synthesize speech using Google's native Indic Kannada voice engine."""
    sentences = re.split(r'([.!?।])', text)
    chunks = []
    curr = ''
    for part in sentences:
        if len(curr) + len(part) < 180:
            curr += part
        else:
            if curr.strip():
                chunks.append(curr.strip())
            curr = part
    if curr.strip():
        chunks.append(curr.strip())

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


def _synth_one(text: str, out_path: str, engine: str,
               voice: str | None, api_key: str | None) -> str:
    """Render one beat with the selected engine, falling back gracefully."""
    eng = (os.environ.get('OORMANI_TTS_ENGINE') or engine).lower()
    if eng == 'gemini':
        _gemini_tts_synthesize(text, out_path, voice=voice or 'Aoede', api_key=api_key)
    elif eng == 'edge':
        asyncio.run(_edge_tts_synthesize(text, out_path,
                                         voice=voice or DEFAULT_VOICE, rate='+5%'))
    else:
        try:
            _google_tts_synthesize(text, out_path, tempo=1.15)
        except Exception:
            asyncio.run(_edge_tts_synthesize(text, out_path,
                                             voice=voice or DEFAULT_VOICE, rate='+5%'))
    return out_path


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
                     engine: str = 'google',
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
                         engine: str = 'google',
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
