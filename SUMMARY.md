# SUMMARY

Inventory highlights
- Docker compose: infra split — `/home/zhan/infrastructure/docker-compose.yml` (traefik, website) and `/home/zhan/infrastructure/docker-compose.truffles.yml` (n8n, n8n-worker, postgres, qdrant, redis, pgadmin); `/home/zhan/truffles/docker-compose.yml` is a stub.
- Running containers include truffles-api, n8n, postgres, qdrant, redis, pgadmin, traefik, bge-m3, truffles-website, gemini proxy.
- Volumes: truffles_n8n_data, truffles_postgres_data, truffles_qdrant_data, truffles_redis_data, ops_bge-m3-data.
- Postgres: single schema public; 23 tables including clients, conversations, messages, handovers, knowledge_versions, knowledge_sync_logs, audit_log, error_logs, message_traces.
- Qdrant: collection truffles_knowledge, vector size 1024 (Cosine), points_count 111, payload_schema empty.
- API: FastAPI routes /webhook, /telegram-webhook, /reminders/process, /admin/health, /admin/outbox/process.
- WhatsApp: ACK-first (/webhook enqueues outbox), inbound dedup + webhook secret; outbound via ChatFlow with retries and msg_id idempotency (webhook/outbox).
- Guardrails: whitelist/low-signal + domain router anchors; low-confidence thresholds 0.85/0.5.
- Alerts: alert_service configured; /alerts/test exists for runtime check.
- CI/CD: GitHub Actions `.github/workflows/ci.yml` (ruff + pytest + build/push to GHCR; optional deploy via SSH).

Missing/risks (high-level)
- Canary by tenant not implemented.
- QC stage missing; audit/incident logs not wired.
- Outbound idempotency only for webhook/outbox (not all send paths).
- Release rollback strategy not documented; sentinel monitoring missing.

Top-10 GAP priority
1) GAP-002 Canary by tenant missing
2) GAP-006 QC stage missing
3) GAP-011 Outbound idempotency partial
4) GAP-008 Audit log not wired
5) GAP-009 Incident/error logs not wired
6) GAP-012 Release rollback not documented
7) GAP-013 Sentinel/continuous monitoring missing

YAML validation commands
- python -c "import yaml; yaml.safe_load(open('docs/IMPERIUM_CONTEXT.yaml','r',encoding='utf-8')); print('OK')"
- python -c "import yaml; yaml.safe_load(open('docs/IMPERIUM_DECISIONS.yaml','r',encoding='utf-8')); print('OK')"
- python -c "import yaml; yaml.safe_load(open('docs/IMPERIUM_GAPS.yaml','r',encoding='utf-8')); print('OK')"

Validation executed with python3 (python is not in PATH).
