# ಊರ್ಮನಿ ಸುದ್ದಿ — YouTube channel kit

Everything here is drawn from the logo by `scripts/youtube_kit.py`: deep ink,
warm gold light, and the round logo exactly as it is. To rebuild:

```bash
python3 scripts/youtube_kit.py            # stills + motion
python3 scripts/youtube_kit.py --still    # stills only (10 s)
```

Files starting with `_check_` show the safe areas. They are only for checking, so never upload them.

## Where each file goes

| File | Where | Notes |
|---|---|---|
| `profile_800.png` | Studio → Customisation → Branding → **Picture** | The round logo; YouTube crops a circle |
| `banner_2560x1440.jpg` | Branding → **Banner image** | Logo, name line and subscribe button sit inside the 1546×423 strip that phones show |
| `watermark_150.png` | Branding → **Video watermark**, display time **Entire video** | YouTube's clickable subscribe button; nothing is burned into the video |
| `thumbnail_sample_seneshwara.jpg` | the video → **Thumbnail** | Sample from a real frame of the Seneshwara Ganapathi video |
| `motion_intro_1920x1080.mp4` | First 4 s of a long video | Gold dust drifts, the round logo comes into focus, a glint runs round its rim, the name settles, the camera pushes in slowly. House sound effects |
| `motion_endscreen_1920x1080.mp4` | Last 20 s of every long video, then Studio → **End screen** | Everything is in place by 1.2 s. Put two Video elements on the dark panels and the Subscribe element on the medallion (`_check_endscreen_slots.jpg`) |
| `endscreen_1920x1080.png` | The same end screen as a still | For editors that want an image |
| `motion_live_starting_soon_loop_1920x1080.mp4` | Before a live stream, set to loop | 10 s seamless loop: breathing light, a glint on the ring, the live dot pulses |
| `live_starting_soon / be_right_back / thank_you _1920x1080.png` | Scenes in the streaming app | |
| `live_overlay_1920x1080.png` | Transparent overlay on the camera during a stream | Medallion and ನೇರಪ್ರಸಾರ pill, top-left |

## A thumbnail for every video

Start from a real frame of that video, with the deity, a face or the moment large in it:

```bash
python3 scripts/youtube_kit.py thumb --photo frame.jpg --title "ಸೇನೇಶ್ವರ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ" --place "ಬೈಂದೂರು" --out out/thumb.jpg
```

* `--title`: 2–4 Kannada words. The last line goes on metallic gold.
* `--place`: the town, shown in the red pill.
* `--tag "ನೇರಪ್ರಸಾರ"` for a live stream.
* `--focal 0.45 0.30`: where the subject is in the photo, so the crop keeps it.
* The bottom-right is kept empty because YouTube puts the video length there.
* Never use a close-up of a child as the thumbnail (youtube-longform-edit rule).

## Channel text — as set on YouTube (Studio → Customisation → Basic info)

**Handle:** @OormaniSuddi · **Language:** Kannada · **Contact email:** oormanisuddi@gmail.com

**Kannada** — name `ಊರ್ಮನಿ ಸುದ್ದಿ | Oormani Suddi`:

```
ಊರ್ಮನಿ ಸುದ್ದಿ — ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ

ಕರಾವಳಿಯ ಊರಿನ ಸುದ್ದಿ, ಕನ್ನಡದಲ್ಲಿ.

Local news from coastal Karnataka (Karavali), in Kannada.

📸 Instagram: https://www.instagram.com/oormanisuddi
💬 WhatsApp: https://chat.whatsapp.com/KZieCRqqaCaDjGADvbVYzg

ತಿದ್ದುಪಡಿ / ದೂರು : Gautam Paduvari · +91 96117 56514 · oormanisuddi@gmail.com

ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ, ಬೆಲ್ 🔔 ಒತ್ತಿ — ನಿಮ್ಮ ಊರಿನ ಸುದ್ದಿ ತಪ್ಪಿಸಿಕೊಳ್ಳಬೇಡಿ.
```

**English** (translation) — name `Oormani Suddi`:

```
Oormani Suddi — Namma Ooru • Namma Dhwani (Our town • Our voice)

Local news from coastal Karnataka (Karavali), in Kannada.

📸 Instagram: https://www.instagram.com/oormanisuddi
💬 WhatsApp: https://chat.whatsapp.com/KZieCRqqaCaDjGADvbVYzg

Corrections / complaints: Gautam Paduvari · +91 96117 56514 · oormanisuddi@gmail.com

Subscribe and press the bell 🔔 so you never miss news from your town.
```

**Links:** Instagram and WhatsApp. **Watermark display time:** Entire video.

**Channel keywords (Studio → Settings → Channel):**

```
ಊರ್ಮನಿ ಸುದ್ದಿ, Oormani Suddi, ಕರಾವಳಿ, Karavali, ಕನ್ನಡ ಸುದ್ದಿ, Kannada News, ಬೈಂದೂರು, Byndoor, Coastal Karnataka
```

## Instagram (@oormanisuddi)

Name `ಊರ್ಮನಿ ಸುದ್ದಿ | Oormani Suddi` · picture `profile_800.png` · category "News & media website" (label shown).

```
ಕರಾವಳಿಯ ಊರಿನ ಸುದ್ದಿ • Karavali local news
ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ
DM for Live Broadcast or Contact 9611756514
```

Links: WhatsApp community and YouTube (`https://www.youtube.com/@OormaniSuddi`).
Contact: email oormanisuddi@gmail.com, phone +91 9611756514 (Call), both displayed.
WhatsApp Business number left blank, since it is only for ads.

## Rules for anything added here

* Only what the owner has stated goes in channel text or on artwork: no topic lists, no claims about who films what, no superlatives.
* No decorative lines: no stripes, rules, streaks or underlines. Use light and fills only.
* Gold is a fill, never type. Red only on news elements (place, live).
