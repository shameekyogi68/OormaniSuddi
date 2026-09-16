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
