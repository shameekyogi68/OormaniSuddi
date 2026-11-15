"""
ಊರ್ಮನಿ ಸುದ್ದಿ — towns the voice cannot say, and the recorded clip that says them (D146)
=====================================================================================
Measured 2026-10-30, on Gemini "Kore" (gemini-2.5-flash-preview-tts), in nine takes of each and three spellings of each:

    ವಂಡ್ಸೆ   → "ಒನ್ ಸೇ" / "ಒಂದು ಸೆ"   (never ವಂಡ್ಸೆ; in one reel not said at all)
    ಉಪ್ಪುಂದ  → "ಒಪ್ಪುಂಡ" / "ಉಪ್ಪುಂಡ"
    ಯಡ್ತರೆ   → "ಎಟ್ರೆ" / "ಎಡ್ತರೆ"

The other 19 coastal towns tried were said right. A spelling that was heard right on one take was heard wrong on the
next, so a cleverer spelling is not a cure (brand/lexicon.py). Asking again costs one of the day's ten voice requests
each time, for a name that will not come.

So a town in this registry is NEVER left to the voice in the opening line, and its dateline is a recorded clip of the
name — spliced in front of the headline, in the same voice — once a PERSON has listened and approved it. A town that is
flagged and has no approved clip is not spoken at all, and the gate holds the package (SND-09) and says why: a missing
spoken town is a visible fault the editor can fix; a wrong one is a mistake on the air.

    python3 scripts/town_clips.py list
    python3 scripts/town_clips.py add ವಂಡ್ಸೆ take.wav --made-with "…"      # file → assets/voice/towns/
    python3 scripts/town_clips.py approve ವಂಡ್ಸೆ --by "<the name the editor gives>"

Never approve in a name the editor has not given — the same rule as `verified_by`.

THE GAZETTEER (D147). Every town is in this registry, and a town is left to the voice only once it has been PROVED: its
spelling heard right — by a Kannada-capable ear and by Whisper, on its shape (brand/ear.shape: no vowel put inside a
cluster) — on each of its last `Limits.town_verify_takes` takes. Every reel adds its own hearings of every town it says
(`record`), so the registry learns; a take heard wrong undoes the proof until it is proved again. A town not proved is
asked for in probe takes during the render; if it is still not proved, the package is held (SND-09). Two reels went out
saying a name wrong after D146 (2026-10-31, 2026-11-01) because nothing required a town to have been heard right before.

    python3 scripts/town_clips.py status                   # every town: proved / not yet / clip / held
    python3 scripts/town_clips.py verify ಬ್ರಹ್ಮಾವರ          # probe takes now (each costs one voice request)
    python3 scripts/town_clips.py seed                     # read the hearings kept in past reels' reports
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from . import ear
from . import reel_speech as RS
from .tokens import Limits

# How a town is said for a probe take: in the dateline position, as a headline opens (D147).
PROBE = '{town}. ಇಂದಿನ ಸುದ್ದಿ.'
KEEP_TAKES = 12

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'assets' / 'voice' / 'towns'
REGISTRY = ROOT / 'assets' / 'voice' / 'towns.json'


def registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save(reg: dict) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def unsayable() -> set[str]:
    """Towns the voice is not left to say."""
    return {t for t, v in registry().items() if v.get('say_inline') is False}


def clip_for(town: str) -> Path | None:
    """The recorded clip of `town`, if a person has approved it."""
    v = registry().get(town) or {}
    if v.get('clip') and (v.get('approved_by') or '').strip():
        p = DIR / v['clip']
        return p if p.exists() else None
    return None


def spelling(town: str) -> str:
    """What the voice is handed for `town` today (assets/pronunciation.json applied)."""
    return RS.spoken(town).strip().rstrip('.')


def verified(town: str) -> bool:
    """Heard right on each of its last Limits.town_verify_takes takes of today's spelling (D147)."""
    say = spelling(town)
    takes = [t for t in (registry().get(town) or {}).get('takes') or [] if t.get('spelling') == say]
    last = takes[-Limits.town_verify_takes:]
    return len(last) >= Limits.town_verify_takes and all(t.get('right') for t in last)


def status(town: str) -> str:
    """'say' (proved: the voice says it), 'unverified' (not yet proved — the voice says it, the render probes it, and the
    gate holds it if it is still not proved), 'clip' (a recorded, approved clip), or 'missing' (flagged, no approved clip)."""
    if town in unsayable():
        return 'clip' if clip_for(town) else 'missing'
    return 'say' if verified(town) else 'unverified'


def heard_right(town: str, heard_by: dict) -> bool | None:
    """Was `town` heard said right in one clip? True / False, or None when it could not be told — no Kannada-capable ear,
    or no Whisper (a runaway Whisper transcript is not a hearing). Any ear that heard it wrong makes it wrong."""
    ears = {e: t for e, t in (heard_by or {}).items() if t and not (e == 'whisper' and ear.looping(t))}
    if 'whisper' not in ears or not any(e != 'whisper' for e in ears):
        return None
    return all(ear.name_said(town, t, lenient=(e == 'whisper')) for e, t in ears.items())


def record(town: str, take: dict) -> None:
    """Keep one hearing of `town`: {spelling, right, heard_by, source, on}. The last KEEP_TAKES are kept."""
    reg = registry()
    v = reg.get(town) or {}
    v.setdefault('say_inline', True)
    v['takes'] = ((v.get('takes') or []) + [take])[-KEEP_TAKES:]
    reg[town] = v
    save(reg)


def ensure_listed(towns) -> None:
    """Every town we cover has an entry (copy.PLACE_TAGS is the one registry of places; this one is how each is said)."""
    reg = registry()
    new = [t for t in towns if t and t not in reg]
    for t in new:
        reg[t] = dict(say_inline=True, takes=[])
    if new:
        save(reg)


def without_town(say_head: str, town: str) -> str:
    """The headline the voice is asked for when the dateline is a clip: "ವಂಡ್ಸೆ. ಹಸಿ ಕಸ …" → "ಹಸಿ ಕಸ …"."""
    return re.sub(r'^\s*' + re.escape(town) + r'[\s.,:]*', '', say_head).strip()


def splice(clip: Path, wav: Path, pause: float | None = None) -> float:
    """The town, `pause` seconds of silence, then `wav` — written back to `wav`; returns its seconds."""
    import numpy as np
    import soundfile as sf
    pause = Limits.saara_reel_town_pause if pause is None else pause
    a, sr = sf.read(str(clip))
    b, sr2 = sf.read(str(wav))
    if sr != sr2:
        raise RS.ReelError(f'the clip of {clip.stem} is {sr} Hz and the reel is {sr2} Hz')
    a = a if a.ndim == 1 else a.mean(axis=1)
    b = b if b.ndim == 1 else b.mean(axis=1)
    out = np.concatenate([a, np.zeros(int(pause * sr)), b])
    sf.write(str(wav), out, sr)
    return round(len(out) / sr, 3)


def add(town: str, source: Path, made_with: str, heard: dict | None = None) -> Path:
    """Take a recording of `town`, trim it to its sound, bring it to the house loudness, keep it — NOT yet approved."""
    DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'\W+', '_', town).strip('_') or 'town'
    out = DIR / f'{slug}.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(source), '-af', RS.TRIM, '-ar', '48000', '-ac', '1', str(out)], check=True)
    RS.level(out)
    reg = registry()
    reg[town] = (reg.get(town) or {}) | dict(say_inline=False, clip=out.name, made_with=made_with, heard=heard or {},
                                              approved_by='', approved_on='')
    save(reg)
    return out


def approve(town: str, by: str) -> None:
    reg = registry()
    if town not in reg or not reg[town].get('clip'):
        raise KeyError(f'{town} has no recorded clip to approve')
    if not by.strip():
        raise ValueError('approval needs the name of the person who listened')
    reg[town].update(approved_by=by.strip(), approved_on=date.today().isoformat())
    save(reg)
