"""Golden tests — the design itself, pinned.

Renders fixed content with a frozen clock and compares a hash of the raw RGB
pixels. This is what makes "same content, same design" a checkable claim rather
than a promise.

A failure here means the visual output changed. That is not automatically a
bug — if you changed the design on purpose, look at the new files, satisfy
yourself they are right, then re-bless:

    python3 -m tests.test_golden --bless

Content comes from tests/fixture_edition.json, which is frozen. Do NOT point
this at editions/*.json — those change every day, and a golden test that fails
whenever real news arrives is worse than no golden test.

Hashes are over decoded pixels, not the JPEG bytes, so they survive a different
libjpeg. They will still move if Pillow's Lanczos or FreeType's rasteriser
changes; docs/DECISIONS.md explains why that is worth knowing about.
"""
import os
import sys

# Bootstrap without a relative import, so this file works under every
# invocation: `python3 -m unittest discover tests`, `discover -s tests -t .`,
# `python3 -m tests.test_contract`, and running the file directly.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)   # so relative asset paths in the content resolve as at render time
import hashlib
import json
import shutil
import tempfile
import unittest

from PIL import Image

import templates as TP
from brand.content import Edition, frozen

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, 'golden.json')
PINNED_NOW = '2026-08-25T09:40:00+05:30'
# The golden test renders FIXED fixture content, never a live edition. Pointing
# it at editions/*.json makes it fail every time real news is added — which is
# exactly what it did the first time somebody used this system for real.
EDITION = os.path.join(HERE, 'fixture_edition.json')


def _hash(path: str) -> str:
    with Image.open(path) as im:
        return hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()


def render_all(outdir: str) -> dict[str, str]:
    """Render every still template from the pinned edition."""
    ed = Edition.load(EDITION)
    weather = next(s for s in ed.stories if s.category == 'weather' and s.photo)
    crime = next(s for s in ed.stories if s.category == 'crime')
    order = next(s for s in ed.stories if not s.photo)

    out: dict[str, str] = {}
    with frozen(PINNED_NOW):
        out['report_weather'] = _hash(TP.render(
            'report_card', weather, f'{outdir}/report_weather.jpg'))
        out['report_crime'] = _hash(TP.render(
            'report_card', crime, f'{outdir}/report_crime.jpg'))
        out['text_order'] = _hash(TP.render(
            'text_card', order, f'{outdir}/text_order.jpg'))
        out['story_card'] = _hash(TP.render(
            'story_card', weather, f'{outdir}/story.jpg'))
        out['youtube_thumb'] = _hash(TP.render(
            'youtube_thumb', crime, f'{outdir}/thumb.jpg',
            hook='ಬ್ರಹ್ಮಾವರ ದುರಂತ: ಪುತ್ರ ಬಂಧನ'))
        out['broadsheet'] = _hash(TP.render(
            'broadsheet', ed, f'{outdir}/broadsheet.jpg'))
        for i, p in enumerate(TP.render('carousel', ed, outdir, prefix='car')):
            out[f'carousel_{i}'] = _hash(p)
    return out


class Golden(unittest.TestCase):

    def test_output_matches_the_blessed_design(self):
        if not os.path.exists(GOLDEN):
            self.skipTest('no golden.json — run: python3 -m tests.test_golden --bless')
        with open(GOLDEN, encoding='utf-8') as f:
            expected = json.load(f)
        tmp = tempfile.mkdtemp(prefix='oormani-golden-')
        try:
            actual = render_all(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        missing = sorted(set(expected) - set(actual))
        self.assertFalse(missing, f'templates disappeared: {missing}')
        changed = sorted(k for k in expected if expected[k] != actual.get(k))
        self.assertFalse(
            changed,
            'visual output changed for: ' + ', '.join(changed) +
            '\nIf this was intentional, review the new renders then re-bless:'
            '\n    python3 -m tests.test_golden --bless')

    def test_rendering_twice_gives_the_same_bytes(self):
        """Determinism. Without this the golden test is meaningless."""
        a = tempfile.mkdtemp(prefix='oormani-det-a-')
        b = tempfile.mkdtemp(prefix='oormani-det-b-')
        try:
            ed = Edition.load(EDITION)
            crime = next(s for s in ed.stories if s.category == 'crime')
            with frozen(PINNED_NOW):
                h1 = _hash(TP.render('report_card', crime, f'{a}/x.jpg'))
                h2 = _hash(TP.render('report_card', crime, f'{b}/x.jpg'))
            self.assertEqual(h1, h2)
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)


def bless():
    out = os.path.join(os.path.dirname(HERE), 'out', '_blessed')
    os.makedirs(out, exist_ok=True)
    hashes = render_all(out)
    with open(GOLDEN, 'w', encoding='utf-8') as f:
        json.dump(hashes, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f'blessed {len(hashes)} templates → tests/golden.json')
    print(f'renders kept in {os.path.relpath(out)} — LOOK AT THEM before you '
          f'accept the new hashes')


if __name__ == '__main__':
    if '--bless' in sys.argv:
        bless()
    else:
        unittest.main()
