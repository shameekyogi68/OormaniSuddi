"""
ಊರ್ಮನಿ ಸುದ್ದಿ — Corrections, as a record rather than a promise
==============================================================
`docs/CORRECTIONS.md` states the policy: acknowledge within 24 hours, dispose
within 15 days, publish a visible ತಿದ್ದುಪಡಿ rather than silently editing. IT
Rules 2021 Part III makes those two clocks a statutory obligation, not a
courtesy.

A policy with no ledger behind it cannot answer the only questions that matter
when a complaint escalates: when did we hear, what did we do, and did we do it
in time. This is the ledger. It is a JSON-lines file, because an append-only
log survives a crash mid-write and can be read by eye.

Two things it deliberately does NOT do. It does not answer anybody — a model
replying to a victim-identification complaint is a liability, and the 24-hour
clock is a legal clock. And it does not edit a published story: the
`correction` field on `Story` is what puts ತಿದ್ದುಪಡಿ on the card, and the
whole point of D-policy here is that a substantive change is visible.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'archive', 'corrections.jsonl')

ACK_HOURS = 24        # IT Rules 2021 Part III
CLOSE_DAYS = 15

STATES = ('received', 'acknowledged', 'published', 'rejected', 'closed')


@dataclass
class Complaint:
    id: str                       # 2026-09-16-01
    received_at: str              # ISO
    about: str                    # the edition date, or the asset
    summary: str                  # what they say is wrong
    complainant: str = ''         # name or handle, as given
    channel: str = ''             # whatsapp | email | instagram | comment
    state: str = 'received'
    acknowledged_at: str = ''
    resolved_at: str = ''
    outcome: str = ''             # what we changed, or why we did not
    published_correction: str = ''  # the ತಿದ್ದುಪಡಿ text that went out
    handled_by: str = ''
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _load() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    rows = []
    with open(LEDGER, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _append(row: dict) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')


def current() -> dict[str, dict]:
    """The latest state of every complaint, folded from the append-only log."""
    out: dict[str, dict] = {}
    for row in _load():
        cid = row.get('id')
        if not cid:
            continue
        out.setdefault(cid, {}).update(row)
    return out


def next_id(day: str) -> str:
    n = sum(1 for cid in current() if cid.startswith(day)) + 1
    return f'{day}-{n:02d}'


def receive(about: str, summary: str, complainant: str = '',
            channel: str = '', when=None) -> Complaint:
    """Log a complaint the moment it arrives. This starts both clocks."""
    from .content import now
    at = when or now()
    c = Complaint(id=next_id(f'{at:%Y-%m-%d}'), received_at=at.isoformat(),
                  about=about, summary=summary, complainant=complainant,
                  channel=channel)
    _append(c.to_dict())
    return c


def update(cid: str, **fields) -> dict:
    """Append a change. Nothing is ever rewritten in place."""
    from .content import now
    state = current().get(cid)
    if not state:
        raise KeyError(f'no complaint {cid!r} in the ledger')
    if 'state' in fields and fields['state'] not in STATES:
        raise ValueError(f'unknown state {fields["state"]!r}; '
                         f'choose from {STATES}')
    row = {'id': cid, 'at': now().isoformat(), **fields}
    _append(row)
    return {**state, **row}


def acknowledge(cid: str, by: str) -> dict:
    from .content import now
    return update(cid, state='acknowledged',
                  acknowledged_at=now().isoformat(), handled_by=by)


def resolve(cid: str, by: str, outcome: str,
            published_correction: str = '') -> dict:
    from .content import now
    return update(cid, state='published' if published_correction else 'closed',
                  resolved_at=now().isoformat(), outcome=outcome,
                  published_correction=published_correction, handled_by=by)


# ─────────────────────────────────────────────────────────────────────────────
#  THE CLOCKS
# ─────────────────────────────────────────────────────────────────────────────

def overdue() -> dict[str, list[dict]]:
    """Complaints past a statutory clock. The only report that is urgent."""
    from .content import now, parse_dt
    late_ack, late_close = [], []
    for cid, row in current().items():
        state = row.get('state', 'received')
        if state in ('closed', 'published', 'rejected'):
            continue
        try:
            received = parse_dt(row['received_at'])
        except Exception:
            continue
        age = now() - received
        if not row.get('acknowledged_at') and age > timedelta(hours=ACK_HOURS):
            late_ack.append({**row, 'hours': age.total_seconds() / 3600})
        if age > timedelta(days=CLOSE_DAYS):
            late_close.append({**row, 'days': age.days})
    return {'unacknowledged': late_ack, 'unresolved': late_close}


def summary_line() -> str:
    rows = current()
    if not rows:
        return 'No complaints logged.'
    late = overdue()
    open_n = sum(1 for r in rows.values()
                 if r.get('state', 'received') not in ('closed', 'published', 'rejected'))
    bits = [f'{len(rows)} logged', f'{open_n} open']
    if late['unacknowledged']:
        bits.append(f'⚠️ {len(late["unacknowledged"])} past the {ACK_HOURS}h '
                    f'acknowledgement clock')
    if late['unresolved']:
        bits.append(f'⚠️ {len(late["unresolved"])} past the {CLOSE_DAYS}-day '
                    f'resolution clock')
    return ' · '.join(bits)


# ─────────────────────────────────────────────────────────────────────────────
#  THE WEEKLY POST
#  A correction nobody sees is a correction nobody made. This drafts the
#  Kannada copy for the weekly clarifications slide; a person still posts it.
# ─────────────────────────────────────────────────────────────────────────────

def weekly_post(days: int = 7) -> str:
    from .content import now, parse_dt
    from .tokens import Brand
    since = now() - timedelta(days=days)
    published = []
    for row in current().values():
        if not row.get('published_correction'):
            continue
        try:
            when = parse_dt(row.get('resolved_at') or row['received_at'])
        except Exception:
            continue
        if when >= since:
            published.append((when, row))
    if not published:
        return ''
    lines = ['ತಿದ್ದುಪಡಿ ಮತ್ತು ಸ್ಪಷ್ಟನೆ', '']
    for when, row in sorted(published):
        lines.append(f'▪ {when:%d-%m}: {row["published_correction"]}')
    lines += ['',
              'ತಪ್ಪು ಕಂಡರೆ ತಿಳಿಸಿ. ನಾವು ಸರಿಪಡಿಸಿ, ಅದನ್ನು ಬಹಿರಂಗವಾಗಿ ಹೇಳುತ್ತೇವೆ.',
              Brand.grievance_line(),
              f'— {Brand.name} · {Brand.handle}']
    return '\n'.join(b for b in lines if b is not None)
