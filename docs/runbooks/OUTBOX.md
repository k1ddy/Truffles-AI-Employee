# Runbook: Outbox

Purpose
- Keep outbound delivery reliable and idempotent.

Symptoms
- Messages stuck in PENDING/PROCESSING
- Outbox backlog grows, SLA breached

Quick checks
```bash
curl -s http://localhost:8000/admin/health
```

Mandatory safety preflight
- Before running `ops/diagnose.py` suites or any outbound live-check, verify runtime guard flags:
```bash
curl -s http://localhost:8000/admin/health | jq '.safety'
```
- Expected:
  - `status` is `ok` or `warning`.
  - `danger_flags` is empty.
- If `danger_flags` is not empty, stop and fix environment first.
  - Typical blockers:
    - `test_mode_outbox_worker_on_nonlocal_db`
    - `test_mode_outbox_worker_without_allowlist`

Contract guardrails
- Outbox payload types:
  - `schema_version=outbox.v1` + `event_type=whatsapp.send_text` for send-only delivery.
  - `schema_version=outbox.v1` + `event_type=whatsapp.send_media` for media delivery
    (`media_type`, `media_url`/`signed_url`, optional `caption`, `media_meta`).
  - Legacy webhook payloads validated by `app.schemas.outbox_payload.OutboxPayloadContract`.
- Invalid payload → `decision_trace.stage=outbox_payload_guard`, `decision_meta.action=error`, no outbox enqueue.
- Timing evidence: `decision_meta.timing.outbox` + `outbox_messages.meta.timing`.
- Provider Gateway:
  - `PROVIDER_GATEWAY_INBOUND_ENABLED=1` + `PROVIDER_GATEWAY_INBOX_ENABLED=1` → `inbox_events` recorded on `/provider/inbound`.
  - `PROVIDER_GATEWAY_OUTBOUND_ENABLED=1` routes **all** outbox sends through Provider Gateway (global).

```bash
curl -sG http://localhost:9090/api/v1/query --data-urlencode \
  'query=histogram_quantile(0.95, sum by (le, client_slug) (rate(outbox_latency_bucket[5m])))' \
  | python3 - <<'PY'
import json, sys
data = json.load(sys.stdin)
for item in data.get("data", {}).get("result", []):
    slug = item.get("metric", {}).get("client_slug", "all")
    value = item.get("value", [None, None])[1]
    print(f"outbox_p95 {slug}: {value}s")
PY
```

```bash
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
SELECT status, COUNT(*), MIN(created_at) AS oldest\
FROM outbox_messages\
WHERE status IN ('PENDING','PROCESSING','FAILED')\
GROUP BY status;"
```

```bash
# Bundle timings for a specific inbound message.
python3 ops/diagnose.py trace-bundle --client-slug demo_salon --message-id "<CHATFLOW_MESSAGE_ID>"
```

Recovery steps
1) Restart outbox worker
```bash
docker restart truffles-outbox
```

2) Scale out workers (safe horizontal add)
```bash
# Use the same image as API to avoid behavior drift
IMAGE_NAME="$(docker inspect truffles-api --format '{{.Config.Image}}')"
docker run -d --name truffles-outbox-2 \
  --env-file /home/zhan/truffles-main/truffles-api/.env \
  --network truffles_internal-net \
  --restart unless-stopped \
  "$IMAGE_NAME" python -m app.workers.outbox
```

Verify:
```bash
docker ps | rg 'truffles-outbox'
curl -s http://localhost:8000/admin/health | rg outbox
```

Rollback (remove extra worker):
```bash
docker rm -f truffles-outbox-2
```

3) If PROCESSING is stuck (use only for recovery, not for evidence)
```bash
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
UPDATE outbox_messages\
SET status='PENDING', last_error='manual_release', next_attempt_at=NOW(), updated_at=NOW()\
WHERE status='PROCESSING' AND updated_at < NOW() - INTERVAL '2 minutes';"
```

4) If FAILED spikes, inspect reasons
```bash
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
SELECT last_error, COUNT(*)\
FROM outbox_messages\
WHERE status='FAILED'\
GROUP BY last_error ORDER BY 2 DESC LIMIT 10;"
```

Evidence to capture
- SQL snapshot (counts + oldest)
- Worker logs around restart
- Any alert triggered (if present)

Notes
- Do not modify DB/trace to fabricate evidence. Use DB updates only for recovery.
- `WEBHOOK_ENQUEUE_ONLY=1` forces `/webhook` to enqueue-only (bypasses full decision pipeline).
- Outbox worker now has startup hard-stop for unsafe test-mode combinations; override exists only for explicit local debug: `OUTBOX_WORKER_UNSAFE_ALLOW=1`.

---

## Staging Rollout: Outreach + Human Lock (2026-02-20)

Purpose
- Verify manual outreach by phone/JID from Console and per-client bot pause (`human_lock`) without breaking outbox reliability.

Scope
- API endpoints:
  - `POST /console/v1/outreach/messages`
  - `GET /console/v1/conversations/{conversation_id}/human-lock`
  - `POST /console/v1/conversations/{conversation_id}/human-lock/pause`
  - `DELETE /console/v1/conversations/{conversation_id}/human-lock`
- Webhook runtime gate: `decision=human_lock_silent`.

### A. One-time per DB: migration 033

Check pending migrations:
```bash
python3 truffles-api/scripts/apply_sql_migrations.py --check
```

Deploy/restart with migrations enabled:
```bash
IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main \
PULL_IMAGE=1 \
RUN_MIGRATIONS=1 \
MIGRATION_BOOTSTRAP_MODE=auto \
REQUIRE_GHCR=1 \
bash scripts/restart_release.sh
```

Verify table exists:
```bash
DB_USER=$(docker exec -i truffles_postgres_1 /bin/sh -lc 'printf %s "${POSTGRES_USER:-postgres}"')
docker exec -i truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
SELECT to_regclass('public.conversation_human_locks') AS table_name;"
```

### B. Worker health (always)

```bash
docker ps --format '{{.Names}} {{.Status}}' | rg 'truffles-(api|outbox|sentinel)'
curl -s http://localhost:8000/admin/health | jq '.checks.outbox, .safety'
```

### C. Live-check: outreach + pause + webhook gate

Prepare environment:
```bash
export CONSOLE_URL="http://localhost:8000/console/v1"
export CONSOLE_TOKEN="<console_access_token>"
export CLIENT_ID="<client_uuid>"
export BRANCH_ID="<branch_uuid>"
export CONVERSATION_ID="<conversation_uuid>"
export REMOTE_JID="<digits>@s.whatsapp.net"
export CHATFLOW_TOKEN="<chatflow_token>"
export INSTANCE_ID="<chatflow_instance_id>"
```

1) Send outreach + auto pause 30m:
```bash
curl -sS -X POST "$CONSOLE_URL/outreach/messages" \
  -H "Authorization: Bearer $CONSOLE_TOKEN" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "X-Branch-Id: $BRANCH_ID" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: outreach-stg-$(date +%s)" \
  -d "{\"destination\":\"$REMOTE_JID\",\"content\":\"STG outreach check\",\"conversation_id\":\"$CONVERSATION_ID\",\"pause_bot_minutes\":30}" \
  | jq
```

2) Check lock status:
```bash
curl -sS "$CONSOLE_URL/conversations/$CONVERSATION_ID/human-lock" \
  -H "Authorization: Bearer $CONSOLE_TOKEN" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "X-Branch-Id: $BRANCH_ID" \
  | jq
```

3) Simulate inbound while lock is active:
```bash
python3 ops/chatflow_send.py \
  --token "$CHATFLOW_TOKEN" \
  --instance-id "$INSTANCE_ID" \
  --jid "$REMOTE_JID" \
  --text "HLK-LIVE-$(date +%s)"
```

4) Verify decision trace/meta (expect `human_lock_silent`):
```bash
python3 ops/diagnose.py explain --conversation-id "$CONVERSATION_ID" --minutes 10 --limit 20
python3 ops/diagnose.py trace-bundle --conversation-id "$CONVERSATION_ID" --minutes 10 --output -
```

5) Release pause and verify bot answers again:
```bash
curl -sS -X DELETE "$CONSOLE_URL/conversations/$CONVERSATION_ID/human-lock" \
  -H "Authorization: Bearer $CONSOLE_TOKEN" \
  -H "X-Client-Id: $CLIENT_ID" \
  -H "X-Branch-Id: $BRANCH_ID" \
  | jq
```

### D. Evidence package (mandatory)

- `conversation_id`
- `trace-bundle` output with `decision=human_lock_silent` for locked inbound
- `decision_meta` for last inbound
- latest `outbox_messages` row status (`queued|sent|failed`)

SQL snapshot:
```bash
DB_USER=$(docker exec -i truffles_postgres_1 /bin/sh -lc 'printf %s "${POSTGRES_USER:-postgres}"')
docker exec -i truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
SELECT id, status, attempts, last_error, updated_at \
FROM outbox_messages \
WHERE conversation_id = '$CONVERSATION_ID'::uuid \
ORDER BY created_at DESC \
LIMIT 5;"
```

### E. Rollback

- Emergency off for pause behavior: remove active locks.
```bash
DB_USER=$(docker exec -i truffles_postgres_1 /bin/sh -lc 'printf %s "${POSTGRES_USER:-postgres}"')
docker exec -i truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
UPDATE conversation_human_locks \
SET active = FALSE, released_at = NOW(), lock_until = NOW(), updated_at = NOW() \
WHERE active = TRUE;"
```

- If feature rollback is required: deploy previous image via `scripts/restart_release.sh` and re-run section B checks.
