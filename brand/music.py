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


# A licence you cannot point at is a licence you cannot produce when a claim
# arrives. 'own' is the one exemption — there is no URL for something the
# channel made itself — and everything else needs a page somebody can reopen.
#
# 'recorded-in-project' is not a licence. It is a note saying the terms were
# written down somewhere, which is exactly what nobody can find eighteen months
# later when a Content ID claim lands on a film that has been up since Ganesha.
SELF_MADE = ('own',)


def allowed_paths() -> dict[str, dict]:
    out = {}
    for row in load().get('tracks', []):
        path = (row.get('path') or '').replace('\\', '/')
        if path and row.get('status') == 'allowed':
            out[path] = row
    return out


def audit() -> list[str]:
    """Walk the register against the disk and against itself.

    The quarterly licence_audit in the editorial calendar, as something that
    runs rather than something somebody remembers to do.
    """
    import glob
    problems: list[str] = []
    reg = load()
    rows = reg.get('tracks', [])
    listed = {(r.get('path') or '').replace('\\', '/') for r in rows}

    on_disk = set()
    for ext in ('mp3', 'wav', 'm4a', 'aac'):
        for f in glob.glob(os.path.join(ROOT, 'assets', '**', f'*.{ext}'),
                           recursive=True):
            on_disk.add(os.path.relpath(f, ROOT).replace('\\', '/'))

    for p in sorted(on_disk - listed):
        problems.append(
            f'{p} is on disk and not in the register. An unregistered bed '
            f'cannot be used, but it can be picked by mistake — add a row, '
            f'even if that row says blocked.')

    for p in sorted(listed - on_disk):
        problems.append(
            f'{p} is registered and not on disk. Either it was deleted, or a '
            f'path moved and a render that asks for it will fail at the worst '
            f'moment.')

    for r in rows:
        if r.get('status') != 'allowed':
            continue
        path = r.get('path', '?')
        lic = (r.get('licence') or '').strip()
        url = (r.get('source_url') or '').strip()
        if not lic:
            problems.append(f'{path} is allowed with no licence recorded at all.')
        elif lic not in SELF_MADE and not url:
            problems.append(
                f'{path} is allowed under {lic!r} with no source_url. '
                f'{"Artist " + r["artist"] + ". " if r.get("artist") else ""}'
                f'That is a third-party track with nothing to produce when a '
                f'Content ID claim arrives. Paste the licence page URL, or set '
                f'status to blocked until somebody can.')
    return problems


def _provenance_gap(row: dict) -> str | None:
    lic = (row.get('licence') or '').strip()
    url = (row.get('source_url') or '').strip()
    if lic in SELF_MADE:
        return None
    if not url:
        who = f' by {row["artist"]}' if row.get('artist') else ''
        return (f'{row.get("path", "this bed")} is marked allowed under '
                f'{lic or "no licence"}{who}, but the register has no '
                f'source_url — so there is nothing to produce if a Content ID '
                f'claim arrives. Add the licence page to assets/LICENCES.json, '
                f'or pick a bed that has one.')
    return None


def check_path(path: str) -> str | None:
    """Return an error string if this bed cannot be used."""
    if not path:
        return None
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace('\\', '/')
    allowed = allowed_paths()
    if rel in allowed:
        return _provenance_gap(allowed[rel])
    base = os.path.basename(path)
    for p, row in allowed.items():
        if os.path.basename(p) == base:
            return _provenance_gap(row)
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
