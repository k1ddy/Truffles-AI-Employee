# SUMMARY

⚠️ Этот handover требует проверки. Пункты ниже — ориентир, но их нужно подтвердить по API/DB/логам.

Принципы «мозгов» бота (быстрый контекст)
- Истина только из Truth-слоя (`SALON_TRUTH.yaml`) + строгое соблюдение LAW.
- Policy-gate до RAG/LLM: оплаты/перенос/medical/жалобы → всегда эскалация.
- RAG-документы не должны противоречить LAW; иначе это утечка.
- Любая правка мозгов = пакет: truth + intents + eval + sync (иначе регресс).
- Короткие/статусные сообщения не эскалировать (whitelist + bot_status).

Session handover (2025-12-24)
- Decision: roles/identities + learning queue + Telegram per branch; branch routing configurable (by_instance/ask_user/hybrid).
- Added models: Agent, AgentIdentity, LearnedResponse; added migration `ops/migrations/013_add_agents_and_learning_queue.sql`; added `branch_id` to conversations.
- Specs updated: `SPECS/ESCALATION.md`, `SPECS/ARCHITECTURE.md`, `SPECS/ACTIVE_LEARNING.md`, `SPECS/MULTI_TENANT.md`, `SPECS/CONSULTANT.md`.
- Implemented: `/admin/settings` extended for branch routing + auto-approve; webhook branch routing (by_instance/ask_user/hybrid) + remember_branch.
- Added migration `ops/migrations/014_add_branch_routing_settings.sql`; default auto-approve = `owner,admin`.
- Prod fix (needs verification): applied migration 013/014 to add `conversations.branch_id` (webhook was crashing without it).
- Prod config (needs verification): created `branches` row for demo_salon (instance_id + telegram_chat_id), set settings to by_instance + remember_branch.
- Known blocker: inbound payload currently lacks `metadata.instanceId`, so by_instance cannot resolve branch until upstream is fixed.
- Known behavior: demo_salon truth-gate отвечает прайсом на "как у/в стиле"; фото не поддерживаются → нужен отдельный rule.
- Webhook now ingests instanceId from query params or nodeData into metadata (upstream still needs to send it).
- Removed legacy workflow artifacts and n8n references (docs/prompts/ops); deleted ops helper tied to workflow JSON.
- Deploy paths standardized to `/home/zhan/truffles-main/truffles-api`; `/home/zhan/restart_api.sh` updated accordingly.
- Git worktree fixed: `.git` restored from clean clone → git status/commit/push работают.
- Tests: not verified in this session (rerun `pytest -q`).
- Next step: wire Telegram flow to use agents/identities + learned_responses queue + branch telegram_chat_id.

Inventory highlights
- Docker compose: infra split — `/home/zhan/infrastructure/docker-compose.yml` (traefik, website) and `/home/zhan/infrastructure/docker-compose.truffles.yml` (core stack); `/home/zhan/truffles-main/docker-compose.yml` is a stub.
- Running containers include truffles-api, postgres, qdrant, redis, pgadmin, traefik, bge-m3, truffles-website, gemini proxy.
- Volumes: truffles_postgres_data, truffles_qdrant_data, truffles_redis_data, ops_bge-m3-data.
- Postgres: single schema public; 23 tables including clients, conversations, messages, handovers, knowledge_versions, knowledge_sync_logs, audit_log, error_logs, message_traces.
- Qdrant: collection truffles_knowledge, vector size 1024 (Cosine), points_count 111, payload_schema empty.
- API: FastAPI routes /webhook, /telegram-webhook, /reminders/process, /admin/health, /admin/outbox/process.
- WhatsApp: ACK-first (/webhook enqueues outbox), inbound dedup + webhook secret; outbound via ChatFlow with retries and msg_id idempotency (webhook/outbox).
- Guardrails: whitelist/low-signal + domain router anchors; low-confidence thresholds 0.85/0.5.
- Alerts: status unknown; verify via `/alerts/test` and Telegram delivery.
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

Validation not executed in this session.
