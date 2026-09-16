# Brief for an AI tool

**You are being given news copy and asked to produce ಊರ್ಮನಿ ಸುದ್ದಿ designs.
Read this file completely before you do anything else.**

You do **not** design anything. The design already exists and is finished. Your
job is to turn raw copy into correct JSON and hand it to the renderer. If you
write drawing code, choose colours, or pick font sizes, you have gone wrong —
the output will not match the channel and the work will have to be redone.

---

## 1 · The only workflow

```
raw news copy  →  edition JSON  →  python3 render.py <file>  →  finished files
```

That is the whole thing. Three commands you will need:

```bash
python3 render.py --describe          # every template, and the rule for choosing it
python3 render.py --schema story      # the exact input contract
python3 render.py --check my.json     # validate without rendering
python3 render.py my.json             # render the full package
```

`--describe --json` gives the same information machine-readable, and
`templates/registry.json` is the same table on disk. Prefer reading those over
guessing.

---

## 2 · What you write

One JSON file per day's bulletin, in `editions/`. Lead story first — the
thumbnail and the 9:16 story card are both made from it.

```json
{
  "date": "2026-08-25T09:40:00+05:30",
  "edition_no": 112,
  "strapline": "ಕರಾವಳಿ ಬುಲೆಟಿನ್",
  "stories": [
    {
      "headline": "ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್: ಇಂದು ಮತ್ತು ನಾಳೆ ಭಾರಿ ಮಳೆ, ಬಿರುಗಾಳಿ ಸಾಧ್ಯತೆ",
      "category": "weather",
      "deck": "ಉಡುಪಿ ಮತ್ತು ದಕ್ಷಿಣ ಕನ್ನಡ ಜಿಲ್ಲೆಗಳಿಗೆ ಹವಾಮಾನ ಇಲಾಖೆಯಿಂದ ಎಚ್ಚರಿಕೆ ಪ್ರಕಟ.",
      "points": [
        "ಗಂಟೆಗೆ 40-50 ಕಿ.ಮೀ ವೇಗದ ಗಾಳಿ ಬೀಸುವ ಸಾಧ್ಯತೆ ಇದೆ ಎಂದು ಇಲಾಖೆ ತಿಳಿಸಿದೆ.",
        "ಮೀನುಗಾರರು ಆಗಸ್ಟ್ 27ರವರೆಗೆ ಸಮುದ್ರಕ್ಕೆ ಇಳಿಯದಂತೆ ಸೂಚನೆ ನೀಡಲಾಗಿದೆ."
      ],
      "takeaway": "ತುರ್ತು ಸಹಾಯಕ್ಕೆ ಜಿಲ್ಲಾ ವಿಪತ್ತು ನಿರ್ವಹಣಾ ಕೊಠಡಿ 1077 ಸಂಪರ್ಕಿಸಿ.",
      "photo": {
        "path": "assets/udupi_coastal_storm.jpg",
        "nature": "representative",
        "credit": "ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ",
        "licence": "own",
        "focal": [0.5, 0.5]
      },
      "location": "ಉಡುಪಿ ಜಿಲ್ಲೆ",
      "dateline": "ಜಿಲ್ಲಾ ವರದಿ",
      "sources": ["ಭಾರತೀಯ ಹವಾಮಾನ ಇಲಾಖೆ", "ಉಡುಪಿ ಜಿಲ್ಲಾಡಳಿತ"],
      "source_urls": ["https://mausam.imd.gov.in/", "https://udupi.nic.in/"],
      "verified_by": "Gautam Paduvari",
      "verified_at": "2026-08-25T07:50:00+05:30",
      "status": "official",
      "published_at": "2026-08-25T08:40:00+05:30"
    }
  ]
}
```

A complete, valid, four-story example is in `editions/2026-08-25.json`. Copy its
shape. The authoritative field list is `schemas/story.schema.json` — every
property there carries a description explaining what it is for.

---

## 3 · Choosing a template

You usually do **not** need to choose. Omit `template` and the renderer picks:

| Condition | Template |
|---|---|
| the story has a `quote` | `quote_card` |
| it has `numbers` and no photo | `stat_card` |
| it has a `photo` that exists on disk | `report_card` |
| otherwise | `text_card` |

Set `"template": "..."` only when you have a reason the rule above cannot know.

**Give every story a `reel_line`.** It is a short video headline, about 45
characters. Your print headline is probably 70–80, and at Kannada reading speed
on video that needs ~11 seconds of screen time by itself. Without a `reel_line`
the reel still renders — it just runs long, and may drop your last story.

```json
"headline":  "ಬೈಂದೂರು ಮೂಕಾಂಬಿಕಾ ಏರ್‌ಪೋರ್ಟ್ ಯೋಜನೆ: ಪ್ರಸ್ತಾವನೆ ಹಂತದಲ್ಲೇ ಬಾಕಿ, ಆರಂಭವಾಗದ ಕಾಮಗಾರಿ",
"reel_line": "ಮೂಕಾಂಬಿಕಾ ಏರ್‌ಪೋರ್ಟ್: ಕಾಮಗಾರಿ ಆರಂಭವಾಗಿಲ್ಲ"
```

**And give every fact a `reel_points` short form.** Same reason, one level
down. A reel's fact card is glanced at while the anchor is already speaking
that fact — measured, the voice delivers Kannada at roughly twice the speed a
viewer reads unfamiliar text on a moving frame. A 110-character point on a
card is therefore copy nobody finishes. `reel_points` is index-matched to
`points`; the voice still reads the FULL point either way, so nothing is lost
from the reel, only from the frame.

```json
"points": [
  "ವಾರಾಹಿ ನೀರೆತ್ತುವ ಜಲವಿದ್ಯುತ್ ಶೇಖರಣಾ ಯೋಜನೆಯ ಸಮಗ್ರ ಯೋಜನಾ ವರದಿ (DPR) ಸಿದ್ಧತೆಯ ಅಂತಿಮ ಹಂತದಲ್ಲಿದೆ."
],
"reel_points": [
  "ವಾರಾಹಿ ಯೋಜನೆಯ DPR ಅಂತಿಮ ಹಂತದಲ್ಲಿ"
]
```

Leave an entry blank, or omit the list, to fall back to the full point.

**Every image is disclosed on the card that shows it**, not just the first
one. A reel's fact cards come from `gallery` and its end card from `photo`, so
every one of them carries its own `nature` label and `credit`. An
AI-generated picture must be `"nature": "ai"` — it will be labelled
<span>ಎಐ ರಚಿತ ಚಿತ್ರ</span> on every frame it appears in, and in the caption.

**Every photograph needs a `licence`.** One of `own`, `licensed`, `cc`,
`public-domain`, `handout`, `fair-dealing`. Anything other than `own` also needs
a `source_url`. Do not write `credit: "ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ"` on a picture the
channel did not take — that asserts ownership.

**Crime stories may not assert guilt.** Write the allegation, not the verdict:
<span>ಆರೋಪ</span> / <span>ಆರೋಪಿ</span> / <span>ಶಂಕಿತ</span> / <span>ಪ್ರಕರಣ ದಾಖಲು</span>.
Plain past tense ("the son who killed…") is refused unless you set
`"convicted": true`, which means a court actually convicted. Set
`"involves_minor": true` or `"sexual_offence": true` where they apply and the
system blocks identifying detail for you.

> **The `headline` and the `reel_line` must each carry their own marker.**
> They are checked on their own, not as part of the whole story, because that
> is how they are read — a thumbnail, a WhatsApp forward, a screenshot, a reel
> scene, with none of the rest of the copy attached. Putting <span>ಆರೋಪಿ</span>
> in the `deck` does **not** make a guilt-asserting headline acceptable.
>
> ```
> ✗ "headline": "ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ"      ← refused, even with ಆರೋಪಿ in the deck
> ✓ "headline": "ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ"
> ```

**A story with no photograph is fine.** Omit `photo` entirely and the card
draws an editorial plate — a branded graphic, credited ಗ್ರಾಫಿಕ್ಸ್. Do NOT
attach a loosely related stock image to avoid an empty-looking post; the plate
is the designed answer to that, and it is honest.

**`hook` goes on the FIRST story.** The YouTube thumbnail and the 9:16 story
card are both made from the lead, so a `hook` on any other story is ignored and
the thumbnail falls back to the full headline — which is too long to read at
feed size.

**The one judgement you must make: is there an honest photograph?**

- If a real picture of the actual scene exists → `nature: "actual"`, and you
  **must** also write a `caption` saying what it shows.
- If the picture is a real photograph of a similar scene → `nature:
  "representative"` or `"file"`. It will be labelled ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ / ಸಂಗ್ರಹ
  ಚಿತ್ರ. If the picture was generated — including reused stock — `nature`
  is `"ai"`. A credit that says AI cannot wear `representative`.
- **If no honest picture exists, omit `photo` entirely.** The story then gets
  `text_card`, which is a good-looking card built from the brand's own sunset
  horizon. Never attach a decorative stock photo to fill the space. Illustrating
  a Brahmāvara story with a highway bridge signposted HONNAVAR is the specific
  failure this system was built to prevent.

### Festival wishes are not stories

A greeting — Gauri-Ganesha, Deepavali, Ugadi, Rajyotsava, Eid, Christmas — is
**not** a story. Never send it through `report_card` or an edition: it has no
source, no status and no headline, and news design makes it read as a report
about the festival. Write a separate file in `editions/greetings/` with
`"kind": "greeting"`:

```json
{
  "kind": "greeting",
  "slug": "2026-09-13_gauri_ganesha",
  "occasion": "ಗೌರಿ ಗಣೇಶ ಹಬ್ಬದ",
  "blessing": "ವಿಘ್ನ ನಿವಾರಕ ಗಣಪತಿ ಹಾಗೂ ತಾಯಿ ಗೌರಿಯ ಕೃಪೆ ಸದಾ ನಿಮ್ಮ ಮೇಲಿರಲಿ",
  "theme": "sacred",
  "photo": {"path": "...", "nature": "ai", "credit": "AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ", "licence": "own"},
  "keep_clear": [0.32, 0.66]
}
```

`python3 render.py editions/greetings/<file>.json` writes `wish_9x16.jpg`,
`wish_4x5.jpg`, `wish_1x1.jpg` and the caption to `out/greetings/<slug>/`.

- **`keep_clear` is required with a photo.** It is the band of the image, as
  `[top, bottom]` fractions of its height, holding the deity or subject. No type
  will ever be set inside it. Look at the picture and measure it; do not guess.
- **Themes:** `sacred` (Ganesha, Navaratri, Dasara), `lights` (Deepavali),
  `harvest` (Ugadi, Sankranti, Bisu), `rajyotsava`, `national`, `serene` (Eid,
  Christmas, Buddha Purnima).
- **Keep it short.** occasion ≤ 30, wish ≤ 26, blessing ≤ 96 characters; about 60
  reads best.
- No photograph is a valid choice — the poster draws a gold mandala instead.
  Never use a stock image just to fill the frame.

---

## 3b · Writing so it travels

A coastal story is forwarded by somebody who recognises their own town in it.
Three rules follow from that, and the gate checks all three.

**The town name goes in the first 125 characters.** Instagram truncates the
caption behind "… more" at roughly there. `hook()` will prefix the place for
you when it fits — but if your headline buries the town behind a clause, it
lands past the fold and the taluk it was written for never sees it.

**Set `location` on every story.** It drives the hashtags, the first comment,
the per-town WhatsApp forward, and whether the story can be placed at all. A
story with no location is a story nobody can tell is theirs.

**Write the takeaway.** A helpline, a last date, a road closed, who to call.
Copy that tells a reader what to DO is the strongest forward predictor there
is, and it is the difference between a story people read and a story people
send to their family.

`follows_up` takes the date of an earlier edition when this genuinely continues
it — a road that was closed and has reopened. The caption then says so, which
tells a reader this channel follows things up. Use it only when there is new
information: a follow-up with no new fact is padding, and padding teaches an
audience to stop reading.

---

## 4 · Hard limits

Exceed these and preflight warns; exceed them badly and it fails.

| Field | Budget | What happens past it |
|---|---|---|
| `headline` | ~78 chars (4:5), ~34 (thumbnail) | set smaller; past 1.45× it fails |
| `deck` | ~190 chars | warns; stops reading as a standfirst |
| `points` | 3 items, ~150 chars each | extras are dropped from the bottom |
| `numbers` | 3 pairs | 4 crowds |
| `hook` | ~7 words | warns — the thumbnail is read at 210 px wide |
| `stories` | 3–4 per edition | carousel carries all stories; reel engine produces individual short reels (reel_01, reel_02...) ONLY for 10/10 reel-worthy stories (`is_reel: true`) |

**`is_reel`: set `false` on routine, dry, or non-visual news.** Carousel and Posts cover every story in the edition so the audience has full news coverage. But vertical video algorithms severely punish low completion rates: only stories that score 10/10 in visual drama, public urgency, high stakes, or viral regional talkability should become reels (`is_reel: true`). Routine administrative circulars, holiday notices, tenders, or date extensions should set `"is_reel": false` to protect channel watch time and distribution.

**Numerals: Latin (25, 1077, 40-50), never Kannada (೨೫).** This matches Kannada
print and broadcast practice. Mixing the two systems inside one card is a
**preflight failure**, not a warning.

Write Kannada that a person actually says out loud. The templates set it large;
padded officialese looks worse at 78 px than it does in a paragraph.

---

## 5 · What will be rejected, and why

`Story.validate()` refuses to render rather than produce a dishonest card.
There is no flag to switch any of this off, and you must not add one.

| Rejection | Fix |
|---|---|
| photo with no `credit` | name the photographer, the agency, or `"ಊರ್ಮನಿ ಸುದ್ದಿ ವರದಿಗಾರರಿಂದ"` |
| `nature: "actual"` with no `caption` | say what the picture shows, or change nature |
| empty `sources` | name who told you; own reporting counts — `["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"]` |
| sourced story with no `source_urls` | add an http URL the editor can reopen, or mark own reporting |
| no `verified_by` (blocks APPROVAL.md, not the render) | a PERSON opens the source, checks the facts, and puts their name here. You cannot fill this in on their behalf — see §6 |
| no `location` (warns) | set it. Nobody forwards a story they cannot tell is about their town, and the reach layer cannot place it |
| a notice marked `is_reel` (warns) | civic, health and education read better as cards. A notice gets screenshotted; a video about one gets scrolled |
| more than 2 stories marked `is_reel` (warns) | on an account this size, four reels split the same audience four ways and all four look average |
| unknown `category` | pick from the registry; `governance` is not silent explainer |
| AI credit with `nature: "representative"` | generated frames, including stock, use `nature: "ai"` |
| obituary with one source | two sources, or own reporting |
| `live_url` that is not a URL | only a real stream earns ನೇರ ಪ್ರಸಾರ |
| unknown field name | you typo'd; the error lists the valid fields |

Two things are computed and cannot be asserted:

- **`category: "breaking"` decays.** It is checked against `published_at` and
  silently demoted after 12 hours. Do not try to force it.
- **`status` is printed as it stands** — ದೃಢಪಟ್ಟ ವರದಿ / ಅಧಿಕೃತ ಪ್ರಕಟಣೆ /
  ಬೆಳವಣಿಗೆಯಲ್ಲಿದೆ / ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ. If a story is not confirmed, say
  `"developing"` or `"unconfirmed"`. A card that admits it is still being
  checked is worth more than one that pretends otherwise.

---

## 6 · Things you must not do

1. **Do not write rendering code.** No Pillow, no canvas, no HTML-to-image.
   Eleven templates already exist (`python3 render.py --describe`). If none
   fits, say so and stop — do not improvise one.
2. **Do not hard-code a colour, a font size, or a margin.** Every such value
   lives in `brand/tokens.py`. If you think one needs to change, that is a
   design decision for a human, and `docs/DECISIONS.md` explains why it is what
   it is.
3. **Do not edit files in `brand/` or `templates/`** to make a particular story
   fit. Shorten the copy instead — that is what a sub-editor would do.
4. **Do not invent facts, sources, quotes, or credits** to satisfy a required
   field. If you do not know the source, the correct output is a question to the
   human, not a plausible-looking string.
5. **Do not suppress a provenance label.** ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ appearing on a card
   is the system working, not a bug.
6. **Do not fill in `verified_by` yourself, ever.** It is the name of the
   person who opened the sources and checked the facts. Putting a name there —
   yours, the channel's, or the editor's — because the gate is asking for one
   converts the single check a machine cannot perform into a string a machine
   wrote. If it is missing, the correct output is to say so and stop. D59.
7. **Do not write a sign-off.** `SIGNOFF.json` and the judgement block in
   `APPROVAL.md` record a human verdict on taste, cultural dignity and news
   judgement. You may prepare the evidence — the frames, the numbers, the
   options — and you may recommend. You may not sign. D62.
8. **Do not upload anything.** A person posts every item. That is the product,
   not an inefficiency.

---

## 7 · Checking your work

```bash
python3 render.py --check edition.json     # preflight, renders nothing
python3 render.py edition.json             # render; audits output automatically
python3 -m unittest tests.test_contract     # the honesty rules (instant)
python3 -m unittest discover tests          # + the design itself (~2 min)
```

`--check` reports three levels: `✗` failures block the render, `!` warnings are
a sub-editor's call, silence means clean.

After rendering, every file is inspected for wrong dimensions, oversize,
crushed blacks, blown highlights, and a missing focal point. Read that audit —
a clean preflight with a dirty audit usually means a bad `focal` point.

**Reproducibility.** Identical JSON plus the same `--at` produces byte-identical
files. If you need that (regression testing, comparing two versions of copy),
pin the clock:

```bash
python3 render.py edition.json --at 2026-08-25T09:40:00+05:30
```

Without `--at`, output still varies only in the ways it should: the dateline and
whether a story still counts as breaking.

---

## 8 · Where to look next

| You want | Read |
|---|---|
| the full design standard | [`../STANDARDS.md`](../STANDARDS.md) |
| what each template does, field by field | [`TEMPLATES.md`](TEMPLATES.md) |
| **why** a rule exists, before changing it | [`DECISIONS.md`](DECISIONS.md) |
| the machine-readable template table | `templates/registry.json` |
| the machine-readable input contract | `schemas/story.schema.json` |
| a complete valid edition | `editions/2026-08-25.json` |
| the Python API instead of JSON | `examples/make_examples.py` |
