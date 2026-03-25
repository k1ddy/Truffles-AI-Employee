# TP-2026-02-17-platform-ux-root-a88

- Название/цель: Устранить ключевую UX-путаницу в Console Plane для multi-tenant ролей и ускорить навигацию UI без изменения бизнес-логики.
- Canon refs: `AGENTS.md`, `STATE.md` (GAP по Console UX/branch visibility), `STRUCTURE.md`, `SPECS/SYSTEM_REFERENCE.md`.
- Invariant: Не менять RBAC/доступы, не менять контракт `FACT/COLLECT/HANDOFF`, не менять серверную фильтрацию active entities.
- Scope:
  - Улучшить рендер контекст-бара (company/client/branch labels) для случаев без явного selected id.
  - Добавить явную подсказку для `platform_admin` о том, что отображаются только активные сущности.
  - Убрать full reload из боковой навигации Console.
  - Снизить лишние refetch при фокусе окна для `/console/v1/me`.
- Out of scope:
  - Изменения backend-правил фильтрации клиентов/филиалов.
  - Миграции БД.
  - Редизайн страниц бизнес-ниш.
- Touch-list (файлы/таблицы):
  - `console-web/src/components/ConsoleShell.tsx`
  - Документы сессии: `docs/TASK_PACKAGES/*`, `docs/SESSIONS/*`, `docs/SESSION_INDEX.md`
- Plan (1..N):
  1. Подтвердить текущий UX-дефект в `ConsoleShell` на path контекста branch/client.
  2. Внести UI-правки для fallback label и platform-admin hint.
  3. Перевести navigation click с full reload на client-side route push.
  4. Запустить локальные проверки (`lint`, `build`) и зафиксировать evidence.
- DoD:
  - При `selected_branch_id=null` и одном доступном филиале UI не показывает `—`.
  - Platform Admin видит явную подсказку о фильтре активных сущностей.
  - Навигация в sidebar не делает `window.location.assign`.
  - `npm run lint` и `npm run build` в `console-web` проходят.
- Checks:
  - `cd console-web && npm run lint`
  - `cd console-web && npm run build`
- Evidence:
  - `git diff --stat` для `ConsoleShell.tsx`
  - Логи `npm run lint` и `npm run build` (успешные)
  - Обновление session log + index в текущем worktree
- Rollback:
  - Выполнять `git revert` по фактическому hash коммита из PR после merge.
- No-go:
  - Не подменять backend-контракты фиктивными UI-данными.
  - Не убирать существующие RBAC guards.
  - Не добавлять hardcode под demo-pack.
- Риски/блокеры:
  - E2E через Keycloak может идти в remote origin и не отражать локальный UI-бандл; основная валидация для этой правки выполняется через lint/build + code review.
