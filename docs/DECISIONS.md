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

## D39 · A reel is the lead story, and it opens on the news

**Decided.** The 9:16 reel is the **lead story only**, with **no brand sting**.
It opens on the photograph and the `reel_line`. A 1.8s outro still carries the
follow CTA. `reel_cover.jpg` is written from the first story once the headline
has arrived — that file is the Instagram / Shorts cover. Captions open on the
story hook (place + news), not the date; hashtags are 8 hyperlocal tags, not
12 mega-tags; YouTube titles do not append `#Shorts`.

**Replaced.** A 30s four-story dump that opened on a 1.9s logo sting, with
edition copy that led "28 ಆಗಸ್ಟ್ · ಕರಾವಳಿ ಬುಲೆಟಿನ್" and a `#Shorts` suffix
on every YouTube title.

**Why.** After two weeks of posting, reach was weak for reasons the design
system was manufacturing:

1. **The first three seconds.** Instagram and YouTube both decide whether to
   distribute a clip in the first 1–3 seconds of watch. A logo sting is a
   scroll cue — the viewer has not yet been told there is news. D33 made the
   sting *bright* so it would not look like a dead tile; it did not make it
   *worth watching*. The masthead already brands every scene.
2. **Four stories in 30s is a slideshow.** Retention, not impression count, is
   what the platforms then amplify. A 12–18s single-story reel watched to the
   end beats a 30s four-headline dump abandoned at 40%. The carousel and the
   16:9 bulletin already carry the rest of the edition; the reel does not have
   to.
3. **Copy was a date stamp.** Instagram indexes the first ~125 characters for
   search. Opening on the date and the word "bulletin" matches nothing anyone
   types. Opening on `ಉಡುಪಿ: ಕರಾವಳಿಗೆ ಆರೆಂಜ್ ಅಲರ್ಟ್` matches the people the
   story is for. Mega-tags (`#Karnataka`, `#BreakingNews`) put a new account
   in a pool it cannot win; eight place-first tags put it in front of the
   district.
4. **`#Shorts` in the title.** YouTube classifies Shorts by aspect ratio and
   duration. The hashtag wastes the ~60 characters a search result actually
   shows, and reads as spam.

The 16:9 bulletin is unchanged: it still opens on the sting, still carries
every story, still has to clear 60s so YouTube will use `yt_thumbnail.jpg`.

`brand/motion.py :: render_reel` · `brand/copy.py` · `brand/tokens.py :: Motion.reel_intro, reel_outro`

---

## D40 · The 4K bulletin is the same design at twice the size, not a bigger canvas

`bulletin_4k` was added as a 3840×2160 format and shipped without ever being
rendered. It could not be: `page_base` asks for a glow 1.15× the frame width,
`radial_glow` allocated a square of that DIAMETER regardless of the canvas, and
at 3840 that is 17664² — which Pillow refuses outright as a decompression bomb.
The 16:9 YouTube cut, the only output on the realistic monetisation path
(1,000 subs + 4,000 watch hours), therefore produced nothing at all.

Two things were wrong and both are fixed:

1. **`radial_glow` now builds only the part of the bloom that lands on the
   canvas.** The falloff is still measured from the true centre and radius, so
   on-canvas pixels are identical — verified byte-for-byte across all eleven
   stills before the change was kept. It is computed in float64 as before: in
   float32 a scattering of pixels crosses a rounding boundary on the way to
   uint8, which is invisible to the eye and still a different golden hash.

2. **The layout is resolution-independent.** `StoryScene.fs` is the frame scale
   — 1.0 for a 1080-wide portrait frame and a 1920-wide landscape one — and
   every fixed measure is multiplied by it. Without this a 3840-wide render kept
   1920-sized type: the column came out two-thirds empty and the headline read
   at half its intended size. A 4K frame is now indistinguishable from the 1080p
   one at the same display size, because it is the same design.

A format that is already at twice the delivery resolution renders at `ss=1`
rather than composing on a further 2× canvas — a 4× pixel bill for antialiasing
no one can resolve. `render_reel` takes the supersample from the format instead
of hard-coding 2, and `bulletin` declares the `ss=2` it was always getting.

An 82s four-story bulletin renders in about 7 minutes at 3840×2160 and masters
to −14.8 LUFS / −1.4 dBTP. The reason to deliver 2160p rather than 1080p is not
the pixel count on a phone: it is that YouTube encodes 1440p and above with VP9,
and this design is very dark — flat ink and slow gradients are exactly where
1080p H.264 bands.

`brand/surface.py :: radial_glow` · `brand/motion.py :: StoryScene, render_reel`
· `brand/tokens.py :: FORMATS`

---

## D41 · The thumbnail hook is guarded like a headline, and set like one

Two separate failures in the same file.

**The hook was not checked.** `Story.validate()` refuses a crime headline that
states guilt before conviction, and the comment in `content.py` explaining why
names "a thumbnail" as the first place a headline travels alone. But
`youtube_thumb(hook=…)` *replaces* the headline on exactly that thumbnail, and
`hook` is not a Story field, so validate() never saw it. A careful headline plus
a punchy `--hook` under deadline defeated the whole guard. The check now runs in
the template on the same terms, with no flag to turn it off — the same reasoning
as D29. `tests/test_contract.py` pins it.

**The hook was set too small to read.** A rewrite had laid the photo full-bleed,
set the hook on ONE line shrunk to fit, and put the deck beneath it. In a feed a
thumbnail is about 210px wide: the deck was gone entirely and a long hook had
shrunk to roughly 40px — about 6px on screen. The 7-word legibility warning had
been deleted along with it.

The thumbnail is now built in the same frame language as the bulletin it fronts:
ink column left, photograph full-height right, gold seam between. The type sits
on solid ground rather than on picture detail, so it is legible by construction
instead of by luck with a particular photograph — and the thumbnail and the
video's own frames are recognisably the same publication. The hook is capped at
three lines and floored at 76px; below that the fix is a shorter hook, not
smaller type, and the word warning says so.

`templates/youtube_thumb.py` · `brand/components.py :: eyebrow(show_location=)`

---

## D42 · Kannada case markers agglutinate, and the ones we generate are checked

The first comment on every weather post read **"ಉಡುಪಿ ನಲ್ಲಿ ಈಗ ಹೇಗಿದೆ?"**. In
Kannada a case marker is a bound morpheme — it attaches to the noun and pulls a
linking stem with it. Written as a free-standing word it is "Udupi in": not a
typo, a grammatical error, on the copy that is supposed to start a conversation
with local readers. The default first comment had the same fault with ನಿಂದ.

`copy.locative()` and `copy.belonging()` now form these properly. The linking
stem follows the noun's final vowel and the same three stems serve every suffix:

| ends | stem | example |
|---|---|---|
| ಿ ೀ ೆ ೇ ೈ | + ಯ | ಉಡುಪಿ → ಉಡುಪಿಯಲ್ಲಿ |
| ು ೂ | + ಿನ (replacing the ು) | ಮಂಗಳೂರು → ಮಂಗಳೂರಿನಲ್ಲಿ |
| ಾ, or a bare consonant with inherent 'a' | + ದ | ಕುಂದಾಪುರ → ಕುಂದಾಪುರದಲ್ಲಿ |

Only the last word of a place inflects — ಉಡುಪಿ **ಜಿಲ್ಲೆಯಲ್ಲಿ**, not
ಉಡುಪಿಯಲ್ಲಿ ಜಿಲ್ಲೆ.

**Anything it cannot analyse returns `''` and the caller rephrases** to a
sentence that needs no case marker. Inventing morphology for an unrecognised
place would put broken Kannada in front of readers, which is worse than a
plainer sentence — the same instinct as omitting `photo` rather than reaching
for a stock image. `tests/test_contract.py` checks every place in `PLACE_TAGS`
across three categories and asserts no stranded suffix survives.

## D43 · The publishing plan is rendered, not retyped

AGENTS.md has listed a scheduled timetable as a required deliverable since the
workflow was written, and nothing produced one — so it was retyped by hand every
morning. That is how the times drift, how a reel gets published without its
cover set, and how the first comment gets forgotten.

`render.py` now writes `schedule.txt` and `schedule.json` from **what it
actually rendered**, so the plan can never list a reel that does not exist. Two
rules carry the reasoning:

* **Reels are spaced ≥2.5h.** Two of ours in one window compete with each other
  rather than with anyone else. The rule is a constant, and a test enforces it —
  it caught the first slot table, which claimed 2.5h and shipped 19:00/21:00.
* **The long-form bulletin goes up first.** It is the only asset on the
  4,000-watch-hour path; Shorts do not count toward it. Posting it at 08:30
  gives it the whole day to accumulate.

The times themselves are **starting positions from the shape of the day on this
coast, not measured truth about this account** — and the file says so, in the
file. Once there is a month of real analytics they should be moved to whatever
those say. A plan written down is a plan that can be corrected.

`brand/copy.py :: locative, belonging, publishing_plan, plan_text` · `render.py`

---

## D44 · A bulletin target drops stories; it never rescales scenes

`plan_bulletin` had grown a block that scaled every hold proportionally to land
exactly on `--bulletin-seconds`. It was wrong in both directions and silent in
both:

| `--bulletin-seconds` | copy needs | it showed |
|---|---|---|
| 60 | 21.5 / 23.1 / 15.9 / 18.8s | 15.5 / 16.6 / 11.5 / 13.5s — every scene cut |
| 120 | the same | 31.8 / 34.1 / 23.5 / 27.7s — every scene padded 65% |

The only guard was `hold_min`, which is a floor on a scene in the abstract and
says nothing about whether *this* scene's copy fits in it. And the short-scene
warning was suppressed whenever a target was set — so the one run that needed
the warning was the one run that could not produce it.

`target` is a ceiling, exactly as `plan_durations` has always documented it:
stories are dropped from the end and nothing is compressed below reading time.
Padding is refused for the same reason a thin edition is reported rather than
stretched (D37). The warning now fires unconditionally.

The path had no test — which is how it survived. It has one now.

`brand/motion.py :: plan_bulletin, render_reel` · `tests/test_contract.py`

---

## D45 · A narrated reel is cut from the speech, never alongside it

A reel with a voiceover used to be timed like this: synthesize one long MP3,
measure its total duration, give the whole story that many seconds, then split
those seconds into equal chapters and hope the picture matched the words.

It did not match. On the 2026-09-07 edition, measured:

| card | appeared at | the voice reached it at | drift |
|---|---|---|---|
| fact 0 | 17.6s | 33.1s | **15.5s** |
| fact 1 | 35.4s | 45.7s | 10.3s |
| fact 2 | 53.2s | 57.3s | 4.1s |
| outro | 71.0s | — the sign-off was spoken at 62.4s, over a fact card | — |

For fifteen seconds the viewer read one fact while hearing another, and the
reel ended with a silent outro because the narration had already finished.

No amount of tuning fixes this, because **a total duration does not contain
the information needed to place a cut**. Only segment boundaries do. So the
narration is now synthesized one BEAT at a time — the lead, each fact, the
advisory, the sign-off — each measured, then concatenated with known gaps.
`brand.voice.card_keys()` and `brand.motion.reel_cards()` are generated from
the same spine, so a story with three facts has five cards and five beats,
always, and the timeline becomes arithmetic on the audio:

    scene i starts at  segment[i].start - vo_lead
    scene i runs for   segment[i].span + scene_cross

There is no second clock, so there is nothing to drift against. The cut falls
inside `vo_gap`, the silence between two sentences — which is also why a
transition can no longer clip a syllable.

Two constraints ride on top. A card is never shorter than its Kannada takes to
READ (`reel_min_spans` is passed to the voice engine as a floor, because TTS
reads Kannada far faster than a viewer meeting the sentence for the first
time); and that stretching is capped at `vo_hold_max`, because uncapped it
asked for 6.6s of held picture and silence mid-reel, which reads as the video
having stalled. Past the cap the honest diagnosis is that the card says more
than the voice does, and it is reported rather than absorbed.

Because the claim is checkable, it is checked: `audit_sync()` scans the
finished narration for its real silences and requires every cut to fall inside
one. All 13 cuts across the three reels of that edition pass.

`brand/voice.py :: synthesize_track` · `brand/motion.py :: _render_narrated_reel, audit_sync`

---

## D46 · A glyph the face does not carry is a rendering fault, caught in the type engine

Every published reel carried an empty box. The chapter badges were written
`"▪ ಬ್ರೇಕಿಂಗ್ ಮುಖ್ಯಾಂಶ"` and `"⚠ ಸಾರ್ವಜನಿಕ ಎಚ್ಚರಿಕೆ"`, and:

* `▪` is in **none** of the four house faces, and not in SF either.
* `⚠` is in SF only — and a badge containing Kannada is routed to a Kannada
  face by `font_for`, so it never reached SF.

Nothing raised. `.notdef` renders, layout measures it, the file encodes, and
the box is visible only to whoever watches the video afterwards.

A find-and-replace would have fixed those two characters and left the next one
to fail identically, so the guard is in the type engine instead. `typo.safe()`
runs inside `text_width`, `ink_extents` and `_draw_line` — every measurement
and every draw — and is idempotent, so measurement and drawing can never
disagree:

* a **symbol or punctuation** mark the face lacks is substituted from a map
  that only ever targets characters all four faces carry, or dropped;
* a **letter or combining mark** is left alone and reported by `preflight()`,
  because silently dropping one would change what a Kannada sentence says —
  a worse failure than a visible box.

Only whitespace this function itself creates is closed up. The designed double
space either side of the tagline's bullet has to survive, and the first cut of
this collapsed it and moved every still in the house.

The marks themselves are now **drawn**, not typed: `_badge_mark()` renders the
square and the warning triangle with `ImageDraw`. A drawn shape has no font to
be missing from.

`brand/typo.py :: safe, covers, missing_glyphs` · `brand/motion.py :: _badge_mark` · `brand/qa.py :: preflight`

---

## D47 · The fact card is set at news size, and the end card holds a picture

Three faults that all read as "the reel is not finished", fixed together
because they share a cause — scenes drawn to standards that did not match.

**Type.** A fact card was capped at 46px against a 96px headline, so every
card after the first read as a caption. It is now bounded by the space
between the masthead and the meta row rather than by a fixed 340px block, so a
short fact is set BIG instead of small in a half-empty tile. The lines were
also drawn at weight 620 while `fit` had measured them at 600, so long lines
crept past their own measure.

**Seating.** The block hung from its top, so a two-line card and a five-line
card ended in different places and the cards visibly disagreed from scene to
scene. It is seated on the meta row instead.

**The end card.** At 2.4s a near-black panel was survivable. Carrying the
spoken sign-off it runs eight or nine seconds, and nine seconds of dead black
at the end of a video is where the retention graph falls off. It keeps the
story's own photograph behind a deep veil, pushed in slowly.

Also here: the photo credit was given a fixed one-line tile while being
wrapped to the full column width, so a credit long enough to wrap — an AI
label plus a caption is easily 60 characters — had its second line sliced
through the middle by the edge of its own sprite. It is laid out and measured
now. It is an honesty label; one the reader cannot read does not discharge the
obligation it exists for.

`brand/tokens.py :: Motion.reel_card_*` · `brand/motion.py :: ChapterScene, OutroScene, StoryScene._measure`

---

## D48 · Scenes wipe; the music ducks once

**The cut.** Scenes cross-dissolved, which for the whole length of the
transition made the frame a double exposure of two crowds — the single thing
that most made these look generated rather than edited. A wipe shows one
picture or the other at every pixel, which is what a cutting room does. The
old gold "sweep" also washed the entire frame at alpha 190; the wipe carries a
narrow rim on its leading edge instead.

**The bed.** The old filter chained `volume=0.22` across the whole voiceover
and `volume=0.45` at every scene start. ffmpeg applies chained volume filters
**multiplicatively**, so the music dropped to 0.099 at each cut and surfaced
between them — audible pumping against the anchor. It is now one duck level,
one window per spoken beat, so the score sits still under speech and lifts in
the gaps. The whoosh is centred on the wipe, which is possible only because
every cut time is now exactly known.

`brand/motion.py :: _transition, _master_narrated_audio` · `brand/tokens.py :: Motion.bgm_*`

---

## Changing something here

If you are about to change a value in `brand/tokens.py`:

1. Find its entry above. If there isn't one, add it after you decide.
2. Run `python3 -m pytest tests/ -q`. Golden failures are expected when the
   design genuinely changes — look at the diff images before accepting them.
3. Re-render the reference set and look at it: `python3 examples/make_examples.py`.
4. Update [`../STANDARDS.md`](../STANDARDS.md) if the rule changed, not just the value.
