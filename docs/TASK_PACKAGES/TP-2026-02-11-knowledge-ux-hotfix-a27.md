# TP-2026-02-11 Knowledge UX Hotfix (a27)

## Название/цель
Исправить вкладку `Knowledge` для Platform Admin: убрать ложную "пустоту" данных, сделать branch-change действия прозрачными и добавить устойчивость к gateway-сбоям.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/SESSIONS/SESSION-2026-02-10-knowledge-fleet-ux-a27.md`

## Invariant
- Контракт `knowledge/current|history|publish|rollback` не меняется.
- RBAC и branch-scope не ослабляются.
- Context switching (`X-Company-Id/X-Client-Id/X-Branch-Id`) остается deterministic.

## Scope
- `console-web/src/app/knowledge/page.tsx`
  - улучшить UX блока branch readiness (effective values + change intent);
  - исправить refresh/invalidation specialist queries при смене контекста;
  - добавить gateway-friendly retry состояние для 502/503/504.

## Out of scope
- Изменение backend API/DB схем.
- Изменение deploy pipeline.
- Полный редизайн Console.

## Touch-list
- `console-web/src/app/knowledge/page.tsx`
- `docs/TASK_PACKAGES/TP-2026-02-11-knowledge-ux-hotfix-a27.md`
- `docs/SESSIONS/SESSION-2026-02-11-knowledge-ux-hotfix-a27.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить deterministic сравнение branch overrides и effective previews.
2. Починить контекстный refresh для specialists при выборе клиента/филиала.
3. Добавить gateway error state + retry для Knowledge queries.
4. Проверить `console-web` lint/build.

## DoD
- Вкладка явно показывает что является branch override, а что effective fallback.
- Кнопка branch-change активируется только при реальном diff и причине.
- При 502/503/504 виден retry banner, UI не "зависает" в ложной пустоте.
- `npm run lint` и `npm run build` в `console-web` проходят.

## Checks
- `cd console-web && npm run lint`
- `cd console-web && npm run build`
- `git diff -- console-web/src/app/knowledge/page.tsx`

## Evidence
- `git diff --stat`
- вывод lint/build
- PR URL

## Rollback
- Revert commit с изменениями `console-web/src/app/knowledge/page.tsx`.

## No-go
- Не менять backend контракты и миграции.
- Не использовать `--no-verify`.

## Риски/блокеры
- Без live SSO-сессии нельзя полностью воспроизвести пользовательский сценарий вручную в браузере; компенсируется lint/build + существующими e2e smoke в CI.
