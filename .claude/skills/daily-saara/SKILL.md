---
name: daily-saara
description: The editor's whole morning in one command. Use when the editor types /daily-saara (or "daily saara", /daily-Saara) and pastes the day's Kannada news — or asks to start today with Gautam Paduvari. It archives yesterday, turns the paste into ಸುದ್ದಿ ಸಾರ stories, runs the fact / legal / Kannada desks, and renders the ಸುದ್ದಿ ಸಾರ REEL (reel_saara.mp4 — one 9:16 video for Instagram Reels, Facebook Reels and YouTube Shorts), checks it, and reports. No step is asked of the editor. The carousel is NOT made unless the editor asks.
---

# Daily Saara — ಸುದ್ದಿ ಸಾರ, as a reel (D132, D133)

**What the editor wants:** type `/daily-saara`, paste the news, and get the finished
reel. Nothing in between is asked of them — not "should I make a reel?", not "which
format?", not "shall I render?", not "is this ok?". Decide, do it, check it, report it.
The only reason to stop and ask is a paste you genuinely cannot split or attribute.

**The product:** `out/<today>/reel_saara.mp4` — 1080×1920, ~50–58 s, Google Kannada
voice, house news bed, house sound effects, Ink & Gold design, front page whole at
frame 0, a follow button at the end, loops. Captions: `saara_caption.txt`
(Instagram + Facebook) and `reel_saara_youtube.txt` (the Short). Plan: `schedule.txt`.

**The carousel** (4:5 slides) is kept in the code, switched off. Make it **only** when
the editor says so (`--carousel`). Never delete it, never restyle it. If the reel cannot
be made, the render makes the carousel by itself so the day is not empty — and says so.

You are the managing editor (see `docs/RUNBOOK.md`). The agents are in `.claude/agents/`.
Work in this order and do not skip a step.

---

## Step 1 · Archive & clean yesterday

```bash
python3 scripts/daily_flow.py archive-yesterday --force
```

Archives yesterday's record to `archive/<yesterday>/` and deletes its heavy `out/`
renders. `editions/<yesterday>.json` is never deleted.

## Step 2 · Intake — the paste becomes today's edition

Do this yourself, or launch the `intake-editor` agent with the paste (it has the rules).
For each news item in the paste:

1. **Keep the source text as pasted** — `python3 scripts/intake.py source [--url URL --outlet NAME] < item.txt`
   (own reporting / no link: no flags). One story, one source; never fold one under another.
2. **Write the story into `editions/<today>.json`** (`schema_version` 4, `date`
   `<today>T09:00:00+05:30`, `strapline` `ಕರಾವಳಿ ದಿನಪತ್ರಿಕೆ`), every field **only from the paste**:
   - `segment: "saara"`, `photo_plan: ""` — ಸುದ್ದಿ ಸಾರ never carries a picture
   - `headline` — print headline, `ಊರು: ವಿವರಣೆ`. Crime/dispute copy carries ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ in it
   - **`reel_line`** — the on-screen headline. **≤ `Limits.saara_reel_line_chars` (34) characters** so it
     sets in two big lines. No town (the tag shows it). Crime copy keeps ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ in it
   - **`reel_support`** — **ONE complete sentence** from the paste, read aloud and shown whole on the
     gold card. Short: about 7–9 Kannada words for five stories, 6 for six
     (`python3 scripts/reel_check.py` prints the exact allowance). It must stand alone beside the
     headline and, for crime, must not assert guilt
   - `deck` (1–2 sentence lead), `points` (exactly 3), `takeaway` (1, if there is one) — full-length;
     the captions use them
   - `category` (what happened — never `civic` by default), `location` (coastal town, e.g.
     `ಕುಂದಾಪುರ`; two towns as `ಕುಂದಾಪುರ, ಗಂಗೊಳ್ಳಿ`), `sources`, `source_urls`, `status: "confirmed"`,
     `published_at`
   - `verified_by: "Gautam Paduvari"`, `verified_at: <now ISO>` — the editor's standing instruction
     in this skill; if the editor names someone else in chat that day, use that name. Never any other.
3. **Order lead-first** (the first story opens the reel's front page): the story most readers in the
   most towns need first. Five stories is ideal; **six is the most** (`Limits.saara_max_stories`).
   More than six: keep the best six in ಸುದ್ದಿ ಸಾರ and tell the editor which were held — never drop one silently.
4. **Already published?** `python3 scripts/intake.py seen editions/<today>.json` — a repeat needs
   `follows_up` and a new fact, or is dropped (say which).

Write figures as figures (`33ನೇ`, `22ರಂದು`, `₹500`, `ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ`): the voice says them
as Kannada words. Never write a figure you cannot find in the paste.

## Step 3 · Verify, validate, and make the reel copy CLEAN

```bash
python3 scripts/verify.py editions/<today>.json --all --by "Gautam Paduvari"
python3 render.py --check editions/<today>.json
python3 scripts/reel_check.py editions/<today>.json --strict
```

`reel_check.py` lays the real reel out in headless Chrome in a few seconds and prints, per
story, what the render would find out four minutes later. **Repeat until it says `CLEAN`**
(at most four rounds). It names exactly what to change:
- a headline that needs a third line → shorten that `reel_line`
- a card sentence too long for the clock → shorten that `reel_support` (never cut a fact — rewrite
  the sentence shorter)
- a word the voice may misread (Latin letters, a figure beyond 99 999) → respell in
  `assets/pronunciation.json` (`{"<as written>": "<as it should sound>"}`), or write it in Kannada
- the whole reel over `Limits.saara_reel_max_seconds` → shorten the longest story

Edit only `reel_line` / `reel_support` in these rounds. Never add a fact to make a sentence fit.

## Step 4 · The desks (parallel agents)

```bash
python3 scripts/dispatch.py
```

Launch each wave it lists as ONE message of parallel `Agent` calls, one per line: `fact-checker`,
`legal-standards` (crime/death/minor stories), `kannada-editor` (ಸುದ್ದಿ ಸಾರ copy, including the two
reel fields — they are spoken), `instagram-strategist`. Apply every FIX they return. A BLOCK goes to
the editor, never around it. After ANY edit to `reel_line` / `reel_support`, run `reel_check.py --strict`
again. Never file a receipt yourself for a desk that did not run.

## Step 5 · Render the reel

```bash
python3 render.py editions/<today>.json --only saara
```

About 4 minutes (the film is drawn frame by frame). It writes, in `out/<today>/`: `reel_saara.mp4`,
`reel_saara_cover.jpg`, `saara_caption.txt`, `reel_saara_youtube.txt`, `saara_copy.txt`,
`schedule.txt`, and the evidence in `_review/`.

- **"ಸುದ್ದಿ ಸಾರ REEL NOT MADE — <why>"**: read the reason. Copy that does not fit → fix it (Step 3) and
  re-render. A voice failure (Google, three tries) → re-render once. Chrome missing → tell the editor.
  (The carousel was made meanwhile so the day is not empty — say so; the reel is still the goal.)
- **Warnings** (`⚠ ಸುದ್ದಿ ಸಾರ reel: …`): word timing fell back to an even split, a headline on three
  lines, a voice word that may be misread. Fix what you can (Step 3), re-render if you changed copy.

## Step 6 · After the render — inspect and gate

```bash
python3 scripts/dispatch.py
```

Launch the due agents (`package-inspector` for `reel_saara`, `social-writer` for both caption files).
If the gate is HELD (`review_report.json`): launch `gate-doctor`, apply the mechanical fixes, re-render
(max two loops), and report anything left. Never edit a check to make a code go away.

## Step 7 · Report — short, plain, in Kannada-friendly English

1. The file: `out/<today>/reel_saara.mp4` — duration, stories, size.
2. What to post where, from `schedule.txt` (Instagram Reel + Facebook Reel + YouTube Short; the two
   caption files).
3. **Anything the editor should listen for**: the words in "may be misread" warnings, and which
   stories had to use their own sentence because `reel_support` was missing. You cannot hear the reel —
   say so; the editor listens once.
4. What the desks changed or blocked.
5. The sign-off line, with the name only if the editor has given one:
   `python3 scripts/sign_off.py out/<today> --by "<name>"` — a person signs taste and news judgement
   (D62); a model never does.

---

## Never
- ask whether to make a reel, or which format — it is always the reel
- make the carousel unless the editor asks (`render.py … --carousel`); never delete or restyle it
- put a picture on a ಸುದ್ದಿ ಸಾರ story, write a fact the paste does not carry, or invent a name
- skip `reel_check.py`, a desk wave, or the gate; or file a receipt for work no agent did
- leave the editor to fix copy: if the reel's copy is wrong, you rewrite it and re-check

If the editor reports a word mispronounced:
`python3 scripts/reel_say.py "<the sentence>" --respell "<word>=<how it sounds>" --play` — it records the
respelling in `assets/pronunciation.json` and plays it back; then re-render. That fixes the word for every
format, every day.
