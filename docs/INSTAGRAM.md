# Instagram playbook — how ಊರ್ಮನಿ ಸುದ್ದಿ writes for people and for the feed (D97)

Read by the `instagram-strategist` and the `social-writer`. Short on purpose.
Every line carries a label, so a guess is never mistaken for a fact:

* **[Official]** — Instagram or its head has said so publicly.
* **[Reported]** — widely reported by people at the platform, not on a help page.
* **[House]** — our own working rule. A hypothesis until the numbers say so.
* **[Data]** — measured on *this* channel. There is none yet: only two posts were
  ever logged (see §6). Every [House] line is waiting to become [Data] or be dropped.

The algorithm changes. The agents have no web access (D92), so this file is
kept current by the editor: paste Instagram's own announcements into
`inbox/instagram_notes.md` and the strategist will weigh them above this page.

## 1 · What the feed rewards

1. **People, not signals, are the point.** The feed asks "would this person like
   this?", per surface (Feed, Reels, Explore, Stories). Reels and Explore are
   where people who do not follow us find us. [Official]
2. **The three signals Instagram names for Reels:** watch time, likes per reach,
   and **sends per reach** (shared in a DM) — sends matter most for reaching
   people who do not follow. [Official, 2025 — re-check against the notes file]
3. **Saves and sends beat likes.** A save says "I will need this", a send says
   "you need this". Likes are the cheapest signal. [Official/Reported]
4. **A carousel nobody swipes may be shown again, starting at slide 2.**
   [Reported] Slide 2 must therefore work as a first slide.
5. **Original beats re-posted.** Aggregated or watermarked content from other
   apps is shown less. [Official] Our copy is written from our own reading of
   the source, in our own design — never paste a source's text or image.
6. **Words in the caption are search terms.** Place, topic and what happened,
   in plain Kannada and in English — hashtags matter less than they did. [Reported]
7. **Five hashtags at most**, only true to the story (D86, `PUB-09`). [House, D86]
8. **No engagement bait.** "Like if…", "tag three friends" and giveaways-for-follows
   are demoted. A real question about the reader's own town is fine. [Official]

## 2 · What a person does with a post (psychology)

All [House] — to be tested.

* **One second to decide.** The first slide or frame must carry a place the
  viewer lives in and something that happened. A town name is the strongest
  stop-sign this channel has.
* **They share what is theirs.** Nobody forwards a seven-town digest; people
  forward their own town's news (D72). Name the town first.
* **Curiosity pulls, a full list does not.** On 27 Sept the cover listed every
  headline and readers stopped there. Keep the index (the owner's choice) but
  the swipe cue and the second slide must earn the swipe. Judge it by
  swipe-through, not by taste.
* **Utility is saved; news is sent.** Deadlines, holidays, helplines, rules →
  saves. Something a neighbour should know *now* → sends. Write each for the
  action it should produce.
* **Sending is a small act of status.** The sender wants to be first and
  useful. Make the news forwardable in one line: place, what, what to do.
* **Sober is credible.** Deaths and crime: plain words, no shock framing — it is
  also the law (D29) and why those headlines stay in ink.
* **Kannada reads slowly on a moving screen** — about 7 characters a second on
  video (`Motion.read_rate`). One idea per frame. Never more words than a
  person can read before the next change.
* **The Gulf reads at a different hour.** 08:00 IST is 06:30 in the UAE and
  18:30 IST is 17:00: both land in a Gulf family's day. Gulf news (ಅನಿವಾಸಿ) is
  saved and sent abroad, so it earns a picture.

## 3 · One format, one job

| Format | Job it is built for | The signal it should earn |
|---|---|---|
| ಸ್ಪೀಡ್ ನ್ಯೂಸ್ (reel) | reach people who do not follow us | watch time, then sends |
| ಸುದ್ದಿ ಸಾರ (text carousel) | be the morning habit | saves, swipe-through |
| ಮುಖ್ಯ ಸುದ್ದಿ (photo carousel) | the one story worth sending | sends, comments |

## 4 · Writing for it

**Carousel slides** (`Paper`, `Limits`): the cover says what the post is and
that there is more; every slide after it leads with its place and is complete
on its own; a swipe cue on every slide but the last (`EverySlideLeadsToTheNext`);
the last slide says where to save, send and follow. Slides are text-light:
headline within `Limits.headline_chars`, three points at most.

**Captions:**
1. Line one: the hook, with the town, inside the first 125 characters
   (`reach.place_before_fold`, `PUB-05`) — what is shown before "more".
2. Then what it is (and how many stories), one honest question, the source,
   the Grievance line, the 📍 towns, five hashtags (`brand/copy.py` does this).
3. No links in the caption (they are not clickable). The WhatsApp link lives on
   the slides and in the bio.
4. **Alt text** is written for every post (`MASTER_COPY.md` lists it): it helps
   search and it is the only way a blind reader gets the post.

**Video carousels** (D98, D99): every carousel is posted as videos. Motion in
the feed is itself a stop-sign, but the first frame is what the grid and a
fast thumb see, so a cover is never blank: its picture and headline are there
at frame 0. [House] — compare swipe-through and saves against the still
carousels once `metrics.py` has enough posts.

**Reels from footage:** the hook in the first two seconds, the news card clear of
Instagram's own interface (D96).

## 5 · The first hour, and the day after

Posting is not the end. [House]

1. Post at the slot in `schedule.txt` (`Limits.carousel_slot`, `mukhya_slot`,
   `roundup_slot`) — or the moment a breaking story is signed.
2. **Answer every comment in the first hour**, by name, in Kannada. A reply is
   a second chance for the post to be seen.
3. **Put the post in the WhatsApp community** straight away (`whatsapp_<group>.txt`):
   sends from people who already trust us are the strongest early signal.
4. **Share it to Stories** with the town named.
5. **The next morning**, look at one number per post (§6) and write it down.

## 6 · The loop that is missing

Only two posts were ever logged, so nothing here is yet *measured*. Once a week
the editor types what the Insights screen shows, in about two minutes:

```bash
python3 scripts/metrics.py add --date 2026-10-03 --asset saara --format saara \
    --category civic --at 08:00 --views 900 --reach 700 --saves 30 --shares 25 \
    --nonfollowers 35
python3 scripts/metrics.py report --weeks 4
```

Rules for reading it (so we do not fool ourselves):
* The report stays silent below 20 posts in all (5 per group): fewer is astrology.
* Compare **sends and saves per 1,000 reach**, not raw views.
* Watch the **share of reach from people who do not follow us** (`--nonfollowers`) — that is growth.
* Change one thing at a time: the hook, or the slot, or the format.
* The weekly planning review turns each [House] line above into [Data] or deletes it.

## 7 · Never

Buy engagement · tag unrelated trends · post a source's image or text as ours ·
use a shock headline on a death · write a hook the story cannot pay off · reply
to a complaint about an error with anything but the corrections process
(`docs/CORRECTIONS.md`).
