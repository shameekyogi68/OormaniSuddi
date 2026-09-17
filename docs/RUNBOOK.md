# Runbook — a day, and the days that go wrong

The system book explains why everything is the way it is. This is the other
document: what to type, in what order, and what to do when something breaks at
07:40 with a bulletin due.

Nothing here is new policy. If this file and `AGENTS.md` disagree, `AGENTS.md`
is right and this file has a bug.

---

## Every time you sit down

```bash
python3 scripts/health.py
```

One page: did the morning fetch run and did it write leads, is anything past a
statutory clock, is there a second copy of the published record, is a review
overdue, is the code pushed, does the contract still pass. Everything it reads
is inside this repository.

---

## Chat workflow: Start / approve / Stop

For running the day through a conversation with an AI assistant instead of
typing each command by hand. The underlying scripts are exactly the ones
below — this is a second front door onto them, not a second set of rules.
Any AI reading `AGENTS.md` follows this precisely; it is a standing editorial
instruction, not a one-off request to whichever session heard it first.

**You say "Start".** The assistant:

1. Makes sure today has a draft. If `editions/{date}.json` doesn't exist yet,
   it runs `scripts/fetch_daily_news.py` then `scripts/draft_edition.py`
   itself. If one already exists, it uses that — it does not discard an
   edition you may already be partway through.
2. Opens every story's actual `source_url` and reads the real article — not
   just the short tip snippet, so you are reading a real account, not a
   summary of a summary.
3. Shows you each story in plain language in the chat: what happened, where,
   which category, and anything flagged (crime, a minor, a sexual offence) or
   any source link that would not load at all. Nothing is rendered, verified,
   or published at this point — it stops and waits for you.

**You approve** (say "go", "go ahead", "create the content", or similar).
The assistant:

1. Marks verified, under your name, exactly the stories it showed you in
   step 3 — `scripts/verify.py --by "<your name>"`. This is not the
   automation "What is never automated" (below) refers to: nobody's name is
   attached without you, in the conversation, having actually seen the real
   content and told it to proceed. A story it could not actually load for
   you is left out, never verified on your behalf.
2. Renders carousel only, plus a reel if — and only if — the lead story
   earns one. House rule 2026-09-17-02:
   ```bash
   python3 render.py editions/{date}.json \
       --only $(python3 scripts/pick_formats.py editions/{date}.json) \
       --out out/{date}
   ```
   `pick_formats.py` decides the reel mechanically, from the same
   relevance check the Chief Editor gate already trusts (`brand.reach.
   should_be_reel`, D72) — not a guess, and not every day. `story_card` and
   `broadsheet` are never in the default at all: carousel already covers
   that ground, and every extra file is more time spent posting. Never the
   bulletin, thumbnail, or standalone post cards either, unless you
   specifically ask for them.
3. Reports what the Chief Editor gate found (`APPROVAL.md`). Publishing
   still needs your sign-off — `scripts/sign_off.py out/{date} --by
   "<name>"` — taste, culture and news judgement stay yours, D62, same as
   every other day.

**You say "Stop".** The assistant undoes the day so nothing half-finished is
left lying around:

1. Looks at `assets/daily/{date}/`, if anything is there. A generic scene
   (a highway, a hospital exterior, a classroom) belongs in `assets/stock/`
   permanently, so it never has to be generated a second time — it asks you
   which, if any, are worth keeping, and copies those across first.
2. Runs `scripts/discard_edition.py {date} --force-assets`, which deletes
   today's `editions/{date}.json`, the checklist, `out/{date}/`, and
   `assets/daily/{date}/`. It refuses outright, and touches nothing, if the
   day was already signed off — "Stop" is only for a day that never got
   that far; a published day is undone with nothing, it is archived with
   `scripts/archive_edition.py` instead.

---

## A normal day

By the time you sit down, this has already happened — 06:10 and again at
07:00, see "who runs the morning" below:

```bash
python3 scripts/fetch_daily_news.py       # writes inbox/today.json + .md
python3 scripts/draft_edition.py          # writes editions/{date}.json + a checklist
```

`draft_edition.py` copies three or four stories straight from the tip sheet
into `editions/{date}.json` — every `headline`, `deck` and `point` is text
already there, nothing written. It never sets `verified_by`; it cannot (D59,
D76). What is left is:

```bash
open inbox/checklist_2026-09-16.md
```

For each story: open its source URL, confirm it is true, then

```bash
python3 scripts/verify.py editions/2026-09-16.json --story 1 --by "Gautam Paduvari"
# or, once every source checks out:
python3 scripts/verify.py editions/2026-09-16.json --all --by "Gautam Paduvari"
python3 scripts/verify.py editions/2026-09-16.json --status   # what's left
```

Never put your name on `--by` for a story you have not actually opened —
`verified_by` is the one claim in this whole pipeline that a person, not a
script, is making. The checklist also lists anything the fetch found but
`draft_edition.py` declined to auto-draft — a headline that would fail a
legal check, one too long for the render, an English-only tip. Those need
building by hand from `inbox/today.md`, same as before this existed.

```bash
python3 render.py editions/2026-09-16.json --check      # validate, render nothing
python3 render.py editions/2026-09-16.json \
    --only $(python3 scripts/pick_formats.py editions/2026-09-16.json) \
    --out out/2026-09-16
```

Carousel ships every day. `pick_formats.py` adds a reel only when the lead
story earns one (D72) — house rule 2026-09-17-02. `story_card` and
`broadsheet` are never in the default; the bulletin, thumbnail and standalone
post cards are real and they are `--only` on request. Making any of them the
default is how a small desk produces a lot of mediocre content, and spends
more time posting it, instead of one good thing.

Then look at what was made:

```bash
open out/2026-09-16/_review/         # every slide, every reel frame
open out/2026-09-16/run_report.md    # what happened, and where the time went
```

Look at the frames **at feed size** — shrink the window until the carousel
cover is about the size of a thumb. That is the size that decides whether
anybody opens it.

Listen to one reel on headphones. Then, and only then:

```bash
python3 scripts/sign_off.py out/2026-09-16 --by "Gautam Paduvari"
```

`APPROVAL.md` now reads *cleared to publish*. Upload by hand, from
`MASTER_COPY.md`, at the times in `schedule.txt`. Paste the first comment the
moment you post.

### The forwards — this is the circulation department

```bash
cat out/2026-09-16/REACH.md       # which towns this edition speaks to
ls  out/2026-09-16/forward_*.txt  # one per town
```

Send each town's forward to **that town's** groups and broadcast list, not to
everyone. People forward what is theirs; nobody forwards a seven-taluk digest,
because it belongs in no group. This is the highest-leverage thing in the day
and it takes four minutes.

`REACH.md` also flags stories marked as reels that read better as cards, and
tells you when more reels are marked than the day targets. Both are warnings,
not blocks — a big day is allowed to be a big day.

At the end of the day:

```bash
python3 scripts/archive_edition.py 2026-09-16
```

### A short day

Decided in advance, because deciding it at 07:40 is how a thin story gets
promoted to a reel. D69.

The format question is already settled, every day, by house rule
2026-09-17-02: carousel, and `pick_formats.py` adds a reel only when the
lead story earns one (D72). Bulletin, thumbnail, post cards, story_card and
broadsheet are never the default regardless of how the day is going — those
were already `--only` on request (Rule 7), or dropped outright. A short day
is not about dropping formats; it is about how many **stories** belong in the
carousel:

| Fewer stories than usual? | What to do |
|---|---|
| Two or three solid tips | Ship a two- or three-slide carousel. Short is honest. |
| A weak tip padding out a fourth slot | Leave it out. `draft_edition.py` already skips anything that needs a rewrite (D76) — do the same by hand for anything it drafted that still reads thin. |
| Nothing local at all | Publish the weather card alone, or say nothing else. |

The floor is **one carousel.** That is a day. Two usable tips and an honest
carousel is a better day than five stories nobody checked.

What never drops: `verified_by`, the legal guards, the sign-off. A short day is
a reason to publish **less**, never a reason to publish less carefully.

If the fetch half-failed and there are not three stories worth running, publish
the weather card and say nothing else. `ಇಂದು ಯಾವುದೇ ಹೊಸ ಸುದ್ದಿ ಇಲ್ಲ` is a
position, and readers respect it more than filler.

---

## What is coming

```bash
python3 scripts/whats_on.py              # the next 30 days
python3 scripts/whats_on.py --days 90    # plan a quarter
python3 scripts/whats_on.py --reviews    # what is overdue
```

Festivals, the seasons the desk should be reporting inside, and five recurring
reviews. Lunar festivals show the **month** and never the day — confirm each
from a Udupi panchanga when its month opens. The tool will not guess, because a
greeting on the wrong day is worse than no greeting.

```bash
python3 scripts/whats_on.py --scaffold ganesha    # start the greeting JSON
python3 scripts/whats_on.py --reviews --done law_review
```

---

## When it goes wrong

### The gate is red

`review_report.json` names the code and who owns the fix. The common ones:

| Code | What it means | What to do |
|---|---|---|
| `SRC-02` | a story has no `verified_by` | open the source, check it, put your name in the edition JSON. Do not let an assistant fill it in. |
| `LAW-01` | a crime line asserts guilt | rewrite the **headline** and the **reel_line** themselves. A marker in the deck does not reach them. |
| `IMG-01` | an image would show with no disclosure | give it a credit and a nature other than `actual` |
| `IMG-02` | a generated image is wearing the wrong nature | `nature: "ai"`, including reused stock |
| `IMG-03` | a reel has fewer gallery frames than facts | add gallery photos, or drop a fact |
| `SND-01` / `SND-02` | a reel is silent, or narration failed | re-run the reel; check the network and the TTS key |
| `SND-03` | a TTS hazard in the script | ₹, `%`, a decimal, dotted initials, a digital clock time — see D50 |
| `TYPE-01` | a character no house font can set | replace it in the copy; the renderer will not invent a substitute |
| `PKG-01` | the copy names a file that was not rendered | re-render, or fix the copy |
| `PUB-01` | the handle is miscapitalised | `@oormanisuddi`, exactly |
| `PUB-05` | the town name is past the caption fold | rewrite the hook so the town is in the first 125 characters |
| `PUB-06` | a notice is marked as a reel | make it a card — a notice is screenshotted, not watched |
| `PUB-07` | more reels than the day targets | run the best two |
| `PUB-08` | a story names no place | set `location`; nobody forwards what is not theirs |
| `OPS-01` | no Grievance Officer named | `tokens.Brand` — this one blocks everything, correctly |

### "It says cleared but also not cleared"

That is correct and deliberate. `APPROVAL.md` records what a **machine**
established. Taste, cultural dignity and news judgement are signed by a person.
Run `scripts/sign_off.py`. See D62.

### Who runs the morning, and how you know it worked

`com.oormanisuddi.daily` fires at 06:05 and runs `~/run_oormani.sh`, outside
this repository — this project cannot inspect it and does not try to (D71).

`com.oormanisuddi.morning` is this repository's own job, installed with
`bash scripts/install_launchd.sh`. It fires twice — **06:10** (five minutes
after the outside job, so it is never racing it for `inbox/`) and **07:00**
(an independent second attempt, in case the Mac was asleep at 06:10) — and
each run does the whole chain: fetch the tips, then draft the edition
(D76). Firing twice costs nothing because both scripts refuse to redo work
that already exists — `draft_edition.py` never overwrites an
`editions/{date}.json` that is already there, and a repeat fetch is harmless.

Either way, know it ran:

```bash
python3 scripts/health.py        # "morning fetch — ran 2h ago, 32 tips"
                                  # "today's edition — 2/4 verified"
cat logs/last_fetch.json         # the raw record
```

If health says the last fetch success was more than 30 hours ago, something
stopped calling the script. Run it by hand, then look at whatever is
scheduled — `bash scripts/install_launchd.sh --status` for ours,
`launchctl list | grep oormani` for both.

### The morning fetch produced nothing

```bash
cat inbox/.fetch_failed
tail -30 logs/fetch-$(date +%Y-%m-%d).log
bash scripts/install_launchd.sh --status
```

Fewer than three tips means the sources are down or blocking. Do not
manufacture a day out of the two you have — that is the pressure the whole
tip-sheet design exists to resist. Publish less, or publish own reporting.

### A render is stuck, or the Mac is swapping

Only one heavy job runs at a time; a second `render.py` refuses with the PID of
the first. If a job really is dead, the lock goes stale on its own after four
hours, or:

```bash
cat .render.lock     # who holds it
rm .render.lock      # only when you are sure nothing is running
```

Close Chrome. 8 GB is shared between the OS, the compositor, Pillow at 2× and
ffmpeg. If a master render is running, do not start anything else — that is
what turns twelve seconds into twelve minutes.

### The golden test failed

The rendered pixels changed. That is not automatically a bug.

```bash
python3 -m unittest tests.test_golden     # which templates moved
open out/_blessed/                        # LOOK at them
```

If you changed the design on purpose and the new renders are right:

```bash
python3 -m tests.test_golden --bless
```

If you did **not** change the design, check `PROVENANCE.json` in a recent
render against the current environment — a Pillow, raqm or system-font update
moves Kannada rasterisation without anybody touching this repo. That is what
the font hashes are there to tell you.

### A reader says we got something wrong

The clock starts when the message arrives, not when you get to it.

```bash
python3 scripts/correction.py new --about 2026-09-16 \
    --summary "..." --channel whatsapp
python3 scripts/correction.py ack 2026-09-16-01 --by "Gautam Paduvari"
# after fixing it
python3 scripts/correction.py close 2026-09-16-01 --by "Gautam Paduvari" \
    --outcome "..." --published "ತಿದ್ದುಪಡಿ: ..."
python3 scripts/correction.py status     # anything past 24h / 15 days
```

If the substance changed, the correction has to be **visible**. A silent edit
is the thing the policy exists to prevent.

### The voice said a name wrong

```bash
python3 scripts/verify_narration.py out/2026-09-16
```

Words in the "never heard" list are what a listener will lose too. If it is a
name, add it to `assets/pronunciation.json` and re-render — the fix then
applies to every future edition, which is the point.

---

## Weekly

```bash
python3 scripts/whats_on.py --reviews      # anything overdue?
python3 scripts/metrics.py add --date ... --asset reel_01.mp4 --format reel \
    --category civic --place ಬೈಂದೂರು --at 17:30 --seconds 34 \
    --views 412 --reach 380 --local-reach 300 \
    --saves 9 --shares 14 --watch 62
python3 scripts/metrics.py report
python3 scripts/correction.py weekly       # draft the clarifications post
bash scripts/backup.sh --status            # three copies, or fewer?
```

`--local-reach` is the in-district number from Instagram Insights → Audience →
cities. It is the one that decides whether this is a local paper or a page that
happens to be in Kannada, and the report opens on it.

Two minutes of typing what the app already shows you. Every number in
`tokens.Limits` — the slots, the reel window, the hook length — is a
hypothesis until this has enough rows to argue with. The report refuses to
recommend anything below five posts per group and twenty in total, because a
recommendation from four posts is astrology.

## Asking for something to change from now on

```bash
python3 scripts/house_rule.py where "reels should be 30 seconds"
```

It routes you. A **number** goes to `tokens.Limits` with a decision and a test.
A **legal** rule goes to `brand/content.py` with a test. A **place** goes to
`copy.PLACE_TAGS`. Everything else — wording, habits, the order you like things
done in — is a house rule:

```bash
python3 scripts/house_rule.py add "ಹಬ್ಬದ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಸಂಘಟಕರ ಹೆಸರು ಕಡ್ಡಾಯ" \
    --scope picture --why "organisers reshare what credits them" --by "Gautam"

python3 scripts/house_rule.py list
python3 scripts/house_rule.py retire 2026-09-16-01 --why "no longer true"
```

It prints at that stop every day from then on, and `render.py` shows all of
them before it makes anything. Retiring keeps the record — knowing a rule was
dropped and when is worth more than a tidy file.

**It cannot switch a check off.** `add()` refuses `skip the verified_by check`
and anything like it, and tells you the alternative. If a guard is genuinely
wrong, that is an hour: change the code, write the decision saying what breaks
without it, add the test.

## Before changing a number

1. Find its entry in `docs/DECISIONS.md`. If there isn't one, you are about to
   make a decision — write it down.
2. Change it in `brand/tokens.py :: Limits`, not in a document. Documents quote
   the name; they do not restate the value. D56.
3. `python3 -m unittest discover tests`
4. `python3 docs/_build_traceability.py` — every decision needs a test, a
   golden guard, or a written reason.

## Installing things on this Mac

`python3` here is externally managed, so pip refuses a plain install:

```bash
python3 -m pip install --break-system-packages -r requirements.txt
```

The two that are worth having and are not installed yet:

| Package | What it buys | Without it |
|---|---|---|
| `trafilatura` | the intake fetches the **article**, not just the headline | the sheet still works and says `HEADLINE ONLY` — honest, and thinner |
| `mlx-whisper` | `verify_narration.py` can hear whether the voice said the words | narration is checked as text only, which cannot catch a mispronounced name |

Neither is required. Both degrade to a clear message rather than a crash,
which is deliberate: a missing optional dependency must never silently make
the output less honest.

## What is never automated

Uploading. Legal flags. `verified_by`. The sign-off. Answering a complaint.
Those are the five places a person is the product.

The chat workflow above does not change this: an assistant may only write
`verified_by` when the actual person, live in the conversation, has just been
shown the real source content and told it to proceed. That is a person doing
the thing through a different front door — not a schedule, a script, or an AI
deciding on its own that something is true.
