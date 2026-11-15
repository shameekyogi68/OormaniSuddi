"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the reel's voice, heard back and put right before the film is cut (D146)
=======================================================================================
Every clip the reel is made from is listened to (brand/ear.py) against the words it was asked to say, and a clip that
fails is put right here, in this order, cheapest first:

  1. RE-CUT. A headline and its card come from ONE request, cut apart at the pause. If the cut ate the card's first
     word, or left the card's words on the headline, the same recording is cut at its other silences — no voice
     request spent. (2026-10-30: the card's ಕಪ್ಪು came out "ಹೂ".)
  2. A NEW TAKE, spelling the failing word another way (brand/lexicon.py). Each take is one of the day's ten voice
     requests per key, so there are at most `Limits.ear_takes`, and the best take is the one kept.
  3. HELD. If it still fails, the report says which word, what was heard, and after how many takes — the gate stops
     the package (SND-09). A reel is never published on the hope that an unheard word is right.

Nothing here edits the copy or the lexicon. A name the voice cannot say is a job for a person: a recorded clip
(`brand/town_clips.py`), or a different sentence.

Then THE TOWNS (D147, `vet_towns`): every hearing of every town is kept in the gazetteer (assets/voice/towns.json); a town
that is not yet proved — heard right on each of its last `Limits.town_verify_takes` takes — is asked for in probe takes,
and a town still not proved holds the package. A name is never shipped on one lucky take.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from . import copy as C
from . import ear, lexicon, town_clips
from . import reel_speech as RS
from .tokens import Limits


def _places_in(text: str) -> tuple[str, ...]:
    """Every town we cover that the sentence names — each is held to the name standard (D147)."""
    return tuple(t for t in C.PLACE_TAGS if ' ' not in t and t in text)


def rows(copies: list[dict], hook: str, outro_kn: str) -> list[dict]:
    towns = tuple(dict.fromkeys(c['place_short'] for c in copies if c.get('place_short')))
    out = [dict(label='the hook', key='intro', text=hook, names=tuple(t for t in towns if t in hook), edges=False)]
    for i, c in enumerate(copies):
        town = (c['place_short'],) if c.get('place_short') and c.get('voice_town', 'say') in ('say', 'unverified') else ()
        head = c.get('voice_head', c['say_head'])
        out.append(dict(label=f'story {i + 1} headline', key=f'h{i}', text=head,
                        names=tuple(dict.fromkeys(town + _places_in(head))), edges=True))
        out.append(dict(label=f'story {i + 1} card', key=f'b{i}', text=c['body'], names=_places_in(c['body']), edges=True))
    out.append(dict(label='the follow card', key='outro', text=outro_kn, names=(), edges=False))
    return out


def _whisper(tmp: Path, rs: list[dict]) -> dict[str, str]:
    """What the reel's own Whisper heard in each clip (the ear that is always there), by key; {} if it is away."""
    res = RS.audit([dict(label=r['key'], wav=str(tmp / f"{r['key']}.wav"), text=RS.spoken(r['text'])) for r in rs])
    if 'unavailable' in res:
        return {}
    return {k: v.get('heard', '') for k, v in res.items()}


def hear_rows(tmp: Path, rs: list[dict]) -> dict[str, dict]:
    whisper = _whisper(tmp, rs)
    out = {}
    for r in rs:
        out[r['key']] = ear.listen(RS.spoken(r['text'], respell=False), tmp / f"{r['key']}.wav", r['names'], r['edges'],
                                   whisper=whisper.get(r['key']))
    return out


def _bad(v: dict) -> list[str]:
    return list(dict.fromkeys(v['lost'] + v['changed']))


def _rank(vs: list[dict]) -> tuple:
    """Fewer failing words is better; then the higher score."""
    return (sum(len(_bad(v)) + (1 if v['extra'] else 0) for v in vs), -min(v['score'] for v in vs))


def _trial(vs: list[dict], texts: list[str], take: int) -> dict[str, str]:
    """The next spelling of each failing word that actually appears in the text the voice is given."""
    trial: dict[str, str] = {}
    joined = ' '.join(texts)
    for v in vs:
        for w in _bad(v):
            cands = lexicon.candidates(w)
            if cands and w in joined:
                trial[w] = cands[(take - 1) % len(cands)]
    return trial


def _summary(v: dict, takes: int, cuts: int, trial: dict | None = None) -> dict:
    out = dict(ok=v['ok'], lost=v['lost'], changed=v['changed'], weak=v['weak'], extra=v['extra'], takes=takes, recuts=cuts,
               heard=v['heard'], ears=v['ears'], heard_by=v.get('heard_by', {}), unavailable=v.get('unavailable', ''),
               names=v.get('names', []))
    if v.get('names_unheard'):
        out['names_unheard'] = v['names_unheard']
    if trial:
        out['trial'] = trial
    return out


def _note(log: list | None, rs: list[dict], heard: dict[str, dict], trial: dict | None) -> None:
    """Keep every hearing of every town in a clip — the takes that failed are evidence too (D147)."""
    if log is None:
        return
    for r in rs:
        v = heard.get(r['key']) or {}
        for town in r['names']:
            log.append((town, (trial or {}).get(town) or town_clips.spelling(town), v.get('heard_by') or {}, r['label']))


def run(tmp: Path, copies: list[dict], hook: str, outro_kn: str, durs: dict,
        ask_pair: Callable[[int, dict], tuple[float, float]], ask_single: Callable[[str, dict], float],
        log: Callable[[str], None] = lambda s: None, heard_log: list | None = None) -> dict:
    """Listen to every clip, put right what fails, return {key: summary}. `durs` is updated in place for any clip that
    was cut again or asked for again. `ask_pair(i, trial)` / `ask_single(key, trial)` make a NEW take with the trial
    respellings in force and return the seconds."""
    rs = rows(copies, hook, outro_kn)
    by_key = {r['key']: r for r in rs}
    verdicts = hear_rows(tmp, rs)
    _note(heard_log, rs, verdicts, None)
    report: dict[str, dict] = {}

    # the opening and the close: one clip, one request
    for key in ('intro', 'outro'):
        v, takes, best, trial = verdicts[key], 1, None, None
        while not v['ok'] and takes < Limits.ear_takes:
            if best is None or _rank([v]) < _rank([best[0]]):
                best = (v, tmp / f'{key}.best.wav')
                shutil.copy(tmp / f'{key}.wav', best[1])
            log(f'      ! {by_key[key]["label"]}: heard "{v["heard"][:60]}" — missing/changed {" ".join(_bad(v))}; asking again (take {takes + 1})')
            trial = _trial([v], [by_key[key]['text']], takes)
            durs[key] = ask_single(key, trial)
            takes += 1
            again = hear_rows(tmp, [by_key[key]])
            _note(heard_log, [by_key[key]], again, trial)
            v = again[key]
        if best is not None and not v['ok'] and _rank([best[0]]) < _rank([v]):
            shutil.copy(best[1], tmp / f'{key}.wav')
            durs[key] = RS.voice.get_audio_duration(str(tmp / f'{key}.wav'))
            v = best[0]
        report[key] = _summary(v, takes, 0, trial if best is None or v is not best[0] else None)

    # a story's headline and its card
    for i in range(len(copies)):
        hk, bk = f'h{i}', f'b{i}'
        vh, vb = verdicts[hk], verdicts[bk]
        takes, cuts, tried, trial = 1, 0, set(), None
        full = tmp / f'{hk}.pair.wav'
        best = None
        while not (vh['ok'] and vb['ok']):
            late = vh['extra'] or vb['first_lost']                  # the cut fell inside the card's first word
            early = vh['last_lost'] and not late                    # …or inside the headline's last
            mid_file = full.with_suffix('.cut')
            if (late or early) and full.exists() and mid_file.exists() and cuts < 3:
                mid = float(mid_file.read_text())
                options = [c for c in RS.other_cuts(full, mid) if (c < mid if late else c > mid) and round(c, 2) not in tried]
                if options:
                    cut = options[0]
                    tried.add(round(cut, 2))
                    cuts += 1
                    log(f'      ! story {i + 1}: the cut at {mid:.2f}s ate a word — cutting again at {cut:.2f}s')
                    durs[hk], durs[bk] = RS.cut_pair(full, tmp / f'{hk}.wav', tmp / f'{bk}.wav', cut)
                    again = hear_rows(tmp, [by_key[hk], by_key[bk]])
                    _note(heard_log, [by_key[hk], by_key[bk]], again, trial)
                    vh, vb = again[hk], again[bk]
                    continue
            if takes >= Limits.ear_takes:
                break
            if best is None or _rank([vh, vb]) < _rank(best[0]):
                for k in (hk, bk):
                    shutil.copy(tmp / f'{k}.wav', tmp / f'{k}.best.wav')
                best = ([vh, vb], dict(durs), trial)
            log(f'      ! story {i + 1}: {" ".join(_bad(vh) + _bad(vb)) or "the cut"} — asking again (take {takes + 1})')
            trial = _trial([vh, vb], [by_key[hk]['text'], by_key[bk]['text']], takes)
            durs[hk], durs[bk] = ask_pair(i, trial)
            takes += 1
            cuts, tried = 0, set()
            again = hear_rows(tmp, [by_key[hk], by_key[bk]])
            _note(heard_log, [by_key[hk], by_key[bk]], again, trial)
            vh, vb = again[hk], again[bk]
        if best is not None and not (vh['ok'] and vb['ok']) and _rank(best[0]) < _rank([vh, vb]):
            for k in (hk, bk):
                shutil.copy(tmp / f'{k}.best.wav', tmp / f'{k}.wav')
                durs[k] = best[1][k]
            vh, vb = best[0]
            trial = best[2]
        report[hk], report[bk] = _summary(vh, takes, cuts, trial), _summary(vb, takes, cuts, trial)
    return report


def vet_towns(tmp: Path, copies: list[dict], hook: str, report: dict, heard_log: list,
              ask_probe: Callable[[str, str], float], source: str, log: Callable[[str], None] = lambda s: None) -> dict:
    """The gazetteer step (D147). Keep every hearing of every town; probe a town not yet proved, at most
    `Limits.town_verify_takes` voice requests each; mark a town still not proved on every clip that says it, so the gate
    holds the package. Returns {town: status}."""
    from datetime import date
    on = date.today().isoformat()
    for town, spelling, heard_by, label in heard_log:
        right = town_clips.heard_right(town, heard_by)
        if right is not None:
            town_clips.record(town, dict(spelling=spelling, right=right, heard_by=heard_by, source=f'{source} {label}', on=on))
    rs = {r['key']: r for r in rows(copies, hook, '')}
    towns = list(dict.fromkeys(list(rs['intro']['names']) +
                               [c['place_short'] for c in copies if c.get('voice_town', 'say') in ('say', 'unverified')
                                and c.get('place_short')]))
    out = {}
    for town in towns:
        n = 0
        while not town_clips.verified(town) and n < Limits.town_verify_takes:
            key = f'probe{len(out)}_{n}'
            text = town_clips.PROBE.format(town=town)
            log(f'      ! {town} is not yet proved — probe take {n + 1}')
            ask_probe(text, key)
            row = dict(label=f'probe of {town}', key=key, text=text, names=(town,), edges=False)
            v = hear_rows(tmp, [row])[key]
            right = town_clips.heard_right(town, v.get('heard_by') or {})
            n += 1
            if right is None:                                   # nobody who can tell is listening: stop spending the voice
                break
            town_clips.record(town, dict(spelling=town_clips.spelling(town), right=right, heard_by=v.get('heard_by'),
                                         source=f'{source} probe', on=on))
        out[town] = 'say' if town_clips.verified(town) else 'unverified'
        if out[town] == 'unverified':
            for key, r in rs.items():
                if town in r['names'] and key in report and (key == 'intro' or key.startswith('h')):
                    report[key]['town_unverified'] = town
    return out
