# TP-2026-03-17-consultant-core-pending-resume-reuse-sync-residual-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-REUSE-SYNC-RESIDUAL-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-RESOLVED-HANDOFF-BOUNDARY-FROZEN-REWORK-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-resolved-handoff-boundary-frozen-rework-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-REUSE-SYNC-FROZEN-REWORK-IMPLEMENTATION-A922`, `CONSULTANT-CORE-PENDING-RESUME-AUTHORITY-CLOSURE-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the residual seam audit after Block V and prove whether the next surviving pending-resume authority in frozen `decision.py` is the handover-reuse sync helper. This block must reject wrapper-only cleanup and select a next move only if one old live authority can actually be deleted.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-resolved-handoff-boundary-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_state_service.py`

## FACT pre-check (before audit closure)
- `Baseline commands`:
  - `sed -n '8398,8455p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8503,8518p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '_sync_pending_resume_on_handover_reuse|_derive_pending_booking_resume_boundary_payload|pending_resume_synced' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '_capture_pending_resume_context|_build_pending_resume_snapshot_payload|_restore_pending_resume_context|_derive_pending_booking_resume_boundary_payload' truffles-api/app/services/state_service.py`
  - `rg -n 'reuse_active_handover_captures_interaction_state_in_pending_resume|reuse_active_handover_preserves_existing_pending_snapshot' truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - frozen `truffles-api/app/routers/webhook/decision.py:8409-8426` still owns `_sync_pending_resume_on_handover_reuse(...)`, which decides whether handover reuse captures a fresh pending-resume snapshot, strips active continuity keys when a snapshot already exists, mutates `conversation.context`, and returns whether the sync changed runtime state.
  - `_sync_pending_resume_on_handover_reuse(...)` is consumed only from `_reuse_active_handover(...)` at `truffles-api/app/routers/webhook/decision.py:8443`.
  - `truffles-api/app/services/state_service.py` already owns the underlying pending-resume capture/restore primitives through `_capture_pending_resume_context(...)`, `_restore_pending_resume_context(...)`, and `_build_pending_resume_snapshot_payload(...)`.
  - frozen `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8510` is now a thin owner-surface wrapper and is not itself the best next progress unit.
  - deterministic endpoint coverage already proves both handover-reuse sync behaviors in `truffles-api/tests/test_message_endpoint.py:45664` and `truffles-api/tests/test_message_endpoint.py:45763`.

## Root cause (mandatory)
- **Symptom:** after Block V, a smaller but still live pending-resume continuity seam remains in frozen `decision.py` during handover reuse.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8409-8426`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8443`.
  3. inspect `truffles-api/app/services/state_service.py:634-704`.
  4. inspect `truffles-api/tests/test_message_endpoint.py:45664-45811`.
- **Evidence:** the frozen helper still mutates `conversation.context`, while the underlying pending-resume capture rules already live in `state_service.py`.
- **Five Whys (or equivalent):**
  1. Why is there still old authority after Block V? Because handover-reuse sync still mutates pending-resume state inline in frozen `decision.py`.
  2. Why is this not just wrapper cleanup? Because the helper decides snapshot preservation vs normalization and mutates runtime context before handover reuse proceeds.
  3. Why is the thin boundary wrapper not the right target first? Because it already delegates the real derivation to `state_service.py` and does not own comparable mutation authority.
  4. Why is `state_service.py` the right owner? Because it already owns pending-resume snapshot capture/restore primitives used by this sync logic.
  5. Why is one more bounded implementation admissible? Because deleting this helper would make one frozen live authority unreachable without broadening into full `_reuse_active_handover(...)` migration.
- **Root cause statement:** the surviving old authority is the handover-reuse pending-resume sync helper in frozen `decision.py`, not the remaining thin derivation wrappers.
- **Fix mechanism:** move the reuse-sync mutation logic into `state_service.py`, then delete the frozen helper and reduce `_reuse_active_handover(...)` to bounded invocation plus trace.

## Old authority seams under audit (mandatory)
- **FACT:** live seam under audit is `_sync_pending_resume_on_handover_reuse(...)` at `truffles-api/app/routers/webhook/decision.py:8409-8426`.
- **FACT:** thin residual wrapper `_derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/routers/webhook/decision.py:8510` remains but is not the next best progress unit.
- **FACT:** this block does not claim closure of `_reuse_active_handover(...)` as a whole.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/state_service.py::_capture_pending_resume_context(...)`
  - `truffles-api/app/services/state_service.py::PENDING_RESUME_CLEAR_KEYS`
  - existing handover-reuse endpoint tests in `truffles-api/tests/test_message_endpoint.py`
- **Why reuse wins here:** the repo already has the continuity primitives; the missing work is moving the remaining mutation authority out of frozen `decision.py`.

## Execution profile
- **TP mode:** `analysis`
- **Doc touch budget (files):** `9`
- **Code dominance:** `docs`

## Invariant
- no runtime change in this audit block
- no claim that broader handover reuse or full pending lifecycle is closed
- no wrapper-only deletion counted as progress

## Scope
- classify the next surviving pending-resume authority after Block V
- decide whether `_sync_pending_resume_on_handover_reuse(...)` is a bounded deletable seam
- lock the next admissible implementation move

## Out of scope
- runtime implementation
- `_reuse_active_handover(...)` full migration
- thin dead-wrapper cleanup as a claimed progress unit
- broader pending lifecycle rewrite

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-residual-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Inspect the remaining pending-resume symbols in frozen `decision.py`.
2. Separate live mutation authority from thin wrappers.
3. Select exactly one next admissible implementation seam, or stop with a residual-only verdict.
4. Lock one machine-readable next move in canon.

## DoD
- the audit names the exact surviving pending-resume live authority after Block V
- the audit states explicitly why thin wrappers are not the next progress unit
- one next admissible implementation seam is locked in canon, or the block stops with a residual-only verdict

## Checks
- `sed -n '8398,8455p' truffles-api/app/routers/webhook/decision.py`
- `sed -n '8503,8518p' truffles-api/app/routers/webhook/decision.py`
- `rg -n '_sync_pending_resume_on_handover_reuse|_derive_pending_booking_resume_boundary_payload|pending_resume_synced' truffles-api/app/routers/webhook/decision.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- seam map for the surviving pending-resume symbols in frozen `decision.py`
- explicit verdict that `_sync_pending_resume_on_handover_reuse(...)` is or is not the next deletable authority seam
- updated canon/session artifacts if the verdict is positive

## Rollback
1. Revert the audit TP and canon/session updates.
2. Regenerate the agent packet.
3. Re-run architecture/governance checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc-only residual audit; no runtime rollout.
- **Go/no-go signals:** seam classification completed and governance checks green.
- **Rollback:** revert audit docs/canon sync and regenerate packet.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** audit plus governance checks only.
- **Stop condition:** if `_sync_pending_resume_on_handover_reuse(...)` proves too entangled with full `_reuse_active_handover(...)`, stop and record a broader rework verdict instead of forcing a cosmetic extraction.
- **Escalation path:** `Top Architect`

## No-go
- no runtime implementation in this block
- no thin-wrapper deletion counted as progress
- no broad handover-reuse rewrite

## Risks / blockers
- the helper is small, so the audit must prove it is still live mutation authority and not mere wrapper residue
- `_reuse_active_handover(...)` also handles state transition and Telegram notification, so scope can widen if not bounded tightly

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - `_sync_pending_resume_on_handover_reuse(...)` remains live in frozen `decision.py`
  - thin wrapper `_derive_pending_booking_resume_boundary_payload(...)` remains in frozen `decision.py`
  - broader `_reuse_active_handover(...)` remains in frozen `decision.py`
- **Why not in this block:**
  - this block is seam classification only
- **Risk if deferred:**
  - the repo would keep a live pending-resume mutation seam in frozen `decision.py` while owner primitives already exist elsewhere
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-frozen-rework-implementation-a922.md`
- **Expiry/trigger to stop deferral:**
  - immediately after the next bounded implementation decision

## Next-block contract (mandatory)
- **Next block objective:** delete the frozen handover-reuse pending-resume sync helper if the seam stays bounded under implementation planning
- **First deterministic check command:** `rg -n '_sync_pending_resume_on_handover_reuse|pending_resume_synced' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the implementation cannot delete `_sync_pending_resume_on_handover_reuse(...)` without broadening into full handover reuse ownership, stop with `GAP`
- **Owner role for closure:** `Top Architect`
