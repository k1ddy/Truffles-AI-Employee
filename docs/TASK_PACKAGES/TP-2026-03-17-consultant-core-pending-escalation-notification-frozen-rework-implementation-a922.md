# TP-2026-03-17-consultant-core-pending-escalation-notification-frozen-rework-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PENDING-ESCALATION-NOTIFICATION-FROZEN-REWORK-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-REUSE-POST-WAIVER-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-post-waiver-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-ESCALATION-NOTIFICATION-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one bounded frozen rework for the next live handover seam after Block X. This block must delete or reduce the repeated `escalate_to_pending(...) -> send_telegram_notification(...)` cluster in frozen `decision.py` to a bounded owner-surface invocation, without claiming closure of the broader handover lifecycle.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-handover-reuse-post-waiver-audit-a922.md`
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
  - `rg -n 'result = escalate_to_pending\(|send_telegram_notification\(' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8578,8618p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '8758,8794p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '11239,11268p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1205,1370p' truffles-api/app/services/state_service.py`
- `FACT findings`:
  - frozen `decision.py` still repeats the same create-notify authority cluster after `escalate_to_pending(...)` across multiple branches.
  - the repeated cluster owns handover creation success handling, `handover_reopened` derivation, and Telegram notification dispatch inline in the frozen file.
  - `state_service.py` already owns `escalate_to_pending(...)`, so the closest reuse-first owner surface is non-frozen and adjacent to the seam.

## One web search (mandatory before implementation)
- **Query (exact):** `Extract Function site:refactoring.com/catalog`
- **Date/time (local):** `2026-03-17 23:11 +0500`
- **Sources opened (from this query):**
  - `Extract Function` — `https://refactoring.com/catalog/extractFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** extract the repeated behavior into one function at the module that already owns the closest collaborators so old callsites shrink to one invocation.
- **Decision:** `reuse/integrate` — add one non-frozen owner surface next to `escalate_to_pending(...)` in `state_service.py` and reduce all frozen create-notify callsites to that owner-surface invocation.
- **Rejected options:**
  - another repeated inline create-notify rewrite in `decision.py`
  - helper-only cleanup without deleting the repeated frozen cluster
  - broad handover lifecycle rewrite across frozen and non-frozen runtime

## Root cause (mandatory)
- **Symptom:** after Block X, frozen `decision.py` still owns repeated pending-escalation create-notify authority.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/routers/webhook/decision.py:8590-8618`.
  2. inspect `truffles-api/app/routers/webhook/decision.py:8766-8794`.
  3. inspect `truffles-api/app/routers/webhook/decision.py:11239-11268`.
- **Evidence:** the repeated frozen cluster still calls `escalate_to_pending(...)`, derives `handover_reopened`, and calls `send_telegram_notification(...)` inline for the same pending-escalation pattern.
- **Five Whys:**
  1. the create-notify authority remained after Block X because Block X only removed active-handover reuse inline behavior.
  2. the cluster stayed inline because it was duplicated across many branches instead of one helper.
  3. each duplicated branch still needed the same create/reopen outcome and notification outcome.
  4. no shared non-frozen owner surface yet combined those repeated steps.
  5. until that shared owner surface exists and all frozen callsites use it, the old repeated authority remains live.
- **Root cause statement:** the surviving live frozen seam is the repeated pending-escalation create-notify cluster, which keeps handover success handling and notification dispatch authority inside `decision.py`.
- **Fix mechanism:** move the repeated cluster into one non-frozen owner surface with runtime hooks, then reduce every frozen callsite to bounded invocation only.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `escalate_to_pending(...)` in `truffles-api/app/services/state_service.py`, existing `send_telegram_notification(...)` in `truffles-api/app/services/escalation_service.py`, and existing endpoint tests that patch `decision.escalate_to_pending` / `decision.send_telegram_notification`.
- **External reuse:** Martin Fowler `Extract Function` guidance from `https://refactoring.com/catalog/extractFunction.html` to collapse the repeated frozen cluster into one shared owner surface.

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded frozen rework with helper extraction only for the repeated create-notify cluster.
- **Go/no-go signals:** frozen `decision.py` no longer contains inline `escalate_to_pending(...) -> send_telegram_notification(...)` clusters for this seam; targeted handover-create tests and governance checks stay green.
- **Rollback:** revert `state_service.py`, `decision.py`, matching tests, and waiver lines.
- **Post-release monitoring window:** local-only validation for this block; no staged rollout beyond targeted tests and governance checks.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted create/reuse handover tests plus governance checks only.
- **Stop condition:** if removing the repeated cluster requires broader handover lifecycle ownership changes, stop with `GAP`.
- **Escalation path:** `Top Architect`

## Invariant
- no edits to `truffles-api/app/routers/webhook/booking.py`
- no claim of full handover lifecycle closure
- no helper-only progress claim without deleting the repeated frozen create-notify cluster

## Scope
- add one non-frozen owner surface for pending-escalation create-notify handling
- reduce all matching frozen create-notify callsites in `decision.py` to bounded owner-surface invocation
- add targeted owner-surface tests if needed
- sync canon/evidence after implementation

## Out of scope
- broader handover lifecycle rewrite
- rejection/resolve paths outside this repeated create-notify seam
- thin helper cleanup as standalone progress

## Touch-list
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-escalation-notification-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one owner-surface runtime contract in `state_service.py` for pending-escalation create-notify handling.
2. Reduce all matching frozen `decision.py` create-notify callsites to bounded invocation.
3. Update the scoped waiver in `docs/LEGACY_SUNSET.yaml`.
4. Prove the seam with targeted tests and governance checks.
5. Sync canon/session/state with FACT-only evidence.

## DoD
- frozen `decision.py` no longer owns inline pending-escalation create-notify authority for this seam
- owner-surface runtime logic lives outside the frozen file
- targeted handover-create tests stay green
- governance checks stay green

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'human_request_bypasses_active_booking_flow_and_escalates or llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff or booking_verification_creates_handover_when_none_active or style_reference_photo_escalates_during_booking_flow'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_escalation_notification or handover_reuse'`

## Evidence
- reduced frozen create-notify callsites in `decision.py`
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
- many endpoint tests patch `decision.escalate_to_pending` and `decision.send_telegram_notification`, so the owner surface must preserve patch compatibility or tests need bounded updates
- the repeated cluster appears across many frozen callsites, so partial migration does not count as progress

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen `get_active_handover(...)`; thin pending-resume wrappers; broader handover lifecycle callsites outside the repeated create-notify cluster.
- **Why not in this block:** this block is limited to the repeated pending-escalation create-notify seam only.
- **Risk if deferred:** frozen `decision.py` keeps repeated handover creation success handling and Telegram notification dispatch authority inline even after Block X.
- **Linked follow-up Task Package(s):** `TP-2026-03-17-consultant-core-pending-escalation-notification-post-waiver-audit-a922` (to be authored after runtime evidence)
- **Expiry/trigger to stop deferral:** immediately after this bounded create-notify cut lands.

## Next-block contract (mandatory)
- **Next block objective:** run one post-waiver audit over the remaining handover residual symbols after the repeated create-notify cluster loses authority.
- **First deterministic check command:** `rg -n 'result = escalate_to_pending\(|send_telegram_notification\(|get_active_handover\(' truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if the repeated create-notify cluster still owns the live body in frozen `decision.py`, stop with `GAP`.
- **Owner role for closure:** `Top Architect`
