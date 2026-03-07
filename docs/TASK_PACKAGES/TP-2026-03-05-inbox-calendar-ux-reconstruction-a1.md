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
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE11-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE12-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE13-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE14-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE15-LIVE-VALIDATION-A1`
  - `CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION-WAVE16-A1`

## Название/цель
Обновить ТЗ в формат исполнимой программы: закрыть требования по вкладкам `Заявки` и `Записи` не набором разрозненных правок, а полной последовательностью атомарных wave/part блоков с явной бизнес-логикой, строгой связью между TP/PR и без дублирования действий в интерфейсе.

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

## FACT pre-check (before implementation)
- `Implemented and merged (fact)`:
  - Связка `Заявки -> Записи -> возврат в заявку` уже внедрена.
  - First-screen в `Заявках` упрощен: очередной triage слева, чат в центре, лишние дубли SLA убраны.
  - В `Записях` уже есть action-first queue controls: `lane`, `needs_action`, `attention_reason`, server-side cursor pagination.
  - Связь записи с заявкой стала явной через `appointments.case_id`.
  - Runtime слой уже улучшен до `SSE-first + polling fallback`, есть wave4 release runbook.
- `Remaining product gaps (fact)`:
  - SLA в `Заявках` все еще не выражен как action-driven контракт менеджера; UI использует абстрактные age/ok-warning-breached сигналы.
  - Case actions все еще ограничены `take/resolve/return`; нет `reassign`, `snooze`, `reopen`, `bulk`.
  - Макросы остаются текстовыми; нет action-макросов (`assign/status/snooze/tag`).
  - Workspace между `Заявками` и `Записями` стал связным, но еще не доведен до single-workspace уровня без route-level трения.
  - Для supervisor/admin не хватает полноценных queue governance возможностей: team views, configurable columns, routing/admin actions.
  - Post-merge live feedback выявил новый semantic bug: operator UI still leaks raw sync reason-codes such as `chatflow_failed` and conflates business success with secondary sync warnings.
  - Action area around `Передать / Отложить / Вернуть в работу` remains structurally overloaded: mixed CTA hierarchy, dense reassignment panel, and ambiguous toggle semantics (`Передать` -> `Скрыть передачу`).
  - Compact inbox rail в `Заявках` слишком узкий и перегруженный для текущего количества queue controls, summaries и case cards; это operator-UX defect, а не косметика.

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
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

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
| Wave5 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md` | One PR preferred; split only into `Part A backend contract` then `Part B frontend surfaces` | Action-driven SLA contract вместо абстрактных статусов. | Implemented in branch |
| Wave6 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md` | Split allowed and expected: `Part A single-case actions`, `Part B bulk/supervisor actions` | Добавить `reassign/snooze/reopen/bulk` и operator case control. | Implemented in branch (`Part A`, `Part B1`, `Part B2` in PR `#931`) |
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
| Wave15 Live Validation | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md` | No feature PR; evidence gate after Wave15 merge | Подтвердить на live backend без mocks, что `reopen` и sync-bearing action больше не показывают raw technical feedback менеджеру. | Blocked with precise evidence: explicit safe `INSPECT_CASE_LIVE_CASE_ID` missing; dedicated live mutation test now skips instead of fake-pass |
| Wave16 | `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md` | Split allowed and expected: `Part A case action surface`, `Part B queue rail simplification` | Полностью пересобрать перегруженные operator surfaces в `Заявках`: action area и левую очередь. | Done (merged via `PR #938`) |
| Wave17 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1.md` | Split allowed and expected: `Part A filter contract`, `Part B rail UX cleanup` | Разделить queue mode, owner scope, advanced diagnostics и presentation prefs, чтобы фильтры в `Заявках` перестали конфликтовать логически и визуально. | Done (merged via `PR #939`) |
| Wave17 Closeout | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-closeout-a1.md` | No new PR; decision gate for `PR #939` | Подтвердить, что Wave17 закрыл корень конфликта фильтров и не требует отдельного follow-up до новых операторских evidence. | Done (local review complete; PR #939 merged) |
| Wave18 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave18-a1.md` | Split allowed and expected: `Part A contract extraction`, `Part B rollout + verification` | Довести фильтры `Заявки` до строгого filter-state correctness contract и доказать это deterministic coverage. | Done (merged via `PR #940`) |
| Wave19 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md` | Planning/decomposition block only; no product PR | Зафиксировать общую semantic chain `бот -> заявка -> менеджер -> запись -> история` и atomic implementation program без повторения spot-fix подхода. | Done |
| Wave20 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md` | Split allowed and expected: `Part A operator mode contract`, `Part B history/archive rail` | Пересобрать IA панели `Заявки`: first-screen `Открытые / Закрытые / Все`, queue views only for open-mode, явный filter drawer и history/archive surface. | Done (merged via `PR #941`) |
| Wave21 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md` | Split allowed and expected: `Part A semantic context`, `Part B booking-state propagation` | Довести бесшовную semantic chain между ботом, заявкой, действиями менеджера и календарём `Записи`, чтобы case/business state и booking state объясняли друг друга. | Done (merged via `PR #942` and `PR #943`) |
| Wave22 | `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md` + `TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-live-proof-a1.md` | Split executed: `Part A deterministic proof` merged via `PR #944`; `Part B live-proof closure` stays separate until safe case approval | Закрыть программу forbidden-state matrix, deterministic acceptance и live no-mocks validation без fake-pass. | In progress (`Part A` merged via `PR #944`; live proof blocked pending safe case) |

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

## TP/PR linkage rules (mandatory)
- Если wave не помещается в один PR, split обязан быть зафиксирован прямо в wave TP до начала part-реализации.
- `Part B` запрещен без green evidence по `Part A` и без обновленного `Next-block contract`.
- Следующий wave TP открывается только после explicit closeout предыдущего wave в session log.
- Никакая новая фича не может уходить в "wave later" без явного follow-up TP ID.

## Plan (1..N)
1. Обновить master TP как точную atomic program map.
2. Создать wave5 TP как следующий product block и привязать его к master/session docs.
3. Запустить wave5 implementation с backend-first SLA action contract.
4. После wave5 merge открыть follow-up TP для wave6 только с уже зафиксированным split contract.

## DoD
- Master TP больше не противоречит фактическому состоянию программы.
- Все уже выполненные волны отражены как `Done`.
- Все remaining требования из пользовательского ТЗ отображены в конкретных wave/part блоках.
- Для каждого future wave заранее указано, допускается ли split и как именно он выглядит.
- Session docs указывают на актуальный активный block, а не на уже merged infra follow-up.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "Wave5|Wave6|Wave7|Wave8|Wave9|Requirement coverage map|Atomic split rule" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "## (One web search|Root cause|Residual architecture debt|Next-block contract)" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && scripts/session_check.sh`

## Evidence
- Git diff по touch-list.
- Output checks.
- Session log with updated active TP.

## Release safety (mandatory)
- **Rollout:** по волнам; merge следующей продуктовой волны запрещен без closure предыдущей.
- **Go/no-go:** current wave checks green + no unresolved P0/P1 regressions in prior wave.
- **Rollback:** `git revert` текущего PR и возврат к предыдущему stable wave.

## Rollback
- `git revert REVISION_SHA`
- Повторный прогон wave-specific checks.
- Возврат active session task_package на предыдущий stable block при stop-the-line.

## No-go
- Считать ТЗ закрытым после частичных UX улучшений.
- Создавать новые верхнеуровневые разделы вместо доведения `Заявки/Записи`.
- Дробить wave на части post-factum без обновления TP.
- Прятать remaining gaps за формулировкой "позже" без linked follow-up.

## Риски/блокеры
- Wave5-Wave9 могут расползаться, если не удерживать backend-first split contract.
- Большие монолитные файлы в `console.py`, `calendar/page.tsx`, `CaseList.tsx` повышают стоимость изменений.
- Есть риск переусложнить UI, если сначала делать layout, а не action contract.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: SLA action contract, case actions, action macros, unified workspace, supervisor governance еще не завершены.
- `Why not in this block`: master TP задает программу и не заменяет собой реализацию product blocks.
- `Risk if deferred`: визуально улучшенная console останется частично operator-grade и не закроет ТЗ пользователя полностью.
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md`.
- `Expiry/trigger to stop deferral`: любой новый merge по `Заявки/Записи`, который не уменьшает один из этих residual gaps, требует отдельного owner-approved waiver.

## Next-block contract (mandatory)
- `Next block objective`: выполнить Wave17 filter-contract reconstruction after Wave16 merge, while keeping Wave15 live validation recorded as a precise external blocker until a safe explicit live case is available.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_cases_helpers.py tests/test_console_inbox_macros.py`
- `Blocked-by conditions`: Wave15 must not regress reopen semantics, macro action receipts, or current workspace loop; live validation requires a safe explicit case/scenario.
- `Owner role for closure`: Brain / Top Architect.
