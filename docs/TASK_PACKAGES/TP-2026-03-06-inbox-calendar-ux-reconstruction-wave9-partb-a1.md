# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-PARTB-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1

## Название/цель
Довести queue governance до supervisor/admin-grade контракта без нового экрана: добавить backend-supported owner views (`assignee/unassigned`) и встроить их в текущую очередь `Заявок`, чтобы передача и контроль ownership не зависели от локальной пагинации или ручных догадок.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md`

## Git / worktree
- `Branch`: `feat/2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1`
- `Worktree path`: `/home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1`
- `Base ref`: `origin/main`
- `Merge policy`: continue inside existing PR `#932`
- `Cleanup`: Brain / Top Architect after merge

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/routers/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `truffles-api/tests/test_console_cases_helpers.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/components/CaseList.tsx`
  - `console-web/src/lib/inbox-workspace.ts`
  - `console-web/src/lib/api-client.ts`
  - `console-web/e2e/inspect_case.spec.ts`
- `Baseline findings`:
  - Wave9 Part A уже добавил role-aware queue views и visible-field governance, но privileged slice `Без владельца` всё ещё строится на текущей загруженной выборке.
  - Для supervisor/admin сейчас нет server-backed owner filter по конкретному менеджеру или по unassigned cases.
  - Current bulk `reassign` уже умеет безопасно передавать ownership, но очередь не даёт supervisor быстро увидеть backlog конкретного владельца до самой передачи.

## One web search (mandatory before implementation)
- **Query (exact):** `HubSpot route tickets in help desk official documentation`
- **Date/time (local):** `2026-03-06T11:30:23+05:00`
- **Sources opened:**
  - `https://knowledge.hubspot.com/help-desk/route-tickets-in-help-desk`
- **Ready solutions found:** зрелые help desk routing surfaces держат owner assignment и unassigned backlog в серверном рабочем представлении, чтобы supervisor не принимал решение по локально урезанной выборке.
- **Decision (`reuse/integrate/build`):** `integrate` — встроить owner views и unassigned filter в текущую очередь `Заявок`, переиспользуя существующие bulk actions и assignee option contracts.
- **Rejected options:** отдельный supervisor-only экран; только client-side filtering по owner/unassigned поверх пагинации.
- **Source quality:** high-signal primary source = official HubSpot knowledge base documentation.

## Root cause (mandatory)
- **Symptom:** Wave9 Part A сделал очередь заметно управляемее, но supervisor/admin всё ещё видит `Без владельца` только внутри текущей загруженной выборки и не может открыть очередь конкретного менеджера как устойчивый рабочий режим.
- **Minimal reproduction:** открыть `Заявки` под owner/admin, выбрать `Без владельца` или попытаться проверить backlog конкретного менеджера на очереди больше 20 кейсов.
- **Evidence:** `CaseList.tsx` после Part A хранит only UI-level governance; `GET /cases` не принимает `assignee_id`/`unassigned`; отдельного queue-level assignee list endpoint нет.
- **Five Whys:**
  1. Почему privileged queue governance ещё не закрыт? Потому что owner/unassigned slice не закреплён в backend query contract.
  2. Почему client-side slice недостаточен? Потому что пагинация и cursor limit скрывают часть очереди.
  3. Почему нельзя решить это новым экраном? Потому что ТЗ требует оптимизировать текущие вкладки и избегать дублирующих routes.
  4. Почему нужен отдельный assignee endpoint? Потому что filter по owner должен работать без выбранной заявки.
  5. Почему блок bounded? Потому что здесь закрывается именно supervisor/admin ownership visibility; routing rules/capacity остаются за пределами этого Part B.
- **Root cause statement:** supervisor/admin queue governance остаётся неполным, пока ownership views завязаны на client-side slice вместо backend-supported filters.
- **Fix mechanism:** расширить `GET /cases` фильтрами `assignee_id`/`unassigned`, добавить queue-level list of assignees и подключить эти owner views в текущий `CaseList`.

## Reuse-first plan (mandatory)
- **Reuse:** текущий `GET /cases`, `_list_case_assignee_options`, bulk `reassign`, workspace persistence, Wave9 Part A queue views.
- **Integrate:** добавить owner governance внутрь существующей очереди и обновить existing queue views to use backend-supported filters where needed.
- **Build only if needed:** только новый queue-level assignee endpoint и минимальные filter fields/prefs.

## Invariant
- Не ломать current manager default readability и existing Wave9 Part A queue views.
- Не дублировать owner controls в новом route или side panel.
- Bulk `reassign/snooze` и case selection должны остаться рабочими во всех owner views.
- `assigned_to_me` не должен конфликтовать с explicit owner/unassigned filter silently.

## Scope
- добавить backend query params `assignee_id` и `unassigned` в `GET /cases`;
- добавить queue-level `GET /cases/assignees` для текущего scope/branch;
- встроить owner filter в `CaseList` для privileged roles;
- перевести privileged `Без владельца` view на server-backed contract;
- покрыть new contract deterministic tests and inspect-case mock lane.

## Out of scope
- Полноценный routing engine/capacity balancing.
- Новый admin dashboard.
- SLA redesign или новые массовые действия.

## Touch-list
- `truffles-api/app/routers/console.py`
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/lib/inbox-workspace.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/e2e/inspect_case.spec.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Создать Wave9 Part B TP и перевести session canon на новый active block.
2. Добавить backend filters `assignee_id/unassigned` и queue-level assignee list endpoint.
3. Подключить privileged owner filter в `CaseList` с workspace persistence и без конфликтов с `assigned_to_me`.
4. Обновить deterministic tests/contracts and inspect-case lane.
5. Запушить изменения в PR `#932`.

## DoD
- Supervisor/admin может открыть queue по конкретному owner или по unassigned cases без локальной pagination drift.
- Queue-level assignee filter работает внутри текущей вкладки `Заявки`.
- `assigned_to_me` и explicit owner filter не создают silent conflict.
- Wave9 Part A views и bulk actions не ломаются.
- OpenAPI/tests/e2e отражают новый contract.

## Checks
- `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint -- --file src/components/CaseList.tsx --file src/lib/inbox-workspace.ts --file src/lib/api-client.ts --file e2e/inspect_case.spec.ts`
- `cd console-web && npm run build`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Pytest/OpenAPI/generate-api/lint/build/Playwright outputs.
- Updated session log with Wave9 Part B status.

## Release safety (mandatory)
- **Rollout:** continue in PR `#932`; new backend params are additive and consumed only by privileged queue controls.
- **Go/no-go:** default queue for manager remains readable; owner filter returns stable data and bulk actions still submit correct case_ids.
- **Rollback:** revert Wave9 Part B diff; Wave9 Part A governance remains intact.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave9 Part B checks.

## No-go
- Оставлять `Без владельца` только как client-side slice и называть это полноценным supervisor control.
- Добавлять отдельный supervisor route.
- Смешивать `assigned_to_me`, `assignee_id` и `unassigned` без явной валидации конфликта.

## Риски/блокеры
- Query-param conflicts могут ломать очередь молча, если не дать `INVALID_PARAM`.
- Queue assignee list должен уважать branch RBAC и не утекать за scope.
- E2E mocks нужно синхронизировать с новым assignee endpoint, иначе lane станет ложноположительным.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: owner views будут server-backed, но полноценные routing rules/capacity/overflow controls всё ещё останутся вне Wave9.
- `Why not in this block`: это уже следующий продуктовый слой beyond current queue governance scope.
- `Risk if deferred`: supervisor увидит корректный ownership backlog, но не получит policy-based routing automation.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`.
- `Expiry/trigger to stop deferral`: если после merge owner/admin всё ещё не может безопасно контролировать routing policy без ручных обходов, потребуется новый bounded TP.

## Next-block contract (mandatory)
- `Next block objective`: close Wave9 by validating that supervisor/admin queue governance is complete enough for current TЗ and decide whether separate routing-policy wave is still required.
- `First deterministic check command`: `cd console-web && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/inspect_case.spec.ts --project=chromium --reporter=line`
- `Blocked-by conditions`: Wave9 Part B must keep Part A views, bulk actions, and current case/calendar workspace stable.
- `Owner role for closure`: Brain / Top Architect.
