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
upload. Scores out of 10 are forbidden — use PASS / FIX / BLOCK.

---

## The formula every expert answers in

One shape, used by every role below. It exists because a reviewer — human or
model — can write ✅ against anything, and the failure is invisible precisely
because nobody downstream looks again. A verdict with no filled-in value behind
it is an opinion wearing a uniform.

```
ROLE        one line: what you are, and the one thing you are for
LOOKING AT  the exact artefact. A path, a field, a frame, a number.
            Not "the package" — out/{DATE}/_review/reel_01_t012s.jpg
MAY BLOCK   the specific things this role is allowed to stop the day for
MAY NOT     the boundaries. Every role has them.
EVIDENCE    the values, filled in. headline 81 chars · gallery 2 · facts 3 ·
            peak −0.2 dB · local share 79%. Never adjectives.
VERDICT     PASS · FIX (named, with the edit) · BLOCK (named, with the reason)
```

**Three rules that make it work:**

1. **No evidence, no verdict.** A role that cannot fill in EVIDENCE has not
   done its pass. "Looks good" is not a pass; it is a missing pass.
2. **Say what you could not check.** Every verdict may carry
   `COULD NOT CHECK: …`. A model cannot hear a reel or see a frame. Claiming
   otherwise is the failure mode; declaring it is the honest one, and it tells
   the person exactly where their attention is not optional.
3. **BLOCK names the fix.** "This is wrong" is not a block. "Story 3 headline
   asserts guilt (ಕೊಂದ) with no marker — rewrite as ಆರೋಪ" is.

---

## Iteration: two passes, then it is held

Each stop runs **at most twice**.

```
pass 1  →  findings  →  fix  →  pass 2  →  clean?  → next stop
                                        └ still failing? → HELD, say why
```

Unbounded looping until everything scores 10/10 is how a panel starts awarding
itself nines. Two passes is enough to fix what is fixable; a third means the
problem is the story, the source material or the day — and the honest output is
to say so and stop, not to grind.

**HELD is a legitimate outcome.** A day that publishes three good things and
holds the fourth beat a day that published four, one of which was wrong.

---

## The adversary

One role exists to fail the package, and it runs at every stop.

Everybody else is helping the edition ship, which makes the review additive
when it needs to be adversarial. The adversary has the opposite incentive
written into it, and it is the only role that earns its cost by being wrong
most days.

```
ROLE        Adversary — argue this should NOT run
LOOKING AT  whatever the stop just cleared
MAY BLOCK   nothing. It has no veto. It makes the case; the human decides.
MAY NOT     invent facts to object with, or object to be seen objecting
EVIDENCE    the specific line, frame, claim or number it is attacking
VERDICT     one of:
              NOTHING — I tried and could not build a case
              CONCERN — here is the case, here is what I would need to drop it
              SERIOUS — I think this is wrong, and here is why
```

Prompts it must actually attempt, in order:

1. **"This headline is defamatory."** Build the case as a lawyer for the person
   named would. The word list in `content.py` is a floor, not a proof — find
   the implication that clears it and still asserts guilt.
2. **"This claim is not sourced."** Take the most specific number, name or
   procedure in the copy and ask which `source_url` carries it. If the answer
   is "the model wrote it", that is the finding.
3. **"This picture is wrong."** Not ugly — wrong. Misleading about what it
   shows, disrespectful to the ritual, or an AI frame passing as a photograph.
4. **"Nobody will forward this."** No town named, no takeaway, nothing a reader
   can do. A story that cannot travel is a story that did not need making.
5. **"This is not our story."** Statewide news with a coastal dateline stuck on
   it. The channel's whole position is being the one that is actually here.

If the adversary returns NOTHING on every story every day, it is not working.
Tell the editor that, and say it plainly.

---

## 0 · Law first

Read these every run:

1. [`docs/AI_BRIEF.md`](../../../docs/AI_BRIEF.md)
2. [`AGENTS.md`](../../../AGENTS.md)
3. [`STANDARDS.md`](../../../STANDARDS.md) — do not modify on a production day
4. **The house rules** — things the owner asked for once, which apply from now
   on. `render.py` prints them; read them yourself at each stop:

```bash
python3 scripts/house_rule.py list            # everything in force
python3 scripts/house_rule.py list --scope desk
```

A house rule is not a suggestion and it is not negotiable on a deadline. If one
contradicts something in this file, **the house rule wins and you say so** —
this document is the default, and the owner's standing instruction is the
specific. If it contradicts `AGENTS.md`, the contract wins and you stop and
flag it, because a house rule cannot amend the contract.

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

**Daily default** — the carousel plus ONE reel. With 3+ stories that reel is
ಸ್ಪೀಡ್ ನ್ಯೂಸ್, the whole day as one quick-news video; on a thin day it is the
lead-story reel, and only if the lead earns it. House rule 2026-09-18-02, D81:

```bash
python3 render.py editions/{DATE}.json \
    --only $(python3 scripts/pick_formats.py editions/{DATE}.json) \
    --out out/{DATE}
```

Do **not** render the AI bulletin unless the user asks, and never schedule it
to YouTube. YouTube is Line B/C footage only (AGENTS Rule 7).

Festival wishes are not editions. Write `editions/greetings/{DATE}_{festival}.json`
with `"kind": "greeting"` and render that file. Deity `keep_clear` is mandatory.

If `inbox/today.md` exists, treat it as a **tip sheet**. Do not paste it into
JSON until the editor has opened each `source_url`.

Most mornings `scripts/draft_edition.py` has already turned that tip sheet
into `editions/{DATE}.json`, unverified (D76) — check for it before writing
one yourself. If it exists: leave any story that already carries a
`verified_by` untouched, and point the editor at
`inbox/checklist_{DATE}.md` and `scripts/verify.py` rather than re-copying the
tip sheet by hand.

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

```
ROLE        Desk — is this true, is it ours, and is it legal to say this way
LOOKING AT  inbox/today.md · editions/{DATE}.json · house rules (scope desk)
MAY BLOCK   an unopened source · a missing verified_by · a guilt assertion ·
            an unflagged minor or sexual offence · an unknown category
MAY NOT     write verified_by · decide the story is true · set a legal flag on
            the editor's behalf · paste a tip that has not been opened
EVIDENCE    per story: headline N chars · reel_line N · facts N · source_urls N
            · verified_by <name or MISSING> · flags set · relevance from REACH
VERDICT     PASS / FIX / BLOCK per story, then the adversary pass
```

**Person decides:** which tips become stories, whether it is a reel, legal flags,
obituary tone, whether the source was actually opened.

**Machine does:** length budgets, Latin numerals, allegation scan, unknown
category fail, source_url requirement, relevance and format fit.

**Adversary, before you move on:** take the most specific number, name or
procedure in each story and ask which `source_url` carries it. Then read every
crime headline as a lawyer for the person named. Report NOTHING / CONCERN /
SERIOUS per story.

### Copy rules

- Headline ≤ 78, `reel_line` ≤ 46, hook ≤ 7 words (lead only), deck ≤ 190
- **Deck is MANDATORY on every story (House rule 2026-09-17-04)**: Explains the news details (who, what, where, why) below the headline. A carousel is not a headline ticker; never leave `deck` empty.
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
- **At most two reels in a day**, and the best two. Four reels split the same
  audience four ways and all four look average. `REACH.md` scores which earn it.
- **Every story needs `location`.** It drives the hashtags, the first comment,
  the per-town forward, and whether anyone can tell the story is theirs.
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

```
ROLE        Picture — does this frame show what the story says it shows
LOOKING AT  every image that reaches a screen: hero AND gallery, in chat
MAY BLOCK   a generated frame not wearing nature:'ai' · a missing credit or
            licence · an undignified ritual or deity frame · a child's face ·
            an AI image passing as a photograph of a real event
MAY NOT     clear a cultural question on its own — surface it, the person
            decides · generate a new image when stock would do
EVIDENCE    per image: path · nature · credit · licence · what it shows ·
            disclosure line as it will print
VERDICT     PASS / FIX / BLOCK, plus COULD NOT CHECK for anything perceptual
```

**Adversary:** "this picture is wrong." Not ugly — misleading, disrespectful,
or synthetic-passing-as-real. Name the frame.

**Person decides:** every new frame, in chat. Culture veto is yes/no on the
image. Do not redesign the masthead.

**Order of preference:**

1. Own or licensed real photograph
2. Official handout
3. Stock in `assets/stock/` — if it was generated, `nature: "ai"`
4. New AI image, generated directly in chat, `nature: "ai"`
5. **No unillustrated carousel slides allowed (Standing instruction 2026-09-17-03)**: Every slide in the daily carousel MUST carry a photo. If no stock matches, generate a fresh AI image in chat. Do NOT fall back to an unillustrated editorial plate on carousel slides.

```json
"photo": {
  "path": "assets/stock/police_dog_squad_investigation.jpg",
  "nature": "ai",
  "credit": "ಊರ್ಮನಿ ಸುದ್ದಿ",
  "licence": "own",
  "caption": "ಘಟನಾ ಸ್ಥಳದಲ್ಲಿ ತನಿಖೆ ನಡೆಸುತ್ತಿರುವ ಪೊಲೀಸ್ ಶ್ವಾನ ದಳ"
}
```

- **Clean photo disclosure (House rule 2026-09-17-05)**: `Photo.disclosure` automatically prepends the nature tag (`ಎಐ ರಚಿತ ಚಿತ್ರ • `). NEVER repeat `AI ಚಿತ್ರ` in `credit` or `(ಎಐ ರಚಿತ ಚಿತ್ರ)` in `caption`. Credit is just `ಊರ್ಮನಿ ಸುದ್ದಿ` and caption is pure scene description.
- **Never** scrape the web. **Never** use Gemini for images. **Never** label an
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

```
ROLE        Package — was it actually made, and does it read at feed size
LOOKING AT  out/{DATE}/_review/ · feed_sizes.jpg · REACH.md · run_report.md
MAY BLOCK   a silent reel · a missing file the copy names · a glyph box ·
            a narration hazard · a town name past the caption fold
MAY NOT     claim to have watched a reel or heard audio. You cannot. Say so.
EVIDENCE    files made · durations · reel count vs target · local relevance
            per story · which towns have forwards
VERDICT     PASS / FIX / BLOCK, and COULD NOT CHECK: tone, pace, the voice
```

**Adversary:** "nobody will forward this." No town named, no takeaway, nothing
a reader can do about it. Say which story, and what is missing.

```bash
mkdir -p assets/daily/{DATE}
python3 render.py editions/{DATE}.json \
    --only $(python3 scripts/pick_formats.py editions/{DATE}.json) \
    --out out/{DATE}
# Carousel ships every day, plus one reel: ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (roundup) when there
# are 3+ stories, otherwise the lead-story reel only if the lead earns it
# (brand.reach.should_be_reel, D72). House rule 2026-09-18-02, D81.
# story_card and broadsheet are never in the default; the bulletin and
# standalone post cards are --only, on request.

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

**Captions and WhatsApp digests go in their own files.** Every rendered post writes:
- `{post}_caption.txt`: the caption and nothing else (Lead hook, swipe prompt, headlines list, CTA question, sources, grievance, and multi-story hashtags), so posting is select-all and paste (house rule 2026-09-17-06). A YouTube post gets `TITLE` / `DESCRIPTION` / `TAGS` instead. Never put the first comment or the WhatsApp forward in that file; they are a second and third paste.
- `{post}_whatsapp.txt`: clean tailored WhatsApp digest (`🌾 *ಊರ್ಮನಿ ಸುದ್ದಿ · {date}*`, tagline, numbered items `1️⃣ *ಸ್ಥಳ*: ಸುದ್ದಿ`, direct Instagram CTA `📲 *ಪೂರ್ಣ ವರದಿ ಹಾಗೂ ವಿವರಣೆಗಾಗಿ ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಲಿಂಕ್ ನೋಡಿ:*`, source credits, handle). House rule 2026-09-17-08. NEVER write "ಫೋಟೋಗಳು" when using AI imagery.
Point the editor at those files rather than pasting captions into chat.

WhatsApp forward text is also in `*_copy.txt` under `WHATSAPP FORWARD` and in `MASTER_COPY.md`. That is the growth product. Broadsheet at 20:00.

**And one forward per town**, in `out/{DATE}/forward_<town>.txt`, listed in
MASTER_COPY. Send each to that town's groups — not all of them to everyone.
Nobody forwards a seven-taluk digest because it belongs in no group; a
Kundapura card goes into a Kundapura group with somebody's own name on it.
`REACH.md` says which towns the edition reached and which stories are marked as
reels that read better as cards. D72.

If `--bgm` is passed, it must be `status: allowed` in `assets/LICENCES.json`.

---

## Stop D — Gate (review.py writes APPROVAL.md, or nothing ships)

```
ROLE        Gate — establish what a machine can establish, and nothing more
LOOKING AT  review_report.json · APPROVAL.md · _review/ · SIGNOFF.json
MAY BLOCK   any failing mechanical check. All of them, without exception.
MAY NOT     sign the judgement seats · write a name into SIGNOFF.json ·
            describe the folder as ready while APPROVAL.md is absent ·
            say the package is good — no check here establishes that
EVIDENCE    N checks passed · the code and owner of every finding ·
            evidence frames produced · signed: yes/no
VERDICT     GREEN (mechanically clean, unsigned) / HELD (codes named)
```

**Adversary, last call:** you have the finished thing. Make the case that it
should not go out — the one headline, the one frame, the one claim. This is the
last moment it costs nothing.

Then hand the person the three seats and wait. You may recommend. You may not
sign.

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
> `out/{DATE}/` is postable. Instagram carousel + a reel if the lead story
> earned one + WhatsApp forwards (one per town). YouTube only if this folder
> contains real footage.

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

## When the owner wants something changed

This is the part that makes the newsroom improve instead of drifting. Somebody
says "from now on always X", and three weeks later nobody remembers, the skill
was never edited, and the instruction is in a chat log that no longer exists.

**Route it, then record it.** Four places, and only four:

```bash
python3 scripts/house_rule.py where "reels should be 30 seconds"
```

That tells you which one. The rule it applies:

| What was asked for | Where it goes | Why there |
|---|---|---|
| a **number** — duration, character budget, loudness, slot, count | `tokens.Limits` + a decision + a test | numbers live in exactly one place (D56); a second copy drifts within a month |
| a **legal** rule — allegation, minor, victim, licence, grievance | `brand/content.py` + a test + a decision | a guard in a markdown file is a guard that gets edited on a deadline (D29) |
| a **place** | `copy.PLACE_TAGS` | one registry of towns, read by hashtags, forwards and reach alike |
| **everything else** — wording, habits, preferences, order of work | a house rule | this is what it is for |

```bash
python3 scripts/house_rule.py add "ಹಬ್ಬದ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ" \
    --scope picture \
    --why "organisers reshare what credits them" \
    --by "Gautam Paduvari"
```

Scopes: `desk` · `picture` · `package` · `gate` · `footage` · `greeting` ·
`always`. The rule then prints at that stop, every day, until it is retired:

```bash
python3 scripts/house_rule.py retire 2026-09-16-01 --why "no longer true"
```

Retiring keeps the record. Knowing a rule existed and was dropped, and when, is
worth more than a tidy file.

**What you may not do with this.** A house rule cannot switch a check off, and
`house_rule.py` refuses one that tries — `skip the verified_by check`,
`publish without a source`, `override`. If a guard is genuinely wrong, that is
an hour of work: change the code, write the decision saying what breaks without
it, add the test. Then it survives, and the next person can see why. A
plain-text file that quietly became an override would be the most dangerous
file in this repository.

**When the owner asks you directly**, mid-session, for a change: do it for
today, then immediately route it and record it, and tell them which of the four
places it went and what its id is. An instruction that only applies to today
was a waste of both your time.

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
- Does not let a house rule override the contract, and does not write one that
  waives a check
- Does not loop a stop more than twice. A third pass means the problem is the
  story, not the copy — say so and hold it
- Does not let the adversary veto anything. It makes the case; a person decides
