#!/usr/bin/env python3
"""
ಊರ್ಮನಿ ಸುದ್ದಿ — JSON in, finished design out.
=============================================

The machine-facing entry point. Anything that can write JSON — a script, a
newsroom tool, an AI given raw copy — can drive the whole design system through
this without knowing any Python.

    python3 render.py edition.json                     # the full package
    python3 render.py edition.json --only carousel reel
    python3 render.py story.json --template report_card --out card.jpg
    python3 render.py --describe                       # every template + its rules
    python3 render.py --schema story                   # the input contract
    python3 render.py --check edition.json             # preflight only, render nothing

Reproducibility: pass --at (or set OORMANI_NOW) to pin the clock. Identical
input plus the same --at gives byte-identical output, which is what the golden
tests in tests/ rely on.

The contract and the reasoning live in docs/AI_BRIEF.md. Read that first if you
are generating the JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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
    return 'story', Story.from_dict(raw), raw.get('template'), raw.get('hook', '')


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────────────────────────────────────

def write_copy(subject, outdir: str, name: str, voice_script: str | None = None) -> str:
    """Write the post copy next to the artwork.

    Artwork on its own is not a post. Every render gets a .txt you can paste
    from and a .json a scheduler can read.
    """
    c = (copywriter.for_edition(subject) if isinstance(subject, Edition)
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
    return txt


def _reel_with_voice(story, sub_ed, path: str, vo_path: str,
                     reel_seconds: float | None,
                     bgm: str | None = None) -> str | None:
    """Narrate the story, then cut the reel to that narration.

    The two steps are ordered and they depend on each other, which is the
    whole point. `reel_min_spans` tells the voice engine how long each card
    needs to be READABLE, so a beat is never shorter than the Kannada on it
    takes to read; the returned track then tells the reel engine exactly where
    every sentence begins, so every cut lands in a gap between sentences.

    If synthesis fails — no network, no TTS engine — the reel is still made,
    silent, from reading time alone. A missing voiceover must not cost the
    edition its video.
    """
    try:
        from brand.voice import synthesize_track
        from brand import motion
        track = synthesize_track(story, vo_path,
                                 min_span=motion.reel_min_spans(story))
        print(f'    · narration: {len(track.segments)} beats, '
              f'{track.duration:.1f}s')
        TP.render('reel', sub_ed, path, target_seconds=reel_seconds, voice=track, bgm=bgm)
        return track.script
    except Exception as e:
        # The reel is still made — a missing voiceover must not cost the
        # edition its video. But a reel that was MEANT to be narrated and came
        # out silent is not publishable, and the Chief Editor has to know:
        # without this marker the folder looked complete and was approved with
        # a silent reel in it.
        print(f'    ! voiceover synthesis failed ({e}); '
              f'rendering the reel silent, timed from reading speed')
        TP.render('reel', sub_ed, path, target_seconds=reel_seconds)
        with open(os.path.splitext(path)[0] + '.NARRATION_FAILED', 'w',
                  encoding='utf-8') as f:
            f.write(f'{type(e).__name__}: {e}\n')
        return None


class _NullLog:
    """So render_edition can be called without a log and not know it."""
    def start(self, *a, **k): pass
    def done(self, *a, **k): pass
    def warn(self, *a, **k): pass
    def fail(self, *a, **k): pass
    def event(self, *a, **k): pass


def render_edition(ed: Edition, outdir: str, only: list[str] | None,
                   reel_seconds: float | None,
                   bulletin_seconds: float | None = None,
                   bgm: str | None = None,
                   log=None,
                   ) -> list[tuple[str, str]]:
    made: list[tuple[str, str]] = []
    want = set(only) if only else None
    log = log or _NullLog()

    def run(key):
        return want is None or key in want

    for i, st in enumerate(ed.stories, 1):
        key = getattr(st, '_template', None) or TP.choose(st)
        if not run(key) and not run('posts'):
            continue
        spec = TP.get(key)
        # Stable filename, template reported alongside. Putting the template
        # name IN the filename meant that a story which switched from
        # text_card to report_card left the old file behind, and the folder
        # ended up with two versions of post 02 and no way to tell which was
        # current.
        p = os.path.join(outdir, f'post_{i:02d}.jpg')
        spec(st, p)
        made.append((p, spec.format))
        write_copy(st, outdir, f'post_{i:02d}_copy')
        print(f'  ✓ {os.path.basename(p):<22} {key}  + copy')

    if run('carousel'):
        _t = time.time()
        for p in TP.render('carousel', ed, outdir, prefix='carousel'):
            made.append((p, 'square'))
            print(f'  ✓ {os.path.basename(p)}')
        write_copy(ed, outdir, 'carousel_copy')
        print('  ✓ carousel_copy.txt')
        log.done('carousel', seconds=round(time.time() - _t, 1))

    lead = ed.stories[0]
    if run('story_card'):
        _t = time.time()
        p = os.path.join(outdir, 'story_9x16.jpg')
        TP.render('story_card', lead, p)
        made.append((p, 'story'))
        print(f'  ✓ {os.path.basename(p)}')
        log.done('story_card', seconds=round(time.time() - _t, 1))

    if run('youtube_thumb'):
        _t = time.time()
        p = os.path.join(outdir, 'yt_thumbnail.jpg')
        TP.render('youtube_thumb', lead, p, hook=getattr(lead, '_hook', ''))
        made.append((p, 'thumb'))
        print(f'  ✓ {os.path.basename(p)}')
        log.done('youtube_thumb', seconds=round(time.time() - _t, 1))

    if run('broadsheet'):
        _t = time.time()
        p = os.path.join(outdir, 'broadsheet.jpg')
        TP.render('broadsheet', ed, p)
        made.append((p, 'broadsheet'))
        print(f'  ✓ {os.path.basename(p)}')
        log.done('broadsheet', seconds=round(time.time() - _t, 1))

    if run('reel'):
        # Editorial filter: only stories meeting the 10/10 standard (is_reel=True)
        # get rendered as vertical reels. Routine or low-visual stories stay in
        # carousel/posts to preserve channel retention and algorithmic health.
        reel_stories = [(orig_idx, st) for orig_idx, st in enumerate(ed.stories, 1)
                        if getattr(st, 'is_reel', True)]

        if len(ed.stories) > 1:
            if not reel_stories:
                print('  · no stories qualified for reels (is_reel=false on all)')
            for r, (orig_idx, st) in enumerate(reel_stories, 1):
                sub_ed = replace(ed, stories=[st])
                p = os.path.join(outdir, f'reel_{r:02d}.mp4')
                vo_path = os.path.join(outdir, f'reel_{r:02d}_voiceover.mp3')
                _t = time.time()
                vo_script = _reel_with_voice(st, sub_ed, p, vo_path, reel_seconds, bgm=bgm)
                log.done(f'reel_{r:02d}', seconds=round(time.time() - _t, 1),
                         narrated=bool(vo_script))
                write_copy(st, outdir, f'reel_{r:02d}_copy', voice_script=vo_script)
                cov = os.path.join(outdir, f'reel_{r:02d}_cover.jpg')
                if os.path.exists(cov):
                    made.append((cov, 'story'))
                print(f'  ✓ {os.path.basename(p)}  (story {orig_idx:02d}) + copy')
                if r == 1:
                    # Keep canonical reel.mp4, reel_cover.jpg, reel_copy for backwards compatibility
                    p_canon = os.path.join(outdir, 'reel.mp4')
                    if os.path.exists(p):
                        shutil.copy2(p, p_canon)
                    c_named = os.path.join(outdir, f'reel_{r:02d}_cover.jpg')
                    c_canon = os.path.join(outdir, 'reel_cover.jpg')
                    if os.path.exists(c_named):
                        shutil.copy2(c_named, c_canon)
                    vo_canon = os.path.join(outdir, 'reel_voiceover.mp3')
                    if vo_path and os.path.exists(vo_path):
                        shutil.copy2(vo_path, vo_canon)
                    write_copy(st, outdir, 'reel_copy', voice_script=vo_script)
            if reel_stories:
                print('    · set each reel_*_cover.jpg as the Instagram cover (not YouTube)')
        else:
            lead = ed.stories[0]
            if getattr(lead, 'is_reel', True):
                p = os.path.join(outdir, 'reel.mp4')
                vo_path = os.path.join(outdir, 'reel_voiceover.mp3')
                _t = time.time()
                vo_script = _reel_with_voice(lead, ed, p, vo_path, reel_seconds, bgm=bgm)
                log.done('reel', seconds=round(time.time() - _t, 1),
                         narrated=bool(vo_script))
                write_copy(lead, outdir, 'reel_copy', voice_script=vo_script)
                cov = os.path.join(outdir, 'reel_cover.jpg')
                if os.path.exists(cov):
                    made.append((cov, 'story'))
                print(f'  ✓ {os.path.basename(p)}  + copy')
                print('    · set reel_cover.jpg as the Instagram cover (not YouTube)')
            else:
                print('  · lead story is_reel=false; skipping reel.')

    # The 16:9 long-form cut. yt_thumbnail.jpg above is built for THIS video —
    # without it the channel renders a thumbnail for a video that does not
    # exist, and a sub-60s vertical reel is a Short, which ignores custom
    # thumbnails anyway. See templates/bulletin.py and DECISIONS.md D37.
    if run('bulletin'):
        _t = time.time()
        p = os.path.join(outdir, 'bulletin.mp4')
        TP.render('bulletin', ed, p, target_seconds=bulletin_seconds)
        write_copy(ed, outdir, 'bulletin_copy')
        print(f'  ✓ {os.path.basename(p)}  + copy')
        log.done('bulletin', seconds=round(time.time() - _t, 1))

    # The publishing plan. AGENTS.md has asked for a scheduled timetable as a
    # deliverable since the workflow was written, and it was being retyped by
    # hand every morning — which is exactly how the times drift and the first
    # comment gets forgotten. Derived from what was actually rendered, so it
    # can never list a reel that does not exist.
    kinds = [k for _f, k in made]
    n_reels = len([f for f, _k in made
                   if os.path.basename(f).startswith('reel_')
                   and f.endswith('_cover.jpg')])
    # The real name of the last carousel slide, read off the folder rather
    # than assumed: the count follows the edition, and the schedule is the one
    # file the publisher actually follows.
    slides = sorted(f for f in os.listdir(outdir)
                    if f.startswith('carousel_') and f.endswith('.jpg'))
    plan = copywriter.publishing_plan(
        n_reels=n_reels,
        has_bulletin=os.path.exists(os.path.join(outdir, 'bulletin.mp4')),
        has_carousel=os.path.exists(os.path.join(outdir, 'carousel_01_cover.jpg')),
        has_story_card=os.path.exists(os.path.join(outdir, 'story_9x16.jpg')),
        has_broadsheet=os.path.exists(os.path.join(outdir, 'broadsheet.jpg')),
        carousel_last=slides[-1] if slides else '')
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
    def _read(p: str) -> str:
        with open(p, encoding='utf-8') as fh:
            return fh.read().rstrip()

    car = os.path.join(outdir, 'carousel_copy.txt')
    if os.path.exists(car):
        lines += ['## Carousel', '', '```', _read(car), '```', '']
    for name in sorted(os.listdir(outdir)):
        if re.fullmatch(r'reel(_\d+)?_copy\.txt', name):
            lines += [f'## {name}', '', '```',
                      _read(os.path.join(outdir, name)), '```', '']
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
    ap.add_argument('--out', help='output file (story) or directory (edition)')
    ap.add_argument('--template', help='force a template; see --describe')
    ap.add_argument('--hook', default='', help='short line for youtube_thumb')
    ap.add_argument('--only', nargs='+', metavar='T',
                    help='render only these templates (plus "posts")')
    ap.add_argument('--minimal', action='store_true',
                    help='the daily default path only: '
                         + ', '.join(Limits.daily_templates)
                         + '. What ships on a four-hour day instead of a '
                           'ten-hour one. Overridden by --only.')
    ap.add_argument('--reel-seconds', type=float, default=None,
                    help='ceiling, not a quota. Omit to let the reel be as long '
                         'as the copy needs to stay readable.')
    ap.add_argument('--bulletin-seconds', type=float, default=None,
                    help='ceiling for the 16:9 YouTube bulletin. Omit to let it '
                         'run as long as the decks need — typically 60-120s.')
    ap.add_argument('--bgm', help='custom background music path (e.g. devotional song)')
    ap.add_argument('--at', metavar='ISO',
                    help='pin the clock, e.g. 2026-08-25T09:40:00+05:30')
    ap.add_argument('--check', action='store_true',
                    help='preflight only; render nothing')
    ap.add_argument('--describe', action='store_true', help='list every template')
    ap.add_argument('--json', action='store_true', help='machine-readable --describe')
    ap.add_argument('--schema', metavar='NAME', help='print a JSON schema')
    args = ap.parse_args()

    # A minimal day is the four things that actually ship most mornings. The
    # bulletin, the thumbnail and the standalone post cards are real, and they
    # are --only on request; making them the default is how a small desk ends
    # up producing a lot of mediocre content instead of four good things.
    if args.minimal and not args.only:
        args.only = list(Limits.daily_templates)

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

    # ── single story ─────────────────────────────────────────────────────
    if loaded[0] == 'story':
        _, st, tpl, hook = loaded
        key = args.template or tpl or TP.choose(st)
        hook = args.hook or hook
        try:
            st.validate()
        except ContentError as e:
            print(f'✗ {e}', file=sys.stderr)
            return 1
        rep = preflight(st, TP.get(key).format, hook=hook)
        rep.show(f'preflight · {key}')
        if rep.fail or args.check:
            return 1 if rep.fail else 0
        out = args.out or f'out/{key}.jpg'
        kw = {'hook': hook} if key == 'youtube_thumb' else {}
        TP.render(key, st, out, **kw)
        inspect(out, TP.get(key).format).show(os.path.basename(out))
        base = os.path.splitext(out)[0]
        write_copy(st, os.path.dirname(out) or '.',
                   os.path.basename(base) + '_copy')
        print(f'\n✓ {out}')
        print(f'✓ {base}_copy.txt  ·  {base}_copy.json')
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
    if args.check:
        return 0

    if args.bgm:
        from brand.music import check_path
        err = check_path(args.bgm)
        if err:
            print(f'✗ {err}', file=sys.stderr)
            return 1

    outdir = args.out or f'out/{ed.date:%Y-%m-%d}'
    os.makedirs(outdir, exist_ok=True)

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
        made = render_edition(ed, outdir, args.only, args.reel_seconds,
                              args.bulletin_seconds, bgm=args.bgm, log=log)
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
