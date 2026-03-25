# TP-2026-03-17-consultant-core-turn-planner-safe-explicit-handoff-owner-family-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-EXPLICIT-HANDOFF-OWNER-FAMILY-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-ACTIVE-NAME-FAMILY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-active-name-followup-family-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-EXPLICIT-HANDOFF-FAMILY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий admissible richer semantic owner family: explicit ingress handoff snapshots should no longer enter frozen `truffles-api/app/routers/webhook/decision.py` before persistence. This block must complete the bounded family already emitted by `intent_routing.py` for `ingress_explicit_human_request` and `ingress_explicit_frustration_handoff`, reusing existing handoff materialization helpers and the typed owner artifact path without widening into style-reference or generic handoff refactors.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-active-name-followup-family-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "ingress_explicit_human_request|ingress_explicit_frustration_handoff|OwnerCutoverAction|MSG_ESCALATED|_reuse_active_handover|escalate_to_pending" truffles-api/app/core/intent_routing.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `sed -n '334,350p' truffles-api/app/core/intent_routing.py`
  - `sed -n '21964,22049p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1,40p' truffles-api/app/core/turn_executor.py`
- `FACT findings`:
  - explicit human-request and frustration handoff turns are already normalized as one ingress snapshot family in `intent_routing.py`
  - `TurnPlanner` already supports `handoff` outcomes, but owner artifact typing in `TurnExecutor` still exposes only `reply` / `booking_prompt`
  - frozen `decision.py` already has bounded reusable handoff materialization helpers (`_reuse_active_handover`, `MSG_ESCALATED`, `DEFAULT_MANAGER_REQUEST_MESSAGE`) and the safe create path through `escalate_to_pending(...)`
  - style-reference text handoff remains a separate, stateful family because it mutates `style_reference_pending`
- `Detected drift (docs vs code)`: canon says richer owner replacement should prefer broader existing owner families, but the explicit ingress handoff family still falls through frozen legacy despite already having a bounded shared snapshot contract.

## One web search (mandatory before implementation)
- **Query (exact):** `Python typing Literal official docs`
- **Date/time (local):** `2026-03-17 17:18 +0500`
- **Why this query is precise:** the block needs a typed extension of `OwnerCutoverAction` for a direct handoff owner path without weakening runtime contract typing.
- **Sources opened (from this query):**
  - `typing — Support for type hints / typing.Literal` — `https://docs.python.org/3/library/typing.html#typing.Literal`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `typing.Literal` is the correct narrow type surface for extending the explicit owner action set without falling back to untyped `str`.
- **Decision:** `reuse/integrate` — extend the existing `OwnerCutoverAction` union to include `"escalate"` and keep the owner artifact contract typed.
- **Rejected options:**
  - widening owner action typing back to generic `str`
  - adding a new bridge family instead of consuming the existing explicit handoff snapshot family
  - including `style_reference_text` in the same block
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** explicit manager-request and frustration turns still depend on frozen `decision.py`, even though ingress already emits them as one bounded handoff snapshot family.
- **Minimal reproduction:**
  1. Inspect `detect_policy_core_route_snapshot(...)` in `truffles-api/app/core/intent_routing.py`.
  2. Observe that both explicit handoff cases already normalize to `action="handoff"`, `tool_action="handoff"`, `needs_manager=true`.
  3. Inspect `reasoning_core.handle_webhook_payload(...)` and confirm no direct owner handler consumes that family before delegating into frozen `decision.py`.
  4. Inspect `TurnExecutor` and observe that owner artifact typing still lacks a dedicated explicit handoff action.
- **Evidence to capture:**
  - direct owner bypass for create path and reuse path
  - owner artifact / turn outcome for explicit handoff uses typed `action="escalate"`
  - fallback-to-delegate remains clean when owner materialization is unavailable or unsafe
- **Five Whys (or equivalent):**
  1. Why do these turns still hit legacy? Because no direct owner handler consumes the existing ingress handoff family.
  2. Why is a new bridge not needed? Because the family is already defined by existing snapshot reasons in `intent_routing.py`.
  3. Why not take style-reference too? Because style-reference also owns `style_reference_pending` state and is therefore a different, more stateful family.
  4. Why is `TurnExecutor` part of the root cause? Because owner artifact typing currently prevents a typed explicit handoff action from being expressed directly.
  5. Why take this block now? Because it is the next admissible richer owner deletion after the active-name family cutover and removes two legacy seams without widening semantic routing.
- **Root cause statement:** explicit ingress handoff turns already share one normalized semantic family, but new-core execution still lacks a typed direct owner path for safe handoff reuse/create materialization, so those turns keep falling through frozen `decision.py`.
- **Fix mechanism:**
  - extend typed owner action support in `TurnExecutor` to include explicit handoff completion (`escalate`)
  - add one bounded direct owner handler in `reasoning_core` for the explicit handoff snapshot family
  - reuse existing frozen read-only handoff helpers for reuse/create materialization and return to legacy only when that bounded owner path is unavailable or unsafe

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing explicit handoff snapshots in `truffles-api/app/core/intent_routing.py`
  - existing `TurnPlanner.build_from_policy_override(...)`
  - existing `TurnExecutor.build_owner_cutover_artifact(...)`
  - existing frozen helpers `decision_router._reuse_active_handover`, `decision_router.MSG_ESCALATED`, `decision_router.DEFAULT_MANAGER_REQUEST_MESSAGE`
  - existing services `escalate_to_pending(...)` and `send_telegram_notification(...)`
- **External reuse:**
  - official Python `typing.Literal` documentation for the typed owner-action extension
- **Why not reinvent the wheel:** this block should reuse the existing snapshot family and handoff helpers, not introduce another ingress seam or a new handoff runtime subsystem.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one richer owner-family deletion plus a typed owner-execution extension and focused contract coverage.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into style-reference pending/state ownership.
- Explicit handoff owner path must only take over when reuse/create materialization is safely available; otherwise it must fall back to legacy before persistence.

## Scope
- Extend `TurnExecutor` typed owner action support for explicit handoff completion.
- Add one bounded `reasoning_core` direct owner handler for the explicit ingress handoff family.
- Add focused reasoning-core and runtime-contract tests.
- Sync canon/session artifacts if the block is green.

## Out of scope
- `style_reference_text`
- generic handoff refactor
- frozen router files
- broader pending/manager-active state semantics
- proof-path or multi-pack work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-explicit-handoff-owner-family-cutover-a922.md`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Extend `OwnerCutoverAction` with typed explicit handoff support.
3. Implement a bounded `reasoning_core` direct owner handler for `ingress_explicit_human_request` and `ingress_explicit_frustration_handoff`.
4. Reuse existing handoff materialization helpers for reuse/create paths; fall back to legacy when unsafe.
5. Add focused direct-owner and contract tests.
6. Run focused and full validations.
7. Sync canon/session artifacts only if the block is green.

## DoD
- explicit human-request and frustration handoff turns bypass frozen `decision.py` through a typed direct owner path
- owner artifact / turn outcome records `action="escalate"`
- create and reuse paths both stay green
- fallback-to-delegate remains green when safe owner materialization is unavailable
- no new bridge families and no frozen-router edits

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'explicit_handoff_owner or policy_core_handoff_override'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- direct-owner reasoning-core tests for explicit create/reuse/fallback paths
- runtime-contract test proving typed `action="escalate"`
- green full reasoning-core/runtime-contract/architecture checks
- updated source-of-truth / packet showing the explicit handoff family cutover

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** focused explicit handoff tests first, then full reasoning-core + contracts + architecture
- **Stop condition:** if explicit handoff cannot be deleted through the existing snapshot family without widening into style-reference or broader handoff state ownership, stop and return to richer audit instead of forcing another bridge
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-family deletion only; no new entrypoints
- **Go/no-go signals:** focused explicit handoff tests + full reasoning-core/contracts/architecture green; packet/session gates green
- **Rollback:** revert the owner-path, typed action extension, tests, and doc sync
- **Post-release monitoring window:** next block should prefer a richer owner audit over another handoff micro-slice

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - canon may count the explicit ingress handoff family as deleted only if both create and reuse direct-owner paths are proven and unsafe cases still fall back to legacy.

## Rollback
1. Revert the turn-executor / reasoning-core / test / doc changes for this block.
2. Regenerate packet.
3. Re-run guards.

## No-go
- no frozen-router edit
- no new detector family
- no style-reference state ownership in this block
- do not count the block as done unless both explicit handoff family members are proven through direct owner tests

## Risks / blockers
- if owner materialization mutates state before a failed fallback, the legacy delegate can observe dirty transaction state
- if the block silently widens into style-reference or broader handoff semantics, it stops being the bounded richer cut justified by the audit

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader generic handoff / style-reference ownership still remains legacy-owned
  - single continuity writer is still not fully closed
  - boundary owner remains only partially cut over
- **Why not in this block:**
  - this block is limited to the next richer admissible owner family already exposed by the current policy-snapshot surface
- **Risk if deferred:**
  - explicit ingress handoff remains a known richer owner family that still depends on frozen `decision.py`
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - once the explicit handoff family is closed, the next move must return to richer owner audit instead of taking another handoff micro-slice by inertia

## Next-block contract (mandatory)
- **Next block objective:** `richer_owner_replacement_audit_after_safe_explicit_handoff_owner_family_cutover`
- **First deterministic check command:** `rg -n "style_reference_text|handoff|booking_prompt" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py`
- **Blocked-by conditions:** lack of a broader admissible owner seam without new bridge growth
- **Owner role for closure:** `Top Architect`
