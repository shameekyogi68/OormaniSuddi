"""
ಊರ್ಮನಿ ಸುದ್ದಿ — What made this edition
======================================
Five lines of code that buy three things the project already claims to care
about and could not actually deliver:

  * **Reproducibility.** The golden test pins rendered pixels, but a Pillow or
    raqm bump reshapes Kannada rasterisation and the fingerprints fail for a
    reason that has nothing to do with design. Recording the versions means a
    golden failure can say *why* instead of just *that*.
  * **Honest disclosure.** "Which AI made this?" is a question a reader, a
    platform, or the Ministry may reasonably ask about a frame that carries
    ಎಐ ರಚಿತ ಚಿತ್ರ. The answer should be in the folder, not in someone's memory.
  * **Correlation.** When quality changes, the first question is what else
    changed. A voice that got worse in October is usually a model that got
    swapped in October.

Written as `PROVENANCE.json` next to the artwork, and copied into the archive.
"""
from __future__ import annotations

import hashlib
import os
import platform
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha256(path: str, limit: int = 1 << 22) -> str:
    """Hash a file. Fonts are small; the cap is a guard, not a policy."""
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as fh:
            read = 0
            while read < limit:
                chunk = fh.read(65536)
                if not chunk:
                    break
                h.update(chunk)
                read += len(chunk)
    except OSError:
        return ''
    return h.hexdigest()[:16]


def font_fingerprints() -> dict[str, str]:
    """Every face the renderer can reach, hashed.

    A system font that updates under you is the classic silent golden-test
    failure: nothing in the repo changed, and every Kannada line moved by a
    fraction of a pixel.
    """
    from .tokens import FONTS
    out: dict[str, str] = {}
    for name, rel in FONTS.items():
        path = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
        out[name] = _sha256(path) or 'missing'
    return out


def library_versions() -> dict[str, str]:
    out = {'python': sys.version.split()[0],
           'platform': f'{platform.system()} {platform.release()} {platform.machine()}'}
    try:
        import PIL
        out['Pillow'] = getattr(PIL, '__version__', 'unknown')
        # raqm is what shapes Kannada conjuncts. Without it every ottakshara
        # renders as separate letters, which is a design failure that looks
        # like a font failure.
        try:
            from PIL import features
            out['raqm'] = str(features.check('raqm'))
            out['libraqm'] = features.version('raqm') or 'unknown'
        except Exception:
            out['raqm'] = 'unknown'
    except ImportError:
        out['Pillow'] = 'missing'
    try:
        import numpy
        out['numpy'] = numpy.__version__
    except ImportError:
        out['numpy'] = 'missing'
    try:
        import subprocess
        v = subprocess.run(['ffmpeg', '-version'], capture_output=True,
                           text=True, timeout=10).stdout.split('\n')[0]
        out['ffmpeg'] = v.replace('ffmpeg version ', '').split(' ')[0] or 'unknown'
    except Exception:
        out['ffmpeg'] = 'missing'
    return out


def engines() -> dict[str, str]:
    """Which model wrote, spoke and drew. Names only — never a key."""
    from .voice import DEFAULT_ENGINE, DEFAULT_VOICE
    import os as _os
    tts = (_os.environ.get('OORMANI_TTS_ENGINE') or DEFAULT_ENGINE).lower()
    return {
        'tts_engine': tts,
        'tts_voice': DEFAULT_VOICE if tts == 'edge' else 'kn-IN (Google Cloud)',
        'tts_tempo': '1.15',
        'text_model': _os.environ.get('OORMANI_TEXT_MODEL', 'gemini-2.5-flash'),
        'image_source': 'stock library + chat-generated AI frames',
    }


def snapshot(edition=None, outdir: str = '') -> dict:
    """The full record for one render."""
    from .content import now, SCHEMA_VERSION
    from .tokens import Limits
    rec = {
        'kind': 'render_provenance',
        'at': now().isoformat(),
        'schema_version': SCHEMA_VERSION,
        'outdir': outdir,
        'libraries': library_versions(),
        'fonts': font_fingerprints(),
        'engines': engines(),
        'limits': {k: v for k, v in vars(Limits).items()
                   if not k.startswith('_') and isinstance(v, (int, float, str, tuple))},
    }
    if edition is not None:
        rec['edition'] = {
            'date': edition.date.isoformat(),
            'edition_no': edition.edition_no,
            'stories': len(edition.stories),
            'verified_by': sorted({s.verified_by for s in edition.stories
                                   if s.verified_by}),
            'unverified': len(edition.unverified),
            'synthetic_imagery': sum(1 for s in edition.stories
                                     if s.has_synthetic_imagery),
            'sources': sorted({u for s in edition.stories
                               for u in s.source_urls if u}),
        }
    return rec


def write(outdir: str, edition=None) -> str:
    import json
    path = os.path.join(outdir, 'PROVENANCE.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(snapshot(edition, outdir), fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    return path
