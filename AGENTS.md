# 🌾 ಊರ್ಮನಿ ಸುದ್ದಿ (Oormani Suddi)

> **Brand**: ಊರ್ಮನಿ ಸುದ್ದಿ · **Tagline**: ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ
> **Handle**: `@oormanisuddi`
> **Coverage**: ಕರಾವಳಿ — coastal Karnataka. One word, set in `tokens.Brand.coverage`.

This file is the contract. If another document disagrees with it, that
document has a bug. The system it describes is the one decided in
[`docs/DECISIONS.md`](docs/DECISIONS.md) **D92** (2026-09-27). The system
before it is kept at the git tag `pre-final-upgrade-2026` for anyone who needs
the old formats; nothing from it runs today.

---

## Start here

**An AI tool handed news copy → read [`docs/AI_BRIEF.md`](docs/AI_BRIEF.md)
first.** The JSON contract, how a story picks its format, the picture rule,
and what will be rejected.

**The editor pastes news in this chat, approves, or says "Stop" → follow
[`docs/RUNBOOK.md`](docs/RUNBOOK.md) "Chat workflow" exactly**, whichever AI
tool you are. It is the editor's standing instruction for how a conversation
drives the day.

**Raw video clips** → [`.claude/skills/youtube-longform-edit/SKILL.md`](.claude/skills/youtube-longform-edit/SKILL.md)
for a long-format YouTube video, [`.claude/skills/reels-shorts-edit/SKILL.md`](.claude/skills/reels-shorts-edit/SKILL.md)
for a vertical Reel / Short.

**A human changing the design → [`STANDARDS.md`](STANDARDS.md)**, then
`docs/DECISIONS.md` before changing any value.

---

## What the channel makes

Three news formats, and only three (D92). Every story carries `segment` and
runs in that one format only — one story, one format.

| `segment` | renders as | name | shape | pictures |
|---|---|---|---|---|
| `speed` | `roundup` | ಸ್ಪೀಡ್ ನ್ಯೂಸ್ | 9:16 reel, one frame per story | a picture if the story has one; otherwise a type-only frame |
| `saara` | `saara` | ಸುದ್ದಿ ಸಾರ | 4:5 carousel: index cover → one slide per story → sources & follow | **never** |
| `mukhya` | `mukhya` | ಮುಖ್ಯ ಸುದ್ದಿ | 4:5 carousel for ONE breaking/top story: photo cover → ಏನಾಗಿದೆ? points → source & corrections | **always** |

How many stories each takes lives in `tokens.Limits` (`roundup_min_stories`,
`saara_min_stories`, `saara_max_stories`, `mukhya_max_per_day`) — quote the
names, never the values. Festival greetings (`kind: "greeting"`) and the two
footage skills also stay; they are not news formats.

---

## Doing the work

```bash
# intake — pasted news in, source kept
python3 scripts/intake.py source --url URL --outlet NAME < paste.txt   # or --file F
python3 scripts/intake.py source < paste.txt       # own reporting / press release: no --url
python3 scripts/intake.py seen editions/DATE.json  # anything already published (DUP-01)

# checking
python3 scripts/fact_check.py editions/DATE.json   # every figure vs the kept source, offline (D84)
python3 render.py --check editions/DATE.json       # validate, render nothing
python3 scripts/dispatch.py                        # which agents are due, in waves
python3 scripts/verify.py editions/DATE.json --story N --by NAME   # a person checked it

# making
python3 render.py editions/DATE.json               # every segment present in the edition
python3 render.py editions/DATE.json --only saara  # any of: roundup saara mukhya
python3 render.py editions/greetings/X.json        # a festival wish
python3 render.py --describe                       # every format and its rules
python3 render.py --schema story                   # the input contract

# after
python3 scripts/sign_off.py out/DATE --by "<name>" # taste / culture / news, signed by a person
python3 scripts/archive_edition.py DATE            # Stop: the published record
python3 scripts/verify_narration.py out/DATE       # did the voice say the words

# the newsroom
python3 scripts/health.py                          # is anything quietly broken
python3 scripts/house_rule.py list                 # standing instructions in force
python3 scripts/house_rule.py where "…"            # where does this change belong
python3 scripts/whats_on.py                        # what is coming, what is overdue
python3 scripts/correction.py status               # the IT Rules clocks
python3 scripts/metrics.py report                  # whether the guessed numbers hold
bash scripts/backup.sh --status                    # three copies, or fewer

python3 -m unittest tests.test_contract            # the contract (instant)
python3 -m unittest discover tests                 # + the golden design
```

On a fresh checkout, once:

```bash
python3 -m pip install --break-system-packages -r requirements.txt
bash scripts/install_hooks.sh          # contract runs before every commit
bash scripts/backup.sh --install       # nightly backup
```

Nothing is scheduled to fetch or draft news. The editor pastes it (D92).

Content is JSON in `editions/`. You never write rendering code — the formats
already exist (`python3 render.py --describe`).

---

## Rules that override anything you might infer

1. **`Story.validate()` is not negotiable.** Every photograph carries a credit,
   a licence and a declared nature. Every story names a source and its
   `segment`. ಬ್ರೇಕಿಂಗ್ is computed from the publish timestamp, never asserted.
   Do not add an override flag — it will be used on a deadline, and then the
   whole system is decoration.
2. **Real pictures first; AI only after asking (D92).** ಸುದ್ದಿ ಸಾರ never
   carries pictures. ಮುಖ್ಯ ಸುದ್ದಿ always does (`IMG-04` without one). When a
   mukhya story — or a speed story that wants one — has no picture, **ask the
   editor "real photo or generate?"** and record the answer in `photo_plan`
   (`real` | `ai`). Never supply a picture on your own initiative.
   - A **real** photo carries `credit` and `licence` (`own` only if our
     reporter shot it), `nature` `actual` / `handout` / `file`, and a
     `caption` saying what it shows.
   - An **AI** picture is made only with `photo_plan: "ai"`, and its photo
     carries `approved_by` — the editor's name. `Photo.validate()` refuses
     one without it (`IMG-05` at the gate). One single frame; no text, signs,
     banners or number plates; never an identifiable face standing in for a
     real, named person. `nature: "ai"`.
   - There is no stock library. Do not scrape pictures off the web.
3. **Paper & Red (D92, [`STANDARDS.md`](STANDARDS.md)).** Light paper, ink
   type, the logo's exact colours from `tokens.C`. Red is the news — kicker,
   ಬ್ರೇಕಿಂಗ್, the half of a headline after its colon. Sunset gold is the brand —
   a fill or a rule, never small type (`gold_800` when gold must be text).
   Crime and death headlines are ink only. Left-aligned, square corners. A
   festival **greeting** is its own genre with its own look
   (`templates/greeting.py`, D54).
4. **Crime copy states allegations, never verdicts.** Enforced by
   `Story.validate()` (D29–D30). The `headline` and `reel_line` are checked
   **on their own** — each travels without the rest of the story, so each
   carries its own ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ. A qualifier in the deck does not
   cover a headline.
5. **No source, no claim. No human verification, no publication.** A story
   that is not own reporting needs a `source_url` the editor can reopen, and
   its pasted text is kept (`scripts/intake.py source`). It ALSO needs
   `verified_by`: the name of the person who checked it. `status` is not
   that — "confirmed" is what the card says about the news, and a model can
   write it. **An assistant may run `scripts/verify.py` only with the name
   the editor gives in chat when they approve. Never invent or assume a
   name.** D55, D59.
6. **One story, one format, once.** `segment` holds one value. A source
   already published on an earlier day is refused (`DUP-01`) unless the story
   sets `follows_up` and carries a new fact.
7. **`APPROVAL.md` is a mechanical clearance, not a verdict.** It says the
   checks passed. Whether the lead is right, a deity treated with dignity, the
   package the channel at its best — a person looks at `_review/` at feed
   size and signs: `python3 scripts/sign_off.py out/DATE --by "<name>"`. Do
   not upload an unsigned package; never sign in someone else's name. D62.
8. **Keep `tokens.Brand.grievance_officer` and a watched contact filled in.**
   IT Rules 2021 Part III requires a named Grievance Officer — Gautam
   Paduvari, WhatsApp +91 96117 56514, email oormanisuddi@gmail.com — and the
   line is on every closing slide. `compliance()` and `review()` fail while it
   is blank. See `docs/CORRECTIONS.md`.
9. **Platform strategy: YouTube ≠ Instagram.** Weeks 1–3: AI TTS + slideshow
   reels averaged 37 views on YouTube, real footage 397 — a 10× gap.
   - **YouTube** gets real camera footage, a real human voice, or a
     face-to-camera read. Rendered graphics may sit on top of footage; they
     are never the whole video.
   - **Instagram** gets the three formats.
   - **Reels from `render.py` (ಸ್ಪೀಡ್ ನ್ಯೂಸ್) are Instagram-only.** Cross-post
     to YouTube Shorts only when the editor explicitly asks.
   - Every YouTube description ends with an engagement question in Kannada
     ("ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.").
10. **Strict workspace isolation.** No AI model, agent, subagent, script or
    tool reads, writes, runs or inspects anything outside
    `/Users/shameekyogi/My Apps/Oormani Suddi`. Path traversal out of it is
    prohibited and must fail closed. Anything outside (for example a
    LaunchAgent) is a job for a person.

**Stop means one thing:** archive with `python3 scripts/archive_edition.py
DATE`. Never delete the edition JSON.

---

## The team

Agents live in `.claude/agents/` — intake-editor, fact-checker,
legal-standards, kannada-editor, picture-editor, social-writer,
package-inspector, gate-doctor, corrections-officer, systems-steward,
planning-editor. Do not decide from memory which to call:
`python3 scripts/dispatch.py` lists who is due, in waves. Launch each wave as
ONE message of parallel Agent calls, one agent per story. No agent verifies,
signs, uploads or answers a complaint. D87, D89.

---

## Asking for a change

Four places, and only four. `python3 scripts/house_rule.py where "…"` tells you
which:

| What | Where | Why there |
|---|---|---|
| a **number** | `tokens.Limits` + decision + test | D56 — one home, or it drifts |
| a **legal** rule | `brand/content.py` + test + decision | D29 — never in a file that can be edited on a deadline |
| a **place** | `copy.PLACE_TAGS` | one registry, read by hashtags, forwards and reach |
| everything else | `scripts/house_rule.py add` | wording, habits, preferences |

A house rule applies from the moment it is added, every run, until retired. It
**cannot** switch a check off — `add()` refuses that. `AGENTS.md` beats a house
rule; a house rule beats a skill's defaults. D73.

---

## When it goes wrong

[`docs/RUNBOOK.md`](docs/RUNBOOK.md) — every gate code mapped to its fix, both
statutory clocks, and what to do when the golden test fails.

---

## Layout of the project

```
render.py           JSON in, finished design out — the entry point
editions/*.json     the content; one file per day
templates/          roundup (ಸ್ಪೀಡ್ ನ್ಯೂಸ್), saara, mukhya, greeting
  __init__.py         the registry: what each takes, its limits
brand/              the engine — read STANDARDS.md before changing any of it
  tokens.py           colour, type scale, grid, formats, Limits
  typo.py             Kannada-safe text engine (baselines, wrapping, fitting)
  content.py          Story / Photo / Edition, the contract, the clock,
                      and the India criminal-reporting guards
  copy.py             captions, hashtags, alt text
  review.py           the Chief Editor gate (APPROVAL.md)
  voice.py            narration and the pronunciation normaliser (D53)
scripts/            intake, fact check, verify, sign-off, archive, dispatch …
schemas/            JSON Schema for the input, generated from the code
docs/               AI_BRIEF, RUNBOOK, DECISIONS, TEMPLATES (generated)
tests/              the contract, and golden hashes pinning the design
assets/  fonts/  sfx/    logo master + derivatives, the faces, sound
out/                rendered deliverables (not tracked; out/_blessed/ holds the golden renders)
```

`assets/logo.png` is the **master** logo. Do not delete it.

## Regenerating the generated files

```bash
python3 -m templates --dump && python3 schemas/_build.py && python3 docs/_build_templates_md.py && python3 docs/_build_traceability.py
```

Derived from code so they cannot drift. Run them after touching the registry,
the category list, or the Story fields.
