"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Voice & Narration Engine
========================================
Generates broadcast-grade Kannada voiceover narration for news reels using:
1. Microsoft Neural Edge-TTS (kn-IN-GaganNeural - Male, kn-IN-SapnaNeural - Female)
   -> Free, unlimited, native Kannada prosody and flawless local pronunciation.
2. Google Gemini Flash TTS (using Gemini API Key with gemini-2.5-flash-preview-tts)
   -> Generative multimodal audio with prebuilt voices.
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
from typing import Optional

from .content import Story

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


def build_narration_script(story: Story) -> str:
    """Compose a broadcast-grade television journalist narration script from a Story.
    
    Transforms print news bullet points into a dramatic, authoritative,
    flowing TV news anchor delivery:
      1. Television anchor greeting / intro hook
      2. Spoken news lead (adapting print headlines without awkward punctuation)
      3. Standfirst ground context (deck)
      4. Ground developments with journalistic transitions ('ಇನ್ನು...', 'ಇದೇ ವೇಳೆ...')
      5. Public safety advisory (if present)
      6. Signature TV anchor sign-off ('ಕ್ಷಣ ಕ್ಷಣದ ನಿಖರ ಕರಾವಳಿ ಸುದ್ದಿಗಳಿಗಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿ ಫಾಲೋ ಮಾಡಿ...')
    """
    if getattr(story, 'narration_script', None) and story.narration_script.strip():
        return story.narration_script.strip()

    sentences: list[str] = []

    # 1. Anchor Hook / Intro
    is_urgent = any(k in story.headline or k in (story.deck or '')
                    for k in ['ಅಪಘಾತ', 'ಸಾವು', 'ಕಳವು', 'ಪೊಲೀಸ್', 'ಬಂಧನ', 'ದಾಳಿ', 'ಪಲ್ಟಿ', 'ದುರಂತ'])
    if is_urgent:
        sentences.append('ನಮಸ್ಕಾರ, ಊರ್ಮನಿ ಸುದ್ದಿಯ ಪ್ರಮುಖ ಸುದ್ದಿ.')
    else:
        sentences.append('ನಮಸ್ಕಾರ, ಊರ್ಮನಿ ಸುದ್ದಿಯ ಕರಾವಳಿ ವಿಶೇಷ ವರದಿಗೆ ಸ್ವಾಗತ.')

    # 2. Spoken Headline Adaptation
    hl = (story.headline or '').strip()
    if hl:
        if ':' in hl:
            parts = [p.strip() for p in hl.split(':', 1)]
            prefix, rest = parts[0], parts[1]
            if any(k in rest for k in ['ಅಪಘಾತ', 'ಸಾವು', 'ಪಲ್ಟಿ']):
                hl_spoken = f"{prefix} ಬಳಿ ಭೀಕರ ಅಪಘಾತ ಸಂಭವಿಸಿದ್ದು, {rest}"
            else:
                hl_spoken = f"{prefix}ದಲ್ಲಿ {rest}"
        else:
            hl_spoken = hl
        hl_spoken = hl_spoken.rstrip('.!?;:') + '.'
        sentences.append(hl_spoken)

    # 3. Ground Context (Deck)
    deck = (story.deck or '').strip()
    if deck:
        deck_spoken = deck.replace(';', ', ಹಾಗೂ').rstrip('.!?;:') + '.'
        sentences.append(deck_spoken)

    # 4. Detailed Facts / Ground Developments
    if story.points:
        transitions = ['ಇನ್ನು, ', 'ಇದೇ ವೇಳೆ, ', 'ಸ್ಥಳೀಯ ವರದಿಗಳ ಪ್ರಕಾರ, ']
        for idx, pt in enumerate(story.points):
            p_clean = pt.strip().rstrip('.!?;:')
            if not p_clean:
                continue
            if idx > 0 and idx - 1 < len(transitions):
                if not any(p_clean.startswith(t.strip()) for t in ['ಇನ್ನು', 'ಇದೇ', 'ಆದರೆ', 'ಸ್ಥಳ']):
                    p_clean = transitions[idx - 1] + p_clean
            sentences.append(p_clean + '.')

    # 5. Public Advisory
    if story.takeaway:
        tk = story.takeaway.strip().replace(';', ',').rstrip('.!?;:')
        if tk:
            sentences.append(f'ಸಾರ್ವಜನಿಕರ ಗಮನಕ್ಕೆ: {tk}.')

    # 6. Signature Anchor Sign-off
    sentences.append('ಕ್ಷಣ ಕ್ಷಣದ ನಿಖರ ಕರಾವಳಿ ಸುದ್ದಿಗಳಿಗಾಗಿ ಊರ್ಮನಿ ಸುದ್ದಿ ಫಾಲೋ ಮಾಡಿ — ಇದು ನಮ್ಮ ಊರು, ನಮ್ಮ ಧ್ವನಿ.')

    script = ' '.join(sentences)
    script = re.sub(r'[\r\n\t]+', ' ', script)
    script = re.sub(r'\s+', ' ', script)
    script = script.replace('▪', '').replace('•', '').replace('—', ', ')
    script = re.sub(r'\s*,\s*', ', ', script)
    script = re.sub(r'\s*\.\s*', '. ', script).strip()
    return script


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
