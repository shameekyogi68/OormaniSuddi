#!/bin/bash
# ಊರ್ಮನಿ ಸುದ್ದಿ — three copies, two media, one offsite.
#
#   bash scripts/backup.sh              back up now
#   bash scripts/backup.sh --status     when did each copy last happen
#   bash scripts/backup.sh --install    run it nightly at 22:30 via launchd
#
# Git covers the CODE. It deliberately does not cover the two things that
# cannot be regenerated:
#
#   archive/    the published record — every edition JSON, its APPROVAL.md,
#               the copy that actually went out, the corrections ledger and
#               the metrics. If a complaint arrives in March about something
#               published in November, this is the only evidence that exists.
#   assets/     the stock library and the licensed music beds.
#
# Losing the code costs a rebuild. Losing archive/ costs the ability to defend
# a story, which under IT Rules 2021 is not a thing you can shrug at.
#
# This script is deliberately dumb: tar + rsync, nothing to keep alive, no
# account, no service. Set OORMANI_BACKUP_DIR to an external drive and it uses
# it; otherwise it writes locally and tells you that local-only is not a backup.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

LOCAL="$ROOT/.backups"
EXTERNAL="${OORMANI_BACKUP_DIR:-}"
STAMP="$(date +%Y-%m-%d)"
KEEP=14                    # daily archives to retain locally

notify() {
  /usr/bin/osascript -e "display notification \"$2\" with title \"ಊರ್ಮನಿ ಸುದ್ದಿ\" subtitle \"$1\"" 2>/dev/null || true
}

case "${1:-run}" in
  --status)
    echo
    echo "  git         $(git -C "$ROOT" log -1 --format='%h %cr' 2>/dev/null || echo 'no commits')"
    REMOTE_STATE="$(git -C "$ROOT" rev-list --count '@{upstream}..HEAD' 2>/dev/null)"
    if [ -n "$REMOTE_STATE" ]; then
      [ "$REMOTE_STATE" = "0" ] && echo "  offsite     pushed, up to date" \
                                || echo "  offsite     ⚠️  $REMOTE_STATE commit(s) NOT pushed"
    else
      echo "  offsite     ⚠️  no upstream set — 'git push -u origin master'"
    fi
    LAST="$(ls -t "$LOCAL"/oormani-*.tar.gz 2>/dev/null | head -1)"
    [ -n "$LAST" ] && echo "  local       $(basename "$LAST")  $(du -h "$LAST" | cut -f1)" \
                   || echo "  local       ⚠️  never run"
    if [ -n "$EXTERNAL" ]; then
      [ -d "$EXTERNAL" ] && echo "  external    $EXTERNAL  $(ls -t "$EXTERNAL"/oormani-*.tar.gz 2>/dev/null | head -1 | xargs -I{} basename {} 2>/dev/null || echo 'never run')" \
                         || echo "  external    ⚠️  $EXTERNAL is not mounted"
    else
      echo "  external    ⚠️  OORMANI_BACKUP_DIR is not set — this is one disk"
    fi
    echo
    exit 0
    ;;
  --install)
    PLIST="$HOME/Library/LaunchAgents/com.oormanisuddi.backup.plist"
    mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
    cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.oormanisuddi.backup</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$ROOT/scripts/backup.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>22</integer><key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>$ROOT/logs/backup.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/backup.err.log</string>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
PLISTEOF
    launchctl unload "$PLIST" 2>/dev/null
    launchctl load "$PLIST" && echo "✓ nightly backup installed (22:30)" || exit 1
    echo "  Set an external destination so this is a real backup:"
    echo "    export OORMANI_BACKUP_DIR=/Volumes/<drive>/OormaniSuddi"
    exit 0
    ;;
esac

mkdir -p "$LOCAL" "$ROOT/logs"
ARCHIVE="$LOCAL/oormani-$STAMP.tar.gz"

echo "$(date '+%Y-%m-%d %H:%M:%S')  backup"

# ── 1 · the irreplaceable things ─────────────────────────────────────────────
# editions/ is in git too, but it costs almost nothing here and a backup that
# needs git to be intact is not a backup.
TARGETS=()
for d in archive editions assets/stock assets/bgm_options assets/LICENCES.json \
         assets/pronunciation.json fonts; do
  [ -e "$ROOT/$d" ] && TARGETS+=("$d")
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "  nothing to back up yet"
  exit 0
fi

tar -czf "$ARCHIVE" "${TARGETS[@]}" 2>/dev/null
SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "  local     $ARCHIVE  ($SIZE)"

# Keep the last KEEP days locally; the external copy keeps everything.
ls -t "$LOCAL"/oormani-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f

# ── 2 · the second medium ────────────────────────────────────────────────────
if [ -n "$EXTERNAL" ] && [ -d "$EXTERNAL" ]; then
  mkdir -p "$EXTERNAL"
  cp "$ARCHIVE" "$EXTERNAL/" && echo "  external  $EXTERNAL"
  EXT_OK=1
else
  EXT_OK=0
  [ -n "$EXTERNAL" ] && echo "  external  ⚠️  $EXTERNAL not mounted" \
                     || echo "  external  ⚠️  OORMANI_BACKUP_DIR not set"
fi

# ── 3 · offsite ──────────────────────────────────────────────────────────────
# Code only. The published record is not pushed to a remote by this script —
# that is a decision about where the channel's evidence lives, and it should be
# made deliberately rather than by a backup job.
AHEAD="$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '?')"
if [ "$AHEAD" = "0" ]; then
  echo "  offsite   git up to date"
  GIT_OK=1
elif [ "$AHEAD" = "?" ]; then
  echo "  offsite   ⚠️  no upstream branch set"
  GIT_OK=0
else
  echo "  offsite   ⚠️  $AHEAD commit(s) unpushed — run: git push"
  GIT_OK=0
fi

if [ "$EXT_OK" = "1" ] && [ "$GIT_OK" = "1" ]; then
  echo "  ✓ three copies, two media, one offsite"
else
  echo "  ! this is fewer than three copies. See --status."
  notify "Backup incomplete" "Local copy written. See scripts/backup.sh --status"
fi
