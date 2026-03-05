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

## Название/цель
Обновить ТЗ в формат исполнимой программы: закрыть все бизнес-требования по вкладкам `Заявки` и `Записи` в полном объеме через связанный набор TP/PR волн, без дублирования логики и без разрыва контекста между операторскими действиями.

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

## FACT pre-check (before implementation)
- `Implemented in previous waves (fact)`:
  - Связка `Заявки -> Записи` и контекстный возврат уже внедрены.
  - UX-29..UX-33 в `docs/CONSOLE_AUDIT/UX_BACKLOG.md` переведены в `Fixed/Mitigated`.
- `Remaining architecture gaps (fact)`:
  - SLA в `Заявках` все еще завязан на age-threshold и не выражает формальный action priority contract.
  - `appointments` не содержит явной `case_id` связи на уровне модели; часть связки остается эвристикой по `conversation_id`.
  - `calendar/bookings` выдается list-only (без cursor/has_more), queue-triage масштабируется ограниченно.
  - Реал-тайм обновления операторского контекста основаны на polling, нет событийного канала для управляемой задержки.

## One web search (mandatory before implementation)
- **Query (exact):** `Dynamics 365 Customer Service unified routing queue prioritization assignment methods`
- **Date/time (local):** `2026-03-05T09:37:36+05:00`
- **Sources opened:**
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/queues-omnichannel`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/configure-assignment-rules`
  - `https://learn.microsoft.com/en-us/dynamics365/customer-service/use/work-with-queues`
- **Ready solutions found:** приоритет очереди как формальный сигнал (priority number + routing rules), явные assignment methods, наблюдаемая lifecycle-диагностика work items.
- **Decision (`reuse/integrate/build`):** `integrate` — внедрить приоритеты, причины внимания и operator queue semantics в текущие вкладки `Заявки/Записи` без добавления нового top-level модуля.
- **Rejected options:** отдельный новый "диспетчер" экран как главный путь работы менеджера.
- **Source quality:** high-signal primary source = official Microsoft Learn documentation.

## Root cause (mandatory)
- **Symptom:** менеджеры видят улучшенный UI, но не получают полностью управляемый операционный контур для приоритизации и масштабного triage.
- **Minimal reproduction:** последовательность `входящий кейс -> переход в записи -> приоритизация очереди -> возврат в чат` требует ручных/эвристических решений и не дает контрактной модели срочности.
- **Evidence:** API/model ограничения и UI polling-модель, перечисленные в FACT pre-check.
- **Five Whys:**
  1. Почему теряется бизнес-смысл SLA? Нет явного queue-priority контракта, есть только возраст кейса.
  2. Почему контекст иногда неполный? Связь кейса и записи частично восстанавливается эвристикой.
  3. Почему triage плохо масштабируется? Нет server-side курсоров и формального lane-сигнала в read-model.
  4. Почему менеджерские действия не полностью наблюдаемы? Нет унифицированного action audit/readout в потоке `case-booking`.
  5. Почему это критично? Падает предсказуемость SLA, растет время ответа и риск неверного приоритета.
- **Root cause statement:** отсутствует полный operator-grade контракт между case queue semantics, booking linkage и runtime наблюдаемостью; UI-правки без этого не закрывают ТЗ полностью.
- **Fix mechanism:** завершить программу отдельными волнами с атомарным scope: `queue contract -> runtime reliability/scale`, с явным TP/PR linkage.

## Reuse-first plan (mandatory)
- **Reuse:** существующие `console`/`calendar` роуты, текущие `Inbox/Calendar` страницы, уже реализованные UX-паттерны wave1/wave2.
- **Integrate:** добавить формальный queue/read-model контракт и reliability-слой поверх текущих вкладок.
- **Build only if needed:** только недостающие контракты, миграции и event-stream части, без новой IA.

## Invariant
- Сохраняем LLM-first и deterministic-boundary принципы.
- Не добавляем новые top-level вкладки.
- Не дублируем действия между `Заявки` и `Записи`.
- Любая метрика/статус должна иметь явное бизнес-действие менеджера.

## Scope
- Обновить ТЗ до multi-wave execution model с обязательной связью TP/PR.
- Зафиксировать границы wave3/wave4 так, чтобы закрыть остаток требований без архитектурных костылей.
- Зафиксировать acceptance и release safety условия для полного завершения темы.

## Out of scope
- Немедленная реализация всех wave3/wave4 изменений в этом TP.
- Изменение продуктовой модели вне вкладок `Заявки/Записи`.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`
- `docs/SESSIONS/SESSION-2026-03-05-inbox-calendar-ux-reconstruction-a1.md`

## Plan (1..N)
1. Зафиксировать master-TP как source-of-truth программы и contract map.
2. Привязать wave2 к master и закрыть continuity-разрыв в `Next-block contract`.
3. Создать wave3 TP (backend/data-contract atomics + operator queue semantics).
4. Создать wave4 TP (realtime/observability/scale + production rollout discipline).
5. Проверить link-integrity и mandatory sections по всем wave-документам.

## Execution model (mandatory TP/PR split)
| Wave | TP document | PR policy | Objective | Status |
|---|---|---|---|---|
| Wave1 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md` | PR-1 (completed) | Базовая связка `Заявки и Записи`, first-screen улучшения, SLA copy cleanup. | Done |
| Wave2 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md` | PR-2 (completed) | Action-first queue controls и терминология для оператора. | Done |
| Wave3 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md` | PR-3 (single PR; split allowed into `-part1/-part2` только по TP update) | Formal queue semantics и backend contract consistency. | Planned |
| Wave4 | `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md` | PR-4 (single PR; split allowed into `-part1/-part2` только по TP update) | Realtime reliability, observability, rollout safety на проде. | Planned |
| Closeout | `TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md` | PR-5 (single PR) | Canary/go-no-go/rollback discipline и live lane evidence closure. | Planned |

## TP/PR linkage rules (mandatory)
- Если wave не помещается в один PR, перед split обязателен update соответствующего wave TP с явным `part`-разделением и зависимостями.
- Каждый child TP обязан ссылаться на `BLOCK_ID` master + предыдущую волну в `DEPENDS_ON`.
- Merge следующей волны запрещен без evidence и `Next-block contract` из предыдущей.

## DoD
- Есть master TP с полной программной декомпозицией и четкими связями wave->TP->PR.
- У каждой волны есть собственный TP с mandatory секциями и deterministic checks.
- Все remaining requirements из ТЗ отображены в конкретных волнах, без “потом решим”.
- Между волнами нет дублирования scope и нет логических разрывов.

## Checks
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "## (One web search|Root cause|Residual architecture debt|Next-block contract)" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`
- `cd /home/zhan/worktrees/2026-03-05-inbox-calendar-ux-reconstruction-a1 && rg -n "CONSOLE-INBOX-CALENDAR-UX-RECONSTRUCTION" docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave1-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave2-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`

## Evidence
- Git diff по touch-list.
- Output checks.
- Обновленный session log с ссылкой на master + wave3/wave4 TP.

## Release safety (mandatory)
- **Rollout:** по волнам; каждая волна проходит свой go/no-go до старта следующей.
- **Go/no-go:** mandatory checks + wave-specific tests/evidence + отсутствие open P0 regressions.
- **Rollback:** `git revert` текущего PR и возврат к предыдущей завершенной волне.

## Rollback
- `git revert REVISION_SHA`
- Перезапуск checks для подтверждения восстановленного состояния.

## No-go
- Декомпозиция "на словах" без отдельных TP/PR и ссылок между ними.
- Добавление новых top-level вкладок вместо оптимизации `Заявки/Записи`.
- Ослабление acceptance-гейтов для ускорения merge.

## Риски/блокеры
- Разрастание scope wave3 (migration + API + UI) в один PR.
- Различия данных на live backend для wave4 realtime/evidence.
- Риск regressions при переходе от polling к event-driven модели.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: отсутствует формальный queue-priority контракт и полноценный event-driven контур.
- `Why not in this block`: текущий блок только обновляет ТЗ и программную структуру.
- `Risk if deferred`: UX будет улучшен визуально, но без полного операционного эффекта на проде.
- `Linked follow-up Task Package(s)`: `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave3-a1.md`, `TP-2026-03-05-inbox-calendar-ux-reconstruction-wave4-a1.md`.
- `Expiry/trigger to stop deferral`: любой новый P0 UX/SLA дефект в `Заявки/Записи` требует немедленного старта wave3.

## Next-block contract (mandatory)
- `Next block objective`: реализовать wave3 — формальный queue semantics контракт и устранить эвристическую связь кейса/записи.
- `First deterministic check command`: `cd truffles-api && pytest -q tests/test_console_openapi_calendar_contract.py tests/test_calendar_bookings_router.py tests/test_console_cases_helpers.py`
- `Blocked-by conditions`: wave2 evidence должно оставаться валидным, а master TP не должен иметь open continuity gaps.
- `Owner role for closure`: Brain / Top Architect.
