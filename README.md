# ಊರ್ಮನಿ ಸುದ್ದಿ · Oormani Suddi

**ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ** — a Kannada local-news channel for coastal Karnataka,
[@oormanisuddi](https://www.instagram.com/oormanisuddi/).

This repository turns the news an editor pastes into finished, checked
Instagram posts in three formats — ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (a 9:16 reel), ಸುದ್ದಿ ಸಾರ and
ಮುಖ್ಯ ಸುದ್ದಿ (4:5 animated carousels) — and refuses to make one that would
misattribute a source, assert an accused person's guilt, identify a child or a
victim, or hide that a picture was generated.

## Start here

| You are | Read |
|---|---|
| anyone, first | [`AGENTS.md`](AGENTS.md) — the contract. Short. If another document disagrees with it, that document is wrong. |
| an AI tool handed news | [`docs/AI_BRIEF.md`](docs/AI_BRIEF.md), then [`docs/RUNBOOK.md`](docs/RUNBOOK.md) "Chat workflow" |
| the editor, running a day | [`docs/RUNBOOK.md`](docs/RUNBOOK.md) |
| looking after the machine | [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md) |
| changing the design | [`STANDARDS.md`](STANDARDS.md), then [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| asking *why* anything is the way it is | [`docs/DECISIONS.md`](docs/DECISIONS.md) — `grep -n "^## D<n>"`, never read whole |

## Set up

```bash
brew install ffmpeg
python3 -m pip install --break-system-packages -r requirements.txt
bash scripts/install_hooks.sh
python3 -m unittest discover tests
python3 scripts/health.py
```

## A day, in four commands

```bash
python3 scripts/intake.py source --url URL --outlet NAME < story.txt   # keep each source
python3 render.py --check editions/DATE.json                           # validate
python3 render.py editions/DATE.json                                   # render + gate
python3 scripts/sign_off.py out/DATE --by "<name>"                     # a person signs
```

Between them sit the desks (`python3 scripts/dispatch.py`), the editor's
approval (`scripts/verify.py`) and the gate's `APPROVAL.md`. The RUNBOOK has
the order. Nothing is fetched, scheduled or posted automatically.
