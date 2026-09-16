# ಊರ್ಮನಿ ಸುದ್ದಿ — Design Standard

The single reference for everything this channel publishes. If a decision is not
here, it belongs here; add it rather than deciding twice.

Code lives in `brand/`. Nothing outside `brand/tokens.py` may hard-code a
colour, a type size or a margin.

---

## 0 · The position

**Premium comes from restraint and precision, not from adding.** Gold borders,
outlined boxes, drop shadows on everything and five accent colours are what
cheap looks like. Authority looks like: a real grid, one accent, hairlines
instead of borders, photographs that share a single grade, type set on a
baseline, and generous space.

**Luxury is not the same as decoration.** The luxurious quality in this system
is that nothing is arbitrary — every measure, every leading value and every
tint is derived, and the eye reads that consistency as care even when it cannot
name it.

**Genuine is a design feature, not a constraint on one.** The credit line under
a photograph, the named source, the honest status — these are the things that
make a broadsheet look like a broadsheet. We print them because they are true,
and they happen to be what makes the page look authoritative.

### The nine things we never do again

Every one of these was in the previous output and every one is now impossible
in the system.

1. A gold rule around the whole canvas.
2. Stacked outlined rounded boxes — kicker pill, headline box, body box, meta pills.
3. A hard seam where a photograph stops and the page begins.
4. Photographs pasted untreated, so the picture and the type look like two documents.
5. Four different left edges on one card.
6. Rendering at 1x.
7. Leading taken from a Kannada face's nominal metrics (they run to 1.68em).
8. Body copy or footers below 19px at 1080 wide.
9. A picture that does not say where it came from.

---

## 1 · Colour

Sampled from the logo, not invented. `brand/tokens.py :: C`

| Role | Value | Where |
|---|---|---|
| `ink_950` `#03050A` | page base | every card |
| `ink_900 … ink_600` | surfaces, rules | panels, hairlines |
| `ink_300 / ink_400` | dim text | meta, provenance |
| `paper_0 … paper_300` | text on ink | headline → caption |
| **`gold_500` `#F5B301`** | **the one brand accent** | rules, numerals, handle, tagline, the plate's sun |
| `gold_800` `#8A6200` | the accent **on light grounds only** | greeting light themes, paper |
| `red_500` `#C81E1E` | alert only | breaking chip, live chip |
| `sea_500` `#0E5C7A` | civic secondary | category rail |

**Gold never goes on paper.** `gold_500` on `paper_50` measures 1.70:1 — not
"a bit low", unreadable. `Role.accent_on_paper` (bronze `gold_800`) is the
accent for any light ground, at 5.04:1. This is not a guideline:
`brand/legibility.py` measures every pair the house sets type in, `compliance()`
fails the render below the floor, and `FORBIDDEN` in that table asserts that
plain gold on paper stays illegible — so "fixing" it by brightening the gold
fails a test instead of shipping on a festival poster. D60.

| Floor | Value | Applies to |
|---|---|---|
| `Limits.contrast_min` | 4.5:1 | body text |
| `Limits.gold_on_light_min` | 3.0:1 | display sizes |
| `Limits.min_effective_px` | 7px | the line that sells the post, **at the width it is first seen** |

That last one is the one people get wrong. Everything here is designed at 1080
and consumed at 400 or less: a carousel cover is ~150px in a profile grid, a
reel's first frame ~200px in the feed, a thumbnail ~210px in a search row. A
19px provenance line is 2.6px in a carousel grid — it is not small, it is
absent. That is fine, because the disclosure is also in the caption; what is
not fine is the headline failing the same test. `legibility.PRIMARY_STEP` names
the step that has to survive first sight for each format, and preflight checks
it.

**Gold is on every card. Category colour is confined to the rail.** That is why
a mixed feed still reads as one publication. Do not tint a headline, a panel or
a background with a category colour.

Category registry: `tokens.CATEGORIES` — breaking, crime, weather, civic,
health, education, culture, sport, farm, obituary, explainer.

**Standing copy lives in `tokens.Brand`** — name, tagline, handle, coverage,
bulletin, CTA. Never write them out in a template. The coverage line is one
word, **ಕರಾವಳಿ**: a list of towns dates itself the moment you cover somewhere
that is not on it.

---

## 2 · Typography

Kannada is the hard case and the engine exists to serve it.
`brand/typo.py`

### The three rules the code enforces

1. **Draw on baselines, never on boxes.** Kannada vowel signs (ೀ ೈ ೊ) climb far
   above the headline and subscript consonants (್ತ ್ರ ್ದ) hang far below. Text
   positioned by bounding box jumps line to line depending on which matras it
   happens to contain. Everything is drawn with `anchor='ls'` onto a computed
   baseline.

2. **Never letter-space Kannada.** Tracking means drawing glyph by glyph, which
   destroys the shaping raqm does for conjuncts — ಸುದ್ದಿ becomes ಸು ದ ್ ದಿ. The
   engine silently ignores tracking on any string containing Kannada. Tracking
   is for Latin caps only, and is expressed as an em fraction.

3. **Leading is a multiple of the em, plus a collision guarantee.**
   AnekKannada declares ascent+descent of **1.68em**. Setting 1.4 leading off
   that gives 2.35× the type size, and a two-line fact then reads as two
   separate items. Leading is taken from the em and then raised, if and only if
   necessary, so no descender can touch the next line's ascender — measured on
   the actual lines being set.

### Faces

| Key | File | Use |
|---|---|---|
| `kn` | `NotoSansKannada-Bold` | **all headlines** — shapes every conjunct correctly |
| `kn_var` | `AnekKannada-Variable` | decks, body, meta. Weight 100–800, Width 75–125 |
| `kn_serif` | `NotoSerifKannada-Bold` | pull-quotes, broadsheet masthead |
| `latin` | SF (`SFNS.ttf`) | numerals, ALL-CAPS eyebrows, `@oormanisuddi` |

**Any Latin face given user copy must go through `typo.font_for()`**, which
swaps in a Kannada face when the string needs one. SF has no Kannada coverage;
passing Kannada to it renders tofu boxes.

### Scale — at 1080 wide (`tokens.T`)

| Token | Size | Leading | Use |
|---|---|---|---|
| `display` | 104 | 1.20 | text cards, carousel statements |
| `h1` | 78 | 1.26 | primary headline, 4:5 |
| `h2` | 64 | 1.28 | carousel headline, stat card |
| `h3` / `h4` | 52 / 42 | 1.30 / 1.34 | secondary |
| `deck` | 34 | 1.44 | standfirst |
| `body` | 30 | 1.52 | facts, carousel body |
| `meta` | 24 | 1.36 | date, location, byline |
| `caption` | 22 | 1.42 | photo caption |
| `eyebrow` | 21 | 1.20 | ALL-CAPS Latin, tracking 0.14em |
| `micro` | 19 | 1.30 | provenance — **the floor** |

Nothing below `micro`. Below 19px at 1080 it is decoration pretending to be
information.

### Wrapping

`typo.wrap(balance=True)` evens the ragged edge so the last line is never a
lonely orphan word. That is the most visible difference between a designed
headline and an automatic one, and it is on by default.

`typo.fit()` finds the largest size that fits a given box. Automated news copy
varies wildly in length; this is what keeps a seven-word headline and a
twenty-word headline both looking designed.

---

## 3 · Grid, formats, safe zones

`tokens.Grid`, `tokens.FORMATS`

- Baseline unit **6px**. Side margin **72px** on 1080-wide (`margin_l` 88 for
  quote and stat cards).
- **Square corners.** `Grid.radius = 0`. Rounding is opt-in and only for photo
  tiles (`radius_soft` 10).
- Category rail width **5px**.

| Format | Size | SS | Safe inset (L,T,R,B) |
|---|---|---|---|
| `post` | 1080×1350 | 2 | 72, 72, 72, 72 |
| `square` | 1080×1080 | 2 | 72, 72, 72, 72 |
| `story` | 1080×1920 | 2 | 72, **250**, 72, **340** |
| `reel` | 1080×1920 | 2 | 72, **230**, **220**, **480** |
| `thumb` | 1280×720 | 2 | 48, 40, 48, 96 |
| `broadsheet` | 1080×1620 | 2 | 64, 56, 64, 56 |
| `bulletin` | 1920×1080 | 2 | 96, 72, 96, 84 |
| `bulletin_4k` | 3840×2160 | **1** | 192, 144, 192, 168 |

**Reel safe zones are not advisory.** Instagram parks its action rail over the
right 200px and its caption block over the bottom ~470px. Text placed there is
decoration. The band below the safe area still carries the brand — on a paused
reel and everywhere the video is reposted it is visible, so it gets the handle
and the tagline rather than a rectangle of dead black.

**Everything renders at 2× and downsamples once with Lanczos.** Layout code
speaks in final delivery pixels; `Surface` handles the rest. The exception is a
format already at twice delivery resolution — `bulletin_4k` — which renders 1:1,
because composing it on a further 2× canvas is a 4× pixel bill for antialiasing
no one can resolve.

**The design is drawn for a 1080-wide portrait frame and a 1920-wide landscape
one. Anything larger is the same design scaled, never a bigger canvas.**
`StoryScene.fs` is that scale and every fixed measure is multiplied by it. A 4K
bulletin whose type stayed 1920-sized is not a 4K bulletin — it is a 1080p one
with three quarters of the column empty. See DECISIONS.md D40. JPEG is written at
q95 with **4:4:4 chroma** — Kannada matras are thin, and coloured type on a red
rail turns to mush under default 4:2:0 subsampling.

---

## 4 · Photography

### The house grade — `surface.house_grade()`, `tokens.Grade`

One grade, every picture, deliberately gentle:

- filmic S-curve contrast 0.16 (pivots at 0.5, never clips either end)
- saturation 0.88 — news, not tourism
- split tone: shadows toward brand ink 0.20, highlights toward sunset gold 0.12
- clarity 0.35 (wide-radius local contrast)
- vignette 0.22
- grain σ5, biased 0.6 toward the shadows

It exists to make images from many different cameras read as one publication —
not to stylise the news. **Grain is not optional.** Flat digital black is the
cheapest-looking thing on a phone screen.

### Dissolving a picture into the page

**Fade the image's own alpha; never paint a dark veil over it.** A veil is one
particular colour and will always mismatch the page beneath by a shade, leaving
a faint band exactly where you were trying to hide the join. An alpha fade lets
whatever is underneath come through, so there is no join to find.
`place_photo(fade_bottom=…)`.

The scrim ramp (`surface.scrim`) is a **smoothstep on a power-shaped input**,
not a plain power curve. A plain power curve saves all its darkening for the
last few percent — the picture is still a quarter visible where the type
begins, then snaps shut.

Crop focal default is **(0.5, 0.42)**, not centre: in news photography the
subject's face and the action sit above centre, and a naive centre crop
decapitates people.

---

## 5 · The genuineness contract

`brand/content.py`. These are enforced by `Story.validate()` — there is no flag
to switch them off.

| Rule | Enforcement |
|---|---|
| Every photograph names a credit | `ContentError` if missing |
| Every photograph declares its nature | `actual` / `file` / `representative` / `handout` / `graphic` / `ai` |
| A picture not of the scene is labelled on the card | `ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ`, `ಸಂಗ್ರಹ ಚಿತ್ರ`, `ಎಐ ರಚಿತ ಚಿತ್ರ` — printed, not suppressible |
| A photo claiming `actual` must carry a caption | `ContentError` if missing |
| At least one source is named | `ContentError` if missing; own reporting counts, say so |
| **ಬ್ರೇಕಿಂಗ್ is computed, never asserted** | from `published_at`; auto-demoted after 12h |
| **ನೇರ ಪ್ರಸಾರ requires a real stream URL** | `live_url` must start with `http` |
| Verification status is printed as it stands | ದೃಢಪಟ್ಟ ವರದಿ / ಅಧಿಕೃತ ಪ್ರಕಟಣೆ / ಬೆಳವಣಿಗೆಯಲ್ಲಿದೆ / ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ |

A card that admits it is still being checked is worth more than one that
pretends otherwise.

**If there is no honest picture, omit `photo`.** `report_card` then draws an
**editorial plate** — the logo's horizon reduced to geometry, credited
ಗ್ರಾಫಿಕ್ಸ್. Every post and every carousel slide therefore carries a visual,
without anyone being shown a stock photograph dressed as reporting. A plate is
visibly a graphic; that is the point.

**Numerals: Latin (123), not Kannada (೧೨೩)** — this is what Kannada broadcast
and print use for figures, and mixing the two on one card is caught by
preflight as a failure.

---

## 6 · Composition

- Layouts **flow content, they do not position it**. The copy decides the
  composition: a short headline earns a bigger photograph; a long one takes the
  space it needs and the photograph yields.
- **Editorial drop-priority** when a card cannot hold everything, in the order a
  sub-editor would cut: the advisory goes before the facts, the standfirst goes
  before the facts, the facts go before the headline. The headline is never cut.
- **Leftover space goes to the picture**, never left as a gap above the footer.
- **Item gaps must clearly exceed internal line gaps.** In a fact list: 34px
  between items against ~10px between lines. Get this backwards and a two-line
  fact reads as two facts.
- **Hairlines, not borders.** 1px at alpha 0.14 (`Role.hairline`), 0.07 for the
  soft separator.
- Type over photography carries a soft shadow. Type over a flat panel never does.

---

## 7 · Motion — reels & shorts

`brand/motion.py`

- **Nothing cuts on.** Every element arrives on an eased curve (`out_quint`)
  with a ~30px rise and a 0.075s per-line stagger. Hard-appearing text is the
  loudest signal that a video was assembled by a script.
- **Ken Burns is eased and drifts.** `in_out_sine` scale settling *into* frame
  plus lateral drift. A linear zoom reads as a slideshow.
- **Duration follows reading time** — `Motion.read_rate` **7.0** Kannada
  chars/sec, plus 1.4s of build-in and a 0.8s settle, floored at 5s. Kannada is
  an abugida: a 70-character headline is ~40 aksharas, and a first read on
  moving video runs 3-4 aksharas a second. `target_seconds` is a **ceiling, not
  a quota** — scenes are never compressed below reading speed; stories are
  dropped from the end instead.
- **A reel is the lead story, and it opens on the news.** No logo sting.
  Instagram and YouTube decide distribution in the first 1–3 seconds; a 1.9s
  ident is a scroll cue. The masthead already brands every scene. The carousel
  and the 16:9 bulletin carry the rest of the edition. `reel_cover.jpg` is the
  cover — set it; do not leave frame 0 as the default.
- **Write a `reel_line`.** ~45 characters. A print headline of 75 needs ~11s of
  screen time on its own, which is most of a scene.
- **Full-bleed picture, type seated over its lower half.** Not a photo band
  plus a text band — on 9:16 that letterboxes the picture and shrinks the
  headline below arm's-length legibility.
- **One static layer per scene.** Type is rendered once at 2× and reused as a
  sprite; only the photograph is recomputed per frame. This is why a 28s reel
  renders in about 40 seconds.
- **A reel scene carries the headline and usually nothing else.** A supporting
  line appears only when the headline needs under 5.5s, is at most 62
  characters, **and still fits inside `hold_max` once the headline has taken
  its share**. Headline plus deck together needed ~25s of reading in a 6s
  scene — that was the whole reason viewers could not read them.
- **`hold_max` is a backstop, not a budget.** A scene needing more than 12s is
  reported at render time, never silently truncated: "duration follows reading
  time" is only true if nothing quietly overrides it. If you see that warning,
  cut the copy — do not raise the ceiling.
- Transitions: 0.40s cross-dissolve with a brief gold sweep. A transition you
  notice is too long.
- A **progress bar** runs across the top. Viewers stay for a bar they can see
  the end of.

### Audio

- Score at 0.62, **ducked to 0.42** for 1s around every scene change so the hit
  and the headline have room.
- Hits: impact on the open, whoosh into each scene, ping on the headline.
- **Normalised to −14 LUFS / −1.5 dBTP** — what Instagram and YouTube normalise
  to. Delivering hotter just means the platform turns it down, and loud material
  turned down sounds flat.
- Video: H.264 high, CRF 17, `+faststart`. Audio: AAC 192k, 48kHz.

---

## 8 · Templates

| Function | Format | Use it for |
|---|---|---|
| `report_card` | 4:5 | the workhorse — any story with an honest photograph |
| `text_card` | 4:5 | orders, advisories, results; anything with no honest picture |
| `quote_card` | 1:1 | a single voice, on a duotone bed |
| `stat_card` | 1:1 | when the story *is* the number |
| `carousel` | 1:1 ×N | the day's bulletin: cover → story per slide → sources & follow |
| `story_card` | 9:16 | Instagram Story, WhatsApp status |
| `youtube_thumb` | 16:9 | pass a short `hook=`, not the headline — ≤7 words, and it is guilt-checked like a headline |
| `broadsheet` | 2:3 | the day's front page |
| `render_reel` | 9:16 video | the lead story as a Reel / Short — no sting |

---

## 9 · Preflight & audit

`brand/qa.py`. Neither raises — a sub-editor may overrule a guideline; what
they must not be able to do is overrule it by accident.

`preflight(story, format, hook='')` catches, before rendering: headline over
budget for the format, mixed numeral systems (**fail**), overlong deck or
facts, more facts than the card carries, stale breaking flags, AI imagery,
unconfirmed status, missing location.

`inspect(path, format)` catches, after rendering: wrong dimensions, file over
the platform ceiling, crushed blacks, blown highlights, a card with no focal
point.

`render.py` runs both around every render and refuses to continue on a failure.
`render.py --check` runs preflight alone, rendering nothing.

---

## 10 · Working with it

```bash
python3 render.py editions/2026-08-25.json     # a full package from JSON
python3 render.py --describe                   # every template + its rules
python3 render.py --check my.json              # validate, render nothing
python3 -m unittest discover tests -v          # the design is still correct
```

Content is JSON in `editions/`; copy `editions/2026-08-25.json`. Every
deliverable comes from the same objects, so the post, the carousel, the story,
the thumbnail and the reel cannot drift apart.

A tool generating that JSON should read [`docs/AI_BRIEF.md`](docs/AI_BRIEF.md).
Per-template reference: [`docs/TEMPLATES.md`](docs/TEMPLATES.md). **Before
changing any value here, read [`docs/DECISIONS.md`](docs/DECISIONS.md)** — it
records what each rule replaced and what breaks without it.

### Landscape (16:9 bulletin)

The scale is calibrated for a 1080-wide **portrait** frame. A 16:9 bulletin is
watched on a phone at ~400px wide, so small type must be scaled up (`ts = 1.38`)
or it disappears.

Landscape does **not** use the lower-third. The type sits in a full-height
column on the left 46%; the photograph takes the right 54% at full height. A
16:9 frame's surplus is width, not height, and spending height on furniture
cost the picture its middle — see [`docs/DECISIONS.md`](docs/DECISIONS.md) D38.
Headline to 76px over five lines, masthead / date / time / photo credit all in
the column, and only the handle on the picture.

The bulletin is also paced differently, because it is watched rather than
glanced at. A bulletin scene shows the **print headline and the deck** — the
carousel's payload, not the reel's single `reel_line` — and may run to 30s
where a reel scene caps at 12s.

Its **length is derived, never targeted**. Headline plus deck on a four-story
edition comes to 60-120s on its own; facts are promoted into the body only
while the total is still under 60s, which is where YouTube stops treating a
video as a Short and starts using the thumbnail we render. An edition without
the copy to reach 60s is reported as short and **not padded** — see
[`docs/DECISIONS.md`](docs/DECISIONS.md) D37.

### Reproducibility

Identical content plus the same pinned clock gives byte-identical output:

```bash
python3 render.py editions/2026-08-25.json --at 2026-08-25T09:40:00+05:30
```

`tests/test_golden.py` relies on this to pin the design. A golden failure means
the visuals changed — look at the renders, then re-bless deliberately with
`python3 -m tests.test_golden --bless`.

### Adding a template

1. Write `templates/<name>.py`. Take colour, size and spacing from `tokens` —
   never a literal.
2. Build from `components`, not from `ImageDraw`.
3. Flow the content; do not position it.
4. Take the format's safe zone seriously.
5. Finish with `grain(sf, Grade.grain, Grade.grain_shadow_bias)`.
6. Add a `Spec` to `templates/__init__.py`, then regenerate the derived files:
   `python3 -m templates --dump && python3 docs/_build_templates_md.py`
7. Add a golden case in `tests/test_golden.py`.

---

## 11 · The checklist

Before anything goes out:

- [ ] Rendered at 2×, correct dimensions, under the size ceiling
- [ ] Every photograph credited, and labelled if it is not of the actual scene
- [ ] At least one source named on the card
- [ ] Status is what it actually is
- [ ] "ಬ್ರೇಕಿಂಗ್" only if it genuinely is
- [ ] Latin numerals throughout, no mixing
- [ ] Nothing critical inside a platform safe zone
- [ ] Nothing set below 19px
- [ ] One accent (gold); category colour only on the rail
- [ ] No border round the canvas, no outlined boxes (news — greetings follow §12)
- [ ] Preflight and audit both clean

---

## 12 · Festival greetings — a separate genre

Everything above is the standard for **news**. A festival or occasion wish is
built to be felt and forwarded rather than believed, and is set by
`templates/greeting.py` under its own rules (DECISIONS D54):

- Centred and symmetrical. Signed — "ಶುಭ ಕೋರುವವರು" and the brand — never mastheaded.
- The festival name in the serif, in engraved gold foil. Never flat yellow.
- Ornament is allowed here and only here, drawn in gold at hairline weight:
  corner filigree, a lotus divider, an arch window, lamp-light bokeh. Never
  clip-art, never a continuous border.
- A theme changes only the ground and the light. Gold stays the one accent.
- A photograph declares `keep_clear`, and no type ever enters the deity's band.
- AI imagery is labelled on the poster and in the caption.
- No hard photo seam: the arch window's foot dissolves into the ground.
