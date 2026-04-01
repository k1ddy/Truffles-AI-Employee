# TP-2026-03-31-consultant-core-continuity-state-normalization-a922

## Название / цель
Нормализовать continuity/state на whole-system hot path так, чтобы canonical runtime state стал единственным активным writer для pending-question continuity, current goal, touched-slice carryover, и derived compatibility snapshots. Совместимые carriers (`context_manager`, `session_memory`, `pending_resume`, top-level expected-reply fields) должны обновляться только как projection от canonical runtime state, а не оставаться самостоятельными авторами continuity.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com read model projection source of truth derived model mutable state`
- Date/time (local): `2026-03-31 12:19 +0500`
- Sources opened:
  - `https://martinfowler.com/bliki/ObservableState.html`
- Source quality:
  - Martin Fowler architecture primary source / high-signal reference
- Ready solutions found:
  - derived/projection state may exist, but mutable observable continuity ownership should remain singular;
  - caches and compatibility mirrors are acceptable only when they do not become externally observable competing state;
  - the right move is to reproject compatibility state from the canonical writer instead of hardening multiple mutable carriers.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing `DialogStateService`, `DialogState`, `ConversationProjectionV1`, and session-memory normalization helpers;
  - integrate runtime compatibility re-projection into the canonical runtime write path;
  - build a dedicated continuity-state normalization guard and tests.
- Rejected options:
  - broad journal-first rewrite;
  - local patches in frozen legacy webhook files as the main fix;
  - leaving `session_memory` / `pending_resume` / `context_manager` as active continuity co-writers.

## Invariant
- Do not reopen fact-plane cutover or direct-truth bypasses.
- Do not add new continuity logic into frozen legacy router files beyond narrowing/adapter projection.
- Do not let `session_memory`, `pending_resume`, `context_manager`, or top-level expected-reply fields outrank canonical runtime state when canonical runtime state exists.
- Do not sync active canon/state/packet until the full continuity block is green.

## Scope
- canonical runtime `DialogState` remains the short-term continuity nucleus
- runtime writes must reproject `context_manager` and `session_memory` from canonical runtime state
- `pending_resume` must remain canonical-restore-only on the active path
- touched-slice carryover must remain canonical and mirrored, not regain legacy authorship
- deterministic guard/test proof for the continuity normalization block

## Out of scope
- boundary constriction
- pack/runtime separation completion
- broad legacy mesh deletion
- operational entrypoint dedupe
- replay or human semantic audit

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-state-normalization-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-continuity-state-normalization-a922.md`
- `docs/CONTINUITY_STATE_NORMALIZATION_GUARD.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/recovery_execution_guard.py`
- `scripts/arch_guard.py`
- `scripts/continuity_state_normalization_guard.py`
- `scripts/touched_slice_continuity_guard.py`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_continuity_state_normalization_guard.py`
- `truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`

## Root cause (mandatory)
### Symptom
The first fact family now uses the explicit fact-plane hot path, but continuity/state still remains split across multiple compatibility carriers. On runtime writes, canonical `DialogState` can hold the correct pending-question / goal / carryover state while `context_manager`, `session_memory`, and top-level expected-reply fields still retain stale values and continue to act like alternate truth surfaces.

### Minimal reproduction
1. Start with stale `context_manager.current_goal`, stale `context_manager.canonical_dialog_state.pending_question_contract`, stale top-level `expected_reply_*`, and stale `session_memory.pending_question_contract`.
2. Execute a canonical runtime write on the hot path with a booking collect turn.
3. Observe that canonical `DialogState` carries the fresh continuity state but compatibility carriers remain stale.

### Evidence
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/state_service.py`

### Five Whys
1. Why does continuity stay mixed after the fact-family cutover? Because runtime writes do not fully reproject compatibility carriers from canonical runtime state.
2. Why is that a blocker? Because stale `context_manager`, `session_memory`, `pending_resume`, and top-level expected-reply fields can keep old continuity alive beside the canonical state.
3. Why is this not just a legacy-reader issue? Because some compatibility carriers are still written and then re-read as continuity inputs.
4. Why must this be fixed at the runtime write seam? Because that is the one place where canonical state is fresh and authoritative.
5. Why is `DialogStateService` the correct fix point? Because it already owns canonical runtime state normalization, compatibility projection helpers, and pending-resume/session-memory transformation logic.

### Broken invariant
If canonical runtime state exists, no compatibility carrier may outrank it or remain stale after the write; compatibility carriers must become derived projections, not competing mutable continuity sources.

### Shared mechanism
Canonical runtime continuity projection and compatibility-carrier demotion.

### Why the surfaced family belongs to that mechanism
The first fact-family cutover moved resolver authority, so the next shared blocker is continuity authorship. The visible residual is no longer fact selection; it is continuity truth still split across carriers.

### Open-world envelope expected to improve after the fix
- booking collect follow-ups on the hot path;
- info-to-booking interruptions that carry pending-question state;
- pending-resume restore paths that should preserve canonical continuity without stale top-level overrides;
- any path that reads `context_manager`, `session_memory`, or top-level expected-reply fields after a canonical runtime write.

### Root cause statement
Canonical runtime state is already present, but runtime writes stop short of reprojecting the compatibility continuity surfaces from that canonical state. As a result, stale compatibility carriers remain observable and can continue to behave like continuity co-owners.

### Fix mechanism
- add canonical compatibility re-projection to the runtime write path;
- make `context_manager` and `session_memory` snapshots derive from the just-written canonical runtime state;
- keep top-level `expected_reply_*` / `current_goal` as derived-only shadows or cleared outputs;
- add deterministic proof that stale continuity carriers are overwritten by canonical runtime state on the hot path.

## Plan
1. Add canonical compatibility re-projection to `DialogStateService.write_runtime_payload(...)`.
2. Ensure runtime writes rebuild `context_manager` and `session_memory` snapshots from canonical runtime state before any pending-resume capture.
3. Add tests that prove stale continuity carriers are overwritten by canonical runtime state on the active path.
4. Add a dedicated continuity normalization guard.
5. Close the block only after runtime tests, architecture tests, guard chain, packet, and diff checks are green.

## DoD
- `DialogStateService.write_runtime_payload(...)` reprojects `context_manager.current_goal`, `context_manager.canonical_dialog_state.pending_question_contract`, and `session_memory.pending_question_contract / active_goal` from canonical runtime state on the active path.
- stale top-level `expected_reply_*` and `current_goal` do not survive a canonical runtime write.
- `pending_resume` capture on the active path uses canonical-derived compatibility snapshots, not stale legacy fields.
- deterministic guard/test evidence proves canonical runtime state overwrites stale compatibility continuity on the active path.
- active docs and packet move from `Narrow Fact-Family Cutover` to `Continuity / State Normalization` only after checks pass.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/continuity_state_normalization_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_resume or current_goal or expected_reply or class_carryover or session_memory"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "touched_slice_class_carryover or pending_resume or current_goal or expected_reply or session_memory"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`
- `pytest -q truffles-api/tests/architecture/test_continuity_state_normalization_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-continuity-state-normalization-a922.md`
- `docs/CONTINUITY_STATE_NORMALIZATION_GUARD.yaml`
- `scripts/continuity_state_normalization_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_continuity_state_normalization_guard.py`
- updated `docs/system_forensics/authority_registry.json`
- updated `docs/system_forensics/compatibility_carrier_inventory.json`

## Rollback
- revert the runtime compatibility re-projection changes in `DialogStateService.write_runtime_payload(...)`
- remove the continuity normalization guard/tests
- restore `Narrow Fact-Family Cutover` as the active block if the continuity block must be abandoned

## No-go
- do not solve continuity by adding new direct writes in frozen legacy webhook files
- do not let `session_memory` or `pending_resume` regain primacy over canonical runtime state
- do not broaden this block into boundary or legacy-mesh cleanup
- do not sync active docs or `STATE.md` before the full block is green

## Risks / blockers
- frozen legacy readers remain live and can still observe derived compatibility snapshots;
- broader service/consult carryover surfaces remain legacy-heavy and are not fully drained here;
- post-owner semantic constriction remains open after this block.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- service/consult carryover adapter surfaces remain legacy-heavy
- broader fact families remain outside the governed continuity slice
- post-owner semantic constriction remains open
- boundary constriction remains open
- legacy mesh drain remains open

### Why not in this block
This block is limited to continuity/state ownership and compatibility-carrier demotion on the active path.

### Risk if deferred
Without this block, canonical runtime state can still coexist with stale observable continuity carriers, and the system keeps multiple effective truth sources alive even after the fact-plane cutover.

### Linked follow-up Task Package(s)
- future post-owner semantic constriction TP
- future boundary constriction TP
- future legacy mesh drain TP

### Expiry / trigger to stop deferral
- stop deferral immediately if any new live path reads stale `session_memory`, `pending_resume`, `context_manager`, or top-level expected-reply/current-goal over the canonical runtime state after a canonical runtime write.

## Next-block contract (mandatory)
### Next block objective
Constrict post-owner semantic reconstruction so planner/executor/runtime shell no longer rebuild meaning-bearing artifacts after the owner speaks.

### First deterministic check command
`python3 scripts/semantic_bridge_growth_guard.py`

### Blocked-by conditions
- continuity carriers still remain stale after canonical runtime writes
- `pending_resume` can still restore stale expected-reply/current-goal over canonical runtime state
- `context_manager` or `session_memory` still outrank canonical runtime continuity on the active path

### Owner role for closure
- Top Architect / Brain
