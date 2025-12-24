# CHATGPT_QUESTIONS_ANSWERS.md

## Snapshot
- Date: 2025-12-24T12:39:44+05:00
- Branch: main-worktree
- Commit (HEAD): b74704701d43cd6394e231ec89ccc52a189d9a4d
- Prod host/services: 5.188.241.234 (truffles-api, truffles_postgres_1, truffles_redis_1, truffles_qdrant_1, truffles_n8n_1, truffles-traefik, bge-m3); public: https://api.truffles.kz, https://n8n.truffles.kz

## Outbox
Q: Where is inbound webhook endpoint implemented?
A: truffles-api/app/routers/webhook.py (`handle_webhook` for /webhook, `handle_webhook_direct` for /webhook/{client_slug}).

Q: Where is ACK-first implemented?
A: truffles-api/app/routers/webhook.py `_handle_webhook_payload` with `enqueue_only=True` and `enqueue_outbox_message` in truffles-api/app/services/outbox_service.py; returns "Accepted" without LLM.

Q: How is outbox processor triggered in prod (exact mechanism)?
A: Cron `/etc/cron.d/truffles-outbox` runs every minute and calls `POST http://localhost:8000/admin/outbox/process` (documented in TECH.md).

Q: What auth header/token name protects admin/outbox processing?
A: Header `X-Admin-Token` validated against `ALERTS_ADMIN_TOKEN` in truffles-api/app/routers/admin.py.

## Coalescing (8s)
Q: Where is the 8s window defined and how enforced?
A: `OUTBOX_COALESCE_SECONDS` default 8 in truffles-api/app/routers/admin.py, passed to `claim_pending_outbox_batches` in truffles-api/app/services/outbox_service.py; SQL enforces idle window via `HAVING MAX(created_at) <= NOW() - (:idle_seconds * INTERVAL '1 second')`.

Q: What key is used to group messages?
A: `conversation_id` (grouping in claim_pending_outbox_batches and batch processing in truffles-api/app/routers/admin.py).

Q: What dedup / idempotency guard prevents double replies?
A: Unique index on (client_id, inbound_message_id) in ops/migrations/012_add_outbox_messages.sql + `enqueue_outbox_message(...).on_conflict_do_nothing`; inbound dedup uses `is_duplicate_message_id` in truffles-api/app/routers/webhook.py (Redis + message_dedup table in ops/migrations/010_add_message_dedup.sql); outbound idempotency uses ChatFlow `msg_id` set in truffles-api/app/services/chatflow_service.py.

## Truth-first
Q: Where is demo_salon truth stored (path) and what keys exist?
A: truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml; keys: salon, promotions, booking, guest_policy, service_duration_estimates, hygiene, brands, safety, quality, pricing, price_list.

Q: Which code path selects truth-first vs RAG/LLM?
A: truffles-api/app/routers/webhook.py `_handle_webhook_payload` calls `get_demo_salon_decision` (truffles-api/app/services/demo_salon_knowledge.py) before booking/intent/RAG; if it returns a decision, it replies/escalates and exits.

## Policy-gate (LAW)
Q: Where are LAW rules encoded (path)? How does "payments/reschedule/discount/medical-complaint" route?
A: Rules documented in truffles-api/app/knowledge/demo_salon/POLICY.md and enforced in truffles-api/app/services/demo_salon_knowledge.py (`_detect_policy_intent`, `get_demo_salon_decision`). Routes: payments/reschedule/medical/complaint -> `action="escalate"`; discount/haggle -> `action="reply"` with official promotions (no escalation).

## EVAL
Q: Where are EVAL tests and how to run?
A: truffles-api/tests/test_demo_salon_eval.py (cases in truffles-api/app/knowledge/demo_salon/EVAL.yaml). Run: `pytest -q truffles-api/tests/test_demo_salon_eval.py`.

Q: Current EVAL status? (pass/fail + failing tests list)
A: Pass (1 test, 0 failing). Warning: PydanticDeprecatedSince20.

## Known issues / TODO
- Issue: Active Learning owner responses not detected (no "Owner response detected" log).
- Evidence: STATE.md notes owner message delivered to client but no learning log.
- Fix idea: trace telegram_webhook -> manager_message_service -> learning_service.is_owner_response; verify owner_telegram_id matching and add logging around owner detection.
- Issue: Low-confidence escalations still frequent on simple messages.
- Evidence: STATE.md notes short acknowledgements and "are you still there" escalating due to low RAG score.
- Fix idea: add base KB entries + keep low-confidence clarification flow before handover.
