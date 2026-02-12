#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/booking_confirm_verify.sh [options]

Options:
  --client-slug <slug>        Default: demo_salon
  --branch-slug <slug>        Default: branch_b
  --base-url <url>            Default: http://localhost:8000
  --jid-commit <jid>          Remote JID for CA05 booking-commit
  --jid-full <jid>            Remote JID for CA12 booking-full
  --instance-id <id>          Override instance_id (must match branch.instance_id)
  --apply                      Enable DB mutations (booking_settings + calendar setup)
  --cancel-appointments        Cancel active appointments for JIDs (requires --apply)
  --no-livecheck               Skip CA05/CA12 live-checks
  --evidence-dir <path>        Evidence output directory (default: /tmp/booking-confirm-<stamp>)
  --api-container <name>       Default: truffles-api
  --db-container <name>        Default: truffles_postgres_1
  --db-user <user>             Default: POSTGRES_USER from DB container
  --db-name <name>             Default: parsed from DATABASE_URL or chatbot
  --livecheck-timeout <sec>    Default: 25
  --livecheck-poll-timeout <sec> Default: 30
  -h, --help                   Show help

Notes:
  - DB writes require --apply. For non-local base-url, set ALLOW_NON_LOCAL=1.
  - Livecheck requires TEST_MODE=1 and allowlist JIDs in truffles-api env.
EOF
}

info() { echo "[info] $*"; }
die() { echo "[error] $*" >&2; exit 1; }

sql_escape() {
  printf "%s" "$1" | sed "s/'/''/g"
}

normalize_digits() {
  printf "%s" "$1" | tr -cd '0-9'
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

CLIENT_SLUG="demo_salon"
BRANCH_SLUG="branch_b"
BASE_URL="http://localhost:8000"
API_CONTAINER="truffles-api"
DB_CONTAINER="truffles_postgres_1"
DB_USER=""
DB_NAME=""
INSTANCE_ID=""
JID_COMMIT=""
JID_FULL=""
LIVECHECK_TIMEOUT="25"
LIVECHECK_POLL_TIMEOUT="30"
APPLY=0
CANCEL_APPOINTMENTS=0
NO_LIVECHECK=0
EVIDENCE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-slug) CLIENT_SLUG="$2"; shift 2;;
    --branch-slug) BRANCH_SLUG="$2"; shift 2;;
    --base-url) BASE_URL="$2"; shift 2;;
    --jid-commit) JID_COMMIT="$2"; shift 2;;
    --jid-full) JID_FULL="$2"; shift 2;;
    --instance-id) INSTANCE_ID="$2"; shift 2;;
    --apply) APPLY=1; shift;;
    --cancel-appointments) CANCEL_APPOINTMENTS=1; shift;;
    --no-livecheck) NO_LIVECHECK=1; shift;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2;;
    --api-container) API_CONTAINER="$2"; shift 2;;
    --db-container) DB_CONTAINER="$2"; shift 2;;
    --db-user) DB_USER="$2"; shift 2;;
    --db-name) DB_NAME="$2"; shift 2;;
    --livecheck-timeout) LIVECHECK_TIMEOUT="$2"; shift 2;;
    --livecheck-poll-timeout) LIVECHECK_POLL_TIMEOUT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) die "Unknown arg: $1";;
  esac
done

require_cmd docker
require_cmd python3
require_cmd curl

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ "$CANCEL_APPOINTMENTS" -eq 1 && "$APPLY" -ne 1 ]]; then
  die "--cancel-appointments requires --apply"
fi

if [[ "$APPLY" -eq 1 && "$BASE_URL" != http://localhost* && "${ALLOW_NON_LOCAL:-0}" != "1" ]]; then
  die "Refusing --apply for non-local base-url. Set ALLOW_NON_LOCAL=1 to override."
fi

if [[ -z "$DB_USER" ]]; then
  DB_USER="$(docker exec "$DB_CONTAINER" /bin/sh -lc 'printf "%s" "${POSTGRES_USER:-}"' || true)"
fi
DB_USER="${DB_USER:-postgres}"

if [[ -z "$DB_NAME" ]]; then
  db_url="$(docker exec "$API_CONTAINER" /bin/sh -lc 'printf "%s" "${DATABASE_URL:-}"' || true)"
  if [[ -n "$db_url" ]]; then
    DB_NAME="$(DB_URL="$db_url" python3 - <<'PY' || true
import os
from urllib.parse import urlparse
url = os.environ.get("DB_URL", "")
if url:
    parsed = urlparse(url)
    name = (parsed.path or "").lstrip("/")
    if name:
        print(name)
PY
)"
  fi
fi
DB_NAME="${DB_NAME:-chatbot}"

psql_scalar() {
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -t -A -F $'\t' -c "$1"
}

psql_exec() {
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "$1"
}

psql_to_file() {
  local file="$1"
  local sql="$2"
  psql_exec "$sql" | tee "$file"
}

STAMP="$(date -u +%Y%m%d-%H%M%S)"
if [[ -z "$EVIDENCE_DIR" ]]; then
  EVIDENCE_DIR="/tmp/booking-confirm-${STAMP}"
fi
mkdir -p "$EVIDENCE_DIR"

info "Evidence dir: $EVIDENCE_DIR"
{
  echo "client_slug=${CLIENT_SLUG}"
  echo "branch_slug=${BRANCH_SLUG}"
  echo "base_url=${BASE_URL}"
  echo "api_container=${API_CONTAINER}"
  echo "db_container=${DB_CONTAINER}"
  echo "db_user=${DB_USER}"
  echo "db_name=${DB_NAME}"
  echo "apply=${APPLY}"
  echo "cancel_appointments=${CANCEL_APPOINTMENTS}"
} > "${EVIDENCE_DIR}/run_context.txt"

curl -s "${BASE_URL}/admin/health" | tee "${EVIDENCE_DIR}/admin_health.json" >/dev/null

branch_row="$(psql_scalar "select id, client_id, instance_id, timezone, phone from branches where slug='$(sql_escape "$BRANCH_SLUG")' and is_active = true order by updated_at desc nulls last, created_at desc nulls last limit 1;")"
if [[ -z "$branch_row" ]]; then
  die "Branch not found: ${BRANCH_SLUG}"
fi
branch_id="$(echo "$branch_row" | cut -f1)"
client_id="$(echo "$branch_row" | cut -f2)"
branch_instance_id="$(echo "$branch_row" | cut -f3)"
branch_tz="$(echo "$branch_row" | cut -f4)"
branch_phone="$(echo "$branch_row" | cut -f5)"

{
  echo "branch_id=${branch_id}"
  echo "client_id=${client_id}"
  echo "branch_instance_id=${branch_instance_id}"
  echo "branch_timezone=${branch_tz}"
  echo "branch_phone=${branch_phone}"
} | tee "${EVIDENCE_DIR}/branch_meta.txt" >/dev/null

if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID="$branch_instance_id"
fi
if [[ -n "$branch_instance_id" && "$INSTANCE_ID" != "$branch_instance_id" ]]; then
  die "instance_id mismatch (payload ${INSTANCE_ID} vs branch ${branch_instance_id})"
fi

allowlist="$(docker exec "$API_CONTAINER" /bin/sh -lc 'printf "%s" "${OUTBOUND_ALLOWLIST_JIDS:-}"' || true)"
if [[ -z "$allowlist" ]]; then
  die "OUTBOUND_ALLOWLIST_JIDS is empty in ${API_CONTAINER}"
fi
IFS=',' read -r -a allowlist_arr <<< "$allowlist"

blocked_digits_raw="$(psql_scalar "select regexp_replace(phone, '\\\\D', '', 'g') from branches where phone is not null;")"
mapfile -t blocked_digits_arr <<< "$blocked_digits_raw"

jid_is_blocked() {
  local jid="$1"
  local digits
  digits="$(normalize_digits "$jid")"
  if [[ -z "$digits" ]]; then
    return 0
  fi
  for blocked in "${blocked_digits_arr[@]}"; do
    local blocked_digits
    blocked_digits="$(normalize_digits "$blocked")"
    if [[ -n "$blocked_digits" && "$digits" == "$blocked_digits" ]]; then
      return 0
    fi
  done
  return 1
}

jid_is_preferred_test() {
  local jid="$1"
  local digits
  digits="$(normalize_digits "$jid")"
  [[ "$digits" =~ ^7700000000[0-9]+$ ]]
}

if [[ -z "$JID_COMMIT" ]]; then
  for prefer_test in 1 0; do
    for jid in "${allowlist_arr[@]}"; do
      jid="${jid//[[:space:]]/}"
      if [[ -z "$jid" ]] || jid_is_blocked "$jid"; then
        continue
      fi
      if [[ "$prefer_test" -eq 1 ]] && ! jid_is_preferred_test "$jid"; then
        continue
      fi
      JID_COMMIT="$jid"
      break
    done
    if [[ -n "$JID_COMMIT" ]]; then
      break
    fi
  done
else
  if jid_is_blocked "$JID_COMMIT"; then
    die "jid_commit is a branch number; choose a non-branch allowlist JID"
  fi
fi
if [[ -z "$JID_COMMIT" ]]; then
  die "No safe allowlist JID found for jid_commit"
fi
if [[ -z "$JID_FULL" ]]; then
  for prefer_test in 1 0; do
    for jid in "${allowlist_arr[@]}"; do
      jid="${jid//[[:space:]]/}"
      if [[ -z "$jid" ]] || [[ "$jid" == "$JID_COMMIT" ]] || jid_is_blocked "$jid"; then
        continue
      fi
      if [[ "$prefer_test" -eq 1 ]] && ! jid_is_preferred_test "$jid"; then
        continue
      fi
      JID_FULL="$jid"
      break
    done
    if [[ -n "$JID_FULL" ]]; then
      break
    fi
  done
  if [[ -z "$JID_FULL" ]]; then
    JID_FULL="$JID_COMMIT"
    info "Only one safe allowlist JID found; using it for CA12 as well."
  fi
else
  if jid_is_blocked "$JID_FULL"; then
    die "jid_full is a branch number; choose a non-branch allowlist JID"
  fi
fi
{
  echo "jid_commit=${JID_COMMIT}"
  echo "jid_full=${JID_FULL}"
} | tee "${EVIDENCE_DIR}/jids.txt" >/dev/null

if [[ "$NO_LIVECHECK" -eq 0 ]]; then
  test_mode="$(docker exec "$API_CONTAINER" /bin/sh -lc 'printf "%s" "${TEST_MODE:-}"' || true)"
  if [[ "$test_mode" != "1" && "$test_mode" != "true" ]]; then
    die "TEST_MODE not enabled in ${API_CONTAINER}"
  fi
  admin_token="$(docker exec "$API_CONTAINER" /bin/sh -lc 'printf "%s" "${ALERTS_ADMIN_TOKEN:-}"' || true)"
  if [[ -z "$admin_token" ]]; then
    die "ALERTS_ADMIN_TOKEN missing in ${API_CONTAINER}"
  fi
fi

if [[ "$APPLY" -eq 1 ]]; then
  apply_sql="$(cat <<SQL
UPDATE branches
SET booking_settings = '{"booking_mode":"confirm_slots","slot_duration_min":60,"confirmation_policy":"client","default_duration_min":60,"availability_provider":"google_calendar"}'::jsonb
WHERE id = '${branch_id}';

INSERT INTO calendar_connections (client_id, branch_id, provider, calendar_id, status, created_at, updated_at)
VALUES ('${client_id}', '${branch_id}', 'google_calendar', 'primary', 'ACTIVE', now(), now())
ON CONFLICT (branch_id, provider)
DO UPDATE SET calendar_id = EXCLUDED.calendar_id, status = 'ACTIVE', updated_at = now();

INSERT INTO google_calendar_tokens (client_id, branch_id, access_token, refresh_token, token_type, expires_at, encryption_version, created_at, updated_at)
VALUES ('${client_id}', '${branch_id}', 'test_access_token', 'test_refresh_token', 'Bearer', now() + interval '30 days', 0, now(), now())
ON CONFLICT (client_id, branch_id)
DO UPDATE SET access_token = EXCLUDED.access_token,
              refresh_token = EXCLUDED.refresh_token,
              token_type = 'Bearer',
              expires_at = EXCLUDED.expires_at,
              encryption_version = 0,
              updated_at = now();

INSERT INTO calendar_sync_cursors (connection_id, cursor, last_synced_at, created_at, updated_at)
SELECT cc.id, 'seed', now(), now(), now()
FROM calendar_connections cc
WHERE cc.branch_id = '${branch_id}'
  AND cc.provider = 'google_calendar'
  AND NOT EXISTS (
    SELECT 1 FROM calendar_sync_cursors c WHERE c.connection_id = cc.id
  );

UPDATE calendar_sync_cursors
SET cursor = 'seed',
    last_synced_at = now(),
    updated_at = now()
WHERE connection_id IN (
  SELECT id FROM calendar_connections WHERE branch_id = '${branch_id}' AND provider = 'google_calendar'
);
SQL
)"
  psql_exec "$apply_sql" | tee "${EVIDENCE_DIR}/apply_sql.txt"
else
  info "Apply disabled; skipping booking_settings/calendar setup."
fi

if [[ "$CANCEL_APPOINTMENTS" -eq 1 ]]; then
  jids_sql=""
  for jid in "$JID_COMMIT" "$JID_FULL"; do
    if [[ -n "$jid" ]]; then
      escaped="$(sql_escape "$jid")"
      if [[ -n "$jids_sql" ]]; then
        jids_sql+=", "
      fi
      jids_sql+="'${escaped}'"
    fi
  done
  if [[ -z "$jids_sql" ]]; then
    die "No JIDs available for cancellation."
  fi
  mapfile -t appointment_ids < <(psql_scalar "select a.id from appointments a join conversations c on c.id=a.conversation_id join users u on u.id=c.user_id where c.branch_id='${branch_id}' and u.remote_jid in (${jids_sql}) and a.status in ('HOLD','PENDING_CONFIRMATION','CONFIRMED','RESCHEDULE_REQUESTED','CHECKED_IN');")
  if [[ "${#appointment_ids[@]}" -gt 0 ]]; then
    APPOINTMENT_IDS="$(IFS=,; echo "${appointment_ids[*]}")"
    docker exec -i "$API_CONTAINER" env CLIENT_ID="${client_id}" APPOINTMENT_IDS="${APPOINTMENT_IDS}" python3 - <<'PY' | tee "${EVIDENCE_DIR}/appointments_cancelled.txt"
from uuid import UUID
import os

from app.database import SessionLocal
from app.models.appointment_service import AppointmentService
from app.models.service import Service
from app.services.appointment_service import SchedulingService

client_id = UUID(os.environ["CLIENT_ID"])
ids = [UUID(value) for value in os.environ.get("APPOINTMENT_IDS", "").split(",") if value]

db = SessionLocal()
try:
    service = SchedulingService(db)
    for appointment_id in ids:
        appointment = service.cancel_appointment(
            appointment_id=appointment_id,
            client_id=client_id,
            reason="booking_confirm_verify_reset",
        )
        print(f"{appointment.id} status={appointment.status}")
finally:
    db.close()
PY
  else
    info "No active appointments found for allowlist JIDs."
  fi
fi

docker exec -i "$API_CONTAINER" env CLIENT_ID="${client_id}" BRANCH_ID="${branch_id}" python3 - <<'PY' | tee "${EVIDENCE_DIR}/provider_health.txt"
from uuid import UUID
import os

from app.database import SessionLocal
from app.models.appointment_service import AppointmentService
from app.models.service import Service
from app.services.calendar_sync_service import get_provider_health

client_id = UUID(os.environ["CLIENT_ID"])
branch_id = UUID(os.environ["BRANCH_ID"])

db = SessionLocal()
try:
    health = get_provider_health(db, client_id=client_id, branch_id=branch_id)
    print(health)
finally:
    db.close()
PY

if [[ "$NO_LIVECHECK" -eq 0 ]]; then
  TEST_MODE=1 INSTANCE_ID="$INSTANCE_ID" python3 ops/diagnose.py livecheck-auto \
    --suite ca05-booking-commit \
    --client-slug "$CLIENT_SLUG" \
    --branch-slug "$BRANCH_SLUG" \
    --base-url "$BASE_URL" \
    --noise none \
    --timeout "$LIVECHECK_TIMEOUT" \
    --poll-timeout "$LIVECHECK_POLL_TIMEOUT" \
    --remote-jid "$JID_COMMIT" \
    --reset-before-suite | tee "${EVIDENCE_DIR}/livecheck_ca05_booking_commit.jsonl"

  TEST_MODE=1 INSTANCE_ID="$INSTANCE_ID" python3 ops/diagnose.py livecheck-auto \
    --suite ca12-booking-full \
    --client-slug "$CLIENT_SLUG" \
    --branch-slug "$BRANCH_SLUG" \
    --base-url "$BASE_URL" \
    --noise none \
    --timeout "$LIVECHECK_TIMEOUT" \
    --poll-timeout "$LIVECHECK_POLL_TIMEOUT" \
    --remote-jid "$JID_FULL" \
    --reset-before-suite | tee "${EVIDENCE_DIR}/livecheck_ca12_booking_full.jsonl"
else
  info "Livecheck skipped (--no-livecheck)."
fi

extract_summary() {
  local jsonl="$1"
  local out="$2"
  python3 - "$jsonl" "$out" <<'PY'
import json
import sys

path, out = sys.argv[1], sys.argv[2]
summary = None
with open(path, "r", encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if "summary" in data:
            summary = data["summary"]

if summary is None:
    raise SystemExit("summary_not_found")

with open(out, "w", encoding="utf-8") as handle:
    json.dump(summary, handle)
PY
}

get_summary_value() {
  local summary="$1"
  local key="$2"
  python3 - "$summary" "$key" <<'PY'
import json
import sys

summary_path = sys.argv[1]
key = sys.argv[2]
data = json.load(open(summary_path, "r", encoding="utf-8"))
if key == "message_id":
    results = data.get("results") or []
    value = results[-1].get("message_id") if results else ""
else:
    value = data.get(key) or ""
print(value)
PY
}

appointment_ids=()
message_ids=()

if [[ "$NO_LIVECHECK" -eq 0 ]]; then
  ca05_summary="${EVIDENCE_DIR}/summary_ca05_booking_commit.json"
  ca12_summary="${EVIDENCE_DIR}/summary_ca12_booking_full.json"
  extract_summary "${EVIDENCE_DIR}/livecheck_ca05_booking_commit.jsonl" "$ca05_summary"
  extract_summary "${EVIDENCE_DIR}/livecheck_ca12_booking_full.jsonl" "$ca12_summary"

  ca05_msg_id="$(get_summary_value "$ca05_summary" "message_id")"
  ca12_msg_id="$(get_summary_value "$ca12_summary" "message_id")"
  ca05_appointment_id="$(get_summary_value "$ca05_summary" "appointment_id")"
  ca12_appointment_id="$(get_summary_value "$ca12_summary" "appointment_id")"

  if [[ -n "$ca05_msg_id" ]]; then
    python3 ops/diagnose.py explain --client-slug "$CLIENT_SLUG" --message-id "$ca05_msg_id" --limit 1 \
      | tee "${EVIDENCE_DIR}/explain_ca05_booking_commit.txt"
    message_ids+=("$ca05_msg_id")
  fi
  if [[ -n "$ca12_msg_id" ]]; then
    python3 ops/diagnose.py explain --client-slug "$CLIENT_SLUG" --message-id "$ca12_msg_id" --limit 1 \
      | tee "${EVIDENCE_DIR}/explain_ca12_booking_full.txt"
    message_ids+=("$ca12_msg_id")
  fi

  if [[ -n "$ca05_appointment_id" ]]; then
    appointment_ids+=("$ca05_appointment_id")
  fi
  if [[ -n "$ca12_appointment_id" ]]; then
    appointment_ids+=("$ca12_appointment_id")
  fi
fi

psql_to_file "${EVIDENCE_DIR}/sql_branch_booking_settings.txt" \
  "select id, slug, booking_settings from branches where id='${branch_id}';"
psql_to_file "${EVIDENCE_DIR}/sql_branch_instance.txt" \
  "select id, slug, instance_id, timezone from branches where id='${branch_id}';"
psql_to_file "${EVIDENCE_DIR}/sql_calendar_connections.txt" \
  "select id, client_id, branch_id, provider, calendar_id, status, created_at, updated_at from calendar_connections where branch_id='${branch_id}';"
psql_to_file "${EVIDENCE_DIR}/sql_calendar_tokens.txt" \
  "select id, client_id, branch_id, expires_at, encryption_version, created_at, updated_at from google_calendar_tokens where branch_id='${branch_id}';"
psql_to_file "${EVIDENCE_DIR}/sql_calendar_cursors.txt" \
  "select id, connection_id, last_synced_at, cursor, created_at, updated_at from calendar_sync_cursors where connection_id in (select id from calendar_connections where branch_id='${branch_id}');"

if [[ "${#appointment_ids[@]}" -gt 0 ]]; then
  ids_sql=""
  for value in "${appointment_ids[@]}"; do
    escaped="$(sql_escape "$value")"
    if [[ -n "$ids_sql" ]]; then
      ids_sql+=", "
    fi
    ids_sql+="'${escaped}'"
  done
  psql_to_file "${EVIDENCE_DIR}/sql_appointments.txt" \
    "select id, conversation_id, status, confirmation_policy, start_at, end_at, source, specialist_id, created_at from appointments where id in (${ids_sql});"
  psql_to_file "${EVIDENCE_DIR}/sql_appointment_sync_states.txt" \
    "select appointment_id, provider, state, last_error, updated_at from appointment_sync_states where appointment_id in (${ids_sql});"
  psql_to_file "${EVIDENCE_DIR}/sql_appointment_audit.txt" \
    "select appointment_id, action, payload->>'booking_mode' as booking_mode, payload->>'availability_provider' as availability_provider, payload->>'effective_booking_mode' as effective_booking_mode, created_at from appointment_audit where appointment_id in (${ids_sql}) order by created_at;"
  psql_to_file "${EVIDENCE_DIR}/sql_outbox_calendar_sync.txt" \
    "select inbound_message_id, status, payload_json->'payload'->>'appointment_id' as appointment_id, created_at from outbox_messages where payload_json->>'event_type' = 'calendar.sync_outbound' and payload_json->'payload'->>'appointment_id' in (${ids_sql}) order by created_at;"
  psql_to_file "${EVIDENCE_DIR}/sql_calendar_blocks.txt" \
    "select id, branch_id, start_at, end_at, source, provider from calendar_blocks where branch_id='${branch_id}' and start_at::date in (select start_at::date from appointments where id in (${ids_sql}));"
fi

if [[ "${#message_ids[@]}" -gt 0 ]]; then
  msg_sql=""
  for value in "${message_ids[@]}"; do
    escaped="$(sql_escape "$value")"
    if [[ -n "$msg_sql" ]]; then
      msg_sql+=", "
    fi
    msg_sql+="'${escaped}'"
  done
  psql_to_file "${EVIDENCE_DIR}/sql_outbox_booking_send.txt" \
    "select inbound_message_id, status, payload_json->>'event_type' as event_type, created_at from outbox_messages where inbound_message_id in (${msg_sql}) order by created_at;"
  psql_to_file "${EVIDENCE_DIR}/sql_outbox_idempotency.txt" \
    "select inbound_message_id, count(*) from outbox_messages where inbound_message_id in (${msg_sql}) group by inbound_message_id;"
  psql_to_file "${EVIDENCE_DIR}/sql_messages_decision_meta.txt" \
    "select id, metadata->'decision_meta' as decision_meta from messages where metadata->>'messageId' in (${msg_sql});"
fi

info "Done. Evidence captured in ${EVIDENCE_DIR}"
