---
name: youtube-longform-edit
description: Turn raw video clips into a premium long-format (16:9, 2+ minute) YouTube video for ಊರ್ಮನಿ ಸುದ್ದಿ — story cut, AI resolution enhancement, colour grade, real sound + royalty-free instrumental music, brand cards and logo, QC, and the YouTube upload package — run by a 12-expert panel with evidence-based sign-off. Use whenever the user brings video clips/footage and asks to edit, merge, make or upgrade a YouTube video, long video, or event/temple/festival coverage. Not for Instagram Reels, YouTube Shorts or AI card slideshows (those go through render.py).
---

# Long-format YouTube edit from raw clips

This is the house method for turning phone footage into a finished long-format YouTube video.
It exists because the first job done without it (Ganapathi pratishtapana, Seneshwara temple,
Byndoor, 14 Sep 2026) reached only about **50% of the client's expectation** and took most of a day.
Everything that went wrong there is now either a rule below or a tool that makes it impossible.
Read [`LESSONS.md`](LESSONS.md) once: it is the evidence behind every rule here.

**Scope.** Horizontal long-format YouTube videos made from real footage. Vertical Reels/Shorts from
clips follow the sister skill [`reels-shorts-edit`](../reels-shorts-edit/SKILL.md), which reuses these
tools. AI-card videos go through `render.py`. AGENTS.md rule 7 applies: YouTube uploads must be real footage,
which is exactly what this produces.

**Everything runs inside this project folder** (AGENTS.md rule 6). Work files go in
`<footage>/_work/`, finished files in `<footage>/output/`. Never use `/tmp` or other folders.

---

## 1 · Non-negotiables (the client's own rules — never re-litigate)

1. **Real on-location sound stays.** Firecrackers, bells, chanting, crowd and speech are cleaned,
   levelled and kept audible under or beside the music. Never mute the footage.
2. **Music is royalty-free AND instrumental only.** No vocals, no bhajan lyrics, no spoken
   dialogue. Confirm with evidence before using a track (§7). Record its licence in the project JSON.
3. **Brand masthead at the TOP for the entire runtime, exactly like the reels** — including the
   intro and outro cards. Top-left: the round logo, the ಊರ್ಮನಿ ಸುದ್ದಿ wordmark and the gold tagline.
   Top-right: the event date and weekday (and time if given), all on a soft dark veil fading down
   from the top edge. It is drawn by the same `brand/components.py :: masthead()` the reel engine
   uses, so the two formats never drift. No bottom-corner watermark (client instruction, 15 Sep 2026).
   Keep important action out of the top ~12% of the frame when choosing shots and framing.
4. **Clip order follows the file numbers** (IMG_2565 before IMG_2566) unless the client says otherwise.
5. **Names exactly as the client wrote them.** Copy temple, place and event names from the client's
   Kannada. Never transliterate from memory: "ಸೇನೇಶ್ವರ" was once filed as "Someshwara".
   Any text you cannot confirm (section titles, people's names) stays off screen.
6. **Premium means it looks and sounds professional to a viewer.** Clean, sharp, consistent colour,
   clear sound, and a story that holds attention. Technical numbers alone are not enough.
7. **Nothing is "done" until it has been checked:** ffprobe numbers, loudness, the QC frame sheet
   looked at, and `python3 -c "from brand.review import approve_footage; approve_footage('<output>')"`
   writing `APPROVAL_FOOTAGE.md`. No file, no upload. Use `--tile 256` on Real-ESRGAN
   (`tools/sr_upscale.py`) so the 8 GB M1 does not swap-death.
8. **The client sees live status during long work:** what is running, % done and an honest ETA.
   Measure the ETA from actual speed. Update it when something changes and correct wrong numbers openly.

---

## 2 · The fast path (what happens, in order)

Target on this Mac (M1, 8 GB) for ~15 min of raw footage and a 3–5 min edit: **first reviewable
cut in about 45 minutes, AI master about 2 hours after approval**.

| Step | What | Time | Output |
|---|---|---|---|
| A | **Intake**: `tools/intake.py`, then look at EVERY contact sheet | 5–10 min | `_work/intake/intake.md` + sheets |
| B | **One brief**: a single batched question to the client (below) | 1 message | answers |
| C | **Edit decision list**: write `<footage>/project.json` (§4 story rules) | 10–15 min | project.json |
| D | **Cards check**: `tools/make_cards.py project.json --preview`, look at the PNGs | 2 min | cards look right |
| E | **Preview cut**: `build.py project.json --preview --detach` + `monitor.py` | 15–30 min | `*_1080p_preview.mp4` → client |
| F | **Master**: `build.py project.json --detach` + `monitor.py --restart 2` | ~1 s/frame + 20 min | `*_1440p.mp4` |
| G | **QC + expert sign-off** (§3), then deliver file + YouTube package (§9) | 10 min | final |

**Step B — ask once, batched, then stop asking.** One AskUserQuestion call, at most four questions,
each with a recommended option. Decide everything else yourself.
1. **Original files?** If intake flags clips as low-res (WhatsApp is 848×464 / 464×848), ask for the
   originals via AirDrop, Google Drive "original quality" or cable. This is the biggest single quality
   lever; nothing downstream can fully recover it.
2. **Length and style:** tight story cut (recommended, 3–5 min) or full coverage.
3. **Names for on-screen text:** event, place, and the ceremony stages to use as section titles/chapters.
4. **Music:** propose 2–3 specific instrumental tracks with licence (§7) and get download permission.

Downloads always need the client's explicit yes, with file name, source, size and licence stated.
Batch all of it into this one question.

**Don't wait idle.** While the client answers, prepare the preview cut from intake so it is ready to run.

---

## 3 · The expert panel (all 12 sign off before delivery)

Each expert owns a checklist. The Chief Editor scores every dimension out of 10 **with evidence**:
numbers, frame timestamps, the sheet looked at. Below 9 in any dimension → fix and re-check. If a
dimension is capped by the source (e.g. WhatsApp resolution), say so plainly instead of looping.

| # | Expert | Owns | Pass bar |
|---|---|---|---|
| 1 | **Story Producer** | Intake log, what the event is, story arc, hook | Can state the story in one line; cold open picked; every clip watched via sheets |
| 2 | **Editor** | Cut list, pacing, cut grammar, retention | No shot drags; no repeated angle back-to-back; hero moments held; runtime fits the story |
| 3 | **Colourist** | Consistent look shot-to-shot, skin, whites, gold | Same-location shots match; skin natural; dhotis not clipped; no neon greens; no banding |
| 4 | **Restoration Engineer** | Upscale mode, denoise strength, sharpness | 100% crops vs. plain scaling show real gain; faces not waxy; no halos or ringing |
| 5 | **Sound Engineer** | Real-sound clean-up, levels, mix, master | −14 LUFS ±1, true peak ≤ −1 dBTP; no clicks at cuts; speech and chants intelligible |
| 6 | **Music Supervisor** | Track choice, instrumental proof, licence record, edit to phrases | Licence recorded; no vocals; starts on a phrase; ends resolved, not chopped |
| 7 | **Motion & Brand Designer** | Intro/outro cards, lower thirds, logo, typography | Cards match STANDARDS.md (gold is the only accent); Kannada shaped correctly; logo full runtime |
| 8 | **Kannada Language & Culture Expert** | Every on-screen word, names, ritual respect | Spelling verified against the client's text; deity and ritual shown with dignity |
| 9 | **YouTube Growth Expert** | Title, thumbnail, description, chapters, first-30-s retention | Hook in the first 5 s; chapters valid; description ends with the Kannada engagement question |
| 10 | **Legal & Monetisation Expert** | Copyright, Content ID risk, privacy, ad-safety | Music licence on file; no other copyrighted audio (loudspeaker film songs!); no child close-up in thumbnail |
| 11 | **Technical QC Engineer** | `qc` stage report, sheet, codec/colour tags | qc_report.md all PASS; sheet inspected; file plays start to end |
| 12 | **Chief Editor** | Final gate, honesty of the handover | Scores with evidence; limits stated honestly; nothing claimed that was not checked |

**Loudspeaker music check (Legal).** Temple and procession footage often has film songs or devotional
recordings playing through loudspeakers. That audio can trigger Content ID even though you added only
licensed music. Listen for it in intake (spikes in sound, rhythmic music under crowd noise). Keep
those stretches short, lower the real sound there, or cut around them.

---

## 4 · Creative standards (what the missing 50% most likely was)

The shipped Ganapathi cut was correct but plain: chronological highlights, uniform dissolves,
no hook, no captions, no chapters. Do all of the following by default.

**Structure**
- **Cold open, 3–6 s**, before the brand intro: the single most striking moment with its natural sound,
  such as a firecracker burst, the idol reveal, an aarti flame or a drum hit. It hooks retention;
  put it in `cold_open`.
- **Brand intro, 4–5 s**: place + event title from the client's exact wording.
- **Three acts** mapped to real stages of the event: arrival/procession → main ritual/peak → people,
  blessings, emotion. Each act is a `section` with a confirmed Kannada label, which becomes chapters.
- **Hero finale**: hold the best final shot 8–12 s and let the music resolve over it.
- **Outro, 6–7 s**: thanks + subscribe + handle (defaults come from `brand/tokens.py`).

**Pacing**
- Action and procession: shots of 3–6 s. Ritual and deity: 7–12 s. Rarely more than 15 s on one take.
- Vary shot scale (wide → medium → close). Never cut between two near-identical angles.
- A 3–5 min cut from ~15 min raw is usually right. Longer only if every minute earns its place.

**Cut grammar** (automated in `build.py`; override per shot with `transition_in`)
- New shot, same section → near-hard cut (0.1 s).
- Jump within the same clip → 0.5 s dissolve (hides the jump).
- New section → 0.8 s dissolve. Into and out of cards → dip to black.
- No gimmick transitions (spins, glitches, zoom-blurs, flashy wipes) on devotional content.
- Cut on action or on a sound event when possible, not in the middle of a gesture or a mantra.

**Sound design**
- Let natural peaks breathe: under a bell, conch, chant or firecracker hit, dip the music about 6 dB
  for 1–2 s. Do it with `music.levels.sections`, or a dedicated short section around the moment.
- Nothing silent: every cut has room tone or music. The qc stage flags long silences.
- The music should feel edited to the picture: pick `offset` so it starts on a phrase, and make sure
  the runtime ends near a musical resolution; the last 3 s fade out.

**Graphics**
- Lower thirds only for confirmed names: place, stage of the ritual, speaker. Never on the deity's face.
  About 4–5 s, bottom-left band, gold bar.
- Chapters only from confirmed section labels. YouTube needs 3+ chapters of 10 s or more.
- Kannada is rendered only through Pillow with raqm (`make_cards.py`), never ffmpeg drawtext.

**Respect** (Culture expert has a veto)
- The deity is shown steady, well-framed and held, never flash-cut, never zoom-punched for effect.
- No comic sound effects, no speed-ups of rituals, no cutting away at the peak of an aarti.
- Public religious events: crowd faces are fine. Avoid close-ups of children as a thumbnail or hero frame.

---

## 5 · Picture: colour and resolution

- **Deliver 1440p (2560×1440) even from 1080p or lower sources.** YouTube serves 1440p+ uploads with
  its higher-quality codecs, so viewers at 1080p also see a cleaner picture.
- **Upscale modes** (`upscale` in project.json):
  - `ai` — Real-ESRGAN general-x4v3 on the Mac GPU (`tools/sr_upscale.py`). Visibly rebuilds leaves,
    ornaments, crowns, fabric and faces on compressed footage. ~1.0–1.3 s per 1440p frame on this Mac.
  - `grade` — hqdn3d denoise + Lanczos scale + CAS sharpen + deband. ~10× faster; used for `--preview`.
- `ai_denoise` 0.5 is the tested default. Go lower (0.3) if faces look waxy or painted, higher (0.7)
  for very blocky footage. Always compare a 100% crop of a face shot before committing to a full render.
- **Framing:** landscape clips are centre-cropped to exact 16:9 (848×464 → 824×464). Portrait clips
  go on a blurred, darkened copy of themselves (pillarbox). Both are automatic.
- **Grade** (tested house look): contrast 1.06, saturation 1.12, gamma 0.98, slight warm balance
  (shadows/mids/highlights red +, blue −), soft vignette PI/8. Adjust per job only after checking:
  skin natural, whites not clipped, golds rich but not orange, greens not neon.
- **Stabilisation:** the Homebrew ffmpeg has no vidstab. `deshake` warps faces, so don't use it.
  Pick steadier takes instead, or install vidstab first if a job truly needs it.
- **Slow motion:** only from 50/60 fps sources. Never interpolate 30 fps (minterpolate artefacts).
- **Honesty:** 848×464 WhatsApp footage cannot become true 1440p. Say what it can and cannot become.
  Show the before/after crop, and ask for originals next time.

---

## 6 · Sound: the mix spec (automated in `build.py`)

| Stage | Setting |
|---|---|
| Real sound per shot | adeclip → highpass 90 Hz → lowpass 15 kHz → afftdn −28 → gentle compressor (2.5:1) |
| Level match | each shot to −18 LUFS integrated, gain capped at +10 dB, limiter 0.89 |
| Placement | each shot faded over its own transitions and placed at its exact timeline start (continuous timestamps) |
| Real bus | compressor 3:1 at −24 dB, gain 0.85, limiter 0.95 |
| Music bed | starts at `offset`; level per item from `levels` (cards louder, ritual lower), 2 s ramps; 1 s fade-in, 3 s fade-out |
| Ducking | `duck: false` shipped: music and real sound sit side by side. `duck: true` makes music dip under loud real sound (sidechain) — use when speech must be understood |
| Master | limiter only as deep as needed, then two-pass **linear** loudnorm to −14 LUFS, −1 dBTP (no pumping) |
| Delivery | AAC 320 kb/s, 48 kHz stereo |

**Balance is taste.** The client first wanted real sound kept, then accepted music leading
(card 0.80 / story 0.62 / ritual 0.55). Put the balance into the preview so the client hears it
before the 2-hour master, and change only `music.levels` afterwards (audio re-renders in about 2 min).

---

## 7 · Music: finding and proving an instrumental track

1. Look first in `assets/bgm_options/ganapathi/journey_to_the_golden_temple_tokyorifft.mp3` (proven
   instrumental, licence in the example project) and the rest of `assets/bgm_options/`. Those other
   files are named "breaking news" stingers and have no licence note, so treat them as unsuitable
   for devotional or event content and unverified until a source is recorded.
2. Otherwise use Pixabay Music (Pixabay Content License: free commercial use, no attribution required).
   Prefer stock-library artists whose catalogue is instrumental background music.
   **Avoid anything titled bhajan, song, aarti, "AI bhajan", or with a singer's name**, which almost
   always has vocals or dialogue. The 9-minute "Ganpati Bappa Morya" festive mix had dialogue.
3. Get the direct file with the Browser tool: open the track page, read the `<audio>` element's `src`
   (a `cdn.pixabay.com/audio/...mp3` URL), then `curl -sI` it to find its size before asking.
4. **Prove it is instrumental** before the master render. There is no reliable automatic vocal detector
   in this toolchain, so the proof is listening: the full track plays under the preview cut, and the
   client confirms "no vocals, no dialogue" in their preview feedback. Never skip the preview for a new track.
5. Record in project.json `music.license`: title, artist, source URL, licence, download date, and
   whether it is AI-generated (Pixabay labels this — tell the client).
6. Choose `offset` so the music is already carrying when the story starts. Many tracks open with
   silence or a slow build; the shipped job used 12 s.

---

## 8 · Running long renders on this Mac without losing hours

Measured on the client's **M1, 8 GB RAM**, which is usually also running Chrome, WhatsApp and other
Claude sessions:
- AI upscale: ~1.0–1.3 s/frame when the Mac is free; up to 30 s/frame when memory runs out, and the
  process can be killed outright (SIGKILL, exit −9).
- 1440p assembly with the `medium` preset: ~0.1–0.5× real time. The `slow` preset stalled at 0.2×,
  so don't use it.
- **One heavy job at a time.** A preview and a master running together starved the AI job.
- **Always `--detach`** (survives the chat session ending; earlier jobs died with the session).
  Then run `tools/monitor.py <project> [--preview] --restart 2` through the Monitor tool.
  It reports only real changes, measured ETAs and relaunches after a kill. Cached work is never redone.
- Tell the client up front: closing Chrome makes it roughly 2× faster.
- **Keep the client updated with a status table** at start, on every stage change, and when an ETA
  moves by more than 10 minutes: job / status / % / time left / expected finish clock time.
  Correct a wrong ETA openly. Send a PushNotification when the master finishes.
- Disk: a 3-min 1440p job uses ~2–4 GB in `_work`. After the client confirms upload, ask before
  deleting `_work`. Keep project.json and the output master.

---

## 9 · Delivery and the YouTube package

**Files** (in `<footage>/output/`):
- `OORMANI_SUDDI_<Place>_<Event>_1440p.mp4` — the master (H.264 high, CRF 15, BT.709 tags, faststart, AAC 320k).
- `..._1080p_preview.mp4` — review cut (delete after the master ships).
- `..._chapters.txt` — paste into the description.
- A 100% crop before/after image (sent to the client) and `_work/qc/qc_sheet.jpg` + `qc_report.md`.

**Handover message** (short, plain): where the file is, what was done in one line each
(picture / sound / branding), QC numbers, honest limits, and which old files can be deleted.
Files over 30 MB cannot be sent to the phone, so say so. Send a comparison image instead.

**YouTube package** (write it; don't make the client ask):
- **Title** — Kannada first, then an English keyword tail; ≤ 70 characters visible.
  Example shape: `ಬೈಂದೂರು ಸೇನೇಶ್ವರ ದೇವಸ್ಥಾನ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ | Byndoor Ganesha 2026`.
- **Thumbnail** — hero frame taken from the AI master at full resolution (deity or peak moment large,
  high contrast), ≤ 4 Kannada words, brand logo. Never a child's face as the focus.
- **Description** — 2-line hook; place, date, event; chapters; music credit line (title, artist, Pixabay);
  3–5 hashtags; last line exactly: `ನಿಮ್ಮ ಅಭಿಪ್ರಾಯ ಏನು? ಕಮೆಂಟ್ ಮಾಡಿ.` (AGENTS.md rule 7).
- **Settings** — category News & Politics or People & Blogs; Made for Kids: No; add chapters;
  pinned comment asking viewers which moment they liked.
- Upload the 1440p master, not the preview.

---

## 10 · Commands

```bash
K=.claude/skills/youtube-longform-edit/tools
python3 $K/intake.py "<footage folder>"                          # A: log clips + contact sheets
python3 $K/build.py <footage>/project.json --check                # C: validate the edit list
python3 $K/make_cards.py <footage>/project.json --preview         # D: render cards, then LOOK at them
python3 $K/build.py <footage>/project.json --preview --detach     # E: 1080p review cut
python3 $K/monitor.py <footage>/project.json --preview            #    live status (run via Monitor)
python3 $K/build.py <footage>/project.json --detach               # F: AI 1440p master
python3 $K/monitor.py <footage>/project.json --restart 2          #    live status + auto-relaunch
python3 $K/build.py <footage>/project.json audio mux qc           # re-mix only (~3 min), e.g. music levels
bash    $K/fetch_models.sh                                        # re-download AI weights if missing
```

**project.json** — start from [`examples/ganapathi_seneshwara_2026-09-14.json`](examples/ganapathi_seneshwara_2026-09-14.json)
(the shipped job). Its clips have since been removed from the footage folder, so `--check` on it now
fails by design. The keys:

| Key | Meaning |
|---|---|
| `title_slug` | output file stem, from the client's names |
| `footage_dir` / `work_dir` / `output_dir` | relative to project root (work/output default inside footage) |
| `segments[]` | `clip`, `in`, `out` (seconds), `section`, optional `transition_in: ["fade", 0.4]` |
| `cold_open[]` | same shape; plays before the intro card |
| `cards.intro` | `title`, `lines[]`, `bg: [clip, seconds]`, `dur`; `cards.outro` has brand defaults |
| `masthead` | top brand bar, as on reels: `date` ("2026-09-14" is shown as `14 ಸೆಪ್ಟೆಂಬರ್ 2026` + weekday), optional `time` ("19:15"), `scale` (1.05), `scrim` (0.62), `on_cards` (true) |
| `sections` | `{section_key: "confirmed Kannada label"}` → chapters |
| `lower_thirds[]` | `segment` index, `title`, `subtitle`, optional `delay`, `dur` |
| `music` | `file`, `license` (required), `offset`, `levels {card, default, cold_open, sections{}}`, `duck` |
| `upscale` / `ai_denoise` / `grade` / `resolution` / `encode` | picture settings (defaults are the tested values) |

---

## 11 · ffmpeg traps already paid for (don't rediscover them)

- **A filter label can be consumed only once.** Reuse needs `asplit`/`split`. The symptom is
  "Error binding filtergraph inputs/outputs: Invalid argument".
- **acrossfade chains leave timestamp gaps; sidechaincompress stops at the first gap.** Symptom: the mix
  cuts off at ~50 s. Fix: place each shot with `adelay` + `apad` and sum with `amix normalize=0`,
  plus `asetpts=N/SR/TB`.
- **xfade offsets are cumulative**: offset_j = (sum of previous durations) − (sum of previous transition
  durations) − this transition. A transition must be shorter than both neighbouring shots.
- **loudnorm in single pass pumps.** Measure, limit peaks just enough, then apply two-pass `linear=true`.
- **WhatsApp aspect is not 16:9** (848×464); crop to 824×464 before scaling.
- **Tag colour explicitly** (`setparams` + `-colorspace bt709 ...`) and convert RGB↔YUV with BT.709
  limited range, or players shift colours.
- **ffmpeg drawtext cannot shape Kannada conjuncts.** Use Pillow with raqm.
- **`-movflags +faststart`** means the file is unreadable ("moov atom not found") until ffmpeg
  finishes. That is not corruption.
- **A background shell exit code of 0 can hide a failed inner job** (`python ...; echo EXIT=$?`).
  Check `_work/stage.json` or the log, not the wrapper's exit code.
- **Don't count output files to judge progress**: `.part` files exist while still being written.
  build.py only renames a segment after its frame count is verified.
