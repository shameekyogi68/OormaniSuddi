"""
ಊರ್ಮನಿ ಸುದ್ದಿ — a Kannada-capable ear for the reel's voice (D146)
==================================================================
On 2026-10-30 a reel went out in which the voice never said the town of story 2
(ವಂಡ್ಸೆ — the clip held "ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ…" and nothing before it), clipped the first
word of that story's card (ಕಪ್ಪು → "ಹೂ"), read a man's name as three sentences
(ಮಹೇಶ್ ಪಿ.ಎಸ್:), and said the town in the opening as "ಒನ್ ಸೇ". Every check had run. The
one that listens — Whisper, brand/reel_audit.py — cannot read Kannada: it writes a
clean clip as noise ("ಹಸಿಕಿಕಸ", "ಪು ಸೈಯನಿಕ") and scores a clip with a missing town 0.87, so
it could not tell a slip from its own mistakes and the gate could only say "listen for it".

This module listens with a model that can read Kannada, the way a person would:

  * BLIND. The listener is never shown the script. A listener told what to expect hears it
    (that is how people "hear" a word that was never said); asked only to write down the
    sounds, it wrote "ಒನ್ ಸೇ" for a town the voice had spoilt, and nothing at all where a
    word was missing.
  * WORD BY WORD, against what was meant — the screen's spelling, not the respelling the voice
    was handed. A missing town fails the clip; a sentence that scores 0.9 overall does not hide it.
  * A NAME is held to a higher standard than a word. A town, a person, an office: heard at least
    `Limits.ear_name_coverage` whole, or the clip is asked for again.
  * MORE THAN ONE EAR. The listeners are Gemini audio models; each has its own free allowance per
    key (20 a day, measured 2026-10-30), so a reel's dozen listens never meets a wall, a spent
    model/key is skipped until Google says it resets, and a second model confirms an ordinary word
    before it costs a re-take. The strictest ear goes first — a lenient one "corrects" what it
    hears (it wrote ವಂದ್ಸೆ where the strict ones, and Whisper, heard "ಒನ್ ಸೇ").

What it cannot do, said plainly (docs/REEL_STANDARD.md §6): it cannot judge accent, warmth or
whether a name sounds like the place's own people say it. It hears whether the right WORDS were
said, whole, in order. The owner's ear is still the last word on a name — `scripts/town_clips.py`.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import voice
from .reel_audit import phonetic
from .tokens import Limits

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'build' / 'ear_cache'
STATE = ROOT / 'build' / 'ear_state.json'

# Strictest first. 3-flash-preview reproduced every spoilt sound it was given ("ಒನ್ಸೆ", "ಎಡ್ತೆರೆ"); 3.5-flash is quick but
# lenient on a name. Each model has its own 20-a-day allowance per key; none of the slower 3.7/3.8 models is used.
MODELS = ('gemini-3-flash-preview', 'gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.1-flash-lite')

PROMPT = ('Transcribe this Kannada news-anchor audio in Kannada script, EXACTLY as pronounced, sound by sound. '
          'Do not correct, normalise or guess the intended word: if a word sounds odd, write the odd sound; '
          'if a word or a syllable is swallowed or missing, leave it out. Write English words in Kannada script. '
          'Output only the transcript.')

_lock = threading.Lock()
_last_call = [0.0]
_cool: dict[str, float] = {}               # (model:key) → monotonic time before which a per-minute limit holds
MIN_GAP = 1.0                              # seconds between calls — the free tier has a per-minute limit too


class EarUnavailable(RuntimeError):
    """Nobody could listen: no key, or every model's daily allowance is spent. Never holds a day by itself."""


# ── who may be asked ─────────────────────────────────────────────────────
def _tag(model: str, key: str) -> str:
    return 'ear:' + model + ':' + hashlib.sha256(key.encode()).hexdigest()[:10]       # never the key itself


def _spent(tag: str) -> bool:
    try:
        return time.time() < json.loads(STATE.read_text(encoding='utf-8')).get(tag, 0)
    except (OSError, ValueError):
        return False


def _mark_spent(tag: str, seconds: float) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        try:
            st = json.loads(STATE.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            st = {}
        st[tag] = time.time() + max(600.0, seconds)
        STATE.write_text(json.dumps(st), encoding='utf-8')
    except OSError:
        pass


def _post(model: str, key: str, data: bytes, timeout: float) -> str:
    payload = {'contents': [{'parts': [{'text': PROMPT}, {'inline_data': {'mime_type': 'audio/wav',
                                                                          'data': base64.b64encode(data).decode()}}]}],
               'generationConfig': {'temperature': 0.0, 'maxOutputTokens': 1500}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        j = json.loads(r.read())
    parts = (j.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
    return ''.join(p.get('text', '') for p in parts).strip()


def hear(wav: str | Path, models: tuple[str, ...] | None = None, timeout: float = 60.0) -> dict:
    """{text, model} — what a listener wrote down for this recording, blind. Cached by the recording's bytes.

    Raises EarUnavailable when nobody can be asked."""
    data = Path(wav).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    want = tuple(models or MODELS)
    for m in want:                                             # a listener that already heard these exact bytes
        cached = CACHE / f'{digest}.{m}.json'
        if cached.exists():
            try:
                return json.loads(cached.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                pass
    keys = voice.load_gemini_keys()
    if not keys:
        raise EarUnavailable('no Gemini key')
    last = ''
    for m in want:
        for key in keys:
            tag = _tag(m, key)
            if _spent(tag) or _cool.get(tag, 0) > time.monotonic():
                continue
            with _lock:                                        # one call at a time, a second apart
                wait = MIN_GAP - (time.monotonic() - _last_call[0])
                if wait > 0:
                    time.sleep(wait)
                _last_call[0] = time.monotonic()
            try:
                text = _post(m, key, data, timeout)
            except urllib.error.HTTPError as e:
                body = ''
                try:
                    body = e.read().decode('utf-8', 'replace')
                except Exception:                              # noqa: BLE001
                    pass
                last = f'{m}: HTTP {e.code}'
                if e.code == 429:
                    if 'PerDay' in body or 'per day' in body.lower():
                        mt = re.search(r'retry in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s', body)
                        _mark_spent(tag, (int(mt.group(1) or 0) * 3600 + int(mt.group(2) or 0) * 60 + float(mt.group(3))) if mt else 10800)
                    else:
                        _cool[tag] = time.monotonic() + 20
                elif e.code in (400, 401, 403, 404):
                    _mark_spent(tag, 3600)                     # a key or model this account cannot use: do not ask again soon
                continue
            except Exception as e:                             # noqa: BLE001 — a timeout, a reset: the next listener
                last = f'{m}: {type(e).__name__}'
                continue
            if not text:
                last = f'{m}: wrote nothing'
                continue
            res = {'text': text, 'model': m}
            try:
                CACHE.mkdir(parents=True, exist_ok=True)
                (CACHE / f'{digest}.{m}.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
            except OSError:
                pass
            return res
    raise EarUnavailable(last or 'every listener is spent for today')


# ── what was heard against what was meant ────────────────────────────────
def _plain(text: str) -> list[str]:
    return [w for w in (t.strip('.,;:!?"“”()[]‌') for t in text.split()) if w]


def _hits(words: list[str], heard: str, fn) -> list[tuple[str, list[bool]]]:
    """Each word's sounds under `fn`, and which of them were found, in order, in what was heard. Run together, so a
    listener that splits or joins words does not matter."""
    from . import reel_speech as RS
    heard = RS.numbers_to_words(heard)
    ps = [fn(w) for w in words]
    a, b = ''.join(ps), fn(heard)
    hit = [False] * len(a)
    for i, _j, n in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(i, i + n):
            hit[k] = True
    out, pos = [], 0
    for p in ps:
        out.append((p, hit[pos:pos + len(p)]))
        pos += len(p)
    return out


def coverage(words: list[str], heard: str) -> list[float]:
    """For each word asked for, the fraction of its sounds found, in order, in what was heard (0..1).

    The comparison is on the consonant skeleton (brand/reel_audit.phonetic): vowel length and the near-twins a listener
    spells its own way are collapsed, so a right word spelt differently still scores 1.0 — while a word that is
    missing, or another word, does not."""
    return [1.0 if not p else sum(h) / len(p) for p, h in _hits(words, heard, phonetic)]


# ── a name is heard with its clusters (D147) ─────────────────────────────
# The skeleton above cannot tell ಬ್ರ from ಬರ: on 2026-11-01 the voice said "ಬರ-ಹ-ಮಾವರ", Whisper wrote "ಬರಹ ಮಾವರ", and the
# skeleton of that is the skeleton of ಬ್ರಹ್ಮಾವರ. A NAME is compared on its shape: where two consonants are joined (a
# virama between them) there is no vowel, and a listener that heard one there heard the name said wrong.
JOIN = '\u0cdc'                       # an unassigned code point in the Kannada block: "these two consonants are joined"
_CONS = '[ಕ-ಹ]'


def shape(text: str, doubled: bool = True) -> str:
    """The skeleton, with a JOIN mark between consonants said together. What people write two ways for one sound is one
    shape: ಬ್ರಮ್ಹ is ಬ್ರಹ್ಮ (the ಹ said after its partner), ಮಂದಾರ್ತಿ is ಮನ್ದಾರ್ತಿ (a nasal written out). `doubled=False` lets a
    doubled consonant (ತ್ತ, ಮ್ಮ) pass as single — for Whisper, which writes ಸಿಬ್ಬಂದಿ as "ಸಿಬಂದಿ" on a clean clip."""
    t = re.sub('[\u200c\u200d]', '', text)
    if not doubled:
        t = re.sub('ಹ(' + _CONS + ')', lambda m: m.group(1) + '್ಹ' if m.group(1) != 'ಹ' else m.group(0), t)
    t = re.sub('ಹ್(' + _CONS + ')', lambda m: m.group(1) + '್ಹ' if m.group(1) != 'ಹ' else m.group(0), t)
    t = re.sub('([ನಣಮಙಞ])್(?=(' + _CONS + '))', lambda m: m.group(0) if m.group(1) == m.group(2) else 'ನ್', t)
    t = re.sub('ಂ(?=' + _CONS + ')', 'ನ್', t)
    t = re.sub(r'(' + _CONS + r')್\s*(?=(' + _CONS + r'))',
               lambda m: m.group(1) if (not doubled and m.group(1) == m.group(2)) else m.group(1) + JOIN, t)
    return phonetic(t)


def _name_heard(words: list[str], heard: str, i: int, lenient: bool) -> float:
    """How much of name `words[i]`'s sounds were heard (its joins are not counted as sounds, so they cannot dilute a
    changed consonant); at most 0.5 when any join in it was heard with a vowel put inside."""
    p, h = _hits(words, heard, lambda w: shape(w, doubled=not lenient))[i]
    sounds = [ok for c, ok in zip(p, h) if c != JOIN]
    score = sum(sounds) / len(sounds) if sounds else 1.0
    if any(c == JOIN and not ok for c, ok in zip(p, h)):
        return min(0.5, score)
    return score


def name_said(name: str, heard: str, lenient: bool = False) -> bool:
    """Was `name` heard said right somewhere in `heard`? Judged against the one to three heard words that sound most
    like it — compared against a whole sentence, a name could borrow a sound or a join from another word."""
    ws, p = _plain(heard), phonetic(name)
    if not ws or not p:
        return False
    spans = [' '.join(ws[i:i + n]) for n in (1, 2, 3) for i in range(len(ws) - n + 1)]
    best = max(spans, key=lambda t: (difflib.SequenceMatcher(None, p, phonetic(t), autojunk=False).ratio(), -len(t)))
    v = judge(name, best, (name,), lenient=lenient)
    return name not in v['lost'] + v['changed']


def looping(text: str) -> bool:
    """A transcript that has run away with itself — the same word or phrase three times over, or a broken character.
    Whisper does this on a clip it cannot follow (2026-10-31: "…ಗೇವಿದ್ಯಾರ್ತಿಗಳಿಗೆ ×5"); such a transcript is not a hearing,
    and it must not "find" a word a Kannada-capable ear heard missing."""
    if '\ufffd' in text:
        return True
    ws = _plain(text)
    for n in (1, 2, 3):
        for i in range(len(ws) - 3 * n + 1):
            if ws[i:i + n] == ws[i + n:i + 2 * n] == ws[i + 2 * n:i + 3 * n]:
                return True
    return False


def judge(script: str, heard: str, names: tuple[str, ...] = (), edges: bool = False, lenient: bool = False) -> dict:
    """{ok, lost, changed, weak, extra, first_lost, last_lost, score}: a clip against the words it was asked to say.

    `names` are words held to Limits.ear_name_coverage (a town, a person). With `edges`, the first and last words —
    where a cut can eat a sound — are held to Limits.ear_edge_coverage. `lenient` is for a weak ear (Whisper writes a
    clean Kannada clip as noise): an ordinary word counts only if it is clearly absent; a name is held the same."""
    words = _plain(script)
    cov = coverage(words, heard)
    lost, changed, weak = [], [], []
    for i, (w, c) in enumerate(zip(words, cov)):
        p = phonetic(w)
        if len(p) < 2:
            continue
        is_name = _is_name(w, names)
        if is_name:                                         # a name is heard by its shape, clusters and all, by every ear (D147)
            c = _name_heard(words, heard, i, lenient)
        floor = Limits.ear_name_coverage if is_name else Limits.ear_word_coverage
        if lenient and not is_name:
            floor = min(floor, 0.34)
        if edges and i in (0, len(words) - 1):             # where a cut eats a sound — and a re-cut costs no voice request
            floor = max(floor, Limits.ear_edge_coverage)
        if c < floor:
            (lost if c < 0.34 else changed).append(w)
        elif c < 0.85:
            weak.append(w)
    a, b = phonetic(script), phonetic(heard)
    # a headline whose tail carries the card's first words (a cut that fell late) says more than it was given
    extra = bool(a) and not lenient and len(b) > 1.4 * len(a)
    bad = set(lost + changed)
    return dict(ok=not bad and not extra, lost=lost, changed=changed, weak=weak, extra=extra,
                first_lost=bool(words) and words[0] in bad, last_lost=bool(words) and words[-1] in bad,
                score=round(sum(cov) / len(cov), 3) if cov else 1.0, heard=heard, lenient=lenient,
                first=words[0] if words else '', last=words[-1] if words else '')


def combine(results: list[dict], names: tuple[str, ...] = ()) -> dict:
    """Several ears' verdicts on one clip, as one. A NAME any ear fails is failed — a lenient ear that calls a spoilt
    name right is exactly the failure to guard against. An ordinary word is failed only if every Kannada-capable ear that
    judged it failed it: one weak ear's noise must not cost a re-take (each costs one of the day's ten voice requests) —
    and the weak ear (Whisper) cannot outvote them either: on 2026-10-31 its runaway transcript "found" a headline's last
    word that the Gemini ear had heard missing, and the reel went out with that word on the next card (D147)."""
    if len(results) == 1:
        return results[0]
    strict = [r for r in results if not r.get('lenient')] or results
    bad_strict = [set(r['lost'] + r['changed']) for r in strict]
    every = set.intersection(*bad_strict) if bad_strict else set()
    anyone = set.union(*[set(r['lost'] + r['changed']) for r in results])
    bad = every | {w for w in anyone if _is_name(w, names)}
    base = results[0]
    keep = lambda ws: [w for w in ws if w in bad]                                    # noqa: E731
    lost = sorted({w for r in results for w in keep(r['lost'])})
    changed = sorted({w for r in results for w in keep(r['changed'])} - set(lost))
    extra = any(r['extra'] for r in results)
    first, last = base.get('first', ''), base.get('last', '')
    return dict(ok=not bad and not extra, lost=lost, changed=changed,
                weak=sorted({w for r in results for w in r['weak']} - bad), extra=extra,
                first_lost=(first in bad) if first else base['first_lost'] and bool(bad),
                last_lost=(last in bad) if last else base['last_lost'] and bool(bad),
                score=round(min(r['score'] for r in results), 3), heard=base['heard'])


def listen(script: str, wav: str | Path, names: tuple[str, ...] = (), edges: bool = False, whisper: str | None = None) -> dict:
    """One clip, heard and judged by every ear that is available — the Gemini listeners (strictest first, blind) and,
    when given, `whisper`, the transcript the reel's own Whisper already made (the ear that is always there).

    {ok, lost, changed, weak, extra, heard, ears:[…], unavailable?}. When nobody but Whisper could listen, `unavailable`
    says so and the gate reports it — a quiet ear is never a pass."""
    verdicts, ears, heard, unavailable = [], [], {}, ''
    if whisper is not None:
        heard['whisper'] = whisper
        if not looping(whisper):                              # a runaway transcript is not a hearing (D147)
            verdicts.append(judge(script, whisper, names, edges, lenient=True))
            ears.append('whisper')
    try:
        first = hear(wav)
        verdicts.insert(0, judge(script, first['text'], names, edges))
        ears.insert(0, first['model'])
        heard[first['model']] = first['text']
        if verdicts[0]['lost'] or verdicts[0]['changed']:
            try:                                                # a second Gemini ear on a failure, if one is left
                second = hear(wav, tuple(m for m in MODELS if m != first['model']))
                verdicts.insert(1, judge(script, second['text'], names, edges))
                ears.insert(1, second['model'])
                heard[second['model']] = second['text']
            except EarUnavailable:
                pass
    except EarUnavailable as e:
        unavailable = str(e)
    said = [n for n in names if any(_is_name(w, (n,)) for w in _plain(script))]
    if not verdicts:
        return dict(ok=True, lost=[], changed=[], weak=[], extra=False, first_lost=False, last_lost=False, score=1.0,
                    heard='', ears=[], heard_by=heard, unavailable=unavailable or 'nobody could listen',
                    names=said, names_unheard=said)
    res = combine(verdicts, names)
    res.update(ears=ears, heard_by=heard, names=said)
    res['heard'] = heard.get(ears[0], res['heard'])
    if unavailable:
        res['unavailable'] = unavailable
    if said and all(e == 'whisper' for e in ears):
        # Whisper alone is not enough for a name: it cannot read Kannada. A name no Kannada-capable ear heard is held (D147).
        res['names_unheard'] = said
    return res


def _is_name(word: str, names: tuple[str, ...]) -> bool:
    """`word` is one of the names, or the name with an ending on it (ಬೈಂದೂರಿನಲ್ಲಿ for ಬೈಂದೂರು)."""
    p = phonetic(word)
    if not p:
        return False
    for n in names:
        q = phonetic(n)
        if q and (p == q or (len(q) >= 4 and p.startswith(q[:-1]))):
            return True
    return False
