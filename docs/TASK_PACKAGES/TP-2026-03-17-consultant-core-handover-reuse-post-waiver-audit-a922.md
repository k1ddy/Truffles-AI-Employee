# TP-2026-03-17-consultant-core-handover-reuse-post-waiver-audit-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-REUSE-POST-WAIVER-AUDIT-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-REUSE-FROZEN-REWORK-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-ESCALATION-NOTIFICATION-FROZEN-REWORK-IMPLEMENTATION-A922`, `CONSULTANT-CORE-HANDOVER-RESIDUAL-GAP-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Run the post-waiver audit after Block X and prove which handover-related frozen seam is still live in `decision.py`. This block must distinguish thin residual helpers from the next real deletable authority seam.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before audit closure)
- `Baseline commands`:
  - `sed -n '8394,8455p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n 'def get_active_handover|def _reuse_active_handover|def _has_pending_booking_resume_contract|def _derive_pending_booking_resume_boundary_payload' truffles-api/app/routers/webhook/decision.py`
  - `rg -n 'result = escalate_to_pending\(|send_telegram_notification\(' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8578,8618p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8758,8794p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - frozen `_reuse_active_handover(...)` is now a thin owner-surface invocation only.
  - frozen `get_active_handover(...)` and the pending-resume wrapper family remain small helper residue and are not the next progress unit by themselves.
  - the next broader live frozen seam is the repeated `escalate_to_pending(...) -> send_telegram_notification(...)` create-notify cluster, including `handover_reopened` derivation, which still decides runtime behavior inline across multiple callsites in `decision.py`.
  - `state_service.py` already owns `escalate_to_pending(...)`, so the nearest reuse-first owner surface is non-frozen and adjacent to this seam.

## Root cause (mandatory)
- **Symptom:** after Block X, frozen `decision.py` still repeats live create-notify handover orchestration across many branches.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8590-8618`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8766-8794`.
  3. inspect `truffles-api/app/routers/webhook/decision.py:11239-11268`.
- **Evidence:** the repeated cluster still creates/reopens pending handover state through `escalate_to_pending(...)`, derives `handover_reopened`, and sends Telegram notification inline in frozen code.
- **Five Whys:**
  1. Block X removed only the active-handover reuse coordinator body.
  2. the create-notify branch stayed because it was spread across many decision branches rather than one helper.
  3. those branches still need the same non-frozen `escalate_to_pending(...)` owner plus notification dispatch.
  4. the cluster stayed inline because no shared non-frozen owner surface yet combined create/reopen outcome with notification outcome.
  5. without a post-waiver audit, the next block could waste time on thin helper residue instead of the live repeated authority.
- **Root cause statement:** the remaining live frozen seam is the repeated pending-escalation create-notify cluster, not the thin helper residue near `_reuse_active_handover(...)`.
- **Fix mechanism:** target one bounded implementation block that moves the repeated create-notify cluster behind a non-frozen owner surface and reduces frozen callsites to bounded invocation.

## Reuse-first plan (mandatory)
- **Internal reuse:** `truffles-api/app/services/state_service.py:1205` already owns `escalate_to_pending(...)`; `truffles-api/app/services/escalation_service.py:789` already owns `send_telegram_notification(...)`.
- **External reuse:** none required for this audit block.

## Invariant
- no thin-helper cleanup is counted as progress
- no claim of full handover lifecycle closure in this audit
- no `booking.py` edits

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen `get_active_handover(...)`; thin pending-resume wrappers; repeated create-notify cluster; broader handover lifecycle callsites.
- **Why not in this block:** audit only.
- **Risk if deferred:** the repo may keep deleting helper residue while the real repeated handover seam stays live in frozen `decision.py`.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-escalation-notification-frozen-rework-implementation-a922.md`
- **Expiry/trigger to stop deferral:** immediate after seam classification.

## Next-block contract (mandatory)
- **Next block objective:** reduce the repeated frozen pending-escalation create-notify cluster to a bounded owner-surface invocation.
- **First deterministic check command:** `rg -n 'result = escalate_to_pending\(|send_telegram_notification\(' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the create-notify cluster cannot be reduced without broadening into a full handover lifecycle rewrite, stop with `GAP`.
- **Owner role for closure:** `Top Architect`
