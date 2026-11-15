# What was wrong with the voice in the 30 Oct reel — and what now stops it

The reel posted at about 01:30 on 30 Oct (`out/2026-10-30/reel_saara.mp4`, 55.4 s) was **not** re-made and its voice was **not** re-recorded. Its original
Gemini recordings were still on disk (`build/tts_cache`), so I listened to those, and to the published file itself.

## How I listened (and what that does and does not prove)

Nobody on the team can hear sound, me included. What I did instead was ask three separate listeners to write down, in Kannada letters, exactly what each clip
sounds like — **without telling them what it was supposed to say**, so they could not "hear" a word that was never spoken:

* Gemini 3.5-flash, Gemini 3-flash-preview, Gemini 3.1-flash-lite and 3.8-flash (audio models that read Kannada),
* Whisper (what the pipeline already used), and
* a pitch-and-silence measurement (Praat) for the pauses and the tone.

A fault below is listed only where **two or more listeners agreed**. This proves that a word was *not said, or said as another word*. It cannot prove that a name sounds the way
the valley says it, or judge accent and warmth. That part is still your ear.

## What was wrong (the published reel, by time in the video)

| Where | What the voice did | Listeners | Measured |
|---|---|---|---|
| **Opening, 0:00** | ವಂಡ್ಸೆ said as **"ಒನ್ ಸೇ"** (one-say); ಹೆಮ್ಮಾಡಿ lost its double ಮ್ಮ ("ಹೇಮಾಡಿ"/"ಹೆಂಮಾಡಿ") | 3.8-flash, Whisper (3.5-flash smoothed it to "ವಂದ್ಸೆ", still no ಡ) | — |
| **Story 2 headline, 0:15** | **The town was never said.** The recording starts at "ಹಸಿ ಕಸ ವಿಲೇವಾರಿಗೆ…". The screen showed ವಂಡ್ಸೆ; the voice said nothing | all of them | the first sound is 0.27 s in, and it is "ಹಸಿ" |
| **Story 2 card, 0:19** | First word **ಕಪ್ಪು cut off → "ಹೂ" / "ಪು"**. The headline/card cut was placed on the assumption that the town had been said, so it fell inside the card's first word | Gemini, Whisper | — |
| **Story 4 headline, 0:31** | "ಕುಂದಾಪುರ. / ಮಹೇಶ್ ಪಿಎಸ್. / ಎಸಿ ಅಧಿಕಾರ ಸ್ವೀಕಾರ." — **a man's name read as three sentences** | Gemini, Whisper | silences of **0.66 s, 0.64 s and 1.07 s** inside one headline |
| **Story 5 headline, 0:41** | "ಬ್ರಹ್ಮಾವರ. / ಸುಜಿತ್ ಹತ್ಯೆ. / ಆರೋಪಿಗಳು ಜೈಲಿಗೆ." — cut in three at the colon | Gemini | silences of 0.46 s and 0.45 s |
| **Story 4 card, 0:36** | **ನೀಡುವುದಾಗಿ → ನೀಡುವಾಗಿ** (a syllable lost; the meaning changes to "while giving") | Gemini, Whisper | — |

Right, as far as the listeners could tell: story 1, the story 3 card, the story 5 card (ಹದಿನಾಲ್ಕು ✓), the follow line.

**Two things I could not settle — please listen once:** (1) story 3's **ಕಟ್ಬೆಳತೂರು** — the voice says something like "ಕಡ್ಬೆಲ್ತೂರು", the screen spells ಕಟ್ಬೆಳತೂರು; I cannot tell which the village uses.
(2) **ವಿಧಿಸಿದೆ** in story 5 — one listener wrote a stray letter; probably the listener's slip, but it is the word an arrest turns on.

**Tone.** The median pitch of the clips was 187–207 Hz for the stories, 190 for the opening and **216 for the follow card** (about 2 semitones higher — that clip is the same recording every day). Each story is a separate request,
so the voice's "mood" can differ between stories. This voice model takes **no direction** (D145: it answers a direction with silence), so tone can be measured but not controlled. What I could fix is the part that made it sound choppy (below).

## Why every check had passed

The only check that listens was Whisper, and Whisper **cannot read Kannada**: it writes a perfectly good clip as noise ("ಹಸಿಕಿಕಸ", "ಪು ಸೈಯನಿಕ"). So it scored the clip with the missing town **0.87** and could only say
"listen for ವಂಡ್ಸೆ" — one warning among five, with no way for you to know which was real. Warnings were being published.

## What changed (all in the repo, 789 tests pass; the posted reel is untouched)

1. **A listener that reads Kannada, word by word** (`brand/ear.py`). Every clip is heard blind and compared with the words it was meant to say. A **town or name** must be heard whole; the **first and last word** of each clip (where a cut can eat a sound) are held tighter.
   A missing or changed word is no longer a warning: it **holds the package (`SND-09`)**. I replayed the real transcripts of your reel through it: it holds every fault in the table above, and passes the clips that were right.
2. **It puts the clip right before holding it** (`brand/reel_listen.py`): first it re-cuts the headline/card at the recording's other silences (costs no voice request); then it asks for a new take with the failing word spelled another way (at most 3); then it stops and says which word.
3. **The text the voice is given**: initials are read as letters (`ಪಿ.ಎಸ್:` → `ಪಿ ಎಸ್`); a headline's colon is a breath, not a full stop; no silence inside a clip may be longer than 0.55 s (`Limits.ear_pause_max`).
   On a real run today the Kundapura headline came out as **one sentence, 0.6 s shorter**, with no dead air.
4. **Towns the voice cannot say** (`assets/voice/towns.json`). I tried hard — about 23 takes of ವಂಡ್ಸೆ on the voice you use, in several spellings, in lists, in phrases and after a carrier word. It was heard right **3 times**, and each of those was wrong again when repeated. (The two newer Gemini voice models also sounded wrong, but only the weak Whisper checked them.) ಯಡ್ತರೆ: every take wrong ("ಎಡ್ತರೆ").
   (ಉಪ್ಪುಂದ is fine inside a phrase and is **not** flagged; the ear still checks it every day.) A flagged town is **kept out of the opening line**, and its dateline is a **recording of the name that a person has approved**. Until there is one, a story datelined there is **held, not spoken wrong**.
5. Tests: `tests/test_ear.py` (replays your reel's real transcripts), `tests/test_town_clips.py`. Decision `D146`; `docs/REEL_STANDARD.md §5b`; the `/daily-saara` skill (both copies).

I also ran one real end-to-end build on a 2-story cut of the 30 Oct edition (not published): the ear caught the voice clipping "ಕುಂದಾಪುರ" in the opening ("ಕುಂದಾಪ್ಡ"), asked again, and heard it right on take 2.

## What you need to do — and what I could not finish

* **ವಂಡ್ಸೆ and ಯಡ್ತರೆ need a recording of the name by a person.** Say each name once into Voice Memos on your phone or Mac (3 seconds), then:
  `python3 scripts/town_clips.py add ವಂಡ್ಸೆ recording.m4a --made-with "recorded by <who>"` — listen to the file it prints — then
  `python3 scripts/town_clips.py approve ವಂಡ್ಸೆ --by "<your name>"`. It is spliced in front of the headline in every story from that town. (Your voice or a woman's voice? Your call: it is one word before the Kore voice takes over. If you would rather not, the editor can choose a different dateline for that story.)
  I did not approve anything and I did not invent a name.
* **Run the reel after 12:30 IST when you can.** Gemini's free allowance — for the voice (10 requests a day per key) and for the listeners (20 a day per key) — resets at 12:30 IST, so a **1 a.m. run draws on the same day as today's**, and my testing used part of it
  (14 voice requests; most of the strong listeners). A 1 a.m. reel will still be made and still be listened to by Whisper and the lighter Gemini ears, and the gate will say plainly "only Whisper heard" — which is a weaker check. More Gemini keys, or billing on the key, remove this limit.
* **Tone and accent are still your ear's job.** I cannot make the voice warmer or more serious; I removed what made it choppy.

## If a reel is held tomorrow

The gate says which story, which word, and what was heard. Re-running the render asks again for the failing clips only (the rest come from the cache). Do not edit a check to make it pass.
