# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R45 Timeout Initial Booking Degraded Fallback Runtime Decision A922

## Truthful input artifacts
- `/tmp/booking_quality/a922-go2f-seed19-r45/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r45/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/run_manifest.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`

## Completion classification
- `r45` is the first truthful completion replay after the repaired `r44` proof family: `infra_valid=true`, `run_integrity_valid=true`, `manual_audit_status='done'`, `turns_strict_failed=0`, `blocking_reasons.count=0`, and `failure_families.json` is empty.
- The old `r44` false `handoff_miss` blocker is closed on the live replay surface.
- The old weekend-pricing runtime blocker remains closed on the same replay surface.
- `r45` remains semantically invalid, but not because of a surviving strict runtime family or proof blocker.

## Remaining semantic-invalid surface
- `summary.json` records `semantic_acceptance.reasons=['threshold_breach']`, `policy_core_turns=3`, `policy_core_degraded_turns=3`, and `degraded_fallback_rate=1.0`.
- The surviving rows are exactly:
  - `LLM-QUAL-a922-go2f-seed19-r45-001-01-3996bc`
  - `LLM-QUAL-a922-go2f-seed19-r45-002-01-a5a212`
  - `LLM-QUAL-a922-go2f-seed19-r45-006-01-83a5c9`
- All three rows are strict-green `booking_prompt` / `collect` turns, but each records `decision_meta.policy_core_mode='degraded_fallback'`, `decision_meta.policy_core_degrade_reason='policy_error:timeout'`, and `decision_meta.policy_core_guard_recovery='initial_booking_parser'`.

## Runtime ownership of the residual family
- The active owner path is `_try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py:11831`.
- That owner calls `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)`, which falls through timeout recovery at `truffles-api/app/services/reasoning_core.py:7225-7241`.
- Timeout recovery itself is `_resolve_turn_planner_safe_initial_booking_timeout_collect_candidate(...)` at `truffles-api/app/services/reasoning_core.py:7507-7564`.
- When timeout recovery is used, the live reply path appends `policy_core_guard` trace evidence at `truffles-api/app/services/reasoning_core.py:11980-12000`.
- This means the surviving blocker is runtime-owned: the oracle is only reading the degrade evidence the runtime already emitted.

## Verdict
- The repaired `r44` proof family is closed.
- The next admissible block is runtime, not proof.
- The surviving family is not “bad text”; it is timeout-driven degraded execution on fresh initial booking entry.
- The next block must reduce timeout-driven degraded fallback on this owner path while keeping semantic ownership in policy core and keeping true degrade paths observable.

## Next admissible move
- `implement_consultant_core_demo_salon_seed19_r45_timeout_initial_booking_degraded_fallback_runtime_family`
