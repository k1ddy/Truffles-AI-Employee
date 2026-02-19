# TP-2026-02-19-wave-canon-context-marketing-mvp-a140

- Название/цель: Закрыть пакет `1-4` из текущего управленческого запроса: восстановить канон wave-статусов, убрать дубли смысла в context header, зафиксировать явный режим данных, и довести Wave 3 Marketing MVP до узкого исполняемого контракта.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `TECH.md`, `docs/TASK_PACKAGES/TP-2026-02-18-wave3-marketing-mvp-control-plane-a88.md`.
- CA_ID: N/A.

## Invariant
- Контракт решения по user-turn не ломаем: `FACT/COLLECT/HANDOFF`.
- Никаких cross-tenant/cross-branch leakage в маркетинговой рассылке.
- Канон (`STATE.md`, session logs) не должен расходиться с фактическим PR/runtime состоянием.

## Scope
- Canon/governance:
  - убрать conflict markers в `STATE.md`,
  - синхронизировать статусы wave session logs с фактом merged/active.
- Console UX context:
  - зафиксировать разделение семантики шапки (`Компания/Клиент/Филиал`) и индикатора режима данных,
  - показать компактный индикатор в одном уровне с шапкой без лишней высоты.
- Indicator copy:
  - текст: `Режим данных: Активные`,
  - tooltip/help: `Архив и деактивированные в Тенантах`.
- Wave 3 narrow MVP:
  - branch-scoped campaign create/list,
  - preview (`dry_run`) + explicit confirm + execute send,
  - no advanced segmentation/automation.

## Out of scope
- Полный redesign Console Plane.
- Wave 4/5 marketing follow-up.
- Массовая переработка router decomposition beyond needed touch points.

## Touch-list
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-02-18-wave*.md`
- `docs/SESSION_INDEX.md`
- `docs/REPORTS/*` (только при необходимости evidence/status report)
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/src/app/*` (если нужен компактный render-level перенос индикатора)
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/*` (минимально для Wave 3 orchestration)
- `truffles-api/migrations/*` (только если реально нужна новая таблица/поле)
- `truffles-api/tests/test_console_*.py`
- `console-web/e2e/platform-admin.spec.ts` (или целевые e2e smoke assertions)

## Plan
1. Поднять session/worktree и зафиксировать текущие факты wave status + runtime.
2. Починить канон: `STATE.md` conflicts, session status drift, индекс сессий.
3. Обновить UI контекст: четкая роль шапки + компактный индикатор с tooltip.
4. Реализовать Wave 3 narrow MVP (`dry_run -> confirm -> execute`, branch-scope only).
5. Добавить/обновить тесты по UI/API контракту.
6. Прогнать checks, собрать evidence, обновить session log и `STATE.md`.

## DoD
- `STATE.md` без конфликтных маркеров, и status narrative соответствует факту PR/runtime.
- Wave session logs для выполненных wave не остаются в `active` без причины.
- В шапке контекста нет дублирования смысла; индикатор компактный и читабельный.
- Индикатор показывает `Режим данных: Активные`, tooltip ведет к смыслу архива.
- Wave 3 MVP доступен и проходит контракт `dry_run -> confirm -> execute` на branch scope.
- По Wave 3 есть deterministic test coverage и evidence.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `pytest -q truffles-api/tests/test_console_fleet_attention.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/platform-admin.spec.ts --project=chromium --no-deps --reporter=list`
- `scripts/session_check.sh`

## Evidence
- PR URL + merged/active wave mapping.
- Runtime snapshot (`/api/health/full`) + KPI snapshot before/after if touched.
- Скриншот header+indicator до/после.
- API evidence for campaign `dry_run/confirm/execute`.
- Updated `STATE.md` facts + session logs + session index.

## Rollback
- Revert commits in feature branch.
- Для Wave 3 endpoint/UI: feature-flag disable path if needed.
- Вернуть предыдущий context render в одном revert commit.

## No-go
- Не принимать wave closure без фактического PR/test evidence.
- Не оставлять ambiguous copy (`Только активные`) без контекста режима.
- Не расширять Wave 3 сверх narrow MVP.

## Риски/блокеры
- Большой монолит `console.py` повышает риск регрессии при добавлении MVP endpoint.
- Несинхронизированные session artifacts могут потребовать доп. нормализации индекса.
- Внешние auth/runtime флуктуации могут давать flaky e2e на прод-URL.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-19-wave-canon-context-marketing-mvp-a140`
- Worktree: `/home/zhan/worktrees/2026-02-19-wave-canon-context-marketing-mvp-a140`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase), PR to `main`.
- Cleanup: Brain/Top Architect после merge.
