# TP-2026-03-28-consultant-core-workstream5-booking-direct-owner-cluster-cut-a922

## Title / Goal
Remove the remaining live `booking.py -> decision.py` dependency by switching booking flow helpers to their direct owners and extracting the remaining booking-only constant/helper residue into a narrow `booking_runtime.py` owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-4 done`, Workstream 5 open)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 5 — Legacy Mesh Strangler`
- `docs/system_forensics/files/app_routers_webhook_booking.md`
- `docs/system_forensics/files/app_routers_webhook_decision.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `docs/system_forensics/files/app_routers_webhook_media.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com move constants and helper methods from large class to new class`
- Date/time: `2026-03-28T07:51:36+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/class-too-large.html`
- High-signal source quality:
  - Martin Fowler primary refactoring article on splitting one oversized owner by coherent helper groups, redirecting live callers first, and keeping compatibility aliases only during migration.
- Found reusable idea:
  - move one cohesive slice by redirecting live callers to direct owners, then leave the large file with aliases only for remaining callers.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already uses this exact strangler pattern for `runtime_primitives.py`, `booking_signal_runtime.py`, `knowledge_runtime.py`, `context_runtime.py`, `guard_runtime.py`, `pending_runtime.py`, and `info_followup_runtime.py`; booking should now follow the same direct-owner cut.
- Rejected options:
  - keep `booking.py` on `decision_router.*` until the end of Workstream 5: rejected because it preserves the largest remaining live consumer seam.
  - split this into tiny per-symbol edits: rejected because the seam is one cohesive booking-helper family and should be cut in one bounded block.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/booking.py` is still the largest live `decision.py` consumer. It reads expected-reply constants, booking prompts, time/name regex helpers, info-query helpers, guard helpers, style-reference detection, guest-policy detection, and booking cancel helpers through `decision_router.*`.

### Minimal Reproduction
1. Inspect direct reads in `truffles-api/app/routers/webhook/booking.py`.
2. Confirm many of those symbols already have better owners:
   - `runtime_primitives.py`
   - `booking_signal_runtime.py`
   - `info.py`
   - `media.py`
   - `guards.py`
   - `pack_runtime_service.py`
3. Confirm the remaining booking-only residue still lives in `decision.py`:
   - `MSG_BOOKING_ASK_ALL`
   - `MSG_BOOKING_CANCELLED`
   - `MSG_BOOKING_REENGAGE`
   - `MSG_BOOKING_SLOT_LOCK_STUB`
   - `NAME_PATTERN`
   - `NAME_NOISE_TOKENS`
   - `_matches_guest_policy_lexicon(...)`
   - `_is_booking_cancel(...)`

### Evidence
- `rg -n "decision_router\." truffles-api/app/routers/webhook/booking.py`
- `rg -n "MSG_BOOKING_ASK_ALL|MSG_BOOKING_CANCELLED|MSG_BOOKING_REENGAGE|MSG_BOOKING_SLOT_LOCK_STUB|NAME_PATTERN|NAME_NOISE_TOKENS|_matches_guest_policy_lexicon|_is_booking_cancel" truffles-api/app/routers/webhook/decision.py`
- `rg -n "TIME_PATTERN|TIME_HOUR_PATTERN|BOOKING_TIME_SERVICE_INTENTS|MSG_AI_ERROR|MSG_EXPECTED_SERVICE_OFF_TOPIC|def _looks_like_info_query|def _detect_info_class_intents|def _is_style_reference_request|def _booking_clarify_guard_reason|def _format_service_not_found_reply" truffles-api/app/routers/webhook/booking_signal_runtime.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/media.py truffles-api/app/routers/webhook/guards.py truffles-api/app/services/pack_runtime_service.py`

### Five Whys
1. Why does `booking.py` still import `decision.py`?
   - Because its helper family was never redirected to direct owners after the earlier helper extractions.
2. Why is that wrong now?
   - Because `decision.py` remains the live supplier of booking flow prompts, regexes, and decision helpers on the active path.
3. Why does that matter?
   - Because this is the largest remaining live legacy seam and keeps booking behavior coupled to the god-file.
4. Why does this still block Workstream 5?
   - Because Workstream 5 requires surviving legacy surfaces to become adapter-only / alias-only, not live helper owners.
5. Why cut it as one family?
   - Because these reads form one coherent booking-helper slice and the user-visible risk can be covered with focused deterministic booking tests.

### Root Cause Statement
The booking helper slice was left half-migrated: many symbols already had better owners, but `booking.py` kept reading them through `decision.py`, and the remaining booking-only prompt/regex/policy residue was never extracted into its own narrow owner.

### Fix Mechanism
Switch `booking.py` to direct owners for already-extracted helpers, create `booking_runtime.py` for the remaining booking-only residue, keep compatibility aliases in `decision.py`, and add deterministic guards so `booking.py` cannot drift back to `decision_router.*` for that cluster.

## Invariant
- Booking prompts, expected-reply handling, cancel detection, info-interrupt behavior, and style-reference behavior stay unchanged.
- No new semantic routing is introduced.
- `decision.py` loses live booking-helper ownership.

## Scope
- Switch `booking.py` to direct imports from existing narrow owners.
- Extract remaining booking-only residue into `booking_runtime.py`.
- Leave compatibility aliases in `decision.py` only.
- Add focused deterministic coverage and architecture guard updates.

## Out of Scope
- Deleting `decision.py`.
- Reworking media helper ownership.
- Reworking outbox/dedup/shield helper ownership.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/routers/webhook/booking_runtime.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_booking_prompt_leak_guard.py`
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Create `booking_runtime.py` for the booking-only residue.
2. Redirect `booking.py` to direct owners for all moved helper groups.
3. Leave compatibility aliases in `decision.py` only.
4. Add focused deterministic coverage and architecture guard updates.
5. Update repo truth.

## DoD
- `booking.py` no longer reads the moved booking helper cluster through `decision_router.*`.
- `booking.py` no longer needs `_decision_runtime()`.
- Targeted deterministic checks pass.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/booking_runtime.py truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py truffles-api/tests/test_booking_appointments.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_prompt_leak_guard.py truffles-api/tests/test_booking_info_interrupt_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_appointments.py -k "resolve_booking_info_intents or next_booking_prompt or select_booking_interrupt_text"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_prompt or booking_interrupt or booking_cancel or booking_reengage or booking_info or style_reference"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "booking_runtime_cluster_uses_narrow_owners or info_followup_runtime_cluster_uses_narrow_owner or pending_runtime_cluster_uses_narrow_owner"`
- `git diff --check`

## Evidence
- Updated TP
- Focused booking pytest output
- Focused architecture guard output
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new compatibility facade in front of `decision.py`.
- No semantic regex/phrase growth in governed core.
- No doc-only closure without authority reduction.

## Risks / Blockers
- The broader architecture guard still has the unrelated pre-existing residual `truffles-api/app/core/dialog_state_service.py:3202` (`PolicyDecision(...)` outside governed boundary).
- `Canon Sync Gate` remains red because worktree `AGENTS.md` diverges from `/home/zhan/AGENTS.md`; this block cannot claim session gate closure.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `media.py`, `dedup.py`, `outbox.py`, and `shield.py` will still depend on `decision.py` for unrelated helper clusters after this cut.

### Why not in this block
- This family is bounded to the largest remaining live `booking.py -> decision.py` helper seam.

### Risk if deferred
- `decision.py` remains coupled to the booking flow as the biggest live helper supplier.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream5-operational-helper-runtime-cluster-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if this block lands and `booking.py` still has direct `decision_router.*` reads for the moved booking-helper cluster.

## Next-block Contract (mandatory)
### Next block objective
After this cut, reduce the remaining operational helper seams in `media.py`, `dedup.py`, `outbox.py`, and `shield.py`.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "booking_runtime_cluster_uses_narrow_owners or info_followup_runtime_cluster_uses_narrow_owner"`

### Blocked-by conditions
- This block must first prove that `booking.py` no longer reads the moved helper cluster from `decision.py` and that focused booking tests stay green.

### Owner role for closure
- Brain / Top Architect
