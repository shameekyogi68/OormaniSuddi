# Brief for an AI tool

**You are being handed news the editor pasted, and asked to turn it into
ಊರ್ಮನಿ ಸುದ್ದಿ posts. Read this file completely before you do anything else.**

You do **not** design anything. The three formats exist and are finished
(DECISIONS D92). Your job is to turn pasted copy into correct JSON and hand it
to the renderer. If you write drawing code, choose colours or pick font sizes,
you have gone wrong.

---

## 1 · The only workflow

```
pasted news  →  kept source  →  edition JSON  →  checks  →  editor confirms  →  render
```

```bash
python3 scripts/intake.py source --url URL --outlet NAME < paste.txt   # keep an article's text
python3 scripts/intake.py source < paste.txt       # own reporting / press release, no link
python3 scripts/intake.py seen editions/DATE.json  # anything already published?
python3 scripts/fact_check.py editions/DATE.json   # every figure vs the kept source, offline
python3 render.py --describe                       # the formats and their rules
python3 render.py --schema story                   # the exact input contract
python3 render.py --check editions/DATE.json       # validate, render nothing
python3 render.py editions/DATE.json               # render every segment present
```

The pasted text **is** the source. Nothing is fetched or scraped. What the
paste does not say, the story does not say — if you need more, ask the editor.

In a chat, the order of work, what to show the editor and when to wait is
[`RUNBOOK.md`](RUNBOOK.md) "Chat workflow". Follow it.

---

## 2 · What you write

One JSON file per day, `editions/<date>.json`, `schema_version` 4. If it
already exists, extend it: never touch a story that already has `verified_by`.

A minimal valid edition — one ಮುಖ್ಯ ಸುದ್ದಿ with our reporter's photograph, two
stories for the ಸುದ್ದಿ ಸಾರ (content is illustrative):

```json
{
  "schema_version": 4,
  "date": "2026-09-28T09:00:00+05:30",
  "edition_no": 140,
  "stories": [
    {
      "segment": "mukhya",
      "photo_plan": "real",
      "headline": "ಕುಂದಾಪುರ: ಪಂಚಗಂಗಾವಳಿ ಸೇತುವೆ ಸಂಚಾರ ಇಂದಿನಿಂದ ಬಂದ್",
      "category": "civic",
      "deck": "ದುರಸ್ತಿ ಕಾಮಗಾರಿಗಾಗಿ ಸೇತುವೆಯಲ್ಲಿ ವಾಹನ ಸಂಚಾರ ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ.",
      "points": [
        "ಸಂಚಾರ ನಿರ್ಬಂಧ 10 ದಿನ ಜಾರಿಯಲ್ಲಿರಲಿದೆ.",
        "ವಾಹನಗಳು ಬದಲಿ ಮಾರ್ಗದಲ್ಲಿ ಸಂಚರಿಸಬೇಕು."
      ],
      "takeaway": "ಬದಲಿ ಮಾರ್ಗದ ವಿವರಕ್ಕೆ ಸ್ಥಳೀಯ ಪೊಲೀಸ್ ಠಾಣೆ ಸಂಪರ್ಕಿಸಿ.",
      "photo": {
        "path": "assets/daily/2026-09-28/kundapura_bridge.jpg",
        "nature": "actual",
        "credit": "ಊರ್ಮನಿ ಸುದ್ದಿ ವರದಿಗಾರರಿಂದ",
        "licence": "own",
        "caption": "ದುರಸ್ತಿ ಕಾಮಗಾರಿ ಆರಂಭವಾದ ಸೇತುವೆ, ಭಾನುವಾರ ಬೆಳಿಗ್ಗೆ"
      },
      "location": "ಕುಂದಾಪುರ",
      "sources": ["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"],
      "source_urls": [],
      "status": "confirmed",
      "published_at": "2026-09-28T08:45:00+05:30"
    },
    {
      "segment": "saara",
      "photo_plan": "",
      "headline": "ಉಡುಪಿ: ನಾಳೆ ಜಿಲ್ಲೆಯ ಶಾಲೆಗಳಿಗೆ ರಜೆ ಘೋಷಣೆ",
      "category": "education",
      "deck": "ಭಾರಿ ಮಳೆಯ ಮುನ್ಸೂಚನೆ ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಜಿಲ್ಲಾಧಿಕಾರಿ ಆದೇಶ.",
      "location": "ಉಡುಪಿ",
      "sources": ["ಉಡುಪಿ ಜಿಲ್ಲಾಡಳಿತ"],
      "source_urls": ["https://udupi.nic.in/en/notice/holiday-order/"],
      "status": "official",
      "published_at": "2026-09-28T08:30:00+05:30"
    },
    {
      "segment": "saara",
      "photo_plan": "",
      "headline": "ಬೈಂದೂರು: ಮೀನುಗಾರರಿಗೆ ಸಮುದ್ರಕ್ಕೆ ಇಳಿಯದಂತೆ ಸೂಚನೆ",
      "category": "weather",
      "deck": "ಗಾಳಿಯ ವೇಗ ಹೆಚ್ಚುವ ಸಾಧ್ಯತೆ ಇರುವುದರಿಂದ ಎಚ್ಚರಿಕೆ.",
      "location": "ಬೈಂದೂರು",
      "sources": ["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"],
      "source_urls": [],
      "status": "developing",
      "published_at": "2026-09-28T08:40:00+05:30"
    }
  ]
}
```

The authoritative field list is `schemas/story.schema.json`; every property
there says what it is for. `verified_by` is absent on purpose — see §6.

**Sources.** Each story keeps its own:

- an outlet's article pasted with its link → `sources: ["<outlet>"]`,
  `source_urls: ["<that article's URL>"]`, and its text kept with
  `intake.py source --url … --outlet …`. Credit the outlet the link belongs to
  (`FACT-06`); a section page or a chatbot link is not an article (`FACT-05`).
- a press release or notice → `sources: ["<the body that issued it>"]`, with
  its link if it has one; its text kept with `intake.py source`.
- what the editor saw or was told → `sources: ["ಊರ್ಮನಿ ಸುದ್ದಿ ಸ್ಥಳ ವರದಿ"]`.

Never invent a URL, and never fold one story's source under another's.

**Give every speed story a `reel_line`** — a short video headline (the budget
is in `render.py --describe`). A print headline needs far more screen time
than a ಸ್ಪೀಡ್ ನ್ಯೂಸ್ frame has.

**Set `location` on every story.** It drives the hashtags, the per-town
forward, and whether a reader can tell the story is theirs (`PUB-08`). Put the
town early: the caption is cut at about 125 characters (`PUB-05`).

**Write the `takeaway`** where there is one — a helpline, a last date, a road
closed. Copy that tells a reader what to do is what gets forwarded.

**`follows_up`** takes the date of an earlier edition when a story genuinely
continues it, with a new fact. Without it, a source already published on an
earlier day is refused (`DUP-01`).

### Festival wishes are not stories

A greeting has no source, status or headline. Write
`editions/greetings/<date>_<festival>.json` with `"kind": "greeting"` and
render that file; `python3 render.py --schema greeting` gives the fields. A
photograph needs `keep_clear` — the band holding the deity or subject, which
no type enters. No photograph is a valid choice.

---

## 3 · Choosing the segment

Every story carries exactly one `segment`. One story, one format.

| `segment` | Format | Use it for |
|---|---|---|
| `mukhya` | ಮುಖ್ಯ ಸುದ್ದಿ — 4:5 animated video carousel (scan-wipe .mp4 per slide, D98–D100) for ONE story: photo cover → ಏನಾಗಿದೆ? points → source & corrections | the breaking or top story of the day. **Always has a picture.** At most `Limits.mukhya_max_per_day`. |
| `speed` | ಸ್ಪೀಡ್ ನ್ಯೂಸ್ — 9:16 reel, one frame per story | quick hits that read in one line. Only when there are at least `Limits.roundup_min_stories` of them. |
| `saara` | ಸುದ್ದಿ ಸಾರ — 4:5 animated video carousel (scan-wipe .mp4 per slide, D98–D100): index cover → one slide per story → sources | everything else. **Never has pictures.** Between `Limits.saara_min_stories` and `Limits.saara_max_stories`. |

The editor's instruction wins. When they gave none, propose segments and have
the editor confirm them **before anything renders**.

---

## 4 · Pictures

Real photographs first. AI only when there is none, and only after asking.

- **`saara` stories carry no picture.** Leave `photo` out.
- **A `mukhya` story needs a picture** (`IMG-04` without one). A `speed` story
  may have one.
- **When the story has no picture, ask the editor: "Real photo or
  generate?"** Record the answer in `photo_plan`:
  - `"real"` — wait for the editor's photograph. It needs `credit`,
    `licence` (`own` only if our reporter shot it; anything else also needs a
    `source_url`), `nature` (`actual`, `handout` or `file`) and a `caption`
    saying what it shows. `actual` without a caption is refused.
  - `"ai"` — only now may a picture be generated. `nature: "ai"`,
    `credit: "ಊರ್ಮನಿ ಸುದ್ದಿ"`, `licence: "own"`, a caption describing only
    the scene (the ಎಐ ರಚಿತ ಚಿತ್ರ label is added for you — house rule
    2026-09-17-05), and **`approved_by`: the editor's name**. `Photo.validate()`
    refuses an AI picture without it (`IMG-05`).
  - `""` — not asked yet. Never decide on the editor's behalf.
- **An AI picture:** one single frame; no text, signs, banners, posters or
  number plates; the story's real action, place and material culture; never
  an identifiable face standing in for a real, named person; no minors'
  faces, victims, blood or gore.
- There is no stock library. Never attach a picture from the web.

---

## 5 · The law

**Crime stories state allegations, never verdicts.** Write
<span>ಆರೋಪ</span> / <span>ಆರೋಪಿ</span> / <span>ಶಂಕಿತ</span> /
<span>ಪ್ರಕರಣ ದಾಖಲು</span>. Plain past tense ("the son who killed…") is refused
unless `"convicted": true`, meaning a court actually convicted. Set
`"involves_minor": true` or `"sexual_offence": true` where they apply and the
system blocks identifying detail.

> **The `headline` and the `reel_line` must each carry their own marker.**
> They are checked on their own, because that is how they are read — a
> ಸ್ಪೀಡ್ ನ್ಯೂಸ್ frame, a WhatsApp forward, a screenshot. A marker in the
> `deck` does **not** make a guilt-asserting headline acceptable.
>
> ```
> ✗ "headline": "ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ ಬಂಧನ"      ← refused, even with ಆರೋಪಿ in the deck
> ✓ "headline": "ಹೆತ್ತವರ ಕೊಲೆ ಆರೋಪ, ಪುತ್ರ ಬಂಧನ"
> ```

An obituary needs two sources, or own reporting. Crime and death headlines are
set in ink, never red — that is the renderer's job, not yours.

**Numerals: Latin (25, 1077), never Kannada (೨೫).** Mixing the two is a
preflight failure.

Write Kannada a person actually says out loud.

---

## 6 · What will be rejected, and why

`Story.validate()` refuses to render rather than produce a dishonest post.
There is no flag to switch any of this off, and you must not add one.

| Rejection | Fix |
|---|---|
| no `segment`, or not one of `speed` / `saara` / `mukhya` | pick one — one story, one format |
| `photo_plan` not `""` / `real` / `ai` | the editor's answer, as given |
| AI photo with no `approved_by` | ask the editor; their name goes there — or use a real photo |
| photo with no `credit` or `licence` | name the photographer / agency; `own` only for our reporter's picture |
| `nature: "actual"` with no `caption` | say what the picture shows, or change nature |
| empty `sources` | name who told you; own reporting counts |
| sourced story with no `source_urls` | the article's URL, or mark own reporting |
| unknown `category` | pick from `render.py --describe` |
| obituary with one source | two sources, or own reporting |
| unknown field name | you typo'd; the error lists the valid fields |

At the gate (blocks `APPROVAL.md`, not the render): no `verified_by`
(`SRC-02`), a figure not in the kept source (`FACT-01`), a repeat (`DUP-01`), a
ಮುಖ್ಯ ಸುದ್ದಿ without a picture (`IMG-04`). The full table is in
[`RUNBOOK.md`](RUNBOOK.md).

Two things are computed and cannot be asserted:

- **ಬ್ರೇಕಿಂಗ್ decays.** It is checked against `published_at` and demoted after
  12 hours.
- **`status` is printed as it stands** — ದೃಢಪಟ್ಟ ವರದಿ / ಅಧಿಕೃತ ಪ್ರಕಟಣೆ /
  ಬೆಳವಣಿಗೆಯಲ್ಲಿದೆ / ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ. If it is not confirmed, say
  `"developing"` or `"unconfirmed"`.

---

## 7 · Things you must not do

1. **Do not write rendering code**, and do not edit `brand/` or `templates/`
   to make a story fit. Shorten the copy — that is what a sub-editor does.
2. **Do not hard-code a colour, size or margin.** They live in `brand/tokens.py`.
3. **Do not invent facts, sources, URLs, quotes or credits.** If the paste
   does not say it, ask.
4. **Do not generate a picture the editor has not asked for** (`photo_plan`
   must be `"ai"`, with their name in `approved_by`).
5. **Do not suppress a provenance label.** ಎಐ ರಚಿತ ಚಿತ್ರ on a frame is the
   system working.
6. **Do not choose a name for `verified_by`.** It is the person who checked
   the source. Run `scripts/verify.py` only with the name the editor gives in
   chat when they approve; otherwise say it is missing and stop. D59.
7. **Do not sign.** `sign_off.py` records a human verdict on taste, culture
   and news. You may prepare the evidence and recommend. D62.
8. **Do not upload anything.** A person posts every item.

---

## 8 · Checking your work

```bash
python3 render.py --check editions/DATE.json   # preflight, renders nothing
python3 render.py editions/DATE.json           # render; audits output automatically
python3 -m unittest tests.test_contract        # the honesty rules (instant)
```

`--check` reports three levels: `✗` failures block the render, `!` warnings are
a sub-editor's call, silence means clean. Pin the clock with
`--at 2026-09-28T09:00:00+05:30` for byte-identical output.

---

## 9 · Where to look next

| You want | Read |
|---|---|
| the day, step by step | [`RUNBOOK.md`](RUNBOOK.md) |
| the design standard | [`../STANDARDS.md`](../STANDARDS.md) |
| each format, field by field | [`TEMPLATES.md`](TEMPLATES.md) |
| **why** a rule exists | [`DECISIONS.md`](DECISIONS.md) — D92 for the formats |
| the machine-readable input contract | `schemas/story.schema.json` |
