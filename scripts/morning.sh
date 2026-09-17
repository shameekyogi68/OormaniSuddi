#!/bin/bash
# ಊರ್ಮನಿ ಸುದ್ದಿ — the 06:05 intake, and what happens when it fails.
#
# Run by launchd (see scripts/launchd/). The whole point of the wrapper is the
# failure path: a fetch that dies quietly at 06:05 is discovered at noon, which
# is a day without an edition. This puts a notification on the editor's screen
# instead.
#
# Install:  bash scripts/install_launchd.sh
# Run now:  bash scripts/morning.sh
# Logs:     logs/fetch-YYYY-MM-DD.log

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

mkdir -p logs
DATE="$(date +%Y-%m-%d)"
LOG="logs/fetch-$DATE.log"

notify() {
  # osascript is on every Mac; no dependency, no account, no service.
  /usr/bin/osascript -e "display notification \"$2\" with title \"ಊರ್ಮನಿ ಸುದ್ದಿ\" subtitle \"$1\"" 2>/dev/null || true
}

{
  echo "════════════════════════════════════════════════"
  echo "$(date '+%Y-%m-%d %H:%M:%S')  morning intake"
} >> "$LOG"

if /usr/bin/env python3 scripts/fetch_daily_news.py >> "$LOG" 2>&1; then
  TIPS=$(/usr/bin/env python3 -c "
import json,sys
try:
    d=json.load(open('inbox/today.json',encoding='utf-8'))
    c=d.get('counts',{})
    print(f\"{c.get('tips',0)} tips · {c.get('full_articles',0)} full articles · {c.get('flagged_unsupported',0)} to verify\")
except Exception:
    print('tip sheet ready')
" 2>/dev/null)
  echo "$(date '+%H:%M:%S')  OK — $TIPS" >> "$LOG"

  # What is coming, and anything overdue. This is the moment it is useful:
  # a festival three days out is still a shoot you can arrange, and one that
  # is tomorrow is a card you rush.
  {
    /usr/bin/env python3 scripts/whats_on.py --days 21
    /usr/bin/env python3 scripts/whats_on.py --reviews
  } >> "$LOG" 2>&1

  # Turn the tip sheet into a real, renderable edition — every field copied
  # from the tips, nothing written. verified_by stays empty on every story;
  # this is what collapses the morning from "read 33 tips and write JSON" to
  # "open four links and run one command each" (D76). It never overwrites an
  # edition that already exists — a human may already be mid-edit.
  DRAFT_MSG="tip sheet ready"
  if [ ! -f "editions/$DATE.json" ]; then
    if /usr/bin/env python3 scripts/draft_edition.py --date "$DATE" >> "$LOG" 2>&1; then
      DRAFT_MSG="$(/usr/bin/env python3 -c "
import json
d=json.load(open('editions/$DATE.json',encoding='utf-8'))
print(f\"{len(d['stories'])} stories drafted — open inbox/checklist_$DATE.md\")
" 2>/dev/null || echo 'edition drafted')"
    else
      echo "$(date '+%H:%M:%S')  draft_edition: nothing safely auto-drafted — build editions/$DATE.json by hand from inbox/today.md" >> "$LOG"
    fi
  else
    echo "$(date '+%H:%M:%S')  editions/$DATE.json already exists — not touching it" >> "$LOG"
  fi

  DUE=$(/usr/bin/env python3 scripts/whats_on.py --reviews 2>/dev/null | grep -c '⚠️' || true)
  if [ "${DUE:-0}" -gt 0 ]; then
    notify "$DRAFT_MSG · $DUE review(s) due" "$TIPS"
  else
    notify "$DRAFT_MSG" "$TIPS"
  fi
  exit 0
fi

REASON="$(cat inbox/.fetch_failed 2>/dev/null | tail -1)"
[ -z "$REASON" ] && REASON="see $LOG"
echo "$(date '+%H:%M:%S')  FAILED — $REASON" >> "$LOG"
notify "Morning fetch FAILED" "$REASON"
exit 1
