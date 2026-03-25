# TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-REUSE-FROZEN-REWORK-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-AUTHORITY-CLOSURE-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-authority-closure-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-HANDOVER-REUSE-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded frozen rework for the next surviving live seam after pending-resume authority closure. This block must delete or reduce `_reuse_active_handover(...)` in frozen `decision.py` to a bounded owner-surface invocation in `state_service.py`, without claiming closure of the full handover lifecycle.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-authority-closure-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Baseline commands`:
  - `sed -n '8394,8476p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '^def get_active_handover|^def _reuse_active_handover' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1054,1538p' truffles-api/app/services/state_service.py`
  - `rg -n 'reuse_active_handover_captures_interaction_state_in_pending_resume|reuse_active_handover_preserves_existing_pending_snapshot' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - `_reuse_active_handover(...)` in frozen `decision.py` still owns active-handover lookup, pending-resume sync outcome handling, state transition, Telegram notification, escalation trace, and return.
  - `state_service.py` already owns the closest neighboring ownership family: handover reopen/escalate/resolve/return plus pending-resume sync.
  - `_has_pending_booking_resume_contract(...)` and related thin wrappers are not the next progress unit.

## One web search (mandatory before implementation)
- **Query (exact):** `Move Function site:refactoring.com/catalog`
- **Date/time (local):** `2026-03-17 22:46 +0500`
- **Sources opened (from this query):**
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** when behavior leans on another module's collaborators, move the function so the old site becomes a thin call or disappears.
- **Decision:** `reuse/integrate` — move handover-reuse orchestration into `state_service.py` and leave frozen `decision.py` with bounded invocation only.
- **Rejected options:**
  - another local helper chain in `decision.py`
  - thin-wrapper cleanup as the claimed progress unit
  - broad handover lifecycle rewrite in one block

## Root cause (mandatory)
- **Symptom:** after pending-resume authority closure, the next live frozen seam is broader handover-reuse orchestration in `decision.py`.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8407-8476`.
  2. inspect `truffles-api/app/services/state_service.py:1054-1538`.
  3. inspect `truffles-api/tests/test_message_endpoint.py:45664-45811`.
- **Evidence:** frozen `decision.py` still owned active-handover lookup, pending-resume sync outcome handling, state transition, Telegram notification, and escalation trace inside `_reuse_active_handover(...)` before this block.
- **Five Whys:**
  1. `_reuse_active_handover(...)` stayed in frozen `decision.py` because the earlier bounded cuts targeted narrower pending-resume seams first.
  2. those narrower cuts stopped at the point where the remaining live seam widened from pending-resume-only behavior into broader handover reuse orchestration.
  3. broader handover reuse orchestration remained inline because neighboring handover ownership had already moved into `state_service.py`, but this coordinator body had not.
  4. the coordinator body kept surviving because thin wrapper residue could still distract the block sequence away from the larger live seam.
  5. without an explicit closure audit, the program would keep risking wrapper farming instead of deleting the next real frozen authority.
- **Root cause statement:** `_reuse_active_handover(...)` still owns a live runtime path in frozen `decision.py` even though adjacent handover and pending-resume state machinery already lives in `state_service.py`.
- **Fix mechanism:** move the orchestration body into `state_service.py` with runtime hooks, then reduce frozen `decision.py` to bounded invocation.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing handover functions in `truffles-api/app/services/state_service.py`, existing pending-resume sync logic in `truffles-api/app/services/state_service.py`, and existing direct `_reuse_active_handover(...)` endpoint tests in `truffles-api/tests/test_message_endpoint.py`.
- **External reuse:** Martin Fowler `Move Function` guidance from `https://refactoring.com/catalog/moveFunction.html` to move behavior to the module that already owns the closest collaborators.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded frozen rework with targeted reuse-path tests only.
- **Go/no-go signals:** `_reuse_active_handover(...)` no longer owns runtime authority inline in `decision.py`; targeted tests and governance checks green.
- **Rollback:** revert `state_service.py`, `decision.py`, matching tests, and waiver lines.
- **Post-release monitoring window:** local-only validation for this block; no staged rollout beyond required targeted tests and governance checks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted handover-reuse tests plus governance checks.
- **Stop condition:** if `_reuse_active_handover(...)` cannot be reduced without broadening into full handover rewrite, stop with `GAP`.
- **Escalation path:** `Top Architect`

## Invariant
- no edits to `truffles-api/app/routers/webhook/booking.py`
- no claim of full handover lifecycle closure
- no thin-wrapper cleanup counted as progress without authority deletion

## Scope
- add one handover-reuse owner surface in `truffles-api/app/services/state_service.py`
- reduce frozen `_reuse_active_handover(...)` in `decision.py` to bounded invocation
- add targeted owner-surface tests if needed
- sync canon/evidence after implementation

## Out of scope
- full handover lifecycle rewrite
- broader escalation architecture rewrite
- thin wrapper cleanup as a standalone progress claim

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one owner-surface runtime contract in `state_service.py` for active handover reuse.
2. Reduce frozen `_reuse_active_handover(...)` to bounded invocation.
3. Update the scoped waiver in `docs/LEGACY_SUNSET.yaml`.
4. Prove the seam with targeted tests and governance checks.
5. Sync canon/session/state with FACT-only evidence.

## DoD
- frozen `decision.py` no longer owns `_reuse_active_handover(...)` inline authority
- owner-surface runtime logic lives in `state_service.py`
- targeted handover-reuse tests stay green
- governance checks stay green

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'reuse_active_handover_captures_interaction_state_in_pending_resume or reuse_active_handover_preserves_existing_pending_snapshot'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'handover_reuse or pending_resume'`

## Evidence
- reduced frozen `_reuse_active_handover(...)` body in `decision.py`
- new owner-surface contract in `state_service.py`
- targeted test results
- updated canon/session/state artifacts

## Rollback
1. Revert `state_service.py` and `decision.py`.
2. Restore waiver scope in `docs/LEGACY_SUNSET.yaml`.
3. Regenerate packet and rerun targeted checks.

## No-go
- no `booking.py` edits
- no full handover lifecycle rewrite
- no weakened quality gates

## Risks / blockers
- `_reuse_active_handover(...)` has many callsites, so the owner surface must preserve test-patch compatibility or tests need bounded updates
- moving the body to `state_service.py` increases service size, so this block should remain strictly seam-reduction and not expand responsibilities further

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** thin pending-resume wrappers remain in frozen `decision.py`; broader handover lifecycle still spans frozen and non-frozen files.
- **Why not in this block:** this block is limited to active handover reuse.
- **Risk if deferred:** the repo would keep a live broader runtime seam in frozen `decision.py` right after pending-resume closure.
- **Linked follow-up Task Package(s):** `TP-2026-03-17-consultant-core-handover-reuse-post-waiver-audit-a922` (to be authored after runtime evidence)
- **Expiry/trigger to stop deferral:** immediately after this bounded reuse cut lands

## Next-block contract (mandatory)
- **Next block objective:** run one post-waiver audit over the remaining handover/pending-resume residual symbols after `_reuse_active_handover(...)` loses authority
- **First deterministic check command:** `rg -n '^def get_active_handover|^def _reuse_active_handover|_has_pending_booking_resume_contract|_derive_pending_booking_resume_boundary_payload' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if `_reuse_active_handover(...)` still owns the live body in frozen `decision.py`, stop with `GAP`
- **Owner role for closure:** `Top Architect`
