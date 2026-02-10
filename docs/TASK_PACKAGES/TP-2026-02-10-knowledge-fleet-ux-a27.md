# TP-2026-02-10 Knowledge Fleet UX (a27)

## Название/цель
Улучшить вкладку `Knowledge` для роли `platform_admin`: дать fleet-level навигацию и быстрые действия по подключенным компаниям, а также structured UX для обновления базовых знаний филиала (часы/услуги) без ручного raw JSON.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `docs/CONSOLE_AUDIT/pages/knowledge.md`
- `docs/CONSOLE_AUDIT/roles/platform_admin.md`

## Invariant
- Tenant isolation и RBAC не ослабляются.
- `Knowledge` publish/rollback safety flow сохраняется.
- Не меняем backend decision/runtime pipeline.

## Scope
- Frontend `Knowledge`:
  - добавить fleet control для `platform_admin` (client/branch selection + quick links);
  - добавить branch readiness блок (knowledge_tag/working_hours status + быстрый apply);
  - добавить structured draft builder для hours/services;
  - показать read-only список специалистов и связанный quick-link в Team.
- Использовать существующие API (`/admin/clients`, `/admin/branches`, `/admin/fleet/attention`, `/calendar/specialists`, `/admin/branch-changes/*`, `/knowledge/*`).

## Out of scope
- Новые backend endpoints.
- CRUD специалистов во вкладке `Knowledge`.
- Массовые bulk operations.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`

## Plan
1. Добавить platform-admin fleet panel в `Knowledge`.
2. Добавить branch readiness + safe apply через branch-change flow.
3. Добавить structured draft builder (hours/services) и связать с draft textarea.
4. Добавить read-only specialists snapshot + переход в Team.
5. Прогнать lint/build и подготовить PR.

## DoD
- Platform admin может выбрать client/branch и быстро перейти в контекст знаний.
- Branch readiness показывает ключевые поля и безопасно применяет изменения.
- Structured builder формирует draft без ручного raw JSON.
- Локальные `lint` и `build` проходят.

## Checks
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

## Evidence
- `git diff --stat`
- output `lint/build`
- PR URL

## Rollback
- Revert commit с изменениями `console-web/src/app/knowledge/page.tsx` и session docs.

## No-go
- Не менять `_legacy.py`.
- Не менять runtime webhook/decision core.
- Не трогать чужие измененные файлы в worktree.

## Риски/блокеры
- Возможный drift UX при большом размере страницы `knowledge`.
- Нет write API для специалистов в текущем контуре (оставлено как navigation to Team).
