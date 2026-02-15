# TP-2026-02-15-owner-admin-wave7-fact-os-a1

- Название/цель: Wave-7 (Owner/Admin) — реализовать `Fact Contract Layer` для бизнес-KPI и запустить `Owner Operating System` (preview/apply/rollback/auto-check) как server-driven контур быстрых действий.
- Canon refs: `STATE.md` NOW/GAP (owner/admin backlog critical), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-11/12 open), `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`.

## Invariant
- Не ослаблять RBAC owner/admin/settings/business/subscription.
- Не ломать текущий контракт биллинга (`billable_messages` + evidence rows).
- Не вводить «магические» решения без traceable server evidence.

## Scope
- Fact Contract Layer:
  - добавить в owner/admin KPI единый факт-контракт: `kind=fact|estimate|missing`, `source`, `as_of`, `scope`, `sample_size`.
  - применить к `/business/summary`, `/subscription/summary`, `/business/data-trust`, `/business/team-performance`.
  - исправить `/health`: убрать hardcoded `redis="connected"`, вернуть `unknown/degraded` по факту.
  - обновить UI owner/admin страниц для отображения fact-confidence статуса.
- Owner Operating System:
  - добавить server-driven endpoint preview/apply для трёх режимов: `capture_leads`, `stable_quality`, `team_protection`.
  - сохранять серверный rollback snapshot и возвращать operation result.
  - добавить server auto-check (T+24-like impact snapshot linkage) для применённого режима.
  - подключить Settings/Team UI к новому server-driven контуру.

## Out of scope
- Полный fleet scheduler/cron для всех компаний.
- Полный redesign Console IA.
- Изменение policy-core поведения LLM.

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_owner_admin.py`
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_console_rbac.py` (при необходимости)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/business/page.tsx`
- `console-web/src/app/subscription/page.tsx`
- `console-web/src/app/business/data-trust/page.tsx`
- `console-web/src/app/business/team-performance/page.tsx`
- `console-web/src/app/settings/page.tsx`
- `console-web/e2e/owner-admin-business.spec.ts`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave7-fact-os-v1.md` (new)
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-02-15-owner-admin-wave7-fact-os-a1.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Создать session/worktree и зафиксировать TP.
2. Реализовать backend fact-contract schema + payload across owner/admin summary endpoints.
3. Реализовать server-driven owner operation modes (preview/apply/rollback/auto-check evidence).
4. Обновить frontend owner/admin surfaces под факт-контракт и server operations.
5. Обновить tests/contracts/docs, собрать runtime evidence, открыть PR.

## DoD
- Все owner/admin KPI endpoints возвращают fact-metadata для ключевых чисел.
- `/health` больше не показывает фиктивный Redis status.
- Goal-mode работает через серверный preview/apply/rollback API, а не только client presets.
- Есть test coverage для новых схем/роутов и UI smoke не деградирует.
- Доки/STATE/STRUCTURE/session синхронизированы.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_owner_admin.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_owner_admin.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `npm --prefix console-web run test:e2e:smoke -- --list`

## Evidence
- `/tmp/owner_admin_wave7_t0.json`
- `/tmp/owner_admin_wave7_t24.json`
- `/tmp/owner_admin_wave7_apply_preview.json`
- `/tmp/owner_admin_wave7_apply_result.json`
- `docs/REPORTS/2026-02-15-owner-admin-wave7-fact-os-v1.md`

## Rollback
- Revert wave-7 commit(s) to previous owner/admin wave-6 behavior.

## No-go
- Нельзя помечать расчётные значения как `fact`.
- Нельзя хранить rollback snapshot только в клиентском state.
- Нельзя менять бизнес-формулу биллинга под UI.

## Risks/блокеры
- Понадобится аккуратное изменение OpenAPI/TS-типов без массового регенерационного шума.
- Возможен drift в e2e тестах после UI contract upgrade.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-wave7-fact-os-a1`
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-wave7-fact-os-a1`
- Base ref: `origin/main`
- Merge policy: PR -> `main` after green checks.
- Cleanup: Brain/Top Architect after merge.
