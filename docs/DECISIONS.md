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

## D64 · Brand rules are gilded, not stamped

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

## D65 · The house grade gets a filmic highlight shoulder

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

## D66 · The editorial plate is a scene, not a backdrop

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

## D49 · The disclosure travels with the image, not with the story

`Story.credit_line` read `story.photo` — the hero. That was correct when a
story was one card with one picture. A narrated reel is five or six cards: the
fact cards are drawn from `story.gallery`, and the end card (D47) shows the
hero again. Neither drew a credit at all.

So on a reel whose every image is AI-generated, the label appeared on the
first card and then vanished for the next sixty seconds — over exactly the
frames a viewer actually watches.

`Photo.disclosure` moves the label onto the photograph. `Story.credit_line`
now delegates to it, so the hero and a gallery frame cannot be labelled by two
different rules. `ChapterScene` and `OutroScene` resolve the picture and the
Photo object *together* into `self.shown`, which is what makes it structurally
impossible for a card to label a different image than the one it is showing —
the previous code could fall back to the hero for the picture while leaving
the label blank.

The outro's label sits ABOVE the safe line. Instagram parks its caption over
the bottom ~470px, and a disclosure underneath it is covered on the platform
this reel is mainly made for. A label the viewer cannot see discloses nothing.

`preflight()` now checks every image the story can put on screen, not just the
hero, and fails on any that would appear with no disclosure line.

`brand/content.py :: Photo.disclosure, Story.all_photos` · `brand/motion.py :: ChapterScene, OutroScene` · `brand/qa.py`

---

## D50 · Written Kannada and spoken Kannada are different languages

The delivery was fine. The words were wrong.

A TTS engine handed print copy reads print copy, so the anchor was saying
things no Kannada newsreader would say:

| written | it said | a newsreader says |
|---|---|---|
| `25-35 ಕಿ.ಮೀ` | "25 hyphen 35 ಕಿ dot ಮೀ" | ಗಂಟೆಗೆ 25 **ರಿಂದ** 35 **ಕಿಲೋಮೀಟರ್** |
| `₹1.1 ಲಕ್ಷ` | rupee-sign first, then "1. 1" | 1.1 ಲಕ್ಷ **ರೂಪಾಯಿ** |
| `40%` | "40 percent" | **ಶೇಕಡಾ** 40 |
| `9:15 ಕ್ಕೆ` | "nine colon fifteen" | 9 ಗಂಟೆ 15 **ನಿಮಿಷಕ್ಕೆ** |
| `1,25,000` | digits around commas | 125000 |

`_speech_normalise()` converts each. Two details are load-bearing:

* **A decimal point is not a sentence boundary.** It is protected through the
  whole pipeline and restored last, because the sentence-spacing pass would
  otherwise turn "1.1 ಲಕ್ಷ" into "1. 1 ಲಕ್ಷ" — which an engine reads as two
  numbers and a listener hears as a different amount.
* **A time takes the case its STEM takes.** ಗಂಟೆ ends in ೆ and takes ಗೆ / ಯ;
  ನಿಮಿಷ ends in ಅ and takes ಕ್ಕೆ / ದ. Carrying the written particle across
  unchanged gave "10 ಗಂಟೆಕ್ಕೆ", which is not Kannada. Consuming it
  unconditionally glued the spoken form onto the next word; never consuming it
  doubled it.

A hyphen only becomes ರಿಂದ **between two digits**, so ತ್ರಾಸಿ-ಮರವಂತೆ stays one
place rather than becoming a journey.

`_anchor_cadence()` supplies the performance. edge-tts accepts no SSML, so
every pause has to be written in as punctuation: a beat after the dateline, a
beat either side of an attribution, and a full stop that genuinely lands at the
end of every sentence — which is what produces the falling final intonation.
Without it the engine trails off flat.

**The engine itself changed.** The default was `translate.google.com`'s
undocumented `translate_tts`, time-stretched with `atempo=1.15`. That is a
pronunciation aid, not a broadcast voice, and it is an endpoint that can change
or refuse traffic without notice on a channel that publishes daily.
`kn-IN-SapnaNeural` is a real neural voice that takes direction: +9% rate
(a bulletin's pace; past ~+15% the conjuncts blur), −4Hz pitch (the stock voice
is tagged "Friendly, Positive" — a customer-service register, not a news one),
+8% volume. Measured on the same sentence, it sits at 183Hz against Google's
238Hz: the newsreader register rather than the assistant one, and with no
time-stretch artefacts because it needs no time-stretching.

`brand/voice.py :: _speech_normalise, _anchor_cadence, ANCHOR_RATE, DEFAULT_ENGINE`

---

## D51 · A reel card carries a short form, because the voice is faster than reading

Measured on real copy: the anchor delivers Kannada at roughly **15 characters
per second**. `read_rate` — a cold first read of unfamiliar text on a moving
frame — is **7**. The voice is twice as fast as the eye.

So a narrated fact card was in an unwinnable position. It showed the full print
point (90–115 characters), which needs ~15s to read, while its own narration
finished in ~9s. Every card was reported short, and the reports were correct:
the viewer genuinely could not finish reading before the cut.

Three things could give:

* **Hold the card longer.** Rejected past `vo_hold_max` — 6.6s of frozen
  picture and silence mid-reel reads as the video having stalled (D45).
* **Slow the anchor.** Rejected. A newsreader's pace is part of sounding like
  a newsreader; slowing it to match reading speed makes the delivery worse to
  fix a layout problem.
* **Put less on the frame.** This is what broadcast actually does, and it is
  what `reel_points` does here.

`reel_points` is index-matched to `points` — the same relationship `reel_line`
has to `headline`, one level down. The **voice still reads the full point**
either way, so nothing is lost from the reel, only from the frame. A blank or
missing entry falls back to the full point, and `preflight()` warns on any
point over 80 characters that has no short form.

`reel_read_ease` moved 0.80 → 0.68 at the same time, and that is a change of
STANDARD, not a tuning: 7 chars/sec is the rate for text that is the only
channel. On a narrated card the eye confirms what the ear has already been
given, which is genuinely faster. It is not licence to put print copy on a reel
frame — the warning that survives it is telling you to write a short form.

On the 2026-09-08 edition this removed every reading-time shortfall (ten of
them, up to 4.3s each) and took the reels from 62–70s down to 57–64s.

`brand/content.py :: Story.reel_points` · `brand/motion.py :: reel_cards` · `brand/tokens.py :: Motion.reel_read_ease` · `docs/AI_BRIEF.md`

---

## D52 · The Chief Editor's green signal is established, not asserted

The newsroom skill's final step asks a Chief Editor to "watch the full reel
start to finish" and "read every caption word", then declare the package safe
to post unseen. Written as prose, that instruction is unenforceable: a
reviewer — human or model — can write ✅ against it having looked at nothing,
and the failure is invisible **precisely because** the point of the role is
that nobody downstream checks again. The user is posting on that promise.

That is the same failure this project refuses everywhere else. `Story.validate`
does not ask an editor to remember the law. `preflight` does not ask them to
count characters. `audit_sync` does not ask them to trust that the cuts landed.
So the Chief Editor does not get to *assert* a package is sound either.

`brand/review.py` splits the role in two, and both halves are mandatory:

* **`review()`** establishes what a machine can establish, and what no opinion
  may override — the handle's casing in every copy file, that every referenced
  file exists, that every reel actually carries an audio track and sits inside
  the platform's duration limit, that synthetic imagery is disclosed in the
  caption, that a crime `headline` and `reel_line` each carry their own
  allegation marker, that no string contains a glyph the house fonts cannot
  set.
* **`evidence()`** extracts eight frames per reel plus every carousel slide,
  because a judgement about craft is only worth something if it was made
  against the thing itself.

**`APPROVAL.md` is the green signal, and its absence is the meaningful state.**
A folder without one has not been cleared, whatever was said in conversation.
`approve()` refuses to write it while any check fails, and deletes a stale one
rather than leaving it standing over a package that now fails. `render.py`
exits non-zero when the gate holds.

It earned its place on the first run. On a package that had already passed
every other check in this repository, it caught:

* **eleven copy files and MASTER_COPY.md** still carrying `@OormaniSuddi`
  after the handle moved to `@oormanisuddi` — nineteen occurrences in
  MASTER_COPY.md alone, every one of which would have pointed a reader at an
  account that does not exist;
* **`schedule.json` and `schedule.txt` pointing at `carousel_06_sources.jpg`**
  when the rendered file was `carousel_08_sources.jpg` — the range was
  hardcoded in `publishing_plan()` under a docstring that claimed it was
  "derived from what was actually rendered". The schedule is the one file a
  publisher actually follows.

Neither is a subtle fault. Both survived every existing check because nothing
looked at the finished folder as a whole.

`brand/review.py` · `render.py` · `.agents/skills/second-brain/SKILL.md` Step 13

---

## D54 · A festival greeting is its own genre, not a news card with a festive photo

The first Gauri Ganesha poster was built with the news kit: the masthead
lockup, a "ಧಾರ್ಮಿಕ ವಿಶೇಷ" dateline slot, an eyebrow rail reading "FESTIVAL
WISHES" in tracked capitals, a left-aligned headline, hairline rules and a
footer. Every element was correct by this system's own rules, and the result
read as a bulletin ABOUT a festival — which is exactly why it was rejected. It
also set its headline across the deities' pedestal, and credited the picture
"ಚಿತ್ರ: ಊರ್ಮನಿ ಸುದ್ದಿ" with no AI label on an AI image.

The news rules were not wrong. They were the wrong rules. News grammar exists to
be believed; a wish exists to be felt and forwarded, and the grammar that does
that here is far older than this system:

| news card | greeting |
|---|---|
| left-aligned, asymmetric | centred, symmetrical |
| masthead and dateline | signed — ಶುಭ ಕೋರುವವರು, then the brand |
| no ornament (AGENTS rule 3) | ornament IS the content: drawn, gold, hairline |
| house_grade cools shadows toward navy | warm_grade keeps lamp light; shadows fall into the theme's ground |
| headline in the sans | festival name in the serif, in engraved foil |

So `templates/greeting.py` is a separate genre, and its ornament lives in
`brand/ornament.py`, which nothing else imports — no news template and no
golden hash can be moved by it. Rule 3 still governs news without exception.

Three things carry over unchanged, because they are not style. **Gold is the
only accent**: a theme changes only the ground and the light around the
subject. **Glyph safety** (D46). **Disclosure** (D49): an AI image is labelled
on the poster and repeated in the caption.

**The deity is never covered.** A photograph must declare `keep_clear`, the
band of the image that holds the deity or subject, and `_plan()` guarantees no
type enters it. It tries full bleed; then full bleed with the type up to 14%
smaller; then the picture inside a temple arch; then it refuses. On the Gauri
Ganesha photograph that gives full bleed at 9:16 and the arch at 4:5 and 1:1 —
a portrait subject in a squarer frame genuinely has no room below it for the
wish. Words across Ganapati's face would not be a layout imperfection on this
channel, so `_compose()` re-checks the result instead of trusting the solver,
and the promise is tested on every format.

**Flat yellow is the loudest mark of a cheap poster.** The hero is set in foil:
a gradient with a darker equator and a reflected band below it, a lit upper
lip and a shaded lower lip cut from the glyph's own outline, and two shadows. A
two-stop gradient reads as paint.

**Two faults found by looking, not by testing.** Gold salutation type over the
photo's marigold garland was gold on yellow; it now sits on a pool of the
ground shaped to the line, so the flowers either side stay lit. And the first
arch window ended on a straight cut — the hard photo seam STANDARDS forbids —
where its foot now dissolves through the picture's own alpha.

`templates/greeting.py` · `brand/ornament.py` · `editions/greetings/` · `tests/test_greeting.py`

---

## D55 · No source, no claim. No approval, no upload

**Decided.** A story that is not own reporting must carry at least one
`source_url` the editor can reopen. Fetch writes a tip sheet, never finished
copy. `APPROVAL.md` is still the only green signal, and a person still uploads.
YouTube is real footage. Generated pictures wear `nature: 'ai'`.

**Replaced.** Headlines piped into Gemini for 3–5 journalistic paragraphs;
AI reels scheduled to YouTube Shorts; stock reused as `representative`.

**Why.** The legal apparatus was polishing invented input. Analytics already
showed a 10× gap (37 vs 397) against AI slideshows on YouTube. Labelling
generated stock as ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ is concealment.

**If you undo it.** The channel publishes fiction with a dateline, and trains
YouTube to ignore it.

`brand/content.py` · `scripts/fetch_daily_news.py` · `brand/copy.py :: publishing_plan` · AGENTS Rule 7

---

## D56 · Numeric policy lives in `tokens.Limits`

**Decided.** Reel window 28–45 s, warn above 45, fail above 60. Card beat 135
characters / 10 s. Loudness −14 LUFS / −1.5 dBTP. Slots 11:30 / 14:30 / 17:30 /
20:30. Skills quote these names; they do not invent competing numbers.

**Replaced.** The same limits written differently in AGENTS, the newsroom skill,
the registry, and `review.py`.

**If you undo it.** The next deadline writes a third set.

`brand/tokens.py :: Limits`

---

## D57 · Generated images, including stock, are `nature: 'ai'`

**Decided.** A credit that names an AI image cannot wear `representative`.
The plate is an honest fallback.

**If you undo it.** The IT Rules synthetic-content label is skipped on the
frames that run longest.

`brand/content.py :: Photo.validate`

---

## D58 · A reel opens on the news

**Decided.** The first spoken beat is the headline, not `ನಮಸ್ಕಾರ, ಕರಾವಳಿ ಸುದ್ದಿ.`
Captions disclose that the voice is generated.

**If you undo it.** Viewers swipe in the greeting, which is the first 1.5 s
YouTube and Instagram use to decide distribution.

`brand/voice.py :: narration_beats` · `brand/tokens.py :: Brand.voice_disclosure_kn`

---

## D59 · No human verification, no publication

**Decided.** Every story carries `verified_by` — the NAME of the person who
opened the sources and checked the facts. `brand/review.py` refuses to write
`APPROVAL.md` while any story lacks one.

**Replaced.** D55 said "no source, no claim. No approval, no upload" and
enforced only the first half. `source_url` was required to render; nothing
anywhere required that a person had actually read it.

**Why.** The legal apparatus — the guilt-verb guard, the POCSO location check,
the provenance strip — all assume the facts are real. Nothing in the pipeline
can establish that, and after the intake became a tip sheet the only thing that
could was a person. An obligation nobody is named for is an obligation nobody
has.

**Why it is not inferred from `status`.** `status: confirmed` is what the CARD
says about the news, and a model can write it. `verified_by` is what a person
says about their own work. Collapsing the two would put the assertion back in
the hands of the thing that cannot check.

**Where it is enforced.** At the gate, not in `Story.validate()`. A story must
still be renderable before it is verified — that is how an editor sees the card
they are checking. The refusal belongs at the door to publication.

**If you undo it.** The system goes back to being extremely careful about the
provenance of pictures attached to claims nobody read.

`brand/content.py :: Story.verified_by` · `brand/review.py` · `schemas/story.schema.json`

---

## D60 · Legibility is arithmetic, and arithmetic is testable

**Decided.** `brand/legibility.py` measures every colour pair the house sets
type in, as a WCAG ratio, against `Limits.contrast_min` (4.5) and
`Limits.gold_on_light_min` (3.0). It also measures the line that sells each
post at the width that post is FIRST SEEN at — 150px in a profile grid, 200px
in the Reels grid, 210px in a YouTube search row — against
`Limits.min_effective_px`.

**Replaced.** Both floors were already written in `tokens.Limits`, and nothing
read them. "19px minimum" was a rule about the canvas; every deliverable here
is designed at 1080 and consumed at 400 or less.

**Why.** Gold 500 on ink is 10.7:1. The same gold on paper is 1.70:1 and
unreadable, and nothing stopped a template reaching for `Role.accent` on a
light greeting ground. It would have shipped on a festival poster, where
nobody would have called it a bug. `Role.accent_on_paper` (bronze) exists for
exactly that case, and `FORBIDDEN` in the pair table now asserts that plain
gold on paper stays illegible — so "fixing" it by brightening the gold fails a
test instead of shipping.

**What it deliberately does not do.** It does not complain that small print is
small. A provenance line at 2.6px in a profile grid is fine, because the
disclosure obligation is met by the opened post and by the caption. It checks
the one line that decides whether the post is opened at all.

**The forward.** `Limits.forward_target_kb` stopped being advisory too: the
broadsheet is fitted to it at save time. Quality steps come down first and
chroma is the last resort — never 4:2:0, because Kannada matras are one or two
pixels wide and that is what turns a conjunct into a smear. On real copy it
lands at ~270 KB from ~660 KB without ever leaving 4:4:4.

**If you undo it.** The channel keeps designing at a size no reader uses.

`brand/legibility.py` · `brand/qa.py` · `brand/surface.py :: _fit_to_size` · `tests/test_legibility.py`

---

## D61 · The legal guard is a word list, so its coverage is measured

**Decided.** `tests/legal_corpus.json` holds Kannada crime headlines as a desk
would really write them, each labelled by hand with whether it must be refused.
`tests/test_legal_corpus.py` asserts every one and reports the false-negative
rate when something slips.

**Replaced.** Section 21 of the system book honestly admitted that legal
detection is word-based and incomplete. It was an admission with no number
behind it — nobody knew whether the guard missed one phrasing in fifty or one
in three.

**Why.** Kannada builds the same assertion several ways: the bare past
(ಕೊಂದ), the participle (ಕೊಂದು), the perfective (ಕೊಂದಿದ್ದಾನೆ), the verbal noun
(ಕೊಲೆಗೈದ). The original list carried roughly the first of each. Writing the
corpus found the holes immediately, and the list now carries the forms a desk
actually types.

**The rule that keeps it honest.** When a near-miss turns up in production, add
the row FIRST, watch it fail, then widen the list. A corpus that only ever
grows with successes measures nothing. The safe lines matter as much as the
unsafe ones: without them, an over-eager guard that refuses good ಆರೋಪ copy
would look like an improvement, and it would teach editors to work around the
check.

**What it does not claim.** This measures the word list against a corpus
somebody wrote. It does not make the guard complete, and the named editor
remains the legal actor.

`brand/content.py :: GUILT_ASSERTING` · `tests/legal_corpus.json` · `tests/test_legal_corpus.py`

---

## D62 · The gate records what a machine established, and names who judged the rest

**Decided.** `APPROVAL.md` states plainly that it is a MECHANICAL clearance and
carries three unfilled seats — taste, culture, news judgement. It reads "not
yet cleared to publish" until a named person signs them with
`scripts/sign_off.py`. Every finding carries an error code from `brand/codes.py`
and the step that owns the fix, and `review_report.json` is written pass or
fail.

**Replaced.** A green file whose closing line was "I have reviewed every slide,
every reel, every caption. You can post without watching."

**Why.** No check in `brand/review.py` can tell whether the lead is right,
whether a deity is treated with dignity, or whether the package looks like the
channel at its best. The file was claiming a judgement nothing in it had made —
which is the exact failure the module's own docstring says it exists to
prevent. A score out of ten from an assistant is not evidence for those three;
a name is, because a name can be asked about it afterwards.

**Why the codes.** A prose finding can only be read by a person, so a notifier
cannot react to it, nothing can count it, and the loop-back depends on somebody
remembering who fixes what. `LAW-01`, `IMG-03`, `SND-02` route themselves.

**Why the failed review is written too.** A notifier most needs to read the
review that failed.

`brand/review.py` · `brand/codes.py` · `scripts/sign_off.py`

---

## D63 · The intake retrieves; it never supplies what the source lacks

**Decided.** Where a publisher serves the article, `scripts/fetch_daily_news.py`
fetches the body (via `trafilatura`, optional) so the model condenses
paragraphs instead of expanding a headline. Every generated lead then goes
through a groundedness pass: each number, place and proper noun is checked
against the text it was written from, and anything absent is flagged ⚠️ VERIFY
on the sheet. Where no body could be had, the sheet says HEADLINE ONLY rather
than producing something that reads complete.

**Replaced.** D55 made the fetch a tip sheet, which removed the request for
five journalistic sentences. It left the model working from a headline and an
RSS blurb, and left the editor with no way to see which words came from where.

**Why.** The flagged tokens are the failure mode, precisely: an invented
casualty figure, a hospital that was never named, a helpline number a reader in
Byndoor would actually ring. The pass does not establish truth — nothing here
can — it points the editor's eye at the two or three words that are not in
anything we fetched, instead of at all forty.

**Two details that make it work.** Numbers are checked regardless of length,
because "45" is two characters and is the most dangerous thing a model can
supply. And Kannada case endings are matched by stem, because ಉಡುಪಿಯಲ್ಲಿ
against a source saying ಉಡುಪಿ is grammar, not an invented fact — a check that
cried wolf on every inflection would be switched off within a week.

**If you undo it.** The morning goes back to a sheet that looks equally
confident whether it was built from five paragraphs or from six words.

`scripts/fetch_daily_news.py` · `tests/test_intake.py`

---

## D67 · A decision with nothing behind it is a paragraph

**Decided.** `docs/_build_traceability.py` maps every D-number to the tests that
name it, and `tests/test_contract.py :: EveryDecisionIsAccountedFor` fails when
any decision is enforced by nothing. Three buckets are allowed: named by a
test, regression-guarded by the golden fingerprints, or recorded as untestable
with a reason.

**Replaced.** Sixty decisions and several hundred assertions, with no way to
say which held up which. The first run of the tool found twelve decisions with
a test naming them and forty-two with nothing.

**Why the golden bucket is separate.** It is a weaker guarantee and saying so
costs nothing. The golden hash would fail if leading stopped coming from the em
— but nothing asserts that it does. A regression is caught; the rule is not
verified. Counting those as "tested" would have made the number look better and
meant less.

**A defect this found.** D29, D30 and D31 each existed twice — one design
decision and one legal decision sharing a number — so "see D29" was ambiguous
in `AGENTS.md`, `CLAUDE.md`, `brand/content.py`, `templates/youtube_thumb.py`
and the publish skill. Every live reference meant the legal one, so the three
design decisions became D64–D66 and a test now refuses a duplicate number.

`docs/_build_traceability.py` · `docs/TRACEABILITY.md` · `tests/test_contract.py`

---


## D68 · The reel gate cannot be the thing that limits crime

**Decided.** At most one crime reel per edition, and a warning when crime is
more than 40% of an edition's stories. `tokens.Limits.crime_reels_per_day`,
checked at the gate as `PUB-04`. It warns; it never blocks.

**Why it is not left to the gate that already exists.** Step 2 chooses reels on
"drama, public stakes, shareability". Crime scores highest on all three, every
day, in every newsroom that has ever existed. So the reel gate is not a
constraint on crime — it is a mechanism that selects for it, and adding the
metrics loop makes that worse, because crime will also win on views.

**What that drifts into.** A crime channel. Which is precisely where every
legal exposure in this system lives — the BNS §356 guard, the JJ Act rules, the
POCSO location check all exist because of crime copy — and it is where local
outlets reliably end up without anybody deciding to go there. Nobody chooses
it. It happens one good news day at a time.

**Why it warns rather than blocks.** A real crime day is a real crime day, and
a system that refuses to cover one would be overruling an editor on news
judgement, which is the single thing it must not do. The cap exists to make the
drift a decision somebody takes rather than a direction nobody noticed.

**If you undo it.** The metrics loop added in this same release becomes the
thing that steers the channel, and it will steer it here.

`brand/tokens.py :: Limits.crime_reels_per_day` · `brand/review.py` · `tests/test_contract.py`

---

## D69 · A bad Tuesday has a defined minimum, decided in advance

**Decided.** `--minimal` renders the four things that ship most mornings —
carousel, story card, broadsheet, reel. On a day with four hours instead of
ten, or a morning when the fetch half-failed, that is the edition. Below it,
the honest floor is: one carousel, one broadsheet forward, and nothing else.

**Replaced.** A daily package of eleven deliverables, a bulletin, a thumbnail
and up to five reels, on one 8 GB machine, with no definition anywhere of what
gets dropped first.

**Why.** Every schedule in this project assumed a full day. There was no answer
to "it is 07:40, the scrape returned two usable tips and I have until nine" —
so the answer got improvised, and an improvised answer under time pressure is
how a thin story gets promoted to a reel. Deciding it now, while it is calm,
is the entire point.

**The order things drop in.** Bulletin first — it is off by default and is not
going to YouTube anyway. Then the standalone post cards. Then the thumbnail,
which exists for a video that may not be made. Then reels, one at a time, worst
story first. The carousel and the broadsheet are last, because the carousel is
the day's record and the broadsheet is the forward that actually grows the
channel.

**What never drops.** `verified_by`. The legal guards. The sign-off. A short
day is a reason to publish less, never a reason to publish less carefully.

`brand/tokens.py :: Limits.daily_templates` · `render.py --minimal` · `docs/RUNBOOK.md`

---

## D70 · The year is on a calendar, not in somebody's head

**Decided.** `editions/greetings/calendar.json` holds the year's observances,
the seasons the desk should be reporting inside, and five recurring reviews
with intervals. `scripts/whats_on.py` says what is coming and what is overdue.

**Why.** A local channel is judged on whether it turned up for the things its
town cares about. Missing Krishna Janmashtami in Udupi is a miss a reader
remembers longer than any good story — and it is never missed by decision, it
is missed on a Tuesday. The same is true of the reviews: nobody decides to skip
the law review for a year.

**The rule about lunar dates.** The file records the MONTH and deliberately not
the day. Every Hindu and Islamic festival here moves with its own calendar, and
a greeting posted on the wrong day is worse than no greeting, so the tool
refuses to guess: it fires at the start of the month and says confirm from a
Udupi panchanga. That is a thing a person does, and the one thing this script
must not pretend to have done on their behalf.

**What is in it that a generic Indian calendar would miss.** Bisu Parba, Aati
Amavasya, the Kambala and Yakshagana mela seasons, the monsoon trawling ban at
Malpe and Gangolli. Those are the entries that make it this channel's calendar
rather than anybody's.

**The review that matters most.** `backup_restore_test`, every 90 days. A
backup nobody has ever restored is a hope, and finding that out after a disk
failure is finding it out at the only moment it cannot be fixed.

`editions/greetings/calendar.json` · `scripts/whats_on.py`

---


## D71 · The scheduler is not ours to own; the heartbeat is

**Decided.** This project does not install a 06:05 launchd job on a machine
that already has one. `scripts/fetch_daily_news.py` writes
`logs/last_fetch.json` on its way through, and `scripts/health.py` reads it. The
plist we ship stays available and `install_launchd.sh` refuses to install it
while another job fires at the same hour and minute.

**The situation.** `com.oormanisuddi.daily` runs `~/run_oormani.sh` at 06:05.
That script is outside this repository, and AGENTS rule 8 makes reading outside
it fail-closed — so it cannot be inspected, which means retiring it would be
disabling something nobody here has read. Installing ours alongside is worse:
two jobs writing `inbox/` at the same minute, and the one that finishes second
wins silently.

**Why this is not a compromise.** The improvements are in the SCRIPT, not in
the job. Article-body extraction, the groundedness pass, the model fix —
anything that calls `fetch_daily_news.py` gets all of them, whoever wrote the
caller and whenever they wrote it. Owning the scheduler would have added
nothing except a race.

**What issue #19 actually wanted.** Not "run the fetch on a timer" — it already
ran on a timer. It wanted somebody to find out when the timer stopped working,
before noon. That is the heartbeat, and it works regardless of what schedules
the script, including a cron job, a manual run, or a replacement for
`run_oormani.sh` written next year by somebody who has never read this file.

**If you undo it.** Either the morning silently runs twice and one result is
thrown away, or a working routine gets disabled by something that could not
read it.

`scripts/fetch_daily_news.py :: _heartbeat` · `scripts/health.py` · `scripts/install_launchd.sh`

---


## D72 · Reach is local penetration, and it is measured that way

**Decided.** `brand/reach.py` scores every story on local usefulness, decides
which formats it earns, and checks the town name lands before the caption fold.
`copy.taluk_forwards()` cuts one WhatsApp forward per town the edition covers.
`Limits.reels_per_day_target = 2`. `metrics.py` records `local_reach` and the
report opens on in-district share rather than on views.

**Replaced.** A posting schedule, and "reach" meaning views.

**The correction underneath all of it.** Forty thousand views from Bengaluru is
a miss. Two thousand in one taluk is a local media position, and eventually
sellable to a jeweller in that taluk. Raw reach cannot tell those apart, so it
was the wrong number to optimise and every downstream decision inherited that.

**Why one forward per town.** Nobody forwards a seven-taluk digest, because a
digest is nobody's in particular and there is no group it obviously belongs in.
A Kundapura card goes into a Kundapura group with somebody's own name attached
to it. Same facts, same sourcing, re-cut so the first line is the reader's
town. This is the highest-leverage distribution change available to this desk
and it costs one function.

**Why the place registry is not duplicated here.** Every place name lives in
`copy.PLACE_TAGS` and this module reads it without adding to it — the same rule
`tokens.Limits` has for numbers. Two lists of towns drift within a month, and
then the hashtags, the forwards and the relevance score disagree about where
Byndoor is. A test asserts reach.py hard-codes no place.

**Why it scores usefulness and not attention.** Crime wins every engagement
signal in every newsroom that has ever existed. A reach layer that ranked by
predicted views would be a machine for producing the drift D68 exists to cap.
So the score is: who is affected, how near, how soon, and can the reader act.
A test asserts a civic notice with a deadline outranks a crime story.

**Why two reels rather than four.** On an account this size each post goes to a
small test slice and is judged relatively; splitting the same audience four
ways makes all four look average. It is a target, not a cap — a genuinely big
day is allowed to be one — and the render time saved is the capacity problem
solving itself.

**Why the fold matters.** Instagram truncates a caption at about 125 characters
behind "… more". A coastal story whose town name sits past that is invisible to
the taluk it was written for, which is the only audience that was ever going to
forward it.

**What this deliberately does not do.** It does not auto-publish, it does not
rank stories for the editor, and it does not touch which places the channel
covers. It reports; a person still decides.

**If you undo it.** The channel goes back to being judged on a number that
cannot distinguish its own town from a stranger's.

`brand/reach.py` · `brand/copy.py :: taluk_forwards` · `brand/tokens.py :: Limits` · `scripts/metrics.py` · `tests/test_reach.py`

---


## D73 · The newsroom answers in one shape, argues with itself, and remembers

**Decided.** Four things, which are one thing.

Every expert role answers in the same six fields — ROLE, LOOKING AT, MAY BLOCK,
MAY NOT, EVIDENCE, VERDICT — and a verdict with no filled-in EVIDENCE is not a
pass, it is a missing pass. Every verdict may carry `COULD NOT CHECK`, because
a model cannot hear a reel or see a frame and the honest failure is declaring
that rather than claiming otherwise.

An **adversary** runs at every stop with the opposite incentive written into
it: argue this should not run. It has no veto — it makes the case, a person
decides — and it returns NOTHING, CONCERN or SERIOUS. If it returns NOTHING on
every story every day, it is not working, and the skill says to report that.

**Iteration is bounded at two passes.** Then the stop is HELD with a named
reason. Unbounded looping until everything scores 10/10 is how a panel starts
awarding itself nines; two passes fixes what is fixable, and a third means the
problem is the story rather than the copy.

**House rules** (`brand/house.py`, `scripts/house_rule.py`) record what the
owner asked for once, in their words, with the date and the reason, and the
newsroom reads them at the start of every run.

**Replaced.** Twelve roles scoring themselves out of ten, a loop with no
termination condition, a panel where every member was helping the thing ship,
and standing instructions that lived in a chat log until everybody forgot them.

**Why the routing matters more than the ledger.** Not every change is a house
rule, and putting the wrong one there rebuilds the two-sources-of-truth problem
this project is arranged to prevent. `house_rule.py where "…"` answers it: a
NUMBER goes to `tokens.Limits` with a decision and a test (D56); a LEGAL rule
goes to `brand/content.py` with a test (D29); a PLACE goes to
`copy.PLACE_TAGS`; everything else — wording, habits, the order you like things
done in — is a house rule.

**The hard edge.** `add()` refuses anything that reads like a waiver: skip,
bypass, ignore, disable, override, publish without. This is the most dangerous
file in the repository and it needs the least give, because it is exactly the
shape an override would take if one ever got in: a plain-text file the newsroom
reads every morning and obeys. D29 says a rule that can be waived on a deadline
will be waived on a deadline, and that does not stop being true because the
waiver is polite and dated. If a guard is genuinely wrong, that is an hour:
change the code, write what breaks without it, add the test. Then it survives,
and the next person can see why.

The refusal names the alternative, deliberately. A refusal that does not gets
worked around.

**Precedence.** `AGENTS.md` beats a house rule and the skill stops and flags the
conflict. A house rule beats the skill's own defaults and the skill says so —
the document is the general case, the owner's standing instruction is the
specific one.

**If you undo it.** Experts go back to asserting, the loop goes back to having
no floor, nothing argues the other side, and the next thing you ask for is
forgotten by October.

`brand/house.py` · `scripts/house_rule.py` · `.agents/skills/second-brain/SKILL.md` · `tests/test_house.py`

---


## D74 · A licence you cannot point at is one you cannot produce

**Decided.** A bed may be `status: allowed` only when its licence can be
produced. `own` is the single exemption — there is no licence page for
something the channel made. Everything else needs a `source_url`, and
`brand/music.py` blocks the render without one.

**Found by running the audit rather than by reasoning about it.** The quarterly
`licence_audit` had never run. It took eleven seconds and turned up a
third-party track by a named artist, marked allowed under
`recorded-in-project`, with no URL — already used as the bed on a published
Ganapathi film.

**Why that is not a licence.** "Recorded in project" means the terms were
written down somewhere. That is precisely what nobody can find eighteen months
later when a claim lands, which is the only moment the record matters.

**What was done.** Blocked, not deleted. The file stays on disk with a note
naming the one line that re-enables it: find the page it was licensed from,
paste it into `source_url`, set the real terms. Deleting the evidence of what
was used would be worse than blocking it — a claim about a video already
published is not answered by having tidied up.

**The cost, stated plainly.** The channel is down to one usable bed until
somebody finds that URL. That is the correct state: the alternative was
carrying an exposure on every devotional edit and finding out via a strike.

**If you undo it.** Every video using an unprovable bed stays exposed, and the
register goes back to recording intentions rather than licences.

`brand/music.py :: audit` · `assets/LICENCES.json` · `scripts/health.py` · `tests/test_contract.py`

---


## D75 · A URL two tips share is a listing page, not an article

**Decided.** `attach_bodies()` never fetches or labels a body from a
`source_url` that more than one tip resolved to. Detected structurally —
counting URL repeats across the batch — not by naming Udayavani or any other
site.

**Found running the fetch for real, on 2026-09-17, the first morning anyone
asked why there was no news.** `scrape_udayavani_html()`'s `<h2>`/`<h3>` regex
was matching headline text sitting *inside* the page's embedded React
hydration JSON, with no real per-article link beside it, so every one of its
twelve tips fell back to the same district listing-page URL. `fetch_body()`
then fetched that one page once and handed the identical wrong text to all
twelve, each stamped `body_source: 'article'` — a claim of grounding the sheet
did not have.

**Why this was worse than having no body at all.** The groundedness pass (D63)
compared each lead against that shared garbage instead of the tip's own
source, and flagged real facts as invented because it was reading somebody
else's headline. 28 of 33 leads were flagged in one run. After the fix: 15,
which is the genuine remainder from Kannada-grammar edge cases on other
sources, plus one tip correctly marked "could not be checked" instead of
flagged, because its source was in English.

**Why a structural check and not a URL blocklist.** A list of known-bad pages
protects against this one site. Counting repeats catches the same class of
bug in any scraper, including ones written after this file is.

**If you undo it.** The very system built to catch invented facts starts
manufacturing false ones to flag, at a rate high enough that an editor learns
to ignore the flags — which is the same failure as not checking at all.

`scripts/fetch_daily_news.py :: _shared_urls, attach_bodies` · `tests/test_intake.py`

---


## D76 · "Ready by 8am" needs a number attached to how sure that is

**Decided.** After every successful morning fetch, `scripts/draft_edition.py`
runs automatically and turns `inbox/today.json` into `editions/{date}.json` —
every `headline`, `deck`, `point` and `takeaway` copied verbatim from a tip
the fetch already grounded, nothing written. It skips, rather than guesses,
anything needing a judgement call: an English-only tip, a story that fails
its own legal validation, one whose headline would hard-fail `render.py`'s
preflight. `verified_by` is never set — it cannot be; that is the one field
only a person can fill in (D59), and the gate refuses `APPROVAL.md` without
it (`SRC-02`). `scripts/verify.py` turns filling it in into one command per
story instead of hand-editing JSON. The launchd schedule (D71) now fires
twice, 06:10 and 07:00, so one missed wake does not cost the morning.

**Why this, and not full automation.** The user's request was that the only
thing left at 8am is posting. Taken literally that means no human check
before publication — which is exactly the line D59 and D62 exist to hold, for
reasons already paid for in this project's own history (D29: what was
published before `Story.validate()` existed). The honest answer was to say
that line plainly and then automate everything up to it: a person now opens
`inbox/checklist_{date}.md`, confirms each source is true, and runs
`scripts/verify.py` — four short commands instead of reading 30+ raw tips and
hand-building JSON from scratch.

**Why draft, not just fetch.** The tip sheet already existed (D55). What
"ready by 8am" was missing was not more data — it was the mechanical
reshaping into `Story` objects, done every single morning by hand, that
carries no judgement of its own. A script can copy a field and run the
existing legal and rendering checks against it; it cannot decide a fact is
true. Drawing the line there, instead of at "produce a tip sheet" or at
"publish", is what actually removes the manual work without removing the
check that work exists to satisfy.

**Why it can safely be unattended.** Every failure mode routes to "skip and
say why", never to "guess and move on": `ContentError` (bad law), a failed
preflight (bad render), an English-only or unsourced tip, a listing-page URL
shared by more than one tip (D75, reused directly via `_shared_urls` rather
than re-implemented). A morning with nothing safely draftable produces an
empty edition and a note explaining why, not a broken one.

**If you undo it.** The morning goes back to a tip sheet nobody turns into an
edition until someone notices there is no news for the day — which is the
exact complaint that started this (2026-09-17, "no news created for today").

`scripts/draft_edition.py` · `scripts/verify.py` · `scripts/morning.sh` ·
`scripts/launchd/com.oormanisuddi.morning.plist.template` · `tests/test_draft_edition.py`

---


## D77 · Carousel is the day; a reel is earned, not defaulted

**Decided.** The documented daily default narrows from D69's four formats to
one, plus a decision: `scripts/pick_formats.py` always includes carousel, and
adds `reel` only when the lead story clears `brand.reach.should_be_reel()`
(D72) — the same mechanical relevance check the Chief Editor gate already
reads elsewhere, not a fresh guess. `story_card` and `broadsheet` are dropped
from the default entirely. House rule 2026-09-17-02 records the editor's own
reasoning: carousel already covers the ground both of those exist for, and
every extra file rendered is more time spent posting it, not less.

**Narrows, does not repeal, D69.** `--minimal` and `Limits.daily_templates`
still exist unchanged in code — `render.py --minimal` still renders all four,
for whoever explicitly asks for it. What changes is what every documented
workflow (`docs/RUNBOOK.md`, `.agents/skills/second-brain/SKILL.md`, the
Start / approve / Stop chat protocol, D76) tells a person or an AI to run by
default. D69's floor — `verified_by`, the legal guards, the sign-off never
drop, whatever else does — still holds exactly as written.

**Why a script decides the reel and not a person, each morning.** The
question "does today's lead deserve a reel" already has a mechanical answer
sitting in `brand/reach.py`: category fit, local relevance, whether a place
is even named. Asking a person to re-derive that judgement call by eye every
morning, when the evidence already exists and is already trusted by the Gate
stop, is the exact kind of repeated manual decision this project keeps
finding and removing.

**If you undo it.** Every morning goes back to rendering four files whether
or not three of them are earning their post — more render time, more time
spent posting, and a reel on a story nobody was going to watch past frame
one, which is the one thing `should_be_reel()` already exists to catch.

`scripts/pick_formats.py` · `brand/reach.py :: should_be_reel, formats_for` ·
`tests/test_pick_formats.py`

---


## D78 · A tip is only worth having if its link opens and its flags mean something

**Decided.** Two halves of one problem, both found by measuring the morning
of 2026-09-17 rather than by reading the code.

**The links.** Google News supplied 15 of that morning's 33 tips and produced
an article body for **none** of them: a `/rss/articles/` URL is an opaque
token that only becomes a real address after JavaScript runs. `trafilatura`
gets a 580 KB shell with no link in it, and a person who clicks it lands on
the publisher's home page — which is what happened when the day's lead story
was opened to be verified, and the honest answer had to be "I could not check
this one." Udayavani's RSS returns nothing at all, so its twelve tips fall
back to one district listing URL and are skipped by D75 as they should be.
Six tips of thirty-three had a source anybody could actually reopen.

So the intake now reads two district-scoped publisher feeds first —
News Karnataka's Udupi and Mangaluru feeds, and Vartha Bharati's Karavali
section. Real article URLs, and 2,000–2,400 characters of extractable text
each. **Measured after: 50 tips, 12 full articles, against 33 and zero.**

**The budget counted the wrong thing.** `BODY_BUDGET` capped *attempts*, so
fifteen unresolvable links spent the whole allowance before a fetchable one
was ever reached. It now counts articles actually got, with `BODY_ATTEMPTS`
as the separate politeness ceiling. That single line is most of the zero.

**The flags.** 26 leads of 50 carried a flag, and the most-flagged token in
the entire sheet was `ಹಾಗೂ` — "and". The rest were postpositions (`ರಂದು`,
`ವೇಳೆ`), connectives (`ಸಂಬಂಧಿಸಿದಂತೆ`), case-marked ordinary nouns (`ಸಭೆಯ`,
`ನಗರದ`) and a month the source had abbreviated (`ಸೆ.18` against the lead's
`ಸೆಪ್ಟೆಂಬರ್`). Three fixes: the stopword list now holds the words that cannot
be a fact in any sentence; a lead's case marker is stripped and the bare stem
looked for, which is what `ಸಭೆ` needed because at three aksharas it never
entered the haystack's token set at all; and an abbreviated month is bridged
to its full name, derived from `KN_MONTHS` rather than a second table.

**What that leaves.** The same 50 leads now flag single occurrences of actual
nouns and figures — a place name, an institution, a number — which is what
the pass was built to surface. The invented casualty figure, the invented
helpline and the place the source never named all still flag; there is a test
class whose only job is to prove that widening the list did not blunt the
check.

**Why this matters more than it looks.** D75 already wrote down the cost:
flags at that rate teach an editor to skip them, and an ignored check is the
same as no check. The groundedness pass is the machine's only automatic
defence against an invented fact reaching a card, and it was spending its
credibility on the word "and".

**If you undo it.** The morning goes back to a sheet whose links do not open,
whose leads rest on headlines, and whose warnings are mostly grammar — all
three of which look like a working newsroom right up until somebody has to
verify something.

`scripts/fetch_daily_news.py :: scrape_newskarnataka_kn, scrape_varthabharati_kn,
attach_bodies, _month_bridge, _supported, _FUNCTION_WORDS` · `tests/test_intake.py`

---


## D79 · The 90-day law review, 2026-09-17 — and what it found

**Done, and dated, because "we looked and nothing moved" is a finding.** The
review asks for D29, D49 and D59 to be read against what the law says now, and
for the guilt-verb list and the POCSO location rules to be checked. Recorded
here whether or not anything changed, which is the point of putting a date on
it.

**The guilt list holds.** 41 verbs, 37 corpus rows, all landing where they are
labelled. Probed against phrasings a coastal desk actually writes —
`ಮೋಸ ಮಾಡಿದ`, `ವಂಚಿಸಿದ`, `ಸುಲಿಗೆ ಮಾಡಿದ`, `ಅಪಹರಿಸಿದ`, `ಬೆಂಕಿ ಹಚ್ಚಿದ`,
`ಹಣ ದೋಚಿದ`, `ಲಂಚ ಪಡೆದ` — every one already caught.

**Two phrasings are deliberately NOT added.** `ದಾಳಿ ನಡೆಸಿದ` and
`ಮಾರಾಟ ಮಾಡಿದ` slip through, and they should. A ದಾಳಿ is as often a Lokayukta
or police raid as an assault — one ran in this very morning's tips — and
`ಮಾರಾಟ ಮಾಡಿದ` is ordinary commerce far more often than it is an offence.
Adding them would refuse legitimate civic copy on most days it fired, which
buys nothing and teaches the desk to fight the guard. The rule about a word
list being over-eager stops where the word stops being about guilt.

**The victim-location guard had a real hole, and it was local.** `_GRANULAR`
already carried the coastal forms a generic Indian list misses — ಪೇಟೆ,
ಕ್ರಾಸ್, ಮಠ — but it named four faiths' places of worship and missed the
fifth, ದರ್ಗಾ. And it missed the landmark that locates a person most precisely
in Karkala and Moodbidri: a **ಬಸದಿ**. In a town that size "the basadi" is an
address, and a sexual-offence story naming one identifies the victim as surely
as a street would. Added with ಗುಡಿ, ಕಟ್ಟೆ, ನಿಲ್ದಾಣ, ಅಪಾರ್ಟ್, ಅಂಗಡಿ, ಕ್ಯಾಂಪ್,
ಕಾರ್ಖಾನೆ, ಹೊಟೇಲ್ and ನಿವಾಸ. The district and the taluk still pass, and a
test says so — a guard that refused those would leave no way to say where
anything happened.

**What this review could NOT establish.** Whether the statutes themselves
moved. That needs somebody qualified reading the current text of the BNS, the
JJ Act, POCSO and the IT Rules amendments; nothing here browsed a legal
database, and a word list passing its own corpus is not evidence that the
corpus still matches the law. This entry records a code-and-corpus review, and
the next one should start by answering that question rather than assuming it.

`brand/content.py :: _GRANULAR` · `tests/legal_corpus.json` ·
`tests/test_legal_corpus.py`

---


## D80 · Two rules that were each right and together stopped every morning

**Found by running Start / go / Stop end to end instead of assuming it.**
House rule 2026-09-17-03 made a photograph mandatory on every carousel slide
and the gate enforces it as `IMG-04`. `draft_edition.py` (D76) attaches no
photograph, because it copies text and invents nothing. Both were correct on
their own. Together they held **every** auto-drafted edition at the gate on
one count per story, before anybody had read a word — the pipeline could not
produce an approvable package at all.

**Decided.** `brand/stock.py` is the picture desk when nobody is at it. A
story gets a frame from `assets/stock/` when its own words or its category
earn one, and the draft arrives illustrated. What it will not do is attach a
picture it cannot defend: `sport` and `obituary` have no honest frame in this
library, so those are left bare and the gate stops the package for a person
to answer. A fishing harbour on a school story is a lie told in pictures, and
`docs/AI_BRIEF.md` has said so from the start.

**Three things the first run got wrong, all fixed here.** A raw substring
match put a farmers' market on a story about a political row, because `ದರ`
(price) sits inside `ವಿಚಾರದಲ್ಲಿ` — matching now runs per word, from the start
of the word, which keeps ಮಳೆ → ಮಳೆಯಿಂದ and refuses the accidental middles.
Two stories of one category took the same frame, so a frame is now used once
per edition. And the library was thin where the district is busiest, so the
three loose images sitting in `assets/` — a hospital campus, a coastal storm,
a police cordon — were moved into `assets/stock/`, catalogued, and every
reference to their old paths repointed. 27 frames, all catalogued, and a test
says an uncatalogued one cannot be chosen.

**Also fixed on the same run.** The per-town WhatsApp forwards were being
written to files whose names were not the town's name in any language:
`isalnum()` is False for a Kannada vowel sign, so ಉಡುಪಿ was saved as
`forward_ಉಡಪ.txt` and ಮಂಗಳೂರು as `forward_ಮಗಳರ.txt`. They now carry the Latin
name from `copy.PLACE_TAGS` — `forward_Udupi.txt` — which is the file
somebody has to pick out of a folder at 20:00.

**What the end-to-end run now leaves.** One block, four times over: `SRC-02`,
no `verified_by`. That is the person saying go, and it is the only thing
between a drafted morning and an approvable one. It is supposed to be there.

`brand/stock.py` · `scripts/draft_edition.py` · `render.py` ·
`assets/stock/CATALOG.md` · `tests/test_stock.py`

---


## Changing something here

If you are about to change a value in `brand/tokens.py`:

1. Find its entry above. If there isn't one, add it after you decide.
2. Run `python3 -m pytest tests/ -q`. Golden failures are expected when the
   design genuinely changes — look at the diff images before accepting them.
3. Re-render the reference set and look at it: `python3 examples/make_examples.py`.
4. Update [`../STANDARDS.md`](../STANDARDS.md) if the rule changed, not just the value.
