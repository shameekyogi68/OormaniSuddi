# business/ — the company's books (D118)

Private. Everything here except this file is gitignored, because the
repository is public; `scripts/backup.sh` carries it every night.

Set up once:

```bash
python3 scripts/business.py init
```

| File | What | Who writes it |
|---|---|---|
| `ledger.csv` | every rupee in and out | owner — `business.py money …` |
| `audience.csv` | weekly platform numbers | owner — `business.py audience …` |
| `deals.json` | sponsors, lead → paid | `business.py deal …` |
| `goals.json` | this quarter's goals | general manager proposes, owner confirms |
| `rate_card.json` | what each product costs | owner |
| `notes.md` | platform announcements, pasted | owner |
| `reports/` | the business desks' weekly / monthly reports | agents |
| `drafts/` | pitches, offers, invoices, follow-ups | agents draft; a person sends |

`python3 scripts/business.py status` is the one-screen view. The strategy is
in [`docs/BUSINESS.md`](../docs/BUSINESS.md); the firewall between money and
news is in [`docs/ADVERTISING.md`](../docs/ADVERTISING.md).
