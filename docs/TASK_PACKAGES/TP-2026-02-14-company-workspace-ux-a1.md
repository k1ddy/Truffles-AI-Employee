Название/цель:
- Упростить управление компаниями/филиалами в Console Plane для Platform Admin: понятный русскоязычный UX, компактные и фактические статусы, устойчивый мобильный рендер без деградации навигации.

Canon refs:
- AGENTS.md (one-issue flow, local-first checks)
- STATE.md NOW/GAP (Console onboarding + operations UX gaps)

Invariant:
- Не ломать существующие backend-контракты, hard-stop/go-live gate и provider-операции.
- Не снижать безопасность/tenant-boundaries.

Scope:
- UI/UX слоя `company-workspace`, `integrations`, `ConsoleShell`.
- Улучшение читаемости instance/webhook данных и навигации на мобильных/узких экранах.

Out of scope:
- Переписывание backend-архитектуры провайдера.
- Новые provider API интеграции с ChatFlow.

Touch-list:
- console-web/src/app/company-workspace/page.tsx
- console-web/src/app/integrations/page.tsx
- console-web/src/components/ConsoleShell.tsx
- console-web/src/types/api.generated.ts (если нужно)
- docs/SESSIONS/*
- docs/SESSION_INDEX.md

Plan:
1) Провести фактический UX-аудит по текущим страницам и выделить узкие места рендера/информативности.
2) Переработать Company Workspace: русификация ключевых action labels, компактные factual blocks, улучшение отображения длинных значений (instance_id/webhook).
3) Упростить Integrations/Fleet экран: явные сигналы и меньше когнитивной нагрузки в верхних блоках.
4) Усилить mobile nav resilience в ConsoleShell (избежать огромных svg/ломаной навигации при деградации CSS).
5) Прогнать lint/build + релевантные тесты.

DoD:
- Platform Admin может понять текущее состояние филиала и следующий шаг без чтения технического жаргона.
- Длинные идентификаторы не ломают layout и копируются из UI.
- Мобильная навигация не разваливается и не показывает гигантские иконки.
- Локальные проверки зелёные.

Checks:
- npm run lint (console-web)
- npm run build (console-web)
- pytest -q truffles-api/tests/test_console_integrations_registry.py truffles-api/tests/test_console_fleet_attention.py

Evidence:
- PR URL
- вывод lint/build/tests
- фактический diff

Rollback:
- Откат PR целиком (revert merge commit)

No-go:
- Хардкод данных клиента вместо фактов из API.
- Изменение backend-логики provider lifecycle в этом PR.

Риски/блокеры:
- Риск субъективного UX: минимизировать через факт-first структуру и явные состояния.
