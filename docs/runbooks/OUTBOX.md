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
