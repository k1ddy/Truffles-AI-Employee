# Report — 2026-03-24 Consultant Core Demo Salon Seed19 R46 Service-Only Initial Booking Degraded Fallback Runtime Decision A922

## Input truth
- `/tmp/booking_quality/a922-go2f-seed19-r46/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r46/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-implementation-a922.md`

## Truthful classification
- `r46` is a truthful fresh completion replay:
  - `metrics.counts.turns_strict_failed=0`
  - `blocking_reasons.count=0`
  - `failure_families.json` is empty
  - `run_integrity_valid=true`
  - all `10/10` dialogs are seen
- `r46` is still semantically invalid, but the surface narrowed materially:
  - `metrics.counts.policy_core_degraded_turns=1`
  - `thresholds.breaches=['degraded_fallback_rate']`
- The old `r45` runtime family narrowed from three degraded rows to one surviving row.

## Surviving row
- `LLM-QUAL-a922-go2f-seed19-r46-005-01-df3da9`
- dialog `5`, turn `1`
- user: `Я хочу записаться на маникюр.`
- outcome stays contract-green:
  - `action='booking_prompt'`
  - `tool_action='collect'`
  - `expected_reply_type='time'`
  - bot reply: `На какую дату и время вам удобно?`
- but runtime still degrades first:
  - `policy_core_mode='degraded_fallback'`
  - `policy_core_degrade_reason='policy_error:timeout'`
  - `policy_core_guard_recovery='initial_booking_parser'`
- trace confirms the surviving row still exits through the same owner seam:
  - `turn_planner.safe_booking_prompt_owner.v1`
  - `policy_core_guard -> timeout_initial_booking_collect`

## What changed versus r45
- `r45` degraded rows:
  - dialog `1`, turn `1`: `Я хочу записаться на маникюр на завтра.`
  - dialog `2`, turn `1`: `У меня есть запись на маникюр на завтра.`
  - dialog `6`, turn `1`: `Мне нужно записаться на маникюр.`
- After the bounded `r45` implementation:
  - rows with stronger temporal context no longer degrade
  - only the service-only fresh initial booking variant still degrades
- This is real progress, but not closure.

## Decision
- Do not open another same-shape envelope-only micro-fix by default.
- The next admissible move is a broader runtime family:
  - `implement_consultant_core_demo_salon_seed19_r46_initial_booking_owner_reset_runtime_family`
- Reason:
  - the surviving row is still in the same duplicated `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` authority seam in `truffles-api/app/services/reasoning_core.py`
  - `r45` implementation already used the bounded budget/envelope lever and still left one row alive
  - continuing to stack local tweaks in that seam would be symptom work, not authority reduction

## Residual debt
- `manual_audit.json` currently infers `judge_oracle_alignment_gap` as the root cause even though `summary.json` shows a threshold-only runtime breach on `degraded_fallback_rate`.
- That is a proof/control-plane gap.
- It is not the first blocker here, because the surviving runtime degraded row is directly visible in `responses.jsonl` and `trace_bundle.jsonl`.
- Duplicate booking-prompt candidate defs remain unresolved in `truffles-api/app/services/reasoning_core.py`.
- Prod floor remains degraded.

## Next admissible move
- `implement_consultant_core_demo_salon_seed19_r46_initial_booking_owner_reset_runtime_family`
