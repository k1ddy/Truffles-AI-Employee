# TP-2026-02-15-owner-admin-wave5-controls-a1

- Название/цель: Выполнить Wave-5 Owner/Admin control hardening после merge Wave-4: формализовать T+0/T+24 контроль, добавить impact KPI baseline/replay, дать guided remediation c rollback в UI и запустить декомпозицию owner/admin блока `console.py` без изменения контракта.
- Canon refs: `STATE.md` (NOW: runtime unhealthy/outbox critical), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-11 open), `docs/REPORTS/2026-02-15-owner-admin-wave4-action-loop-v1.md`, `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`.

## Invariant
- Не ослаблять RBAC/tenancy для owner/admin (`business:read`, `settings:write`).
- Не менять billing формулу и subscription accounting (`Business/Sales/BILLING_COUNTING.md`).
- Декомпозиция `console.py` только behavior-preserving (контракты API и тесты остаются зелёными).

## Scope
- Control loop v2:
  - дополнить runbook `OWNER_ADMIN_POSTMERGE_24H` чёткими T+0/T+24 шагами и criteria.
  - добавить KPI snapshot утилиту для owner/admin impact tracking (baseline vs replay).
- UI remediation:
  - в `Team Performance` добавить guided remediation state + rollback action после применения quick profile.
- Backend decomposition starter:
  - вынести owner/admin helper-логику из `truffles-api/app/routers/console.py` в отдельный модуль с минимальным diff.
- Docs/report:
  - обновить audit backlog и wave report с evidence по Wave-5.

## Out of scope
- Полный рефактор всего `console.py`.
- Новая billing/invoice модель.
- Изменение core логики processing outbox или handover SLA алгоритмов.

## Touch-list
- `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`
- `ops/console_owner_admin_kpi_snapshot.py` (new)
- `console-web/src/app/business/team-performance/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `truffles-api/app/services/console_owner_admin.py` (new)
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_owner_business.py`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave5-control-hardening-v1.md` (new)
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-wave5-controls-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Создать отдельную сессию/worktree от `origin/main`.
2. Добавить owner/admin KPI snapshot tool + обновить post-merge runbook под T+0/T+24.
3. Реализовать guided remediation + rollback в Team Performance UI.
4. Вынести owner/admin helper functions из `console.py` в `app/services/console_owner_admin.py` и подключить обратно.
5. Обновить тесты/доки, прогнать checks и зафиксировать evidence.

## DoD
- Есть явный T+0/T+24 runbook с fail-fast критериями и артефактами.
- Есть owner/admin KPI snapshot инструмент с baseline/replay выводом и JSON output.
- Team KPI remediation поддерживает rollback последнего quick profile без ручного ввода чисел.
- Owner/admin helper-блок частично вынесен из `console.py` в сервисный модуль, tests green.
- Обновлены audit/report документы под Wave-5.

## Checks
- `python3 -m py_compile ops/console_owner_admin_kpi_snapshot.py truffles-api/app/services/console_owner_admin.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_owner_admin.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`
- `python3 ops/console_owner_admin_kpi_snapshot.py --pretty --output /tmp/owner_admin_wave5_t0.json`

## Evidence
- KPI snapshots: `/tmp/owner_admin_wave5_t0.json`, `/tmp/owner_admin_wave5_t24.json` (when available), optional compare.
- Live control evidence: runbook command outputs with timestamps.
- Test/lint/build outputs + PR diff.
- Session log + report update.

## Rollback
- Revert Wave-5 commit(s): UI reverts to Wave-4 behavior, router keeps original in-file helper logic.

## No-go
- Нельзя менять API response schemas без обновления контракта и тестов.
- Нельзя добавлять unsafe shortcut bypass для settings write.
- Нельзя смешивать decomposition с функциональным redesign owner/admin flows.

## Risks/блокеры
- `console.py` остаётся большим: декомпозиция ограничена owner/admin helpers в этой волне.
- Runtime KPI в проде может быть noisy; сравнение только baseline/replay при одинаковом контуре.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-wave5-controls-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-wave5-controls-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после зелёных checks и evidence.
- Cleanup: Brain/Top Architect после merge.
