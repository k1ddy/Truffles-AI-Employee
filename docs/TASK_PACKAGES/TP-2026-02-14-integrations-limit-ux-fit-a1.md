# TP-2026-02-14-integrations-limit-ux-fit-a1

- Название/цель: Устранить runtime-ошибку `limit must be between 1 and 100` на странице Integrations и переработать UX так, чтобы контент стабильно помещался на desktop/mobile без потери управляемости.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/GAP по Console Plane UX и provider ops), `STRATEGY/REQUIREMENTS.md`.

- Invariant:
  - Не ослаблять RBAC и tenant-scope ограничения.
  - Не возвращать execute-операции provider lifecycle обратно в `Integrations` (workspace-first сохраняется).
  - API backend контракты не менять.

- Scope:
  - Исправление некорректных `limit` в запросах Integrations UI.
  - UX-упрощение страницы `Integrations` (компоновка, читаемость, вмещаемость).
  - Актуализация smoke e2e assertions при необходимости.

- Out of scope:
  - Редизайн всего Console Plane.
  - Изменения бизнес-логики backend/onboarding/go-live.
  - Миграции БД.

- Touch-list:
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/e2e/smoke.spec.ts` (если потребуется)
  - `docs/SESSIONS/SESSION-2026-02-14-integrations-limit-ux-fit-a1.md`
  - `docs/SESSION_INDEX.md`

- Plan:
  1. Репрод ошибки и фиксация источника (`limit`).
  2. Исправление query limits и безопасная деградация для больших fleets.
  3. UX-перекомпоновка экрана (desktop/mobile fit) с сохранением data-testid контрактов.
  4. Локальные проверки (lint/build + целевые тесты), визуальная проверка скриншотами.

- DoD:
  - Ошибка `limit must be between 1 and 100` больше не воспроизводится.
  - На desktop/mobile страница читаема и пригодна для операционного управления.
  - Ключевой поток перехода в workspace сохранён.
  - Проверки проходят.

- Checks:
  - `cd console-web && npm run lint`
  - `cd console-web && npm run build`
  - `pytest -q truffles-api/tests/test_console_integrations_registry.py -q`
  - `cd console-web && npm run test:e2e -- --grep \"navigate from Integrations row to Company Workspace\"`

- Evidence:
  - Команды проверок и их результат.
  - Скриншоты desktop/mobile до/после.
  - PR URL + diff.

- Rollback:
  - Revert коммита(ов) этой задачи.

- No-go:
  - Не добавлять backend-хардкоды для компенсации UI-ошибок.
  - Не ломать существующие `data-testid` без обновления e2e.

- Риски/блокеры:
  - Ограничение API на `limit<=100` может требовать поэтапной пагинации для очень больших списков.
  - E2E в локали может зависеть от auth/env, при недоступности фиксируем как BLOCKED с логом.
