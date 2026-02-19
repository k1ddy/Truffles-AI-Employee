# TP-2026-02-18-wave0-outbox-unblock-a101

- Название/цель: Wave 0.2 outbox unblock. Убрать runtime-блокер вычитки `PENDING` без `conversation_id` и добавить безопасный ops-механизм архивирования старого pending-tail через `dry_run -> execute`.
- Canon refs: `STATE.md` NOW/GAP (runtime unhealthy/outbox critical), `docs/REPORTS/2026-02-18-wave0-integrity-outbox-baseline-a88.md`, `AGENTS.md` (Wave 0 stop-the-line).

## Invariant
- Не ломаем текущий outbox retry/idempotency контракт.
- Не трогаем billing/remediation логику (`expected_external_block`) и не смешиваем её с runtime fix.
- Любые архивные действия только через явный ops-параметр (по умолчанию выключено).

## Scope
- `claim_pending_outbox_batches`: поддержка `PENDING` с `conversation_id IS NULL`.
- Worker/admin/outbox-service path: явное включение обработки `conversation_id IS NULL`.
- Console ops outbox job:
  - диагностический dry-run split (`pending_with_conversation` / `pending_without_conversation` / `pending_older_than_7d`),
  - execute-архивирование старого pending-tail по age-параметру.

## Out of scope
- Targeted repair `manual_revert:invalid_tenant_context_contract`.
- Новые anti-repeat guards/изоляция test-scope в enqueue-runtime.
- Маркетинг-волны (Wave 3/4/5).

## Touch-list
- `truffles-api/app/services/outbox_service.py`
- `truffles-api/app/workers/outbox.py`
- `truffles-api/app/routers/outbox_service.py`
- `truffles-api/app/routers/admin.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_outbox_service_app.py`
- `truffles-api/tests/test_outbox_service_claim.py`
- `truffles-api/tests/test_console_ops_jobs.py`

## Plan
1. Починить service-claimer для `conversation_id IS NULL` и добавить архивирование pending-tail helper.
2. Протянуть include-flag в runtime entrypoints (worker/admin/outbox-service).
3. Расширить Console ops `outbox_process` dry-run/execute для archive-tail.
4. Добавить/обновить unit tests.
5. Прогнать compile + pytest + ruff и зафиксировать evidence.

## DoD
- `outbox_process` может забирать `PENDING` без `conversation_id`.
- Ops job dry-run показывает split pending-tail и preview архивирования.
- Ops job execute умеет архивировать старый pending-tail по параметрам.
- Тесты зелёные по затронутому контуру.

## Checks
- `python3 -m py_compile truffles-api/app/services/outbox_service.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/tests/test_outbox_service_claim.py truffles-api/tests/test_outbox_service_app.py truffles-api/tests/test_console_ops_jobs.py`
- `pytest -q truffles-api/tests/test_outbox_service_claim.py truffles-api/tests/test_outbox_service_app.py truffles-api/tests/test_console_ops_jobs.py`
- `ruff check truffles-api/app/services/outbox_service.py truffles-api/app/routers/console.py truffles-api/app/workers/outbox.py truffles-api/app/routers/outbox_service.py truffles-api/app/routers/admin.py truffles-api/tests/test_outbox_service_claim.py truffles-api/tests/test_outbox_service_app.py truffles-api/tests/test_console_ops_jobs.py`

## Evidence
- Локальные test/compile/ruff output.
- Post-fix live probes: `curl https://console.truffles.kz/api/health/full`, `ops/console_platform_admin_kpi_snapshot.py`, SQL breakdown по outbox reason/age.
- Запись в `STATE.md` делает Brain/Top Architect.

## Rollback
- Временный rollback через params: `include_without_conversation=false` и `archive_pending_older_than_hours=0` в ops job.
- Кодовый rollback: revert этого TP-коммита.

## No-go
- Не удалять outbox rows физически.
- Не запускать массовое архивирование без dry-run evidence.
- Не менять бизнес-логику billing/manual_revert в этом TP.

## Branch / Worktree
- Branch: `feat/2026-02-18-wave0-outbox-unblock-a101`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave0-outbox-unblock-a101`
- Base ref: `origin/main` (`f40f8147` на старт)
- Merge policy: обычный PR в `main` после локальных checks + evidence.
- Cleanup: после merge удалить ветку/worktree.
