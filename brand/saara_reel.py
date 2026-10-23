"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the ಸುದ್ದಿ ಸಾರ reel (D132)
=========================================
The day's ಸುದ್ದಿ ಸಾರ stories as ONE 9:16 video for Instagram Reels, Facebook
Reels and YouTube Shorts. Since 2026-10-23 this is what ಸುದ್ದಿ ಸಾರ IS: the
carousel is kept, switched off (`Limits.saara_carousel_default`), for the day it
is wanted again. Ink & Gold: deep navy, white type, a gold card — no pictures,
ever, as the format promises.

    front page (whole at frame 0) → one beat per story → follow card → frame 0

Nobody tunes this by hand. It has to come out right on a day nobody has seen:

  * every beat is cut from the MEASURED voice (brand/reel_speech.py), and each
    word's place inside its clip is measured too, so the picture cannot drift;
  * if the voice would take the film past `Limits.saara_reel_max_seconds` the
    beats are tightened (never the speech), and if that is not enough the copy
    is named as too long — never silently cut;
  * the page fits itself: headline size and lines, the card, the running order,
    the town tag; and reports anything that still does not fit (VID-07);
  * a figure is spoken as Kannada words, and anything that may still be
    misread is listed (SND-08);
  * one voice only: if Google fails three times the render stops and says so,
    and the pipeline falls back to the carousel rather than post nothing.

Why Chrome draws it: Kannada conjuncts shape correctly in the browser at any
size, and the motion it needs — soft-edged masks, the gold light riding the
letters (D98, D129), a card that re-shapes between states — is CSS and WebGL.
The page (`saara_reel.html`) is a pure function of time: `boot()` lays
everything out once, `render(t)` poses every element for that instant. This
module drives it over the DevTools protocol one frame at a time, so every frame
is exact and the same input always gives the same film.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from . import reel_speech as RS
from .content import Edition, Story
from .reel_speech import ReelError                     # noqa: F401  (the pipeline catches it)


class ReelFitError(ReelError):
    """The COPY does not fit the reel. Drawing it again would not change that, so it is never retried."""
from .tokens import Brand, Limits, Motion as M

BASE = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_name('saara_reel.html')
CHROME = os.environ.get('OORMANI_CHROME',
                        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
FILE = 'reel_saara.mp4'
COVER = 'reel_saara_cover.jpg'
REPORT = 'reel_saara_report.json'                      # in _review/, read by the gate
FOLLOW = 'ಪ್ರತಿದಿನದ ಕರಾವಳಿ|ಸುದ್ದಿಗಾಗಿ ಫಾಲೋ ಮಾಡಿ'          # Brand.follow_kn, broken for the card
# The hook names the towns first — a local thumb stops for its own town — while the
# running order lights up in time with them.
INTRO_SAY = 'ಇಂದಿನ ಸುದ್ದಿ, {towns}.'   # ~3s: no commas between towns, at most three
OUTRO_SAY = 'ಪ್ರತಿದಿನದ ಸುದ್ದಿಗಾಗಿ ಫಾಲೋ ಮಾಡಿ.'
WEEKDAY_KN = ('ಸೋಮವಾರ', 'ಮಂಗಳವಾರ', 'ಬುಧವಾರ', 'ಗುರುವಾರ', 'ಶುಕ್ರವಾರ', 'ಶನಿವಾರ', 'ಭಾನುವಾರ')
MONTH_KN = ('ಜನವರಿ', 'ಫೆಬ್ರವರಿ', 'ಮಾರ್ಚ್', 'ಏಪ್ರಿಲ್', 'ಮೇ', 'ಜೂನ್', 'ಜುಲೈ', 'ಆಗಸ್ಟ್',
            'ಸೆಪ್ಟೆಂಬರ್', 'ಅಕ್ಟೋಬರ್', 'ನವೆಂಬರ್', 'ಡಿಸೆಂಬರ್')

# Names the engine and its tests have always used.
_syllables = RS.syllables
_word_times = lambda wav, text: RS.word_times(wav, text)[0]        # noqa: E731


def available() -> bool:
    return os.path.exists(CHROME)


# ── what each story says, in which slot ───────────────────────────────────
# The background's two lights per kind of story (linear RGB 0..1), from the logo's
# palette and tokens.CATEGORIES: gold for what is celebrated, the sea for what is
# governed or fished, ember for sport, a deep red for harm.
TONES = {
    'gold':   [[.96, .66, .04], [.95, .42, .06]],
    'sea':    [[.10, .52, .66], [.80, .55, .08]],
    'ember':  [[.95, .40, .06], [.96, .66, .04]],
    'harm':   [[.62, .07, .07], [.90, .32, .06]],
    'indigo': [[.30, .34, .78], [.80, .55, .08]],
    'moss':   [[.22, .52, .30], [.80, .55, .08]],
}
CATEGORY_TONE = {'culture': 'gold', 'obituary': 'indigo', 'civic': 'sea', 'fisheries': 'sea', 'nri': 'sea',
                 'explainer': 'sea', 'sport': 'ember', 'weather': 'ember', 'breaking': 'harm', 'crime': 'harm',
                 'accident': 'harm', 'education': 'indigo', 'health': 'indigo', 'farm': 'moss', 'environment': 'moss'}

_KICKER = re.compile(r'^\s*([^:—–\-]{2,28}?)\s*[:—–]\s+(.+)$')


def _place(st: Story) -> tuple[str, str]:
    """(the tag's text, the one town the voice and the running order use)."""
    parts = [p.strip() for p in re.split(r'[,·/;&]|\s+ಮತ್ತು\s+|\s+-\s+', st.location or '') if p.strip()]
    if not parts:
        m = _KICKER.match(st.headline)
        parts = [m.group(1)] if m else [Brand.coverage]
    return ' · '.join(parts[:2]), parts[0]


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r'(?<=[.!?।])\s+', text.strip()) if s]


def _support_options(st: Story) -> list[str]:
    """Every sentence the story already has that could stand alone on the card —
    never one that is invented, never one that is cut."""
    out: list[str] = []
    sents = _sentences(st.deck)
    if sents:
        out.append(sents[0])
        if len(sents) > 1:
            out.append(f'{sents[0]} {sents[1]}')
    out += [p.strip() for p in st.points if p.strip()]
    if st.takeaway.strip():
        out.append(st.takeaway.strip())
    return [o for o in dict.fromkeys(out) if len(o) >= 18]


def _story_copy(st: Story) -> dict:
    place, short = _place(st)
    notes: list[str] = []
    head = (st.reel_line or '').strip()
    if not head:
        m = _KICKER.match(st.headline)
        head = (m.group(2) if m and short and m.group(1).strip().startswith(short[:3]) else st.headline).strip()
        notes.append('no reel_line — used the headline')
    say = head if short and short in head else f'{short}, {head}' if short else head
    # reel_support — one complete sentence written for the reel — is shown whole and read.
    # Without it the card takes the story's own sentence that fits the clock best (below).
    return dict(place=place, place_short=short, head=head, say_head=say, body=(st.reel_support or '').strip(),
                options=_support_options(st), teaser=head,
                tone=TONES[CATEGORY_TONE.get(st.category, 'gold')], notes=notes)


def _copies(stories: list[Story]) -> list[dict]:
    """Each story's slots, the card sentence chosen against the clock (D132).

    A story the intake desk gave a `reel_support` keeps it. One that has none takes,
    from sentences it already carries (the deck's first, its points, its takeaway),
    the LONGEST that fits its share of the reel — so a day written for the carousel
    still comes out as a reel of the right length, saying only what the story says."""
    copies = [_story_copy(st) for st in stories]
    n = len(copies)
    per = budget(n)['spoken_chars_per_story']
    for i, c in enumerate(copies):
        if c['body']:
            continue
        room = per - len(c['say_head'])
        fits = [o for o in c['options'] if len(o) <= room]
        pick = max(fits, key=len) if fits else (min(c['options'], key=len) if c['options'] else '')
        c['body'] = pick
        c['notes'].append('no reel_support — the card uses the story\'s own sentence '
                          + ('that fits' if fits else 'that is shortest (it still runs long)'))
        if not pick:
            c['notes'].append('NOTHING to put on the card — the story has no deck, points or takeaway')
    return copies


_WEEKDAYS = {'ಸೋಮವಾರ': 0, 'ಮಂಗಳವಾರ': 1, 'ಬುಧವಾರ': 2, 'ಗುರುವಾರ': 3, 'ಶುಕ್ರವಾರ': 4, 'ಶನಿವಾರ': 5, 'ಭಾನುವಾರ': 6}


def editor_questions(edition: Edition) -> list[str]:
    """What only the editor can settle — raised, never "fixed". The dress rehearsal found one: a story
    about "ಮಂಗಳವಾರದ" procession in an edition dated a Thursday is either stale or about next week."""
    out = []
    day = edition.date.weekday()
    for i, st in enumerate(edition.stories, 1):
        text = ' '.join([st.headline, st.deck, st.reel_line, st.reel_support, *st.points])
        named = sorted({w for w in _WEEKDAYS if w in text and _WEEKDAYS[w] != day})
        if named:
            out.append(f'story {i} ({_place(st)[1]}) names {" / ".join(named)}, but this edition is dated '
                       f'{WEEKDAY_KN[day]} {edition.date.day} {MONTH_KN[edition.date.month - 1]} — is it already '
                       'past, or next week? Leave the copy as the paste has it and ask')
    return out


# ── the budget, before a word is spoken ──────────────────────────────────
def _est(text: str) -> float:
    return max(1.0, len(RS.spoken(text)) * M.saara_reel_sec_per_char)


def _hook_text(copies: list[dict]) -> str:
    towns = list(dict.fromkeys(c['place_short'] for c in copies if c['place_short']))
    return INTRO_SAY.format(towns=' '.join(towns[:3]))


def budget(n: int) -> dict:
    """What the copy may weigh for `n` stories, so intake can write to it."""
    beats = M.saara_reel_lead_min + M.saara_reel_gap_min + M.saara_reel_tail_min
    spare = Limits.saara_reel_max_seconds - 3.2 - 3.4 - n * (beats + 0.4)
    per_story = spare / max(1, n) / M.saara_reel_sec_per_char
    return dict(stories=n, spoken_chars_per_story=int(per_story),
                support_chars=int(per_story - 40), support_words=max(5, int((per_story - 40) / 9)),
                head_chars=Limits.saara_reel_line_chars)


def estimate(copies: list[dict]) -> float:
    n = len(copies)
    t = max(M.saara_reel_intro, M.saara_reel_hook_at + _est(_hook_text(copies)) + M.saara_reel_hook_hold)
    for c in copies:
        t += M.saara_reel_lead + _est(c['say_head']) + M.saara_reel_gap + _est(c['body']) + M.saara_reel_tail
    return round(t + max(M.saara_reel_close, 0.55 + _est(OUTRO_SAY) + 0.6), 1)


def _warnings(copies: list[dict], laid: dict, info: dict | None = None) -> list[str]:
    """Copy that will crowd the frame or the clock — said, never silently cut (D132)."""
    out, info = [], info or {}
    n = len(copies)
    b = budget(n)
    for i, c in enumerate(copies):
        lines = (laid.get('lines') or [0] * n)[i] if i < len(laid.get('lines') or []) else 0
        if lines > 2:
            out.append(f'story {i + 1} ({c["place_short"]}): reel_line runs to {lines} lines '
                       f'({len(c["head"])} chars, aim ≤{Limits.saara_reel_line_chars}) — shorten it for two clean lines')
        if len(c['body']) > b['support_chars'] + 25:
            out.append(f'story {i + 1} ({c["place_short"]}): the card sentence is {len(c["body"])} chars '
                       f'(~{len(c["body"].split())} words); for {n} stories keep it under ~{b["support_chars"]} '
                       f'chars (~{b["support_words"]} words)')
        for note in c.get('notes', []):
            out.append(f'story {i + 1} ({c["place_short"]}): {note}')
    for i, how in enumerate(info.get('timing') or []):
        if how != 'measured':
            out.append(f'story {i + 1}: word timing fell back to an even split — the highlight may drift a little')
    voice = info.get('voice') or {}
    if 'unavailable' in voice:
        out.append(f'the voice was NOT heard back ({voice["unavailable"]}) — listen to it once')
    else:
        listen, weak = _voice_findings(voice)
        out.extend(f'voice check — {w}' for w in weak)
        if listen:
            out.append('voice check — a speech model could not match these words, so listen for them: '
                       + ' · '.join(listen))
    if info.get('compress'):
        out.append(f'the voice would run {info["natural"]:.1f}s; beats were tightened to fit '
                   f'{Limits.saara_reel_max_seconds:.0f}s (speech untouched)')
    if info.get('over', 0) > 0.05:
        longest = max(range(n), key=lambda i: len(copies[i]['say_head']) + len(copies[i]['body']))
        out.append(f'the reel runs {info["seconds"]:.1f}s — over the house {Limits.saara_reel_max_seconds:.0f}s. '
                   f'Shorten story {longest + 1} ({copies[longest]["place_short"]}), the longest, '
                   f'or move a story out of ಸುದ್ದಿ ಸಾರ')
    return out


# ── the timeline ─────────────────────────────────────────────────────────
def _timeline(durs: dict, n: int, words: dict | None = None, towns: list[str] | None = None,
              cap: float | None = None) -> dict:
    """Every beat, in seconds, cut from the measured clips. If the natural cut is
    longer than `cap` the PAUSES are tightened, never the speech."""
    words = words or {}
    cap = Limits.saara_reel_max_seconds if cap is None else cap

    def cut(lead, gap, tail, close, hold):
        stories, B = [], max(M.saara_reel_intro if hold == M.saara_reel_hook_hold else 0.0,
                             M.saara_reel_hook_at + durs['intro'] + hold)
        for i in range(n):
            head_at = B + lead
            body_at = head_at + durs[f'h{i}'] + gap
            stories.append(dict(B=round(B, 3), headAt=round(head_at, 3), bodyAt=round(body_at, 3),
                                bodyDur=durs[f'b{i}'], words=words.get(f'b{i}')))
            B = body_at + durs[f'b{i}'] + tail
        tail_close = max(close, 0.55 + durs['outro'] + 0.6)           # the last word ends before the fold
        return stories, round(B, 3), round(B + tail_close, 3)

    natural = cut(M.saara_reel_lead, M.saara_reel_gap, M.saara_reel_tail, M.saara_reel_close, M.saara_reel_hook_hold)
    chosen, level = natural, 0
    if natural[2] > cap:
        chosen = cut(M.saara_reel_lead_min, M.saara_reel_gap_min, M.saara_reel_tail_min,
                     M.saara_reel_close_min, 0.25)
        level = 1
    stories, outro, T = chosen
    hook_words = words.get('intro')
    hook_text = words.get('intro_text') or []
    # when each running-order row lights: as its town is said, else spread over the hook
    row_at = []
    for i in range(n):
        town = (towns or [''] * n)[i]
        k = next((j for j, w in enumerate(hook_text) if w.strip('.,') == town), -1)
        if hook_words and k >= 0:
            row_at.append(round(M.saara_reel_hook_at + hook_words[k][0], 3))
        else:
            row_at.append(round(M.saara_reel_hook_at + durs['intro'] * 0.7 * i / max(1, n - 1), 3))
    return dict(stories=stories, outro=outro, T=T, hookAt=M.saara_reel_hook_at, hookDur=durs['intro'],
                hookWords=hook_words, hookText=hook_text, rowAt=row_at,
                compress=level, natural=natural[2], over=round(max(0.0, T - cap), 3))


# ── the page and the browser ─────────────────────────────────────────────
def _page(edition: Edition, copies: list[dict], tl: dict, dest: Path) -> Path:
    d = edition.date
    data = dict(date=f'{WEEKDAY_KN[d.weekday()]}, {d.day} {MONTH_KN[d.month - 1]}',
                follow=FOLLOW, handle=Brand.handle, timeline=tl, stories=copies)
    html = PAGE.read_text(encoding='utf-8')
    for k, v in {'{{KN}}': (BASE / 'fonts/NotoSansKannada-Bold.ttf').as_uri(),
                 '{{ANEK}}': (BASE / 'fonts/AnekKannada-Variable.ttf').as_uri(),
                 '{{KNSERIF}}': (BASE / 'fonts/NotoSerifKannada-Black.ttf').as_uri(),
                 '{{LOGO}}': (BASE / 'assets/oormani_suddi_round_logo_bg_erased.png').as_uri(),
                 '{{BRAND}}': Brand.name}.items():
        html = html.replace(k, v)
    # the copy sits inside a <script>: a stray "</script>" or "<!--" in it must not end the page
    blob = json.dumps(data, ensure_ascii=False).replace('</', '<\\/').replace('<!--', '<\\!--')
    html = html.replace('/*DATA*/null', blob)
    dest.write_text(html, encoding='utf-8')
    return dest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


async def _drive(page: Path, profile: Path, work, gate=None):
    import websockets
    port = _free_port()
    proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={port}',
                             f'--user-data-dir={profile}', '--hide-scrollbars', '--force-device-scale-factor=1',
                             '--window-size=1080,1920', '--allow-file-access-from-files', '--no-first-run',
                             '--no-default-browser-check', '--disable-background-timer-throttling',
                             '--disable-renderer-backgrounding', '--enable-unsafe-swiftshader',
                             '--disable-extensions', '--disable-sync', '--disable-component-update',
                             '--disable-background-networking', '--mute-audio', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = None
        for _ in range(200):
            try:
                pages = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'))
                target = next(p for p in pages if p['type'] == 'page')
                break
            except Exception:       # noqa: BLE001 — the browser is still starting
                await asyncio.sleep(0.1)
        if not target:
            raise ReelError('Chrome did not start for the ಸುದ್ದಿ ಸಾರ reel')
        async with websockets.connect(target['webSocketDebuggerUrl'], max_size=2 ** 30) as ws:
            n = 0

            async def call(method, wait_event=None, **params):
                nonlocal n
                n += 1
                my = n
                await ws.send(json.dumps({'id': my, 'method': method, 'params': params}))
                got, seen = None, wait_event is None
                while got is None or not seen:
                    m = json.loads(await ws.recv())
                    if m.get('id') == my:
                        if 'error' in m:
                            raise ReelError(f'{method}: {m["error"]}')
                        got = m['result']
                    elif wait_event and m.get('method') == wait_event:
                        seen = True
                return got

            async def js(expr):
                r = await call('Runtime.evaluate', expression=expr, awaitPromise=True, returnByValue=True)
                if 'exceptionDetails' in r:
                    raise ReelError(f'saara_reel.html: {r["exceptionDetails"]}')
                return r.get('result', {}).get('value')

            await call('Emulation.setDeviceMetricsOverride', width=1080, height=1920,
                       deviceScaleFactor=1, mobile=False)
            await call('Page.enable')
            await call('Page.navigate', wait_event='Page.loadEventFired', url=page.as_uri())
            laid = await js('boot()')
            if gate:
                gate(laid)

            async def frame(t: float) -> bytes:
                await js(f'render({t:.5f})')
                shot = await call('Page.captureScreenshot', format='png', optimizeForSpeed=True)
                return base64.b64decode(shot['data'])

            return laid, await work(frame)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)       # the profile is deleted next; let Chrome finish writing it
        except subprocess.TimeoutExpired:
            proc.kill()


# ── sound ────────────────────────────────────────────────────────────────
def _mix(tl: dict, clips: Path, out: Path) -> None:
    sfx, T = BASE / 'assets/sfx', tl['T']
    args, chains, vo, fx = [], [], [], []

    def add(path: Path, at: float, vol: float, label: str, bus: list):
        args.extend(['-i', str(path)])
        i = args.count('-i') - 1
        ms = max(0, int(at * 1000))
        chains.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol},adelay={ms}|{ms}[{label}]')
        bus.append(label)

    add(clips / 'intro.wav', 0.30, 1.0, 'v0', vo)
    for i, s in enumerate(tl['stories']):
        add(clips / f'h{i}.wav', s['headAt'], 1.0, f'h{i}', vo)
        add(clips / f'b{i}.wav', s['bodyAt'], 1.0, f'b{i}', vo)
        add(sfx / 'whoosh.wav', s['B'] - 0.32, 0.32, f'w{i}', fx)      # the wash of light crossing
        add(sfx / 'pop.wav', s['B'] + 0.10, 0.26, f'p{i}', fx)          # the town tag landing
    add(clips / 'outro.wav', tl['outro'] + 0.55, 1.0, 'vz', vo)
    add(sfx / 'open.wav', 0.0, 0.45, 'f0', fx)
    for k, at in enumerate(sorted(set(tl['rowAt']))):                   # each row of the running order
        add(sfx / 'tick.wav', at + 0.04, 0.20, f't{k}', fx)
    add(sfx / 'whoosh.wav', tl['outro'] - 0.32, 0.32, 'wz', fx)
    add(sfx / 'outro.wav', tl['outro'] + 0.1, 0.4, 'fz', fx)
    add(sfx / 'press.wav', tl['outro'] + 1.80, 0.5, 'fp', fx)           # the follow button, pressed
    args.extend(['-stream_loop', '-1', '-i', str(BASE / 'assets/news_bgm.mp3')])
    bed = args.count('-i') - 1
    g = ';'.join(chains)
    g += f';{"".join(f"[{v}]" for v in vo)}amix=inputs={len(vo)}:normalize=0,apad=whole_dur={T},asplit=2[vox][side]'
    g += (f';[{bed}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{T},volume=0.42,'
          f'afade=t=in:d=0.4,afade=t=out:st={T - 1.4:.3f}:d=1.4[bed0]')
    g += ';[bed0][side]sidechaincompress=threshold=0.025:ratio=7:attack=25:release=420[bed]'
    g += (f';[vox][bed]{"".join(f"[{f}]" for f in fx)}amix=inputs={2 + len(fx)}:normalize=0,'
          f'apad=whole_dur={T},atrim=0:{T},loudnorm=I={Limits.lufs}:TP=-1.5:LRA=11[mix]')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *args, '-filter_complex', g, '-map', '[mix]',
                    '-ar', '48000', '-c:a', 'pcm_s16le', str(out)], check=True)


# ── the clips, the timeline, the page ────────────────────────────────────
def _voice_findings(voice: dict) -> tuple[list[str], list[str]]:
    """(the words to listen for, the clips that did not sound like their words)."""
    if 'unavailable' in voice:
        return [], []
    listen, weak = [], []
    for label, v in voice.items():
        if v['similarity'] < Limits.saara_reel_voice_warn:
            weak.append(f'{label}: heard back at {v["similarity"]:.2f} (a right voice scores 0.96+); '
                        f'it said "{v.get("heard", "")[:70]}"')
        elif v['suspects']:
            listen.append(f'{label}: {" ".join(v["suspects"])}')
    return listen, weak


def _build(edition: Edition, tmp: Path, engine: str) -> dict:
    stories = edition.stories
    copies = _copies(stories)
    hook = _hook_text(copies)
    plan = [('intro', hook, 'the hook'), ('outro', OUTRO_SAY, 'the follow card')]
    for i, c in enumerate(copies):
        plan += [(f'h{i}', c['say_head'], f'story {i + 1} headline'), (f'b{i}', c['body'], f'story {i + 1} card')]
    durs = {k: RS.clip(text, tmp / f'{k}.wav', engine) for k, text, _ in plan}

    # Hear the clips back (a speech model, in its own process). A clip that does not sound like its
    # words — noise, silence, the wrong thing — is asked for once more; if it is still wrong the
    # render stops and says which, rather than post a reel that talks nonsense (D133).
    def items(rows):
        return [dict(label=label, wav=str(tmp / f'{k}.wav'), text=RS.spoken(text)) for k, text, label in rows]
    voice = RS.audit(items(plan))
    if 'unavailable' not in voice:
        bad = [row for row in plan if voice[row[2]]['similarity'] < Limits.saara_reel_voice_fail]
        for k, text, label in bad:
            RS.forget(text, engine)
            durs[k] = RS.clip(text, tmp / f'{k}.wav', engine)
        if bad:
            again = RS.audit(items(bad))
            if 'unavailable' not in again:
                voice.update(again)
                still = [r for r in bad if voice[r[2]]['similarity'] < Limits.saara_reel_voice_fail]
                if still:
                    raise ReelError('the voice does not say what it was given — '
                                    + '; '.join(f'{lab} (heard back at {voice[lab]["similarity"]:.2f}: '
                                                f'"{voice[lab].get("heard", "")[:60]}")' for _k, _t, lab in still))
    words, timing = {}, []
    for i, c in enumerate(copies):
        words[f'b{i}'], how = RS.word_times(tmp / f'b{i}.wav', c['body'])
        timing.append(how)
    words['intro'], _ = RS.word_times(tmp / 'intro.wav', hook)
    words['intro_text'] = hook.split()
    tl = _timeline(durs, len(stories), words, [c['place_short'] for c in copies])
    if tl['T'] > Limits.reel_fail_seconds:
        longest = max(range(len(copies)), key=lambda i: durs[f'h{i}'] + durs[f'b{i}'])
        raise ReelFitError(f'the spoken reel runs {tl["T"]:.0f}s — the house fails anything over '
                           f'{Limits.reel_fail_seconds:.0f}s. Shorten the reel_line and reel_support of story '
                           f'{longest + 1} ({copies[longest]["place_short"]}), the longest — about '
                           f'{budget(len(copies))["support_chars"]} chars for the card with {len(copies)} stories — '
                           f'or move a story out of ಸುದ್ದಿ ಸಾರ')
    pron = {f'story {i + 1}': sorted(set(RS.lint(c['say_head']) + RS.lint(c['body'])))
            for i, c in enumerate(copies)}
    return dict(copies=copies, tl=tl, durs=durs, timing=timing, hook=hook, voice=voice,
                pron={k: v for k, v in pron.items() if v},
                page=_page(edition, copies, tl, tmp / 'reel.html'))


def check(edition: Edition, shots: str | None = None) -> dict:
    """Lay the reel out and report everything that would not fit or would run long —
    with no voice and no film (a few seconds). The intake desk runs this on the
    day's copy and rewrites until it is clean; the render runs the same checks."""
    if not available():
        raise ReelError(f'Google Chrome not found at {CHROME} (set OORMANI_CHROME)')
    copies = _copies(edition.stories)
    n = len(copies)
    durs = {'intro': _est(_hook_text(copies)), 'outro': _est(OUTRO_SAY)}
    words = {'intro_text': _hook_text(copies).split()}
    for i, c in enumerate(copies):
        durs[f'h{i}'], durs[f'b{i}'] = _est(c['say_head']), _est(c['body'])
        words[f'b{i}'] = RS._even(c['body'].split(), 0.0, durs[f'b{i}'])
    words['intro'] = RS._even(words['intro_text'], 0.0, durs['intro'])
    tl = _timeline(durs, n, words, [c['place_short'] for c in copies])
    work_dir = BASE / 'build'
    work_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='saara_check_', dir=work_dir, ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        page = _page(edition, copies, tl, tmp / 'reel.html')

        async def look(frame):
            if not shots:
                return None
            os.makedirs(shots, exist_ok=True)
            at = [('cover', 0.0)] + [(f's{i + 1}', st['bodyAt'] + 0.6 * st['bodyDur'])
                                     for i, st in enumerate(tl['stories'])] + [('close', tl['outro'] + 2.3)]
            for name, t in at:
                Path(shots, f'{name}.png').write_bytes(await frame(t))
            return None
        laid, _ = asyncio.run(_drive(page, tmp / 'chrome', look))
    info = dict(compress=tl['compress'], natural=tl['natural'], over=tl['over'], seconds=tl['T'], timing=[])
    pron = {f'story {i + 1}': sorted(set(RS.lint(c['say_head']) + RS.lint(c['body'])))
            for i, c in enumerate(copies)}
    return dict(stories=n, estimated_seconds=tl['T'], budget=budget(n), lines=laid.get('lines'), cover=laid.get('cover'),
                questions=editor_questions(edition),
                issues=laid.get('issues', []), warnings=_warnings(copies, laid, info),
                pronunciation={k: v for k, v in pron.items() if v}, copies=copies)


# ── the film ─────────────────────────────────────────────────────────────
def render(edition: Edition, out_path: str, stills: list[float] | None = None,
           engine: str = 'google') -> dict:
    """Make the ಸುದ್ದಿ ಸಾರ reel. `edition` carries the saara stories only.

    With `stills`, writes PNG frames at those times beside `out_path` and no
    video — the way designs are reviewed (owner, 2026-10-22).
    """
    if not available():
        raise ReelError(f'Google Chrome not found at {CHROME} (set OORMANI_CHROME)')
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    work_dir = BASE / 'build'
    work_dir.mkdir(exist_ok=True)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='saara_reel_', dir=work_dir, ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        b = _build(edition, tmp, engine)
        copies, tl = b['copies'], b['tl']
        info = dict(compress=tl['compress'], natural=tl['natural'], over=tl['over'], seconds=tl['T'],
                    timing=b['timing'], voice=b.get('voice') or {})

        def gate(laid):
            if laid.get('issues'):
                raise ReelFitError('the copy does not fit the reel — ' + '; '.join(laid['issues']))

        def summary(laid, **extra):
            return dict(seconds=tl['T'], timeline=tl, lines=laid.get('lines'), issues=laid.get('issues', []),
                        warnings=_warnings(copies, laid, info), pronunciation=b['pron'],
                        timing=b['timing'], clips={k: v for k, v in b['durs'].items()}, voice_audit=b.get('voice') or {}, **extra)

        if stills:
            async def shoot(frame):
                made = []
                for t in stills:
                    p = out.with_name(f'{out.stem}_t{t:05.1f}.png')
                    p.write_bytes(await frame(t))
                    made.append(str(p))
                return made
            laid, made = asyncio.run(_drive(b['page'], tmp / 'chrome', shoot, gate))
            return summary(laid, stills=made)

        fps = M.saara_reel_fps
        video, mix = tmp / 'video.mp4', tmp / 'mix.wav'
        _mix(tl, tmp, mix)
        n = int(round(tl['T'] * fps))
        enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'image2pipe', '-framerate', str(fps),
                                '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                                '-tune', 'film', '-pix_fmt', 'yuv420p', '-profile:v', 'high', str(video)],
                               stdin=subprocess.PIPE)

        written = 0                                      # frames the encoder already has

        async def film(frame):
            nonlocal written
            while written < n:
                enc.stdin.write(await frame(written / fps))
                written += 1

        # Chrome is a browser on a busy Mac: it can be closed under memory pressure or crash. Every
        # frame is a pure function of its time, so a new Chrome simply picks up at the next frame —
        # nothing already drawn is lost, and the film is the same film (D133).
        retries, laid = 3, {}
        try:
            for attempt in range(1, retries + 1):
                try:
                    laid, _ = asyncio.run(_drive(b['page'], tmp / f'chrome{attempt}', film, gate))
                    break
                except ReelFitError:
                    raise
                except Exception as e:                   # noqa: BLE001
                    if attempt == retries:
                        raise ReelError(f'Chrome failed {retries} times, at frame {written} of {n}: '
                                        f'{type(e).__name__}: {e}') from e
                    print(f'      ! Chrome stopped at frame {written} of {n} ({type(e).__name__}: {e}) — '
                          f'carrying on in a fresh one ({attempt}/{retries - 1})', flush=True)
                    time.sleep(2)
        finally:
            enc.stdin.close()
            enc.wait()
        if enc.returncode != 0 or not video.exists():
            raise ReelError('the video encoder failed')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(mix), '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                        str(out)], check=True)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(out), '-frames:v', '1', '-q:v', '2',
                        str(out.with_name(COVER))], check=False)
    return summary(laid, path=str(out), frames=n, render_seconds=round(time.time() - t0, 1),
                   cover=str(out.with_name(COVER)))


def make(edition: Edition, outdir: str, engine: str = 'google') -> dict:
    """The pipeline's entry: the reel, its cover, and the report the gate reads."""
    res = render(edition, os.path.join(outdir, FILE), engine=engine)
    rv = os.path.join(outdir, '_review')
    os.makedirs(rv, exist_ok=True)
    with open(os.path.join(rv, REPORT), 'w', encoding='utf-8') as fh:
        json.dump({k: v for k, v in res.items() if k != 'timeline'} |
                  {'beats': [dict(B=s['B'], headAt=s['headAt'], bodyAt=s['bodyAt']) for s in res['timeline']['stories']],
                   'outro': res['timeline']['outro'], 'compress': res['timeline']['compress']},
                  fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    return res


if __name__ == '__main__':          # python3 -m brand.saara_reel editions/DATE.json [t1,t2,…]
    import sys
    ed = Edition.from_dict(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    sub = Edition(stories=ed.segment('saara'), date=ed.date)
    times = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else None
    print(render(sub, str(BASE / 'out' / ed.date.strftime('%Y-%m-%d') / '_review' / 'saara_reel.mp4'), stills=times))
