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
        "focal": [0.5, 0.5]
      },
      "location": "ಉಡುಪಿ ಜಿಲ್ಲೆ",
      "dateline": "ಜಿಲ್ಲಾ ವರದಿ",
      "sources": ["ಭಾರತೀಯ ಹವಾಮಾನ ಇಲಾಖೆ", "ಉಡುಪಿ ಜಿಲ್ಲಾಡಳಿತ"],
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
- If the picture is from the archive or merely illustrative → `nature:
  "representative"` or `"file"`. It will be labelled ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ / ಸಂಗ್ರಹ
  ಚಿತ್ರ on the card. That is correct and must not be worked around.
- **If no honest picture exists, omit `photo` entirely.** The story then gets
  `text_card`, which is a good-looking card built from the brand's own sunset
  horizon. Never attach a decorative stock photo to fill the space. Illustrating
  a Brahmāvara story with a highway bridge signposted HONNAVAR is the specific
  failure this system was built to prevent.

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
| `stories` | 3–4 per edition | 5+ squeezes every reel scene under 6 s |

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

1. **Do not write rendering code.** No Pillow, no canvas, no HTML-to-image. Nine
   templates already exist. If none fits, say so and stop — do not improvise one.
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
