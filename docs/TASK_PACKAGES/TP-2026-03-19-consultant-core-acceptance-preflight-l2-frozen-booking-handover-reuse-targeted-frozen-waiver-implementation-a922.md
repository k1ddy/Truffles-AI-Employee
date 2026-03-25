# TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute the exact targeted frozen-waiver runtime cut for the surviving acceptance-preflight `L2` booking handover-reuse family. Delete the old live caller drift in frozen `booking.py` by wiring the truthful `_reuse_active_handover(..., hooks=...)` contract into the five scoped callsites only, add bounded regressions, then run exactly one fresh non-acceptance `L2` rerun and strict audit.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-family-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/summary.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/brief.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/manual_audit.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/trace_bundle.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/summary.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/manual_audit.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/responses.jsonl`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_booking_chaos_dialogs.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
obj = rows['LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a']
print(obj['turn_text'])
print(obj['decision_meta']['error'])
PY`
  - `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/booking.py`
  - `python3 - <<'PY'
import json
from pathlib import Path
run_dir = Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r18')
summary = json.loads((run_dir/'summary.json').read_text())
print(summary['infra_valid'])
print(summary['semantic_valid'])
print(summary['stop_reason'])
PY`
- `FACT findings`:
  - `r17` proves the surviving live blocker is still the frozen booking handover-reuse caller family: `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a` fails with `_reuse_active_handover() missing 1 required keyword-only argument: 'hooks'`.
  - the truthful owner contract already exists at `truffles-api/app/services/handover_owner_service.py:1092`, and the only remaining stale callers are `truffles-api/app/routers/webhook/booking.py:1702`, `:2358`, `:2914`, `:3007`, and `:3741`.
  - the previous direct fix attempt showed likely technical feasibility but was invalid without waiver because `legacy_freeze_guard.py` fail-closed on executable additions in frozen `booking.py`.
  - `r18` remains non-canonical partial evidence only: `infra_valid=true`, `semantic_valid=false`, `stop_reason=signal_15`, `run_integrity_reasons=['run_completion_gap']`, `responses_rows=41`, `trace_rows=41`, `dialogs_seen=[1, 2, 3]`, `error_rows=0`.
  - the allowed future waiver scope is exact: the 5 `booking.py` callers plus bounded regressions in `truffles-api/tests/test_message_endpoint.py` and `truffles-api/tests/test_booking_chaos_dialogs.py`.
- `Detected drift (docs vs code)`:
  - the decision block correctly stopped unwaived runtime work; the next honest move is the scoped implementation itself, not another planning block and not a rerun-only loop.

## One web search (mandatory before implementation)
- **Query (exact):** `python keyword-only arguments official docs`
- **Date/time (local):** `2026-03-19T10:24:00+05:00`
- **Sources opened (from this query):**
  - `https://docs.python.org/3/reference/compound_stmts.html#function-definitions`
  - `https://docs.python.org/3/glossary.html#term-parameter`
- **Source quality:**
  - high-signal / primary source: official Python documentation
- **Reuse rule for this block:**
  - reused from the decision block and parent family package; no second query is allowed or needed
- **Existing solutions found:**
  - caller sites must pass required keyword-only parameters explicitly by keyword
  - adding a compatibility bridge or making `hooks` optional would preserve the seam instead of deleting it
- **Decision:** `integrate`
  - update the exact stale callers and keep the owner contract truthful
- **Rejected options:**
  - new wrapper/helper
  - making `hooks` optional
  - second web query

## Root cause (mandatory)
- **Symptom:** acceptance-preflight `L2` remains blocked because the frozen `booking.py` reuse contours still invoke `_reuse_active_handover(...)` as if `hooks` were not required.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/l2-acceptance-preflight-a922-r17/responses.jsonl` row `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a`.
  2. inspect `truffles-api/app/services/handover_owner_service.py:1092` and confirm `_reuse_active_handover(..., *, hooks: ActiveHandoverReuseRuntimeHooks)`.
  3. inspect the 5 frozen callers in `truffles-api/app/routers/webhook/booking.py` and confirm they do not pass `hooks=`.
  4. inspect `/tmp/booking_quality/l2-acceptance-preflight-a922-r18/manual_audit.md` and confirm the earlier probe is non-canonical and cannot substitute for a fresh rerun under waiver.
- **Evidence:**
  - exact `r17` failing row
  - exact owner signature
  - exact 5 frozen caller sites
  - exact `r18` partial-audit snapshot
- **Five Whys:**
  1. Why is `r17` still semantic-red? Because a frozen runtime exception still survives on a booking contour.
  2. Why does the exception survive? Because the frozen `booking.py` callsites still drift from the truthful owner contract.
  3. Why didn't the previous block remove it? Because the previous block stopped at the freeze boundary and truthfully published a waiver decision.
  4. Why is another rerun alone invalid? Because `r18` already proved executed-prefix relief cannot count as seam deletion without a canonical full rerun.
  5. Why is this implementation block admissible? Because the exact old live seam is now localized, the future waiver scope is machine-readable, and no new mixed hotspot is required.
- **Root cause statement:** the surviving blocker is a narrow frozen caller drift in `booking.py`, not a broader runtime family. The old live seam dies only if those 5 callers explicitly pass the truthful `hooks=` contract under the exact approved waiver scope.
- **Fix mechanism:**
  - add one exact scoped waiver entry in `docs/LEGACY_SUNSET.yaml` for the `booking.py` additions
  - update the 5 `booking.py` callers to pass `ActiveHandoverReuseRuntimeHooks(...)`
  - add bounded regressions for the affected booking contours
  - run one fresh non-acceptance `L2` rerun and strict audit

## Old authority seam to delete (mandatory)
- **FACT:** target seam is the stale frozen caller family in `truffles-api/app/routers/webhook/booking.py:1702`, `:2358`, `:2914`, `:3007`, and `:3741`.
- **FACT:** this block does **not** claim deletion of broader booking/router authority outside those callsites.
- **INFERENCE:** the block is admissible only if those old stale caller forms become unreachable without creating a new wrapper/helper seam.

## Invariant
- no new wrapper/helper
- no owner-signature widening
- no scope expansion beyond exact `booking.py` callsites plus bounded regressions
- no transport / observer / billing / non-frozen A/B/C reopening
- no second fresh `L2` rerun beyond the single allowed one

## Scope
- add exact waiver lines for frozen `booking.py`
- update the 5 frozen `booking.py` callers to pass `hooks=`
- add bounded regressions in `truffles-api/tests/test_message_endpoint.py` and `truffles-api/tests/test_booking_chaos_dialogs.py`
- run one fresh non-acceptance `L2` rerun and strict audit
- sync canon/session/state with the truthful result of this block

## Out of scope
- edits to `truffles-api/app/routers/webhook/decision.py`
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to `truffles-api/app/routers/webhook/info.py`
- edits to `truffles-api/app/routers/webhook/policy.py`
- edits to `truffles-api/app/routers/webhook/guards.py`
- edits to `truffles-api/app/routers/webhook/response.py`
- any new observer/oracle work
- acceptance closure claims without fresh green `L2`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/handover_owner_service.py` owner contract
  - already-aligned non-frozen callers in `info.py`, `policy.py`, `guards.py`, and `response.py`
  - previously drafted bounded regressions for the 4 booking interrupt/flow contours and the booking-commit chaos contour
  - existing `legacy_freeze_guard.py` scoped-waiver contract
- **External reuse:**
  - official Python docs for keyword-only parameters
- **Why not reinvent the wheel:**
  - the owner contract and exact hook shape already exist; only the stale frozen callers remain to be aligned

## Plan (1..N)
1. Add the exact scoped `booking.py` waiver lines to `docs/LEGACY_SUNSET.yaml`.
2. Import `ActiveHandoverReuseRuntimeHooks` in `truffles-api/app/routers/webhook/booking.py`.
3. Update the 5 stale `_reuse_active_handover(...)` callsites to pass `hooks=ActiveHandoverReuseRuntimeHooks(...)`.
4. Add bounded regressions for reschedule reuse, info-escalation reuse, same-day reuse, human-request reuse, and booking-commit reuse.
5. Run focused deterministic tests and required packet/guard/session checks.
6. Run exactly one fresh non-acceptance `L2` rerun and strict audit.
7. Publish either a truthful green `L2` summary or a truthful narrower `GAP`, then sync canon.

## DoD
- the old stale caller family is deleted/unreachable in the 5 frozen `booking.py` callsites
- no new wrapper/helper or signature widening exists
- the scoped waiver passes `legacy_freeze_guard.py`
- bounded regressions pass
- exactly one fresh non-acceptance `L2` rerun exists for this block and has a strict audit
- canon/session/state reflect the truthful result of the block

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_booking_chaos_dialogs.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'booking_interrupt_reschedule_passes_active_handover_hooks or booking_interrupt_info_escalation_passes_active_handover_hooks or booking_same_day_escalation_passes_active_handover_hooks or booking_human_request_escalation_passes_active_handover_hooks'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'booking_interrupt_reschedule_passes_active_handover_hooks or booking_interrupt_info_escalation_passes_active_handover_hooks or booking_same_day_escalation_passes_active_handover_hooks or booking_human_request_escalation_passes_active_handover_hooks or human_request_bypasses_active_booking_flow_and_escalates or llm_policy_core_reschedule_missing_reference_escalates_to_handoff or llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff or booking_reschedule_missing_slot_does_not_escalate_without_manager_request or llm_policy_core_reschedule_misrouted_info_without_reference_escalates or booking_reschedule_tool_missing_slot_escalates_to_handoff'`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- one fresh rerun command under the current local runtime, followed by `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r19 --status done --strict-artifacts`

## Evidence
- exact scoped waiver entry in `docs/LEGACY_SUNSET.yaml`
- diff showing the 5 stale booking callers now pass `hooks=`
- focused test output
- one fresh rerun directory and strict audit
- canon/session/state naming which old seam died or, if green failed, the narrower residual family

## Token / run budget (mandatory for expensive suites)
- **Max fresh non-acceptance `L2` runs:** `1`
- Max full runs: `0` new llm-quality/full acceptance runs; this block is bounded to one fresh non-acceptance rerun plus required deterministic guards.
- **Cheap deterministic gates first:** `py_compile` + focused pytest + freeze/arch/session guards
- **Stop condition:** if the fix requires any frozen file beyond `booking.py`, any new wrapper/helper, owner-signature widening, or a second fresh `L2`, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded local freeze-waived runtime change only; rerun one dev-lane `L2` after deterministic gates pass
- **Go/no-go signals:**
  - the 5 booking callers now use `hooks=`
  - `legacy_freeze_guard.py` passes with the exact scoped waiver
  - focused regressions pass
  - the one fresh rerun is strict-audited before any claim
- **Rollback:** revert the `booking.py`, test, and `docs/LEGACY_SUNSET.yaml` changes, then rerun the deterministic checks
- **Post-release monitoring window:** only through the single fresh rerun and strict audit for this block

## Rollback
1. Revert this block's `booking.py`, tests, and `docs/LEGACY_SUNSET.yaml` changes.
2. Re-run the deterministic checks.
3. Revert canon/session/state if the runtime result is rejected.

## No-go
- no helper wrapper counted as progress
- no widening of the frozen waiver beyond the 5 callsites
- no second fresh rerun
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block
- no claim of final acceptance closure without fresh green evidence

## Risks / blockers
- after the runtime exception dies, a different residual family may surface on the fresh rerun
- `docs/LEGACY_SUNSET.yaml` line scoping must match the actual additions exactly or the freeze gate will fail again
- if the local runtime is not refreshed to the current worktree, rerun evidence will be invalid

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial overall
  - final acceptance closure remains open
  - a new residual family may surface after this frozen caller seam dies
- **Why not in this block:**
  - this block is exact-scope frozen caller convergence only
- **Risk if deferred:**
  - the program remains stalled on a known stale caller seam and will continue rerun churn without admissible progress
- **Linked follow-up Task Package(s):**
  - post-waiver audit/summary block from the fresh rerun result
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - immediately after the one fresh rerun and strict audit for this block

## Next-block contract (mandatory)
- **Next block objective:** publish the truthful post-waiver audit result from the single fresh rerun, either as a green `L2` summary or as a narrower residual `GAP`
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r19 --status done --strict-artifacts`
- **Blocked-by conditions:** if the fresh rerun is absent, non-canonical, or a new family surfaces without the frozen seam dying first, stop and publish `GAP`
- **Owner role for closure:** `Top Architect`
