# Runbook — a day, and the days that go wrong

The system book explains why everything is the way it is. This is the other
document: what to type, in what order, and what to do when something breaks
with a post due.

Nothing here is new policy. If this file and `AGENTS.md` disagree, `AGENTS.md`
is right and this file has a bug. The formats and the picture rule are
DECISIONS D92.

---

## Every time you sit down

```bash
python3 scripts/health.py
```

One page: is anything past a statutory clock, is there a second copy of the
published record, is a review overdue, is the code pushed, does the contract
still pass. Everything it reads is inside this repository.

---

## Chat workflow: paste / approve / Stop

The day runs through a conversation with an AI assistant. The scripts are
exactly the ones below — this is a front door onto them, not a second set of
rules. Any AI reading `AGENTS.md` follows this precisely.

### Who does what

One newsroom, three kinds of worker. Nobody does another's job, and the
machine refuses to move on until each has done theirs (D95).

| Who | Does | Never does |
|---|---|---|
| **The editor** (a person) | pastes the news and says what to make; answers "real photo or generate?"; approves with their name; looks at `_review/` and signs; posts | — |
| **The managing editor** (the AI assistant in chat) | keeps sources (`intake.py`), builds the edition, runs `dispatch.py` and launches each wave, applies the desks' edits, shows the editor every story, runs `verify.py` with the name the editor gave, renders, reports the gate | writes a fact the paste does not say; invents a name; signs; skips a wave |
| **intake-editor** | turns a large paste into the edition, one segment and a true category per story | — |
| **fact-checker** · up to `Limits.agent_batch_max` stories per run | every figure, name and place against the kept source, one receipt per story | edits copy for style |
| **instagram-strategist** · one run per edition | the reach plan: is each story in the right format, the cover hook, text load, the slot, the first comment and the first-hour plan — from `docs/INSTAGRAM.md` and the channel's own numbers | edits anything; invents a multiplier; recommends bait; decides a segment |
| **legal-standards** · each risky story | reads as the lawyer for the person named | — |
| **kannada-editor** · batched like the fact desk | natural Kannada, the source's own words, no fact changed | — |
| **picture-editor** · each story with a picture | checks a real photo; writes the brief and checks an AI one — only after `photo_plan: ai` | generates without being asked |
| **package-inspector** · one per rendered format | every frame at feed size | — |
| **social-writer** | every paste file — captions, WhatsApp, Facebook — against the Instagram rules, marking which are platform rules and which are our hypotheses | — |
| **gate-doctor** | only when the gate is HELD: names each fault's owner | fixes copy itself |
| **corrections-officer** | complaints and the IT Rules clocks | — |
| **planning-editor**, **systems-steward** | weekly, off the production path | — |

**What the machine enforces.** The gate refuses `APPROVAL.md` while any
desk the plan lists has not read the edition's *current* wording, or blocked
it (`OPS-04`). Change a headline after the Kannada desk read it, and that desk
is due again. `sign_off.py` refuses while any rendered format has not been
inspected, or the paste files not audited, since the last render.

### Start — the editor pastes news

The editor pastes the day's news (articles, press releases, what they saw) and
says what to make — "speed news", "saara", "this one is mukhya", or nothing.
Nobody fetches or scrapes news; there is no morning job. The assistant (or the
`intake-editor` agent):

1. **Keeps every source.** For each item:
   ```bash
   python3 scripts/intake.py source --url URL --outlet NAME < paste.txt   # or --file F
   python3 scripts/intake.py source < paste.txt   # own reporting / press release: no --url
   ```
   A link is credited to the outlet it belongs to; a press release to whoever
   issued it; what the editor saw or was told is `ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ`
   (D88). A link copied out of a chatbot answer is replaced by the
   publisher's own.
2. **Builds `editions/<date>.json`** (schema_version 4, contract in
   [`AI_BRIEF.md`](AI_BRIEF.md)) with a `segment` on every story — what the
   editor said, or the desk's proposal where they did not. Nothing is
   written that the pasted text does not say.
3. **Checks nothing is a repeat:**
   ```bash
   python3 scripts/intake.py seen editions/<date>.json
   ```
   A source already published on an earlier day is refused at the gate
   (`DUP-01`) unless the story sets `follows_up` and carries a new fact.
4. **Runs the desks in waves.** `python3 scripts/dispatch.py` lists who is
   due, as agent runs. Each wave is ONE message of parallel Agent calls, one
   per line (a desk reads several stories in one run, D97):
   - wave 1 — `fact-checker` + `legal-standards` + `instagram-strategist`
     (`python3 scripts/fact_check.py editions/<date>.json` checks every figure
     against the kept source, offline);
   - wave 2 — `kannada-editor` + `picture-editor`.

   Apply the strategist's proposals the way you apply any desk's edit — the
   hooks into `hook`, a format change only if the editor agrees.

   No sentence is polished before its fact check passes (D84, D87). These
   waves are not optional: the gate holds any edition a due desk has not
   read (`OPS-04`, D95). The first ಸುದ್ದಿ ಸಾರ skipped them and shipped a death
   in red, three wrong categories and two wording slips.
5. **Shows the editor every story and asks — then waits.** In plain language:
   what happened, where, the source, anything flagged (crime, a minor, a
   sexual offence, a death), and the **proposed segment**. Then asks:
   - "Are these segments right?" (one story, one format);
   - for every `mukhya` story with no picture — and any `speed` story that
     wants one — **"Real photo or generate?"** The answer goes in
     `photo_plan` (`real` | `ai`). With `real`, wait for the photograph. With
     `ai`, the picture is generated only now, and its photo carries
     `approved_by` with the editor's name;
   - "Anything else to add?"

   Nothing is rendered, verified or published at this point.

### Approve — the editor says yes, with their name

"Go", "approved", "make it" — with the name to record. The assistant:

1. **Records verification under that name**, for exactly the stories the
   editor was shown:
   ```bash
   python3 scripts/verify.py editions/<date>.json --story N --by "<name the editor gave>"
   ```
   The assistant may run this **only** with the name the editor gives in
   chat when they approve. Never invent, assume or reuse a name. A story
   whose source could not be shown is left unverified.
2. **Renders** every segment in the edition:
   ```bash
   python3 render.py editions/<date>.json --check
   python3 render.py editions/<date>.json          # or --only roundup saara mukhya
   ```
   Into `out/<date>/`: `roundup.mp4` + `roundup_cover.jpg`; the carousels as
   animated slides — `saara_01_cover.mp4`, `saara_02.mp4` … `saara_NN_sources.mp4`;
   `mukhya_1_01_cover.mp4`, `mukhya_1_02_points.mp4`, `mukhya_1_03_source.mp4` —
   each with its `_copy.txt` and `_caption.txt`. **Post the .mp4s** as ONE
   carousel post of separate videos (＋ → Post → select multiple → tick them
   in order, D100) — never joined into one video — and keep Instagram's
   default thumbnail (D101). Each slide's finished still (`.jpg`) is kept in
   `out/<date>/_review/`: what the inspector reads, never what is posted
   (D102). `--still` skips the videos for a quick draft render (the .jpgs then
   stay in `out/<date>/`).
3. **Runs one adversary pass, then the gate.** The Chief Editor gate writes
   `APPROVAL.md` only when clean. If it is HELD, `gate-doctor` maps each code
   to its fix (table below). Then **wave 3**, as one message: a
   `package-inspector` per rendered format and the `social-writer` over every
   paste file. `sign_off.py` will not accept a signature until both have
   reported on this render (D95).
4. **Points at the caption files** — `roundup_caption.txt`,
   `saara_caption.txt`, `mukhya_1_caption.txt`: the caption and nothing else,
   so posting is open, select all, paste (house rule 2026-09-17-06).
5. **Hands over for sign-off.** The editor looks at `out/<date>/_review/` at
   feed size, listens to the ಸ್ಪೀಡ್ ನ್ಯೂಸ್ once, and signs:
   ```bash
   python3 scripts/sign_off.py out/<date> --by "<name>"
   ```
   The assistant never signs. D62.

### Stop — archive

"Stop" means one thing:

```bash
python3 scripts/archive_edition.py <date>
```

It copies the edition JSON, `APPROVAL.md`, `SIGNOFF.json`, the captions, the
town forwards (`forward_*.txt`), the Facebook posts, `REACH.md` and the
review frames into `archive/<date>/`, then clears the heavy renders. **The
edition JSON is never deleted.** The date has to be `YYYY-MM-DD`.

### If the old morning job still runs

The pre-D92 system installed a LaunchAgent that fetched and drafted news at
06:10 and 07:00. Its scripts are gone, so it can only fail. It lives outside
this repository, so **a person** removes it:

```bash
launchctl bootout gui/$(id -u)/com.oormanisuddi.morning
rm ~/Library/LaunchAgents/com.oormanisuddi.morning.plist
```

---

## Posting

| File | Where | When |
|---|---|---|
| `saara_*.mp4` + `saara_caption.txt` | Instagram carousel (separate videos, one post) | `Limits.carousel_slot` |
| `mukhya_<k>_*.mp4` + `mukhya_<k>_caption.txt` | Instagram carousel (separate videos, one post) | `Limits.mukhya_slot`, or the moment it breaks |
| `roundup.mp4` + `roundup_cover.jpg` + `roundup_caption.txt` | Instagram Reels only | a slot in `Limits.reel_slots` |

`schedule.txt` in the folder is written from what was actually rendered —
follow it. Paste the first comment (in `_copy.txt`) the moment you post.
AI-card reels never go to YouTube unless the editor asks (AGENTS rule 9).

### The forwards — this is the circulation department

```bash
cat out/<date>/REACH.md       # which towns this edition speaks to
ls  out/<date>/forward_*.txt  # one per town
```

Send each town's forward to **that town's** groups, not to everyone. People
forward what is theirs.

### A short day

Decided in advance (D69). Each format has a floor in `tokens.Limits`
(`roundup_min_stories`, `saara_min_stories`); `mukhya_max_per_day` is a
ceiling. Below a floor, the story goes in another format or waits — the
format is never padded with a weak story to reach it. Two solid stories told
well beat five nobody checked. `ಇಂದು ಯಾವುದೇ ಹೊಸ ಸುದ್ದಿ ಇಲ್ಲ` is a position.

What never drops: `verified_by`, the legal guards, the sign-off.

---

## What is coming

```bash
python3 scripts/whats_on.py              # the next 30 days
python3 scripts/whats_on.py --days 90    # plan a quarter
python3 scripts/whats_on.py --reviews    # what is overdue
python3 scripts/whats_on.py --scaffold ganesha    # start a greeting JSON
```

Lunar festivals show the **month** and never the day — confirm each from a
Udupi panchanga. A greeting on the wrong day is worse than no greeting.

---

## When it goes wrong

### The gate is red

`review_report.json` names the code and who owns the fix. The common ones:

| Code | What it means | What to do |
|---|---|---|
| `SRC-02` | a story has no `verified_by` | the editor checks it and gives their name; `verify.py` records it. Never an assistant's own choice of name. |
| `DUP-01` | the source was already published on an earlier day | drop it, or set `follows_up` and carry the new fact |
| `FACT-01` | a figure is not in the kept source | find it in the source or cut it |
| `FACT-02` | the source does not carry the story | wrong link — get the real article, or paste its text |
| `FACT-05` / `FACT-06` | not an article page / credited to the wrong outlet | the publisher's own article URL, credited to that publisher |
| `LAW-01` | a crime line asserts guilt | rewrite the **headline** and the **reel_line** themselves |
| `IMG-01` | an image would show with no disclosure | credit + a nature other than `actual`, or a caption |
| `IMG-02` | a generated image is wearing the wrong nature | `nature: "ai"` |
| `IMG-04` | a ಮುಖ್ಯ ಸುದ್ದಿ has no picture | ask the editor "real photo or generate?"; record `photo_plan` |
| `IMG-05` | an AI picture has no `approved_by` | ask the editor; their name goes in `photo.approved_by` — or use a real photo |
| `SND-01` / `SND-02` | the reel is silent, or narration failed | re-run; check the network and the TTS key |
| `SND-03` | a TTS hazard in the script | ₹, `%`, a decimal, dotted initials, a clock time — D50, D53 |
| `TYPE-01` | a character no house font can set | replace it in the copy |
| `PKG-01` | the copy names a file that was not rendered | re-render, or fix the copy |
| `PUB-01` | the handle is miscapitalised | `@oormanisuddi`, exactly |
| `PUB-05` | the town name is past the caption fold | put the town in the first 125 characters |
| `PUB-08` | a story names no place | set `location` |
| `PUB-09` | more hashtags than Instagram reads | five at most; towns go on the 📍 line (D86) |
| `OPS-01` | no Grievance Officer named | `tokens.Brand` — this one blocks everything, correctly |

### "It says cleared but also not cleared"

Correct and deliberate. `APPROVAL.md` records what a **machine** established.
Taste, cultural dignity and news judgement are signed by a person. D62.

### A render is stuck, or the Mac is swapping

Only one heavy job runs at a time; a second `render.py` refuses with the PID of
the first. A dead lock goes stale after four hours, or:

```bash
cat .render.lock     # who holds it
rm .render.lock      # only when you are sure nothing is running
```

Close Chrome. 8 GB is shared between the OS, Pillow at 2× and ffmpeg.

### The golden test failed

The rendered pixels changed. That is not automatically a bug.

```bash
python3 -m unittest tests.test_golden     # which formats moved
open out/_blessed/                        # LOOK at them
python3 -m tests.test_golden --bless      # only if the change was deliberate and right
```

If you did **not** change the design, compare `PROVENANCE.json` in a recent
render with the current environment — a Pillow, raqm or font update moves
Kannada rasterisation without anybody touching this repo.

### A reader says we got something wrong

The clock starts when the message arrives, not when you get to it.

```bash
python3 scripts/correction.py new --about 2026-09-16 \
    --summary "..." --channel whatsapp
python3 scripts/correction.py ack 2026-09-16-01 --by "Gautam Paduvari"
python3 scripts/correction.py close 2026-09-16-01 --by "Gautam Paduvari" \
    --outcome "..." --published "ತಿದ್ದುಪಡಿ: ..."
python3 scripts/correction.py status     # anything past 24h / 15 days
```

If the substance changed, the correction has to be **visible**.

### The voice said a name wrong

```bash
python3 scripts/verify_narration.py out/<date>
```

If it is a name, add it to `assets/pronunciation.json` and re-render — the fix
then applies to every future edition.

---

## Weekly

```bash
python3 scripts/whats_on.py --reviews      # anything overdue?
python3 scripts/metrics.py add --date ... --asset roundup.mp4 --format reel \
    --category civic --place ಬೈಂದೂರು --at 17:30 --seconds 34 \
    --views 412 --reach 380 --local-reach 300 \
    --saves 9 --shares 14 --watch 62
python3 scripts/metrics.py report
python3 scripts/correction.py weekly       # draft the clarifications post
bash scripts/backup.sh --status            # three copies, or fewer?
```

`--local-reach` is the in-district number from Instagram Insights → Audience →
cities. Every number in `tokens.Limits` is a hypothesis until this has enough
rows to argue with.

## Asking for something to change from now on

```bash
python3 scripts/house_rule.py where "reels should be 30 seconds"
```

A **number** goes to `tokens.Limits` with a decision and a test. A **legal**
rule goes to `brand/content.py` with a test. A **place** goes to
`copy.PLACE_TAGS`. Everything else is a house rule:

```bash
python3 scripts/house_rule.py add "ಹಬ್ಬದ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ" \
    --scope picture --why "organisers reshare what credits them" --by "Gautam"
python3 scripts/house_rule.py list
python3 scripts/house_rule.py retire 2026-09-16-01 --why "no longer true"
```

**It cannot switch a check off.** If a guard is genuinely wrong: change the
code, write the decision saying what breaks without it, add the test.

## Before changing a number

1. Find its entry in `docs/DECISIONS.md`. If there isn't one, write it.
2. Change it in `brand/tokens.py :: Limits`, not in a document. D56.
3. `python3 -m unittest discover tests`
4. `python3 docs/_build_traceability.py`

## Installing things on this Mac

```bash
python3 -m pip install --break-system-packages -r requirements.txt
```

Optional: `mlx-whisper` lets `verify_narration.py` hear whether the voice said
the words; without it narration is checked as text only.

## What is never automated

Uploading. Legal flags. `verified_by`. The sign-off. Answering a complaint.
Choosing to generate a picture. Those are the places a person is the product.

An assistant may write `verified_by` only with the name the editor gives in
the conversation when they approve, after being shown the real source. That
is a person doing the thing through a different front door — not a script or
an AI deciding on its own that something is true.
