# TP-2026-03-24 Consultant Core Demo Salon Seed19 R46 Initial Booking Owner Reset Runtime Implementation A922

## Title/goal
Reduce old/new authority overlap on the surviving `r46` service-only initial-booking family by deleting the dead shadowed owner defs for this family, moving the booking-prompt candidate authority into one non-frozen owner module, and tightening the fresh-entry owner envelope so the runtime no longer depends on the duplicated `reasoning_core.py` seam.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-demo-salon-seed19-r46-service-only-initial-booking-degraded-fallback-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-demo-salon-seed19-r46-service-only-initial-booking-degraded-fallback-runtime-decision-a922.md`
- CA_ID `a922-go2f-seed19-r46-initial-booking-owner-reset-runtime-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python function definition rebinding name execution model`
- **Date/time (local):** `2026-03-24 07:25 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3.11/reference/executionmodel.html`
- **Found ready-made solutions:** the official Python execution model documents that name-binding operations are executable statements. For duplicate top-level `def`, the later binding becomes the live global name, so earlier duplicate bodies are dead code and should be removed instead of maintained in parallel.
- **Decision:** `reuse` Python’s binding truth as the justification for deleting the dead duplicate initial-booking owner defs and consolidating live authority into one canonical non-frozen module.
- **Why:** the surviving `r46` row still lives on a shadowed booking-prompt candidate seam; keeping twin bodies would preserve dead authority and continue the overlap the program is trying to remove.
- **Rejected options:** keep both duplicate defs and add another local tweak; move work into frozen routers; weaken `degraded_fallback_rate`; hide degrade metadata.

## Root cause (mandatory)
- **Symptom:** truthful completion replay `r46` keeps only one surviving semantic blocker: `LLM-QUAL-a922-go2f-seed19-r46-005-01-df3da9`, a strict-green service-only initial booking collect turn that still records `policy_core_mode='degraded_fallback'`.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r46-005-01-df3da9` in `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl` and `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`, then trace the call chain through `truffles-api/app/services/reasoning_core.py`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r46/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`
  - `truffles-api/app/services/reasoning_core.py:2190`
  - `truffles-api/app/services/reasoning_core.py:5048`
  - `truffles-api/app/services/reasoning_core.py:6583`
  - `truffles-api/app/services/reasoning_core.py:7156`
  - `truffles-api/app/services/reasoning_core.py:10281`
  - `truffles-api/app/services/reasoning_core.py:11874`
  - `truffles-api/app/services/reasoning_core.py:16017`
  - `truffles-api/app/services/reasoning_core.py:16030`
  - `truffles-api/app/core/turn_planner.py:78`
  - `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- **Five Whys:**
  1. Why is `r46` still semantically red if strict rows are green? Because one surviving initial booking row still emits `policy_core_mode='degraded_fallback'`, so `degraded_fallback_rate` breaches the threshold.
  2. Why is that row still on the same family? The trace still exits through `turn_planner.safe_booking_prompt_owner.v1` and the duplicated `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` seam.
  3. Why is that seam still risky after the `r45` repair? The runtime logic is still owned inside shadowed `reasoning_core.py` defs, so fresh initial booking entry keeps depending on dead/live duplicate bodies rather than one canonical owner.
  4. Why is continuing the same inline tuning wrong? Another local tweak would keep authority in the same duplicated seam and would not reduce the structural debt that keeps re-surfacing.
  5. Why is owner reset the correct bounded move? The current surviving family is already narrowed to initial booking entry, the dead duplicate defs are provably removable, and the typed target seam already exists under `truffles-api/app/core/`.
- **Root cause statement:** the surviving `r46` blocker is not just “one more timeout”; it persists because fresh initial booking prompt resolution still lives in duplicated `reasoning_core.py` owner defs, so the live path depends on dead-shadowed authority plus a broad prompt envelope instead of one canonical non-frozen owner.
- **Fix mechanism:** create one canonical non-frozen booking-prompt owner module, route the live initial-booking candidate resolution through it, delete the dead duplicate initial-booking family defs from `reasoning_core.py`, and keep the fresh-entry owner envelope booking-only instead of exposing broader consult authority on this path.

## Reuse-first plan (mandatory)
- Internal reuse: keep `route_llm_policy_core(...)`, `_build_turn_planner_safe_booking_prompt_decision(...)`, `_finalize_turn_planner_owner_cutover(...)`, and the existing timeout-recovery candidate contract.
- External reuse: `https://docs.python.org/3.11/reference/executionmodel.html`
- Why not reinvent the wheel: the implementation should relocate existing authority, not invent a second booking runtime.

## Invariant
Do not touch frozen routers. Do not weaken thresholds or hide degrade flags. Do not reopen the repaired `r42` or `r44` families. Keep timeout recovery observable when it really happens.

## Scope
- Non-frozen initial-booking owner reset for the surviving `r46` family
- Removal of dead duplicate defs for the booking-prompt candidate / owner surfaces touched by this family
- Focused deterministic tests and local proof for the new owner

## Out of scope
- proof/control-plane `manual_audit.json` inference repair
- prod floor repair
- acceptance `lock/full`
- unrelated duplicate-def families elsewhere in `reasoning_core.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-demo-salon-seed19-r46-initial-booking-owner-reset-runtime-implementation-a922.md`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `STRUCTURE.md`

## Plan (1..N)
1. Create one canonical non-frozen booking-prompt owner module for initial booking candidate resolution and timeout-recovery candidate shaping.
2. Delete the dead shadowed `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` duplicate and move the live callsites onto the canonical owner.
3. Delete the dead shadowed initial-booking-family owner defs that are no longer the authoritative path for this family.
4. Tighten the fresh initial booking owner envelope to booking-only refs on the canonical owner path.
5. Add focused deterministic coverage for the canonical owner and for the reduced duplicate-def ledger.
6. Run focused checks and decide whether the implementation is strong enough to justify the next fresh completion replay.

## DoD
- initial booking prompt candidate resolution lives in one canonical non-frozen module
- the dead duplicate defs for the touched initial-booking family are removed from `reasoning_core.py`
- the duplicate-def architecture guard ledger is updated to reflect the deleted family debt
- focused deterministic tests prove the canonical owner path and its fresh-entry envelope
- no frozen files are modified

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` before deterministic closure.
- **Max replay runs:** `1` fresh completion replay only if focused deterministic checks and local probe evidence justify it.
- **Stop condition:** if the implementation requires a threshold waiver, frozen edit, or another same-shape inline envelope tweak with no authority reduction, stop and reopen the family scope.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or initial_booking_owner_recovers_timeout_before_terminal_handoff or policy_core_tokens or service_only_initial_booking"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `git diff --check`

## Evidence
- focused pytest output
- `python3 -m py_compile` output
- `git diff --check` output
- if replay is launched: `/tmp/booking_quality/a922-go2f-seed19-r47/*`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime implementation; no prod rollout in this block.
- **Go/no-go signals:** duplicate-def reduction is real, focused deterministic checks are green, and no frozen file or threshold waiver is required.
- **Rollback:** revert the touched non-frozen files in this worktree if focused checks fail.
- **Post-release monitoring window:** not applicable; local-only until replay closure.

## Rollback
Revert the touched non-frozen files in this worktree and restore the previous duplicate-def allowance if the canonical owner breaks the bounded family tests.

## No-go
- no frozen-router edits
- no threshold weakening
- no hidden degrade metadata
- no second same-shape envelope tweak without deleting dead authority

## Risks/blockers
- the `manual_audit.json` root-cause drift remains unresolved in this block and can still confuse narrative summaries
- the surviving live row may still require one fresh replay after deterministic proof because the previous blocker was live-runtime evidence, not only unit behavior

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate initial-booking owner logic outside the touched family may still exist; proof/control-plane root-cause inference drift remains; prod floor remains degraded.
- **Why not in this block:** this block is bounded to the surviving `r46` initial-booking owner family only.
- **Risk if deferred:** without this owner reset, the team would keep tuning the same live seam or misread the residual blocker as “just one more timeout.”
- **Linked follow-up Task Package(s):** fresh completion replay for the repaired `r46` family; then proof/control-plane inference repair if runtime closure holds.
- **Expiry/trigger to stop deferral:** immediate after this block; if the family still survives on replay, the next block must be based on the new canonical owner rather than reviving dead duplicate seams.

## Next-block contract (mandatory)
- **Next block objective:** rerun one fresh completion replay on runtime parity to prove whether the initial-booking owner reset closes `LLM-QUAL-a922-go2f-seed19-r46-005-01-df3da9` or truthfully surfaces the next blocker.
- **First deterministic check command:** `curl -fsS http://127.0.0.1:18186/admin/health && test \"$(git rev-parse HEAD)\" = \"$(curl -fsS http://127.0.0.1:18186/admin/version | jq -r .git_commit)\"`
- **Blocked-by conditions:** if focused deterministic checks fail, if the duplicate-def reduction is not real, or if the runtime is not on fresh parity, do not launch replay.
- **Owner role for closure:** Brain / Top Architect
