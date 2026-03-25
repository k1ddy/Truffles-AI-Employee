# TP-2026-03-17-consultant-core-pending-resume-authority-closure-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-AUTHORITY-CLOSURE-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-RESUME-REUSE-SYNC-FROZEN-REWORK-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-frozen-rework-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-HANDOVER-REUSE-FROZEN-REWORK-IMPLEMENTATION-A922`, `CONSULTANT-CORE-PENDING-RESUME-THIN-WRAPPER-VERDICT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the closure audit after Block W and prove whether any live pending-resume authority still remains in frozen `decision.py`. This block must distinguish live authority from thin wrappers and identify the next real deletable seam only if one still exists.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-resume-reuse-sync-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before audit closure)
- `Baseline commands`:
  - `rg -n 'pending_resume|resume_boundary|resolved_handoff|handover_reuse|pending_handoff_resume_boundary|session_memory_reset_skipped' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8412,8505p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '_has_pending_booking_resume_contract|_derive_pending_booking_resume_reason|_derive_pending_booking_resume_boundary_payload' truffles-api/app/routers/webhook/decision.py`
  - `rg -n '^def _reuse_active_handover|^def get_active_handover' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - after Block W, `_has_pending_booking_resume_contract(...)`, `_derive_pending_booking_resume_reason(...)`, and `_derive_pending_booking_resume_boundary_payload(...)` remain in frozen `decision.py`, but they are thin wrappers and not reused as live authority elsewhere.
  - the next larger surviving live seam adjacent to the pending-resume track is `_reuse_active_handover(...)`, which still owns active-handover reuse orchestration in frozen `decision.py` and only consumes pending-resume logic through an owner-surface call.
  - `truffles-api/app/services/state_service.py` already owns neighboring handover and pending-resume state transitions (`escalate_to_pending`, `manager_resolve`, `manager_return`, `_reopen_handover`, `_find_recent_resolved_handover`, `_sync_pending_resume_on_handover_reuse`).

## Root cause (mandatory)
- **Symptom:** the pending-resume-specific live authority seams are nearly exhausted, but frozen `decision.py` still owns a broader handover-reuse runtime path that now sits next to thin pending-resume wrappers.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8407-8476`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8479-8492`.
  3. inspect `truffles-api/app/services/state_service.py:1054-1538`.
- **Root cause statement:** pending-resume-specific coordinator authority is effectively collapsed, and the next real frozen authority is broader handover-reuse orchestration rather than another pending-resume helper.
- **Fix mechanism:** classify thin wrappers as residual/non-progress and target `_reuse_active_handover(...)` only if its body can be reduced to bounded owner-surface invocation.

## Reuse-first plan (mandatory)
- `truffles-api/app/services/state_service.py` is the closest existing owner surface because it already owns handover creation/reopen/resolve/return and pending-resume state transitions.

## Invariant
- no thin-wrapper deletion is counted as program progress
- no claim that full handover lifecycle is closed in this audit

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** thin pending-resume wrappers remain in frozen `decision.py`; broader handover-reuse orchestration remains in frozen `decision.py`.
- **Why not in this block:** audit only.
- **Risk if deferred:** the repo may keep farming thin-wrapper cleanup instead of hitting the next real seam.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922.md`
- **Expiry/trigger to stop deferral:** immediate after seam classification.

## Next-block contract (mandatory)
- **Next block objective:** delete or reduce frozen `_reuse_active_handover(...)` to a bounded owner-surface invocation.
- **First deterministic check command:** `rg -n '^def _reuse_active_handover|^def get_active_handover' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if `_reuse_active_handover(...)` cannot be reduced without broadening into full handover rewrite, stop with `GAP`.
- **Owner role for closure:** `Top Architect`
