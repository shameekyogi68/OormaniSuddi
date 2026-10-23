"""
ಊರ್ಮನಿ ಸುದ್ದಿ — the ಸುದ್ದಿ ಸಾರ reel (D132)
=========================================
The day's ಸುದ್ದಿ ಸಾರ stories as ONE 9:16 video for Instagram Reels, Facebook
Reels and YouTube Shorts, made beside the carousel from the same stories and
the same copy. Ink & Gold: deep navy, white type, a gold card — no pictures,
ever, as the format promises.

    front page (whole at frame 0) → one beat per story → follow card → frame 0

Why Chrome draws it: Kannada conjuncts shape correctly in the browser at any
size, and the motion it needs — soft-edged masks, the gold light riding the
letters (D98, D129), a card that re-shapes between states — is CSS. The page
(`saara_reel.html`) is a pure function of time: `boot()` lays everything out
once, `render(t)` poses every element for that instant. This module drives it
over the DevTools protocol one frame at a time, so every frame is exact and the
same input always gives the same film.

Voice: the house Google voice reads each story's reel_line (or headline), then
its deck word by word on screen. The picture is cut from the measured clips —
the same principle as brand/voice.py's segmented narration.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from . import voice
from .content import Edition, Story
from .tokens import Brand, Limits, Motion as M

BASE = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_name('saara_reel.html')
CHROME = os.environ.get('OORMANI_CHROME',
                        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
FOLLOW = 'ಪ್ರತಿದಿನದ ಕರಾವಳಿ|ಸುದ್ದಿಗಾಗಿ ಫಾಲೋ ಮಾಡಿ'          # Brand.follow_kn, broken for the card
# The hook names the towns first — a local thumb stops for its own town — while the
# running order lights up in time with them.
INTRO_SAY = 'ಇಂದಿನ ಸುದ್ದಿ, {towns}.'   # ~3s: no commas between towns, at most three
OUTRO_SAY = 'ಪ್ರತಿದಿನದ ಸುದ್ದಿಗಾಗಿ ಫಾಲೋ ಮಾಡಿ.'
WEEKDAY_KN = ('ಸೋಮವಾರ', 'ಮಂಗಳವಾರ', 'ಬುಧವಾರ', 'ಗುರುವಾರ', 'ಶುಕ್ರವಾರ', 'ಶನಿವಾರ', 'ಭಾನುವಾರ')
MONTH_KN = ('ಜನವರಿ', 'ಫೆಬ್ರವರಿ', 'ಮಾರ್ಚ್', 'ಏಪ್ರಿಲ್', 'ಮೇ', 'ಜೂನ್', 'ಜುಲೈ', 'ಆಗಸ್ಟ್',
            'ಸೆಪ್ಟೆಂಬರ್', 'ಅಕ್ಟೋಬರ್', 'ನವೆಂಬರ್', 'ಡಿಸೆಂಬರ್')


def available() -> bool:
    return os.path.exists(CHROME)


# ── what each story says, in which slot ───────────────────────────────────
def _place(st: Story) -> str:
    return (st.location or '').strip() or st.headline.split('—')[0].split(':')[0].strip()


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


def _story_copy(st: Story) -> dict:
    head = (st.reel_line or st.headline).strip()
    place = _place(st)
    short = place.split('·')[0].split(',')[0].strip()
    say = head if short and short in head else f'{short}, {head}' if short else head
    # reel_support — one complete sentence written for the reel — is shown whole and read;
    # without it the deck is read and rolls in two-line captions (D132)
    body = (st.reel_support or st.deck or (st.points[0] if st.points else '')).strip()
    return dict(place=place, place_short=short, head=head, say_head=say, body=body, teaser=head,
                tone=TONES[CATEGORY_TONE.get(st.category, 'gold')])


def _warnings(copies: list[dict], laid: dict) -> list[str]:
    """Copy that will crowd the frame — said, never silently cut (D132)."""
    out = []
    for c, lines in zip(copies, laid.get('lines', [])):
        if lines > 2:
            out.append(f'{c["place_short"]}: reel_line runs to {lines} lines ({len(c["head"])} chars, '
                       f'aim ≤{Limits.saara_reel_line_chars}) — shorten it for two clean lines')
    return out


# ── the voice, measured ──────────────────────────────────────────────────
TRIM = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,'
        'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,'
        f'atempo={M.saara_reel_tempo}')


def _clip(text: str, wav: Path, engine: str) -> float:
    raw = wav.with_suffix('.mp3')
    voice._synth_one(voice._spoken(text), str(raw), engine, None, None)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(raw), '-af', TRIM,
                    '-ar', '48000', '-ac', '1', str(wav)], check=True)
    return round(voice.get_audio_duration(str(wav)), 3)


def _timeline(durs: dict, n: int, words: dict | None = None) -> dict:
    # the front page holds until the hook has been said
    stories, B = [], max(M.saara_reel_intro, M.saara_reel_hook_at + durs['intro'] + 0.45)
    for i in range(n):
        head_at = B + M.saara_reel_lead
        body_at = head_at + durs[f'h{i}'] + M.saara_reel_gap
        stories.append(dict(B=round(B, 3), headAt=round(head_at, 3), bodyAt=round(body_at, 3),
                            bodyDur=durs[f'b{i}'], words=(words or {}).get(f'b{i}')))
        B = body_at + durs[f'b{i}'] + M.saara_reel_tail
    return dict(stories=stories, outro=round(B, 3), T=round(B + M.saara_reel_close, 3),
                hookAt=M.saara_reel_hook_at, hookDur=durs['intro'],
                hookWords=(words or {}).get('intro'), hookText=(words or {}).get('intro_text'))



# ── where each word falls in its clip ────────────────────────────────────
# Whisper cannot read Kannada (2026-10-23: a clean clip came back as noise), so
# the words are placed from the audio itself: the real pauses anchor the
# punctuation, the words between them share the voiced time by syllables
# (aksharas, not code points — a conjunct is one beat), and each boundary is
# snapped to the nearest dip in the voice.
_LONG = set('ಾೀೂೇೋೈೌ')


def _syllables(word: str) -> float:
    n, after_virama = 0.0, False
    for ch in word:
        o = ord(ch)
        if 0x0C95 <= o <= 0x0CB9 or o == 0x0CDE:
            if not after_virama:
                n += 1
            after_virama = False
        elif 0x0C85 <= o <= 0x0C94:
            n += 1
            after_virama = False
        elif o == 0x0CCD:
            after_virama = True
        elif ch.isdigit():
            n += 2.2                       # a figure is read out as a word
            after_virama = False
        else:
            if ch in _LONG:
                n += 0.25
            elif o in (0x0C82, 0x0C83):
                n += 0.3
            after_virama = False
    if word.rstrip('.,;:!?').endswith('\u0CCD'):
        n += 0.4                           # a closing consonant still sounds
    return max(n, 1.0)


def _word_times(wav: Path, text: str) -> list[list[float]]:
    import numpy as np
    import soundfile as sf
    x, sr = sf.read(str(wav))
    if x.ndim > 1:
        x = x.mean(axis=1)
    hop = int(sr * 0.01)
    fr = len(x) // hop
    rms = np.sqrt(np.mean(x[:fr * hop].reshape(fr, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    voiced = db > db.max() - 32
    words = text.split()
    if not words or fr < 3:
        return [[0.0, len(x) / sr]] * len(words)
    # pauses: unvoiced runs of 90ms or more inside the clip
    pauses, i = [], 0
    while i < fr:
        if not voiced[i]:
            j = i
            while j < fr and not voiced[j]:
                j += 1
            if i > 0 and j < fr and j - i >= 9:
                pauses.append((i, j))
            i = j
        else:
            i += 1
    slots = [k for k, w in enumerate(words[:-1]) if w[-1] in ',;:.!?']
    use = sorted(sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[:len(slots)])
    cuts = [(0, None)] + [(s, p) for s, p in zip(slots[:len(use)], use)]
    starts = [0.0] * len(words)
    ends = [0.0] * len(words)
    first_v = int(np.argmax(voiced))
    last_v = fr - int(np.argmax(voiced[::-1]))
    bounds = []                            # (first word, last word, frame from, frame to)
    a_frame, a_word = first_v, 0
    for slot, pause in cuts[1:]:
        bounds.append((a_word, slot, a_frame, pause[0]))
        a_frame, a_word = pause[1], slot + 1
    bounds.append((a_word, len(words) - 1, a_frame, last_v))
    for w0, w1, f0, f1 in bounds:
        seg = voiced[f0:f1]
        csum = np.concatenate([[0], np.cumsum(seg)])
        wts = [_syllables(w) for w in words[w0:w1 + 1]]
        tot, acc = sum(wts), 0.0
        edges = [f0]
        for wt in wts[:-1]:
            acc += wt
            target = csum[-1] * acc / tot
            f = f0 + int(np.searchsorted(csum, target))
            lo, hi = max(f0 + 1, f - 6), min(f1 - 1, f + 6)
            if hi > lo:
                f = lo + int(np.argmin(db[lo:hi]))        # the dip between two words
            edges.append(f)
        edges.append(f1)
        for k in range(len(wts)):
            starts[w0 + k] = edges[k] * 0.01
            ends[w0 + k] = edges[k + 1] * 0.01
    return [[round(s, 3), round(e, 3)] for s, e in zip(starts, ends)]


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
    html = html.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
    dest.write_text(html, encoding='utf-8')
    return dest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


async def _drive(page: Path, profile: Path, work):
    import websockets
    port = _free_port()
    proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={port}',
                             f'--user-data-dir={profile}', '--hide-scrollbars', '--force-device-scale-factor=1',
                             '--window-size=1080,1920', '--allow-file-access-from-files', '--no-first-run',
                             '--no-default-browser-check', '--disable-background-timer-throttling',
                             '--disable-renderer-backgrounding', '--enable-unsafe-swiftshader', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        target = None
        for _ in range(150):
            try:
                pages = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list'))
                target = next(p for p in pages if p['type'] == 'page')
                break
            except Exception:       # noqa: BLE001 — the browser is still starting
                await asyncio.sleep(0.1)
        if not target:
            raise RuntimeError('Chrome did not start for the ಸುದ್ದಿ ಸಾರ reel')
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
                            raise RuntimeError(f'{method}: {m["error"]}')
                        got = m['result']
                    elif wait_event and m.get('method') == wait_event:
                        seen = True
                return got

            async def js(expr):
                r = await call('Runtime.evaluate', expression=expr, awaitPromise=True, returnByValue=True)
                if 'exceptionDetails' in r:
                    raise RuntimeError(f'saara_reel.html: {r["exceptionDetails"]}')
                return r.get('result', {}).get('value')

            await call('Emulation.setDeviceMetricsOverride', width=1080, height=1920,
                       deviceScaleFactor=1, mobile=False)
            await call('Page.enable')
            await call('Page.navigate', wait_event='Page.loadEventFired', url=page.as_uri())
            laid = await js('boot()')

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
        add(sfx / 'whoosh.wav', s['B'] - 0.32, 0.32, f'w{i}', fx)
    add(clips / 'outro.wav', tl['outro'] + 0.55, 1.0, 'vz', vo)
    add(sfx / 'open.wav', 0.0, 0.45, 'f0', fx)
    add(sfx / 'whoosh.wav', tl['outro'] - 0.32, 0.32, 'wz', fx)
    add(sfx / 'outro.wav', tl['outro'] + 0.1, 0.4, 'fz', fx)
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


# ── the film ─────────────────────────────────────────────────────────────
def render(edition: Edition, out_path: str, stills: list[float] | None = None,
           engine: str = 'google') -> dict:
    """Make the ಸುದ್ದಿ ಸಾರ reel. `edition` carries the saara stories only.

    With `stills`, writes PNG frames at those times beside `out_path` and no
    video — the way designs are reviewed (owner, 2026-10-22).
    """
    if not available():
        raise RuntimeError(f'Google Chrome not found at {CHROME} (set OORMANI_CHROME)')
    stories = edition.stories
    copies = [_story_copy(s) for s in stories]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    work_dir = BASE / 'build'
    work_dir.mkdir(exist_ok=True)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='saara_reel_', dir=work_dir, ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        towns = list(dict.fromkeys(c['place_short'] for c in copies if c['place_short']))
        hook = INTRO_SAY.format(towns=' '.join(towns[:3]))
        durs = {'intro': _clip(hook, tmp / 'intro.wav', engine),
                'outro': _clip(OUTRO_SAY, tmp / 'outro.wav', engine)}
        for i, c in enumerate(copies):
            durs[f'h{i}'] = _clip(c['say_head'], tmp / f'h{i}.wav', engine)
            durs[f'b{i}'] = _clip(c['body'], tmp / f'b{i}.wav', engine)
        words = {f'b{i}': _word_times(tmp / f'b{i}.wav', c['body']) for i, c in enumerate(copies)}
        words['intro'], words['intro_text'] = _word_times(tmp / 'intro.wav', hook), hook.split()
        tl = _timeline(durs, len(stories), words)
        page = _page(edition, copies, tl, tmp / 'reel.html')

        if stills:
            async def shoot(frame):
                made = []
                for t in stills:
                    p = out.with_name(f'{out.stem}_t{t:05.1f}.png')
                    p.write_bytes(await frame(t))
                    made.append(str(p))
                return made
            laid, made = asyncio.run(_drive(page, tmp / 'chrome', shoot))
            return dict(stills=made, seconds=tl['T'], timeline=tl, warnings=_warnings(copies, laid))

        fps = M.saara_reel_fps
        video, mix = tmp / 'video.mp4', tmp / 'mix.wav'
        _mix(tl, tmp, mix)
        n = int(round(tl['T'] * fps))
        enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'image2pipe', '-framerate', str(fps),
                                '-c:v', 'png', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                                '-tune', 'film', '-pix_fmt', 'yuv420p', '-profile:v', 'high', str(video)],
                               stdin=subprocess.PIPE)

        async def film(frame):
            for i in range(n):
                enc.stdin.write(await frame(i / fps))
        try:
            laid, _ = asyncio.run(_drive(page, tmp / 'chrome', film))
        finally:
            enc.stdin.close()
            enc.wait()
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(mix), '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
                        str(out)], check=True)
    return dict(path=str(out), seconds=tl['T'], frames=n, render_seconds=round(time.time() - t0, 1),
                warnings=_warnings(copies, laid))


if __name__ == '__main__':          # python3 -m brand.saara_reel editions/DATE.json [t1,t2,…]
    import sys
    ed = Edition.from_dict(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    sub = Edition(stories=ed.segment('saara'), date=ed.date)
    times = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else None
    print(render(sub, str(BASE / 'out' / ed.date.strftime('%Y-%m-%d') / '_review' / 'saara_reel.mp4'), stills=times))
