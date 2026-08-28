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
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import templates as TP
import brand.copy as copywriter
from brand.content import Story, Edition, ContentError, freeze
from brand.qa import preflight, inspect, compliance

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
        print(f'no schema {which!r}; try: story, edition', file=sys.stderr)
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
    if 'stories' in raw:
        return 'edition', Edition.from_dict(raw)
    return 'story', Story.from_dict(raw), raw.get('template'), raw.get('hook', '')


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────────────────────────────────────

def write_copy(subject, outdir: str, name: str) -> str:
    """Write the post copy next to the artwork.

    Artwork on its own is not a post. Every render gets a .txt you can paste
    from and a .json a scheduler can read.
    """
    c = (copywriter.for_edition(subject) if isinstance(subject, Edition)
         else copywriter.for_story(subject))
    d = c.to_dict()
    with open(os.path.join(outdir, f'{name}.json'), 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write('\n')
    txt = os.path.join(outdir, f'{name}.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('═══ INSTAGRAM CAPTION ' + '═' * 46 + '\n\n')
        f.write(c.instagram + '\n\n')
        f.write('═══ ALT TEXT ' + '═' * 55 + '\n\n' + c.alt_text + '\n\n')
        f.write('═══ WHATSAPP ' + '═' * 55 + '\n\n' + c.whatsapp + '\n\n')
        f.write('═══ X / TWITTER ' + '═' * 52 + '\n\n' + c.x_post + '\n\n')
        f.write('═══ YOUTUBE TITLE ' + '═' * 50 + '\n\n' + c.youtube_title + '\n\n')
        f.write('═══ YOUTUBE DESCRIPTION ' + '═' * 44 + '\n\n')
        f.write(c.youtube_description + '\n\n')
        f.write('═══ YOUTUBE TAGS ' + '═' * 51 + '\n\n')
        f.write(', '.join(c.youtube_tags) + '\n')
    return txt


def render_edition(ed: Edition, outdir: str, only: list[str] | None,
                   reel_seconds: float | None,
                   bulletin_seconds: float | None = None
                   ) -> list[tuple[str, str]]:
    made: list[tuple[str, str]] = []
    want = set(only) if only else None

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
        for p in TP.render('carousel', ed, outdir, prefix='carousel'):
            made.append((p, 'square'))
            print(f'  ✓ {os.path.basename(p)}')
        write_copy(ed, outdir, 'carousel_copy')
        print('  ✓ carousel_copy.txt')

    lead = ed.stories[0]
    if run('story_card'):
        p = os.path.join(outdir, 'story_9x16.jpg')
        TP.render('story_card', lead, p)
        made.append((p, 'story'))
        print(f'  ✓ {os.path.basename(p)}')

    if run('youtube_thumb'):
        p = os.path.join(outdir, 'yt_thumbnail.jpg')
        TP.render('youtube_thumb', lead, p, hook=getattr(lead, '_hook', ''))
        made.append((p, 'thumb'))
        print(f'  ✓ {os.path.basename(p)}')

    if run('broadsheet'):
        p = os.path.join(outdir, 'broadsheet.jpg')
        TP.render('broadsheet', ed, p)
        made.append((p, 'broadsheet'))
        print(f'  ✓ {os.path.basename(p)}')

    if run('reel'):
        p = os.path.join(outdir, 'reel.mp4')
        TP.render('reel', ed, p, target_seconds=reel_seconds)
        write_copy(ed, outdir, 'reel_copy')
        print(f'  ✓ {os.path.basename(p)}  + copy')

    # The 16:9 long-form cut. yt_thumbnail.jpg above is built for THIS video —
    # without it the channel renders a thumbnail for a video that does not
    # exist, and a sub-60s vertical reel is a Short, which ignores custom
    # thumbnails anyway. See templates/bulletin.py and DECISIONS.md D37.
    if run('bulletin'):
        p = os.path.join(outdir, 'bulletin.mp4')
        TP.render('bulletin', ed, p, target_seconds=bulletin_seconds)
        write_copy(ed, outdir, 'bulletin_copy')
        print(f'  ✓ {os.path.basename(p)}  + copy')

    return made


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
    ap.add_argument('--reel-seconds', type=float, default=None,
                    help='ceiling, not a quota. Omit to let the reel be as long '
                         'as the copy needs to stay readable.')
    ap.add_argument('--bulletin-seconds', type=float, default=None,
                    help='ceiling for the 16:9 YouTube bulletin. Omit to let it '
                         'run as long as the decks need — typically 60-120s.')
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

    outdir = args.out or f'out/{ed.date:%Y-%m-%d}'
    os.makedirs(outdir, exist_ok=True)
    print(f'\nRENDER → {outdir}')
    t0 = time.time()
    made = render_edition(ed, outdir, args.only, args.reel_seconds,
                          args.bulletin_seconds)

    print('\nOUTPUT AUDIT')
    dirty = 0
    for p, k in made:
        rep = inspect(p, k)
        if rep.fail or rep.warn:
            rep.show(os.path.basename(p))
            dirty += 1
    if not dirty:
        print('  ✓ every file clean')
    print(f'\n{len(made)} files in {time.time() - t0:.0f}s → {outdir}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
