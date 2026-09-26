# Second Brain — Trigger Rules

The workflow itself is [`docs/RUNBOOK.md`](../../docs/RUNBOOK.md) "Chat
workflow" and [`.agents/skills/second-brain/SKILL.md`](../skills/second-brain/SKILL.md).
This file only says which words start and end it. If it ever disagrees with
the RUNBOOK, the RUNBOOK is right.

## Start

The editor **pastes news** (articles, press releases, what they saw) and says
what to make — or says `start`, `produce`, `content ready`, `let's go`.

Then, per the RUNBOOK:

1. Keep every pasted item as its source (`python3 scripts/intake.py source …`)
   and build `editions/<date>.json` with one `segment` per story; run
   `python3 scripts/intake.py seen editions/<date>.json`.
2. Run the desks the dispatcher lists (`python3 scripts/dispatch.py`), each
   wave as one message of parallel agents, one per story.
3. Show the editor every story with its proposed segment, ask them to confirm,
   ask **"real photo or generate?"** for every `mukhya` story with no picture,
   and **wait**. Nothing renders before the editor approves.

No stock library, no trend scraping, no scores out of 10.

## Approve

The editor says yes and gives their name. Run `scripts/verify.py` with **that
name only**, render, run the gate, point at the `*_caption.txt` files. The
editor signs with `scripts/sign_off.py`.

## Stop

`stop`, `close`, `done`, `finish` — **one meaning**:

```bash
python3 scripts/archive_edition.py <date>
```

Never delete the edition JSON.

## Reminders

- Never modify `brand/`, `templates/` or `render.py` on a production day.
- If `render.py --check` fails, fix the INPUT (JSON / copy), never the renderer.
