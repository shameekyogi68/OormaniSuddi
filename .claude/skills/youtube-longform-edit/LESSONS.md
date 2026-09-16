# Lessons from the first long-format job

**Job:** ಮಹತೋಭಾರ ಶ್ರೀ ಸೇನೇಶ್ವರ ದೇವಸ್ಥಾನ, ಬೈಂದೂರು — ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನಾ ಮಹೋತ್ಸವ, edited 14 Sep 2026.
**Input:** 16 WhatsApp-forwarded clips, 848×464 at 30 fps, ~7 min raw, handheld, loud audio.
**Shipped:** a 3:08, 1440p AI-upscaled cut with brand cards, logo, real sound and instrumental music.
**Client's verdict (15 Sep):** "about 50% of my expectations, but it's okay, I have posted it."

The client asked for a record of what went well and what didn't, so that the next edit reaches 100%,
fast, done by experts. This is that record. The rules in SKILL.md come from here.

---

## What the client asked for (in their words, condensed)

"Think like a perfect video editor for YouTube; colour grade and resolution to 1080p with no blur;
our Oormani Suddi brand; trim, edit and merge in the numbered order; transitions; logo; a premium,
long-format video; royalty-free music; work like a totally experienced expert."

Later corrections, each one a rule now:
1. "Along with the song use the real sound of the video, don't erase it, engineer it perfectly."
2. "Have our news logo throughout the video, not only at the start."
3. "The song has dialogues, not needed."
4. "Must be royalty free, no copyright."
5. "Upgrade everything in terms of quality."
6. "Tell me what process is going on and the time left, update me all the time."
7. (15 Sep) "Make sure the logo will be at the top like how we do for reels." The shipped cut had a
   circular logo bottom-right; long-format now carries the reel masthead across the top.

---

## What went right (keep doing it)

- **Contact sheets of every clip before cutting.** The cut followed the real event (procession →
  arrival → installation → blessings → adornment) instead of guessing from file names.
- **Numbered clip order respected**, and a tight ~3-minute story cut instead of a 7-minute dump.
- **AI upscaling (Real-ESRGAN general-x4v3 on the Mac GPU)** gave the single biggest visible gain on
  compressed footage: leaves, flowers, crown, hands and signs were rebuilt. The before/after 100% crop
  proved it to the client better than any description.
- **Brand cards that look designed**: blurred and darkened frame from the footage, glowing logo,
  gold Kannada title, gold hairline, correct conjunct shaping. The client did not complain about them.
- **Audio engineering once the real sound came back:** per-shot declip/denoise/level-match to −18 LUFS,
  master at −14 LUFS / −1 dBTP, linear loudnorm with no pumping.
- **Verification before delivery:** ffprobe specs, loudness scan, frames checked for logo, text and
  transitions. Problems were found by checking, not by the client.
- **Live progress table with ETA** once the client asked for it. Keep it, and give it without being asked.

## What went wrong (and the fix now in place)

| # | What happened | Cost | Fix now |
|---|---|---|---|
| 1 | **Never asked for original files.** Worked from 848×464 WhatsApp copies. | Hard quality ceiling; faces stayed soft and slightly "painted" even after AI | Intake flags low-res clips; Step B asks for originals first |
| 2 | **First cut muted the real sound** (music only) | Full re-render round | Non-negotiable #1; build always mixes real sound |
| 3 | **First music track had spoken dialogue** ("Ganpati Bappa Morya" festive mix), picked by title without listening | Re-search, re-download, re-render | §7: instrumental-only rules, proof step, licence recorded |
| 4 | **Logo hidden on intro/outro cards** | Re-render | Non-negotiable #3; logo overlay spans the whole runtime |
| 5 | **Temple name misspelled in the file name** ("Someshwara" vs ಸೇನೇಶ್ವರ) | Wrong-looking deliverable | Non-negotiable #5: names only from the client's own text |
| 6 | **Too many separate questions** (music style, length, track, download confirmation) spread over several turns | Slow start | Step B: one batched question, then decide |
| 7 | **Creativity was thin**: plain chronological order, all transitions identical 0.5 s fades in v1, no cold-open hook, no chapters, no captions (section titles were guessed and removed), no natural-sound moments, no music phrasing | Most likely the missing "50%" | §4 creative standards are defaults now; cold open, sections, chapters, lower thirds are first-class in project.json |
| 8 | **No preview before the long render.** Every correction cost a full render | Hours | Step E: fast 1080p preview goes to the client before the AI master |
| 9 | **Render speed collapsed**: `slow` preset at 0.2×, a preview and master running together, Chrome using the GPU, 8 GB RAM. The AI job was SIGKILLed once, and two background jobs died when the chat session ended. | ~8 hours of wall time for a 3-minute video | §8: one job at a time, `--detach`, `medium` preset, monitor with `--restart`, cached stages, warn to close Chrome |
| 10 | **Progress reporting was noisy and sometimes wrong**: per-minute repeats, an ETA from 60 s of data (10 min shown instead of 70), counting `.part` files as done | Client confusion | monitor.py: change-only updates, speed measured from finished segments and ffmpeg `-progress` |
| 11 | **ffmpeg bugs found live**: label reused without asplit (exit 234); acrossfade gaps silently cut the sidechain mix at 52 s; single-pass loudnorm pumping; `.part` "moov atom not found" misread | Several failed renders | Fixed inside build.py and listed in SKILL.md §11 |
| 12 | **Scratch files lived in /tmp**, against the workspace-isolation rule, and would have been lost | Tools nearly unrecoverable | Everything is in the skill folder; work files live in `<footage>/_work` |

## Numbers worth remembering

- Source: 848×464 H.264 ~1.7 Mb/s, audio peaking at 0 dBFS on 5 of 16 clips.
- Real-sound shots after clean-up: −11 to −30 LUFS, matched to −18 (one clip capped at +10 dB).
- Music: "Journey to the Golden Temple" (TokyoRifft, Pixabay, AI-generated instrumental) at −11.5 LUFS;
  12 s offset; levels card 0.80 / story 0.62 / ritual 0.55 / finale 0.70; no ducking.
- Master: −14.0 LUFS, peak −4.1 dBFS, 2560×1440, 30 fps, 188.1 s, 851 MB (~36 Mb/s).
- AI upscale speed: 0.96–1.49 s/frame when the Mac was free; 5,400 frames ≈ 1.5–2 h.
- 1440p xfade assembly with the medium preset: 0.09–0.5× real time depending on load.

## Open question to settle on the next job

The client did not say exactly what the missing 50% was. On the next long-format job, include in the
Step B brief: "Last time felt 50% — what should be better: story/creativity, picture quality, sound,
graphics, or speed?" Then record the answer here.
