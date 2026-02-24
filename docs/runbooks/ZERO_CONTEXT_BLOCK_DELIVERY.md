# ZERO-CONTEXT BLOCK DELIVERY

## Purpose

Этот протокол нужен для сценария, где каждый блок выполняет новый агент без памяти и контекста.

Цель:
- связность между блоками,
- полнота реализации каждого блока,
- проверяемое качество без "доверия на слово".

## Contract: что такое "полный блок"

Блок считается полным только если есть все 8 артефактов:
1. `Task Package` (scope/DoD/checks/evidence/rollback/no-go).
2. `Phase/Block Report` с фактическими результатами.
3. Проверки (команды + outcomes).
4. Handoff section (`что сделано / что осталось / риски`).
5. Canon sync (если контракт/правила затронуты).
6. `STATE.md` запись (FACT или GAP).
7. FACT pre-check evidence по коду/контрактам/тестам до начала правок.
8. Drift closeout: docs/specs обновлены в том же блоке или оформлен явный GAP с owner и follow-up block.

Если один пункт отсутствует, блок не закрыт.

## Required IDs

Каждый блок обязан иметь:
- `BLOCK_ID` (стабильный идентификатор),
- `PARENT_BLOCK_ID` (если это slice/wave),
- `DEPENDS_ON` (список предыдущих блоков или `none`),
- `UNLOCKS` (какие блоки может начинать следующий агент).

Обязательная связность программы хранится в:
- `docs/BLOCK_GRAPH.yaml`

## Minimal artifact schema

### Task Package (обязательно)
- `BLOCK_ID`
- `PARENT_BLOCK_ID`
- `DEPENDS_ON`
- `FACT pre-check (before implementation)`
- `Invariant`
- `Scope`
- `Out of scope`
- `Touch-list`
- `Plan`
- `DoD`
- `Checks`
- `Evidence`
- `Doc sync plan (after implementation)`
- `Rollback`
- `No-go`

### Report (обязательно)
- `BLOCK_ID`
- `Input baseline (FACT)`
- `FACT pre-check evidence (before changes)`
- `Contract delta`
- `Implemented changes`
- `Checks + outcomes`
- `Evidence links`
- `Canon/doc sync updates`
- `Residual GAP/Risks`
- `UNLOCKS`
- `Verdict: Passed|Blocked`

## Execution rules for zero-context agent

1. Не читать "всю историю". Читать только:
   - owner canon,
   - конкретный `Task Package`,
   - `docs/BLOCK_GRAPH.yaml`,
   - последний `Report` по `DEPENDS_ON`,
   - последний `STATE.md NOW`.
2. Не продолжать, если `DEPENDS_ON` не закрыт `Passed`.
3. Перед первой правкой выполнить FACT pre-check по живому коду/контрактам/тестам и зафиксировать это в report.
4. Не менять scope без нового TP/re-approval.
5. Не создавать дубли активного `BLOCK_ID`; использовать существующую активную сессию этого блока.
6. Не закрывать блок без проверок, report и drift closeout.

## Handoff contract (в конце блока)

Каждый блок заканчивается секцией:
- `Ready for next agent`
- `Start from`
- `Do not touch`
- `Open risks`
- `First command to verify`

Это обязательный мост для агента с нулевым контекстом.

## Gate command

Для автоматической проверки полноты используйте:
- `scripts/zero_context_gate.sh --tp <path> --report <path>`

Gate валидирует наличие обязательных секций в TP и Report.

## Session-scoped enforcement (без влияния на параллельные треки)

Чтобы включить обязательный gate только для конкретной сессии, добавьте в `docs/SESSIONS/SESSION-...md`:
- `- zero_context_gate: required`
- `- zero_context_tp: docs/TASK_PACKAGES/TP-...md`
- `- zero_context_report: docs/REPORTS/...md`
- `- zero_context_graph: docs/BLOCK_GRAPH.yaml` (optional)

`scripts/session_check.sh` применит zero-context gate только при `zero_context_gate: required`.
Сессии без этого флага продолжают работать без изменений.
