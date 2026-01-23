# Truffles Platform — Runbook

## Quick Reference

| Symptom | Likely Cause | First Action |
|---------|--------------|--------------|
| Messages not delivered | ChatFlow down | Check `/admin/health/check` |
| High escalation rate | LLM issues | Check `llm_fallback_total` |
| Outbox stuck | Worker down | Check outbox queue |
| 403 on Console | Auth misconfigured | Verify OIDC settings |

---

## 1. Outbox Queue Stuck

### Symptoms
- Messages pending > 15 minutes
- `/admin/health/check` shows `outbox.pending > 50`

### Diagnosis
```bash
# Check outbox status
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
SELECT status, COUNT(*), MIN(created_at) as oldest
FROM outbox_messages 
WHERE status IN ('PENDING', 'PROCESSING', 'FAILED')
GROUP BY status;"
```

### Resolution

**If PROCESSING stuck (> 2 min old):**
```bash
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
UPDATE outbox_messages 
SET status = 'PENDING',
    last_error = 'manual_release',
    next_attempt_at = NOW(),
    updated_at = NOW()
WHERE status = 'PROCESSING' 
AND updated_at < NOW() - INTERVAL '2 minutes';"
```

**If FAILED count high:**
```bash
# Check failure reasons
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
SELECT last_error, COUNT(*) 
FROM outbox_messages WHERE status = 'FAILED'
GROUP BY last_error ORDER BY 2 DESC LIMIT 10;"
```

**Restart outbox worker:**
```bash
docker restart truffles-outbox
```

---

## 2. ChatFlow Integration Down

### Symptoms
- `/admin/health/check` shows `chatflow.status = unhealthy`
- Messages sent but not delivered

### Diagnosis
```bash
# Test ChatFlow directly
curl -s "https://app.chatflow.kz/api/v1/send-text?token=$CHATFLOW_TOKEN&instance_id=$INSTANCE_ID&jid=test@s.whatsapp.net&msg=test"
```

### Resolution
1. If ChatFlow down → wait for provider recovery
2. If token expired → regenerate in ChatFlow dashboard
3. If instance problem → check ChatFlow admin panel

---

## 3. Telegram Notifications Failing

### Symptoms
- Escalations created but no Telegram messages
- Managers not receiving alerts

### Diagnosis
```bash
# Check webhook status
curl "https://api.telegram.org/bot$TG_BOT_TOKEN/getWebhookInfo"

# Check recent errors
docker logs truffles-api --tail 100 | grep -i telegram
```

### Resolution

**If webhook URL wrong:**
```bash
curl -X POST "https://api.telegram.org/bot$TG_BOT_TOKEN/setWebhook?url=https://api.truffles.kz/telegram-webhook"
```

**If rate limited (429):**
- Wait 60 seconds
- Check for spam/loops in code

---

## 4. High Escalation Rate

### Symptoms
- `escalation_total` rate > 30% in metrics
- Managers overwhelmed

### Diagnosis
```bash
# Check escalation triggers
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
SELECT trigger_type, trigger_value, COUNT(*) 
FROM handovers 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY trigger_type, trigger_value 
ORDER BY 3 DESC LIMIT 10;"
```

### Resolution
1. If `low_confidence` → check Qdrant / knowledge quality
2. If `shield` → review spam patterns
3. If `intent=HUMAN_REQUEST` → normal behavior

---

## 5. Qdrant / RAG Issues

### Symptoms
- Bot giving wrong answers
- `/admin/health/check` shows `qdrant.status = unhealthy`

### Diagnosis
```bash
# Check Qdrant
curl -s -H "api-key: $QDRANT_API_KEY" http://localhost:6333/collections

# Check collection size
curl -s -H "api-key: $QDRANT_API_KEY" http://localhost:6333/collections/truffles_knowledge
```

### Resolution
```bash
# Restart Qdrant
docker restart truffles_qdrant_1
```

---

## 6. Console Login Failing

### Symptoms
- 403 ACCESS_DENIED after SSO login
- "No agent found" in logs
- 400 CLIENT_SELECTION_REQUIRED on `/console/v1/*`

### Diagnosis
```bash
# Check agent identity
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
SELECT ai.external_id, a.name, a.role 
FROM agent_identities ai 
JOIN agents a ON a.id = ai.agent_id 
WHERE ai.channel = 'oidc';"

# Check duplicate client mappings for one sub
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
SELECT external_id, COUNT(DISTINCT agent_id) AS agents
FROM agent_identities
WHERE channel = 'oidc'
GROUP BY external_id
HAVING COUNT(DISTINCT agent_id) > 1;"
```

### Resolution
```bash
# Create missing agent identity
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
INSERT INTO agent_identities (id, agent_id, channel, external_id)
SELECT gen_random_uuid(), a.id, 'oidc', 'KEYCLOAK_USER_SUBJECT'
FROM agents a WHERE a.name = 'manager';"

# If CLIENT_SELECTION_REQUIRED: keep only one mapping or use X-Client-Id
# (remove extra agent_identities for the same external_id)
```

---

## 7. API Restart Procedure

### Standard Restart (no code change)
```bash
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```

### Restart with new image
```bash
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash ~/restart_api.sh"
```

### Verify restart
```bash
curl https://api.truffles.kz/health
curl https://api.truffles.kz/admin/health/check
```

---

## 8. Worker Cutover (API + Outbox/Sentinel split)

### Goal
Stop old combined worker loops, start dedicated containers, avoid double sending.

### Steps
1) **Stop old API container** (removes embedded workers):
```bash
ssh -p 222 zhan@5.188.241.234 "docker stop truffles-api && docker rm truffles-api"
```
2) **Start new API container** (no embedded workers):
```bash
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```
3) **Start workers**:
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env bash /home/zhan/truffles-main/scripts/restart_workers.sh"
```
4) **Verify only one outbox processor**:
```bash
ssh -p 222 zhan@5.188.241.234 "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | rg 'truffles-api|truffles-outbox|truffles-sentinel'"
```

### Guardrails
- If running an old image that still starts workers inside API, set `OUTBOX_WORKER_ENABLED=0` for API and keep `OUTBOX_WORKER_ENABLED=1` for worker containers.
- Ensure the `.env` file exists; missing env will make worker containers fail to start (or exit immediately).
- `OTEL_SERVICE_NAME` should be different per container (API/outbox/sentinel) to keep traces clean.

## 8. Worker Containers (Outbox/Sentinel)

### Restart workers
```bash
docker restart truffles-outbox
docker restart truffles-sentinel
```
Или:
```bash
ENV_FILE=/home/zhan/truffles-main/truffles-api/.env bash /home/zhan/truffles-main/scripts/restart_workers.sh
```

### Validate workers are alive
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "truffles-outbox|truffles-sentinel"
```

### Rollout checklist (decoupled workers)
1. Deploy new API image (`restart_api.sh`).
2. Ensure no in-process workers (new image removes them).
3. Start `truffles-outbox` and `truffles-sentinel` containers.
4. Verify outbox latency p90 and no stuck PROCESSING (SQL + `/admin/metrics`).
5. Confirm alerts/health via `/admin/health/check`.

---

## 9. Console OpenAPI Drift Check

```bash
cd /home/zhan/truffles-main
python3 truffles-api/scripts/generate_openapi.py --check
```

---

## 10. Database Emergency

### Symptoms
- `/admin/health/check` shows `database.status = unhealthy`
- API returning 500s

### Diagnosis
```bash
# Check postgres
docker logs truffles_postgres_1 --tail 50

# Check connections
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "SELECT count(*) FROM pg_stat_activity;"
```

### Resolution
```bash
# Kill idle connections
docker exec truffles_postgres_1 psql -U $DB_USER -d chatbot -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND query_start < NOW() - INTERVAL '10 minutes';"

# Restart if needed
docker restart truffles_postgres_1
```

---

## 8. Trace / Observability

### Symptoms
- Latency spikes or "no reply" complaints
- Outbox backlog without clear error

### Diagnosis
```bash
python3 ops/diagnose.py trace-bundle --client-slug <slug> --message-id <id> --output /tmp/trace-bundle.json
```

```bash
curl -fsS http://localhost:3200/metrics | rg -m 1 tempo_distributor_spans_received_total
```

### Evidence
- trace-bundle JSON path + timing.stages snapshot
- Tempo metric line or container logs

---

## Contact

| Issue | Contact |
|-------|---------|
| Infrastructure | @zhan |
| Business logic | @zhan |
| Client issues | Contact client owner |
