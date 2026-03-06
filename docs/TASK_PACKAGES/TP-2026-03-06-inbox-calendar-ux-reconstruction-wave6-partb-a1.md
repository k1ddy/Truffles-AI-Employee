# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-PARTB-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-A1

## Название/цель
Добавить bounded bulk/supervisor case actions поверх уже закрытого single-case контракта: сначала backend-first bulk `reassign` и `snooze`, без смешивания этого блока с action-macros и без нового top-level workspace.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/lib/api-client.ts`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `Baseline findings`:
  - Wave6 Part A уже дал корректный single-case contract для `reassign`, `snooze`, `reopen`.
  - В очереди нет selection/bulk toolbar и нет backend endpoint для пакетных operator actions.
  - Supervisor/admin всё ещё делают лишние клики по одной заявке, хотя бизнес-логика уже допускает bounded массовые действия.

## One web search (mandatory before implementation)
- **Query (exact):** `official helpdesk bulk ticket actions assignment reopen snooze documentation Zendesk bulk edit tickets official`
- **Date/time (local):** `2026-03-06T08:18:00+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/manage-tickets-in-help-desk`
  - `https://support.zendesk.com/hc/en-us/articles/4408887656602-Using-macros-to-update-tickets`
  - `https://support.atlassian.com/jira-service-management-cloud/docs/best-practices-for-managing-queues-at-scale/`
- **Ready solutions found:** зрелые helpdesk/workspace продукты держат bulk operations как отдельный operator layer поверх тех же ticket states; queue-at-scale guidance завязана на views/selection/group actions, а не на отдельный второй workflow engine.
- **Decision (`reuse/integrate/build`):** `integrate` — строить bulk layer поверх уже реализованных single-case action primitives и текущей очереди `CaseList`, без новой сущности кейса и без параллельного workflow.
- **Rejected options:** отдельный supervisor-only экран как обход отсутствующего bulk контракта.
- **Source quality:** high-signal sources = official HubSpot knowledge base, official Zendesk help, official Atlassian support docs.

## Root cause (mandatory)
- **Symptom:** после Wave6 Part A оператор может корректно управлять одной заявкой, но supervisor/admin всё ещё не может быстро переработать пачку заявок без десятков повторяющихся кликов.
- **Minimal reproduction:** открыть очередь заявок и попытаться передать или отложить несколько похожих кейсов подряд.
- **Evidence:** single-case actions уже есть, но selection/bulk endpoint отсутствуют; очередь остаётся strictly one-by-one.
- **Five Whys:**
  1. Почему админский сценарий всё ещё медленный? Потому что контракт действий существует только на одну заявку.
  2. Почему это нельзя решать только UI-оптимизациями? Потому что без backend bulk contract фронтенд останется клиентским циклом из N запросов.
  3. Почему это бизнес-проблема? Потому что массовые пики нагрузки и handoff/snooze cleanup требуют supervisor throughput, а не только удобного single-case UX.
  4. Почему это нельзя смешивать с action-macros? Потому что bulk routing и macro automation — разные оси продукта.
  5. Почему bounded split нужен сейчас? Потому что иначе Wave6 расползётся и снова потеряет атомарность.
- **Root cause statement:** отсутствует bounded bulk contract поверх уже реализованных single-case actions, поэтому operator queue остаётся неуправляемой на масштабе.
- **Fix mechanism:** добавить backend-first bulk endpoint и bounded selection semantics для `reassign`/`snooze`, переиспользуя Wave6 Part A primitives и queue contract.

## Reuse-first plan (mandatory)
- **Reuse:** `ConsoleCase`, Wave6 Part A action semantics, `handover.meta` snooze model, `state_manager_reassign`, `_require_case_operator_access`, existing queue list response.
- **Integrate:** добавить один bulk endpoint и минимальный queue selection contract.
- **Build only if needed:** новые bulk request/response schemas и позже — компактный bulk toolbar в `CaseList`.

## Invariant
- Не ломать Wave6 Part A single-case actions.
- Не создавать новый workflow engine для bulk.
- Не превращать bulk actions в silent background mutation без per-case result.
- Любой bulk response должен быть наблюдаемым: `processed/skipped/failed` по каждой заявке.

## Scope
- `Part B1 (backend contract; mandatory in this TP)`:
  - bulk request/response schemas;
  - backend endpoint для bounded bulk `reassign` и `snooze`;
  - per-case result reporting и permission-aware partial success.
- `Part B2 (frontend surface; optional follow-up inside same TP only if Part B1 green)`:
  - queue selection + compact bulk toolbar в `CaseList`.

## Out of scope
- Action macros.
- Full supervisor routing engine.
- Bulk reopen/resolve/return, если это потребует отдельного rollout decision.
- Новый top-level supervisor workspace.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Plan (1..N)
1. Создать bounded TP для Wave6 Part B и перевести session docs на него.
2. Реализовать backend bulk contract для `reassign` и `snooze`.
3. Добавить contract/openapi checks.
4. Только после green backend evidence решать, помещается ли минимальный frontend bulk toolbar в этот же блок.

## DoD
- Есть backend endpoint для bounded bulk actions по заявкам.
- Bulk `reassign` и `snooze` работают поверх existing single-case semantics.
- Response возвращает per-case результат, а не только общий `success`.
- В очереди доступна bounded selection semantics и компактный bulk toolbar без нового экрана.
- Contract/openapi checks зелёные.
- Frontend bulk toolbar не дублирует single-case actions и не ломает first-screen clarity.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file src/lib/api-client.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `scripts/session_check.sh`

## Current branch status
- `Part B1` реализован в backend: добавлен bounded bulk endpoint `/cases/bulk` для `reassign` и `snooze` с per-case `processed/skipped/failed` результатами.
- `Part B2` реализован в UI: в `CaseList` добавлены selection checkbox, `Выбрать все`, компактный bulk toolbar и bounded submit flow для `reassign`/`snooze`.
- Для `bulk reassign` UI ограничивает старт одним филиалом, а `bulk snooze` остаётся доступным для всей текущей выборки.
- Исправлен queue-state bug в `CaseList`: пустой search debounce больше не очищает локальный список без фактической смены query, из-за чего mock/workspace lane терял видимые заявки после mount.

## Evidence
- Git diff по touch-list.
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py` (`37 passed`).
- `cd truffles-api && python3 scripts/generate_openapi.py --check` (`pass`).
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/components/InboxView.tsx --file src/lib/api-client.ts --file e2e/inspect_case.spec.ts` (`pass`).
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line` (`pass`, mock lane now asserts bulk selection and `/cases/bulk` payload).
- `console-web/case_inspection.png` (queue row + selection checkbox + updated inbox surface).
- `console-web/calendar_case_context.png`.
- Session log with Wave6 Part B evidence.

## Release safety (mandatory)
- **Rollout:** backend-first, без включения массового UI до зелёного контракта.
- **Go/no-go:** bulk endpoint + openapi checks green, без регресса Wave5/Wave6 Part A checks.
- **Rollback:** revert текущего bounded PR/diff, single-case contract остаётся baseline.

## Rollback
- `git revert REVISION_SHA`
- Повторный прогон targeted checks.

## No-go
- Делать bulk как цикл из client-side single-case запросов и считать это backend contract.
- Скрывать частичные ошибки bulk операции.
- Подмешивать macro automation в этот блок.

## Риски/блокеры
- Mixed-branch selection может потребовать permission-aware skip, а не hard fail.
- Bulk reassign должен использовать тот же assignee-source contract, иначе возможны неверные передачи.
- Расширение bulk на `reopen/resolve/return` потребует отдельного rollout decision и supervisor policy.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: supervisor-grade queue governance, bulk `reopen/resolve/return`, team views and routing controls.
- `Why not in this block`: этот блок bounded только на массовые `reassign/snooze` поверх текущего queue surface, без перехода в Wave7/Wave9.
- `Risk if deferred`: supervisor всё ещё не получит полный control tower поверх очереди, хотя базовая массовая операционная работа уже стала быстрее.
- `Linked follow-up Task Package(s)`: `TBD wave7`, `TBD wave9`.
- `Expiry/trigger to stop deferral`: если после merge bulk `reassign/snooze` покрыты, следующий product block обязан идти либо в action-macros, либо в supervisor queue governance, но не в косметические UI правки.

## Next-block contract (mandatory)
- `Next block objective`: открыть Wave7 Part A и превратить inbox macros из текстовых шаблонов в executable action-macros поверх уже закрытого Wave6 operator contract.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: PR `#931` должен остаться зелёным; Wave6 bulk/single-case contract не должен регрессировать.
- `Owner role for closure`: Brain / Top Architect.
