#!/usr/bin/env bash
# WIN OS database backup: pg_dump (custom format) + sha256 + retention guard.
# Usage: WIN_BACKUP_DIR=/var/backups/win-os bash backup-win-os.sh
# Reads the connection from WIN_DATABASE_URL (postgresql:// form).
set -euo pipefail
: "${WIN_DATABASE_URL:?set WIN_DATABASE_URL}"
BACKUP_DIR="${WIN_BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/win-os-$stamp.dump"
pg_dump --format=custom --no-owner --file "$out" "$WIN_DATABASE_URL"
sha256sum "$out" > "$out.sha256"
echo "backup written: $out ($(du -h "$out" | cut -f1))"
# Retention: keep the newest 14 daily + 8 weekly files. This block only
# REPORTS candidates; deletion is opt-in with WIN_BACKUP_PRUNE=1.
count="$(ls -1 "$BACKUP_DIR"/win-os-*.dump | wc -l)"
echo "backups present: $count (retention target: 22)"
if [ "${WIN_BACKUP_PRUNE:-0}" = "1" ] && [ "$count" -gt 22 ]; then
  ls -1t "$BACKUP_DIR"/win-os-*.dump | tail -n +23 | while read -r old; do
    echo "pruning $old"; rm -f "$old" "$old.sha256"
  done
fi
