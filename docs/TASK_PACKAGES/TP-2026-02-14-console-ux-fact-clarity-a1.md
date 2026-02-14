# TP-2026-02-14-console-ux-fact-clarity-a1

- Название/цель: Пересобрать UX Console Plane для platform_admin так, чтобы вкладки и блоки были факт-ориентированными, русифицированными и понятными с первого просмотра; устранить проблемы вмещаемости (включая `InstanceID`).
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/GAP по Console UX + provider ops), `STRATEGY/REQUIREMENTS.md`.

- Invariant:
  - Execute-операции provider lifecycle остаются только в `Company Workspace`.
  - RBAC и tenant scope не ослабляются.
  - Backend контракты и схемы БД не меняются.

- Scope:
  - Фактический UX-аудит ключевых вкладок Console через скриншоты + проверку кода.
  - Переработка IA/копирайта и визуального представления в `Integrations` (и связанные элементы навигации при необходимости).
  - Исправление читаемости длинных технических значений (`InstanceID`, webhook fields).
  - Обновление smoke-покрытия при изменении тестовых маркеров.

- Out of scope:
  - Полный редизайн всех страниц консоли.
  - Изменение бизнес-логики onboarding/go-live.
  - Миграции БД.

- Touch-list:
  - `console-web/src/app/integrations/page.tsx`
  - `console-web/src/app/company-workspace/page.tsx` (при необходимости)
  - `console-web/src/components/ConsoleShell.tsx` (при необходимости)
  - `console-web/e2e/smoke.spec.ts` (при необходимости)
  - `docs/SESSIONS/SESSION-2026-02-14-console-ux-fact-clarity-a1.md`
  - `docs/SESSION_INDEX.md`

- Plan:
  1. Выполнить визуальный аудит вкладок (integrations/workspace/tenants/ops/settings/team) через скриншоты + код.
  2. Зафиксировать UX-проблемы: неинформативные вкладки, англоязычные термины, перегрузка, переполнение `InstanceID`.
  3. Внести правки IA/контента/верстки и упростить путь действий platform_admin.
  4. Прогнать проверки (lint/build/e2e smoke subset + backend integrations test), собрать evidence.

- DoD:
  - Вкладки/блоки объясняют “что это”, “что не так”, “что делать дальше”.
  - Критичные элементы на русском, без смешения терминов где не нужно.
  - `InstanceID` и длинные значения читаемы и не ломают layout.
  - Проверки проходят, скриншоты до/после приложены.

- Checks:
  - `cd console-web && npm run lint`
  - `cd console-web && npm run build`
  - `pytest -q truffles-api/tests/test_console_integrations_registry.py -q`
  - `cd console-web && npm run test:e2e -- --grep "@smoke"`

- Evidence:
  - Скриншоты вкладок до/после.
  - Логи проверок.
  - PR URL + diff.

- Rollback:
  - Revert коммита(ов) задачи.

- No-go:
  - Не добавлять декоративные элементы без операционной ценности.
  - Не скрывать факты ради “красивого” UI.
  - Не ломать существующий путь `Manage in Workspace`.

- Риски/блокеры:
  - Разнородные состояния тестовых данных могут искажать визуальный аудит; фиксируем mock/live отдельно.
