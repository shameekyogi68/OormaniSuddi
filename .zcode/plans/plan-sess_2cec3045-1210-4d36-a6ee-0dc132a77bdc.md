## Luxury upgrade of the shared design engine (all nine templates inherit it)

Direction confirmed: **refined polish within the house rules** — one gold accent, hairlines not borders, square corners, restraint. Every change is in `brand/` so all templates (report_card, text_card, quote_card, stat_card, story_card, youtube_thumb, carousel, broadsheet, reel) pick it up without layout rewrites.

### 1. Gilded rules — `brand/surface.py` + `brand/components.py`
The single biggest "premium print" win available inside the rules. Hairlines stay hairlines, but the brand-carrying ones become *engraved*:
- New `gilded_rule(sf, x0, y, x1, weight)`: a horizontal gradient rule from `gold_600` → `gold_400` → `gold_600`, with alpha tapering to nothing at both ends (no hard start/stop). Built on a dithered gradient so no banding.
- New `faded_rule(...)` (paper hairline, ends tapering) for the footer rule.
- `masthead()` uses `gilded_rule` for its rule-below (replacing the flat gold alpha 0.28/0.34 line); `footer()` uses `faded_rule`. The takeaway's gold vrule gets the same vertical taper.

### 2. Richer house photo grade — `brand/tokens.py` (`Grade`) + `house_grade()`
Still gentle, still documentary, but more "graded film, less phone camera":
- Add a filmic **highlight rolloff** step (soft shoulder above ~0.82 luminance) so skies and highlights compress instead of clipping flat — the signature look of expensive colour grading. New `Grade.rolloff = 0.18`.
- Split-tone warmth slightly extended: `high_amt` 0.12 → 0.14, `shadow_amt` 0.20 → 0.22 (measured, small).
- Vignette made **anisotropic** (elliptical, matching frame aspect) instead of circular — vignettes currently darken corners slightly unevenly on 9:16 frames.

### 3. Finer film grain — `grain()`
Two-frequency grain: the current fine σ5 layer plus a very soft coarse layer (large-radius blur of the same noise, ~15% amplitude), giving the lumpy, layered look of real film emulsion instead of uniform static. Still deterministic (same seeded RNG) so goldens stay reproducible.

### 4. Editorial plate upgrade — `editorial_plate()`
The no-photo plate becomes a proper piece of engraved artwork:
- Dither the sky/sea gradients (they currently band slightly — same `_dither` used elsewhere).
- Add a **gold sun reflection** on the sea: a short broken vertical glint under the sun disc, alpha fading with distance.
- Open up the ruled-sea spacing ramp slightly (1.28 → 1.33) and ease line alpha so the sea reads as receding distance.
- Slightly larger, softer sun glow (radius 0.9r → 1.2r, alpha 0.30 → 0.26 — softer but more present).

### 5. Page depth — `page_base()` + `horizon()`
- `page_base()`: add a faint bottom-edge grounding (very subtle ink vignette at the foot) so tall pages feel lit from above and anchored below — the light logic of a photographed page.
- `horizon()`: add a whisper of `gold_300` into the inner glow so the band reads warmer at its centre; keep total alpha below current levels so it stays a suggestion.

### 6. Typography micro-polish — `tokens.T`
Only safe, collision-checked moves:
- `display` leading 1.20 → 1.22 (matras above Kannada display type need the extra air; keeps the measured collision guarantee).
- `meta` tracking 0.010 → 0.014 and `caption` 0.006 → 0.010 (Latin/digits only; Kannada tracking untouched per D2).
- No size changes, no new steps — the scale is documented as derived and stays.

### 7. Docs, tests, verification (per DECISIONS.md protocol)
- Add new D-entries to `docs/DECISIONS.md` (D29 gilded rules & rolloff, D30 layered grain, D31 plate engraving) with the "what breaks without it" rationale; note the Grade/T value changes in the existing entries if values are cited there.
- Run `python3 -m unittest tests.test_contract` (must pass untouched — no contract changes).
- Re-render the fixture, **visually review `out/_blessed/`**, then `python3 -m tests.test_golden --bless` to re-pin the 12 golden hashes, then run the full suite `python3 -m unittest discover tests`.
- Render `editions/2026-08-25.json` and `python3 examples/make_examples.py` to confirm the upgrade on real content; check the qa.py output audit stays clean.

**Not changing:** the palette ramp, one-accent rule, category rail system, grid/margins, safe insets, motion timing, the genuineness contract, any template layout code, and any rule in STANDARDS.md (this plan adds craft, not devices).