#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — JSON in, finished design out.
=============================================

The machine-facing entry point. Anything that can write JSON — a script, a
newsroom tool, an AI given raw copy — can drive the whole design system through
this without knowing any Python.

    python3 render.py editions/DATE.json               # every segment in it
    python3 render.py editions/DATE.json --only saara roundup
    python3 render.py editions/greetings/X.json        # a festival wish
    python3 render.py --describe                       # every format + its rules
    python3 render.py --schema story                   # the input contract
    python3 render.py --check edition.json             # preflight only, render nothing

Reproducibility: pass --at (or set OORMANI_NOW) to pin the clock. Identical
input plus the same --at gives byte-identical output, which is what the golden
tests in tests/ rely on.

Three news formats, and a story runs in exactly one of them — its `segment`
(D92): speed → ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (roundup), saara → ಸುದ್ದಿ ಸಾರ, mukhya → ಮುಖ್ಯ
ಸುದ್ದಿ. The contract and the reasoning live in docs/AI_BRIEF.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, replace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import templates as TP
import brand.copy as copywriter
from brand.content import Story, Edition, ContentError, freeze
from brand.qa import preflight, inspect, compliance
from brand.tokens import Limits

SCHEMAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemas')


# ─────────────────────────────────────────────────────────────────────────────
#  INTROSPECTION — so a caller can learn the rules without reading the source
# ─────────────────────────────────────────────────────────────────────────────

def describe(as_json: bool = False) -> int:
    if as_json:
        print(json.dumps(TP.as_dict(), indent=2, ensure_ascii=False))
        return 0
    for k, s in TP.TEMPLATES.items():
        print(f'\n\033[1m{k}\033[0m  {s.size[0]}×{s.size[1]}  takes={s.takes}  '
              f'produces={s.produces}')
        print(f'  {s.summary}')
        print(f'  WHEN     {s.when}')
        print(f'  REQUIRES {", ".join(s.requires)}')
        if s.accepts:
            print(f'  ACCEPTS  {", ".join(s.accepts)}')
        if s.limits:
            print('  LIMITS   ' + ', '.join(f'{a}={b}' for a, b in s.limits.items()))
        if s.notes:
            print(f'  NOTE     {s.notes}')
    return 0


def show_schema(which: str) -> int:
    p = os.path.join(SCHEMAS, f'{which}.schema.json')
    if not os.path.exists(p):
        print(f'no schema {which!r}; try: story, edition, greeting', file=sys.stderr)
        return 1
    print(open(p, encoding='utf-8').read(), end='')
    return 0


# ─────────────────────────────────────────────────────────────────────────────
#  LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load(path: str):
    """Read JSON and return ('edition', Edition) or ('story', Story)."""
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    if isinstance(raw, list):
        raw = {'stories': raw}
    if isinstance(raw, dict) and raw.get('kind') == 'greeting':
        # A festival wish is not a Story: it has no sources, no status and no
        # headline, and Story.from_dict would rightly reject it. See D54.
        from templates.greeting import Greeting
        return 'greeting', Greeting.from_dict(raw)
    if 'stories' in raw:
        return 'edition', Edition.from_dict(raw)
    raise ContentError('a single story is not rendered on its own any more — '
                       'put it in an edition with a segment (D92)')


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────────────────────────────────────

def write_copy(subject, outdir: str, name: str, voice_script: str | None = None,
               post=None) -> str:
    """Write the post copy next to the artwork.

    Artwork on its own is not a post. Every render gets a .txt you can paste
    from and a .json a scheduler can read. `post` is a prebuilt PostCopy, for
    a format whose caption is not the edition's or the story's default — the
    speed-news reel, which has nothing to swipe.
    """
    c = post or (copywriter.for_edition(subject) if isinstance(subject, Edition)
                 else copywriter.for_story(subject))
    d = c.to_dict()
    if voice_script:
        d['voiceover_script'] = voice_script
    with open(os.path.join(outdir, f'{name}.json'), 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write('\n')
    txt = os.path.join(outdir, f'{name}.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('═══ INSTAGRAM CAPTION ' + '═' * 46 + '\n\n')
        f.write(c.instagram + '\n\n')
        if getattr(c, 'first_comment', ''):
            f.write('═══ INSTAGRAM FIRST COMMENT '
                    '(paste the moment you post) ' + '═' * 8 + '\n\n')
            f.write(c.first_comment + '\n\n')
        if getattr(c, 'whatsapp', ''):
            f.write('═══ WHATSAPP FORWARD ' + '═' * 47 + '\n\n')
            f.write(c.whatsapp + '\n\n')
        f.write('═══ YOUTUBE TITLE ' + '═' * 50 + '\n\n' + c.youtube_title + '\n\n')
        f.write('═══ YOUTUBE DESCRIPTION ' + '═' * 44 + '\n\n')
        f.write(c.youtube_description + '\n\n')
        f.write('═══ YOUTUBE TAGS ' + '═' * 51 + '\n\n')
        f.write(', '.join(c.youtube_tags) + '\n')
        f.write('\n═══ NOTE ' + '═' * 59 + '\n\n')
        f.write('AI-card reels: Instagram only. YouTube gets real footage.\n')
        f.write('Do not cross-post this package to YouTube Shorts unless the '
                'editor explicitly overrides.\n')
        if voice_script:
            f.write('\n═══ KANNADA VOICEOVER NARRATION SCRIPT (READ-OVER) ' + '═' * 20 + '\n\n')
            f.write(voice_script + '\n')

    # And the caption on its own, in its own file — the one you open on a
    # phone at 08:00 and select all of. House rule 2026-09-17-06.
    stem = name[:-5] if name.endswith('_copy') else name
    with open(os.path.join(outdir, f'{stem}_caption.txt'), 'w',
              encoding='utf-8') as f:
        f.write(copywriter.caption_text(c, copywriter.platform_of(stem)))
    if getattr(c, 'whatsapp', ''):
        with open(os.path.join(outdir, f'{stem}_whatsapp.txt'), 'w',
                  encoding='utf-8') as f:
            f.write(c.whatsapp.strip() + '\n')
    return txt


class _NullLog:
    """So render_edition can be called without a log and not know it."""
    def start(self, *a, **k): pass
    def done(self, *a, **k): pass
    def warn(self, *a, **k): pass
    def fail(self, *a, **k): pass
    def event(self, *a, **k): pass


def render_edition(ed: Edition, outdir: str, only: list[str] | None,
                   log=None, animate: bool = False) -> list[tuple[str, str]]:
    """Render every format the edition's stories ask for (D92).

    Each story is drawn in its own segment's format and nowhere else, so the
    same news never runs twice on one day as a carousel AND a reel.

    Segments render in parallel (ThreadPoolExecutor) when more than one is
    requested. The animated scan-wipe step uses its own multiprocessing pool.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    made: list[tuple[str, str]] = []
    want = set(only) if only else None
    log = log or _NullLog()

    def run(key):
        return want is None or key in want

    # ── segment renderers — each returns (made, mukhya_done, prints) ─────
    # They are pure functions of their inputs, writing to distinct files, so
    # running them on threads is safe. PIL releases the GIL during file I/O
    # and each segment spawns its own ffmpeg subprocesses.

    def _render_saara():
        saara = ed.segment('saara')
        if not saara or not run('saara'):
            return [], [], []
        _t = time.time()
        sub = replace(ed, stories=saara)
        segment_made, prints = [], []
        for p in TP.render('saara', sub, outdir):
            segment_made.append((p, 'post'))
            prints.append(f'  ✓ {os.path.basename(p)}')
        write_copy(sub, outdir, 'saara_copy')
        prints.append('  ✓ saara_copy.txt')
        log.done('saara', seconds=round(time.time() - _t, 1),
                 stories=len(saara))
        return segment_made, [], prints

    def _render_mukhya():
        mukhya_stories = ed.segment('mukhya')
        if not mukhya_stories or not run('mukhya'):
            return [], [], []
        segment_made, md, prints = [], [], []
        for k, st in enumerate(mukhya_stories, 1):
            _t = time.time()
            paths = TP.get('mukhya')(st, outdir, k=k)
            for p in paths:
                segment_made.append((p, 'post'))
                prints.append(f'  ✓ {os.path.basename(p)}')
            write_copy(st, outdir, f'mukhya_{k}_copy')
            with open(os.path.join(outdir, f'facebook_group_{k}.txt'), 'w',
                      encoding='utf-8') as fh:
                fh.write(copywriter.facebook_group_post(st) + '\n')
            md.append((k, st.category == 'breaking' and st.is_breaking,
                       os.path.basename(paths[-1])))
            log.done(f'mukhya_{k}', seconds=round(time.time() - _t, 1))
        return segment_made, md, prints

    def _render_roundup():
        speed = ed.segment('speed')
        if not speed or not run('roundup'):
            return [], [], []
        _t = time.time()
        sub = replace(ed, stories=speed)
        segment_made, prints = [], []
        p = os.path.join(outdir, 'roundup.mp4')
        res = TP.render('roundup', sub, p)
        used = replace(ed, stories=speed[:res['stories']])
        write_copy(used, outdir, 'roundup_copy',
                   voice_script='\n'.join(res['spoken']),
                   post=copywriter.for_roundup(used, res['seconds']))
        if os.path.exists(res['cover']):
            segment_made.append((res['cover'], 'story'))
        if res['dropped']:
            prints.append('  ⚠ left out of ಸ್ಪೀಡ್ ನ್ಯೂಸ್ to stay short — move them to '
                          'ಸುದ್ದಿ ಸಾರ or shorten their reel_line: '
                          + ' · '.join(h[:30] for h in res['dropped']))
        log.done('roundup', seconds=round(time.time() - _t, 1),
                 stories=res['stories'])
        return segment_made, [], prints

    # Run all three segments concurrently — they write to different files.
    mukhya_done: list[tuple[int, bool, str]] = []
    fns = [_render_saara, _render_mukhya, _render_roundup]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in fns}
        for fut in as_completed(futures):
            segment_made, md, prints = fut.result()
            made.extend(segment_made)
            mukhya_done.extend(md)
            for line in prints:
                print(line)

    # The animated twin of every carousel slide (D98): the scan wipe.
    # animate_all() uses multiprocessing.Pool internally — all slides encode
    # in parallel across CPU cores.
    if animate:
        from brand.animate import animate_all
        _t = time.time()
        stills = [p for p, _k in made
                  if re.match(r'(saara|mukhya_\d+)_', os.path.basename(p))
                  and p.endswith('.jpg')]
        vids = animate_all(stills)
        for v in vids:
            print(f'  ✓ {os.path.basename(v)}  (animated)')
        log.done('animate', seconds=round(time.time() - _t, 1), slides=len(vids))

    # The publishing plan, derived from what was actually rendered, so it can
    # never list a post that does not exist (D43).
    slides = sorted(f for f in os.listdir(outdir)
                    if f.startswith('saara_') and (f.endswith('.mp4') if animate else f.endswith('.jpg')))
    plan = copywriter.publishing_plan(
        has_saara=os.path.exists(os.path.join(outdir, 'saara_01_cover.mp4' if animate else 'saara_01_cover.jpg')),
        saara_last=slides[-1] if slides else '',
        mukhya=mukhya_done,
        has_roundup=os.path.exists(os.path.join(outdir, 'roundup.mp4')),
        animated=animate)
    if plan:
        with open(os.path.join(outdir, 'schedule.txt'), 'w', encoding='utf-8') as f:
            f.write(copywriter.plan_text(plan, ed.date_kn))
        with open(os.path.join(outdir, 'schedule.json'), 'w', encoding='utf-8') as f:
            json.dump([asdict(x) for x in plan], f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(f'  ✓ schedule.txt  ({len(plan)} slots) + schedule.json')
        _write_master_copy(outdir, ed, plan)

    return made


def _write_master_copy(outdir: str, ed, plan) -> None:
    """One paste sheet: schedule + WhatsApp + Instagram. X is not a channel."""
    lines = [
        f'# ಊರ್ಮನಿ ಸುದ್ದಿ — MASTER COPY',
        f'## {ed.date_kn} · ಆವೃತ್ತಿ {ed.edition_no}',
        '',
        'AI-card reels: Instagram only. YouTube gets real footage.',
        'Paste the first comment the moment you post.',
        '',
        'To post: open the matching `*_caption.txt`, select all, paste. Those '
        'files hold the caption and nothing else. Everything below is the '
        'working sheet.',
        '',
        '## Schedule',
        '',
    ]
    for s in plan:
        lines += [f'- **{s.at}** · {s.platform} · `{s.asset}`',
                  f'  {s.what}', '']
    lines += ['## First hour (docs/INSTAGRAM.md §5)', '',
              '1. Post, then stay: reply to every comment in the first hour, '
              'by name, in Kannada.',
              '2. Paste the first comment from the caption file (an honest '
              'question about the reader\'s own town).',
              '3. Send it to the WhatsApp community now (`whatsapp_*.txt`) — '
              'sends from people who trust us are the strongest early signal.',
              '4. Share to Stories with the town named.',
              '5. Tomorrow: log the numbers — `python3 scripts/metrics.py add …` '
              '(reach, saves, shares, non-followers %).', '']
    alts = []
    for n in sorted(os.listdir(outdir)):
        if re.fullmatch(r'(saara|mukhya_\d+|roundup)_copy\.json', n):
            try:
                with open(os.path.join(outdir, n), encoding='utf-8') as fh:
                    alt = json.load(fh).get('alt_text', '')
            except (OSError, ValueError):
                alt = ''
            if alt:
                alts.append((n[:-len('_copy.json')], alt))
    if alts:
        lines += ['## Alt text — paste in Advanced settings → Write alt text', '',
                  'Helps search, and is the only way a blind reader gets the post.', '']
        for name, alt in alts:
            lines += [f'- **{name}** — {alt}']
        lines += ['']
    def _read(p: str) -> str:
        with open(p, encoding='utf-8') as fh:
            return fh.read().rstrip()

    for name in sorted(os.listdir(outdir)):
        if re.fullmatch(r'(saara|mukhya_\d+|roundup)_copy\.txt', name):
            lines += [f'## {name}', '', '```',
                      _read(os.path.join(outdir, name)), '```', '']
    # ── WhatsApp community: one admin post per area group (D94) ──────────
    try:
        digests = copywriter.community_digests(ed)
    except Exception as e:
        digests = {}
        print(f'  ! community digests could not be built ({e})')
    if digests:
        lines += ['## WhatsApp community — one post per area group', '',
                  f'Admin-only announcement groups. At most '
                  f'{Limits.whatsapp_items_max} stories each; more is how '
                  'members mute.', '']
        for slug, (name, text) in digests.items():
            lines += [f'### {name}', '', '```', text, '```', '']
    fb = sorted(f for f in os.listdir(outdir) if f.startswith('facebook_group_'))
    if fb:
        lines += ['## Facebook groups', '',
                  'Question first, no outside link. One post per group per '
                  'week at most — see docs/CHANNELS.', '']
        for name in fb:
            lines += [f'### {name}', '', '```', _read(os.path.join(outdir, name)),
                      '```', '']

    # ── the forwards, one per town ────────────────────────────────────────
    # The single highest-leverage distribution change available to this desk.
    # A seven-taluk digest is nobody's in particular and belongs in no group;
    # a Kundapura card goes into a Kundapura group with somebody's own name on
    # it. Same facts, same sourcing, re-cut so the first line is the reader's
    # town. See D72.
    try:
        forwards = copywriter.taluk_forwards(ed)
    except Exception as e:
        forwards = {}
        print(f'  ! taluk forwards could not be built ({e})')
    if forwards:
        lines += ['## WhatsApp — one forward per town', '',
                  'Send each of these to that town\'s groups and broadcast '
                  'list, not to everyone. People forward what is theirs.', '']
        for place, text in forwards.items():
            lines += [f'### {place}', '', '```', text, '```', '']

    for slug, (_name, text) in digests.items():
        with open(os.path.join(outdir, f'whatsapp_{slug}.txt'), 'w',
                  encoding='utf-8') as fh:
            fh.write(text + '\n')

    path = os.path.join(outdir, 'MASTER_COPY.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).rstrip() + '\n')
    print('  ✓ MASTER_COPY.md')

    # Also as files, because a forward gets sent from a phone and copying out
    # of a fenced block in a long markdown file at 20:00 is how the wrong
    # town's card goes to the wrong group.
    for place, text in forwards.items():
        # Latin name for the filename. `isalnum()` is False for a Kannada
        # vowel sign, so filtering on it silently ate them: ಉಡುಪಿ came out as
        # forward_ಉಡಪ.txt and ಮಂಗಳೂರು as forward_ಮಗಳರ.txt — a filename that
        # is not the town's name in any language, on the file somebody has to
        # pick out of a folder at 20:00. copy.PLACE_TAGS already holds the
        # Latin spelling for exactly this kind of use.
        safe = copywriter.PLACE_TAGS.get(place.strip(), '')
        if not safe:
            safe = ''.join(c for c in place
                          if c.isalnum() or '\u0c80' <= c <= '\u0cff'
                          or c in ' _-').strip()
        fp = os.path.join(outdir, f'forward_{safe or "edition"}.txt')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    if forwards:
        print(f'  ✓ {len(forwards)} taluk forward(s): '
              + ', '.join(sorted(forwards)))

    # ── the reach view of the day ─────────────────────────────────────────
    try:
        from brand import reach
        rp = os.path.join(outdir, 'REACH.md')
        with open(rp, 'w', encoding='utf-8') as f:
            f.write(reach.report(ed))
        print('  ✓ REACH.md')
    except Exception as e:
        print(f'  ! reach report could not be built ({e})')


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Render Oormani Suddi designs from JSON.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Read docs/AI_BRIEF.md before generating the JSON.')
    ap.add_argument('input', nargs='?', help='edition or story JSON file')
    ap.add_argument('--out', help='output directory')
    ap.add_argument('--only', nargs='+', metavar='FORMAT',
                    choices=list(Limits.daily_templates),
                    help='render only these formats: '
                         + ', '.join(Limits.daily_templates))
    ap.add_argument('--animate', action='store_true', default=True,
                    help='(the default) every carousel slide also as a scan-wipe '
                         'video (.mp4 beside the .jpg), posted as a video carousel (D98, D99)')
    ap.add_argument('--still', action='store_true',
                    help='skip the animated twins — quicker, for checking a draft')
    ap.add_argument('--at', metavar='ISO',
                    help='pin the clock, e.g. 2026-08-25T09:40:00+05:30')
    ap.add_argument('--check', action='store_true',
                    help='preflight only; render nothing')
    ap.add_argument('--describe', action='store_true', help='list every template')
    ap.add_argument('--json', action='store_true', help='machine-readable --describe')
    ap.add_argument('--schema', metavar='NAME', help='print a JSON schema')
    args = ap.parse_args()

    if args.describe:
        return describe(args.json)
    if args.schema:
        return show_schema(args.schema)
    if not args.input:
        ap.print_help()
        return 1
    if args.at:
        freeze(args.at)

    try:
        loaded = load(args.input)
    except (ContentError, json.JSONDecodeError) as e:
        print(f'✗ {args.input}: {e}', file=sys.stderr)
        return 1

    # ── festival greeting ────────────────────────────────────────────────
    if loaded[0] == 'greeting':
        from templates.greeting import package
        _, g = loaded
        try:
            g.validate()
        except ContentError as e:
            print(f'✗ {e}', file=sys.stderr)
            return 1
        print(f'\nಶುಭಾಶಯ — {g.occasion} {g.wish}  ·  theme {g.theme}')
        if args.check:
            print('  ✓ greeting cleared')
            return 0
        outdir = args.out or os.path.join('out', 'greetings', g.slug or 'greeting')
        try:
            made = package(g, outdir)
        except ContentError as e:
            print(f'✗ {e}', file=sys.stderr)
            return 1
        for p, k in made:
            inspect(p, k).show(os.path.basename(p))
        print(f'\n✓ {len(made)} posters + copy → {outdir}\n')
        return 0

    # ── edition ──────────────────────────────────────────────────────────
    _, ed = loaded
    try:
        ed.validate()
    except ContentError as e:
        print(f'✗ {e}', file=sys.stderr)
        return 1

    print(f'\nಊರ್ಮನಿ ಸುದ್ದಿ — {ed.date_kn} · ಆವೃತ್ತಿ {ed.edition_no}')
    print(f'{len(ed.stories)} stories\n')

    # Things you asked for once. Printed before anything is made, because a
    # rule nobody sees until after the render is a rule that costs a re-render.
    try:
        from brand import house
        note = house.brief()
        if note:
            print(note + '\n')
    except Exception:
        pass

    print('PREFLIGHT')
    compliance().show('channel compliance')
    blocked = False
    for st in ed.stories:
        rep = preflight(st, 'post')
        if rep.fail or rep.warn:
            rep.show(st.headline[:52] + '…')
        blocked = blocked or bool(rep.fail)
    if blocked:
        print('\n✗ fix the failures above before publishing.')
        return 1
    print('  ✓ all stories cleared')

    # Which format each story runs in, and whether each format has what it
    # needs — before anything is drawn (D92).
    counts = {k: len(ed.segment(k)) for k in ('saara', 'mukhya', 'speed')}
    print('  formats: ' + ' · '.join(f'{k} {n}' for k, n in counts.items() if n))
    problems = ed.format_problems()
    for msg in problems:
        print(f'  ✗ {msg}')
    if problems:
        print('\n✗ fix the formats above before rendering.')
        return 1
    try:
        from brand.intake import published_before
        for i, st in enumerate(ed.stories, 1):
            for why in published_before(st, ed.date.date()):
                print(f'  ! story {i}: {why}' + ('' if st.follows_up else
                      ' — a repeat needs follows_up and a new fact (DUP-01)'))
    except Exception as e:                       # never block a render on it
        print(f'  ! repeat check skipped ({e})')
    if args.check:
        return 0

    # The folder is named after the EDITION FILE, not its date. Two editions
    # carry the same date whenever the day has more than one (an evening
    # edition, a special report, an explainer series), and a date-named folder
    # let the second silently overwrite the first: on 2026-09-25 the ಕಾನೂನು
    # ಕವಚ explainer replaced that day's news carousel. The daily edition file
    # is `editions/<date>.json`, so its folder is still `out/<date>`. D90.
    stem = os.path.splitext(os.path.basename(args.input))[0]
    outdir = args.out or f'out/{stem}'
    stamp = os.path.join(outdir, '.edition')
    here = os.path.relpath(os.path.abspath(args.input))
    if os.path.exists(stamp):
        with open(stamp, encoding='utf-8') as fh:
            there = fh.read().strip()
        if there and there != here:
            print(f'✗ {outdir} holds the package for {there}, not {here}. '
                  f'Rendering here would overwrite it. Pick another --out, '
                  f'or archive/remove that folder first.', file=sys.stderr)
            return 1
    os.makedirs(outdir, exist_ok=True)
    with open(stamp, 'w', encoding='utf-8') as fh:
        fh.write(here + '\n')

    # One heavy job at a time. Two renders on 8 GB of unified memory is how
    # macOS starts swapping and a three-minute master becomes indefinite.
    from brand.runlog import RunLog, acquire, release, lock_holder
    if not acquire(f'render {outdir}'):
        h = lock_holder() or {}
        print(f'✗ another heavy job is already running (pid {h.get("pid")}, '
              f'{h.get("what")}). On this machine, two at once means neither '
              f'finishes. Wait, or kill it.', file=sys.stderr)
        return 1

    log = RunLog(outdir)
    log.event('start', stories=len(ed.stories), only=args.only or 'all')
    print(f'\nRENDER → {outdir}')
    t0 = time.time()
    try:
        made = render_edition(ed, outdir, args.only, log=log,
                              animate=args.animate and not args.still)
        log.done('render', seconds=round(time.time() - t0, 1),
                 files=len(made))

        print('\nOUTPUT AUDIT')
        dirty = 0
        for p, k in made:
            rep = inspect(p, k)
            if rep.fail or rep.warn:
                rep.show(os.path.basename(p))
                dirty += 1
                for m in rep.fail:
                    log.fail('audit', m, file=os.path.basename(p))
                for m in rep.warn:
                    log.warn('audit', m, file=os.path.basename(p))
        if not dirty:
            print('  ✓ every file clean')
            log.done('audit', files=len(made))

        # What made this edition — models, engines, font hashes, library
        # versions. Five lines of code; it is the difference between a golden
        # failure that says WHY and one that only says THAT.
        from brand import provenance
        provenance.write(outdir, ed)
        log.done('provenance')
        print('  ✓ PROVENANCE.json')
        return _finish(outdir, ed, made, log, t0)
    finally:
        release()


def stills_dir(outdir: str) -> str:
    """Where a carousel's finished .jpg stills live once its videos exist."""
    return os.path.join(outdir, '_review')


def _finish(outdir, ed, made, log, t0) -> int:
    import os
    import time

    # ── the Chief Editor's desk ───────────────────────────────────────────
    # The last gate before a human is told the package is postable. It
    # establishes the facts a machine can establish — the handle, the file
    # references, audio on every reel, the disclosures, the legal markers —
    # and writes APPROVAL.md only when they are all clean.
    #
    # The absence of APPROVAL.md is the meaningful state. A folder without one
    # has NOT been cleared, whatever was said about it in conversation.
    from brand.review import review, approve, evidence, is_signed

    # The frames a judgement about craft has to be made AGAINST. Produced
    # before the review rather than after it, so `_review/` exists whether the
    # package passed or failed — a failing package is exactly the one someone
    # needs to look at.
    try:
        frames = evidence(outdir)
        log.done('evidence', frames=len(frames))
        if frames:
            print(f'  ✓ _review/  ({len(frames)} frames to look at)')
    except Exception as e:                       # ffmpeg missing, etc.
        log.warn('evidence', str(e))

    rep = review(outdir, ed).show()
    for f in rep.findings:
        (log.fail if f.severity == 'fail' else log.warn)(
            'gate', f.message, code=f.code, where=f.where or '-')
    ap = approve(outdir, rep)
    if ap:
        print('  🟢 APPROVAL.md written — mechanical checks clean')
        if is_signed(outdir):
            print('  🟢 signed — cleared to publish')
        else:
            print('  🟡 NOT yet cleared to publish. Look at _review/ at feed '
                  'size, listen to one reel, then:')
            print(f'       python3 scripts/sign_off.py {outdir} --by "<name>"')
    else:
        print(f'  🔴 HELD — {len(rep.fail)} fault(s) above must be fixed and '
              f'the render re-run. Do NOT publish this folder: it has no '
              f'APPROVAL.md. Codes and owners in review_report.json.')

    # The editor's folder holds what gets posted: a carousel slide's .jpg
    # whose .mp4 twin exists MOVES into _review/ (D102). Carousels are posted
    # as the .mp4 slides only (D98–D100, house rule 2026-10-04-01); the still
    # is the exact finished slide, so it is kept — it is what the package
    # inspector and the feed-size sheet read. Moved, never deleted: if the
    # evidence step failed, a delete would have lost the only finished stills.
    stills = stills_dir(outdir)
    moved = []
    for f in sorted(os.listdir(outdir)):
        if re.match(r'(saara|mukhya_\d+)_', f) and f.endswith('.jpg'):
            if os.path.exists(os.path.join(outdir, f[:-4] + '.mp4')):
                try:
                    os.makedirs(stills, exist_ok=True)
                    os.replace(os.path.join(outdir, f), os.path.join(stills, f))
                    moved.append(f)
                except OSError:
                    pass
    if moved:
        print(f'  ✓ {len(moved)} carousel still(s) moved to _review/ — post the .mp4 slides')

    if rep.clean:
        log.done('finish', seconds=round(time.time() - t0, 1), files=len(made))
    else:
        log.fail('finish',
                 f'{len(rep.fail)} blocking fault(s) — no APPROVAL.md written',
                 seconds=round(time.time() - t0, 1), files=len(made))
    report = log.report(outdir)
    if report:
        print(f'  ✓ {os.path.basename(report)}  ·  build.log')

    print(f'\n{len(made)} files in {time.time() - t0:.0f}s → {outdir}\n')
    return 0 if rep.clean else 1


if __name__ == '__main__':
    raise SystemExit(main())
