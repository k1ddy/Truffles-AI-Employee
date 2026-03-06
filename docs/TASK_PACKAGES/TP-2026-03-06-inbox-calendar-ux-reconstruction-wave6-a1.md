# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE5-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-A1

## Название/цель
Добавить операторские case actions, которых не хватает для реальной работы очереди: `reassign`, `snooze`, `reopen`, не смешивая этот блок с bulk-операциями и не создавая новый рабочий экран.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/CaseConversation.tsx`
  - `console-web/src/components/CaseDetailsPanel.tsx`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - Сейчас case actions ограничены `take`, `resolve`, `return`.
  - В `state_service.py` есть внутренний reopen helper, но нет публичного operator endpoint для manual reopen.
  - Для bounded `snooze` можно переиспользовать `handover.meta` и wave5 queue semantics, без новой таблицы и без WhatsApp-специфичного `human-lock` контракта.
  - Для reassignment в runtime нет case-scoped assignee endpoint; UI не знает, кому можно передать кейс.

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk ticket assignment triggers pending on-hold solved reopened official`
- **Date/time (local):** `2026-03-06T07:35:00+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408838166554-About-ticket-assignment-and-triggers`
  - `https://support.zendesk.com/hc/en-us/articles/4408843029658-About-open-versus-pending-and-on-hold-tickets`
  - `https://developer.zendesk.com/documentation/ticketing/reference-guides/ticketing-api/ticket-fields/#custom-ticket-statuses`
- **Ready solutions found:** зрелый helpdesk различает `open/pending/on-hold/solved/reopened`, reassignment — это отдельное действие ownership, а deferred work должен явно выходить из immediate-attention state.
- **Decision (`reuse/integrate/build`):** `integrate` — переиспользовать существующие `handover`, `handover.meta`, `state_service`, audit events и текущую Inbox карточку, добавив только недостающие bounded action endpoints и UI controls.
- **Rejected options:** новый queue-engine или отдельный экран для диспетчеризации как способ добавить эти действия.
- **Source quality:** high-signal source = official Zendesk support/developer documentation.

## Root cause (mandatory)
- **Symptom:** менеджер может взять, закрыть или вернуть кейс боту, но не может корректно передать его другому человеку, отложить разбор или вручную вернуть закрытый кейс в работу.
- **Minimal reproduction:** открыть активную или закрытую заявку в `Заявках`; попытаться передать ответственность коллеге, убрать кейс из очереди до конкретного времени или переоткрыть решенный кейс.
- **Evidence:** текущие endpoints в `console.py`, ограниченные кнопки в `CaseConversation.tsx`, отсутствие case-scoped assignee source, наличие только внутреннего `_reopen_handover`.
- **Five Whys:**
  1. Почему операторский поток ломается? Потому что ownership lifecycle неполный.
  2. Почему это не решается существующими кнопками? Потому что `take/resolve/return` покрывают только часть сценариев.
  3. Почему нельзя просто добавить bulk сразу? Потому что сначала нужен корректный single-case контракт и понятные состояния.
  4. Почему это влияет на бизнес? Потому что кейсы застревают на одном операторе, висят в очереди или закрываются без управляемого возврата.
  5. Почему это нельзя откладывать? Потому что это прямой remaining gap из исходного ТЗ по управлению заявками и записями.
- **Root cause statement:** отсутствует полноценный single-case operator action contract для ownership/defer/reopen в рамках уже существующей модели handover.
- **Fix mechanism:** добавить bounded single-case endpoints и UI actions для `reassign`, `snooze`, `reopen`, переиспользуя текущие state/handover.meta/audit механизмы.

## Reuse-first plan (mandatory)
- **Reuse:** `Handover`, `handover.meta`, `Conversation.state`, `state_service`, `record_audit_event`, current Inbox detail surface.
- **Integrate:** добавить case-scoped assignee options и operator action endpoints в текущий console API.
- **Build only if needed:** минимальные request/response schemas и UI controls; без новой таблицы и без bulk engine.

## Invariant
- Не смешивать single-case actions с bulk operations.
- Не добавлять новый top-level workspace.
- Не ломать текущие `take/resolve/return` flows.
- `Snooze` должен убирать кейс из immediate-attention semantics, а не просто переименовывать статус.
- `Reopen` не должен silently создавать новый несвязанный case.

## Scope
- `Part A1 (backend contract; mandatory if split)`:
  - case-scoped assignee options endpoint;
  - single-case action endpoints for `reassign`, `snooze`, `reopen`;
  - reuse `handover.meta` + wave5 `snoozed` semantics for `snooze` and `state_service` for `reopen`.
- `Part A2 (frontend surfaces; mandatory if split)`:
  - buttons/dialog controls in `CaseConversation`;
  - updated detail copy in `CaseDetailsPanel`;
  - inspect-case coverage for new operator controls.
- `Part B (separate future block, not in this TP)`:
  - bulk operations and supervisor-level mass management.

## Out of scope
- Bulk assign/snooze/reopen.
- Full supervisor routing engine.
- Action macros.
- New queue column management UI.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseDetailsPanel.tsx`
- `console-web/src/utils/labels.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `console-web/src/types/api.generated.ts`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Plan (1..N)
1. Добавить wave6 TP и перевести session docs на новый active block.
2. Реализовать backend-first `reassign`, `snooze`, `reopen` и assignee options contract.
3. Подключить actions в Inbox detail UI.
4. Обновить OpenAPI/types/e2e mocks.
5. Прогнать targeted checks и зафиксировать evidence.

## DoD
- В активной заявке доступны bounded single-case actions `reassign` и `snooze`.
- В закрытой заявке доступен bounded action `reopen`.
- Reassign использует реальный assignee source, а не хардкод списка на фронтенде.
- Snooze меняет action semantics кейса так, чтобы он не выглядел как immediate reply item до истечения snooze.
- Reopen возвращает тот же case в рабочий цикл, а не создает новую несвязанную сущность.
- Contract checks, frontend lint и targeted inspect-case lane зеленые.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/components/CaseConversation.tsx --file src/components/CaseDetailsPanel.tsx --file src/utils/labels.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`

## Current branch status
- `Part A1` реализован: backend endpoints `assignees/reassign/snooze/reopen`, schema/OpenAPI contract и helper coverage добавлены.
- `Part A2` реализован: Inbox action toggles/panels добавлены в `CaseConversation`, details surface обновлён, `inspect_case` mocks расширены.
- `Snooze` реализован через `handover.meta`, чтобы defer semantics не зависели от WhatsApp-specific `human-lock`; resolve/return/reopen/manual-reply очищают stale snooze meta.
- `manager_reopen` переведён на explicit operator override обратно в `manager_active`, чтобы reopen соответствовал бизнес-контракту ручного возврата заявки в работу.

## Evidence
- Git diff по touch-list.
- `cd truffles-api && pytest -q tests/test_state_service.py tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py` (`67 passed`).
- `cd truffles-api && python3 scripts/generate_openapi.py --check` (`pass`).
- `cd console-web && npm run generate:api` (`pass`).
- `cd console-web && npm run lint -- --file src/lib/api-client.ts --file src/components/CaseConversation.tsx --file src/components/CaseDetailsPanel.tsx --file src/utils/labels.ts --file src/types/index.ts --file e2e/inspect_case.spec.ts` (`pass`).
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line` (`pass`).
- `cd console-web && set -a && source /home/zhan/secrets/console-e2e.env && set +a && E2E_USE_STORAGE_STATE=1 E2E_DETERMINISTIC_AUTH=0 PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz INSPECT_CASE_USE_MOCKS=0 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line` (`pass`, calendar no-cases fallback).
- Updated inbox screenshots for action controls.
- Session log with wave6 evidence.

## Release safety (mandatory)
- **Rollout:** one bounded PR preferred; if split is required, `Part A1` merges before `Part A2`.
- **Go/no-go:** backend contract green + generated API/types synced + frontend lint + inspect-case lane pass.
- **Rollback:** revert current PR; `take/resolve/return` remain the safe baseline.

## Rollback
- `git revert REVISION_SHA`
- Re-run wave6 checks.
- Confirm Inbox actions fall back to the previous three-button baseline.

## No-go
- Реализовывать reassignment через фронтендовый hardcoded список людей.
- Называть `snooze` просто визуальным label без изменения queue semantics.
- Создавать новый case при `reopen`.
- Подмешивать bulk scope в этот блок.

## Риски/блокеры
- Reassign требует аккуратного assignee-source contract, иначе возможны неверные передачи.
- Reopen может сломать метрики, если не переиспользовать current handover lifecycle аккуратно.
- Snooze может конфликтовать с wave5 SLA indicators, если не сделать явный `snoozed` action state.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: bulk operations и supervisor queue governance остаются вне этого wave.
- `Why not in this block`: сначала нужен корректный single-case contract.
- `Risk if deferred`: админские массовые сценарии по-прежнему будут делать лишние клики.
- `Linked follow-up Task Package(s)`: `TBD wave7`, future `wave6-part-bulk` if needed.
- `Expiry/trigger to stop deferral`: если после wave6 основной pain переносится в массовые операции, bulk block становится immediate next priority.

## Next-block contract (mandatory)
- `Next block objective`: открыть bounded follow-up TP на wave6 `Part B` и добавить bulk/supervisor actions без регресса single-case контракта.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `Blocked-by conditions`: wave5 SLA action contract must stay green and case action UI cannot regress first-screen clarity.
- `Owner role for closure`: Brain / Top Architect.
