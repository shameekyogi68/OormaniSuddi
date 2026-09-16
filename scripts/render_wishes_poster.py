"""Superseded — the Gauri Ganesha poster is now made by the greeting template.

    python3 render.py editions/greetings/2026-09-13_gauri_ganesha.json

The script that lived here set a festival wish in news grammar — masthead,
eyebrow rail, left-aligned headline — and was rejected for looking like a news
card. Its replacement is templates/greeting.py; see DECISIONS.md D54. This file
only forwards to it, so an old command still produces the current design.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    raise SystemExit(subprocess.call([
        sys.executable, os.path.join(ROOT, 'render.py'),
        os.path.join(ROOT, 'editions', 'greetings', '2026-09-13_gauri_ganesha.json'),
    ]))
