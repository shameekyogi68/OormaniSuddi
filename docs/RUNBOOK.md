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

## A normal day

```bash
# 06:05 runs automatically — see "who runs the morning" below.
# To run it by hand at any time:
python3 scripts/fetch_daily_news.py

# Read the sheet. It is TIPS. Open the source URLs.
open inbox/today.md
```

Anything marked **⚠️ VERIFY** carries a word that was in no text we fetched —
an invented figure, an officer who was never named, a helpline nobody gave us.
Read those first. Either find the word in the source or cut it.

Then write the edition. Three or four stories is a day; eleven is a week's
worth of mediocre. Every story needs:

- `sources`, and `source_urls` unless it is own reporting
- `verified_by` — **your name**, once you have opened the source yourself

```bash
python3 render.py editions/2026-09-16.json --check      # validate, render nothing
python3 render.py editions/2026-09-16.json --minimal    # carousel, story, broadsheet, reel
```

`--minimal` is the four things that ship most mornings. The bulletin, the
thumbnail and the standalone post cards are real and they are `--only` on
request; making them the default is how a small desk produces a lot of
mediocre content instead of four good things.

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

`--minimal` **is** the normal day: carousel, story card, broadsheet, reel.
Below that, things drop in this order:

| Drop | Why it goes first |
|---|---|
| bulletin | off by default and not going to YouTube anyway (Rule 7) |
| post cards | the carousel already carries every story |
| yt_thumbnail | it exists for a video that may not be made |
| reels, worst story first | one good reel beats three adequate ones |
| story card | it points at the carousel; the carousel survives without it |

The floor is **one carousel and one broadsheet forward.** That is a day. Two
usable tips and an honest carousel is a better day than five stories nobody
checked.

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

`com.oormanisuddi.daily` fires at 06:05 and runs `~/run_oormani.sh`, which
lives outside this repository. This project deliberately does **not** install a
second job at the same minute — two of them writing `inbox/` means the loser is
overwritten in silence. See D71.

That costs nothing, because the improvements live in the script rather than in
the job: whatever calls `scripts/fetch_daily_news.py` gets article-body
extraction, the groundedness pass and the current text model.

What you need instead is to know it ran:

```bash
python3 scripts/health.py        # "morning fetch — ran 2h ago, 32 tips"
cat logs/last_fetch.json         # the raw record
```

If health says the last success was more than 30 hours ago, something stopped
calling the script. Run it by hand, then look at whatever is scheduled.

If you ever retire the outside job, ours is ready:

```bash
bash scripts/install_launchd.sh  # refuses while another job holds 06:05
```

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
