# TP-2026-03-05-inbox-calendar-ux-reconstruction-a1 (Master Program)

## Block identity
- `BLOCK_ID`: CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-MASTER-A1
- `PARENT_BLOCK_ID`: none
- `DEPENDS_ON`: none
- `UNLOCKS`:
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE1-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE2-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE3-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE4-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE5-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE6-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE7-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE8-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE9-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE10-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-CLOSEOUT-REVIEW-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE11-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-LIVE-VALIDATION-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE13-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE14-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-LIVE-VALIDATION-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE17-CLOSEOUT-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE18-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE19-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE20-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE21-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE22-LIVE-PROOF-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE23-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE24-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE37-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE38-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE39-A1`

## Название/цель
Обновить ТЗ в формат исполнимой программы: закрыть требования по вкладкам `Заявки` и `Записи` не набором разрозненных правок, а полной последовательностью атомарных wave/part блоков с явной бизнес-логикой, строгой связью между TP/PR и без дублирования действий в интерфейсе.

## Final closure status
- Historical closure from `2026-03-07` is no longer the effective acceptance state.
- `Wave37` merged via `PR #959`, and `Wave38` is now also merged via `PR #960`; there is no rollback of `Wave36`/`Wave37`/`Wave38`.
- `Wave38` closed the repaired Calendar primary flows on `main`: explicit filter apply/reset semantics, natural raw phone input, and bounded booking edit/reschedule/cancel lifecycle with deterministic proof.
- `Wave39` is now fully closed: merged via `PR #961` and replayed on merged `main@710f8faa` without action-safety drift. Calendar no longer has an active operator-safety block. The next valid backlog sequence returns to `UX-08` (`runtime health / outbox pressure`), then `UX-20`, then `UX-26`.
- Routing v2 remains blocked exactly as before; no return to non-Calendar backlog work is allowed before `Wave39` is explicitly closed.
- Owner-approved post-closeout maturity analysis remains valid for queue-state/routing sequencing, but current execution is now governed by `Wave39`, not by `Wave38` merge/closeout work.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1.md`

## FACT pre-check (before implementation)
- `Implemented and merged (fact)`:
  - Связка `Заявки -> Записи -> возврат в заявку` уже внедрена.
  - First-screen в `Заявках` упрощен: очередной triage слева, чат в центре, лишние дубли SLA убраны.
  - В `Записях` уже есть action-first queue controls: `lane`, `needs_action`, `attention_reason`, server-side cursor pagination.
  - Связь записи с заявкой стала явной через `appointments.case_id`.
  - Runtime слой уже улучшен до `SSE-first + polling fallback`, есть wave4 release runbook.
- `Remaining product gaps (fact)`:
  - `Wave38` is now merged on `main` via `PR #960`, so the repaired Calendar primary flows are factual merged behavior rather than local-only evidence.
  - The remaining active product gap is still `Wave39`, but `Part A` is now factual local progress: the frontend already has a canonical action registry and matrix-derived proof; the still-open gap is backend-owned `allowed_actions`, version conflicts, extracted state machines, and post-merge observability/replay.
  - Accepted non-routing residual sequencing from `Wave23`/`Wave24` still stands, but it stays gated behind explicit `Wave39` closure.

## Post-closeout maturity analysis (mandatory)
- `Historical note`: this section records the owner-approved `Wave23` maturity analysis that unlocked `Wave24` through `Wave38`. Current execution is governed by `Final closure status` and `Wave39`; do not treat the D1-D5 bullets below as current open blockers if later merged waves already closed them.
- `Primary blocker`: queue state is still split across browser storage, route context, and strict server query params, so there is no single reproducible operator view contract for `Заявки` and `Записи`.
- `Defect cluster D1`: local-only queue state blocks reproducible handoff and supervisor review.
- `Defect cluster D2`: no server-owned saved-view object means personal views and team presets would fork into duplicate models if built now.
- `Defect cluster D3`: shareable queue URLs are not canonical because URLs carry context ids, not queue-state semantics.
- `Defect cluster D4`: `Записи` still lack supervisor-grade follow-up owner/due/history governance, so future routing would optimize against an incomplete model.
- `Defect cluster D5`: routing inputs are still too narrow (`least_open_cases` only), and richer automation must wait until queue-state canon and bookings governance are explicit.
- `Execution order`: `Wave24 Queue State Canon` first; after that, future work may layer saved views, managed presets, shareable queue URLs, bookings supervisor-grade governance, and only then richer routing.

## One web search (mandatory before implementation)
- **Query (exact):** `Dynamics 365 Customer Service unified routing queue prioritization assignment methods`
- **Date/time (local):** `2026-03-05T09:37:36+05:00`
- **Sources opened:**
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/queues-omnichannel`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/configure-assignment-rules`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/use/work-with-queues`
- **Ready solutions found:** приоритет очереди как формальный сигнал (`priority + routing + queue reasons`), явные assignment methods и наблюдаемая lifecycle-диагностика work items.
- **Decision (`reuse/integrate/build`):** `integrate` — развивать текущие вкладки `Заявки/Записи` как единый операторский контур, а не выносить все в новый top-level модуль.
- **Rejected options:** отдельный новый "диспетчерский" экран как основной путь менеджера.
- **Source quality:** high-signal primary source = official Microsoft Learn documentation.

## Root cause (mandatory)
- **Symptom:** отдельные UX улучшения уже внедрены, но ТЗ пользователя все еще не закрыто целиком, потому что отсутствует полный операционный контракт менеджера.
- **Minimal reproduction:** менеджер берет кейс, переходит в запись, возвращается в чат, пытается понять SLA, передать кейс или стандартизировать действие команды — и упирается в неполный action contract.
- **Evidence:** текущие code facts из `console.py`, `labels.ts`, `console_macro.py`, `CaseConversation.tsx`, `CaseList.tsx`, `calendar/page.tsx`.
- **Five Whys:**
  1. Почему UX еще кажется незавершенным? Потому что уже решены связность и часть queue UX, но не завершен action contract менеджера.
  2. Почему SLA по-прежнему раздражает? Потому что он отображается как техническое состояние, а не как конкретное действие.
  3. Почему операторская работа все еще ограничена? Потому что в backend нет полного набора case actions и action-macros.
  4. Почему вкладка `Записи` еще не operator-grade? Потому что админские queue/governance сценарии пока не доведены до supervisor-level.
  5. Почему нельзя считать ТЗ закрытым сейчас? Потому что еще остаются незакрытые бизнес-сценарии, влияющие на FRT/NRT, передачу ответственности и масштабную управляемость.
- **Root cause statement:** базовая связность и runtime надежность уже внедрены, но отсутствует полный операторский бизнес-контракт для `SLA -> действия -> макросы -> единый workspace -> supervisor governance`.
- **Fix mechanism:** зафиксировать master TP как точную карту атомарных волн, где каждый remaining gap имеет свой bounded block, explicit split contract и свой следующий deterministic check.

## Reuse-first plan (mandatory)
- **Reuse:** текущие `console`/`calendar` роуты, wave1-wave4 UI/layout решения, `appointments.case_id`, queue/filter contracts, SSE/polling fallback, существующие Playwright lanes.
- **Integrate:** достроить case action contract и operator workspace поверх уже реализованного фундамента.
- **Build only if needed:** только недостающие backend contracts, UI surfaces и admin actions; без новых top-level вкладок и без параллельной второй IA.

## Invariant
- Не добавлять новые top-level вкладки вместо улучшения `Заявки/Записи`.
- Не дублировать одинаковые действия в нескольких местах без явной причины.
- Любой SLA/статус обязан вести к понятному действию менеджера.
- Все новые волны должны быть атомарными и иметь явный `part split`, если один блок не помещается в один PR.
- Решения должны вписываться в уже реализованные части console и не ломать wave1-wave4 foundation.

## Scope
- Обновить master ТЗ до реального source-of-truth по всему program scope.
- Зафиксировать, что уже выполнено, что еще не выполнено и в какой atomic wave это закрывается.
- Для каждого remaining wave заранее указать допустимое деление на части, чтобы избежать бесконтрольного расползания scope.

## Out of scope
- Немедленная реализация всех remaining waves в этом master TP.
- Новая product IA вне `Заявки/Записи`.
- Переписывание несвязанных частей console.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `STATE.md`

## Requirement coverage map (mandatory)
| Original requirement | Current state | Closing wave | Atomic split rule |
|---|---|---|---|
| `1. Нет связи между вкладками` | Done | Wave1 | split not allowed |
| `2. Менеджер скроллит вниз, чтобы понять контекст` | Done (first-screen simplified) | Wave1 | split not allowed |
| `3. Непонятные SLA цифры и термины` | Merge-ready in `PR #932` | Wave5 | `Part A backend SLA contract` -> `Part B UI surfaces` if one PR is not enough |
| `4. Вкладка Записи не удобна для управления` | Merge-ready closure with accepted residual | Wave6 + Wave8 + Wave9 + Wave10 | explicit split required by capability group |
| `5. Капитальная реконструкция с ориентацией на мировые CRM` | Merge-ready closure with accepted residual | Master program | close only via explicit closeout review |
| `6. Любые недостающие функции и механизмы должны быть проанализированы и вписаны` | Merge-ready closure with accepted residual | Wave6/Wave7/Wave9/Wave10 | each missing capability must map to one wave/part |
| `7. Все должно быть связано, интуитивно и без дублей` | Merge-ready | Cross-wave invariant | enforced across all waves |

## Execution model (mandatory TP/PR split)
| Wave | TP document | PR policy | Objective | Status |
|---|---|---|---|---|
| Wave1 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md` | PR-1 | Базовая связка `Заявки/Записи`, first-screen, базовая SLA copy cleanup. | Done |
| Wave2 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md` | PR-2 | Action-first queue controls и упрощение терминологии для менеджера. | Done |
| Wave3 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md` | PR-3 | Backend/data-contract consistency: `appointments.case_id`, queue filters, cursors, queue fields. | Done |
| Wave4 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md` | PR-4 | Realtime reliability, observability, rollout safety. | Done |
| Closeout | `TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md` | PR-5 | Canary/go-no-go/rollback discipline для wave4. | Done |
| Wave5 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md` | One PR preferred; split only into `Part A backend contract` then `Part B frontend surfaces` | Action-driven SLA contract вместо абстрактных статусов. | Done (merged via `PR #931`) |
| Wave6 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md` | Split allowed and expected: `Part A single-case actions`, `Part B bulk/supervisor actions` | Добавить `reassign/snooze/reopen/bulk` и operator case control. | Done (merged via `PR #931`) |
| Wave7 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md` + `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md` | Split allowed and expected: `Part A action-macro backend`, `Part B macro UI/integration` | Превратить макросы из текстовых в executable operator actions. | Done (merged via `PR #932`) |
| Wave8 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md` + `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md` | Split allowed and expected: `Part A workspace shell`, `Part B queue position/context preservation` | Довести `Заявки/Записи` до единого workspace без потери контекста. | Done (merged via `PR #932`) |
| Wave9 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md` + `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md` | Split allowed and expected: `Part A queue governance`, `Part B routing/admin views` | Supervisor/admin-grade queue governance: team views, columns, routing controls. | Done (merged via `PR #932`) |
| Wave10 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md` + `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md` | Split allowed and expected: `Part A factual load signals`, `Part B recommended routing action` | Сделать reassignment менее слепым: factual workload hints before any automation. | Done (merged via `PR #932`) |
| Closeout Review | `TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1.md` | No new PR; same `PR #932` decision gate | Explicitly classify original ТЗ closure and accepted residuals before merge. | Done |
| Wave11 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md` | One PR preferred; split allowed into `Part A action-sync correctness` then `Part B queue rail UX` | Post-merge live hardening: reopen-safe sync semantics + readable inbox left rail. | Done (merged via `PR #933`) |
| Wave12 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md` + `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md` | One PR preferred for feature + post-merge live-validation follow-up | Server-owned policy-based routing automation on current reassignment surfaces (`least_open_cases`, no hidden auto-routing) + precise live validation contract. | Done (merged via `PR #934`; live mutation path blocked without explicit safe `INSPECT_CASE_LIVE_CASE_ID`) |
| Wave13 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md` | Split allowed and expected: `Part A backend business-status contract`, `Part B queue/header simplification` | Ввести один понятный operator business status и убрать лишний badge-noise в `Заявках`. | Done (merged via `PR #935`) |
| Wave14 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md` | Split allowed and expected: `Part A backend queue-view contract`, `Part B frontend queue migration` | Перевести queue views на server-owned semantics и убрать local-only approximation из левой очереди. | Done (merged via `PR #936`) |
| Wave15 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md` | Split allowed and expected: `Part A feedback contract`, `Part B action-specific receipts` | Убрать raw technical reason-codes из operator UX и разделить business outcome от secondary sync warnings. | Done (merged via `PR #937`) |
| Wave15 Live Validation | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md` | No feature PR; evidence gate after Wave15 merge | Подтвердить на live backend без mocks, что `reopen` и sync-bearing action больше не показывают raw technical feedback менеджеру. | Done (closed by Wave22 live-proof evidence on safe demo case `2e2de879-e4be-405e-83f6-c11dd95cad65`) |
| Wave16 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md` | Split allowed and expected: `Part A case action surface`, `Part B queue rail simplification` | Полностью пересобрать перегруженные operator surfaces в `Заявках`: action area и левую очередь. | Done (merged via `PR #938`) |
| Wave17 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1.md` | Split allowed and expected: `Part A filter contract`, `Part B rail UX cleanup` | Разделить queue mode, owner scope, advanced diagnostics и presentation prefs, чтобы фильтры в `Заявках` перестали конфликтовать логически и визуально. | Done (merged via `PR #939`) |
| Wave17 Closeout | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-closeout-a1.md` | No new PR; decision gate for `PR #939` | Подтвердить, что Wave17 закрыл корень конфликта фильтров и не требует отдельного follow-up до новых операторских evidence. | Done (local review complete; PR #939 merged) |
| Wave18 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave18-a1.md` | Split allowed and expected: `Part A contract extraction`, `Part B rollout + verification` | Довести фильтры `Заявки` до строгого filter-state correctness contract и доказать это deterministic coverage. | Done (merged via `PR #940`) |
| Wave19 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md` | Planning/decomposition block only; no product PR | Зафиксировать общую semantic chain `бот -> заявка -> менеджер -> запись -> история` и atomic implementation program без повторения spot-fix подхода. | Done |
| Wave20 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md` | Split allowed and expected: `Part A operator mode contract`, `Part B history/archive rail` | Пересобрать IA панели `Заявки`: first-screen `Открытые / Закрытые / Все`, queue views only for open-mode, явный filter drawer и history/archive surface. | Done (merged via `PR #941`) |
| Wave21 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md` | Split allowed and expected: `Part A semantic context`, `Part B booking-state propagation` | Довести бесшовную semantic chain между ботом, заявкой, действиями менеджера и календарём `Записи`, чтобы case/business state и booking state объясняли друг друга. | Done (merged via `PR #942` and `PR #943`) |
| Wave22 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md` + `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-live-proof-a1.md` | Split executed: `Part A deterministic proof` merged via `PR #944`; `Part B live-proof closure` merged via `PR #946` | Закрыть программу forbidden-state matrix, deterministic acceptance и live no-mocks validation без fake-pass. | Done (deterministic proof merged via `PR #944`; explicit live proof + helper hardening merged via `PR #946`) |
| Wave23 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md` | Planning/decomposition block only; no product PR | Провести owner-approved post-closeout defect clustering and lock the next maturity sequence without reopening closed correctness claims. | Done |
| Wave24 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md` | Split executed: backend canon + frontend restore rollout | Ввести server-owned `Queue State Canon` for inbox/calendar before any saved views, managed presets, shareable URLs, or richer routing work. | Done locally; `PR #947` opened |
| Wave25 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md` | Split allowed and expected: `Part A personal catalog backend`, `Part B save/apply frontend UX` | Добавить personal named saved views для `Заявки` и `Записи` поверх `Queue State Canon`, не смешивая их с team presets/share URLs. | Done locally; `PR #947` updated |
| Wave26 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1.md` | Split allowed and expected: `Part A managed preset backend`, `Part B frontend governance/default rollout` | Добавить managed team presets для `Заявки` и `Записи` на том же saved-view object: owner/admin-managed branch/role defaults without forking a second preset model. | Done locally; opened `PR #948` |
| Wave27 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave27-a1.md` | Split allowed: `Part A single-view read contract`, `Part B URL sync + copy-link UX` | Добавить shareable queue URLs для `Заявки` и `Записи` через explicit queue params + optional `view_id`, без opaque blobs и без richer routing. | Done locally; `PR #948` updated |
| Wave28 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave28-a1.md` | Split allowed: `Part A follow-up governance contract`, `Part B history mode + queue UX rollout` | Поднять `Записи` до supervisor-grade governance: explicit `follow-up owner`, `due`, and `history/archive` mode before richer routing. | Done locally; `PR #948` updated |
| Wave29 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1.md` | Split allowed: `Part A backend scoring contract`, `Part B explicit policy selectors in current routing surfaces` | Реализовать richer routing v1 as an opt-in explainable policy `follow_up_sla_balance` over explicit booking follow-up continuity and SLA-sensitive load, without silently replacing `least_open_cases`. | Done (merged) |
| Wave30 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md` | Split allowed: `Part A backend routing-profile contract`, `Part B Team/reassign UI rollout` | Ввести server-owned assignee routing profiles (`available/paused/follow_up_only` + optional capacity) before any skill/presence-aware routing or routing v2. | Done (merged via `PR #950`) |
| Wave31 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md` | Planning/decomposition gate only; no code until activation | Решить, нужен ли вообще следующий routing layer после Wave30, и если да — открыть только bounded routing v2 на реальных server-owned capability inputs. | Re-checked after Wave35: explicit no-go; stay on Wave29/Wave30 until new server-owned capability inputs exist |
| Wave32 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md` | Docs-only audit block; no product code until closure | Провести полный deep audit по `Заявки` и `Записи`: визуальный шум, action hierarchy, logic leakage, real operator coverage, and next execution order for surface decomposition. | Done |
| Wave33 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md` | One PR preferred; Inbox-only bounded frontend diff + deterministic workflow updates | Пересобрать Inbox first screen: оставить только triage controls (`mode`, `queue slice`, `search`, `owner scope`, `refresh`) и вынести saved views/share, advanced filters, view prefs и bulk flows в secondary surfaces. | Merged via `PR #952` |
| Wave34 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md` | One PR preferred; Calendar-only bounded frontend diff + deterministic workflow updates | Пересобрать Calendar first screen: оставить queue triage primary и вынести filters, saved views/share, scheduling, booking governance/actions в secondary surfaces. | Merged (stacked `PR #953`, landed to `main` via `PR #956`) |
| Wave35 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md` | One PR preferred; proof-only bounded diff over rebuilt surfaces | Закрыть operator workflow/layout proof: saved views, team presets, share URLs, follow-up governance, routing-profile restrictions, and medium-width assertions on top of Wave33/Wave34. | Merged (stacked `PR #954`, landed to `main` via `PR #956`) |
| Wave36 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1.md` | One PR preferred; split allowed into `Part A operator surface/copy` then `Part B guided booking composer + misuse proof` | Полностью пересобрать `Записи`: plain-language operator copy, sanitized follow-up ownership, guided booking composer, strong inline validation, visual review after each phase, and valid/invalid interaction proof. | Merged via `PR #958`, but acceptance invalidated by post-merge operator evidence; superseded by `Wave37` |
| Wave37 | `TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md` | Split expected and mandatory: `Part A booking entry + slot discoverability`, `Part B guardrails/copy/actions`, `Part C operator proof + visual acceptance` | Довести `Записи` до реально рабочего operator flow после merged `Wave36`: focused create-booking flow, service-first time discovery, intuitive language, hard guardrails, and full valid/invalid proof. | Merged via `PR #959`, but post-merge operator evidence reopened Calendar under `Wave38` |
| Wave38 | `TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md` | Split mandatory: `Part A filter-state contract`, `Part B phone/composer hardening`, `Part C booking lifecycle completion`, `Part D operator proof + visual acceptance` | Довести `Записи` до полного post-merge operator-grade состояния: deterministic filters, natural phone input, and safe edit/reschedule/cancel lifecycle with full valid/invalid proof. | Merged via `PR #960` |
| Wave39 | `TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1.md` | Split mandatory: `Part A action registry + scenario matrix`, `Part B backend safety contract`, `Part C frontend state machines + fail-closed UI`, `Part D exhaustive proof + visual acceptance`, `Part E observability + post-merge replay` | Закрыть оставшийся системный риск `Записи`: сделать все действия и под-действия вкладки bounded, version-safe, actor-safe, and regression-resistant instead of relying on page-local orchestration. | Merged via `PR #961`; post-merge replay complete on `main` |

## Wave-by-wave closure contract (mandatory)
1. `Wave5` closes only when SLA перестает быть абстрактным и становится action-driven на сервере и в ключевых UI surface.
2. `Wave6` closes only when менеджер/админ может не только взять/закрыть кейс, но и передать, отложить, переоткрыть и делать массовые действия.
3. `Wave7` closes only when макрос может менять не только текст, но и состояние/operator action.
4. `Wave8` closes only when переход `кейс -> запись -> кейс` перестает быть route-friction сценарием и становится единым рабочим экраном.
5. `Wave9` closes only when очередь становится управляемой для supervisor/admin на масштабе, а не только удобной для одного менеджера.
6. `Wave10` closes only when reassignment stops being a blind name-pick and shows factual workload signals in the current operator surfaces.
7. `Wave11` closes only when `Вернуть в работу` перестает порождать ложные external sync errors, а compact queue rail снова становится читаемым рабочим инструментом для менеджера.
8. `Wave12` closes only when routing recommendation перестает быть клиентской подсказкой и становится серверным policy contract для single-case и bulk flows без скрытой автоматики.
9. `Wave13` closes only when менеджер видит один понятный business status заявки вместо смеси raw status/secondary technical badges, а SLA остается отдельным next action.
10. `Wave14` closes only when ключевые queue views больше не фильтруются локально по текущей странице, а используют server-owned semantics и честные counts.
11. `Wave15` closes only when operator UI stops leaking raw technical reason-codes and clearly separates successful case state change from secondary sync warnings.
12. `Wave15 Live Validation` closes only when live no-mocks evidence proves the new operator feedback semantics on a safe explicit case, or closes with a precise blocker instead of a fake pass.
13. `Wave16` closes only when `Передать / Отложить / Вернуть в работу` and the left queue rail become readable, hierarchical, and business-clear without regressing the current workspace loop.
14. `Wave17` closes only when queue view, owner scope, and advanced refinements stop fighting each other and the inbox first screen exposes one clear filtering model.
15. `Wave17 Closeout` closes only when there is an explicit merge-go/no-go verdict for `PR #939` and an explicit answer whether a Wave18 follow-up is required now.
16. `Wave18` closes only when filter precedence, role gating, persistence, and request-param emission are deterministic and do not silently violate business logic.
17. `Wave19` closes only when Owner requirements are translated into one explicit semantic chain and atomic follow-up waves with no hidden scope remain.
18. `Wave20` closes only when `Заявки` first-screen clearly separates `Открытые / Закрытые / Все`, and archive/history access no longer depends on hidden advanced controls.
19. `Wave21` closes only when bot-origin semantics, case lifecycle, and booking lifecycle form one coherent operator story with no contradictory surface states.
20. `Wave22` closes only when manager/admin matrix + live evidence prove that forbidden states are excluded and the new semantic model is stable.
21. `Wave32` closes only when the remaining operator defect is explicitly reframed as surface architecture + workflow proof debt, and the next execution order is decomposition-first rather than more feature accretion.
22. `Wave33` closes only when Inbox first screen keeps only the five triage controls and the removed governance/configuration flows remain reachable from secondary surfaces with deterministic workflow proof still green.
23. `Wave34` closes only when Calendar first screen keeps queue triage primary, and filters/saved views/share/scheduling/follow-up governance move behind secondary surfaces with deterministic workflow proof still green.
24. `Wave36` historical closure claim is no longer sufficient on its own: merged operator evidence showed the guided flow still failed real time-selection discoverability and operator understanding.
25. `Wave37` closes only when Calendar booking creation is explicitly operable end-to-end (`услуга -> мастер -> день -> время -> клиент -> подтверждение`), blocked states are visible and understandable, terminology/actions are plain-language, and every primary control plus sub-object has valid/invalid proof and medium-width visual acceptance.
26. `Wave38` closes only when Calendar filters have an explicit `draft -> applied` contract, phone input supports natural typing/deletion/paste, existing bookings can be edited/rescheduled/cancelled safely, and the full valid/invalid plus visual matrix is green.

## Post-closeout maturity sequence (mandatory)
1. `Wave24 Queue State Canon`: make inbox/calendar queue state server-owned and reproducible before any naming/sharing layer is added.
2. `Saved views + managed presets`: keep personal views and admin/team defaults on the same queue-state model instead of forking separate contracts.
3. `Shareable queue URLs`: make URLs point to canonical queue state or future view ids, not opaque browser-local blobs.
4. `Bookings supervisor-grade governance`: add follow-up owner/due/history semantics to `Записи` before using them as routing signals.
5. `Wave29 richer routing v1`: add opt-in explainable scoring over explicit booking governance and SLA-sensitive load without silent default replacement.
6. `Wave30 routing profiles`: add server-owned assignee routing status/capacity/manual restriction signals before any skill/presence discussion.
7. `Wave32 UX/logic audit`: before any routing v2, prove what is now wrong in the operator surfaces and lock the decomposition/testing order.
8. `Wave33 Inbox decomposition`: reduce `Заявки` first screen to pure triage and move secondary governance/configuration flows out of the primary rail.
9. `Wave34 Calendar decomposition`: apply the same primary/secondary surface discipline to `Записи`.
10. `Wave35 operator proof`: extend deterministic proof from business logic to real workflow/layout and medium-width assertions.
11. `Routing v2 / capability modeling`: remains explicitly blocked after Wave31 re-check; `Wave36` and `Wave37` merged, but Calendar still needs `Wave38` before any return to backlog work.

## TP/PR linkage rules (mandatory)
- Если wave не помещается в один PR, split обязан быть зафиксирован прямо в wave TP до начала part-реализации.
- `Part B` запрещен без green evidence по `Part A` и без обновленного `Next-block contract`.
- Следующий wave TP открывается только после explicit closeout предыдущего wave в session log.
- Никакая новая фича не может уходить в "wave later" без явного follow-up TP ID.

## Plan (1..N)
1. Record the post-closeout defect clusters and the primary architectural blocker in the master canon.
2. Link the new `Wave23` planning block and `Wave24` execution block from the closed master program.
3. Sync session/state/structure docs to the same follow-up sequence.
4. Keep the original program closed while making `Wave24 Queue State Canon` the only valid first unblocker for future maturity work.

## DoD
- Master TP still declares the original `Заявки/Записи` reconstruction closed.
- Post-closeout defect analysis is visible from the master TP and points to `Wave23`/`Wave24`.
- There is no ambiguity that `Queue State Canon` is the first execution block before saved views/presets/shareable URLs/routing.
- Session, state, and structure docs all point to the same follow-up plan.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave23|Wave24|Queue State Canon|Post-closeout maturity analysis|Post-closeout maturity sequence" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "wave23|wave24|Queue State Canon" docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/SESSION_INDEX.md STRUCTURE.md STATE.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && SESSION_AGENT=a1 scripts/session_check.sh`

## Evidence
- Git diff over the canon docs and new follow-up TPs.
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`
- Updated session/state/structure pointers.
- Session check output.

## Release safety (mandatory)
- **Rollout:** docs-only canon sync; no runtime/product rollout in this master refresh.
- **Go/no-go:** merge only if the canon stays internally consistent and `SESSION_AGENT=a1 scripts/session_check.sh` remains green.
- **Rollback:** revert the docs-only follow-up changeset and restore the previous active task-package pointer.

## Rollback
- `git revert REVISION_SHA`
- Re-run the doc checks and `SESSION_AGENT=a1 scripts/session_check.sh`.
- Restore the previous follow-up pointer only if the post-closeout plan must be withdrawn.

## No-go
- Reopen the closed Wave22 correctness program by stealth.
- Start richer routing before queue-state canon exists.
- Build separate incompatible models for personal views, team presets, and shareable URLs.
- Make opaque URL blobs or browser-local state the primary contract for future queue sharing.

## Риски/блокеры
- If `Wave24` is weakened into another frontend-only cleanup, the same reproducibility defect will remain.
- If personal views and team presets fork into separate models, follow-up governance will drift immediately.
- If calendar follow-up ownership/history is skipped, future routing will optimize against an incomplete operational model.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: routing v2 remains explicitly deferred after the Wave31 no-go; the only accepted Calendar residual during `Wave38` is that actionable-owner/customer-assist truth still comes from existing generic sources until the forward fix proves whether a bounded API follow-up is truly necessary.
- `Why not in this block`: the immediate priority is to restore a fully operable Calendar workflow on merged `main`, not to widen the backend model prematurely.
- `Risk if deferred`: if real production data still mixes actionable and technical identities or makes repeat-booking assistance too weak after `Wave37`, a bounded follow-up API contract will still be needed.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave27-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave28-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md`.
- `Expiry/trigger to stop deferral`: if `Wave38` still cannot make filters deterministic or complete the booking lifecycle safely with current APIs, open the bounded API follow-up immediately instead of weakening the UX contract.

## Next-block contract (mandatory)
- `Next block objective`: `Wave38 Part A/B` are now green locally; execute `Part C` next (booking lifecycle completion), then `Part D` operator proof + visual acceptance, and only after that decide whether a bounded Calendar API follow-up is needed or whether work can return to `UX-08` / `UX-20` / `UX-26` without reopening routing v2.
- `First deterministic check command`: `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave38|Part C|edit/reschedule/cancel|calendar-operator.spec.ts|CaseBookingsPanel|PATCH /calendar/bookings" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md STATE.md docs/CONSOLE_AUDIT/UX_BACKLOG.md`
- `Blocked-by conditions`: any attempt to reopen live filter writes from the panel, keep destructive phone formatting, ship edit/cancel without backend contract and proof, or move to other backlog work before `Wave38` closes.
- `Owner role for closure`: Brain / Top Architect.
