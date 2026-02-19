# TP-2026-02-19-wave3-marketing-full-a140

- Название/цель: Довести Wave 3 Marketing до рабочего продукта в Console Plane: UI кампаний, delivery diagnostics и reply-context в decision meta/trace без нарушения outbox safety.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `TECH.md`, `docs/TASK_PACKAGES/TP-2026-02-18-wave3-marketing-mvp-control-plane-a88.md`.
- CA_ID: N/A.

## Invariant
- Массовые отправки только через `dry_run -> confirm_send=true -> execute`.
- Никаких cross-tenant/cross-branch leakage.
- Reply после campaign-сообщения должен сохранять context в `decision_meta/decision_trace`.

## Scope
- Backend:
  - endpoint diagnostics по campaign deliveries (summary + status split + sample failures),
  - safe retry для failed deliveries конкретной кампании,
  - явная запись marketing context в inbound decision meta/trace при reply.
- Frontend:
  - страница/панель Marketing с list/create/preview/execute,
  - diagnostics блок по campaign,
  - компактная UX интеграция в текущий ConsoleShell.
- Docs/canon:
  - `STATE.md` update с FACT/GAP и evidence,
  - session artifacts.

## Out of scope
- AB testing/автооптимизация.
- Полноценная consent/legal automation.
- Глобальный redesign Console IA.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_console_marketing_campaigns.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/migrations/*` (только при необходимости)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/**`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `STATE.md`

## Plan
1. Добавить backend diagnostics/retry contract для campaign deliveries.
2. Добавить reply-context wiring для marketing inbound в decision meta/trace.
3. Реализовать UI flow Marketing (list/create/preview/execute + diagnostics).
4. Синхронизировать OpenAPI/type client.
5. Прогнать checks и зафиксировать evidence + update `STATE.md`.

## DoD
- Platform/Owner/Admin могут управлять кампанией из UI: create, preview, execute.
- Есть diagnostics endpoint/UI с breakdown `queued/sent/failed/replied` и sample failures.
- Есть retry endpoint для failed deliveries с idempotency-safe поведением.
- Inbound reply на campaign message отражает marketing context в `decision_meta` и `decision_trace`.
- OpenAPI/client types синхронизированы, тесты зелёные.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/routers/webhook/decision.py`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_console_marketing_campaigns.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_console_marketing_campaigns.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "marketing or campaign"`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

## Evidence
- PR URL.
- API examples для diagnostics/retry/create/preview/execute.
- Тест-выводы.
- `decision_meta` + `decision_trace` example для campaign reply.
- `STATE.md` update с FACT/GAP.

## Rollback
- Revert PR commits.
- Disable marketing UI route from nav if needed.
- Keep execute gated by `confirm_send=true`.

## No-go
- Нельзя отправлять без preview/confirm.
- Нельзя принимать feature без reply-context evidence.
- Нельзя ослаблять RBAC/branch scope.

## Риски/блокеры
- Большой `console.py` повышает риск регрессий.
- Внешние CI/live env могут быть flaky.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-19-wave3-marketing-full-a140`
- Worktree: `/home/zhan/worktrees/2026-02-19-wave-canon-context-marketing-mvp-a140`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase), PR to `main`.
- Cleanup: Brain/Top Architect после merge.
