# TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-A1
- `PARENT_BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `DEPENDS_ON`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-A1
- `UNLOCKS`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-A1

## Название/цель
Превратить inbox macros из текстовых шаблонов в executable operator actions на backend: сохранить текущую модель быстрых ответов, но добавить структурированный action contract и case-scoped execution endpoint без немедленного UI-расширения конструктора макросов.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/migrations/051_add_console_macro_action_contract.sql`
  - `truffles-api/app/models/console_macro.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_inbox_macros.py`
  - `truffles-api/tests/test_console_openapi_calendar_contract.py`
  - `console-web/src/types/api.generated.ts`
  - `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md`
  - `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `Baseline findings`:
  - Текущий macro contract хранит только `label/body/is_active/scope`; stateful action semantics отсутствуют.
  - В Wave6 уже есть bounded operator actions `take/reassign/snooze/resolve/return/reopen`, значит макросам не нужен новый workflow engine — нужен reuse существующего case contract.
  - `InboxMacros` на фронтенде сейчас только подставляет `body` в draft; backend не умеет хранить и исполнять action bundle.

## One web search (mandatory before implementation)
- **Query (exact):** `Zendesk macros ticket actions assign to self status official documentation`
- **Date/time (local):** `2026-03-06T09:50:53+05:00`
- **Sources opened:**
  - `https://support.zendesk.com/hc/en-us/articles/4408887656602-Using-macros-to-update-tickets`
  - `https://developer.zendesk.com/api-reference/ticketing/business-rules/actions/`
- **Ready solutions found:** official helpdesk pattern = macro хранит готовый набор agent actions, применяется вручную к тикету, может менять comment/assignee/status и должен быть previewable до submit.
- **Decision (`reuse/integrate/build`):** `integrate` — строить action-macro contract поверх уже реализованных case actions и текущих console macros, не вводя отдельный automation engine.
- **Rejected options:** новый rules engine или implicit frontend-only macro execution без backend contract.
- **Source quality:** high-signal sources = official Zendesk help + official Zendesk developer reference.

## Root cause (mandatory)
- **Symptom:** macros ускоряют набор текста, но не ускоряют операционную работу менеджера, потому что не могут менять состояние заявки.
- **Minimal reproduction:** открыть активную заявку, выбрать типовой ответ вроде “ждём клиента” или “закрываем кейс”; менеджер всё равно отдельно кликает `Отложить/Закрыть/Вернуть боту`.
- **Evidence:** current `ConsoleMacro` schema/model/router хранят только текст; Wave6 actions живут отдельно и не связаны с macros contract.
- **Five Whys:**
  1. Почему макрос не экономит полный цикл менеджера? Потому что он меняет только текст ответа.
  2. Почему это остаётся UX/business gap? Потому что операционная работа состоит из текста и state transition, а не только из сообщения.
  3. Почему нельзя решить это только фронтендом? Потому что action semantics должны валидироваться и исполняться сервером с теми же правилами доступа, что и Wave6 actions.
  4. Почему не надо строить новый engine? Потому что bounded case actions уже реализованы и покрывают нужные transition paths.
  5. Почему block надо делить на backend и UI? Потому что сначала нужен стабильный contract хранения/исполнения action-macros, потом UI builder/apply flow.
- **Root cause statement:** inbox macros не имеют серверного action contract и case-scoped execution path, поэтому остаются текстовыми шаблонами и не закрывают реальный операторский сценарий.
- **Fix mechanism:** добавить structured macro action schema + persistence + execution endpoint, переиспользуя существующие Wave6 case-action primitives.

## Reuse-first plan (mandatory)
- **Reuse:** `ConsoleMacroModel`, `Inbox macros CRUD`, Wave6 helpers `_resolve_case_action_context`, `_require_case_operator_access`, `_set_case_snooze_meta`, `_build_case_action_case`, `manager_take/resolve/return/reopen`.
- **Integrate:** расширить existing macro schemas/model одним `action` contract и добавить `POST /inbox/macros/{macro_id}/execute`.
- **Build only if needed:** новый migration column `action_config` и new execution response schema.

## Invariant
- Не ломать существующий text-only macros flow.
- Не дублировать Wave6 case-action бизнес-логику в отдельном engine.
- Не делать macro execution silent: endpoint должен явно возвращать какой action применён и в каком состоянии теперь кейс.
- Не добавлять Wave7 UI builder в этот блок.

## Scope
- `Part A (this TP)`:
  - migration + model support for structured macro action config;
  - schema/create/update/list contract for optional macro action;
  - backend execute endpoint for bounded case actions;
  - targeted tests + OpenAPI + generated frontend types sync.
- `Part B (follow-up, not in this TP)`:
  - UI builder/editor for choosing action inside macro form;
  - macro apply UX inside composer/case workspace with preview and user-facing explanations.

## Out of scope
- New top-level workspace.
- Multi-action automation engine or background workflows.
- Assign-to-other-manager macro actions.
- Tagging system and macro tags.
- Frontend macro form redesign.

## Touch-list
- `truffles-api/migrations/051_add_console_macro_action_contract.sql`
- `truffles-api/app/models/console_macro.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_inbox_macros.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Зафиксировать Wave7 TP и перевести session docs на новый active block.
2. Добавить structured macro action contract в schema/model/migration.
3. Реализовать case-scoped macro execute endpoint поверх Wave6 action helpers.
4. Обновить targeted behavior/openapi checks и generated API types.

## DoD
- Macro contract поддерживает optional structured action без регресса text-only macros.
- Backend умеет исполнить bounded action-macro на кейсе через отдельный endpoint.
- Supported macro actions используют существующие Wave6 transitions, а не отдельные ad-hoc ветки.
- OpenAPI/types/tests зелёные.
- Session canon указывает на Wave7 как active block.

## Checks
- `cd truffles-api && pytest -q tests/test_console_inbox_macros.py tests/test_console_openapi_calendar_contract.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Targeted pytest/openapi output.
- Generated `console-web/src/types/api.generated.ts`.
- Session log with Wave7 Part A evidence.

## Release safety (mandatory)
- **Rollout:** backend-first; existing UI remains backward-compatible with text-only macros until Part B.
- **Go/no-go:** macro CRUD stays backward-compatible, execute endpoint green, no regressions in Wave6 case actions.
- **Rollback:** revert this bounded diff; existing macros remain text-only baseline.

## Rollback
- `git revert REVISION_SHA`
- Re-run Wave7 targeted checks.

## No-go
- Встраивать macro action execution напрямую во фронтенд без backend endpoint.
- Смешивать этот блок с UI builder/edit flow.
- Добавлять новый rules engine или implicit automation worker.
- Ломать существующие text-only macros обязательным action field.

## Риски/блокеры
- Macro actions не должны обходить case permission checks.
- `snooze_case` требует параметров (`minutes`, optional `reason`) и нормализации, иначе backend contract станет двусмысленным.
- Existing macro rows must remain valid after migration with `action_config = NULL`.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: UI builder/apply flow для action-macros и user-facing preview подсказки.
- `Why not in this block`: сначала нужен стабильный backend contract и execution semantics.
- `Risk if deferred`: action-macros будут существовать только на API уровне до следующего блока, без полного UX выигрыша для менеджера.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md`, `TBD wave8`.
- `Expiry/trigger to stop deferral`: после merge этого блока следующий product step должен подключать macro actions в UI, а не возвращаться к text-only improvements.

## Next-block contract (mandatory)
- `Next block objective`: открыть `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md` и подключить macro action builder/apply flow в `InboxMacros` и composer UX.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_inbox_macros.py tests/test_console_openapi_calendar_contract.py`
- `Blocked-by conditions`: Wave7 Part A backend contract and migration must be green and backward-compatible.
- `Owner role for closure`: Brain / Top Architect.
