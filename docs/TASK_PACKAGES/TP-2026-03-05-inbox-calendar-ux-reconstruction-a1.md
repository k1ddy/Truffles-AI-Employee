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
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`

## Requirement coverage map (mandatory)
| Original requirement | Current state | Closing wave | Atomic split rule |
|---|---|---|---|
| `1. Нет связи между вкладками` | Done | Wave1 | split not allowed |
| `2. Менеджер скроллит вниз, чтобы понять контекст` | Done (first-screen simplified) | Wave1 | split not allowed |
| `3. Непонятные SLA цифры и термины` | Implemented in branch | Wave5 | `Part A backend SLA contract` -> `Part B UI surfaces` if one PR is not enough |
| `4. Вкладка Записи не удобна для управления` | Partially done | Wave6 + Wave8 + Wave9 | explicit split required by capability group |
| `5. Капитальная реконструкция с ориентацией на мировые CRM` | In progress | Master program | closed only after Wave9 or explicit residual waiver |
| `6. Любые недостающие функции и механизмы должны быть проанализированы и вписаны` | In progress | Wave6/Wave7/Wave9 | each missing capability must map to one wave/part |
| `7. Все должно быть связано, интуитивно и без дублей` | In progress | Cross-wave invariant | enforced across all waves |

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
| Wave7 | `TBD follow-up TP` | Split allowed and expected: `Part A action-macro backend`, `Part B macro UI/integration` | Превратить макросы из текстовых в executable operator actions. | Planned |
| Wave8 | `TBD follow-up TP` | Split allowed and expected: `Part A workspace shell`, `Part B queue position/context preservation` | Довести `Заявки/Записи` до единого workspace без потери контекста. | Planned |
| Wave9 | `TBD follow-up TP` | Split allowed and expected: `Part A queue governance`, `Part B routing/admin views` | Supervisor/admin-grade queue governance: team views, columns, routing controls. | Planned |

## Wave-by-wave closure contract (mandatory)
1. `Wave5` closes only when SLA перестает быть абстрактным и становится action-driven на сервере и в ключевых UI surface.
2. `Wave6` closes only when менеджер/админ может не только взять/закрыть кейс, но и передать, отложить, переоткрыть и делать массовые действия.
3. `Wave7` closes only when макрос может менять не только текст, но и состояние/operator action.
4. `Wave8` closes only when переход `кейс -> запись -> кейс` перестает быть route-friction сценарием и становится единым рабочим экраном.
5. `Wave9` closes only when очередь становится управляемой для supervisor/admin на масштабе, а не только удобной для одного менеджера.

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
- `Linked follow-up Task Package(s)`: `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md`, `TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1.md`, `TBD wave7`, `TBD wave8`, `TBD wave9`.
- `Expiry/trigger to stop deferral`: любой новый merge по `Заявки/Записи`, который не уменьшает один из этих residual gaps, требует отдельного owner-approved waiver.

## Next-block contract (mandatory)
- `Next block objective`: закрыть wave6 `Part A` через bounded PR, затем открыть follow-up TP для wave6 `Part B` bulk/supervisor actions.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_state_service.py tests/test_console_cases_helpers.py tests/test_console_openapi_calendar_contract.py`
- `Blocked-by conditions`: wave5 SLA contract должен оставаться зелёным; single-case actions не должны регрессировать first-screen clarity или live inspect fallback.
- `Owner role for closure`: Brain / Top Architect.
