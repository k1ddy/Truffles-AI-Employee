# TP-2026-02-15-owner-admin-wave8-incident-control-a88

- Название/цель: Wave-8 (Owner/Admin + Platform Admin) — добавить единый incident/diagnostics контур для outbox/provider проблем с безопасными следующими шагами (`diagnose -> dry-run -> execute`) вместо слепых retry.
- Canon refs: `STATE.md` NOW/GAP (`guard_status=critical`, `outbox_backlog` critical), `docs/REPORTS/2026-02-15-owner-admin-wave7-fact-os-v1.md`, `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`, `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`, `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`.

## Invariant
- Не ослаблять RBAC: `platform_admin` видит весь флот, `owner/admin` только свой scope.
- Не запускать destructive действия без явного шага подтверждения (минимум dry-run перед execute).
- Не выдавать выдуманные причины инцидентов: только факт-основанные статусы с `source/as_of`.

## Scope
- Backend:
  - Ввести API-инциденты для Console Plane:
    - platform feed (fleet scope),
    - owner feed (client scope),
    - owner/admin remediation recommendations с явными runbook шагами.
  - Добавить классификацию причин outbox-очереди:
    - provider unavailable / auth / rate limit / config drift / unknown.
  - Добавить suggested actions на основе существующих jobs (`outbox_process`, `integration_reconcile`, `heal`) в безопасном формате `dry_run_first`.
- Frontend:
  - Добавить в Ops и бизнес-страницы секцию инцидентов с понятными русскими терминами:
    - проблема,
    - вероятная причина,
    - что делать сейчас,
    - что делать дальше.
  - Отобразить ограничение scope по роли (fleet vs business).
- Tests/Contracts:
  - Обновить `openapi.v1`,
  - покрыть новые endpoint'ы и role-scoping тестами.

## Out of scope
- Автоматический mass execute remediation по всему флоту.
- Новая state machine outbox.
- Изменение core LLM decision pipeline.

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_owner_admin.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_rbac.py`
- `truffles-api/tests/test_console_fleet_attention.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/app/business/page.tsx`
- `console-web/src/app/business/team-performance/page.tsx`
- `docs/REPORTS/2026-02-15-owner-admin-wave8-incident-control-v1.md` (new)
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-wave8-incident-control-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Создать session/worktree для wave-8 и зафиксировать сессионный лог.
2. Добавить backend incident schemas + classification + role-scoped endpoints.
3. Подключить suggested remediation actions через существующий jobs-layer (`dry_run_first`).
4. Обновить frontend (Ops + business surfaces) под новый incident contract.
5. Обновить OpenAPI + tests + report + STATE evidence, затем открыть PR.

## DoD
- Platform Admin видит fleet incidents с причиной и actionable next steps.
- Owner/Admin видит только свои incidents и понятные действия без технического шума.
- Для каждого suggested action есть безопасный режим dry-run и объяснение.
- New API/role behavior покрыт тестами и не ломает текущие endpoints.
- Report + STATE зафиксированы с фактическим evidence.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/services/console_owner_admin.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/services/console_owner_admin.py truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_fleet_attention.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`

## Evidence
- API samples:
  - `/tmp/owner_admin_wave8_incidents_owner.json`
  - `/tmp/owner_admin_wave8_incidents_platform.json`
- Control loop:
  - `/tmp/owner_admin_wave8_t0.json`
  - `/tmp/owner_admin_wave8_t24.json`
- QA:
  - pytest/lint/build outputs,
  - report `docs/REPORTS/2026-02-15-owner-admin-wave8-incident-control-v1.md`.

## Rollback
- Revert wave-8 commit(s), вернуть предыдущий UI/API контур без incident-feed.

## No-go
- Нельзя auto-execute remediation без explicit user action.
- Нельзя выдавать recommendation без `reason_code` и `as_of`.
- Нельзя расширять доступ owner/admin до fleet-level данных.

## Risks/блокеры
- Возможен OpenAPI diff noise; держать изменения точечно в новых схемах/paths.
- Причины outbox могут быть смешанными, поэтому нужен confidence/unknown fallback без ложной точности.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-wave8-incident-control-a88`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-wave8-incident-control-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` after green checks.
- Cleanup: Brain/Top Architect after merge.
