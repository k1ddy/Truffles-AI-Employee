# TP-2026-03-18-consultant-core-policy-core-guard-orchestration-package-a922

## Goal
Delete the remaining frozen degraded guard orchestration family from `truffles-api/app/routers/webhook/decision.py` by converging the live guard-safe reply / handoff / hold / completed-booking / degraded-collect orchestration into one narrow non-frozen `truffles-api/app/services/policy_core_guard_orchestration_service.py` owner surface.

## Canon refs
- `STATE.md` NOW: consultant core master residual ledger stop-line audit
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted degraded-guard runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Move Function" "Extract Class"`
- **Date/time (local):** `2026-03-18 12:29:01 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/extractClass.html`
- **Source quality:**
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- **Found ready-made solutions:**
  - `Move Function`: move behavior to the module that owns the invariant and the dominant coordination data
  - `Extract Class`: carve one coherent responsibility out of the mixed host instead of extending the hotspot further
- **Decision:** `reuse + build`
  - reuse existing downstream owner surfaces and hook patterns from `timeout_owner_boundary_service.py`, `policy_timeout_degrade_boundary_service.py`, `policy_validation_boundary_service.py`, `_handle_booking_flow(...)`, `_reuse_active_handover(...)`, and `_create_pending_escalation_with_notification(...)`
  - build exactly one dedicated `truffles-api/app/services/policy_core_guard_orchestration_service.py` owner surface because no existing non-frozen service truthfully owns the full residual family without becoming a new mixed hotspot
  - keep frozen `decision.py` as a bounded caller that prepares runtime inputs and invokes the single owner surface
- **Rejected options:**
  - extend `truffles-api/app/services/state_service.py`: rejected because it is already the continuity owner and would become a mixed state + boundary + handoff host
  - extend `truffles-api/app/services/timeout_owner_boundary_service.py` or `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`: rejected because the residual family is broader than timeout-only ownership and would collapse unrelated boundary families into one hotspot
  - fold the family directly into `truffles-api/app/core/boundary_validator.py` or `truffles-api/app/core/turn_executor.py`: rejected because this package still lives on the legacy `WebhookResponse` materialization path and the public-entrypoint materialization contract is not closed yet
  - add local helper wrappers in frozen `decision.py`: rejected because that would rename the seam without deleting the old authority

## Root cause (mandatory)
- **Symptom:**
  - frozen `decision.py` still owns the last package-sized degraded guard orchestration cluster after the timeout / validation / specialist micro-family deletions
  - the same file still decides guard-safe reply vs handoff vs pending hold vs completed-booking handoff vs degraded collect, and then applies guard override, trace/meta writes, send, commit, and `WebhookResponse` authoring inline
- **Minimal reproduction:**
  - `rg -n "policy_handoff_policy_blocked|policy_core_guard_handoff_safe|policy_core_guard_pending_hold|policy_core_timeout_booking_completion|policy_core_degraded_reschedule_handoff|policy_core_degraded_collect_guard|_apply_policy_guard_override\(|_record_decision_trace\(|_record_message_decision_meta\(|_send_and_save\(|db.commit\(" truffles-api/app/routers/webhook/decision.py`
- **Evidence:**
  - `truffles-api/app/routers/webhook/decision.py:13981-14015` still owns the explicit-manager safe reply when handoff capability policy blocks escalation
  - `truffles-api/app/routers/webhook/decision.py:14413-14484` still owns degraded handoff-safe orchestration (`policy_core_guard_handoff_safe`)
  - `truffles-api/app/routers/webhook/decision.py:14565-14606` still owns pending / manager-active hold orchestration (`policy_core_guard_pending_hold`)
  - `truffles-api/app/routers/webhook/decision.py:14943-14977` still owns timeout completed-booking continuity override finalization (`policy_core_timeout_booking_completion`)
  - `truffles-api/app/routers/webhook/decision.py:15795-15880` still owns degraded collect reschedule escalation orchestration (`policy_core_degraded_reschedule_handoff`)
  - `truffles-api/app/routers/webhook/decision.py:15888-15922` still owns the base degraded collect reply finalization (`policy_core_degraded_collect_guard`)
  - existing non-frozen services each own only one narrower family: timeout owner-boundary, timeout degrade, timeout recovery, specialist followup, time-followup, or validation; none is the truthful owner for the whole residual package
- **Five Whys:**
  1. Why is `decision.py` still a boundary hotspot? Because the surviving degraded guard family still materializes final runtime outcomes there.
  2. Why is that family larger than one more micro-slice? Because the remaining branches share the same ordered boundary workflow while spanning different downstream side effects.
  3. Why can the previous owner surfaces not absorb it cleanly? Because each existing service is scoped to a narrower timeout/validation/specialist family and extending any of them would create a new mixed hotspot.
  4. Why can `state_service.py` not be the destination? Because it is already the continuity owner and mixing guard-boundary orchestration into it would violate the continuity boundary and grow a second god-file.
  5. Why is a package-level owner surface required now? Because only one dedicated family owner can delete the old frozen orchestration seam without restarting seam farming.
- **Root cause statement:**
  - The residual `policy_core_guard` package is still split because the branch-specific owner deletions removed several leaf reply families, but the top-level degraded guard orchestration skeleton still lives inline in frozen `decision.py` and no existing non-frozen service truthfully owns the whole remaining family.
- **Fix mechanism:**
  - build one dedicated `policy_core_guard_orchestration_service.py` owner surface with typed runtime input / hooks for the six residual guard modes
  - reuse existing downstream services and handoff / booking helpers from that owner surface instead of cloning their logic
  - delete the frozen inline apply/trace/meta/send/commit/`WebhookResponse` bodies so the old authority seam becomes unreachable

## Invariant
- `decision.py` must lose live degraded-guard authority, not gain another wrapper forest.
- `state_service.py` must not grow.
- No semantic post-hoc rewrite may be introduced.
- Existing trace / meta / handoff / booking / pending-hold runtime behavior must remain unchanged for covered scenarios.
- If the chosen destination becomes a new mixed hotspot, stop and publish `GAP` instead of shipping a fake cutover.

## Scope
- Introduce one dedicated non-frozen owner surface for the residual `policy_core_guard_orchestration` family
- Delete the frozen inline orchestration bodies for safe reply / handoff / hold / completed-booking / degraded-collect finalization
- Reuse existing downstream owner surfaces only through the new dedicated owner service
- Update only directly impacted docs/tests/contracts for this family

## Out of scope
- `semantic_arbitration_residual`
- broader `continuity_broader_collapse`
- `public_entrypoint_materialization_contract`
- `debounce_buffer_owner_convergence`
- proof bundle / multi-pack correctness claims
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-policy-core-guard-orchestration-package-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_core_guard_orchestration_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- any directly impacted targeted tests/docs only if required

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `timeout_owner_boundary_service.py`
  - `policy_timeout_degrade_boundary_service.py`
  - `policy_validation_boundary_service.py`
  - `policy_timeout_recovery_boundary_service.py`
  - `policy_timeout_booking_specialist_boundary_service.py`
  - `policy_timeout_booking_time_followup_boundary_service.py`
  - `_handle_booking_flow(...)`
  - `_reuse_active_handover(...)`
  - `_create_pending_escalation_with_notification(...)`
- **External reuse:**
  - Martin Fowler refactoring guidance for `Move Function` and `Extract Class`, already captured above and limited to this single mandatory query
- **Why this reuse mix is truthful:**
  - reuse the already-correct downstream owners and hook conventions
  - build exactly one new family owner because no existing service truthfully owns the whole residual package
  - keep `decision.py` as a bounded caller only and verify with grep that the old reason / decision family is deleted, not rewrapped

## Plan
1. Publish and register this package-level implementation TP, then switch canon to it.
2. Implement `truffles-api/app/services/policy_core_guard_orchestration_service.py` with one entrypoint and bounded mode handling for `handoff_policy_blocked_safe_reply`, `guard_handoff_safe`, `pending_hold`, `timeout_booking_completion`, `degraded_collect_reschedule_handoff`, and `degraded_collect`.
3. Reduce the frozen hotspots in `decision.py` to owner-surface invocation plus precomputed runtime inputs only.
4. Add or tighten targeted message-endpoint coverage, including one pending-hold regression if it does not already exist.
5. Run the targeted degraded-guard runtime checks, runtime-contract checks, and required architecture/session guards.
6. Record evidence in `STATE.md` only if the old live guard orchestration seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer contains the residual degraded-guard reason strings `policy_core_guard_handoff_safe`, `policy_core_guard_pending_hold`, `policy_core_timeout_booking_completion`, `policy_core_degraded_reschedule_handoff`, or `policy_core_degraded_collect_guard`
- the handoff-policy-blocked safe-reply orchestration at `decision.py:13981-14015` is also moved out of frozen inline finalization
- `truffles-api/app/services/policy_core_guard_orchestration_service.py` becomes the only non-frozen owner surface for this residual package
- targeted degraded-guard runtime tests and `test_consultant_core_runtime_contracts.py` pass
- required guard scripts and `SESSION_AGENT=a922 scripts/session_check.sh` pass
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `rg -n "policy_core_guard_handoff_safe|policy_core_guard_pending_hold|policy_core_timeout_booking_completion|policy_core_degraded_reschedule_handoff|policy_core_degraded_collect_guard" truffles-api/app/routers/webhook/decision.py`
- `python3 -m py_compile truffles-api/app/services/policy_core_guard_orchestration_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'handoff_policy_blocked_uses_safe_reply or reschedule_missing_reference_escalates_to_handoff or reschedule_missing_reference_availability_phrase_escalates_to_handoff or degraded_timeout_reschedule_without_reference_escalates or degraded_timeout_completed_booking_name_routes_into_booking_flow or referent_followup_degraded_collect_emits_referent_evidence or semantic_temporal_scope_missing_uses_degraded_collect_reason or service_info_interrupt_under_degraded_collect_sets_explicit_booking_progress_contract or pending_hold_routes_through_guard_owner_surface'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP + `STRUCTURE.md`
- canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- diff showing the deleted frozen guard orchestration seam and the new owner-surface entrypoint
- green targeted degraded-guard runtime tests + runtime-contract checks + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Cheap deterministic gates first:** the residual-family grep and `python3 -m py_compile`
- **Targeted lane next:** the degraded-guard `test_message_endpoint.py` selection
- **Contract lane after targeted pass:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- **Stop condition:** if two consecutive iterations fail without new structural evidence that the old seam shrank, stop and return to RCA instead of grinding runs
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime validation in this worktree before any merge; no prod rollout claim in this block
- **Go/no-go signals:**
  - the residual degraded-guard reason strings are gone from frozen `decision.py`
  - the targeted degraded-guard runtime selection passes
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` passes
  - required architecture/session guards pass
- **Rollback:**
  - revert this block's changes to `policy_core_guard_orchestration_service.py`, `decision.py`, affected tests, and synced docs
  - rerun the targeted degraded-guard runtime selection plus `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- **Rollback verification:**
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'handoff_policy_blocked_uses_safe_reply or reschedule_missing_reference_escalates_to_handoff or degraded_timeout_reschedule_without_reference_escalates or degraded_timeout_completed_booking_name_routes_into_booking_flow or pending_hold_routes_through_guard_owner_surface'`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- **Post-release monitoring window:** first post-merge consultant-core block only; do not advance to the next package if this family reappears in frozen `decision.py`

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted degraded-guard/runtime checks.

## No-go
- Do not grow `state_service.py`.
- Do not extend another family-specific boundary service into a new mixed host for this package.
- Do not leave local helper wrappers in frozen `decision.py` and count that as progress.
- Do not claim consultant correctness, full boundary closure, or multi-pack acceptance from this block.
- Do not materialize a second owner surface for the same residual package.

## Risks / blockers
- The new service will need many runtime hooks; if it becomes a generic boundary god-file instead of one bounded family owner, stop with `GAP`.
- Pending / manager-active hold behavior currently lacks an obvious dedicated regression name in `test_message_endpoint.py`; the runtime block must add one if coverage is missing.
- Booking-completion continuity must preserve the current `booking_slot_fill_applied`, `policy_core_guard_recovery`, and override-action evidence exactly.
- If the implementation leaves any of the frozen inline finalization bodies live, the block does not count as progress.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `semantic_arbitration_residual` still remains after this package
- broader `continuity_broader_collapse` still remains after this package
- `public_entrypoint_materialization_contract`, `debounce_buffer_owner_convergence`, `proof_black_box_completion`, and `multi_pack_acceptance` remain open even if this package lands
- the typed `boundary_validator.py` / `turn_executor.py` target remains the long-range boundary contract owner, but this package still needs a legacy-runtime owner adapter because public entrypoint materialization is not closed yet

### Why not in this block
- this package deletes one exact residual frozen family and nothing else
- folding semantic arbitration or entrypoint materialization into the same block would blur owner boundaries again

### Risk if deferred
- new degraded-guard behavior can still accrete in frozen `decision.py`
- the surviving family can keep masking itself as five small branches even though it is one package-level authority seam

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-semantic-arbitration-residual-package-a922` (to be authored only after this package either lands or truthfully blocks)
- `TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922` (only after the ordered backlog reaches it)

### Expiry/trigger to stop deferral
- stop deferral if any new degraded-guard branch lands in frozen `decision.py` or if the new owner surface starts absorbing unrelated timeout/validation families

## Next-block contract (mandatory)
### Next block objective
- implement the `policy_core_guard_orchestration` runtime family convergence defined by this TP and delete the frozen degraded-guard orchestration seam from `decision.py`

### First deterministic check command
- `rg -n "policy_core_guard_handoff_safe|policy_core_guard_pending_hold|policy_core_timeout_booking_completion|policy_core_degraded_reschedule_handoff|policy_core_degraded_collect_guard" truffles-api/app/routers/webhook/decision.py`

### Blocked-by conditions
- inability to keep the destination bounded to one dedicated owner surface
- any proposal that grows `state_service.py`
- any implementation that leaves the frozen inline finalization bodies live or moves them into another mixed hotspot

### Owner role for closure
- Brain / Top Architect
