# ಊರ್ಮನಿ ಸುದ್ದಿ — YouTube channel kit

Everything here is made from the logo and the house colours by
`scripts/youtube_kit.py`. To rebuild after changing the logo:

```bash
python3 scripts/youtube_kit.py
```

Files starting with `_check_` show the safe areas. They are only for checking, so never upload them.

## Where each file goes

| File | Where to upload it | Notes |
|---|---|---|
| `profile_800.png` | Studio → Customisation → Branding → **Picture** | YouTube crops it to a circle |
| `banner_2560x1440.jpg` | Studio → Customisation → Branding → **Banner image** | All the text and the logo stay inside the 1546×423 area that phones show |
| `watermark_150.png` | Studio → Customisation → Branding → **Video watermark**, display time "Entire video" | This is YouTube's clickable subscribe button. Nothing is burned into the video |
| `thumbnail_sample_seneshwara.jpg` | Studio → the video → **Thumbnail** | A sample made from a real frame of the Seneshwara Ganapathi video |
| `endscreen_1920x1080.png` | Put it in the last 20 s of every long video, then Studio → **End screen** | Place two Video elements on the dark boxes and the Subscribe element on the round logo. `_check_endscreen_slots.jpg` shows where |
| `live_starting_soon_1920x1080.png` | The first scene in the streaming app before a live stream | |
| `live_be_right_back_1920x1080.png` | For a break during the stream | |
| `live_thank_you_1920x1080.png` | For the last minute of the stream | |
| `live_overlay_1920x1080.png` | Transparent overlay placed over the camera during the live stream | Logo and ನೇರಪ್ರಸಾರ pill in the top-left |

## A thumbnail for every video

Start from a real frame of that video, with the deity, a face or the moment large in it:

```bash
python3 scripts/youtube_kit.py thumb --photo frame.jpg --title "ಸೇನೇಶ್ವರ ಗಣಪತಿ ಪ್ರತಿಷ್ಠಾಪನೆ" --place "ಬೈಂದೂರು" --out out/thumb.jpg
```

* `--title`: 2–4 Kannada words. The last line goes on gold.
* `--place`: the town, shown in the red pill.
* `--tag "ನೇರಪ್ರಸಾರ"` for a live stream.
* `--focal 0.45 0.30`: where the subject is in the photo, so the crop keeps it.
* The bottom-right is kept empty because YouTube puts the video length there.
* Never use a close-up of a child as the thumbnail (youtube-longform-edit rule).

## Channel text (Studio → Customisation → Basic info)

**Name:** ಊರ್ಮನಿ ಸುದ್ದಿ | Oormani Suddi
**Handle:** @oormanisuddi

**Description:**

```
ಊರ್ಮನಿ ಸುದ್ದಿ — ನಮ್ಮ ಊರು • ನಮ್ಮ ಧ್ವನಿ

ಕರಾವಳಿಯ ಊರಿನ ಸುದ್ದಿ, ಕನ್ನಡದಲ್ಲಿ. ಹಬ್ಬ, ಜಾತ್ರೆ, ಕಂಬಳ, ಯಕ್ಷಗಾನ, ದೇವಸ್ಥಾನದ ಉತ್ಸವಗಳು ಮತ್ತು ಊರಿನ ಆಗುಹೋಗುಗಳು — ನಮ್ಮ ವರದಿಗಾರರು ಸ್ಥಳದಲ್ಲೇ ಚಿತ್ರೀಕರಿಸಿದ ದೃಶ್ಯಗಳೊಂದಿಗೆ.

Local news from coastal Karnataka (Karavali), in Kannada — festivals, jatres, Kambala, Yakshagana, temple events and civic news, filmed on the ground.

📸 Instagram: https://www.instagram.com/oormanisuddi
💬 WhatsApp: https://chat.whatsapp.com/KZieCRqqaCaDjGADvbVYzg

ತಿದ್ದುಪಡಿ / ದೂರು (Grievance Officer): Gautam Paduvari · +91 96117 56514

ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ, ಬೆಲ್ 🔔 ಒತ್ತಿ — ನಿಮ್ಮ ಊರಿನ ಸುದ್ದಿ ತಪ್ಪಿಸಿಕೊಳ್ಳಬೇಡಿ.
```

**Links (shown on the banner):** Instagram and WhatsApp, the same two links as above.

**Channel keywords (Studio → Settings → Channel):**

```
ಊರ್ಮನಿ ಸುದ್ದಿ, Oormani Suddi, ಕರಾವಳಿ, Karavali, ಕನ್ನಡ ಸುದ್ದಿ, Kannada News, ಉಡುಪಿ, Udupi, ಬೈಂದೂರು, Byndoor, ಕುಂದಾಪುರ, Kundapura, ಕಂಬಳ, Kambala, ಯಕ್ಷಗಾನ, Yakshagana, ಜಾತ್ರೆ, Coastal Karnataka
```

**Country:** India. **Default upload language:** Kannada.
