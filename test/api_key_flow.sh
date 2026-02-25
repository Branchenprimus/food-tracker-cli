#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8686"
API_KEY=""
KEEP_ENTRY=0
CREATED_ENTRY_ID=""
TMP_DIR=""

usage() {
  cat <<USAGE
Usage: $0 --key <API_KEY> [--base-url <URL>] [--keep-entry]

Integration test for API key auth flow.

Options:
  --key <API_KEY>      Required app-generated API key (ftk_...)
  --base-url <URL>     API base URL (default: http://localhost:8686)
  --keep-entry         Keep test entry instead of deleting it
  -h, --help           Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --key)
      API_KEY="${2:-}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --keep-entry)
      KEEP_ENTRY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$API_KEY" ]]; then
  echo "Error: --key is required" >&2
  usage
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"

cleanup() {
  if [[ -n "$CREATED_ENTRY_ID" && "$KEEP_ENTRY" -eq 0 ]]; then
    curl -sS -X DELETE "$BASE_URL/api/entries/$CREATED_ENTRY_ID" \
      -H "X-API-Key: $API_KEY" >/dev/null || true
  fi
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

expect_status() {
  local got="$1"
  local expected="$2"
  local label="$3"
  if [[ "$got" != "$expected" ]]; then
    echo "FAIL: $label (expected $expected, got $got)" >&2
    return 1
  fi
  echo "PASS: $label ($got)"
}

request() {
  local method="$1"
  local path="$2"
  local out_file="$3"
  local key_header="$4"
  local data="${5:-}"

  if [[ -n "$data" ]]; then
    curl -sS -o "$out_file" -w "%{http_code}" -X "$method" \
      "$BASE_URL$path" \
      -H "Content-Type: application/json" \
      -H "$key_header" \
      -d "$data"
  else
    curl -sS -o "$out_file" -w "%{http_code}" -X "$method" \
      "$BASE_URL$path" \
      -H "$key_header"
  fi
}

echo "Running API key auth integration test against: $BASE_URL"

# 1) Invalid key should be rejected
STATUS_INVALID=$(request GET "/api/me" "$TMP_DIR/invalid.json" "X-API-Key: invalid_key")
expect_status "$STATUS_INVALID" "403" "invalid key rejected on /api/me"

# 2) Valid key should be accepted
STATUS_VALID=$(request GET "/api/me" "$TMP_DIR/me.json" "X-API-Key: $API_KEY")
expect_status "$STATUS_VALID" "200" "valid key accepted on /api/me"

USER_EMAIL=$(python3 - "$TMP_DIR/me.json" <<'PY'
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('email', ''))
PY
)
if [[ -z "$USER_EMAIL" ]]; then
  echo "FAIL: /api/me response missing email" >&2
  exit 1
fi
echo "INFO: authenticated user = $USER_EMAIL"

# 3) Create entry with valid key should succeed
ENTRY_PAYLOAD=$(python3 - <<'PY'
from datetime import datetime
now = datetime.now()
print('{"title":"api-key-flow-test","kcal":321,"fat_g":11,"carbs_g":22,"protein_g":33,"serving_amount":1,"confidence":0.9,"entry_date":"%s","entry_time":"%s"}' % (now.strftime('%Y-%m-%d'), now.strftime('%H:%M')))
PY
)
STATUS_CREATE=$(request POST "/api/entries" "$TMP_DIR/create.json" "X-API-Key: $API_KEY" "$ENTRY_PAYLOAD")
expect_status "$STATUS_CREATE" "200" "create entry with valid key"

CREATED_ENTRY_ID=$(python3 - "$TMP_DIR/create.json" <<'PY'
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('id', ''))
PY
)
if [[ -z "$CREATED_ENTRY_ID" || "$CREATED_ENTRY_ID" == "None" ]]; then
  echo "FAIL: create response missing id" >&2
  exit 1
fi
echo "INFO: created entry id = $CREATED_ENTRY_ID"

# 4) Invalid key on write endpoint should be rejected
STATUS_WRITE_INVALID=$(request POST "/api/entries" "$TMP_DIR/create_invalid.json" "X-API-Key: invalid_key" "$ENTRY_PAYLOAD")
expect_status "$STATUS_WRITE_INVALID" "403" "invalid key rejected on /api/entries"

# 5) Probe no-key behavior (environment dependent)
STATUS_NO_KEY=$(curl -sS -o "$TMP_DIR/nokey.json" -w "%{http_code}" "$BASE_URL/api/me")
if [[ "$STATUS_NO_KEY" == "200" ]]; then
  echo "INFO: no-key /api/me succeeded (dev fallback identity enabled)"
elif [[ "$STATUS_NO_KEY" == "401" ]]; then
  echo "INFO: no-key /api/me rejected (strict/cloudflare mode)"
else
  echo "WARN: unexpected no-key status on /api/me: $STATUS_NO_KEY"
fi

if [[ "$KEEP_ENTRY" -eq 1 ]]; then
  echo "INFO: --keep-entry set, leaving test entry id $CREATED_ENTRY_ID"
else
  STATUS_DELETE=$(request DELETE "/api/entries/$CREATED_ENTRY_ID" "$TMP_DIR/delete.json" "X-API-Key: $API_KEY")
  expect_status "$STATUS_DELETE" "200" "cleanup delete test entry"
  CREATED_ENTRY_ID=""
fi

echo "All key-auth integration checks passed."
