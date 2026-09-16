---
name: reels-shorts-edit
description: Turn real video clips into a vertical 9:16 Instagram Reel / YouTube Short for ಊರ್ಮನಿ ಸುದ್ದಿ — hook-first cut, AI resolution enhancement, colour grade, real sound + ducked royalty-free instrumental, the reel masthead, organiser credit, captions, outro card, QC against Instagram safe zones, and the caption/Shorts copy — with an expert panel sign-off. Use whenever the user brings clips and asks for a reel, Instagram reel, short, YouTube Short, or vertical video from footage. Not for AI-card news reels from copy (render.py) or horizontal long-format videos (youtube-longform-edit).
---

# Instagram Reel / YouTube Short from real clips

The house method for a 15–60 s vertical video cut from phone footage. It is built from the reel made
on **14 Sep 2026 22:21** (`Ganapathi Video/output/OORMANI_SUDDI_Ganapathi_Reel.mp4`, 44.7 s, posted).
That reel's cut is recorded as a working project in
[`examples/ganapathi_reel_2026-09-14.json`](examples/ganapathi_reel_2026-09-14.json).

**Read the long-format skill's rules first**:
[`../youtube-longform-edit/SKILL.md`](../youtube-longform-edit/SKILL.md) §1 non-negotiables, §7 music,
§8 running renders, §11 ffmpeg traps, and its `LESSONS.md`. They apply here unchanged. This file adds
only what is different about short-form. The tools are shared: `tools/reel_build.py` uses the
long-format engine in `../youtube-longform-edit/tools/` (AI upscaler, audio clean-up, fonts, brand tokens).

**Platforms.** One file serves both Instagram Reels and YouTube Shorts. This does not conflict with
AGENTS.md rule 7: the rule restricts AI-card reels on YouTube, and these are real footage.

**Only render when the client asks for a video.** "Update the files" means files only.
`--check`, `--dry-run` and `--overlays` never write video.

---

## 1 · Short-form rules on top of the house rules

1. **Hook in the first 1.5 s, with sound.** The first shot is the most striking moment, cut hard and never
   faded in from black. Last night's reel opened on a 1.3 s firecracker burst; that is the model.
2. **15–60 s.** Aim for 30–45 s. The tool warns above 60 s and refuses above 90 s.
3. **Reel masthead at the top for the content, exactly as the reel engine draws it**
   (`brand/components.py :: masthead()`): logo + ಊರ್ಮನಿ ಸುದ್ದಿ + tagline at top-left, date + weekday/time at
   top-right, a gilded hairline under it, and a soft top veil. It is off during the outro card, which is
   itself the brand moment. That matches the reel that was posted.
4. **Instagram safe zones** (`brand/tokens.py` `reel` format, 1080×1920): top 230 px, bottom 480 px,
   right 220 px, left 72 px. Captions and credits sit **inside** them. The shipped reel put the organiser
   credit at y ≈ 1735–1840, where Instagram's caption and buttons cover it; the tool now places credit
   lines above the bottom zone.
5. **Captions and credits only with confirmed wording.** The shipped reel dropped three pop-in captions
   because the place/temple wording was guessed. Captions help sound-off viewers, so ask for the words
   in the brief rather than skipping them.
6. **Music ducks under the real sound** (sidechain), so firecrackers, drums and chants punch through.
   Instrumental only, licence recorded.
7. **Loudness −13 LUFS, true peak ≤ −1 dBTP measured on the final AAC file.** The shipped reel measured
   −0.2 dBFS peak after encoding. The tool masters to −1.5 dBTP before AAC and fails QC if the encoded
   file peaks above −1.0.

---

## 2 · The fast path

| Step | What | Command | Time |
|---|---|---|---|
| A | Intake: every contact sheet looked at | `python3 ../youtube-longform-edit/tools/intake.py "<footage>"` | 5 min |
| B | One batched brief (below) | AskUserQuestion | 1 message |
| C | Write `<footage>/reel.json` (§3) | — | 10 min |
| D | Validate everything, write nothing | `reel_build.py reel.json --check` then `--dry-run` | 1 min |
| E | Look at the overlay, captions and outro as PNGs | `reel_build.py reel.json --overlays` | 1 min |
| F | Preview cut (only if the client wants to see one) | `reel_build.py reel.json --preview --detach` + `--monitor` | ~5 min |
| G | Master (AI) | `reel_build.py reel.json --detach`, then `reel_build.py reel.json --monitor --restart 2` | ~1 s/frame + 5 min |
| H | QC sheet with safe-zone guides + copy file, then deliver | written by the build | — |

**Brief (one question batch, recommended option first):**
1. Originals, if intake flags WhatsApp-size clips.
2. Length: 30–45 s (recommended) or up to 60 s.
3. Exact on-screen words: organiser credit lines, caption lines, event date and time for the masthead.
4. Music: an approved instrumental track, or the proven house track.

---

## 3 · Cut and creative standards (15–60 s)

- **Shape:** hook (≤1.5 s) → build (2–4 s shots, rising energy) → hero moments (5–6 s each, slow push-in) →
  a warm human closer (faces, reactions) → outro card (≈2.2 s).
- **Shot length:** 1.2–4 s in the build; hero 5–6 s. Nothing over 7 s. Around 10–14 shots for 45 s.
- **Cuts:** snap cuts (0.12 s crossfade reads as a hard cut) by default. No dissolves between crowds,
  no gimmick transitions on devotional content. Cut on action or on a sound hit.
- **Hero push-in** (`"hero": true`): a 1.0 → 1.055 slow zoom over the shot, rendered from a 2× frame so it
  stays sharp. Use it on the deity, the key ritual and the peak moment — two to four shots, not every shot.
- **Breather:** one 2–3 s calm shot (decorated stage, wide) between the street energy and the ritual.
- **Framing:** portrait clips are centre-cropped to 9:16. Use `frame_x`/`frame_y` (0–1) to keep the subject in
  the frame. Landscape clips either crop (subject must fit a narrow 9:16 slice) or use `"fill": "blur"`
  (the whole landscape frame on a blurred copy of itself). The tool warns when a crop keeps less than 40%.
- **Captions** (`captions[]`): up to 3–4 short lines, 1.5–2.5 s each, centred on the frame and at most
  856 px wide (clear of Instagram's right-hand buttons), white Kannada with a soft shadow.
  Never over the deity's face.
- **Organiser credit** (`credit_lines`): gold first line and white second line above the bottom safe zone,
  on for the whole content part.
- **Outro** (≈2.2 s): blurred frame, glowing logo, ಊರ್ಮನಿ ಸುದ್ದಿ in gold, "Follow @oormanisuddi" in the brand
  font (the shipped outro used Helvetica for that line — fixed).
- **Loop-friendly ending (optional):** end the last content shot on motion that matches the hook so replays
  feel continuous. Replays count toward reach.

---

## 4 · Picture, sound, delivery — what differs from long-format

| | Reel / Short |
|---|---|
| Canvas | 1080×1920, 30 fps, BT.709 tags |
| Upscale | `ai` default (Real-ESRGAN x4v3 on the 9:16 crop, resized to 1080×1920); `grade` for `--preview` |
| Grade | contrast 1.10, saturation 1.18, gamma 0.97, warm balance — the shipped reel's look (a touch punchier than long-format for small screens) |
| Real sound | same per-shot clean-up and −18 LUFS level match as long-format; real bus compressed 3:1 |
| Music | constant `level` (0.8), `offset` into the track, 0.4 s fade-in, 1 s fade-out, ducked by real sound (threshold 0.15, ratio 6, attack 5 ms, release 180 ms — the shipped settings) |
| Master | −13 LUFS, −1.5 dBTP before AAC; QC requires ≤ −1.0 dBTP after AAC |
| Encode | H.264 high, CRF 17, max 25 Mb/s, GOP 2 s, AAC 256 kb/s, faststart |
| Output | `<footage>/output/<title_slug>_1080x1920.mp4` + `<title_slug>_copy.txt` |
| Cover | pick from `_work/reel/qc/qc_sheet.jpg`; keep the subject inside the centre 1080×1350 (the profile-grid crop) |

**Copy file** (`copy` block → `<title_slug>_copy.txt`), in the same shape as the house captions from
`brand/copy.py`: Instagram caption (headline, engagement question, 📍 place 🕐 date · time, status,
credit, source, the correction-contact line from `brand/tokens.py`, hashtags), the first comment,
a YouTube Shorts title under 60 characters, and a Shorts description that ends with
`ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.` (AGENTS.md rule 7) plus `#Shorts`.

---

## 5 · Expert panel (short-form)

Same gate as long-format §3 (Chief Editor scores each dimension with evidence, <9 → fix). The roles that
change:

| Expert | Short-form pass bar |
|---|---|
| **Hook & Retention Editor** (replaces Story Producer + Editor) | Hook ≤1.5 s with sound; no shot over 7 s; energy rises to the hero shots; closer is human |
| **Motion & Brand Designer** | Masthead identical to the reel engine; captions and credit inside the safe zones on the QC sheet guides; outro in brand fonts |
| **Instagram & Shorts Growth Expert** | 30–45 s; cover frame chosen; caption opens with the hook line; first comment ready; Shorts title <60 characters |
| **Technical QC Engineer** | `qc_report.md` all PASS, including true peak on the AAC file and duration bounds |

Colourist, Restoration, Sound, Music Supervisor, Kannada & Culture, Legal & Monetisation and Chief Editor
are exactly as in long-format.

---

## 6 · `reel.json` keys

| Key | Meaning |
|---|---|
| `title_slug`, `footage_dir`, `work_dir`, `output_dir` | as long-format (work defaults to `<footage>/_work/reel`) |
| `segments[]` | `clip`, `in`, `out`, optional `hero`, `frame_x`, `frame_y`, `fill: "blur"`, `transition_in: ["fade", 0.3]`, `note` |
| `masthead` | `date` (YYYY-MM-DD), `time` (HH:MM), `scale` 0.92, `rule` true, `on_outro` false |
| `credit_lines` | up to 2 confirmed lines (gold, white) above the bottom safe zone |
| `captions[]` | `segment` index, `text`, optional `delay` (0.15), `dur` (2.2) |
| `outro` | `dur` 2.2, `bg: [clip, seconds]`, `title` (brand name), `line` ("Follow @oormanisuddi") |
| `music` | `file`, `license` (required), `offset`, `level` 0.8, `duck` true |
| `audio` | `real_lufs` −18, `real_max_gain_db` 10, `real_gain` 1.0, `master_lufs` −13, `true_peak` −1.5 |
| `upscale`, `ai_denoise`, `grade`, `cut` (0.12), `encode {crf, maxrate}` | picture and cut settings |
| `copy` | `headline`, `question`, `place`, `status`, `credit`, `source`, `hashtags[]`, `first_comment`, `shorts_title` |

---

## 7 · What last night's reel taught (14 Sep 2026)

**Keep:**
- The firecracker hook.
- Snap cuts and push-ins on the three hero shots.
- A calm breather shot before the ritual.
- A human closer.
- The house masthead with date/time.
- Organiser credit lines instead of guessed captions.
- Ducked music.
- Two-pass loudness.
- A short logo outro.

**Fixed in the tool:**
- True peak −0.2 dBFS after AAC. Now mastered to −1.5, checked on the final file.
- Credit lines sat under Instagram's caption zone. Now placed above it, with guide lines on the QC sheet.
- Outro subscribe line was in Helvetica. Now uses the brand body font.
- No AI upscale on 464-px-wide WhatsApp footage. Now `ai` by default.
- The masthead was a hand-made PNG placed higher than the reel engine places it. Now drawn by
  `masthead()` at the engine's position.
- Real sound was chained with `acrossfade`, which leaves timestamp gaps (it needed a padding workaround).
  Now placed per shot, as in long-format.
- The build script lived in a temporary folder outside the project and would have been lost. Now it is
  `tools/reel_build.py`.
