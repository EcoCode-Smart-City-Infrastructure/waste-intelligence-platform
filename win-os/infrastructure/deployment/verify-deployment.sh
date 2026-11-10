#!/usr/bin/env bash
# WIN OS deployment verification: run against a deployed API.
# Usage: WIN_API_URL=https://win.example.org WIN_API_KEY_OPERATOR=... \
#        WIN_API_KEY_VIEWER=... bash verify-deployment.sh
set -u
BASE="${WIN_API_URL:-http://127.0.0.1:8080}"
pass=0; fail=0
check() { # name expected actual
  if [ "$2" = "$3" ]; then echo "PASS $1"; pass=$((pass+1));
  else echo "FAIL $1 (expected $2, got $3)"; fail=$((fail+1)); fi
}
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
check "health live" 200 "$(code "$BASE/health/live")"
check "health ready" 200 "$(code "$BASE/health/ready")"
check "unauthenticated is 401" 401 "$(code "$BASE/api/v1/assets")"
check "viewer can read assets" 200 "$(code -H "X-API-Key: $WIN_API_KEY_VIEWER" "$BASE/api/v1/assets")"
check "viewer cannot write" 403 "$(code -X POST -H "X-API-Key: $WIN_API_KEY_VIEWER" -H 'Content-Type: application/json' -d '{"name":"verify"}' "$BASE/api/v1/assets")"
body="$(curl -s -X POST -H "X-API-Key: $WIN_API_KEY_OPERATOR" -H 'Content-Type: application/json' -d '{"name":"verify-deployment bin","data_status":"reported"}' "$BASE/api/v1/assets")"
echo "$body" | grep -q '"id"' && check "operator creates asset" ok ok || check "operator creates asset" ok fail
echo "verify-deployment: $pass passed, $fail failed"
[ "$fail" = "0" ]
