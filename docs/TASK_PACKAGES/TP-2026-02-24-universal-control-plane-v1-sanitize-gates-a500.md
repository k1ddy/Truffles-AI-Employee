# TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500

## Block identity
- `BLOCK_ID`: UCPV1-GATES-SANITARY
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE2-SLICE2-IMPL1
- `UNLOCKS`: UCPV1-PHASE2-SLICE2-IMPL2

## Название/цель
Санитарный контур для program-трека `universal_control_plane_v1`: включить строгое zero-context enforcement только по явному opt-in в session log, без влияния на параллельные реализации.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Invariant
- Параллельные worktree/ветки не блокируются нашими контрольно-качественными правилами.
- `truffles-main/main` не используется как рабочая директория.
- Zero-context полнота блоков становится проверяемой для нашего program-трека.

## Scope
- Добавить в `scripts/session_check.sh` opt-in zero-context gate (`required|off|optional`) на основе session metadata.
- Зафиксировать отдельный zero-context блок в `docs/BLOCK_GRAPH.yaml`.
- Подготовить session metadata для включения gate только в нашей сессии.
- Обновить runbook для явного protocol-level opt-in.

## Out of scope
- Любые изменения чужих worktree/веток.
- Принудительное включение zero-context gate для всех сессий проекта.
- Изменения runtime behavior или business logic.

## Touch-list
- `scripts/session_check.sh`
- `docs/SESSIONS/SESSION-2026-02-22-universal-control-plane-v1-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
- `docs/runbooks/EXECUTION_CYCLE.md`
- `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`
- `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`

## Plan (1..N)
1. Добавить в `session_check` opt-in enforcement, читающий `zero_context_*` поля только из текущей session log.
2. Оформить отдельный block-artifact pair (TP/Report) для санитарного контура.
3. Подключить блок в `BLOCK_GRAPH.yaml` как зависимость перед `UCPV1-PHASE2-SLICE2-IMPL2`.
4. Включить `zero_context_gate: required` в текущей session log только для нашего трека.
5. Прогнать проверки и зафиксировать outcomes в report.

## DoD
- `scripts/session_check.sh` валидирует zero-context block только при `zero_context_gate: required`.
- Для текущей сессии включен zero-context enforcement через session metadata.
- `docs/BLOCK_GRAPH.yaml` отражает новый блок и корректные `depends_on/unlocks`.
- Проверки `bash -n`, `zero_context_gate`, `session_check` проходят.

## Checks
- `bash -n scripts/session_check.sh`
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --report docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --graph docs/BLOCK_GRAPH.yaml`
- `scripts/session_check.sh`

## Evidence
- Diff в `scripts/session_check.sh`.
- `docs/BLOCK_GRAPH.yaml` с новым `BLOCK_ID`.
- Session metadata в `docs/SESSIONS/SESSION-2026-02-22-universal-control-plane-v1-a500.md`.
- Report с командами и результатами.

## Rollback
- Revert commit этого блока.
- Удалить `zero_context_*` поля из session log текущего трека.
- Вернуть `BLOCK_GRAPH.yaml` к предыдущему состоянию.

## No-go
- Не включать global hard gate, который сломает чужие параллельные задачи.
- Не менять чужие ветки/worktree.
- Не выполнять работу в `truffles-main/main`.

## Risks/Blockers
- Исторические phase reports не в полном zero-context формате; gate включается по session opt-in, поэтому миграция делается поэтапно.
- Если `zero_context_*` пути в session metadata устареют, `session_check` корректно упадет и остановит commit.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml`
- `Do not touch`: чужие session logs и другие worktree
- `Open risks`: постепенная миграция старых фазовых документов к новому шаблону
- `First command to verify`: `scripts/session_check.sh`
