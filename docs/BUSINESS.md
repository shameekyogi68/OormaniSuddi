# ಊರ್ಮನಿ ಸುದ್ದಿ — the company (D118)

The newsroom is described in [`AGENTS.md`](../AGENTS.md). This page is the
company around it: what it sells, where the money comes from, who decides
what, and the rhythm that keeps it alive. Read by the business desks
(`general-manager`, `revenue-manager`, `youtube-strategist`,
`facebook-strategist`, `ad-standards`, `finance-controller`) and by the owner.

Every line carries a label, so a guess is never mistaken for a fact:

* **[Rule]** — Indian law or a regulator's code. Confirm with a CA or lawyer
  before acting on money.
* **[Platform]** — the platform's own rule. Platforms change these; the
  figures live once, in `brand/business.py :: PLATFORM_RULES`, with the date
  each was last checked. The steward flags any older than `RULES_STALE_DAYS`.
* **[House]** — our own working rule.
* **[Guess]** — a starting point, to be replaced by our own numbers.

The money itself — ledger, deals, prices, goals — is **private**: it lives in
`business/` (gitignored; this repository is public) and is carried by
`scripts/backup.sh`. Nothing on this page is a figure about our money.

---

## 1 · What we are

A Kannada hyperlocal news company for the coast — Byndoor, Kundapura, Udupi,
Brahmavar, Karkala, Mangaluru. **The product is trust**: people believe what
ಊರ್ಮನಿ ಸುದ್ದಿ says about their own town. Every rupee we earn is rented on that
trust, so nothing that spends it is worth its price. [House]

Who reads us, and where [House — to be measured]:

| Platform | Who | What they want from us | What it pays |
|---|---|---|---|
| Instagram | young locals | the town in one swipe — the three formats | reach → sponsors |
| YouTube | everyone, the diaspora | real footage: festivals, Kambala, yakshagana, civic events | Partner Programme |
| Facebook | parents, Gulf/Mumbai diaspora, group admins | news from home to share | Content Monetization |
| WhatsApp | the town's forwarders | 2–3 items a day, never a flood; a public Channel beside the area groups | nothing directly — it carries the rest, and no platform can take it away |

## 2 · Where the money comes from

In the order it can realistically arrive [House]:

1. **Local sponsors — from week one.** No platform threshold. The sponsored
   festival greeting renders today (`templates/greeting.py`, `sponsor` +
   `deal`, D119); a multi-shop festival offer is one deal per shop. A jeweller,
   textile house, hospital, school or temple committee pays for a labelled
   product (`brand/business.py :: PRODUCTS`): a sponsored festival greeting,
   an ad post or reel, a sponsored video, paid coverage of their event, a
   live stream, a personal notice. Festivals are the sales calendar —
   pitch two to three weeks ahead (`scripts/whats_on.py`).
2. **Event coverage and live streams.** Organisers already want their jatre,
   wedding-hall function or school day filmed well; the footage skills make
   it premium. Labelled ಪ್ರಾಯೋಜಿತ on our channels.
3. **Production services.** Filming or editing *for* a client, not
   published by us, no ಊರ್ಮನಿ ಸುದ್ದಿ branding. Same skills, separate income.
4. **YouTube Partner Programme.** Fan funding first (`youtube_fans`), then
   ad revenue (`youtube_ads`). [Platform] Watch hours come from **long**
   videos — Shorts views count only toward the Shorts route.
5. **Facebook.** In-stream and Reels ads (`facebook_ads`), now run by Meta as
   Content Monetization, partly by invitation. [Platform] Minutes viewed come
   from native video, not links.
6. **Instagram.** No ad-revenue share for us; Instagram is the reach that
   sponsors pay for, plus subscriptions at the threshold
   (`instagram_subscriptions`). [Platform]
7. **Grants.** Journalism programmes open and close; when the owner pastes
   one into `business/notes.md`, the general manager weighs it. [House]

`python3 scripts/business.py status` shows how far each platform programme
is, from the numbers the owner logs weekly.

## 3 · The firewall — money never touches news

The whole policy is public, in [`ADVERTISING.md`](ADVERTISING.md). In short:
money buys a labelled product, never a story, a slot in a news format, a
softer story or a deleted one; every paid piece says so on the work itself
and through the platform's paid-partnership tool; some advertisers we never
take; and a deal goes live only after a person clears it. It is enforced by
`brand/business.py :: check_deal`, with no override flag — for the same
reason as D29.

## 4 · Who decides what

Agents are employees with a job description, not owners. [House]

| | Decides alone | Proposes; the owner decides | Never — a person only |
|---|---|---|---|
| **Business desks** | what to analyse; the content of their reports and drafts; which festival to pitch for | prices, goals, which sponsor to accept, spending, boosting, new products, platform strategy, any `tokens.Limits` change | send a message, sign, invoice for real, receive or pay money, clear a deal (`deal clear --by`), file taxes, publish |
| **Newsroom desks** | as in [`AGENTS.md`](../AGENTS.md) | | verify, sign off, upload (AGENTS rules 5, 7) |
| **The owner** | everything in the middle column | | |

Every decision the owner takes on the general manager's list goes where
`python3 scripts/house_rule.py where "…"` says, so it lasts (D73).

## 5 · The rhythm

| When | Who | What |
|---|---|---|
| daily | newsroom | the editions — `AGENTS.md` |
| Monday, 5 min | owner | log last week's numbers: `scripts/metrics.py add …` (posts) and `scripts/business.py audience …` (followers, watch hours, minutes) |
| Monday | revenue, YouTube, Facebook desks | their weekly reports in `business/reports/` |
| Monday, after them | general manager | the weekly business review: scorecard, three decisions, owners |
| any deal at pitched/agreed | ad-standards | reads it; then the owner clears it |
| 1st–5th of the month | finance controller | the monthly close |
| quarter end | general manager → owner | next quarter's goals into `business/goals.json` (`confirmed_by` = owner) |

`python3 scripts/dispatch.py` lists every desk that is due, under
"business". Each is one model run a week (finance: a month); none runs on
the production path.

## 6 · YouTube

**Content floats.** What is filmed depends on what happens and who can be
there; nothing here is a quota. The system's job is to make whatever is
filmed earn the most. [House, D119]

* Real footage, real voice, or a face to camera — never an AI card reel as
  the whole video (AGENTS rule 9). [Data — weeks 1–3: 37 vs 397 views]
  YouTube's "inauthentic content" policy (renamed 15 Jul 2025) is the
  monetisation risk behind that number. [Official]
* **Watch hours come from long videos and live streams**, never from Shorts
  views. A long event with a crowd (Kambala, yakshagana, jatre) streamed
  live and archived publicly is the fastest honest source of them. [Official;
  planning numbers are Estimate — 15–40 people watching at our size]
* **Shorts are the doorway**: each Short cut from a long video sets that
  video as its Related video in Studio. [Official feature]
* **Taluk and season playlists, and an end screen** on every long video, so
  one video leads to the next. [House]
* Old AI-slideshow uploads are kept private before applying to the Partner
  Programme. [House, decisions_2026-10 A6]
* Packaging follows the footage skills' upload sections: Kannada title, `|`,
  place and topic in English; the towns in the first three description
  lines; chapters over 3 minutes; the Kannada engagement question last.
* A paid video ticks "includes paid promotion" and shows ಪ್ರಾಯೋಜಿತ. [Platform, Rule]

## 7 · Facebook

* Native uploads of every long real-footage video, Kannada caption; any link
  in the first comment (house rule 2026-10-12-03). [House]
* Diaspora (Mumbai, Gulf): a test of cultural footage at 8:30–10 pm IST,
  judged by the logged numbers. [Reported — to be measured]
* The three formats go to the Page on `docs/CHANNELS.md`'s schedule (D94).
* Local groups: one ಮುಖ್ಯ ಸುದ್ದಿ per group per week at most, question first,
  no outside link (`facebook_group_<k>.txt`). [House, D94]
* Paid posts use Meta's branded-content tool. Boost only what already did
  well, with a ₹ cap and a town radius, logged as `boost`. [House]

## 8 · Money

* **Every rupee goes in the ledger** — `scripts/business.py money …`. Income
  and expense streams are fixed lists in `brand/business.py`; `ref` is the
  deal id. [House]
* **Separate bank account** for the business, and UPI/bank transfer for every
  deal, so the ledger and the bank agree. Cash is the exception. [House]
* **Tools are a cost of doing business**, logged as `ai_tools` / `software`.
  The status screen says how many times this month's income covers them. [House]
* **TDS.** A company paying us may deduct TDS (194C / 194J) and give a
  certificate; log it in `--tds` and claim it in the return. [Rule]
* **GST.** Registration is compulsory once a financial year's aggregate
  turnover from services passes `GST_THRESHOLD_INR` in Karnataka;
  `scripts/business.py status` warns at `GST_WARN_SHARE` of it. Advertising
  services carry GST once registered; platform income from abroad counts in
  turnover. A CA decides the details. [Rule]
* **Income tax.** A proprietor files an ITR; whether the presumptive scheme
  suits (44AD / 44ADA) is the CA's call. [Rule]
* **US tax on YouTube.** Submit the US tax form in AdSense; without it Google
  withholds a higher rate on earnings from US viewers. [Platform]
* **Starting prices** are `[Guess]` values in `business/rate_card.json`, set
  by the owner. The revenue desk proposes changes once five deals exist.
* **Set up once** [House]: PAN-linked business bank account, Udyam (MSME)
  registration, a CA's contact, invoice numbering = deal id.

## 9 · Compliance calendar

[Rule — confirm each with the CA; dates move by notification]

| When | What |
|---|---|
| 15 Jun · 15 Sep · 15 Dec · 15 Mar | advance tax instalments, if the year's tax is over the advance-tax line (the presumptive scheme pays once, by 15 Mar) |
| 31 Jul | income-tax return (no audit) |
| monthly / quarterly | GST returns — only once registered; the CA sets the scheme |
| within 24 h / 15 days | IT Rules 2021 grievance clocks — `scripts/correction.py status` |
| once, and on change | IT Rules 2021 Rule 18 — the publisher's details furnished to the Ministry of I&B; confirm it was done |
| every election | Model Code of Conduct: political ads need the MCMC pre-certificate; paid news is an electoral offence (ADVERTISING.md) |
| every 6 months | confirm `PLATFORM_RULES` against YouTube Studio and the Professional dashboard; update `checked` |

## 10 · What success looks like

Goals live in `business/goals.json`, proposed by the general manager,
confirmed by the owner. The starter goals are the platforms' own thresholds,
the first paying sponsors, and income that covers the tools. Measured, not
felt: if a goal has no number in the books, it is not a goal yet. [House]
