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

2) If PROCESSING is stuck (use only for recovery, not for evidence)
```bash
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c "\
UPDATE outbox_messages\
SET status='PENDING', last_error='manual_release', next_attempt_at=NOW(), updated_at=NOW()\
WHERE status='PROCESSING' AND updated_at < NOW() - INTERVAL '2 minutes';"
```

3) If FAILED spikes, inspect reasons
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
