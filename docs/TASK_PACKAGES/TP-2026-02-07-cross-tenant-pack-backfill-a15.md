# TP-2026-02-07-cross-tenant-pack-backfill-a15

- Название/цель: Закрыть остаточные gap'ы после merge по трём направлениям: (1) full negative cross-tenant test matrix для webhook/outbox/audit/provider, (2) de-demoization runtime adapter без implicit зависимости на `demo_salon`, (3) авто-обновление branch RAG metadata после publish без ручного `ops/backfill_branch_rag.py`.
- Canon refs: `STATE.md` (NOW/gaps multi-tenant), `SPECS/MULTI_TENANT.md` (tenant isolation, branch-RAG strict), `AGENTS.md` (P0/P1 invariants), `docs/IMPERIUM_DECISIONS.yaml` (DEC-024, pack/runtime direction).
- Invariant:
  - Fail-closed tenant isolation не ослабляется.
  - FACT/COLLECT/HANDOFF и decision_meta/trace без поведенческой регрессии.
  - Publish flow не требует manual backfill step для branch metadata consistency.
- Scope:
  - Добавить/расширить тесты, покрывающие негативные cross-tenant сценарии по критичным поверхностям.
  - Убрать direct runtime зависимость `pack_runtime_default` от `demo_salon_knowledge` как implicit default entrypoint.
  - Встроить publish-triggered branch metadata reindex/backfill в runtime publish path.
- Out of scope:
  - Новый onboarding orchestration pipeline.
  - Физическая изоляция DB/schema-per-tenant.
  - Добавление второй вертикали packs.
- Touch-list (files/tables):
  - `truffles-api/tests/test_branch_routing_instance.py`
  - `truffles-api/tests/test_provider_gateway_integration.py`
  - `truffles-api/tests/test_audit_service.py`
  - `truffles-api/tests/test_outbox_payload_contract.py` (при необходимости)
  - `truffles-api/app/services/pack_runtime_default.py`
  - `truffles-api/app/services/pack_runtime_service.py` (если нужно wiring)
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/services/knowledge_service.py` (если нужно publish hook)
  - `STATE.md`
- Plan:
  1) Audit текущего кода на предмет незакрытых пунктов 2/3/4.
  2) Дособрать cross-tenant negative test matrix до явного покрытия webhook/outbox/audit/provider.
  3) Refactor runtime default adapter to neutral entrypoint (no implicit demo import coupling).
  4) Добавить publish-time автоматический branch metadata reindex/backfill.
  5) Прогнать targeted checks/tests, зафиксировать evidence и обновить `STATE.md`.
- DoD:
  - Есть явная test-matrix с негативными кейсами tenant mismatch forbidden для webhook/outbox/audit/provider.
  - `pack_runtime_default` больше не зависит на `demo_salon_knowledge` как default implementation import.
  - После publish выполняется автоматический branch metadata backfill/reindex шаг (без ручного ops script).
  - Целевые тесты зелёные.
- Checks:
  - `ruff check truffles-api/app/services/pack_runtime_default.py truffles-api/app/services/knowledge_registry_service.py truffles-api/tests/test_branch_routing_instance.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_audit_service.py`
  - `pytest -q truffles-api/tests/test_branch_routing_instance.py truffles-api/tests/test_provider_gateway_integration.py truffles-api/tests/test_audit_service.py`
  - `pytest -q truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_knowledge_runtime.py`
- Evidence:
  - `/tmp/pytest_cross_tenant_matrix_20260207_a15.txt`
  - `/tmp/pytest_pack_runtime_dedemo_20260207_a15.txt`
  - `/tmp/pytest_publish_backfill_auto_20260207_a15.txt`
  - `STATE.md` запись (DONE + evidence).
- Rollback:
  - Revert PR commit(s).
- No-go:
  - Не менять бизнес-тексты/правила принятия решений в webhook flow.
  - Не вносить runtime fallback на guessed tenant context.
  - Не трогать prod data вручную для «красивого evidence».
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-07-cross-tenant-pack-backfill-a15`
  - Worktree: `/home/zhan/worktrees/2026-02-07-cross-tenant-pack-backfill-a15`
  - Base: `origin/main`
  - Merge policy: PR -> main после green checks.
  - Cleanup: `scripts/session_end.sh --status done` после merge.
- Риски/блокеры:
  - Возможен скрытый coupling pack runtime; покрываем targeted import tests.
  - Возможны flaky integration tests; держим запуск узким и deterministic.
