#!/usr/bin/env bash
# WIN OS preflight: refuse unsupported or unsafe production configurations.
set -euo pipefail
fail() { echo "PREFLIGHT FAIL: $*" >&2; exit 1; }
[ -r /etc/os-release ] || fail "cannot detect operating system"
. /etc/os-release
case "${ID:-}" in ubuntu) ;; *) fail "WIN OS targets Ubuntu Server LTS (detected: ${ID:-unknown})";; esac
case "${VERSION_ID:-}" in 24.04|22.04) echo "OS: Ubuntu $VERSION_ID LTS - supported";; *) fail "unsupported Ubuntu version ${VERSION_ID:-unknown}; supported: 24.04 LTS (primary), 22.04 LTS";; esac
command -v docker >/dev/null || fail "docker is not installed; run the Ansible win_docker role first"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is not installed"
[ -f .env ] || fail ".env is missing; cp win-os/.env.example .env and fill in real values"
grep -q "change-me" .env && fail ".env still contains placeholder secrets"
df -BG --output=avail . | tail -1 | tr -dc '0-9' | awk '{ if ($1 < 10) exit 1 }' || fail "less than 10G free disk"
echo "PREFLIGHT OK"
