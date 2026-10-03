# ಊರ್ಮನಿ ಸುದ್ದಿ — Design Standard

The single reference for how this channel looks. If a decision is not here, it
belongs here; add it rather than deciding twice.

Code lives in `brand/`. Nothing outside `brand/tokens.py` may hard-code a
colour, a type size or a margin. Numbers are quoted here by their
`tokens` name; the value lives in the code (D56).

The news formats are three — ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (`roundup`), ಸುದ್ದಿ ಸಾರ (`saara`),
ಮುಖ್ಯ ಸುದ್ದಿ (`mukhya`) — and they share one look, **Paper & Red** (DECISIONS
D92). Festival greetings are a separate genre with their own look (§9).

---

## 0 · The position

**Premium comes from restraint and precision, not from adding.** Borders,
outlined boxes, drop shadows and five accent colours are what cheap looks
like. Authority looks like: a real grid, a strict division of colour, hairlines
instead of borders, type set on a baseline, and generous space.

**Genuine is a design feature, not a constraint on one.** The credit under a
photograph, the named source, the honest status, the Grievance Officer on the
closing slide — we print them because they are true, and they are what makes
the page look like a newspaper.

### Things we never do

1. A rule around the whole canvas.
2. Stacked outlined rounded boxes — kicker pill, headline box, body box.
3. Centred news copy. News is left-aligned.
4. Four different left edges on one slide.
5. Rendering at 1×.
6. Leading taken from a Kannada face's nominal metrics (they run to 1.68em).
7. Type below the legibility floor.
8. A picture that does not say where it came from.
9. Red on a person's name in a crime or death headline.

---

## 1 · Colour — Paper & Red

The logo's exact colours, from `brand/tokens.py :: C`. Nothing is invented.

| Role | Tokens | Where |
|---|---|---|
| **Paper** — the page | `paper_50` … `paper_200` | every slide and frame ground |
| **Ink** — the type | `ink_950` … `ink_300` | headlines, body, meta, hairlines |
| **Red** — the news | `red_500` / `red_600` | the kicker, ಬ್ರೇಕಿಂಗ್, the half of a headline after its colon, the wordmark bug |
| **Sunset gold** — the brand | `gold_500` | the line under every photograph, the stroke under the red wordmark, numeral chips, accent rules |
| gold as **text** | `gold_800` | only when gold must be read as type |

**The division is the system.** Red means *this is the news*; gold means
*this is ಊರ್ಮನಿ ಸುದ್ದಿ*. A slide that uses red for decoration or gold for news
has broken both signals.

**Crime and death headlines are ink only.** No red on a person's name, and
no red half after the colon — urgency colour on an accused or a dead person
reads as a verdict.

**Gold is a fill on paper, never small type.** `gold_500` on `paper_50`
measures about 1.7:1 — not "a bit low", unreadable. Gold that must be read
uses `gold_800`. This is measured, not advised: `brand/legibility.py` checks
every pair the house sets type in, `compliance()` fails the render below the
floor, and its `FORBIDDEN` table asserts plain gold on paper stays illegible,
so "fixing" it by brightening the gold fails a test. D60.

| Floor | Applies to |
|---|---|
| `Limits.contrast_min` | body text |
| `Limits.gold_on_light_min` | display sizes |
| `Limits.min_effective_px` | the line that sells the post, **at the width it is first seen** |

Everything is designed at 1080 wide and first seen at 400 or less — a
carousel cover in a profile grid, a reel's first frame in the feed.
`legibility.PRIMARY_STEP` names the step that has to survive first sight for
each format, and preflight checks it.

**Standing copy lives in `tokens.Brand`** — name, tagline, handle, coverage,
CTA, grievance officer. Never write them out in a template. The coverage line
is one word, **ಕರಾವಳಿ**.

Category registry: `tokens.CATEGORIES`. Category is data (it drives copy and
reach), not a colour on the slide.

---

## 2 · Typography

Kannada is the hard case and the engine exists to serve it. `brand/typo.py`

### The three rules the code enforces

1. **Draw on baselines, never on boxes.** Kannada vowel signs (ೀ ೈ ೊ) climb far
   above the headline and subscript consonants (್ತ ್ರ ್ದ) hang far below. Text
   positioned by bounding box jumps line to line depending on which matras it
   happens to contain. Everything is drawn with `anchor='ls'` onto a computed
   baseline.

2. **Never letter-space Kannada.** Tracking means drawing glyph by glyph, which
   destroys the shaping raqm does for conjuncts — ಸುದ್ದಿ becomes ಸು ದ ್ ದಿ. The
   engine ignores tracking on any string containing Kannada. Tracking is for
   Latin caps only, expressed as an em fraction.

3. **Leading is a multiple of the em, plus a collision guarantee.**
   AnekKannada declares ascent+descent of **1.68em**. Setting 1.4 leading off
   that gives 2.35× the type size, and a two-line fact reads as two items.
   Leading is taken from the em and raised, if and only if necessary, so no
   descender touches the next line's ascender — measured on the actual lines.

### Faces

| Key | File | Use |
|---|---|---|
| `kn` | `NotoSansKannada-Bold` | **every news headline** — the one heavy weight; shapes every conjunct correctly |
| `kn_var` | `AnekKannada-Variable` | decks, points, body, meta |
| `kn_serif` | `NotoSerifKannada-Bold` | festival greetings |
| `latin` | SF (`SFNS.ttf`) | numerals, ALL-CAPS eyebrows, `@oormanisuddi` |

One heavy weight on a slide: the headline. Everything else is lighter.

**Any Latin face given user copy goes through `typo.font_for()`**, which swaps
in a Kannada face when the string needs one. SF has no Kannada; passing
Kannada to it renders tofu boxes.

### Scale — `tokens.T`

The type scale and its leadings live in `tokens.T` (`display` down to
`micro`). **Nothing below `micro`** — below it, at 1080 wide, text is
decoration pretending to be information.

### Wrapping

`typo.wrap(balance=True)` evens the ragged edge so the last line is never a
lonely word. `typo.fit()` finds the largest size that fits a box, so a
seven-word and a twenty-word headline both look designed.

---

## 3 · Grid, formats, safe zones

`tokens.Grid`, `tokens.FORMATS`

- Baseline unit and side margins from `tokens.Grid`.
- **Square corners.** `Grid.radius = 0`.
- **Left-aligned.** One left edge per slide.

| Format | Used by |
|---|---|
| `post` (4:5) | ಸುದ್ದಿ ಸಾರ, ಮುಖ್ಯ ಸುದ್ದಿ |
| `reel` (9:16) | ಸ್ಪೀಡ್ ನ್ಯೂಸ್ |

**Reel safe zones are not advisory.** Instagram parks its action rail over the
right edge and its caption block over the bottom of a reel; the `reel` safe
inset keeps type out of both.

**Everything renders at 2× and downsamples once with Lanczos.** Layout code
speaks in final delivery pixels; `Surface` handles the rest. JPEG is written
with **4:4:4 chroma** — Kannada matras are thin, and red type turns to mush
under default 4:2:0 subsampling.

---

## 4 · Pictures

**Real photographs first. AI only when there is none, and only after asking
(D92, AGENTS rule 2).**

| Format | Pictures |
|---|---|
| ಸುದ್ದಿ ಸಾರ | **never** — it is the text bulletin |
| ಮುಖ್ಯ ಸುದ್ದಿ | **always** — the cover is the photograph (`IMG-04` without one) |
| ಸ್ಪೀಡ್ ನ್ಯೂಸ್ | the story's picture if it has one; otherwise a type-only frame |

A gold line sits under every photograph. The disclosure — credit, and the
nature label when it is not the actual scene — is printed with it.

Crop focal default is **(0.5, 0.42)**, not centre: in news photography the
face and the action sit above centre.

**Fade a picture's own alpha into the page; never paint a veil over it.** A
veil is one colour and mismatches the page beneath by a shade, leaving a band
exactly at the join.

---

## 5 · The genuineness contract

`brand/content.py`. Enforced by `Story.validate()` — there is no flag to
switch it off.

| Rule | Enforcement |
|---|---|
| Every story runs in one format | `segment` ∈ `speed` / `saara` / `mukhya` |
| Every photograph names a credit and a licence | `ContentError` if missing |
| Every photograph declares its nature | `actual` / `file` / `handout` / `ai` … |
| A picture not of the scene is labelled on the slide | `ಸಂಗ್ರಹ ಚಿತ್ರ`, `ಹಂಚಿಕೆ ಚಿತ್ರ`, `ಎಐ ರಚಿತ ಚಿತ್ರ` — printed, not suppressible |
| An AI picture names who approved it | `photo.approved_by`, or `ContentError` |
| A photo claiming `actual` carries a caption | `ContentError` if missing |
| At least one source is named | own reporting counts, and says so |
| **ಬ್ರೇಕಿಂಗ್ is computed, never asserted** | from `published_at`; demoted after 12h |
| **ನೇರ ಪ್ರಸಾರ requires a real stream URL** | `live_url` must start with `http` |
| Status is printed as it stands | ದೃಢಪಟ್ಟ ವರದಿ / ಅಧಿಕೃತ ಪ್ರಕಟಣೆ / ಬೆಳವಣಿಗೆಯಲ್ಲಿದೆ / ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ |
| The Grievance Officer is on every closing slide | IT Rules 2021 Part III |

**Numerals: Latin (123), not Kannada (೧೨೩)** — what Kannada broadcast and print
use for figures; mixing the two is a preflight failure.

---

## 6 · Composition

- Layouts **flow content, they do not position it**. The copy decides the
  composition.
- **Editorial drop-priority**, in the order a sub-editor would cut: the
  advisory before the facts, the standfirst before the facts, the facts before
  the headline. The headline is never cut.
- **Item gaps clearly exceed internal line gaps.** Get this backwards and a
  two-line fact reads as two facts.
- **Hairlines, not borders.**
- Type over photography carries a soft shadow; type on paper never does.

---

## 7 · Motion — ಸ್ಪೀಡ್ ನ್ಯೂಸ್

`brand/motion.py`, `brand/speednews.py`

- **It opens on the news.** No logo sting — distribution is decided in the
  first seconds.
- **Nothing cuts on.** Elements arrive on an eased curve with a short rise.
- **Duration follows reading time** — `Motion.read_rate`, plus build-in and
  settle. Scenes are never compressed below reading speed. The reel's length
  window is `Limits.reel_target_max` / `Limits.reel_warn_seconds`.
- **Write a `reel_line`.** A print headline needs far more screen time than a
  ಸ್ಪೀಡ್ ನ್ಯೂಸ್ frame has.
- **The anchor says what is on screen**, and every spoken line goes through
  the pronunciation normaliser (D50, D53).
- A counter and a progress segment per story — viewers stay for an end they
  can see.

### Carousel motion — the scan wipe (D98, D99)

`brand/animate.py`, `Motion.anim_*`. Every ಸುದ್ದಿ ಸಾರ and ಮುಖ್ಯ ಸುದ್ದಿ slide
is also a short video, made from the finished slide.

- **Lines flow, they do not queue.** Each line is revealed left to right
  through a soft feathered edge (`anim_feather`) behind a thin gold light
  that rides on the letters and goes out across gaps. The next line starts
  `anim_gap` after the one above it (`anim_head_gap` between headline lines,
  which also settle up `anim_rise` px), with an `anim_beat` where a block
  ends. Easing: a gentle start and a long, slow settle — never linear,
  never a bounce.
- **A cover is never blank.** Its photograph and headline are there at
  frame 0; what follows them is revealed. Every other slide opens on its
  chrome alone.
- **The chrome never moves**: the bug, date, rules, footer, the swipe tab.
- **The hold is what gets read** — `read_rate`, between `anim_hold` and
  `anim_hold_max`. While it holds, the chevrons nudge right every
  `anim_nudge` s: the slide asks to be swiped.
- **No seam.** The last `anim_out` s dissolve back to frame 0, so the loop
  restarts as if it were the first play.
- **Never letter by letter** — a cut conjunct is a broken shape.
- **A photograph is never wiped.** On a cover it is there at frame 0; on
  another slide it fades. The gold sunline under it draws across (`anim_sun`).

### Audio

- Loudness normalised to `Limits.lufs` / `Limits.true_peak_dbtp` — what the
  platforms normalise to.
- Music from the licence register only; sound effects are our own (D82).
- Video: H.264 high, `+faststart`. Audio: AAC, 48kHz.

---

## 8 · Preflight, audit & working with it

`brand/qa.py`. `preflight()` catches, before rendering: copy over budget,
mixed numerals (**fail**), stale breaking flags, missing location. `inspect()`
catches, after rendering: wrong dimensions, oversize files, crushed blacks,
blown highlights. `render.py` runs both and refuses to continue on a failure;
`--check` runs preflight alone.

```bash
python3 render.py editions/DATE.json          # every segment present
python3 render.py --describe                  # every format + its rules
python3 render.py --check editions/DATE.json  # validate, render nothing
python3 -m unittest discover tests            # the design is still correct
```

Identical content plus the same pinned clock (`--at`) gives byte-identical
output. `tests/test_golden.py` relies on this; a golden failure means the
visuals changed — look at the renders, then re-bless deliberately with
`python3 -m tests.test_golden --bless`.

**Before changing any value here, read [`docs/DECISIONS.md`](docs/DECISIONS.md)**
— it records what each rule replaced and what breaks without it.

### Checklist before anything goes out

- [ ] Rendered at 2×, correct dimensions, under the size ceiling
- [ ] Every photograph credited, licensed, and labelled if not of the actual scene
- [ ] Every AI picture approved by name; none on a ಸುದ್ದಿ ಸಾರ
- [ ] Source named; status is what it actually is
- [ ] ಬ್ರೇಕಿಂಗ್ only if it genuinely is
- [ ] Red only for news; gold only for the brand; crime/death headlines in ink
- [ ] Latin numerals throughout
- [ ] Nothing inside a platform safe zone; nothing below the floor
- [ ] Grievance Officer on the closing slide
- [ ] Preflight and audit both clean

---

## 9 · Festival greetings — a separate genre

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
