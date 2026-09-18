#!/usr/bin/env python3
"""The old command for the speed-news reel. The format lives in the engine now.

    python3 scripts/render_roundup_reel.py editions/2026-09-18.json out/2026-09-18

is the same as

    python3 render.py editions/2026-09-18.json --only roundup --out out/2026-09-18

Kept only so the old habit still works. This file used to render the reel
itself, outside render.py: the gate never saw the video, the caption was typed
into the script with that day's headlines, and the anchor's words skipped the
pronunciation normaliser. brand/speednews.py and D81 are the fix.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    ed = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', os.path.splitext(os.path.basename(ed))[0])
    os.execvp(sys.executable, [sys.executable, os.path.join(ROOT, 'render.py'),
                               ed, '--only', 'roundup', '--out', out])
