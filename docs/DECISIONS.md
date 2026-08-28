# Design decisions

Every rule in this system was a choice, and most of them look arbitrary until
you know what went wrong without them. This file is the record. **Read the
relevant entry before changing a value** — several of these were found by
rendering something, looking at it, and finding it wrong.

Format: what was decided, what it replaced, and what breaks if you undo it.

---

## D1 · Leading comes from the em, not the font's metrics

**Decided.** Line height = `font_size × leading`, then raised only if the
measured ink of the actual lines being set would collide.

**Replaced.** `line_height = (ascent + descent) × leading`, the ordinary way.

**Why.** AnekKannada declares ascent + descent of **1.68 em**. A leading of 1.4
against that sets text at 2.35× its own size. The visible symptom was a
two-line fact whose two lines sat further apart than the gap between separate
facts — so a list of three facts read as a list of five or six.

**If you undo it.** Every multi-line block in the system silently doubles its
leading and all the layout solvers start dropping content that would otherwise
fit.

`brand/typo.py :: line_height`

---

## D2 · Text is drawn on baselines, never at box positions

**Decided.** Everything is drawn with `anchor='ls'` onto a computed baseline.

**Replaced.** `draw.text((x, y), ...)`, which positions by bounding box.

**Why.** Kannada vowel signs (ೀ ೈ ೊ) climb far above the headline and subscript
consonants (್ತ ್ರ ್ದ) hang far below. Positioning by bounding box means each
line shifts by a different amount depending on which matras it happens to
contain — so a headline's lines are never on a grid, and a line that happens to
carry a tall matra gets clipped.

**If you undo it.** Baselines wobble line to line, and clipping returns on any
line containing ೀ or ್ರ.

`brand/typo.py :: draw_block, _draw_line`

---

## D3 · Tracking is ignored on Kannada

**Decided.** Letter-spacing applies to Latin only; Kannada strings silently
ignore it.

**Why.** Tracking requires drawing glyph by glyph, which destroys the shaping
raqm performs. ಸುದ್ದಿ becomes ಸು ದ ್ ದಿ — four disconnected glyphs instead of
one conjunct.

**Related bug this caused once.** Tracking was passed as pixels in one place and
as an em fraction in another, so `CRIME` rendered as `C  R  I  M  E`. Tracking
is an **em fraction** everywhere. Do not multiply it by the size at the call site.

`brand/typo.py :: _draw_line, text_width`

---

## D4 · Latin faces fall back to Kannada automatically

**Decided.** Any Latin face given user copy goes through `typo.font_for()`.

**Why.** SF and Georgia have no Kannada coverage. A footer set in SF with a
Kannada strapline rendered as `▓▓▓▓ • ▓▓▓▓` — visible in the carousel's closing
slide before it was caught. You cannot know in advance whether a location name
or strapline will arrive in Kannada or Latin.

**If you undo it.** Tofu boxes, appearing only for the strings that happen to be
Kannada, so it will pass a casual review.

`brand/typo.py :: font_for`

---

## D5 · A photograph fades its own alpha; it is never painted over

**Decided.** `place_photo(fade_bottom=…)` ramps the image's alpha to zero.

**Replaced.** A dark scrim painted on top of the picture.

**Why.** A veil is one particular colour. The page beneath is a gradient with a
radial glow on it. The two will always mismatch by a shade, leaving a faint
band exactly where you were trying to hide the join. An alpha fade lets whatever
is underneath come through, so there is no join to find.

**If you undo it.** A visible horizontal seam across every card with a photo —
the single most recognisable amateur tell in the original output.

`brand/surface.py :: place_photo`

---

## D6 · The scrim ramp is a smoothstep, not a power curve

**Decided.** `alpha = smoothstep(t ** (curve/2))`.

**Replaced.** `alpha = t ** curve`.

**Why.** A power curve saves all of its darkening for the last few percent. At
the point where the type begins, the picture was still ~25% visible, and then it
snapped shut over the remaining 40px. Smoothstep is flat at both ends:
imperceptible where it starts, already solid a little before it finishes.

`brand/surface.py :: scrim`

---

## D7 · Crop focal point defaults to (0.5, 0.42), not centre

**Decided.** Vertical focal default is 0.42.

**Why.** In news photography the subject's face and the action sit above the
frame's centre. A naive centre crop decapitates people.

`brand/surface.py :: cover`

---

## D8 · Grain is mandatory

**Decided.** Every template ends with `grain(sf, Grade.grain, Grade.grain_shadow_bias)`,
biased 0.6 toward the shadows.

**Why.** Flat digital black is the cheapest-looking thing on a phone screen,
especially OLED. Film grain is the difference between "rendered" and "printed".
It is also what stops long gradients from banding.

**If you undo it.** Everything looks like a slide deck.

---

## D9 · Category colour lives only on the rail

**Decided.** Gold appears on every card and is the only accent that does.
Category colour is confined to a 5 px vertical rail beside the kicker.

**Replaced.** Tinting the whole card per category — red card for crime, amber
for weather.

**Why.** A feed is seen as a strip, not as single posts. Eleven category colours
across a grid of nine thumbnails reads as nine different publications. One
constant accent is what makes them read as one.

**If you undo it.** The channel loses its identity in the grid view, which is
where most people actually see it.

`brand/tokens.py :: CATEGORIES, Role.accent`

---

## D10 · Hairlines, square corners, no canvas border

**Decided.** 1 px rules at alpha 0.14. `Grid.radius = 0`. Nothing draws a frame
around the canvas.

**Replaced.** Outlined rounded boxes for the kicker, headline, body and two meta
pills — five stacked containers per card — inside a gold rule around the whole
canvas.

**Why.** Boxes are what you reach for when you do not trust the spacing. Every
one of them competes for attention and none of them is information. A border
around the canvas is the clearest single signal of amateur work.

---

## D11 · Layouts flow content; they never position it

**Decided.** Every template measures the copy first, then decides the
composition. A short headline earns a bigger photograph.

**Why.** News copy varies wildly in length. Fixed positions mean a short story
leaves a dead gap above the footer and a long one overflows into it — both
happened in the first pass. Flowing means the same template looks designed at
40 characters and at 140.

**Corollary — the drop-priority.** When a card cannot hold everything it cuts in
the order a sub-editor would: advisory, then standfirst, then facts from the
bottom. The headline is never cut.

**The exception (D11a).** On `weather`, `health`, `civic` and `breaking` the
order inverts around the advisory: facts are cut first and the advisory
survives. A helpline number matters more to a reader in the rain than the third
supporting fact. Found by rendering a storm alert and noticing the emergency
number had been dropped to make room for a fact.

`templates/report_card.py :: _variants, ALERT_CATEGORIES`

---

## D12 · Item gaps must clearly exceed line gaps

**Decided.** Fact lists use a 34 px item gap against roughly 10 px between lines
within an item.

**Why.** Grouping is read from relative distance. Get the ratio backwards — as
the first version did — and a two-line fact reads as two facts. This is the same
bug as D1 seen from the other end, and both had to be fixed for the list to read
correctly.

---

## D13 · Reels are full-bleed, not a photo band plus a text band

**Decided.** The picture fills the 9:16 frame and the type sits over its lower
half on a scrim.

**Replaced.** A photograph occupying the top ~55% with text below it.

**Why.** The band layout letterboxes the picture and leaves the headline too
small to read at arm's length — which is the only distance a reel is ever
watched from. Broadcast does the opposite for exactly this reason.

`brand/motion.py :: StoryScene`

---

## D14 · A reel scene carries a headline and one supporting line

**Decided.** Not three bullet points.

**Why.** Scene length is ~6 s. Nobody reads three Kannada bullets in six
seconds, and shrinking the type to fit them makes the headline unreadable too.

---

## D15 · Scene duration follows reading time

**Decided.** `reading_seconds()` at 11 Kannada characters/second, floored at
3.2 s, capped at 11 s.

**Replaced.** Fixed 8.5 s slots.

**Why.** Fixed slots either bore the viewer on a short headline or cut them off
mid-sentence on a long one.

`brand/motion.py :: plan_durations`

---

## D16 · Nothing cuts on

**Decided.** Every element arrives on an eased curve (`out_quint`) with a ~30 px
rise and a 0.075 s per-line stagger.

**Why.** Hard-appearing text is the loudest single signal that a video was
assembled by a script rather than edited.

---

## D17 · Audio is normalised to −14 LUFS / −1.5 dBTP

**Decided.** `loudnorm=I=-14:TP=-1.5:LRA=9` then a limiter with auto-level
compensation **disabled**.

**Why.** Both Instagram and YouTube normalise to about −14 LUFS. Delivering
hotter means the platform turns it down, and loud material turned down sounds
flat. The limiter's auto-level compensation was pushing true peak back over the
ceiling until it was switched off.

`brand/motion.py :: _master_audio`

---

## D18 · Safe zones are structural, not advisory

**Decided.** Reel content stays within 72 / 230 / 220 / 480. The band below is
given the handle and tagline rather than left black.

**Why.** Instagram parks its action rail over the right 200 px and its caption
block over the bottom ~470 px. Anything there is decoration. But the band is
visible on a paused reel, in WhatsApp status, and wherever the video is
reposted — so it carries the brand instead of being wasted.

---

## D19 · Genuineness is enforced in the type system, not the style guide

**Decided.** `Story.validate()` raises rather than rendering an uncredited
photograph, an unsourced story, or a "BREAKING" flag on stale news. There is no
override flag.

**Replaced.** A written rule in the guidelines.

**Why.** The original output illustrated a Brahmāvara double murder with a sunny
highway bridge whose signage reads HONNAVAR — a different town — with no credit,
no source and no label. The guideline existed. It did not help.

**If you add an override flag.** It will be used on a deadline, and then this
whole system is decoration.

`brand/content.py :: Story.validate`

---

## D20 · Latin numerals, and never both

**Decided.** 25, 1077, 40-50 — not ೨೫. Mixing the two systems on one card is a
preflight **failure**, not a warning.

**Why.** This is what Kannada print and broadcast actually use for figures. The
first pass mixed them — Kannada digits in the body, Latin in the masthead — and
it reads as a mistake because it is one.

`brand/qa.py :: preflight`

---

## D21 · Everything renders at 2× and downsamples once

**Decided.** `Surface(w, h, ss=2)`; layout code speaks in final delivery pixels.
JPEG is written at q95 with **4:4:4** chroma.

**Why.** Kannada matras are thin diagonal strokes; at 1× they alias visibly.
Default 4:2:0 chroma subsampling turns coloured type on the red rail to mush.

---

## D22 · The clock is injectable

**Decided.** Everything time-dependent goes through `content.now()`, freezable
via `freeze()`, the `frozen()` context manager, `OORMANI_NOW`, or `--at`.

**Why.** Two things depend on wall-clock time — whether a story is still
breaking, and the default publish timestamp. Both would otherwise make identical
content render differently on different days, which makes the golden tests
impossible and "same content, same design" untrue.

`brand/content.py :: now, freeze, frozen`

---

## D23 · Golden tests render a frozen fixture, never a live edition

**Decided.** `tests/test_golden.py` renders `tests/fixture_edition.json`, which
never changes.

**Replaced.** Rendering `editions/2026-08-25.json`.

**Why.** Caught within an hour of the system being used for real: a genuine
day's edition was written into `editions/2026-08-25.json`, and all twelve golden
hashes failed at once. Nothing was wrong with the design — the test was pinned
to a file whose whole purpose is to change daily.

**If you undo it.** The golden test fails every time real news is added, which
trains everyone to re-bless without looking. A golden test nobody reads is worse
than no golden test.

`tests/test_golden.py :: EDITION`

---

## D24 · Translucent text goes through its own layer

**Decided.** `typo` routes any fill with alpha < 255 onto a transparent layer
and alpha-composites it.

**Why.** PIL's `ImageDraw` REPLACES the target pixel at the glyph core rather
than blending — including the alpha channel. Text drawn straight onto the
canvas with a 10%-alpha fill writes `(r, g, b, 26)` into an otherwise opaque
image, and the final `.convert('RGB')` then discards that 26 and keeps the
colour at FULL strength. Every "faint" thing in the system — captions, the
oversized quote mark, the ghost category word on a plate — was rendering at
full opacity.

**How to spot it again.** Anything you set below ~20% alpha that comes out
looking solid.

`brand/typo.py :: _needs_layer, _composite_lines`

---

## D25 · Every post and every slide carries a visual

**Decided.** A story with no honest photograph gets an **editorial plate** —
the logo's horizon reduced to geometry: a ruled sea, a gold sun on the horizon
line, a category-tinted sky. `report_card` draws one instead of a photo, and
`choose()` now returns `report_card` for stories with no picture. Carousel
slides do the same. The credit line reads ಗ್ರಾಫಿಕ್ಸ್.

**Replaced.** Bare typographic cards, and carousel slides that were pictures
for some stories and plain type for others.

**Why.** A feed where some posts have images and others do not reads as an
unfinished set. But the answer to "no picture" is never a stock photo dressed
as reporting — so the plate is *visibly* a graphic and says so.

**The version that was rejected.** A soft photographic sunset with a blurred
sun and shimmering water. It read as a bad photograph rather than a designed
plate, which is exactly the failure being avoided.

**Aspect matters.** The horizon rides with the box: 0.34 on a 9:16 frame, 0.54
on a wide band. At a fixed mid-height it landed directly under the reel
headline.

`brand/surface.py :: editorial_plate`

---

## D26 · Reel timing is honest about Kannada reading speed

**Decided.** `read_rate` 11 → **7.0 characters/second**. Scene time =
`build_in 1.4 + reading + settle 0.8`, floored at 5 s. `target_seconds` is a
**ceiling, not a quota**: scenes are never compressed below reading speed, and
stories are dropped from the end instead.

**Replaced.** 11 chars/sec, a 3.2 s floor, and `k = body / sum(holds)` scaling
every scene to hit the target exactly.

**Why.** A viewer reported he could not read the text. Measured: four stories
in 30 s gave 6.3 s a scene, while the headline plus its supporting line needed
**25–30 s**. Roughly four times too fast. Kannada is an abugida — one akshara
carries a consonant, its vowel and often a conjunct — so a 70-character
headline is ~40 aksharas, and a first read on moving video runs about 3–4
aksharas a second.

**Also decided: less text.** A reel scene shows the headline and nothing else;
a supporting line appears only when the headline needs under 5 s, and is capped
at 62 characters. Both together were the bulk of the problem.

**And a shorter headline.** `Story.reel_line` (~45 chars) is a video headline.
A print headline of 75 characters needs ~11 s of screen time on its own.
Without a `reel_line` the reel still works — it just runs long, and preflight
says so.

`brand/tokens.py :: Motion` · `brand/motion.py :: scene_seconds, plan_durations`

---

## D27 · Standing copy lives in tokens, not in templates

**Decided.** `tokens.Brand` holds the name, tagline, handle, coverage line,
bulletin name and the standing CTA strings.

**Why.** The coverage line was written out as `'ಬೈಂದೂರು • ಕುಂದಾಪುರ • ಉಡುಪಿ'` in
five separate template files, with a sixth variant in the reel outro that also
appended `ಕರಾವಳಿ`. Changing it meant finding all six. It is now one word —
**ಕರಾವಳಿ** — in one place: a list of towns dates itself the moment you cover
somewhere that is not on it.

---

## D28 · Never seed anything from `hash()`

**Decided.** `editorial_plate` seeds its per-story variation from
`zlib.crc32(seed)`.

**Replaced.** `abs(hash(seed))`.

**Why.** Python randomises string hashing per process, so the plate drew a
different sun position and sea offset on every run. The golden test failed
immediately after being blessed — which is the test doing its job: the
"design" was not actually reproducible.

**The general rule.** Anything that must render identically twice takes its
randomness from a stable digest, never from `hash()`, `id()`, `set` ordering or
`dict` ordering across processes.

`brand/surface.py :: editorial_plate`

---

## D29 · Brand rules are gilded, not stamped

**Decided.** The masthead rule, the horizon line, the takeaway rail and the
footer hairline are gradient rules whose alpha tapers to nothing at both ends
(`gilded_rule`, `gilded_vrule`, `faded_rule` in `surface.py`).

**Replaced.** Flat one-colour hairlines at a fixed alpha, spanning margin to
margin.

**Why.** A flat rule at full span has two hard endpoints, and the eye finds
them — it reads as a divider drawn by software. A rule that brightens slightly
toward its centre (gold_400) and dissolves at the ends reads as engraved: the
same hairline, the same single accent, but machined instead of stamped. This
is the premium move that costs no new device — no border, no box, no second
colour.

`brand/surface.py :: gilded_rule / gilded_vrule / faded_rule`,
`brand/components.py :: masthead / footer / takeaway / horizon`

---

## D30 · The house grade gets a filmic highlight shoulder

**Decided.** `house_grade` compresses luminance above the 0.82 knee with an
asymptotic shoulder (`Grade.rolloff = 0.18`); split-tone amounts were raised
a notch (shadow 0.20→0.22, highlight 0.12→0.14). Surface grain is now
two-frequency: the fine emulsion layer plus a soft coarse layer at 15%.

**Why.** The S-curve protects the ends but everything above the knee still
travelled linearly to 1.0, so skies and highlights flattened into the same
digital white. Film compresses its shoulder — most of why graded film looks
expensive and phone output looks cheap. And uniform single-frequency noise
reads as static; layered noise reads as emulsion.

`brand/tokens.py :: Grade`, `brand/surface.py :: house_grade / grain`

---

## D31 · The editorial plate is a scene, not a backdrop

**Decided.** The plate's gradients are dithered; the sun carries a broken gold
reflection down the sea; the ruled-sea spacing opens at 1.33× per line with
eased alpha; the sun glow is softer and slightly larger.

**Why.** The plate exists for stories with no honest photograph, so it must be
visibly a graphic — but visibly a *designed* one. The reflection is the one
move that makes the geometry read as a scene at dusk rather than as a banner:
light on water is the single most recognisable image of this coast.
Undithered, the sky banded exactly where the eye goes — the horizon.

`brand/surface.py :: editorial_plate`

---

## D29 · Legal guards are validation rules, not guidance

**Decided.** `Story.validate()` refuses to render:

* a **crime** story whose copy asserts guilt with no allegation marker, unless
  `convicted=True` — BNS §356 (defamation) and contempt once sub judice. The
  `headline` and the `reel_line` are additionally checked **on their own**, not
  as part of the joined copy: both are displayed alone — a thumbnail, a
  WhatsApp forward, a screenshot, a reel scene — so a qualifier sitting in the
  deck or in the third bullet never reaches the reader who only sees the
  headline. Checking the concatenation let the channel's own sample headline
  through on the strength of an ಆರೋಪಿ in the deck below it, which is exactly
  the publication this guard exists to prevent;
* identifying detail on a story flagged `involves_minor` — JJ Act 2015 §74;
* identifying detail, an actual-scene photograph, or a granular location on a
  story flagged `sexual_offence` — POCSO §23, BNS §72.

**Replaced.** Nothing. There was no guard at all, and the channel's own sample
copy read <span>"ಹೆತ್ತವರನ್ನೇ ಕೊಂದ ಪುತ್ರ"</span> — "the son *who killed* his
parents" — about a person arrested and not convicted.

**Why a validation rule and not a style note.** The same reason as D19: a
guideline that can be waived on a deadline is a guideline that gets waived on a
deadline, and the cost here is an offence rather than an ugly card.

**Deliberately blunt.** `_looks_like_name` flags any `(nn)` age pattern. On a
story involving a minor, a false positive costs a rewrite and a false negative
costs a prosecution, so it errs toward blocking.

`brand/content.py :: _check_criminal_reporting`

---

## D30 · A credit is not a licence

**Decided.** `Photo.licence` is required and must be one of a fixed set;
`source_url` is required unless the licence is `own`.

**Why.** Every photograph was credited <span>"ಊರ್ಮನಿ ಸುದ್ದಿ ಸಂಗ್ರಹ"</span> —
which *asserts the channel owns it* — with no licence recorded anywhere and no
EXIF on any file. If any of those were not the channel's, that is a false
attribution on top of an infringement. Crediting a picture and having the right
to publish it are different things, and only one of them was being tracked.

`brand/content.py :: Photo.validate, LICENCES`

---

## D31 · The system emits copy, not just artwork

**Decided.** `brand/copy.py` generates the Instagram caption, hashtags, alt
text, WhatsApp forward, X post, and YouTube title/description/tags. `render.py`
writes a `.txt` to paste from and a `.json` for a scheduler next to every
render.

**Replaced.** Nothing — there was no caption, no hashtags, no title, no
description and no alt text anywhere in the system.

**Why.** The design bottleneck was solved and the copy bottleneck was
untouched, so every finished card still needed a human to write words before it
could be posted. On both platforms the copy is most of what drives discovery:
Instagram has indexed caption text for keyword search since 2024, and YouTube
ranks largely on title and description.

**Design notes.** The first line is capped at 125 characters because that is
Instagram's fold — it has to earn the tap alone. Hashtags are ordered by
specificity (place → category → brand) so trimming the list removes the least
useful first. When a caption would exceed 2,200 characters the *facts* are
trimmed, never the sourcing.

`brand/copy.py`

---

## D32 · A vertical clip under 60s is a Short, and Shorts have no thumbnail

**Decided.** Added `templates/bulletin.py` — the same motion engine at 16:9,
with the type laid out as a broadcast lower-third instead of a full-height
column.

**Why.** The channel was rendering a carefully engineered 1280×720 thumbnail
for a long-form video that did not exist. Its only video output was a sub-60s
9:16 clip, which YouTube treats as a Short — and Shorts pull a frame rather
than take a custom thumbnail. So the best-engineered artefact in the set was
unusable, and the realistic monetisation route (1,000 subscribers + 4,000 watch
hours) was closed, leaving only the Shorts route at 10M views per 90 days.

**Implementation note.** `StoryScene` now branches on aspect rather than being
duplicated: portrait keeps the platform safe zones and the brand band,
landscape drops both and sets the headline to a 62% column.

`templates/bulletin.py` · `brand/motion.py :: StoryScene`

---

## D33 · The opening frame is the cover

**Decided.** The brand sting opens bright — gold glow, horizon, logo already at
55% opacity on frame 0 — and the reel encodes at CRF 16 / 12 Mbps ceiling.

**Why.** Frame 0 measured **13/255** mean luminance: a near-black square in the
profile grid and as the default reel cover, which reads as a dead post. And at
3.1 Mbps the source being re-encoded by the platform was itself the limit.

---

## D34 · Landscape is a different typographic problem, not a resize

**Decided.** In a 16:9 frame the motion engine sets a landscape type scale
(`ts = 1.38`), a 66% headline column, a headline up to 96px, and the plate's
sun pushed to x≈0.70 with the category word in the upper left.

**Why the type scale.** The whole system is calibrated for a 1080-**wide**
portrait frame. Most YouTube viewing is on a phone, where a 1920×1080 video
plays about 400px wide — so a 19px source line lands at roughly **4px** and is
simply gone. The first landscape cut looked fine on a laptop and was unreadable
at the size people actually watch.

**Why the plate is recomposed.** At the portrait geometry a 16:9 plate left the
top two-thirds and the right third of the frame empty: the horizon sat under the
headline, the sun sat behind the text, and there was nothing to look at. The sun
now counterweights the left-aligned headline and the category word occupies the
sky that would otherwise be dead.

**Also:** landscape has no platform chrome, so the masthead sits at `st_ - 24`
rather than `st_ - 118`. At the portrait offset it rendered off the top of the
frame — a bug visible in the first bulletin render.

`brand/motion.py :: StoryScene` · `brand/surface.py :: editorial_plate`

---

## D35 · The progress bar is flush to the top edge

**Decided.** `_progress_bar` draws at `y=0`, 4px.

**Why.** It used to sit at `y=58`. In a 9:16 frame the masthead is at y≈112
(below Instagram's chrome strip) so there was clearance. Landscape has no
chrome to clear, so its masthead sits at y≈48 — and the gold bar was drawn
**straight through the logo**. Flush to the edge is safe at every aspect and is
what broadcast does anyway.

**The general lesson.** Any element positioned by a constant rather than
relative to what it must clear will collide the first time the layout changes
aspect. Two elements were placed this way; both broke on the first 16:9 render.

---

## D36 · A lower-third is a panel, not a gradient

**Decided.** In landscape the picture stops at 0.47H and a near-solid panel
begins, with a light hairline above it and a 3px gold rule on its top edge.
Content is measured from `panel_top + 44`; the supporting line is capped to a
single line; the photo credit sits on the picture, above the panel.

**Replaced.** A scrim over the photograph with the type on top.

**Why.** However dark you make a veil, a headline over a coastal photograph is
still sitting on rocks and surf, and it never looks clean. Broadcast solves it
by stopping the picture: the type gets its own ground and the defined edge is
most of what reads as *produced* rather than *overlaid*.

**The bug this exposed.** `head_room` was measured from near the top of the
frame, so `fit` chose a headline sized for space the panel did not have; the
block was then bottom-anchored and overran the meta row. A clamp pushed it
down and made it worse. The fix was to measure the region the block can
actually occupy — `panel_top + 44` to `block_bottom` — and let `fit` work
inside it. Arithmetic checked before rendering, not after.

`brand/motion.py :: StoryScene._over, _sprites`

---

## D37 · The bulletin carries the deck, and its length is derived

**Decided.** The 16:9 bulletin is driven by `motion.BULLETIN`, not
`motion.REEL`. A bulletin scene shows the **print headline and the deck** —
the carousel's payload — and may run to 30s instead of 12s. Its total length
is whatever that copy honestly takes: 84s and 97s on the two real editions.
`plan_bulletin()` promotes facts into the body only while the total is still
under a 60s floor, and if even that leaves it short it stays short and says so.

**Replaced.** The bulletin rendered the reel at a different aspect ratio: the
same one-line `reel_line`, the same 12s ceiling, and in landscape only *one*
supporting line (D36) instead of the reel's two. It ran 43s.

**Why.** A reel and a bulletin are different viewing contracts. A reel is a
glance in a vertical feed, where 12s is right because past that the viewer has
already swiped. A bulletin was opened on purpose on YouTube, where watch time
is the product. Serving the reel's copy into a 16:9 frame produced a video
that was simultaneously too thin to be worth watching and — at 43s — a Short,
which YouTube gives its own pulled frame rather than the custom thumbnail the
system had been carefully rendering all along.

So the fix was not to slow the reel down or pad it out. It was to give the
bulletin the information the carousel already had. The length then falls out
of the content, which is what "1-2 minutes" should mean: not a target the
engine pads to, but the honest reading time of a day's news.

**Why not just raise `hold_max`.** That stretches the same one line over more
seconds. The viewer finishes reading in 7s and stares at it for 25.

**The floor is not a quota.** 60s is where YouTube stops treating a video as a
Short. A thin edition that cannot reach it is reported, never inflated — the
same rule as D29's refusal of an override flag and D-reel's refusal to
compress below reading speed. Padding a bulletin would be lying about how much
news there was that day.

`brand/motion.py :: Pace, head_line, body_line, plan_bulletin`
`brand/tokens.py :: Motion.bulletin_*` · `templates/bulletin.py`


---

## D38 · Landscape spends width on the type, not height

**Decided.** In a 16:9 frame the type sits in a **full-height column on the
left 46%**, and the photograph occupies the right 54% at full height, cropped
to that near-square region. The seam is a hard edge with a gold rule. Masthead,
date, time and the photo credit all live in the column; only the handle sits on
the picture, over a shallow foot veil.

**Replaced.** D36's lower-third, applied to landscape: a full-width panel from
0.470H down, with the photograph laid full-bleed behind it.

**Why.** D36 is right about portrait and right about *why* — the type needs its
own ground, and a defined edge is what reads as produced. But a "lower third"
that starts at 0.470H is not a lower third, it is a half-and-half split, and in
landscape it cost the picture its middle. A 4:3 source cropped to 16:9 and then
half-covered kept about **37%** of itself, and the covered half is where the
subject almost always is: on the Manipal registration photograph the panel
began exactly at the counter, so the frame kept the ceiling and the signboard
and threw away every person in it. Cropping the same source to the right-hand
column instead keeps about **75%**, at full height, so people stay whole.

The deeper point is that a 16:9 frame's surplus is **width**, not height.
Spending height on furniture is spending the scarce dimension. Portrait is the
other way round, which is why it keeps the lower-third and this is landscape-only.

**Tried first, and rejected.** Sizing the panel to its type instead of a
constant. It moved the panel from 47% to 51% — the block is genuinely that
tall — so the picture was still cut in half. The geometry was wrong, not the
constant.

**The bug this exposed.** `block_h` was computed as `44 + 34 + …` while
`_sprites()` advanced by `eb_h + 34 * ts`. Those agree only at `ts == 1.0`, so
in landscape (`ts = 1.38`) the block ran ~60px lower than its own measurement
claimed. Nothing had depended on that number in landscape before, so it had
never shown; the moment the photo credit was positioned from it, the credit
landed on top of the deck. Measure with the same steps you draw with.

`brand/motion.py :: StoryScene._over, _measure` · `brand/tokens.py :: Motion.panel_width`

---

## Changing something here

If you are about to change a value in `brand/tokens.py`:

1. Find its entry above. If there isn't one, add it after you decide.
2. Run `python3 -m pytest tests/ -q`. Golden failures are expected when the
   design genuinely changes — look at the diff images before accepting them.
3. Re-render the reference set and look at it: `python3 examples/make_examples.py`.
4. Update [`../STANDARDS.md`](../STANDARDS.md) if the rule changed, not just the value.
