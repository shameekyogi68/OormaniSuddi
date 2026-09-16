#!/bin/bash
# Install (or remove) the 06:05 morning intake job.
#
#   bash scripts/install_launchd.sh            install and load
#   bash scripts/install_launchd.sh --remove   unload and delete
#   bash scripts/install_launchd.sh --status    is it loaded, when did it last run
#
# Issue #19 of the board sheet. The script has always been written for 06:05
# and has only ever been run by hand, which means the one morning somebody
# oversleeps is the morning there is no tip sheet.
#
# Nothing here touches the network or the account. It writes one plist into
# ~/Library/LaunchAgents and loads it.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.oormanisuddi.morning"
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/$LABEL.plist"
TEMPLATE="$ROOT/scripts/launchd/$LABEL.plist.template"

case "${1:-install}" in
  --status)
    if launchctl list | grep -q "$LABEL"; then
      echo "🟢 $LABEL is loaded"
      launchctl list "$LABEL" 2>/dev/null | grep -E 'LastExitStatus|PID' || true
    else
      echo "🔴 $LABEL is not loaded"
    fi
    LAST="$(ls -t "$ROOT"/logs/fetch-*.log 2>/dev/null | head -1)"
    if [ -n "$LAST" ]; then
      echo
      echo "Last run — $LAST"
      tail -3 "$LAST"
    else
      echo "No fetch log yet."
    fi
    exit 0
    ;;
  --remove)
    launchctl unload "$PLIST" 2>/dev/null
    rm -f "$PLIST"
    echo "✓ $LABEL removed. The fetch is manual again:"
    echo "    python3 scripts/fetch_daily_news.py"
    exit 0
    ;;
esac

if [ ! -f "$TEMPLATE" ]; then
  echo "✗ template missing: $TEMPLATE" >&2
  exit 1
fi

# A second job firing at the SAME hour and minute means two fetches racing for
# inbox/today.md, and whichever finishes second wins silently. Only a genuine
# time collision is a problem — the nightly backup at 22:30 is not one.
#
# Compared by label and schedule only. The other job's script may well live
# outside this repository, and nothing here reads outside this repository.
when_of() {
  plutil -extract StartCalendarInterval xml1 -o - \
    "$HOME/Library/LaunchAgents/$1.plist" 2>/dev/null \
    | grep -A1 -E '>(Hour|Minute)<' | grep '<integer>' \
    | sed 's/[^0-9]//g' | paste -sd, - 2>/dev/null
}

OURS="$(when_of "$LABEL" 2>/dev/null)"
[ -z "$OURS" ] && OURS="6,5"          # what the template ships with
CLASH=""
for o in $(launchctl list 2>/dev/null | awk '{print $3}' \
           | grep -i '^com\.oormanisuddi\.' | grep -v "^$LABEL$"); do
  [ "$(when_of "$o")" = "$OURS" ] && CLASH="$CLASH $o"
done

if [ -n "$CLASH" ]; then
  H="${OURS%%,*}"; M="${OURS##*,}"
  printf -v AT '%02d:%02d' "$H" "$M" 2>/dev/null || AT="$H:$M"
  echo "⚠️  Another job already fires at $AT:" >&2
  for o in $CLASH; do echo "      $o" >&2; done
  echo >&2
  echo "    If that one also fetches the tip sheet, installing this as well" >&2
  echo "    gives you two jobs writing inbox/ at the same minute, and the" >&2
  echo "    loser is overwritten without saying so." >&2
  echo >&2
  echo "    Retire the old one:" >&2
  for o in $CLASH; do
    echo "      launchctl unload ~/Library/LaunchAgents/$o.plist" >&2
    echo "      rm ~/Library/LaunchAgents/$o.plist" >&2
  done
  echo >&2
  echo "    Or, if they genuinely do different things:" >&2
  echo "      bash scripts/install_launchd.sh --force" >&2
  if [ "${1:-}" != "--force" ]; then
    exit 1
  fi
  echo "    --force given; installing alongside." >&2
fi

mkdir -p "$AGENTS" "$ROOT/logs"
chmod +x "$ROOT/scripts/morning.sh"

# Substitute the real project root into the template. The template itself
# never carries a machine-specific path.
sed "s|__ROOT__|$ROOT|g" "$TEMPLATE" > "$PLIST"

launchctl unload "$PLIST" 2>/dev/null
if launchctl load "$PLIST"; then
  echo "✓ $LABEL installed — the tip sheet is fetched at 06:05 IST daily."
  echo "  root:   $ROOT"
  echo "  plist:  $PLIST"
  echo "  logs:   $ROOT/logs/fetch-YYYY-MM-DD.log"
  echo
  echo "  A failure puts a notification on screen; it does not fail silently."
  echo "  Check any time:  bash scripts/install_launchd.sh --status"
  echo "  Remove:          bash scripts/install_launchd.sh --remove"
  echo
  echo "  Note: the sheet is TIPS. Nothing becomes an edition until you open"
  echo "  the source and fill verified_by."
else
  echo "✗ launchctl refused to load $PLIST" >&2
  exit 1
fi
