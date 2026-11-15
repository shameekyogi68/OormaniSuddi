#!/usr/bin/env python3
"""
A town the voice cannot say gets a recorded clip of its name (D146, brand/town_clips.py).

    python3 scripts/town_clips.py list
    python3 scripts/town_clips.py add ವಂಡ್ಸೆ recording.m4a --made-with "recorded by <who>"
    python3 scripts/town_clips.py approve ವಂಡ್ಸೆ --by "<the name the editor gives>"

The gazetteer (D147) — every town, and whether it is proved (heard right on each of its last Limits.town_verify_takes takes):

    python3 scripts/town_clips.py status                 # every town we cover
    python3 scripts/town_clips.py verify ಬ್ರಹ್ಮಾವರ        # probe takes now: one voice request + one listen each
    python3 scripts/town_clips.py seed                   # read the hearings kept in past reels' reports (no request)

`add` takes any audio file (a Voice Memo, a phone recording), trims it to its sound and brings it to the house
loudness, and keeps it in assets/voice/towns/ — NOT yet used. A person listens to it (it is the word the whole
valley will hear) and `approve` records who. Never approve in a name the editor has not given.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from brand import town_clips as T      # noqa: E402
from brand.tokens import Limits        # noqa: E402


def _seed() -> int:
    """Every hearing of a town kept in a past reel's report, judged again on its shape, into the gazetteer. Idempotent."""
    import glob
    import json
    from brand import copy as C
    from brand import saara_reel as R
    from brand.content import Edition
    T.ensure_listed(list(C.PLACE_TAGS))
    have = {t.get('source') for v in T.registry().values() for t in v.get('takes') or []}
    added = 0
    for rep_path in sorted(glob.glob(os.path.join(ROOT, 'archive', '*', '_review', 'reel_saara_report.json')) +
                           glob.glob(os.path.join(ROOT, 'out', '*', '_review', 'reel_saara_report.json'))):
        day = Path(rep_path).parents[1].name
        ed_path = os.path.join(ROOT, 'editions', f'{day}.json')
        ear = (json.load(open(rep_path, encoding='utf-8')) or {}).get('ear') or {}
        if not ear or not os.path.exists(ed_path):
            continue
        ed = Edition.from_dict(json.load(open(ed_path, encoding='utf-8')))
        copies = R._copies(ed.segment('saara'))
        hook = R._hook_text(copies)
        heard = [('intro', 'the hook', [c['place_short'] for c in copies if c.get('place_short') and c['place_short'] in hook])]
        heard += [(f'h{i}', f'story {i + 1} headline', [c['place_short']]) for i, c in enumerate(copies) if c.get('place_short')]
        for key, label, towns in heard:
            v = ear.get(key) or {}
            for town in dict.fromkeys(towns):
                source = f'reel {day} {label}'
                if source + ' ' + town in have or v.get('trial'):
                    continue
                right = T.heard_right(town, v.get('heard_by') or {})
                if right is None:
                    continue
                T.ensure_listed([town])
                T.record(town, dict(spelling=T.spelling(town), right=right, heard_by=v['heard_by'], source=source, on=day))
                have.add(source + ' ' + town)
                added += 1
                print(f'  {day} {label:18} {town:12} {"heard right" if right else "HEARD WRONG"}')
    print(f'✓ {added} hearing(s) kept')
    return 0


def _verify(town: str, takes: int, respell: str = '') -> int:
    """Probe takes of `town` now, heard back by the Kannada ear and Whisper, kept in the gazetteer. With `respell`, the voice
    is handed that spelling instead (it must be the same sound — ear.shape); if it is heard right on every take it is
    written to assets/pronunciation.json, the only way a respelling gets there (heard right, never a guess)."""
    from brand import ear
    import shutil
    import tempfile
    from datetime import date
    from brand import reel_listen
    from brand import reel_speech as RS
    T.ensure_listed([town])
    if town in T.unsayable():
        print(f'✗ {town} is flagged as a town the voice cannot say — it needs a recorded clip, not a probe')
        return 2
    if respell and ear.shape(respell) != ear.shape(town):
        print(f'✗ {respell} is not the same sound as {town} — a respelling may change how it is written, never what is said')
        return 2
    d = Path(tempfile.mkdtemp(dir=os.path.join(ROOT, 'build')))
    rights = []
    try:
        text = T.PROBE.format(town=town)
        for n in range(takes):
            key = f'probe{n}'
            RS.forget(text, 'gemini')
            with RS.voice.trial_respelling({town: respell} if respell else {}), RS._one_engine('gemini'):
                RS.clip(text, d / f'{key}.wav', 'gemini')
                spelled = T.spelling(town)
            v = reel_listen.hear_rows(d, [dict(label=f'probe of {town}', key=key, text=text, names=(town,), edges=False)])[key]
            right = T.heard_right(town, v.get('heard_by') or {})
            print(f'  take {n + 1}: ' + ' · '.join(f'{e}: "{t[:50]}"' for e, t in (v.get('heard_by') or {}).items()))
            if right is None:
                print('  ✗ no Kannada-capable ear (or no Whisper) could listen — nothing proved; try after 12:30 IST')
                break
            T.record(town, dict(spelling=spelled, right=right, heard_by=v['heard_by'], source='verify', on=date.today().isoformat()))
            rights.append(right)
            print(f'  take {n + 1} ({spelled}): {"heard right" if right else "HEARD WRONG"}')
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if respell and len(rights) == takes and all(rights) and takes >= Limits.town_verify_takes:
        import json
        pron = Path(ROOT) / 'assets' / 'pronunciation.json'
        data = json.loads(pron.read_text(encoding='utf-8'))
        data[town] = respell
        pron.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'✓ {respell} heard right on all {takes} takes — written to assets/pronunciation.json for {town}')
    print(f'{town}: {T.status(town)}')
    return 0 if T.status(town) == 'say' else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    sub.add_parser('status')
    sub.add_parser('seed')
    vp = sub.add_parser('verify')
    vp.add_argument('town')
    vp.add_argument('--takes', type=int, default=Limits.town_verify_takes)
    vp.add_argument('--spelling', default='', help='hand the voice this spelling (same sound) instead')
    a = sub.add_parser('add')
    a.add_argument('town')
    a.add_argument('file')
    a.add_argument('--made-with', required=True, help='who or what made the recording')
    p = sub.add_parser('approve')
    p.add_argument('town')
    p.add_argument('--by', required=True)
    args = ap.parse_args()

    if args.cmd == 'seed':
        return _seed()
    if args.cmd == 'verify':
        return _verify(args.town, args.takes, args.spelling)
    if args.cmd == 'status':
        for town, v in T.registry().items():
            takes = v.get('takes') or []
            st = T.status(town)
            word = {'say': 'PROVED', 'unverified': 'not yet proved', 'clip': 'recorded clip', 'missing': 'HELD — no clip'}[st]
            print(f'{town:14} {word:16} {sum(t["right"] for t in takes)}/{len(takes)} heard right')
        return 0
    if args.cmd == 'list':
        reg = {t: v for t, v in T.registry().items() if v.get('say_inline') is False}
        if not reg:
            print('no town is flagged — the voice is left to say them all, and the ear listens to every one')
        for town, v in reg.items():
            state = ('clip approved by ' + v['approved_by']) if T.clip_for(town) else \
                    ('clip recorded, NOT yet approved — listen to ' + str(T.DIR / v['clip'])) if v.get('clip') else \
                    'NO CLIP — a story datelined here is held until one is recorded and approved'
            print(f'{town:12} {state}\n             {v.get("why", "")[:140]}')
        return 0
    if args.cmd == 'add':
        src = Path(args.file)
        if not src.exists():
            print(f'✗ {src} does not exist', file=sys.stderr)
            return 2
        out = T.add(args.town, src, args.made_with)
        print(f'✓ kept {out} — listen to it, then: python3 scripts/town_clips.py approve {args.town} --by "<name>"')
        return 0
    try:
        T.approve(args.town, args.by)
    except (KeyError, ValueError) as e:
        print(f'✗ {e}', file=sys.stderr)
        return 2
    print(f'✓ {args.town}: approved by {args.by} — it will be the dateline of every story from {args.town}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
