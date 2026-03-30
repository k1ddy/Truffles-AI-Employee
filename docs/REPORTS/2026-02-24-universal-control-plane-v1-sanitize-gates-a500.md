# Universal Control Plane v1 — Sanitary Gate Isolation Block (a500)

Date
- 2026-02-24

## Block identity
- `BLOCK_ID`: UCPV1-GATES-SANITARY
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE2-SLICE2-IMPL1
- `UNLOCKS`: UCPV1-PHASE2-SLICE2-IMPL2

## Input baseline (FACT)
- `scripts/session_check.sh` проверял session ownership и LLM evidence gate, но не имел session-scoped enforcement для zero-context block completeness.
- `scripts/zero_context_gate.sh` существовал, но запускался вручную и не был привязан к session metadata.
- Требование изоляции: параллельные треки не должны блокироваться нашим gate-ужесточением.

## FACT pre-check evidence (before changes)
- `bash -n scripts/session_check.sh && bash -n scripts/zero_context_gate.sh` -> pass
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --report docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --graph docs/BLOCK_GRAPH.yaml` -> pass (`zero_context_gate: OK`)
- `scripts/session_check.sh` -> baseline pass (до включения session-scoped zero-context enforcement)

## One web search evidence
- Historical note: this evidence block is backfilled on `2026-03-27` to keep the legacy zero-context block valid under the current gate contract.
- `Query (exact)`: `github actions bash ripgrep not installed fallback grep script`
- `Date/time (local)`: `2026-03-27 13:47 Asia/Almaty`
- `Sources opened`:
  - `https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions`
  - `https://www.gnu.org/software/grep/manual/grep.html`
- `Outcome`: keep shell portability by adding `grep` fallback; do not require `rg` on CI runners.

## Root cause validation
- Confirmed root cause: historical block artifacts predate the hardened zero-context template and the gate script previously assumed `rg`.
- Validation outcome: once the shell fallback exists, the next blocking condition is the missing mandatory TP/report sections rather than the shell dependency itself.

## Reuse-first outcome
- Reused existing `scripts/zero_context_gate.sh` and the same TP/report pair.
- Avoided creating a second gate path or runner-specific implementation.

## Contract delta
- Добавлен session-scoped opt-in для zero-context gate:
  - `zero_context_gate: required` включает проверку.
  - `zero_context_tp`, `zero_context_report`, `zero_context_graph` задают конкретные артефакты блока.
- Для сессий без этого флага поведение `session_check` не изменяется.
- В `BLOCK_GRAPH` введен отдельный блок санитарного контура перед `UCPV1-PHASE2-SLICE2-IMPL2`.

## Implemented changes
- `scripts/session_check.sh`
- `docs/SESSIONS/SESSION-2026-02-22-universal-control-plane-v1-a500.md`
- `docs/BLOCK_GRAPH.yaml`
- `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
- `docs/runbooks/EXECUTION_CYCLE.md`
- `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`
- `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`

## Checks + outcomes
- `bash -n scripts/session_check.sh && bash -n scripts/zero_context_gate.sh` -> pass
- `scripts/zero_context_gate.sh --tp docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --report docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md --graph docs/BLOCK_GRAPH.yaml` -> pass (`zero_context_gate: OK`)
- `scripts/session_check.sh` -> pass (`zero_context_gate: OK`, `Session OK: 2026-02-22-universal-control-plane-v1-a500`)

## Iteration budget outcomes
- `Max full runs`: `0`
- Only deterministic shell/doc checks were used.
- No expensive suites or repeated exploratory reruns were required.

## Evidence
- `scripts/session_check.sh`
- `docs/BLOCK_GRAPH.yaml`
- `docs/SESSIONS/SESSION-2026-02-22-universal-control-plane-v1-a500.md`
- `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
- `docs/runbooks/EXECUTION_CYCLE.md`

## Release safety decision
- `Decision`: safe to merge as docs/shell-only gate hardening.
- `Why`: no runtime/business behavior changes; rollout risk is limited to session-gate enforcement.
- `Rollback path`: revert shell/doc changes and remove `zero_context_*` metadata if necessary.

## Canon/doc sync updates
- `Updated docs/specs`:
  - `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md`
  - `docs/runbooks/EXECUTION_CYCLE.md`
  - `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md`
  - `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md`
- `Drift resolved`: `yes`
- `If no`: n/a

## Residual GAP / Risks
- Исторические phase-артефакты остаются в старом формате и требуют миграции при следующих блоках.
- Ошибочные пути в `zero_context_*` metadata приведут к fail-fast в `session_check`.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/BLOCK_GRAPH.yaml`
- `Do not touch`: чужие worktree и `truffles-main/main`
- `Open risks`: миграция старых фазовых документов к единому zero-context шаблону
- `First command to verify`: `scripts/session_check.sh`

## Verdict
- `Passed`
