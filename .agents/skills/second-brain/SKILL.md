---
name: second-brain
description: >
  Newsroom workflow for ಊರ್ಮನಿ ಸುದ್ದಿ — the one skill for the daily news.
  Activates when the editor pastes news and says what to make, or says
  "start", "start today", "stop yesterday and start today", "approved by …",
  or "stop". Paste → intake → desks in waves → show & ask → approve → render →
  gate → sign → Stop (archive).
---

# Second Brain — ಊರ್ಮನಿ ಸುದ್ದಿ

> **Trigger**: the editor pastes news, or says `start` / `produce`
> **Exit**: `stop` / `close` / `done` — archive, never delete

The step-by-step is [`docs/RUNBOOK.md`](../../../docs/RUNBOOK.md) "Chat
workflow". This skill is the way of working around it. Code enforces law,
length, disclosure and files; a person owns facts, the picture decision, the
native ear, the sign-off and the upload.

Read every run: [`AGENTS.md`](../../../AGENTS.md) (the contract),
[`docs/AI_BRIEF.md`](../../../docs/AI_BRIEF.md) (the JSON), and the house rules:

```bash
python3 scripts/house_rule.py list
```

A house rule beats this file; `AGENTS.md` beats a house rule. If a house rule
contradicts the contract, stop and say so.

---

## The day

1. **Paste.** The editor pastes news and says what to make. Nothing is fetched
   or scraped.
2. **Intake.** The `intake-editor` agent (or you) keeps each item's text as its
   source — `python3 scripts/intake.py source …` — and writes
   `editions/<date>.json` with one `segment` per story (`speed` / `saara` /
   `mukhya`, D92). Then `python3 scripts/intake.py seen editions/<date>.json`.
3. **Desks, in waves.** `python3 scripts/dispatch.py` says who is due. Each
   wave is ONE message of parallel Agent calls, one per line it prints (a desk
   reads several stories in one run): fact-checker + legal-standards +
   instagram-strategist first (`scripts/fact_check.py` runs offline against the
   kept source), then kannada-editor + picture-editor.
   Check each agent's evidence against the kept source before applying it.
4. **Show & ask — then wait.** Every story in plain language, its source, its
   flags, and its proposed segment. Ask the editor to confirm segments; for
   every `mukhya` story with no picture ask **"real photo or generate?"** and
   record `photo_plan`; ask if there is anything to add.
5. **Approve.** The editor says yes and gives their name. Run
   `python3 scripts/verify.py editions/<date>.json --story N --by "<that name>"`
   for the stories they saw — only with the name they gave in chat, never one
   you chose.
6. **Render.** `python3 render.py editions/<date>.json` (every segment
   present). Then package-inspector and social-writer (caption audit).
7. **Adversary, once.** One pass over the rendered package, before the gate
   (below).
8. **Gate.** The Chief Editor gate writes `APPROVAL.md` only when clean. HELD →
   gate-doctor maps each code to its fix.
9. **Sign.** Show the `_review/` frames at feed size and point at the
   `*_caption.txt` files. The editor signs:
   `python3 scripts/sign_off.py out/<date> --by "<name>"`. You never sign.
   Hand over the `.mp4` slides — never the `.jpg` stills (AGENTS rule 11). A
   re-render unsigns the package (D108); the editor looks and signs again.
10. **Stop.** `python3 scripts/archive_edition.py <date>`. The edition JSON is
    never deleted.

### Shortcuts for the same steps

`scripts/daily_flow.py` wraps the commands above; it decides nothing.

```bash
python3 scripts/daily_flow.py archive-yesterday        # Stop for the last day
python3 scripts/daily_flow.py receipts                 # the waves due (files nothing)
python3 scripts/daily_flow.py verify --by "<name the editor gave>"   # every story
python3 scripts/daily_flow.py render --by "<name>"     # render, then wave 3
```

Sources are kept one story at a time — `scripts/intake.py source` — never by
splitting a paste with a script (D111).

---

## How every desk reports

```
ROLE        one line: what you are, and the one thing you are for
LOOKING AT  the exact artefact — a path, a field, a frame, a number
MAY BLOCK   what this role may stop the day for
MAY NOT     its boundaries
EVIDENCE    the values, filled in. headline 81 chars · points 3 · source kept yes
VERDICT     PASS · FIX (named, with the edit) · BLOCK (named, with the reason)
COULD NOT CHECK  anything perceptual or unverifiable — say it
```

No evidence, no verdict. Scores out of 10 are not evidence. BLOCK names the
fix. **Two passes, then HELD:** a story still failing after its second pass is
held and the editor is told why — a day that publishes three good stories and
holds the fourth beats a day that published four, one of them wrong.

---

## The adversary — once, before the gate

One pass that argues the package should NOT run. It has no veto; it makes the
case and the editor decides. It must actually attempt:

1. **"This headline is defamatory."** As a lawyer for the person named.
2. **"This claim is not sourced."** The most specific number, name or cause —
   which kept source carries it?
3. **"This picture is wrong."** Misleading, disrespectful, or an AI frame
   passing as a photograph — or a generated picture nobody approved.
4. **"Nobody will forward this."** No town, no takeaway.
5. **"This is not our story."** Statewide news with a coastal dateline stuck on.

Verdict per story: NOTHING / CONCERN / SERIOUS. If it returns NOTHING on every
story every day, it is not working — say so.

---

## Pictures, in one paragraph

ಸುದ್ದಿ ಸಾರ never carries pictures. ಮುಖ್ಯ ಸುದ್ದಿ always does. Real photographs
first, credited and licensed, with a caption. A picture is generated only when
the editor answered "generate" (`photo_plan: "ai"`), and it carries their name
in `photo.approved_by`: one frame, no text or signs or number plates, never an
identifiable face standing in for a real named person, `nature: "ai"`. Culture
veto — wrong geography, a distorted ritual or deity, a child's or victim's
face, gore — is the editor's yes/no. AGENTS rule 2.

---

## When the owner wants something changed

Somebody says "from now on always X"; three weeks later nobody remembers.
**Route it, then record it.** Four places, and only four:

```bash
python3 scripts/house_rule.py where "reels should be 30 seconds"
```

| What was asked for | Where it goes | Why there |
|---|---|---|
| a **number** — duration, budget, loudness, slot, count | `tokens.Limits` + a decision + a test | numbers live in one place (D56) |
| a **legal** rule — allegation, minor, victim, licence, grievance | `brand/content.py` + a test + a decision | a guard in markdown gets edited on a deadline (D29) |
| a **place** | `copy.PLACE_TAGS` | one registry of towns |
| **everything else** — wording, habits, order of work | a house rule | this is what it is for |

```bash
python3 scripts/house_rule.py add "…" --scope picture --why "…" --by "<name>"
python3 scripts/house_rule.py retire <id> --why "…"
```

Scopes: `desk` · `picture` · `package` · `gate` · `footage` · `greeting` ·
`always`. Retiring keeps the record.

A house rule **cannot** switch a check off — `add()` refuses one that tries.
If a guard is genuinely wrong: change the code, write the decision, add the
test. When the owner asks mid-session, do it for today, then route and record
it, and tell them where it went and its id.

---

## What this skill does NOT do

- modify `brand/`, `templates/` or `render.py` on a production day
- invent facts, sources, URLs, quotes or credits
- fetch or scrape news or pictures
- generate a picture the editor has not asked for
- choose a name for `verified_by`, or sign, ever
- post, or send an AI-card reel to YouTube
- answer a grievance — log it with `scripts/correction.py new` and tell the
  person; the 24h / 15-day clocks are statutory
- write a house rule that waives a check
- delete the edition JSON
