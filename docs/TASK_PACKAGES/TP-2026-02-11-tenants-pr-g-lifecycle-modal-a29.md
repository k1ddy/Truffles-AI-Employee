# TP-2026-02-11 Tenants PR-G Lifecycle Modal Flow (a29)

## Название/цель
Перевести lifecycle-действия клиента во вкладке `Tenants` на управляемый modal-flow с impact preview и явным audit trail, чтобы убрать риск/шум browser-паттернов и повысить операционную управляемость.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants NOW/GAP, findings 2026-02-11)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-a-stabilization-a27.md`
- `docs/TASK_PACKAGES/TP-2026-02-11-tenants-pr-d-templates-readiness-a27.md`

## Invariant
- RBAC и tenant-isolation не ослабляются.
- Lifecycle write-contract backend не меняется (`archive/restore` endpoints и коды ошибок).
- Деструктивные действия остаются только с явным подтверждением.

## Scope
- Frontend `Tenants`: заменить inline lifecycle panel на modal-flow.
- Добавить impact preview в модалке (кто клиент, текущий lifecycle, ожидаемое состояние, причина).
- Добавить видимый audit trail блока для последнего lifecycle действия в карточке клиента.
- Обновить smoke e2e и аудит-документацию.

## Out of scope
- Миграции БД и новый backend audit endpoint.
- Полный редизайн страницы `Tenants`.
- Массовые lifecycle операции (bulk archive/restore).

## Touch-list
- `console-web/src/app/tenants/page.tsx`
- `console-web/e2e/smoke.spec.ts`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/SESSIONS/SESSION-2026-02-11-tenants-pr-g-lifecycle-modal-a29.md`
- `docs/SESSION_INDEX.md`

## Git/Branch/Worktree
- Branch: `feat/2026-02-11-tenants-pr-g-lifecycle-modal-a29`
- Worktree path: `/home/zhan/worktrees/2026-02-11-tenants-pr-g-lifecycle-modal-a29`
- Base ref: `origin/main`
- Merge policy: merge commit via PR
- Cleanup: Brain/Top Architect после merge

## Plan
1. Вынести lifecycle draft state в modal state machine с безопасным open/close/reset.
2. Добавить lifecycle modal с impact preview и обязательной причиной + confirm checkbox.
3. Добавить audit trail summary в карточку клиента (последнее действие/время/статус по фактическим данным UI).
4. Обновить e2e smoke на modal selectors и happy-path UX checks без destructive completion.
5. Обновить `tenants.md` по новому UX-контракту.

## DoD
- Lifecycle action инициируется только через modal, без browser prompt/confirm.
- В модалке есть impact preview и явные поля подтверждения.
- Карточка клиента показывает понятный audit trail блок после действия.
- Tenants smoke сценарии зелёные.

## Checks
- `scripts/session_check.sh`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz E2E_USE_STORAGE_STATE=1 E2E_USERNAME=admin E2E_PASSWORD=admin npx --prefix console-web playwright test console-web/e2e/smoke.spec.ts --project=chromium --grep "Tenants"`

## Evidence
- PR URL
- `git status -sb`
- `git diff --stat`
- вывод checks (lint/build/e2e)
- обновлённые docs/session artifacts

## Rollback
- `git revert` commit(ы) PR-G по touch-list.

## No-go
- Не менять backend lifecycle endpoints и их semantics.
- Не вводить скрытые auto-actions без подтверждения оператора.
- Не использовать browser-native `prompt/confirm`.

## Риски/блокеры
- Риск визуальной перегрузки карточки клиента.
- Митигация: компактная модалка, минимальный audit trail блок, устойчивые `data-testid`.
