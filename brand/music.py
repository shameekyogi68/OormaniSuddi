"""Music licence register.

A track that is not in assets/LICENCES.json with status=allowed cannot be
used as a bed. Unverified files in assets/bgm_options/ stay on disk but
fail the render if selected.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, 'assets', 'LICENCES.json')


def load() -> dict:
    if not os.path.exists(REGISTER):
        return {'tracks': []}
    with open(REGISTER, encoding='utf-8') as fh:
        return json.load(fh)


def allowed_paths() -> dict[str, dict]:
    out = {}
    for row in load().get('tracks', []):
        path = (row.get('path') or '').replace('\\', '/')
        if path and row.get('status') == 'allowed':
            out[path] = row
    return out


def check_path(path: str) -> str | None:
    """Return an error string if this bed cannot be used."""
    if not path:
        return None
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace('\\', '/')
    allowed = allowed_paths()
    if rel in allowed:
        return None
    base = os.path.basename(path)
    for p, row in allowed.items():
        if os.path.basename(p) == base:
            return None
    return (
        f'{rel} is not in the music licence register as allowed. '
        f'Add a row to assets/LICENCES.json or pick a registered bed. '
        f'Unverified tracks in assets/bgm_options/ are blocked.')


def check_package(outdir: str) -> list[str]:
    """Scan a footage or render folder for music.json / project.json beds."""
    fails = []
    for name in ('project.json', 'music.json', 'qc_report.md'):
        p = os.path.join(outdir, name)
        if not os.path.exists(p):
            continue
        try:
            text = open(p, encoding='utf-8').read()
        except OSError:
            continue
        if name.endswith('.json'):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            music = data.get('music') if isinstance(data, dict) else None
            file = None
            if isinstance(music, dict):
                file = music.get('file') or music.get('path')
                if isinstance(music.get('license'), dict) or music.get('licence'):
                    continue
            if file:
                err = check_path(file)
                if err:
                    fails.append(err)
    return fails
