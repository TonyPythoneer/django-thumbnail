#!/bin/bash
set -euo pipefail

python3() { uv run python3 "$@"; }

BASE_URL="${BASE_URL:-http://localhost:8000}"
USERNAME="${USERNAME:-test1@example.com}"
PASSWORD="${PASSWORD:-test1}"
POLL_MAX=20
POLL_INTERVAL=2

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; echo -e "${RED}[HINT]${NC} Is the stack running? Try: make up-app && make logs-app"; exit 1; }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

COOKIE_JAR=$(mktemp)
TEST_IMAGE=$(mktemp)_smoke.jpg
trap 'rm -f "$COOKIE_JAR" "$TEST_IMAGE"' EXIT

# --- 1. login ---
info "Login as $USERNAME"
LOGIN_RESP=$(curl -s -c "$COOKIE_JAR" -X POST "$BASE_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

echo "$LOGIN_RESP" | grep -q '"user"' || fail "Login failed: $LOGIN_RESP"
pass "Login"

CSRF_TOKEN=$(grep csrftoken "$COOKIE_JAR" | awk '{print $NF}')

# --- 2. create image record → get presigned upload URL ---
info "Create image record"
CREATE_RESP=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "$BASE_URL/api/images/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"filename": "smoke_test.jpg"}')

IMAGE_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['image_id'])" 2>/dev/null) \
  || fail "Create image failed: $CREATE_RESP"
UPLOAD_URL=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['upload_url'])" 2>/dev/null)

pass "Image record created (id=$IMAGE_ID)"

# --- 3. upload file to presigned URL ---
info "Upload file to MinIO presigned URL"
# generate minimal valid JPEG (1x1 red pixel)
python3 -c "
from PIL import Image as PILImage
img = PILImage.new('RGB', (800, 600), color=(70, 130, 180))
img.save('$TEST_IMAGE', format='JPEG')
"

UPLOAD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$UPLOAD_URL" \
  --data-binary "@$TEST_IMAGE")

[[ "$UPLOAD_STATUS" =~ ^(200|204)$ ]] || fail "Upload to MinIO failed (HTTP $UPLOAD_STATUS)"
pass "File uploaded to MinIO"

# --- 4. trigger thumbnail task ---
info "Trigger thumbnail task"
TASK_RESP=$(curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "$BASE_URL/api/tasks/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d "{\"image_id\": \"$IMAGE_ID\"}")

TASK_ID=$(echo "$TASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null) \
  || fail "Create task failed: $TASK_RESP"
pass "Task created (id=$TASK_ID)"

# --- 5. poll task status ---
info "Polling task status (max ${POLL_MAX}x every ${POLL_INTERVAL}s)"
for i in $(seq 1 "$POLL_MAX"); do
  STATUS_RESP=$(curl -s -b "$COOKIE_JAR" "$BASE_URL/api/tasks/$TASK_ID/")
  STATUS=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null) || STATUS="unknown"
  info "  attempt $i: status=$STATUS"
  if [[ "$STATUS" == "done" ]]; then
    pass "Thumbnail generated (status=done)"
    break
  elif [[ "$STATUS" == "failed" ]]; then
    fail "Task failed: $STATUS_RESP"
  fi
  sleep "$POLL_INTERVAL"
done

[[ "$STATUS" == "done" ]] || fail "Timed out waiting for task (last status=$STATUS)"

echo ""
pass "Smoke test complete. Check Jaeger at http://localhost:16686"
