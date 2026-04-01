# TP-2026-03-17-consultant-core-pending-resume-frozen-rework-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-FROZEN-REWORK-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-REWORK-PLAN-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded frozen rework block for pending-resume continuity. This block must route pending-resume derivation/restore/activation and direct snapshot/restore helpers through `DialogStateService` plus `state_service` owned surfaces, reducing the old helper bodies in frozen `decision.py` and frozen `pending.py` to bounded service invocation only.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-rework-plan-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-frozen-rework-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/pending.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `rg -n "capture_pending_resume_payload|restore_pending_resume_payload" truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py`
  - `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|pending_resume_boundary_payload|pending_resume_boundary_active|pending_handoff_resume_boundary" truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_build_pending_resume_snapshot|_restore_pending_resume|pending_resume" truffles-api/app/routers/webhook/pending.py`
  - `sed -n '590,640p' truffles-api/app/services/state_service.py`
  - `sed -n '1097,1218p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '8558,8795p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '10820,10930p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '111,180p' truffles-api/app/routers/webhook/pending.py`
- `FACT findings`:
  - `DialogStateService` already owns generic pending-resume payload capture/restore in `truffles-api/app/core/dialog_state_service.py:1097` and `truffles-api/app/core/dialog_state_service.py:1151`.
  - `state_service.py` already delegates generic pending-resume capture/restore through those owner methods in `truffles-api/app/services/state_service.py:590` and `truffles-api/app/services/state_service.py:608`.
  - frozen `decision.py` still owns boundary-specific pending-resume helper bodies at `truffles-api/app/routers/webhook/decision.py:8558`, `truffles-api/app/routers/webhook/decision.py:8688`, and `truffles-api/app/routers/webhook/decision.py:8750`, plus activation/preserve flow at `truffles-api/app/routers/webhook/decision.py:10833`.
  - frozen `pending.py` still owns direct snapshot/restore helper bodies at `truffles-api/app/routers/webhook/pending.py:111` and `truffles-api/app/routers/webhook/pending.py:137`.
  - existing tests already cover this family across the owner surfaces and legacy runtime callsites:
    - `truffles-api/tests/test_dialog_state_service.py`
    - `truffles-api/tests/test_state_service.py`
    - `truffles-api/tests/test_message_endpoint.py`
- `Detected drift (docs vs code)`:
  - the target owner exists, but the remaining old helper bodies are still reachable in two frozen files; runtime progress now requires reducing those bodies, not authoring another planning or helper-only block.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" pending resume rework plan`
- **Date/time (local):** `2026-03-17 20:40 +0500`
- **Why this query is precise:** the next runtime block needs one converge path for a legacy capability already split between new and old owners.
- **Sources opened (from this query):**
  - `Parallel Change` — `https://martinfowler.com/bliki/ParallelChange.html`
- **Source quality:** primary architecture guidance from Martin Fowler / Danilo Sato.
- **Existing solutions found:** when the new side already owns part of the contract, the truthful next block is a bounded migrate/contract implementation that moves remaining legacy callsites and then retires the old helper bodies.
- **Decision:** `reuse/integrate` — extend `DialogStateService` and `state_service` just enough to absorb boundary-specific pending-resume semantics, then reduce the frozen helper bodies in `decision.py` and `pending.py` to bounded service calls.
- **Rejected options:**
  - another timeout-owner micro-slice
  - another wrapper around legacy pending-resume helpers
  - reopening tiny continuity micro-slices as if a new non-frozen seam appeared

## Root cause (mandatory)
- **Symptom:** pending-resume continuity still has multiple live owners even though the target owner surfaces already exist.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/core/dialog_state_service.py:1097` and `truffles-api/app/core/dialog_state_service.py:1151` to confirm generic pending-resume payload capture/restore is already implemented.
  2. inspect `truffles-api/app/services/state_service.py:590` and `truffles-api/app/services/state_service.py:608` to confirm non-frozen delegation already reuses those owner methods.
  3. inspect `truffles-api/app/routers/webhook/decision.py:8558`, `truffles-api/app/routers/webhook/decision.py:8688`, `truffles-api/app/routers/webhook/decision.py:8750`, and `truffles-api/app/routers/webhook/decision.py:10833` to confirm frozen boundary-specific pending-resume helpers still remain live.
  4. inspect `truffles-api/app/routers/webhook/pending.py:111` and `truffles-api/app/routers/webhook/pending.py:137` to confirm frozen snapshot/restore helpers still remain live there as well.
- **Evidence to capture:**
  - new owner methods reused by runtime
  - reduced helper bodies in `decision.py` and `pending.py`
  - preserved pending-resume behavior via targeted tests
  - scoped waiver lines for both frozen files
- **Five Whys (or equivalent):**
  1. Why is single continuity owner still incomplete? Because frozen pending-resume helper bodies still execute direct authority.
  2. Why not stop at the existing owner methods? Because they do not yet make the old helper bodies unreachable.
  3. Why is this block admissible? Because the next implementation can reduce concrete old helper bodies in both frozen files.
  4. Why not split into more micro-slices? Because the remaining authority is one asset family across two frozen files.
  5. Why use `DialogStateService` and `state_service`? Because they already own the generic pending-resume contract and are the proven converge path.
- **Root cause statement:** the repo already has the future continuity owner for generic pending-resume payload capture/restore, but frozen `decision.py` and frozen `pending.py` still own boundary-specific derivation, restore, activation, and snapshot helper bodies. The old continuity power shape remains live until those concrete helper bodies are reduced to service-owned calls.
- **Fix mechanism:**
  - extend owner surfaces only where boundary-specific pending-resume semantics are still missing
  - reduce the old helper bodies in `decision.py` and `pending.py` to bounded service invocation only
  - keep tests fixed on contract behavior, not text similarity

## Old authority seam to delete/reduce (mandatory)
- **FACT:** target helper bodies in frozen `decision.py`:
  - `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8558`
  - `_restore_pending_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8688`
  - `_restore_resolved_handoff_resume_boundary(...)` at `truffles-api/app/routers/webhook/decision.py:8750`
- **FACT:** target helper bodies in frozen `pending.py`:
  - `_build_pending_resume_snapshot(...)` at `truffles-api/app/routers/webhook/pending.py:111`
  - `_restore_pending_resume(...)` at `truffles-api/app/routers/webhook/pending.py:137`
- **FACT:** this block does **not** claim deletion of the whole pending lifecycle or all pending branches.
- **INFERENCE:** the block is admissible because it can reduce concrete old helper bodies in both frozen files, not just add another bridge.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - existing tests in `truffles-api/tests/test_dialog_state_service.py`
  - existing tests in `truffles-api/tests/test_state_service.py`
  - existing tests in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
- **Why not reinvent the wheel:** the target owner and partial delegation path already exist; the missing work is reducing the remaining frozen helper bodies and wiring the boundary-specific semantics into the existing owner path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `freeze-waiver-pending-resume-rework`
- **Why this profile fits:** this is a real runtime block that must edit two frozen files in a tightly bounded way.

## Invariant
- no new semantic hardcode families
- no new continuity writers outside the converged owner path
- no claim of whole pending-lifecycle deletion
- pending-resume behavior must stay contract-stable across state service, message endpoint, and pending ack flows

## Scope
- extend owner surfaces for missing boundary-specific pending-resume semantics
- reduce pending-resume helper bodies in frozen `decision.py` and `pending.py` to bounded service invocation only
- add scoped waivers for the exact frozen executable additions
- preserve existing pending-resume behavior with targeted deterministic tests
- sync canon/session artifacts after implementation

## Out of scope
- broader pending lifecycle rewrite
- `booking.py`
- semantic owner work
- proof-path work
- multi-pack closure work

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Extend `DialogStateService` and/or `state_service` with the minimum boundary-specific pending-resume owner methods still missing.
2. Reduce the pending-resume helper bodies in frozen `decision.py` and frozen `pending.py` to bounded service invocation only.
3. Record scoped waiver lines in `docs/LEGACY_SUNSET.yaml`.
4. Prove pending-resume capture/restore and boundary flows remain green through targeted deterministic tests.
5. Sync canon/session/state and rerun governance checks.

## DoD
- the target helper bodies in `decision.py` and `pending.py` are deleted or reduced to bounded service invocation only
- owner logic for pending-resume continuity lives in `DialogStateService` plus `state_service`
- targeted pending-resume tests stay green
- required governance checks are green
- no over-claim that the whole pending lifecycle is deleted

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'pending_resume'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_handoff_pricing_interrupt_preserves_time_followup or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reduced helper bodies in `decision.py` and `pending.py`
- owner-surface additions in `DialogStateService` / `state_service`
- targeted deterministic test results
- updated canon/session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted pending-resume tests only
- **Stop condition:** if the diff cannot reduce concrete frozen helper bodies in both files or starts creating another live writer path, stop and open broader rework escalation instead of growing the block
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded frozen rework with deterministic closure before any rollout
- **Go/no-go signals:**
  - old helper bodies in both frozen files are reduced to bounded owner calls
  - pending-resume capture/restore tests stay green
  - endpoint pending-resume boundary flows stay green
  - governance guards stay green
- **Rollback:** revert owner-surface additions, frozen callsite reductions, and waiver lines, then rerun targeted tests and governance checks
- **Post-release monitoring window:** first pending-resume and pending soft-pass conversations must preserve expected-reply, re-entry, booking context, and trace/meta evidence without reopening the old helper bodies

## Rollback
1. Revert owner-surface additions plus frozen helper-body reductions.
2. Restore `docs/LEGACY_SUNSET.yaml` to the pre-Block-R waiver scope.
3. Regenerate packet and rerun targeted tests plus governance checks.

## No-go
- no broader pending lifecycle rewrite
- no new wrapper-only service counted as progress
- no edits to `booking.py`
- no claim that pending-resume is fully solved beyond the bounded helper-body reduction

## Risks / blockers
- the bounded rework spans two frozen files and must stay tightly limited to pending-resume helper-body reduction
- boundary-specific pending-resume semantics touch expected-reply, booking, session-memory, and re-entry together; splitting them incorrectly could reintroduce multiple live writers

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader pending lifecycle still remains outside this helper family
  - frozen legacy still exists outside the targeted helper bodies
  - single continuity owner is still not full-program complete after this block
- **Why not in this block:**
  - this block only captures the concrete pending-resume helper family already proven as the next admissible seam
- **Risk if deferred:**
  - the team will keep the old continuity helper bodies alive while assuming the new owner already converged
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-pending-resume-post-waiver-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - immediately after the bounded helper-family reduction lands

## Next-block contract (mandatory)
- **Next block objective:** run one post-waiver audit to verify which pending-resume authority remains live after the frozen helper-family reduction and whether another bounded deletion seam still exists
- **First deterministic check command:** `rg -n "_derive_pending_booking_resume_boundary_payload|_restore_pending_handoff_resume_boundary|_restore_resolved_handoff_resume_boundary|_build_pending_resume_snapshot|_restore_pending_resume" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py`
- **Blocked-by conditions:** if implementation leaves the old helper bodies live alongside new owner logic or reintroduces multiple live continuity writers, stop and escalate instead of advancing
- **Owner role for closure:** `Top Architect`
