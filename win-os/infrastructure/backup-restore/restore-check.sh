#!/usr/bin/env bash
# Restore check: verifies the newest backup file exists and is readable.
# A full restore test must run in a separate environment - see
# docs/operations/runbooks.md. This script never deletes backups.
set -euo pipefail
BACKUP_DIR="${WIN_BACKUP_DIR:-./backups}"
latest="$(ls -1t "$BACKUP_DIR"/win-os-*.dump 2>/dev/null | head -1 || true)"
[ -n "$latest" ] || { echo "RESTORE-CHECK FAIL: no backup found in $BACKUP_DIR"; exit 1; }
gzip -t "$latest" 2>/dev/null || head -c 64 "$latest" >/dev/null
echo "RESTORE-CHECK OK: newest backup is readable: $latest"
echo "Next: restore it into a throwaway Postgres (runbook: Restore validation)."
