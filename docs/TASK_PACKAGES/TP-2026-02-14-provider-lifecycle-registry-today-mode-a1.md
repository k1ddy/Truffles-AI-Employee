Название/цель:
- Закрыть P0-дыры управления Platform Admin: (1) единый Provider Lifecycle Registry по филиалам и (2) режим «Сегодня» в Integrations/Workspace с next action + SLA дедлайном.

Canon refs:
- AGENTS.md (local-first, one-issue flow, evidence)
- STATE.md NOW/GAP (Console onboarding + provider lifecycle + UX gaps)

Invariant:
- Не ломать tenant-access checks, hard-stop go-live gates и существующие provider-операции.
- Не менять поведение execution-операций без подтверждений.

Scope:
- Backend read-model/endpoint для provider lifecycle в Console API.
- Frontend Integrations/Workspace UX: режим «Сегодня», только проблемные филиалы, next action, SLA deadline, быстрый переход в Workspace.

Out of scope:
- Интеграция внешнего ChatFlow API (его нет в контракте).
- Полная архитектурная перестройка Console Plane.

Touch-list:
- truffles-api/app/schemas/console.py
- truffles-api/app/routers/console.py
- truffles-api/tests/test_console_integrations_registry.py
- contracts/console_api/openapi.v1.yaml
- console-web/src/lib/api-client.ts
- console-web/src/types/api.generated.ts
- console-web/src/app/integrations/page.tsx
- console-web/src/app/company-workspace/page.tsx
- docs/SESSIONS/*
- docs/SESSION_INDEX.md

Plan:
1) Добавить backend read-model `ProviderLifecycleItem` + endpoint `/admin/provider-lifecycle` с limit/cursor/scope/only_problematic.
2) Добавить вычисление `next_action`, `sla_deadline_at`, `sla_state`, `blockers` на базе фактов integration+binding.
3) Добавить backend тесты пагинации, фильтров и поля SLA/next_action.
4) Обновить OpenAPI/типы.
5) Добавить в Integrations режим «Сегодня»: фильтр проблемных, KPI «требует действий», колонка next action + SLA + кнопка «Открыть в Workspace».
6) Добавить в Company Workspace компактный «Сегодня по филиалу» блок.
7) Прогнать тесты/линт/билд.

DoD:
- Platform Admin видит единый lifecycle-факт по филиалам без ручного склеивания из разных блоков.
- В Integrations есть явный режим «Сегодня» с actionable списком и SLA.
- В Workspace видно текущий blocker/дедлайн по выбранному филиалу.
- Локальные проверки зелёные.

Checks:
- pytest -q truffles-api/tests/test_console_integrations_registry.py
- pytest -q truffles-api/tests/test_console_fleet_attention.py
- npm run generate:api (console-web)
- npm run lint (console-web)
- npm run build (console-web)

Evidence:
- PR URL
- команды проверок + статус
- git diff --stat

Rollback:
- Revert merge commit PR.

No-go:
- Хардкод per-demo логики.
- Ослабление security/access checks.

Риски/блокеры:
- SLA расчет эвристический (нет провайдерского API времени истечения webhook), значит дедлайны должны быть явно помечены как системные дедлайны контроля.
