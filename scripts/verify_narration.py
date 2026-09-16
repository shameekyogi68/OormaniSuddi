#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — did the voice actually say the words?
=====================================================
Every check on the narration today reads the TEXT: `check_narration` catches a
₹ before it is spoken, `audio_gaps` catches a silence where the engine stopped
at something it read as a full stop. Neither can hear.

The gap they leave is the one the owner has caught by ear three times: a name
mispronounced, a word dropped, a figure read as two numbers. The fix is a round
trip — transcribe the rendered audio and compare it with the script it was
given. Anything the transcript loses is something a listener will lose too.

    python3 scripts/verify_narration.py out/2026-09-16
    python3 scripts/verify_narration.py out/2026-09-16/reel_01_voiceover.mp3

Whisper is optional and local. `mlx-whisper` is the fast path on Apple Silicon;
`faster-whisper` works anywhere. With neither installed this prints how to get
one and exits 0 — an absent optional dependency must not fail a morning.

    pip install mlx-whisper          # M-series Macs, uses the Neural Engine
    pip install faster-whisper       # anywhere

This does not replace the native ear. It catches the mechanical failures so the
listening time goes on tone and pace, which is what a person is actually for.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Below this, the transcript and the script have genuinely diverged. Kept
# generous: Whisper on Kannada is good, not perfect, and a gate that cries
# wolf on every render gets ignored, which is worse than not having it.
SIMILARITY_FLOOR = 0.70
WORD_LOSS_FLOOR = 0.15      # fraction of script words missing from the transcript


def engine() -> str:
    for mod in ('mlx_whisper', 'faster_whisper'):
        try:
            __import__(mod)
            return mod
        except ImportError:
            continue
    return ''


def transcribe(path: str, model: str = '') -> str:
    eng = engine()
    if eng == 'mlx_whisper':
        import mlx_whisper
        name = model or 'mlx-community/whisper-small-mlx'
        out = mlx_whisper.transcribe(path, path_or_hf_repo=name, language='kn')
        return (out.get('text') or '').strip()
    if eng == 'faster_whisper':
        from faster_whisper import WhisperModel
        m = WhisperModel(model or 'small', device='cpu', compute_type='int8')
        segments, _info = m.transcribe(path, language='kn')
        return ' '.join(s.text for s in segments).strip()
    return ''


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r'[ಀ-೿]+|[A-Za-z]+|\d+', text) if w]


# Kannada agglutinates and a transcriber does not always attach the same case
# ending the script used — ಉಡುಪಿ / ಉಡುಪಿಯಲ್ಲಿ, ಜಿಲ್ಲಾಡಳಿತ / ಜಿಲ್ಲಾಡಳಿತದ. That
# is morphology, not a mispronunciation, and a check that fails on it is a
# check that gets switched off. Comparison happens on stems; the FULL words are
# still what gets reported, because a name is what the editor needs to see.
_STEM = 4


def _stem(word: str) -> str:
    return word[:_STEM].lower() if len(word) > _STEM else word.lower()


def compare(script: str, heard: str) -> dict:
    """What a listener would lose, expressed as numbers."""
    a, b = _words(script), _words(heard)
    sa, sb = [_stem(w) for w in a], [_stem(w) for w in b]
    ratio = difflib.SequenceMatcher(None, sa, sb).ratio() if sa else 1.0
    heard_stems = set(sb)
    missing = [w for w, s in zip(a, sa) if s not in heard_stems]
    loss = len(missing) / len(a) if a else 0.0
    return {'similarity': round(ratio, 3),
            'word_loss': round(loss, 3),
            'script_words': len(a), 'heard_words': len(b),
            'missing': missing[:12]}


def check_file(path: str, script: str, model: str = '') -> dict:
    heard = transcribe(path, model)
    if not heard:
        return {'file': os.path.basename(path), 'skipped': 'no transcript'}
    res = compare(script, heard)
    res['file'] = os.path.basename(path)
    res['heard'] = heard[:400]
    res['pass'] = (res['similarity'] >= SIMILARITY_FLOOR
                   and res['word_loss'] <= WORD_LOSS_FLOOR)
    return res


def scripts_in(outdir: str) -> dict[str, str]:
    """The narration each voiceover was given, read off the copy files."""
    out: dict[str, str] = {}
    for name in sorted(os.listdir(outdir)):
        if not name.endswith('_copy.json'):
            continue
        try:
            with open(os.path.join(outdir, name), encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            continue
        script = (data.get('voiceover_script') or '').strip()
        if not script:
            continue
        stem = name[:-len('_copy.json')]
        out[f'{stem}_voiceover.mp3'] = script
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', help='a render folder, or one voiceover file')
    ap.add_argument('--model', default='', help='override the Whisper model')
    ap.add_argument('--script', default='',
                    help='the intended text, when checking a bare audio file')
    args = ap.parse_args()

    eng = engine()
    if not eng:
        print('Whisper is not installed, so the round trip was skipped.\n\n'
              '    pip install mlx-whisper       # M-series Macs, fastest\n'
              '    pip install faster-whisper    # anywhere\n\n'
              'Until then the narration is checked as TEXT only — which cannot '
              'hear a mispronounced name.')
        return 0
    print(f'  engine: {eng}')

    jobs: list[tuple[str, str]] = []
    if os.path.isdir(args.target):
        pairs = scripts_in(args.target)
        for name, script in pairs.items():
            p = os.path.join(args.target, name)
            if os.path.exists(p):
                jobs.append((p, script))
        if not jobs:
            print(f'  no narrated voiceovers in {args.target}')
            return 0
    else:
        if not args.script:
            print('✗ checking a single file needs --script "<the intended text>"',
                  file=sys.stderr)
            return 1
        jobs.append((args.target, args.script))

    bad = 0
    results = []
    for path, script in jobs:
        print(f'\n  {os.path.basename(path)} …')
        res = check_file(path, script, args.model)
        results.append(res)
        if res.get('skipped'):
            print(f'    ! skipped ({res["skipped"]})')
            continue
        mark = '✓' if res['pass'] else '✗'
        print(f'    {mark} similarity {res["similarity"]:.2f} '
              f'(floor {SIMILARITY_FLOOR}) · '
              f'word loss {res["word_loss"]:.0%} (ceiling {WORD_LOSS_FLOOR:.0%})')
        if res['missing']:
            print(f'    words the transcript never heard: '
                  f'{", ".join(res["missing"])}')
            print('    → if a NAME is in that list, add it to '
                  'assets/pronunciation.json and re-render.')
        if not res['pass']:
            bad += 1

    if os.path.isdir(args.target):
        out = os.path.join(args.target, 'narration_audit.json')
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump({'engine': eng, 'floor': SIMILARITY_FLOOR,
                       'results': results}, fh, indent=2, ensure_ascii=False)
            fh.write('\n')
        print(f'\n  → {os.path.basename(out)}')

    print(f'\n  {len(jobs) - bad}/{len(jobs)} narrations match their script\n')
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
