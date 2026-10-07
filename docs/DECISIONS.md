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

## D53 · A dot that is not a sentence end is heard, never seen

*(Entry written 2026-09-27 from the code and tests it had always been cited
by; the decision itself dates from the narrated reels.)* A TTS engine reads
every dot as a full stop, and two of those shipped before a listener, not
the pipeline, caught them: "₹1.10 ಲಕ್ಷ" was read as "one" … "ten lakh" — a
different amount with a pause inside it — and "ಕೆ. ಜೆ. ಜಾರ್ಜ್" came out with
long gaps between the letters of a man's name. Neither is fixable after the
text reaches the engine, so the narration normaliser writes figures and
initials out the way an anchor SAYS them before synthesis: money with a
scale word in whole units of the scale below, with ರೂಪಾಯಿ after it
(₹1.10 ಲಕ್ಷ → 1 ಲಕ್ಷದ 10 ಸಾವಿರ ರೂಪಾಯಿ, through the real ratio between scales,
not a flat ten); any other decimal as ಪಾಯಿಂಟ್; initials without their dots
(ಕೆ ಜೆ ಜಾರ್ಜ್); abbreviations such as ಡಾ. expanded before the initials rule
can mistake them for one. Every voice in the engine — the ಸ್ಪೀಡ್ ನ್ಯೂಸ್
anchor included — goes through it.

`brand/voice.py :: _speech_normalise, _say_scaled` ·
`tests/test_contract.py :: ThingsTheEngineReadsAsAFullStop` ·
`tests/test_speednews.py`

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


## D81 · ಸ್ಪೀಡ್ ನ್ಯೂಸ್: the day as one quick-news reel, built into the engine

**Decided.** With three or more stories, the daily reel is ಸ್ಪೀಡ್ ನ್ಯೂಸ್ —
`render.py --only roundup`, `brand/speednews.py`. A place and one line per
story, spoken by the anchor while it is on screen, each story cut to its own
measured narration, a counter and one progress segment per story, a two-second
follow card, under 45 seconds. On a thin day the lead-story reel (D39) is
still the reel, and only if the lead earns it. Never both. House rule
2026-09-18-02, which retires 2026-09-17-02.

**Why D39 is narrowed, not overturned.** D39 said four headlines in 30s is a
slideshow the viewer swipes off, and for the reel it was written about it was
right. Speed news is a different, proven grammar — every Kannada channel runs
it — and it answers D39's objection with the two things a slideshow lacks: the
anchor is saying the line while it is on screen, and the viewer can see it is
story 3 of 8 with the next one two seconds away.

**Found by watching the first attempt frame by frame.** It was a side script,
`scripts/render_roundup_reel.py`, and it had fourteen faults:

- The wipe moved whole frames, so its gold edge sliced Kannada headlines
  mid-akshara on every cut. Now the wipe moves pictures only: story text is
  gone before it starts and lands after it, and the chrome sits above it.
- It used `fmt('story')`, whose right margin is 72px. Headlines ran under the
  like/comment/share rail and the handle footer sat under the caption. Now
  `fmt('reel')`: right 220, bottom 480, and a test holds every block inside.
- The anchor's words went to the TTS engine raw, skipping `voice._spoken`
  and everything D53 learned about ₹, initials and decimals.
- Each story was held to a 4.6s floor, then eight seconds of logo closed it:
  51s for eight headlines. The first engine render then capped stories at
  6.0s while two narrations ran longer — which starts the next voice on top
  of this one. Now a story is exactly as long as it is said; a line too long
  for the format is reported for a shorter `reel_line`, never cut.
- Every Google clip ends on ~0.38s of silence; eight of those is three
  seconds. Trimmed at the ends only — the beat after the place name stays —
  with a light extra pace for the format (`Motion.speed_tempo`).
- It mastered to −11.8 LUFS in one loudnorm pass. Two passes now land on
  −14.0, with a limiter for the tenth of a dB linear mode cannot promise.
- The gate matched `reel(_\d+)?\.mp4`, so `roundup_reel_9x16.mp4` was cleared
  with no duration, audio or silence check at all. It is `roundup.mp4` now and
  the gate reviews it, and every reel now carries a loudness check (`SND-07`).
- Its caption was typed into the script with that day's eight headlines, and
  said "swipe" on a video. `copy.for_roundup` builds it from the edition and
  carries both disclosures a synthetic anchor over generated pictures owes.
- Its cover landed as `roundup_reel_cover_cover.jpg`, because `_write_cover`
  was handed the cover's path instead of the video's; and 35 intermediate
  files were left in the delivery folder. Intermediates live in `build/`.
- The AI-image disclosure was 18px of grey over a crowd. It is a solid pill,
  on every frame that shows the picture, including through the wipe.

**Measured after.** Today's eight stories: 44.9s, all eight in, −14.0 LUFS,
gate clean.

**If you undo it.** The day's reel goes back to being a script outside the
engine, and every fault above comes back with it — most of them invisible to
every check, which is how they shipped the first time.

`brand/speednews.py` · `templates/roundup.py` · `scripts/pick_formats.py` ·
`brand/review.py` · `brand/copy.py :: for_roundup` · `tests/test_speednews.py`

---


## D82 · Sound effects are made here, registered, and tied to the cut

**Decided.** Every sound effect a reel plays is from the house set,
`brand/sfx.py`: synthesised from a fixed seed, so `python3 -m brand.sfx`
rebuilds byte-identical files; registered in `assets/LICENCES.json` as
`kind: sfx`, `licence: own`. Nothing outside the register is played — by the
speed-news reel or by the lead-story engine, whose `_sfx_set` used to reach
first for `sfx/pro_*.wav`.

**Why.** A sound effect draws a Content ID claim exactly as a music bed does,
and D74 had only audited beds. `sfx/pro_*.wav` have no record anywhere and
sit beside a deleted `sfx/downloaded/` folder of numbered third-party files —
nobody can say which of those they were cut from, so nobody could answer a
claim on one. The four older files (`whoosh`, `news_impact`, `tech_ping`,
`camera_shutter`) were synthesised by a script that was itself deleted; the
new set supersedes them with the same provenance, recorded this time.

**The set, and what each is for.** `open` — a short low hit on frame 0, under
the anchor's first word. `whoosh` — centred on every picture wipe, panned left
to right with it. `tick` — a quiet tock as each headline lands. `outro` — a
three-note ident as the follow card's logo arrives. Gains are low on purpose:
in speed news the anchor is the programme and the effects are punctuation.
Measured on the first render: frame 0 went from −91 dB (silence) to −7 dB,
and the 3–7 kHz band rises 13 dB exactly at the wipe centre.

**`allowed_paths(kind)`.** Rows without a kind are beds, as every row was
before. A render asking for an allowed bed must never be handed a 0.14s tick.

**Same release: the reel and its cover redesigned (D81 continued).** Square
corners, as STANDARDS Rule 3 always required — the first cut used rounded
pills. Each story arrives on a lower-third band that sweeps in from the left
and runs to the foot of the frame, with the place tag on its gold top edge;
the headline rises onto solid ground instead of floating on a shadow over a
busy photograph. A firmer Ken Burns push (`Motion.speed_push`), because the
house value is tuned for 6–12s scenes and barely moved in five. The follow
card animates. And the cover is a title card, not frame 0.8: ಸ್ಪೀಡ್ ನ್ಯೂಸ್ at a
size that reads on the profile grid, the count and length, the towns, the lead
line — all inside the centre 3:4 the grid crops to, which a test holds.

**If you undo it.** The engine goes back to playing files nobody can account
for, and the first claim is the one nobody can answer.

`brand/sfx.py` · `assets/sfx/` · `assets/LICENCES.json` · `brand/music.py ::
allowed_paths` · `brand/motion.py :: _sfx_set` · `brand/speednews.py ::
sfx_cues, render_cover` · `tests/test_speednews.py`

---


## D83 · Speed news shows the whole picture, and uses the whole frame

**Decided.** Each story's photograph is fitted WHOLE into a window, as large
as the frame allows, over a blurred and darkened copy of itself; the band and
headline start below it. The headline is pinned to the same line on every
story — the caption line — and the picture is centred in the room above.
Speed news uses its own top and bottom (`Motion.speed_top` 150,
`speed_bottom` 380) instead of the lead reel's 230 / 480.

**Found by the editor, the day after D82: "images are half cut", and "too
middle".** Both were right, and measurable. The day's pictures are square and
wide — 1:1, 1.73:1, 1.96:1 — and D82 laid them full bleed on a 9:16 frame,
which cuts away 44% of a square picture's width and 71% of the widest; the
band then covered the lower half of what remained. And the lead reel's margins,
reused, left dead bands above and below the content.

**Why pin the text and float the picture, not the reverse.** Tried the other
way first: the band followed the picture down. A wide picture then pulled the
headline up under it and left the foot of the frame empty, and the headline
jumped to a different height on every story. The eye should find the news in
the same place eight times running; the picture is what is allowed to vary.

**The margins still clear the platform.** Instagram's Reels header is about
120px on a 1080×1920 frame, and username + two caption lines + audio about
340px. A test holds both, and the right margin is still the action rail's.

**Also fixed.** `KenBurns.frame` could compute a crop a fraction of a pixel
outside its plate when a window has exactly the photograph's shape, and PIL
refuses a negative offset rather than rounding it. Clamped to the plate.

`brand/speednews.py :: StorySlate, Layout, _backdrop` · `brand/motion.py ::
KenBurns.frame` · `brand/tokens.py :: Motion.speed_top, speed_bottom` ·
`tests/test_speednews.py`

---

## D84 · The fact desk checks every published line, before and after writing

**Decided.** Every figure and name in every line that reaches a reader or a
listener — headline, reel_line, hook, deck, points, takeaway, narration — is
checked against the text of the source it cites. The text is kept per URL in
`inbox/sources/`. A figure not in the source fails the gate (`FACT-01`); a
source page that does not carry the story fails it (`FACT-02`); a story whose
source text we do not hold fails too, because nothing in it was checked and
an invented URL ends up exactly there (`FACT-03`); an unsupported word or
name is a warning to read (`FACT-04`).
`scripts/fact_check.py` runs it before render and in the 06:10 job.

**Why.** D63 checked the one-line lead the intake wrote. Nothing checked what
the desk wrote after it, and every later line is one a model can write. The
editor asked, on 2026-09-24, for a fact checker "before writing any news, any
sentence". The first run found all six of that day's `source_url`s were
model-written (`utm_source=gemini`, one slug beginning `english-heading-`)
and served a sidebar of other headlines — 85–100% of each story's words were
absent. The copy had been "sourced" to pages that did not carry it.

**A figure the source spells another way is proved, not waved.** The fact
desk records the exact sentence of the source in `inbox/factcheck/*.json`;
the check only accepts it if that sentence is in the kept source. That is
evidence a person can reread, and it cannot be used to pass an invented
number, because an invented number has no sentence. No override flag (D29).

**What it cannot do.** Decide the source is right; read Kannada copy against
an English article word for word (figures and Latin names are still
checked, and the report says the rest needs a person). `verified_by` stays a
human name (D59).

`brand/factcheck.py` · `scripts/fact_check.py` · `brand/review.py` (FACT-01..04)
· `brand/codes.py` · `tests/test_reach_copy.py :: EveryFigureIsInTheSource`

---

## D85 · A stock frame is earned by the story's words, scored — never by category

**Decided.** `brand/stock.py` scores every catalogued frame against the
story's own words, weighted by where they sit (headline / reel_line / hook
3, deck 2, points / takeaway 1), and attaches the best one only when it earns
`Limits.stock_match_min`. The category fallback is gone: a story nothing
matches is left for a fresh, story-specific frame. `python3 -m brand.stock
editions/X.json` prints every candidate, its score and the words behind it.

**Why.** The editor, 2026-09-24: images "not even nearest to the topic". The
old matcher took the FIRST table entry with any keyword anywhere in the
story, so one incidental word in the third fact beat three in the headline;
it fell back to one frame per category, which is precisely the lazy match
house rule 2026-09-20-01 forbids; it sent ಪರೀಕ್ಷೆ / ಫಲಿತಾಂಶ to the
certificate ceremony the editor had rebuked; it mapped ಸಾವು (death) to a
hospital; and it split keys on spaces, so no two-word key (ರೆಡ್ ಅಲರ್ಟ್,
ಕುಡಿಯುವ ನೀರು) could ever match. The eleven frames added since D80 were
never in its table. Keys are now actions and objects, not topics; a word
that described three different scenes was removed.

**Also.** Stock frames were credited `AI ಚಿತ್ರ — ಊರ್ಮನಿ ಸುದ್ದಿ` with a
caption repeating `(ಎಐ ರಚಿತ ಚಿತ್ರ)`, the stutter house rule 2026-09-17-05
forbids. Credit is the channel; the caption says ಸಾಂದರ್ಭಿಕ ಚಿತ್ರ.

**The picture-editor agent** does what scoring cannot: names the action,
reads the CATALOG "Visual" line, writes a structured 16:9 brief, and
describes every image blind before comparing it with the story.

`brand/stock.py` · `brand/tokens.py :: Limits.stock_match_min` ·
`.claude/agents/picture-editor.md` · `tests/test_stock.py`

---

## D86 · Five hashtags, and a trend only when the story is about it

**Decided.** An Instagram caption carries at most `Limits.ig_hashtags_max`
(5) tags: the town in Kannada, TownNews, one trend today that the story is
genuinely about, the subject, then ಕರಾವಳಿಸುದ್ದಿ / the channel. Every town the
tags cannot hold is written in a 📍 line in Kannada and English, which
Instagram's keyword search reads. YouTube descriptions carry 3 hashtags (the
ones shown above the title); the TAGS field is search phrases, fitted to 500
characters. `scripts/trending_tags.py` writes `inbox/trends_<date>.json` each
morning from Google Trends (Karnataka, then India); the trend-scout agent
adds what it can evidence from Instagram and YouTube. `brand/trends.py`
attaches a trend only when the story says its words — the whole phrase, or
two distinctive words of it. The gate fails a caption over five (`PUB-09`).

**Why five.** Instagram has read five hashtags per post or Reel since
December 2025 and ignores the rest; our carousel caption was carrying 28.

**Why not irrelevant trends, though the editor asked for them.** The goal is
reach, and an unrelated trend costs reach. YouTube's spam policy treats tags
and hashtags unrelated to the video as misleading metadata — the video is
removed and the channel gets a strike. Instagram shows a post to a small
slice first and widens it only if they stop and watch; a trend-seeker who
gets a Kundapura flood swipes past, and that is the signal that ends the
post's distribution. A trend the story is about is the opposite: the right
people, searching right now.

**House rule 2026-09-17-07** asked for every town and category in the
hashtags. That cannot survive a five-tag platform, so its intent — every
town discoverable — moved to the 📍 line, and the rule was superseded.

`brand/copy.py :: hashtags, edition_hashtags, place_line, youtube_tags` ·
`brand/trends.py` · `scripts/trending_tags.py` · `brand/review.py` (PUB-09) ·
`tests/test_reach_copy.py`

---

## D87 · The newsroom runs as a team of agents, in parallel, fact desk first

**Decided.** Four specialist agents in `.claude/agents/` — fact-checker,
picture-editor, social-writer, trend-scout — run in waves: trend-scout and one
fact-checker per story together; then one picture-editor per story and the
social-writer together; then render, the gate, and a post-render caption
audit. One agent, one story. `.agents/skills/second-brain/SKILL.md` carries
the order.

**Why.** Asked for by the editor on 2026-09-24. One generalist doing six
stories in sequence checks the first three carefully and the rest by
assumption; six fact-checkers each own one story. The waves exist because
the fact desk has to pass a story before anyone polishes its copy or picks
its picture — speed that runs ahead of the facts is how a wrong figure gets a
good font.

**What the agents cannot do** is anything a person is responsible for:
`verified_by`, the three sign-off seats, posting.

`.claude/agents/*.md` · `.agents/skills/second-brain/SKILL.md`

---

## D88 · Fresh, ours, a real article, and credited to the outlet it came from

**Decided.** `brand/sourcing.py` answers three questions for the intake, the
drafter and the gate alike. *Whose is it:* every `source_url` belongs to an
outlet (`OUTLETS`), and the story must credit that outlet — `FACT-06` fails
it otherwise. *Is it an article:* a section page, a link carrying a chatbot's
tracking tag (`utm_source=gemini`) or a placeholder slug is not a source —
`FACT-05`. *Is it today's:* the intake records when each tip was published
(the page's own metadata, the feed, or the date in the URL) in
`Tip.published_at`, shows it on the tip sheet, and drops anything older
than `Limits.news_max_age_hours`; a date with no time counts in calendar
days. The drafter also skips tips that name no coastal place
(`copy.is_coastal`, one registry: `PLACE_TAGS` plus the English press's
spellings) unless they are state news the coast lives with (house rule
2026-09-20-02), and fills `location` from the same registry. A new
`news-scout` agent runs the same four tests on anything the feeds miss and
on news the editor adds. The gate warns (`FACT-07`) when every source a
story cites predates its edition.

**Why.** The editor, 2026-09-25: news they added by hand ended up credited
to one paper, and the intake brought stale and unrelated stories. Measured on
the 24 Sept package: all six stories credited ಉದಯವಾಣಿ with chatbot-made links
(D84 found them), and the morning draft had carried four stories dated the
22nd, a Vartha Bharati section page as a "source", and a Kasaragod story —
while Puttur, Shirva and "Kundapur" stories read as not ours because the
place table held only Udupi taluks in Kannada spelling.

**News the editor adds keeps its own provenance** — a link is that outlet's,
a press release is its issuer's, what the editor saw is own reporting
(house rule 2026-09-25-01). Folding it under the paper the rest came from is
a false attribution, and it is what the sources slide then prints.

**Corrected the next morning by the fact desk itself.** Twelve fact-checker
agents, one per story, re-checked the 23 and 24 Sept editions and found two
things this decision first got wrong. Udayavani links are real articles: the
site loads the story text from a separate file (`news_section`, on its
CloudFront store), so a plain fetch saw only the sidebar and every Udayavani
link looked like a listing page — `fetch_daily_news._udayavani_body` now
reads what a browser reads, publish date included. And `english-heading-…`
is Udayavani's own slug, not a placeholder. Only the chatbot tag was bogus.
They also found Udayavani writes ೊ as two code points; matching is now NFC.
What the agents found in the COPY stands: of 12 stories, 10 carried claims
their source did not make — a denied death (Sharjah), an invented cause of
death, invented investigations — and 2 were dropped (a festival story after
the festival; a minor's death, 15 days old, with nothing new).

`brand/sourcing.py` · `brand/copy.py :: is_coastal, place_in, PLACE_TAGS` ·
`scripts/fetch_daily_news.py :: date_tips, drop_stale_and_unciteable` ·
`scripts/draft_edition.py` · `brand/review.py` (FACT-05..07) ·
`.claude/agents/news-scout.md` · `tests/test_sourcing.py`

---

## D93 · Universal Carousel Visibility Contract: Zero Phantom Fields & Special Segment Branding

*(Numbered D89 when written; renumbered D93 on 2026-09-27 because a second,
unrelated D89 — the dispatcher, below — already carried that number. Code
comments and gate codes PUB-10/PUB-11 that say "D89" about carousel
visibility mean this entry. The carousel and ಕಾನೂನು ಕವಚ it governed were
retired by D92.)*

**Context (2026-09-25):**
Two critical failures broke editorial trust on carousel posts:
1. **The "Half-Baked Carousel"**: `Story` JSON held key facts in `points` (e.g. 3 harsh reality consequences of a cyber crime FIR: job disqualification, passport denial, court trials). But `carousel.py` only rendered `headline` + `deck`, discarding `points` entirely. Decks ended with promises like "ಕಟು ವಾಸ್ತವ ಇಲ್ಲಿದೆ:" followed by empty black void. Readers saw half-baked news while the JSON looked complete.
2. **Hardcoded Regional Boilerplate on Special Segments**: Special awareness/rights series like `ಕಾನೂನು ಕವಚ` (digital cyber safety) were given hardcoded coastal branding: `ಕರಾವಳಿ ಬುಲೆಟಿನ್` on mastheads, `#ಕರಾವಳಿಸುದ್ದಿ` hashtags, `ಇಂದಿನ ಪ್ರಮುಖ ಕರಾವಳಿ ಮುಖ್ಯಾಂಶಗಳು:` on WhatsApp, and `forward_ಕರಾವಳಿ.txt`.

**Decisions:**
1. **100% JSON Visibility**: If `st.points` exists, `carousel.py` MUST render it using `cp.factlist` (gold numerals 01, 02, 03, subtle hairlines, and Kannada type). Zero phantom data in JSON.
2. **Visual Slide Budget & PUB-10 Gate**: When points follow, the deck functions as a concise 1–2 line lead-in (`max_lines=2`). If `headline + deck + points` overflows the card capacity (`src_top - 20`), the build FAILS with `PUB-10`. No slide may clip text.
3. **Points Capacity & PUB-11 Gate**: A carousel slide holds up to `Limits.points_max` (3) points. More than 3 points fails `PUB-11`.
4. **Special Segment Branding**: `brand/copy.py::is_special_series` detects non-bulletin series (`ಕಾನೂನು ಕವಚ`, explainers without coastal locations). For special segments:
   - Masthead displays segment strapline (e.g. `ಕಾನೂನು ಕವಚ • ಪ್ರಕರಣ 1`), never `ಕರಾವಳಿ ಬುಲೆಟಿನ್`.
   - Cover counter displays `{n} ಅಂಶಗಳು`, never `{n} ಸುದ್ದಿಗಳು`.
   - Closing slide footer displays segment title, never `ಕರಾವಳಿ`.
   - Instagram hashtags are topic-driven (`#ಕಾನೂನುಕವಚ #oormanisuddi #CyberSafety`), never `#ಕರಾವಳಿಸುದ್ದಿ`.
   - WhatsApp digest uses `{strapline} — ಪ್ರಮುಖ ಮುಖ್ಯಾಂಶಗಳು:`, never `ಕರಾವಳಿ ಮುಖ್ಯಾಂಶಗಳು`.
   - No regional `forward_*.txt` files are produced.

`templates/carousel.py` · `brand/review.py` (PUB-10, PUB-11) · `brand/copy.py :: is_special_series, edition_hashtags, edition_whatsapp, for_edition, taluk_forwards` · `brand/tokens.py` · `brand/codes.py`

---
## D89 · The team is dispatched by the state of the newsroom, not by memory

**Decided.** Twelve agents in `.claude/agents/`, each with one job, a jail
to this repository, a list of what it may not do, and a report formula.
Four are **proactive** — news-scout, trend-scout, planning-editor,
systems-steward — and are due when something is coming or missing. Eight are
**reactive** — fact-checker, legal-standards, kannada-editor, picture-editor,
social-writer, package-inspector, gate-doctor, corrections-officer — and are
due when something happened. `brand/dispatch.py` reads the state (editions,
kept sources, gate reports, calendar, complaint clocks, health) and returns
who is due, why, and in which wave; tasks in one wave run in parallel. Two
hooks make it automatic: at session start it prints the plan, and after any
command that RUNS render, fact_check, verify, draft, fetch or correction it
puts the newly due reactive work in front of the assistant.

Every agent files its report as a **receipt** stamped with a hash of what it
looked at, minus who verified it. Edit the story and the receipt stops
matching, so the agent is due again; sign it and nothing is re-done. A BLOCK
in a receipt goes to the person. Failing gate codes route to agents through
`CODE_AGENT`, one line per code family, beside `codes.OWNER` for people; a
test fails if a new family has no agent.

**Why.** The editor, 2026-09-25: reactive and proactive agents, a swarm, the
best output possible. The first five agents (D87) existed and nobody was
told when to run them, so they ran when someone remembered. Seven stages had
no specialist at all: the legal read (the Sharjah headline that denied a
death), Kannada copy, looking at rendered frames (the fake nameplate), gate
repair, corrections under the IT Rules clocks, planning ahead of festivals,
and the machine itself (backups nine days stale that morning).

**What stays human** is unchanged and enforced by test: no agent file may
carry a sign-off or verify command; `verified_by`, the sign-off, uploading,
legal flags and answering a complaint are listed under "needs a person".

**The hook's first live day** it fired on a heredoc that only mentioned
`verify.py`. It now reacts only to a command that runs a pipeline script on
its first line; a test holds eight such cases.

`brand/dispatch.py` · `scripts/dispatch.py` · `.claude/agents/*.md` ·
`.claude/settings.json` (SessionStart, PostToolUse:Bash) ·
`tests/test_dispatch.py`

---
## D90 · A render folder belongs to one edition, and says which

**Decided.** `render.py` names an edition's output folder after the edition
FILE (`out/<stem>`), not its date, and stamps the folder with
`.edition` — the edition it was made from. It refuses to render into a
folder stamped for a different edition. The daily file is
`editions/<date>.json`, so the daily folder is still `out/<date>`. The
dispatcher reads the stamp and will not inspect or gate a folder "for" an
edition it does not hold; it tells the person instead.

**Why.** Found by the package-inspector agent on its first run, 2026-09-25:
the ಕಾನೂನು ಕವಚ explainer, dated the same day as the news, rendered into
`out/2026-09-25` and replaced that day's news carousel; one stale news frame
was left behind among the explainer's. Nothing in the pipeline noticed,
because every check looked at a folder that was internally consistent — it
was just the wrong edition's.

**Also from that run.** Two more stock frames carried AI-made text — a court
sign naming ಕುಂದಾಪುರ and a "Burglary Case: 142/2023" label — and are no
longer offered by `brand/stock.py`, as with the fake nameplate (D85).

`render.py` · `brand/dispatch.py :: owner_of` · `brand/stock.py` ·
`tests/test_dispatch.py :: ARenderNeverOverwritesAnotherEdition`

---
## D91 · A stock frame with text in it is never attached automatically

**Decided.** `brand/stock.py :: WITHDRAWN` lists every catalogued frame that
carries AI-made text a reader would take as fact — a town, a name, an
institution, a number plate, a case number — or shows something that may
not have happened; `candidates()` never offers one, whatever the story says.
Each entry says why. A frame leaves the list only by being regenerated with
no text at all. 14 frames remain auto-attachable; everything else gets a
fresh, story-specific frame from the picture desk.

**Why.** The systems-steward agent opened all 39 frames on 2026-09-26: 21
carried text — "UDUPI TRAFFIC" on a jeep used for any town, a court sign
naming ಕುಂದಾಪುರ, an officer's nameplate for a man who does not exist, a
banner for a university, a leopard already inside the trap. 17 were still
in the matcher, including the four that match every crime and accident
story. Three had been pulled one at a time as they were caught (D85, D90);
a register is how the next one is not caught in a published carousel.

**Found in the same run, and fixed:** every scheduled 06:10 / 07:00 intake
since 2026-09-18 had died on `import numpy`, because launchd's bare PATH
finds macOS's own Python 3.9 (`scripts/morning.sh` now picks the first
Python that can import the engine); and `scripts/health.py` read a fresh
backup as nine days old, sorting by name instead of time.

`brand/stock.py :: WITHDRAWN` · `scripts/morning.sh` ·
`scripts/health.py :: check_backups` · `tests/test_stock.py ::
AFrameWithTextInItIsNeverAttached`

---
## D92 · Three formats, one story in one of them, pasted news, real pictures first

**Decided (2026-09-27, the year's final upgrade).** After a month on air the
owner and co-founder found the channel repetitive — the same stories every day
as a carousel AND a reel, in the same dark look — and built on AI pictures and
scraped leads. From this decision on:

1. **Three news formats, and only three.** Everything else was deleted.

   | key | name | shape | pictures |
   |---|---|---|---|
   | `roundup` | ಸ್ಪೀಡ್ ನ್ಯೂಸ್ | 9:16 reel, one frame per story | a picture if the story has one; otherwise a type-only frame |
   | `saara` | ಸುದ್ದಿ ಸಾರ | 4:5 carousel: index cover → one slide per story → sources | **never** — it is the text bulletin |
   | `mukhya` | ಮುಖ್ಯ ಸುದ್ದಿ | 4:5 carousel for ONE story: photo cover → ಏನಾಗಿದೆ? → source & corrections | **always** — breaking and top stories |

   Festival greetings (`greeting`) and the two footage skills stay; they are
   not news formats.

2. **One story, one format.** Every story carries `segment` — `speed`,
   `saara` or `mukhya` — and is rendered in that format only. A story cannot
   be on the ಸುದ್ದಿ ಸಾರ and in the ಸ್ಪೀಡ್ ನ್ಯೂಸ್ on the same day: the field
   holds one value. The editor says which; when they do not, the desk proposes
   and the editor confirms before anything renders. A story already published
   on an earlier day is refused (DUP-01) unless it is a real follow-up
   (`follows_up`, with a new fact).

3. **Real pictures first; AI only when there is none, and only after asking.**
   A ಮುಖ್ಯ ಸುದ್ದಿ cannot render without a picture (IMG-04), and the desk may
   not supply one on its own: the story records the editor's answer in
   `photo_plan` — `real` (the editor is sending a photograph) or `ai` (the
   editor said generate). Every AI picture carries `photo.approved_by`, the
   name of the person who said yes; `Photo.validate()` refuses one without it.
   An AI picture never shows an identifiable face standing in for a real,
   named person. The stock library is gone: a reused generated frame was
   wrong-topic, carried invented text, and repeated across days (D85, D91).

4. **Pasted news in, no scraping.** The editor pastes copy and says what to
   make. The pasted text is kept as the story's source
   (`scripts/intake.py source`), the fact desk checks every figure against it
   offline, and a person still verifies (D59). The morning fetch, the
   automatic draft, the trend scraper and their schedule are deleted.

5. **One look — Paper & Red.** Light paper, ink type, the logo's exact colours
   (`tokens.C`): red for the news (the kicker, ಬ್ರೇಕಿಂಗ್, the half of a
   headline after its colon), sunset gold for the brand (the line under every
   photograph, the stroke under the red wordmark, numeral chips, accent
   rules). Gold is a fill on paper, never small type; gold type uses
   `gold_800`. Crime and death headlines are ink only — no red on a person's
   name. Left-aligned, one heavy weight (the headline), square corners. The
   Grievance Officer line stays on every closing slide (IT Rules 2021).

**Why.** The month's record: seven days of carousel + speed news on the same
stories; 21 of 39 stock frames carrying fake text; a photoreal "SP" standing
in for a named officer; 10 of 12 stories on 23–24 Sept carrying claims their
source did not contain (D84, D88); a morning fetch that ran 2h43m when it ran
at all. Each of the five points above removes a cause rather than adding a
check on top of it.

**Retired by this decision:** D25 (every slide carries a visual), D32–D41 and
D43–D44 (post cards, thumbnail, broadsheet, 16:9 bulletin, the lead reel as a
daily format), D76 (the morning draft), D80, D85, D91 (the stock library),
and the daily-default half of D81. Their text stays above as the record.

`brand/content.py :: Story.segment, Story.photo_plan, Photo.approved_by` ·
`templates/saara.py` · `templates/mukhya.py` · `brand/paper.py` ·
`brand/speednews.py` · `brand/review.py :: IMG-04, DUP-01` ·
`scripts/intake.py` · `tests/test_formats.py`

---
## D94 · The distribution plan: where each format goes, and when

**Decided (2026-09-27)**, from the owner's coastal distribution strategy,
checked against what this channel's own data and decisions already say.

**Adopted**
- **Times** (`Limits.carousel_slot`, `mukhya_slot`, `roundup_slot`): ಸುದ್ದಿ
  ಸಾರ 08:00, ಮುಖ್ಯ ಸುದ್ದಿ 13:30 (or the moment a breaking one clears),
  ಸ್ಪೀಡ್ ನ್ಯೂಸ್ 18:30 as the evening round-up. Starting positions;
  `scripts/metrics.py` moves them.
- **Facebook** gets the same carousels and reels as Instagram. For town
  groups, `facebook_group_<k>.txt` per ಮುಖ್ಯ ಸುದ್ದಿ: the news, then a
  question to the town, and no outside link. One post per group per week at
  most, so admins do not block the page.
- **WhatsApp community** in three area groups — ಕುಂದಾಪುರ–ಬೈಂದೂರು,
  ಉಡುಪಿ–ಬ್ರಹ್ಮಾವರ–ಕಾರ್ಕಳ, ಮಂಗಳೂರು — admin-only, at most
  `Limits.whatsapp_items_max` stories a day each, written as
  `whatsapp_<group>.txt` (`brand/copy.py :: community_digests`). The
  per-town forwards (D72) stay.
- **The join link** is on every closing slide, so a card forwarded into a
  family group leads its new reader back.
- **Gulf & NRI** gets its own category (`nri`, ಅನಿವಾಸಿ).
- **Bilingual Shorts titles** (Kannada | English place + topic) for the
  real-footage Shorts made by the reels-shorts-edit skill.
- **Shares and saves over likes** — already how this channel measures reach
  (D72, `Limits.local_reach_floor`); the closing slide asks for both.

**Not adopted, and why**
- **Posting ಸ್ಪೀಡ್ ನ್ಯೂಸ್ to YouTube Shorts.** AGENTS rule 9: on this
  channel, AI-voiced card reels averaged 37 views on YouTube against 397 for
  real footage, the latest at 1–4. YouTube gets real footage only.
- **A dark navy / slate background with white and yellow type** for ಸುದ್ದಿ
  ಸಾರ. The owner chose the light Paper & Red look in the logo's colours (D92).
- **Broad tags** (#KannadaNews, #BreakingNewsKannada) and more than five
  hashtags. D86: Instagram reads five, and place tags reach the people a
  local story is for.
- **"A real photograph, always" for ಮುಖ್ಯ ಸುದ್ದಿ.** Kept as the first
  choice; the owner's rule is to ASK before any AI picture (D92), not to
  forbid one.

`brand/tokens.py :: Limits` · `brand/copy.py :: publishing_plan,
community_digests, facebook_group_post` · `templates/saara.py` ·
`templates/mukhya.py` · `docs/CHANNELS.md` · `tests/test_formats.py`

---
## D95 · The desks are not optional

**Decided (2026-10-01).** The Chief Editor gate refuses `APPROVAL.md` while
any desk the dispatcher lists for an edition has not read it in its CURRENT
wording, or has blocked it — `OPS-04`, from `brand/dispatch.py :: desk_gaps`,
the same function the plan uses, so the gate and the plan cannot disagree.
`scripts/sign_off.py` refuses while any rendered format has not been
inspected, or the paste files not audited, since the last render
(`inspection_gaps`). The social-writer's audit now covers every paste file —
captions, the WhatsApp community posts and the Facebook group posts (D94).

**Why.** The first ಸುದ್ದಿ ಸಾರ (2026-09-27) was approved with no desk having
read it. The waves were advice, and on a busy morning advice is skipped: it
shipped a death headline in red, three stories under the wrong category and
two wording slips — each the job of a desk that never ran. There is no
override: a desk that is skipped under deadline is the whole failure.

**Who does what** is one table, in `docs/RUNBOOK.md` → "Who does what".

`brand/dispatch.py :: desk_gaps, inspection_gaps` · `brand/review.py :: OPS-04`
· `scripts/sign_off.py` · `tests/test_dispatch.py :: TheDesksAreNotOptional`

---
## D96 · A footage reel's news layer is laid out around Instagram, not over it

**Decided (2026-10-01).** A news reel made from real footage carries one
fixed layer (`brand/reel_news.py`, the `news` block of the reels-shorts-edit
skill): a 2-second hook in huge type; the red bug with place and date below
Instagram's header; a paper story card above the caption and left of the
buttons, carrying the headline and one fact at a time; and a paper end card
with the source, the footage credit and who verified it. Instagram's own
interface is measured once, in `tokens.ReelsChrome`, and every text box is
checked against it — a layout that would touch it is refused, not drawn.
Nothing on any frame is smaller than 28 px. Death headlines stay ink.

**Why.** The MRPL reel of 30 Sept 2026, as seen on the owner's phone: the
masthead sat under "← Reels", the date under the camera icon, the card under
the like/share column, and a source line was too small to read. The skill's
own safe zone started the top at 230 px — Instagram's header reaches 250.

`brand/reel_news.py` · `brand/tokens.py :: ReelsChrome` ·
`.claude/skills/reels-shorts-edit/tools/reel_build.py` ·
`tests/test_reel_news.py`

---
## D97 · An Instagram reach desk, and fewer agent runs for the same checking

**Decided (2026-10-03).**
1. **A reach desk.** `instagram-strategist` runs once per edition, after every
   story has a segment: format fit, cover hooks, text load, the slot, the first
   comment and the first-hour plan, from `docs/INSTAGRAM.md`. It is a desk like
   the others — due until it has read the edition's current formats and
   categories (`desk_gaps`, `OPS-04`) — but its hash is the strategy fields only
   (`segment`, `category`, `location`, `published_at`, `photo_plan`), so a Kannada
   copy edit never sends it round again. The social-writer audits the posts
   against the same playbook; the planning-editor's weekly review keeps it
   honest. `MASTER_COPY.md` carries the first-hour checklist and the alt text.
2. **Every line of the playbook is labelled** [Official] / [Reported] / [House] /
   [Data]. Only two posts were ever logged, so nearly all of it is [House]: a
   hypothesis. `scripts/metrics.py` now also takes `--nonfollowers` (the growth
   signal) and the new format names, and the dispatcher asks the editor for the
   week's numbers when the log goes quiet. No multiplier is written down that
   the numbers do not show.
3. **Batched runs.** The plan is launched as AGENT RUNS: a per-story desk reads
   up to `Limits.agent_batch_max` stories in one run and files a receipt per
   story, against that story's own hash (`--story 1 2 3`). The gate still asks the
   per-story question. A six-story day is 5–6 runs, not 15–18; every spawn
   re-loads its instructions and conventions.
4. **Every agent pins its model** (`sonnet`), so what a run costs does not depend
   on which model the chat is on. The house-rules printout at each render is one
   short line per rule.
5. **No forged receipts.** `scripts/daily_flow.py receipts` used to write PASS
   receipts for desks that had not run; it now only shows what is due.

**Why.** The owner asked for someone who understands Instagram and the people on
it, and for the same quality at lower token cost. The cost was the spawn count
and re-reading the same text, not the thinking; the shortcut that had appeared
to save it defeated the gate that exists because of the 27 Sept slips.

`brand/dispatch.py :: launches, strategy_hash, _insights_task` ·
`.claude/agents/instagram-strategist.md` · `docs/INSTAGRAM.md` ·
`scripts/metrics.py` · `tests/test_dispatch.py :: TheTeamRunsInBatches…`

---
## D98 · Every carousel slide has an animated twin: the scan wipe

**Decided (2026-10-03).** `python3 render.py editions/DATE.json --animate` makes
a `.mp4` beside every ಸುದ್ದಿ ಸಾರ and ಮುಖ್ಯ ಸುದ್ದಿ slide, to be posted as a video
carousel (Instagram lets a carousel be videos, and a video in a carousel loops
until the reader swipes). Each line of text is revealed left to right behind a
thin gold edge, top to bottom (`Motion.anim_*`: lines start `anim_gap` apart,
the whole reveal is at most `anim_reveal_max`); the finished slide then HOLDS
for `anim_hold`, because the hold is what gets read. A photograph fades in
first. The red bug, date, footer and swipe tab never move.

`brand/animate.py` works from the finished PICTURE — it finds the lines of text
— so every present and future slide animates the same way, and the last frame
is the static slide. Nothing is ever revealed letter by letter: cutting a
Kannada conjunct shows broken shapes, so whole lines are wiped.

**Why.** The owner chose the scan wipe from four demos (word pop, swipe push,
mask rise, scan wipe) and asked for it as the carousel itself, in the style of
news-brand carousels. The static slides remain the source of truth and the
fallback.

`brand/animate.py` · `brand/tokens.py :: Motion.anim_*` · `render.py --animate` ·
`tests/test_animate.py`

---
## D99 · The scan wipe, refined to a premium standard — and on by default

**Decided (2026-10-03).** The owner asked for the animated carousels to be
taken to a premium, "luxurious" standard and made the final version. What
changed from D98, and why:

* **Flow, not a queue.** Lines used to start 0.42 s apart, each a hard-edged
  wipe — it read as typing. Now each line wipes through a soft 70 px feathered
  edge and the next starts 0.13 s later (0.18 s between headline lines, a
  0.22 s beat between blocks), so the page fills like one wave in at most
  `anim_reveal_max`. Headline lines also settle up `anim_rise` px. The easing
  is a cubic-bezier with a gentle start and a long settle.
* **The gold edge became a light.** A thin gold line with a soft halo — the
  logo's sun — that rides only on the letters (it goes out across the gap
  between a kicker and the slide number) and fades as the line completes.
* **A cover is never blank.** In D98 a cover opened on empty paper. But the
  profile grid and a fast thumb see frame 0, and a stranger gives a post one
  second (INSTAGRAM.md §2). Now the photograph and the headline — the
  stop-sign, found as the first run of display-size lines with its kicker —
  are there at frame 0, and what follows is revealed.
* **The hold is long enough to read.** D98 held 5 s; a story slide carries
  ~280 Kannada characters, 40 s at `read_rate`. Video carousels loop, and a
  loop that wipes the text away mid-read is hostile. The hold now follows the
  type on the slide (estimated from the picture, measured against the
  fixture: 288 estimated, 285 typed) between `anim_hold` and `anim_hold_max`.
* **The slide asks to be swiped.** While it holds, the chevrons on the edge
  tab and in the footer nudge right — two soft taps every `anim_nudge` s.
* **No seam.** The last `anim_out` s dissolve back to frame 0, so the loop
  starts again as if it were the first play.
* **The edge tab** is rounded where it meets the page and square at the
  screen edge, its chevron centred with room to nudge. The only change to a
  still slide; the golden renders were re-blessed after looking at them.
* **On by default.** `render.py` makes the videos unless `--still` is given:
  an option the operator must remember is an option that gets forgotten.

Considered and left out: a Ken Burns push on the photograph (the bug and the
credit are drawn on it, and would zoom with it); a shimmer over the headline
(the owner has twice rejected decoration that reads as AI-made); sound
(carousel videos play muted).

`brand/animate.py` · `brand/tokens.py :: Motion.anim_*` · `brand/paper.py :: edge_tab` ·
`render.py --still` · `tests/test_animate.py`

---
## D100 · A carousel is separate slides, drawn as one sheet across the swipe

**Decided (2026-10-04).** The owner, after seeing a stitched preview: "make
sure carousels are carousels, not one video — and perfect transitions when
the user swipes."

* **Separate slides.** The engine has always written one .mp4 per slide; the
  joined file was only a preview. That is now stated where it is acted on:
  `schedule.txt` says "ONE carousel post of N separate videos … never join
  them", and a test proves each video is a single 1080×1350 slide.
* **The swipe is Instagram's** — the native, finger-driven slide. A
  transition baked into a video would fight it. What the design controls is
  what the reader sees DURING the swipe: slide N's right edge against slide
  N+1's left edge. So every seam is continuous: the footer hairline runs to
  every inner edge (one line from the first slide to the last), and the red
  edge tab meets a new red landing mark at the same height on the next
  slide, so mid-swipe the two are one pill across the seam — the carousel
  reads as one sheet of paper being pulled along. The landing mark is
  chrome: it is there at frame 0, which is the frame the reader swipes into,
  and the lines start to flow the moment the slide lands.
* The landing mark is 16 px wide (the tab is 40) so it never crowds the
  text at the 64 px margin. On ಮುಖ್ಯ ಸುದ್ದಿ slide 2 it sits at the cover's tab
  height, half-way down the photograph.

`brand/paper.py :: landing, footer(seam=)` · `templates/saara.py` ·
`templates/mukhya.py` · `brand/animate.py` (the landing mark is chrome) ·
`brand/copy.py :: publishing_plan` · `tests/test_animate.py`

---
## D101 · Every frame is a safe thumbnail: a whole cover, and pencil before ink

**Decided (2026-10-04).** The owner: Instagram asks for a thumbnail (cover
frame) when a video carousel is posted, and picking the first slide's frame
is a problem for all the slides. They left the design to us.

Instagram takes the post's thumbnail — the profile-grid tile — from the first
video, and lets the editor scrub to any frame. D99 opened every slide on
paper and revealed it, so the default frame was a half-built or empty slide.
Now **no frame is ever unfinished-looking**:

* **A cover is whole at frame 0.** Nothing on it is revealed; the gold light
  passes over its lines (and the swipe bar) instead, swelling and fading as
  it goes. The default thumbnail is the finished cover.
* **Slides after the cover open as pencil, then ink.** Frame 0 is paper, the
  chrome and a faint outline of the slide's own layout (`anim_ghost`, 12 %);
  the ink wipes in over it. The settle-up (`anim_rise`) is gone — the layout
  is already in place, and a rising line would double against it.
* **Any frame after ~4 s is a finished slide, on every slide** (reveal ends
  ≤ 3.6 s; the loop dissolve only starts in the last 0.5 s), so one scrub
  position is safe for the whole carousel.

Considered: a one-frame "poster" of the finished slide at frame 0 on every
slide (a flicker on every swipe), and a separate cover picture (Instagram
does not take one for carousel videos). The posting plan now says: keep the
default thumbnail.

`brand/animate.py` · `brand/tokens.py :: anim_ghost, anim_rise` ·
`brand/copy.py :: publishing_plan` · `tests/test_animate.py`

---
## D102 · The render folder holds what gets posted; the stills move to _review/

**Decided (2026-10-04).** The owner asked for everything to be made right and
to work the same way from now on. Changes made outside the session had
already started to deliver the carousels as videos only; three things in
them were unsafe, and are fixed here:

* **The stills are moved, not deleted.** `render.py` used to delete each
  carousel `.jpg` once its `.mp4` existed. The still is the exact finished
  slide — what the package inspector reads and the feed-size sheet is made
  from — and if the evidence step had failed, the delete would have lost the
  only copy. Now it moves into `out/<date>/_review/`; `out/<date>/` holds the
  .mp4 slides to post, the captions and the paste files.
* **A frame taken from a video is a finished frame.** Where no still exists,
  the evidence frame was taken at 0.5 s — since D101 that is a pencil outline
  or a half-wiped line. It is now taken from the held part of the video.
* **A render cannot hang.** `animate_all` encodes slides in parallel with
  spawned worker processes, which re-import the program that started them. A
  program typed into `python3 -` cannot be re-imported, so every worker died
  and was replaced, silently, for ten minutes (it happened on 2026-10-04).
  The pool is now used only when the program is a real file; otherwise the
  slides are encoded one at a time.

Kept from those changes: the three segments render on threads, the slides
encode in parallel, and the docs say carousels are animated video slides.

`render.py :: _finish, stills_dir` · `brand/review.py :: evidence` ·
`brand/animate.py :: animate_all` · `tests/test_animate.py :: TheDeliveryFolder`

---
## D103 · The ಸುದ್ದಿ ಸಾರ cover is a front page: one lead, the rest as teasers

**Decided (2026-10-05).** The owner was not happy with the first slide and
chose, from four drafts made with the day's real stories (A front page,
B towns, C big number, D top three), **A · ಮುಖಪುಟ**.

The index cover set every headline at the same weight. On a six-story day
(4 Oct) it was a wall of bold two-line text with nothing to look at first,
grey texture at profile-grid size, and — as 27 Sept showed — it gave the
whole day away, so readers stopped at slide one.

Now:
* **The lead.** The edition's FIRST saara story is set as a headline in the
  house grammar (place in ink, the news half in red; ink only for crime and
  death), as large as the day leaves room for — up to `LEAD_HI` on a light
  day, down to the house floor on a full one. Its kicker sits above it.
* **The teasers.** Every other story is one line, pinned above the swipe
  bar under "ಇನ್ನಷ್ಟು ಇಂದು": its place in red (the headline's own place,
  else its location, else its category), then as much of the rest as fits,
  **cut at a word** — never inside an akshara, where a cut shows a broken
  conjunct. Its own slide carries it in full.
* **Order matters now.** The intake desk orders saara stories lead-first and
  says why; the editor's word wins.
* A cover that cannot hold the lead and every teaser is refused with a
  reason (ContentError), never drawn over the footer.

The animation (D101) is unchanged: the cover is whole at frame 0 and the gold
light passes over the lead and the teasers.

`templates/saara.py :: saara, _teaser, _one_line, LEAD_HI` ·
`.claude/agents/intake-editor.md` · `tests/test_formats.py :: TheFrontPageCover`

---
## D104 · The ಸುದ್ದಿ ಸಾರ cover moves as a running order

**Decided (2026-10-06).** The owner was not happy with the cover's animation
(D101: a gold light sweeping over every line of the finished page). From
four previews on the 4 Oct cover — A peek, B running order, C spotlight,
D calm — they chose **B · running order**.

* The cover stays whole from frame 0 (the thumbnail, D101). Nothing passes
  over it any more.
* From `anim_order_start`, a soft gold underlay (`anim_order_tint`) and a
  red tick at the left edge light ONE teaser at a time, top to bottom, each
  for `anim_order_step`, then a rest beat — like a newsroom's running order
  being read down. The tint goes only where the page is paper: the type is
  never touched. The lead and its kicker are never lit.
* The cover runs whole rounds, so the loop comes round in step with the
  order; the hold stays under `anim_hold_max`.
* The teasers are found from the picture — a light hairline, then a line
  that opens with a red place name — so the black rule under the header
  never makes the lead's kicker a teaser, and the order follows however many
  stories the day has.
* A cover with no teasers (ಮುಖ್ಯ ಸುದ್ದಿ) keeps only the chevron nudge.

`brand/animate.py :: analyse (teasers), plan (order), _running` ·
`brand/tokens.py :: Motion.anim_order_*` · `tests/test_animate.py`

---
## D105 · The carousel render, eleven times faster

**Decided (2026-10-06).** The owner: the daily carousel takes too long —
make it as fast as possible. Measured on the 4 Oct edition (8 slides) on
the studio Mac (4 performance + 4 efficiency cores): **120 s → 10 s**, with
the same frames and better picture quality.

Where the time was, and what changed:
* **The animation (113 s of 120).** Every 23-second slide video pushed ~700
  full frames through a pipe into a `medium` x264 encode, eight at once with a
  dozen threads each on eight cores. Now:
  - **One period, copied.** The hold's motion repeats exactly — a chevron
    tap every `anim_nudge`, or one round of the running order — so one
    period is encoded and joined N times by stream copy (no re-encode). Only
    the opening and the ending are drawn frame by frame. The frames are the
    ones the long way made: the motion is periodic to the frame.
  - **8-bit frames, float only where it moves.** A frame starts from the
    finished slide; only the strips moving at that instant are computed in
    floating point; a finished line is a single `minimum`.
  - **`veryfast` at a FIXED quantiser** (`-qp 16`, no macroblock-tree). A
    quality target (CRF) looks ahead, so the same still encoded a shade
    differently in each segment — a faint shimmer at every join, which the
    tests caught. At a fixed quantiser the same picture encodes the same way
    wherever it falls. Held-frame PSNR against the still: 52 dB (was ~48).
    Files are 3–4 MB a slide.
  - **The cores shared out**: half the cores as workers, the rest as encoder
    threads (8 × 1: 15.5 s, 4 × 2: 9.9 s, 2 × 4: 11.1 s, serial: 15.1 s).
* **The still slides (5.3 s → 1.7 s).** Layout fitting measured the same
  words at the same sizes 55,000 times; text widths and ink extents are now
  cached (`typo._length`, `typo._extents`).

`brand/animate.py :: _period, _encode, _join, X264, animate_all` ·
`brand/typo.py` · `tests/test_animate.py` (unchanged guarantees, now 5× faster to run)

---

## D106 · A day, a source and an archive stay inside the contract

**Decided (2026-10-06).** The render was already right. Four gates were
looser than the words next to them, and each one fails on a deadline.

**Decided.**
* A day argument is `YYYY-MM-DD` and a real calendar day. Archive, discard
  and the daily flow resolve it and then refuse a path that leaves the
  project, before they create or delete anything.
* Stop keeps the files a phone posts from: `forward_*.txt`,
  `facebook_group_*.txt`, `REACH.md`, captions, WhatsApp copy and
  `MASTER_COPY.md`. The mp4s are still deleted.
* A source URL is an http(s) URL with a host. `http:not-a-url` is refused
  at validation, and the source slide no longer crashes on it.
* Own reporting, a press release, and a statute waive the URL only when a
  source *entry* is exactly that mark. A wire credit that mentions POCSO
  is still a sourced story.
* The daily-flow sign-off hint prints `<name>` until the editor gives one.
  Gemini TTS sends its key in a header, not in the URL.

**Replaced.** `startswith('http')`, a substring match on the source list,
an archive keep-list that dropped the circulation files, and `..` joined
onto `out/` before `rmtree`.

**If you undo it.** A bad date can delete a folder outside this repo, Stop
throws away the town forwards, and a story whose credit merely contains
"POCSO" renders with no link to reopen.

`brand/content.py :: edition_day, path_inside, http_url, is_own_reporting` ·
`scripts/archive_edition.py` · `scripts/discard_edition.py` ·
`scripts/daily_flow.py` · `tests/test_archive_edition.py` ·
`tests/test_discard_edition.py` · `tests/test_contract.py`

---

## D107 · A render folder holds this render and nothing older

**Decided (2026-10-06).** Each format clears its own previous output — the
slides, their stills in `_review/`, their copy — before it is drawn, and the
town forwards and WhatsApp posts are rebuilt from the whole edition every
time. `render.py --only saara` touches nothing of `mukhya` or `roundup`; a
full render clears a format the day no longer has. The render lock is taken
before the folder is stamped or touched.

The gate adds `PKG-06`: each carousel in the folder must run 01 cover → … →
one closing source slide, with no gap, no double and nothing after the close.

**Replaced.** Overwrite-in-place. A day re-rendered with one story fewer kept
`saara_05.mp4` and `saara_06_sources.mp4` from the earlier render beside the
new `saara_05_sources.mp4`; `schedule.txt`, derived from the folder, told the
editor to post "6 separate videos … saara_06_sources" — the cut story among
them. The gate checked that every named file existed, never that every file
present belonged.

**If you undo it.** Dropping a story after the desks — the most ordinary
deadline change there is — publishes it anyway.

`render.py :: FORMAT_FILES, EDITION_FILES, clear_previous` ·
`brand/review.py :: carousel_sequence_problems` · `brand/codes.py` PKG-06 ·
`tests/test_package_integrity.py`

---

## D108 · A signature covers the package it was given for

**Decided (2026-10-06).** `sign_off.py` records, beside the names, a
fingerprint of everything a person posts or sends from the folder — every
`.mp4`, `.jpg`, `.png` and `.txt` at its top level. `is_signed()` is true only
while that fingerprint still matches. Change a slide, add one, re-render with
different bytes, and the package is unsigned again; `APPROVAL.md` says it was
signed for a different render. Seats signed for an earlier render do not carry
over when the remaining seats are signed later. The gate's own bookkeeping
(`APPROVAL.md`, `review_report.json`, `build.log`) does not unsign.

A signature written before this existed has no fingerprint; it counts only
while it is newer than every posted file, so the packages already signed stay
signed and a later render still unsigns them.

**Replaced.** `SIGNOFF.json` survived a re-render. The next `APPROVAL.md`
read "Signed. Cleared to publish." over slides nobody had looked at, which is
the exact overclaim D62 exists to prevent — and `discard_edition.py` refused
to discard a package on the strength of it.

**If you undo it.** A person's name ends up on a package they never saw.

`brand/review.py :: package_fingerprint, signature_current, signed_seats,
is_signed, sign` · `scripts/sign_off.py` · `brand/dispatch.py` ·
`tests/test_package_integrity.py`

---

## D109 · The guilt guard follows the words, not the category

**Decided (2026-10-06).** `Story.validate()` still checks every crime and
breaking story against the whole of `GUILT_ASSERTING` (D29). A story filed
under ANY other category is now checked too — headline, reel_line, hook and
the joined copy — against the words that can describe nothing but a person
committing a crime (ಕೊಲೆಗೈದ, ಲಂಚ ಪಡೆದ, ವಂಚಿಸಿದ, ಥಳಿಸಿದ, ಕದ್ದ …). Words with
an innocent sense — ಕೊಂದ for an animal, ಸುಟ್ಟ for a fire, ಇರಿದ for a bull,
ನಾಶ ಮಾಡಿದ for the rain — are listed in `NOT_ONLY_CRIME` and stay crime-only.

A guilt word now counts only where a word begins, so ನಿರ್ದೋಷಿ ("acquitted")
no longer reads as ದೋಷಿ; the idiom ಕದ್ದುಮುಚ್ಚಿ ("secretly") no longer reads as
ಕದ್ದ.

**Replaced.** A guard scoped by `category`, which a desk — often a model —
chooses. A bribe filed as civic news, a killing filed as an accident or a
fraud filed under farm skipped the guard entirely. And an acquittal headline
was refused as a guilt assertion.

**Measured (D61).** Nine rows were added to `tests/legal_corpus.json` first:
five misfiled crimes (all five got through before the change), and four safe
lines in other categories. Two more safe rows — the acquittal and the idiom —
failed before the word-boundary change. All 48 rows now land.

`brand/content.py :: NOT_ONLY_CRIME, asserts_guilt, _check_criminal_reporting`
· `tests/legal_corpus.json` · `tests/test_legal_corpus.py`

---

## D110 · A moment's network trouble does not change the voice

**Decided (2026-10-06).** Every TTS request — Google's chunks and Gemini's —
goes through `voice._fetch`, which retries a dropped connection, a timeout, a
429 or a 5xx up to `NET_ATTEMPTS` times with a doubling back-off. A refusal of
the input (another 4xx) is not retried. A failed Google synthesis no longer
leaves its chunk folder behind.

**Replaced.** One `urlopen` per chunk. A single dropped request failed the
whole beat over to the next engine in `FALLBACK_ORDER` — the neural voice the
native ear rejected (D53) — so a reel could go out in two voices because of
one bad second on the network.

`brand/voice.py :: _fetch, NET_ATTEMPTS, NET_BACKOFF` · `tests/test_reliability.py`

---

## D111 · No script splits a paste or guesses an outlet

**Decided (2026-10-06).** `scripts/daily_flow.py intake` is retired; it now
refuses and names `scripts/intake.py source`, one story at a time, or the
intake-editor agent. Its other subcommands stay.

**Replaced.** A regex batch intake that treated every line holding a link as
a story, kept that one line as the story's "source", and credited any link it
did not recognise to ಉದಯವಾಣಿ — the misattribution FACT-06 and house rule
2026-09-25-01 forbid. It also pre-wrote fact-check evidence for Kannada
number words; its patterns could never match (a `\b` after a vowel sign), and
had they matched, a common word like ಒಂದು would have been filed as evidence
for any "1" in the copy.

**If you undo it.** Stories credited to a paper that never ran them, checked
against a one-line "source".

`scripts/daily_flow.py` · `tests/test_intake.py`

---

## D112 · The backup keeps the record once, and prunes what it says it prunes

**Decided (2026-10-06).** Each item in `archive/` — a day's published
record, or any file over 1 MB — is tarred once into `.backups/record/` and
re-tarred only when something in it changes. The nightly tarball now holds
only the small registers: the pasted sources, the calendar and `archive/`'s
loose ledgers. Pruning reads one path per line, and the second copy (iCloud or
a drive) mirrors the same layout and is pruned the same way. A restore is the
record items plus the newest nightly; `scripts/backup.sh` says how.

**Replaced.** Every night re-tarred the whole of `archive/` (159 MB after
three weeks, growing ~5 MB a day), and `ls | xargs rm` split every path at the
space in "My Apps", so nothing was ever pruned — locally or in iCloud, which
had no pruning at all. On a disk with 6 GB free, the job that exists to save
the record was on course to be the thing that filled the disk.

**If you undo it.** The nightly backup fills the Mac within months, and then
renders start failing for want of space.

`scripts/backup.sh` · `scripts/health.py` · `tests/test_backup.py`

---

## D113 · Health says when the Mac itself is the problem

**Decided (2026-10-06).** `scripts/health.py` checks free disk against
`Limits.disk_warn_gb` and `Limits.disk_min_gb`, and checks the three things a
render needs from the machine that the repository cannot carry: ffmpeg and
ffprobe on the PATH, Pillow built with raqm (Kannada shaping), and edge-tts
(the fallback voice). Its test run is every suite but the four that render
video — the set the pre-commit hook runs — discovered, not listed.

**Replaced.** A health page that could be all green on a Mac with 6 GB left,
or after an update that dropped raqm and would render every conjunct broken —
the failures most likely in a year nobody touches the code.

`scripts/health.py :: check_disk, check_tools, check_tests` ·
`brand/tokens.py :: Limits.disk_warn_gb, disk_min_gb` · `tests/test_health.py`

---

## D114 · fontTools is a dependency, because the glyph guard depends on it

**Decided (2026-10-07).** `fonttools` is in `requirements.txt` and in CI's
install. `health.py` fails the `tools` line when it is missing. CI's actions
move to `checkout@v5` / `setup-python@v6` (Node 20 is retired on runners).

**Replaced.** An unlisted import. `brand/typo.py :: _coverage` reads each
face's cmap with fontTools and, deliberately, fails open when it cannot — so
on any machine without fontTools the guard against letters shipping as empty
boxes (TYPE-01, D53) was silently off. The Mac had it by accident; the CI
runner did not, and `tests.test_contract` had been failing there on every
push since at least 2026-09-18 with nobody reading it. A new Mac set up from
the instructions would have rendered tofu with no warning.

`requirements.txt` · `.github/workflows/contract.yml` · `scripts/health.py ::
check_tools` · `tests/test_health.py`

---

## Changing something here

If you are about to change a value in `brand/tokens.py`:

1. Find its entry above. If there isn't one, add it after you decide.
2. Run `python3 -m pytest tests/ -q`. Golden failures are expected when the
   design genuinely changes — look at the diff images before accepting them.
3. Re-render the reference set and look at it: `python3 examples/make_examples.py`.
4. Update [`../STANDARDS.md`](../STANDARDS.md) if the rule changed, not just the value.
