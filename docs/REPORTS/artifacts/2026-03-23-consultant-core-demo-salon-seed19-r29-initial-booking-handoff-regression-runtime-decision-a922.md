# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R29 Initial Booking Handoff Regression Runtime Decision A922

## Truthful input artifacts
- `/tmp/booking_quality/a922-go2f-seed19-r26/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r27/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r28/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r29/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`

## Classification
- `r26`, `r27`, and `r28` are non-canonical replay attempts and cannot be used for blocker classification.
- `r29` is the first truthful fresh replay after those audits.
- The first surviving blocker on `r29` is a `runtime contract bug`, not proof drift.

## Why it is runtime
- Locked baseline `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl` is strict-green on dialog `1`, turn `1` with `booking_prompt` / `collect`.
- Fresh replay `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl` now routes the same turn through `turn_planner_safe_explicit_handoff_owner`.
- `r29` is `infra_valid=true` and strict artifacts are complete, so the mismatch is admissible.

## Fresh failing row
- Row: `LLM-QUAL-a922-go2f-seed19-r29-001-01-5279e4`
- User: `Я хочу записаться на маникюр на завтра.`
- Expected: `booking_prompt`, `tool_action=collect`, `source=llm_policy_core`, trace includes `question_contract`.
- Actual: `action=escalate`, `tool_action=handoff`, `reason_code=terminal_owner_unresolved`, trace stage `turn_planner_safe_explicit_handoff_owner`.
- Strict reasons: `expected_meta_mismatch`, `expected_trace_miss`.

## Shadow risk
- `booking_prompt` owner names are duplicated at `truffles-api/app/services/reasoning_core.py:5005` and `truffles-api/app/services/reasoning_core.py:10136`.
- `explicit_handoff` owner names are duplicated at `truffles-api/app/services/reasoning_core.py:3321` and `truffles-api/app/services/reasoning_core.py:8481`.
- Any implementation block must stay on the executable later owner path or open duplicate cleanup first.

## Next admissible move
- `implement_consultant_core_demo_salon_seed19_r29_initial_booking_handoff_regression_runtime_family`
