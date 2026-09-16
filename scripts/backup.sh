#!/bin/bash
# ಊರ್ಮನಿ ಸುದ್ದಿ — three copies, two media, one offsite.
#
#   bash scripts/backup.sh              back up now
#   bash scripts/backup.sh --status     when did each copy last happen
#   bash scripts/backup.sh --install    run it nightly at 22:30 via launchd
#
# Git covers everything it can: the code, the fonts, the stock library, the
# licensed beds, the editions. Pushing is the offsite copy of all of that.
#
# This script covers the ONE thing git deliberately does not:
#
#   archive/    the published record — every edition as it went out, its
#               APPROVAL.md and SIGNOFF.json, the copy, the corrections ledger,
#               the metrics database, the calendar state. If a complaint
#               arrives in March about something published in November, this is
#               the only evidence that exists, and under IT Rules 2021 that is
#               not a thing to shrug at.
#
# The default backup is therefore SMALL — archive/ and the couple of registers
# that live outside it. That matters: an earlier version tarred 80 MB every
# night, 79 MB of which was already on GitHub, onto a disk that is 90% full.
#
#   --full   everything, including assets/ and fonts/ — a bare-metal restore
#            image for a new machine. Run it to an external drive when you have
#            one, not nightly.
#
# NOT backed up, on purpose: .env and .gemini_key. Putting live API keys in a
# tarball that syncs to a cloud folder trades a small risk for a larger one,
# and both keys can be reissued from the Google Cloud console in two minutes.
# Losing them costs a morning; leaking them costs more.
#
# Deliberately dumb: tar and cp. Nothing to keep alive, no account, no service.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

LOCAL="$ROOT/.backups"
STAMP="$(date +%Y-%m-%d)"
KEEP=14                    # daily archives to retain locally

# Where the second copy goes.
#
# An explicit OORMANI_BACKUP_DIR always wins — that is how you point this at an
# external drive. With nothing set, it falls back to iCloud Drive if the folder
# exists, because a backup that depends on somebody having exported a variable
# in the right shell is a backup that silently stops the day they open a new
# terminal. launchd does not read a shell profile at all, so the nightly job
# would have been the first thing to lose it.
ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs/OormaniSuddi"
EXTERNAL="${OORMANI_BACKUP_DIR:-}"
EXTERNAL_IS_ICLOUD=0
if [ -z "$EXTERNAL" ] && [ -d "$(dirname "$ICLOUD")" ]; then
  EXTERNAL="$ICLOUD"
  EXTERNAL_IS_ICLOUD=1
  mkdir -p "$EXTERNAL" 2>/dev/null
fi

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
    if [ -n "$EXTERNAL" ] && [ -d "$EXTERNAL" ]; then
      LASTX="$(ls -t "$EXTERNAL"/oormani-*.tar.gz 2>/dev/null | head -1)"
      WHICH="$([ "$EXTERNAL_IS_ICLOUD" = "1" ] && echo 'iCloud Drive (default)' || echo "$EXTERNAL")"
      echo "  second      $WHICH"
      [ -n "$LASTX" ] && echo "              $(basename "$LASTX")" \
                      || echo "              ⚠️  never run"
      if [ "$EXTERNAL_IS_ICLOUD" = "1" ]; then
        echo "              ↳ a real external drive is better. Plug one in and:"
        echo "                export OORMANI_BACKUP_DIR=/Volumes/<drive>/OormaniSuddi"
        echo "                bash scripts/backup.sh --full"
      fi
    elif [ -n "$EXTERNAL" ]; then
      echo "  second      ⚠️  $EXTERNAL is not mounted"
    else
      echo "  second      ⚠️  nowhere set and no iCloud — this is one disk"
    fi
    FULLX="$(ls -t "$LOCAL"/oormani-full-*.tar.gz 2>/dev/null | head -1)"
    [ -n "$FULLX" ] && echo "  full image  $(basename "$FULLX")" \
                    || echo "  full image  ⚠️  never run — 'bash scripts/backup.sh --full'"
    echo
    echo "  git holds the code, fonts, stock and beds. This holds archive/ —"
    echo "  the published record, which git deliberately does not carry."
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
  <key>EnvironmentVariables</key><dict>
    <key>OORMANI_BACKUP_DIR</key><string>$EXTERNAL</string>
  </dict>
  <key>StandardOutPath</key><string>$ROOT/logs/backup.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/backup.err.log</string>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
PLISTEOF
    launchctl unload "$PLIST" 2>/dev/null
    launchctl load "$PLIST" || exit 1
    echo "✓ nightly backup installed (22:30)"
    echo "  second copy → $EXTERNAL"
    [ "$EXTERNAL_IS_ICLOUD" = "1" ] && \
      echo "  (iCloud Drive, the default. An external drive is better — plug one in, set OORMANI_BACKUP_DIR, and re-run --install.)"
    exit 0
    ;;
esac

mkdir -p "$LOCAL" "$ROOT/logs"

FULL=0
[ "${1:-}" = "--full" ] && FULL=1

if [ "$FULL" = "1" ]; then
  ARCHIVE="$LOCAL/oormani-full-$STAMP.tar.gz"
  KIND="full"
  # Everything needed to rebuild on a machine that has never seen this repo,
  # for the case where GitHub is also unreachable.
  CANDIDATES=(archive editions assets/stock assets/bgm_options
              assets/LICENCES.json assets/pronunciation.json fonts
              brand templates scripts docs tests render.py requirements.txt
              AGENTS.md CLAUDE.md STANDARDS.md)
else
  ARCHIVE="$LOCAL/oormani-$STAMP.tar.gz"
  KIND="daily"
  # Only what git does not have. Everything else is one `git clone` away.
  CANDIDATES=(archive editions/greetings/calendar.json)
fi

echo "$(date '+%Y-%m-%d %H:%M:%S')  backup ($KIND)"

TARGETS=()
for d in "${CANDIDATES[@]}"; do
  [ -e "$ROOT/$d" ] && TARGETS+=("$d")
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "  nothing to back up yet — archive/ is empty until an edition is archived"
  exit 0
fi

tar -czf "$ARCHIVE" "${TARGETS[@]}" 2>/dev/null
SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "  local     $ARCHIVE  ($SIZE)"
if [ "$FULL" = "0" ]; then
  echo "            (archive/ only — the code, fonts, stock and beds are in git)"
fi

# Prune each kind separately — a full image should outlive a fortnight of
# dailies, and mixing them meant one --full run evicted two weeks of record.
ls -t "$LOCAL"/oormani-2*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
ls -t "$LOCAL"/oormani-full-*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f

# ── 2 · the second medium ────────────────────────────────────────────────────
if [ -n "$EXTERNAL" ] && [ -d "$EXTERNAL" ]; then
  mkdir -p "$EXTERNAL"
  if cp "$ARCHIVE" "$EXTERNAL/"; then
    [ "$EXTERNAL_IS_ICLOUD" = "1" ] && echo "  second    iCloud Drive" \
                                    || echo "  second    $EXTERNAL"
    EXT_OK=1
  else
    echo "  second    ⚠️  could not write to $EXTERNAL"
    EXT_OK=0
  fi
else
  EXT_OK=0
  [ -n "$EXTERNAL" ] && echo "  second    ⚠️  $EXTERNAL not mounted" \
                     || echo "  second    ⚠️  nowhere to put a second copy"
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
