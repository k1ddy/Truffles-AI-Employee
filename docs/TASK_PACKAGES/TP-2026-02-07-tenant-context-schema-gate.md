# TP-2026-02-07-tenant-context-schema-gate

- Название/цель: Вшить единый runtime-валидатор `tenant_context` на основе канонического JSON Schema и убрать риск частичной tenant-изоляции между webhook/provider/outbox.
- Canon refs: `STATE.md` (NOW: tenant_context runtime hardening), `contracts/tenancy/tenant_context.v1.jsonschema`, `SPECS/MULTI_TENANT.md` (tenant context contract), `AGENTS.md` (P0/P1 fitness).
- Invariant:
  - Tenant mismatch не проходит в обработку/доставку.
  - `decision_meta/decision_trace` на inbound не теряются.
  - Outbox idempotency/worker flow не ломаются.
- Scope:
  - Добавить общий сервис валидации `tenant_context` по `contracts/tenancy/tenant_context.v1.jsonschema`.
  - Подключить в webhook preflight (проверка payload tenant_context).
  - Подключить в provider-gateway (inbound/outbound contract checks).
  - Подключить в outbox row guard (json payload contract check).
  - Добавить/обновить targeted tests.
- Out of scope:
  - Provider/Channel DEC и новая Channel-модель.
  - Onboarding automation.
  - Физическая изоляция schema/DB-per-tenant.
- Touch-list (files/tables):
  - `truffles-api/app/services/tenant_context_contract.py` (new)
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/routers/provider_gateway.py`
  - `truffles-api/tests/test_webhook_parsing_tenant_context.py`
  - `truffles-api/tests/test_provider_gateway_inbound.py`
  - `truffles-api/tests/test_provider_gateway_outbound.py`
  - `truffles-api/tests/test_provider_gateway_integration.py`
  - `truffles-api/tests/test_outbox_payload_contract.py`
  - `STATE.md`
- Plan:
  1) Проверить текущие runtime точки валидации и зафиксировать gap.
  2) Реализовать общий schema-validator + кэш загрузки schema.
  3) Интегрировать validator в webhook/provider/outbox с fail-closed поведением.
  4) Добавить/обновить тесты для valid/invalid tenant_context по schema.
  5) Прогнать targeted pytest + ruff и зафиксировать evidence.
- DoD:
  - Во всех runtime точках используется единый validator от канонического schema-файла.
  - Invalid `tenant_context` приводит к предсказуемому contract error/early reject.
  - Целевые тесты зелёные.
- Checks:
  - `ruff check truffles-api/app/services/tenant_context_contract.py truffles-api/app/routers/webhook/http.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/routers/provider_gateway.py truffles-api/tests/test_provider_gateway_inbound.py truffles-api/tests/test_provider_gateway_outbound.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_webhook_parsing_tenant_context.py truffles-api/tests/test_outbox_payload_contract.py`
  - `pytest -q truffles-api/tests/test_provider_gateway_inbound.py truffles-api/tests/test_provider_gateway_outbound.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_webhook_parsing_tenant_context.py truffles-api/tests/test_outbox_payload_contract.py`
- Evidence:
  - `/tmp/pytest_tenant_context_schema_gate_20260207.txt`
  - запись в `STATE.md` (NOW bullet) с ссылками на код и тесты.
- Rollback:
  - Откатить изменения в touch-files к `origin/main`.
- No-go:
  - Не менять `_legacy.py`.
  - Не править БД/trace руками.
  - Не ослаблять tenant guards ради прохода тестов.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-07-tenant-context-schema-gate-a13`
  - Worktree: `/home/zhan/worktrees/2026-02-07-tenant-context-schema-gate-a13`
  - Base: `origin/main`
  - Merge policy: PR в `main` после green checks и evidence.
  - Cleanup: `scripts/session_end.sh --status done` после merge.
- Риски/блокеры:
  - Legacy payloads могут иметь частично заполненный tenant_context; нужно сохранить backward-compatible reject semantics там, где это уже enforced.
