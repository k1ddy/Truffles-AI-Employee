# TP-2026-02-03-console-inbox-escalate-metrics

- Название/цель: Добавить Inbox action “Передать/Эскалировать” и метрики first_response/resolve в Consultant tab.
- Canon refs: `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`, `SPECS/CONTROL_PLANE.md` §9.3/9.4, `SPECS/ESCALATION.md`, `STRATEGY/REQUIREMENTS.md`.
- Invariant:
  - Handover state machine без дрейфа.
  - Outbox idempotency не ломается.
  - RBAC fail-closed.
- Scope:
  - UI action “Передать/Эскалировать” (используем existing return-to-bot endpoint или новый action по решению).
  - Добавить `first_response_at`, `resolved_at`, `resolution_time_seconds` в ConsoleCase.
  - Обновить OpenAPI + console-web UI.
- Out of scope:
  - RBAC/IA changes.
  - Team management и Integrations/Insights.
- Touch-list:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/schemas/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseDetailsPanel.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.generated.ts`
  - `truffles-api/tests/*`
- Plan:
  1. Зафиксировать семантику “Передать/Эскалировать” (return-to-bot или отдельный action).
  2. Добавить поля метрик в API schema/response.
  3. Обновить UI action bar + Consultant tab.
  4. Обновить OpenAPI + типы.
  5. Tests + lint.
- DoD:
  - Action доступен по роли и работает.
  - Метрики first_response/resolve отображаются.
  - Tests/lint зелёные.
- Checks:
  - `pytest -q truffles-api/tests/test_console_cases_helpers.py`
  - `npm --prefix console-web run generate:api`
  - `npm --prefix console-web run lint`
- Evidence:
  - Логи тестов/линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Новые handover статусы без тестов.
  - Обход RBAC.
- Риски/блокеры:
  - Semantics action “Передать/Эскалировать” уточнить до реализации.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-03-console-inbox-escalate-metrics-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-console-inbox-escalate-metrics-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
