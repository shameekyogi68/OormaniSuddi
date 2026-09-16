---
name: second-brain
description: >
  Newsroom workflow for ಊರ್ಮನಿ ಸುದ್ದಿ. Activates on "start with content".
  Four human stops (Desk, Picture, Package, Gate) around code that cannot
  be sweet-talked. Cleans up on "close" while archiving the published record.
---

# Second Brain — ಊರ್ಮನಿ ಸುದ್ದಿ

> **Trigger**: `start with content` (or `start`, `begin`, `content ready`, `produce`)
> **Exit**: `stop` / `close` / `done` / `cleanup`

This is a **four-stop desk**, not a 13-expert panel. Code enforces law, length,
disclosure and files. A person owns facts, pictures, the native ear, and the
upload. Scores out of 10 are forbidden — use PASS / FAIL / HUMAN REVIEW.

---

## 0 · Law first

Read these every run:

1. [`docs/AI_BRIEF.md`](../../../docs/AI_BRIEF.md)
2. [`AGENTS.md`](../../../AGENTS.md)
3. [`STANDARDS.md`](../../../STANDARDS.md) — do not modify on a production day

**D55 lock (do not negotiate):**

> No source, no claim. No human verification, no edition. No `APPROVAL.md`, no
> upload. YouTube gets tape. Generated pictures say they are generated. The
> person who publishes is legally responsible.

Constants:

```
DATE         = today's date, YYYY-MM-DD
DAILY_DIR    = out/{DATE}
DAILY_ASSETS = assets/daily/{DATE}
EDITION_FILE = editions/{DATE}.json
ARCHIVE_DIR  = archive/{DATE}
```

**Daily default** (minimum viable day):

```bash
python3 render.py editions/{DATE}.json --only carousel story_card broadsheet reel --out out/{DATE}
```

Do **not** render the AI bulletin unless the user asks, and never schedule it
to YouTube. YouTube is Line B/C footage only (AGENTS Rule 7).

Festival wishes are not editions. Write `editions/greetings/{DATE}_{festival}.json`
with `"kind": "greeting"` and render that file. Deity `keep_clear` is mandatory.

If `inbox/today.md` exists, treat it as a **tip sheet**. Do not paste it into
JSON until the editor has opened each `source_url`.

---

## Before Stop A — what is coming

```bash
python3 scripts/whats_on.py
```

A festival three days out is a shoot you can still arrange; one that is
tomorrow is a card you rush. Lunar festivals show the MONTH only — confirm the
day from a Udupi panchanga, and never let a placeholder date reach a render.

If anything is marked overdue, say so to the editor. The backup restore test is
the one that costs most to skip.

---

## Stop A — Desk (facts, Kannada, legal flags)

**Person decides:** which tips become stories, whether it is a reel, legal flags,
obituary tone, whether the source was actually opened.

**Machine does:** length budgets, Latin numerals, allegation scan, unknown
category fail, source_url requirement.

### Copy rules

- Headline ≤ 78, `reel_line` ≤ 46, hook ≤ 7 words (lead only), deck ≤ 190
- Points: max 3, each ≤ 150. Latin numerals only.
- Crime: `headline` AND `reel_line` each carry ಆರೋಪ / ಆರೋಪಿ / ಶಂಕಿತ / ಪ್ರಕರಣ ದಾಖಲು
- Every story: `sources` plus `source_urls` (http), **or**
  `sources: ["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"]`
- Every story: `verified_by` — the NAME of the person who opened that source
  and checked the facts. **You may not fill this in.** If the person has not
  said they checked it, say so and stop. The gate will not write APPROVAL.md
  without it, and that is the point. (D59)
- Obituary: two sources or own reporting
- `involves_minor` / `sexual_offence` / `convicted` set honestly
- Case markers are bound: ಉಡುಪಿಯಲ್ಲಿ, never ಉಡುಪಿ ನಲ್ಲಿ
- Do not invent officials, hospitals, vehicle models, quotes, or causes
- `is_reel: true` only for visual / urgent / shareable stories. Routine civic
  notices stay carousel-only.
- **At most one crime reel.** Crime wins the drama/stakes/shareability test
  every single day, so that test cannot be the thing that limits it. If two
  crime stories both look reel-worthy, one of them is a carousel story and the
  second reel slot goes to civic, weather or culture. D68.

If a tip has no URL and is not own reporting: it stays in `inbox/`. It does
not become an edition.

Anything the tip sheet marked **⚠️ VERIFY** carries a word that appeared in no
text we fetched — an invented figure, an officer nobody named, a helpline a
reader would actually ring. Those get read first, and either found in the
source or cut. (D63)

Write `editions/{DATE}.json`. Then:

```bash
python3 render.py --check editions/{DATE}.json
```

Unknown fields, missing licences, guilt verbs, missing URLs — these fail here.

---

## Stop B — Picture (stock first, honest AI, culture veto)

**Person decides:** every new frame, in chat. Culture veto is yes/no on the
image. Do not redesign the masthead.

**Order of preference:**

1. Own or licensed real photograph
2. Official handout
3. Stock in `assets/stock/` — if it was generated, `nature: "ai"`
4. New AI image, shown in chat, `nature: "ai"`
5. Editorial plate (omit `photo`) — **allowed**. "Zero plate" is vanity.

```json
"photo": {
  "path": "assets/stock/police_dog_squad_investigation.jpg",
  "nature": "ai",
  "credit": "AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ",
  "licence": "own",
  "caption": "ಪೊಲೀಸ್ ಶ್ವಾನ ದಳ (ಎಐ ರಚಿತ ಚಿತ್ರ)"
}
```

**Never** scrape the web. **Never** use Gemini for images. **Never** label an
AI frame `representative`. That word is for a real photograph of a similar
scene.

Culture / legal veto (FAIL and regenerate):

- Wrong geography (Brahmāvara story, Honnavar bridge)
- Distorted sacred tradition (Yakshagana, Hulivesha, Daivaradhane, deities)
- Minor faces, victim faces, gore, blood

Reels need `gallery` length ≥ number of facts. Save new frames to
`assets/daily/{DATE}/`.

---

## Stop C — Package (render, listen, glance evidence)

```bash
mkdir -p assets/daily/{DATE}
python3 render.py editions/{DATE}.json --minimal --out out/{DATE}
# --minimal is carousel + story_card + broadsheet + reel: the four things that
# ship most mornings. Anything else is --only, on request.

python3 scripts/verify_narration.py out/{DATE}    # did the voice say the words
```

**Person does:** listen to one reel on headphones. Open
`out/{DATE}/_review/` frames. Native ear decides the voice, not a score.

**Machine does:** `render.py --check`, speech-locked cuts, WhatsApp text in
every `*_copy.txt`, schedule from files that exist, music licence register,
`run_report.md` and `build.log` for what happened, `PROVENANCE.json` for what
made it.

If `verify_narration.py` lists a NAME among the words it never heard, add it to
`assets/pronunciation.json` and re-render — that fixes every future edition
too, which is the reason to do it there rather than in the script.

Reels open **on the news**. Do not write `ನಮಸ್ಕಾರ, ಕರಾವಳಿ ಸುದ್ದಿ.` into
`narration_script`. Captions disclose synthetic voice
(`Brand.voice_disclosure_kn`).

AI reels are **Instagram only**. `schedule.txt` must not say YouTube Shorts
for them.

WhatsApp forward text is in `*_copy.txt` under `WHATSAPP FORWARD`. That is
the growth product. Broadsheet at 20:00.

If `--bgm` is passed, it must be `status: allowed` in `assets/LICENCES.json`.

---

## Stop D — Gate (review.py writes APPROVAL.md, or nothing ships)

```bash
python3 - <<'PY'
from brand.content import Edition
from brand import review as R
ed = Edition.load('editions/{DATE}.json')
rep = R.review('out/{DATE}', ed).show()
print(len(R.evidence('out/{DATE}')), 'evidence files')
PY
```

`render.py` already runs this at the end of every render — the block above is
for re-checking a folder without re-rendering it.

If `rep.clean` is False: **HELD.** `review_report.json` names the code and the
step that owns the fix (`LAW-01` → rewrite the line, `IMG-03` → picture desk,
`SND-02` → re-run narration). Fix, re-render, re-run. Do not describe the
folder as ready.

When the mechanical checks pass, `APPROVAL.md` is written and it says **not
yet cleared to publish**. That is correct, not a bug. Three things remain that
no check in this repo can establish:

| Seat | The question |
|---|---|
| taste | Does this look like the channel at its best, **at feed size**? |
| culture | Is every ritual, deity, name and community treated with dignity? |
| news | Is this the right lead, and can we stand behind every claim? |

**You may prepare the evidence and recommend. You may not sign.** Embed the
`_review/` frames in chat at feed size, say what you would do and why, and then
the person runs:

```bash
python3 scripts/sign_off.py out/{DATE} --by "<their name>"
```

An assistant's 10/10 is not evidence. A name is, because a name can be asked
about it afterwards. (D62)

Only once `R.is_signed('out/{DATE}')` is true:

> 🟢 ಮುಖ್ಯ ಸಂಪಾದಕರ ಅನುಮೋದನೆ
> `out/{DATE}/` is postable. Instagram carousel + 0–2 reels + WhatsApp
> broadsheet. YouTube only if this folder contains real footage.

Embed carousel slides in chat. Present MASTER_COPY / copy files. **A person
uploads.** Do not connect Instagram or YouTube posting APIs.

Footage packages (Line B/C) use `R.approve_footage(folder)` →
`APPROVAL_FOOTAGE.md`. Same rule: no file, no upload.

---

## `stop` / `close`

Do **not** delete the published record.

```bash
python3 scripts/archive_edition.py {DATE}
```

That script:

1. Copies evergreen generic frames from `assets/daily/{DATE}/` into
   `assets/stock/` and updates `CATALOG.md` (human still chooses which).
2. Copies `editions/{DATE}.json`, `APPROVAL.md`, copy files, schedule, and
   low-res review frames into `archive/{DATE}/`.
3. Deletes `out/{DATE}/` intermediates and leftover `assets/daily/{DATE}/`.
4. Keeps the edition JSON and the stock library.

---

## What this skill does NOT do

- Does not modify `brand/`, `templates/`, or `render.py` on a production day
- Does not invent facts, sources, quotes, or credits
- Does not fill in `verified_by` — that is a person saying they checked
- Does not sign the judgement seats, ever
- Does not auto-post
- Does not send AI-card reels to YouTube
- Does not score itself 10/10
- Does not override `Story.validate()`
- Does not answer a grievance. The 24h / 15-day clocks are statutory; log it
  with `scripts/correction.py new` and tell the person.
