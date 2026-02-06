# TP-2026-02-06-tenant-context-runtime-a13

- Название/цель: Вшить tenant_context контракт в runtime webhook/outbox/metrics и закрыть cross-tenant тесты вне Console.
- Canon refs: `STATE.md` (NOW: tenant_context gap + cross-tenant tests gap), `contracts/tenancy/tenant_context.v1.jsonschema`, `STRUCTURE.md`, `SPECS/MULTI_TENANT.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Нет cross-tenant обработки/отправки при tenant mismatch.
  - decision_trace/decision_meta продолжают писаться на user-turn.
  - outbox idempotency и текущая логика delivery retries не ломаются.
- Scope:
  - Добавить `tenant_context` в webhook request schema + parsing.
  - В preflight webhook проверять tenant_context (client/slug/instance/branch) и формировать effective tenant_context.
  - Сохранять effective tenant_context в metadata входящего user-message.
  - Добавить tenant_context фильтр в metrics daily/analytics SQL.
  - Добавить guard в outbox processing на tenant_context/client_id/branch_id mismatch.
  - Добавить unit tests для webhook/outbox/audit tenant isolation.
- Out of scope:
  - DEC на Provider/Channel модель.
  - Физическая изоляция (schema/DB-per-tenant).
  - Полный onboarding automation.
- Touch-list (files/tables):
  - `truffles-api/app/schemas/webhook.py`
  - `truffles-api/app/routers/webhook/parsing.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/services/metrics_daily_service.py`
  - `truffles-api/tests/test_branch_routing_instance.py`
  - `truffles-api/tests/test_provider_gateway_integration.py`
  - `truffles-api/tests/test_webhook_parsing_tenant_context.py`
  - `truffles-api/tests/test_metrics_daily_tenant_context_sql.py`
  - `truffles-api/tests/test_audit_service.py`
  - `STATE.md`
- Plan:
  1) Внести webhook schema/parsing/preflight изменения для tenant_context.
  2) Прокинуть tenant_context в persisted message metadata.
  3) Добавить tenant_context guard в outbox row processing.
  4) Добавить tenant_context filtering в metrics SQL.
  5) Добавить и прогнать targeted pytest.
  6) Обновить `STATE.md` evidence до merge.
- DoD:
  - Webhook preflight отклоняет tenant mismatch (`client/slug/branch/instance`).
  - Inbound user-message содержит `metadata.tenant_context`.
  - Outbox row с tenant mismatch не отправляется и помечается `FAILED` с contract_error.
  - Metrics SQL учитывает `metadata.tenant_context.client_id`.
  - Targeted pytest зелёный.
- Checks:
  - `pytest -q truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_audit_service.py truffles-api/tests/test_webhook_parsing_tenant_context.py truffles-api/tests/test_branch_routing_instance.py truffles-api/tests/test_metrics_daily_tenant_context_sql.py truffles-api/tests/test_reasoning_core.py`
- Evidence:
  - `/tmp/pytest_tenant_context_runtime_20260206_a13.txt`
  - запись в `STATE.md` (NOW bullet) с путями к коду и тестам.
- Rollback:
  - Откатить изменения в перечисленных touch-files к `origin/main`.
- No-go:
  - Не менять `_legacy.py` оркестрацией.
  - Не править БД/trace руками ради evidence.
  - Не ослаблять tenant guard для прохождения тестов.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-06-tenant-context-runtime-a13`
  - Worktree: `/home/zhan/worktrees/2026-02-06-tenant-context-runtime-a13`
  - Base: `origin/main`
  - Merge: PR/merge в `main` после test evidence.
  - Cleanup: `scripts/session_end.sh --status done` + cleanup worktree/branch.
- Риски/блокеры:
  - Возможны legacy outbox rows без tenant_context; guard не должен ломать их при отсутствии mismatch.
