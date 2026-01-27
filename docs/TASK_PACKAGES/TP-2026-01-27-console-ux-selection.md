# TP-2026-01-27 — Console UX: Selection Clarity + Knowledge Gating

- Название/цель: сделать выбор Company/Client/Branch понятным и быстрым, убрать лишний шум (branch filter в Cases) и
  добавить явное ветвление для Knowledge, чтобы не ловить BRANCH_SELECTION_REQUIRED/Failed to reach API.
- Invariant: RBAC/тенант‑изоляция и onboarding state machine не ослабляются; выбор филиала остаётся обязательным для
  knowledge; не менять CODEMAP.
- Scope:
  - UI‑сигналы/статусы при смене контекста (Company/Client/Branch).
  - Branch‑gating на странице Knowledge (явный выбор филиала, если требуется).
  - Рационализация фильтра филиала в Cases (скрывать если избыточен).
- Out of scope: изменение API/контрактов, миграции БД, локализация всего интерфейса (отдельный блок).
- Touch-list:
  - `console-web/src/components/ConsoleShell.tsx`
  - `console-web/src/app/knowledge/page.tsx`
  - `console-web/src/components/CaseList.tsx`
  - (возможный helper) `console-web/src/lib/selection.ts`
- Branch/Worktree/Base:
  - Branch: `feat/console-ux-selection`
  - Worktree: `/home/zhan/worktrees/console-ux-selection`
  - Base ref: `origin/main`
  - Merge policy: merge commit
  - Cleanup: удалить ветку + worktree после merge
- Plan:
  1) Добавить ясный индикатор смены контекста и подтверждение (loading/notice) в header.
  2) Knowledge: показать gate “Выберите филиал” при отсутствии выбранного branch_id, и рефетчить данные после выбора.
  3) Cases: скрыть branch‑filter, если контекст уже branch‑restricted или выбор филиала недоступен.
  4) Локальные проверки: lint (по необходимости) + smoke‑проверка UI.
- DoD:
  - Переходы Company/Client/Branch дают понятный UX (есть подтверждение/индикатор).
  - Knowledge не падает с BRANCH_SELECTION_REQUIRED, вместо этого показывает выбор филиала.
  - В Cases не дублируется branch‑filter в branch‑restricted режиме.
- Checks:
  - `npm --prefix console-web run lint` (если были UI‑изменения).
  - Ручной smoke в UI (Settings/Cases/Knowledge).
- Evidence:
  - Скрин/описание UI‑поведения (если нужно — в `docs/REPORTS/`).
  - CI run URL (после PR).
- Rollback: revert merge commit.
- No-go: не изменять RBAC/схемы/контракты, не запускать CI на docs‑only.
- Риски/блокеры:
  - Без выбранного branch_id Knowledge остаётся заблокированным (это корректно, но требует ясного UX).
