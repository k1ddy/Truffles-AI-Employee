# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R45 Timeout Initial Booking Degraded Fallback Runtime Implementation A922

## Input truth
- `/tmp/booking_quality/a922-go2f-seed19-r45/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-decision-a922.md`

## Implemented repair
- `truffles-api/app/services/intent_service.py`
  - kept the bounded `max_tokens_override` hook so the fresh initial-booking owner can lower policy-core output budget without replacing semantic ownership
- `truffles-api/app/services/reasoning_core.py`
  - introduced a bounded `fresh_initial_booking_entry` envelope on both duplicated booking-prompt candidate defs
  - pre-seeded `slot_state.service` from the current message only on that bounded fresh-entry path
  - removed `info_refs` only on that bounded fresh-entry path so policy core no longer carries unrelated info envelopes into the initial booking collect contract
  - kept the bounded `max_tokens_override=160` only on that bounded fresh-entry path
  - preserved observable timeout recovery unchanged: if policy core still times out, runtime still emits `policy_core_mode='degraded_fallback'` / `policy_core_guard_recovery='initial_booking_parser'`
- `truffles-api/tests/test_intent.py`
  - kept deterministic coverage proving the explicit max-token override is honored by `route_llm_policy_core(...)`
- `truffles-api/tests/test_reasoning_core.py`
  - added regression coverage proving fresh initial booking entry now sends `slot_state={'service': 'Маникюр'}`, `info_refs=[]`, and the bounded max-token override
  - kept the existing timeout-recovery regressions green so the exception path stays observable instead of being hidden

## Deterministic evidence
- `pytest -q truffles-api/tests/test_intent.py -k "policy_core and max_tokens_override"`
  - `1 passed, 166 deselected`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or initial_booking_owner_recovers_timeout_before_terminal_handoff or policy_core_tokens"`
  - `3 passed, 204 deselected`
- `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py`
  - `pass`

## Live realism evidence
- `/tmp/booking_quality/a922-go2f-seed19-r45/initial_booking_policy_core_budget_probe_post_fix.json`
  - live candidate-path probe on `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)`
  - `3/4` trials returned non-degraded semantic `collect_slot='datetime'` with `slot_values={'service': 'Маникюр'}`
  - `0/4` trials emitted `policy_core_mode='degraded_fallback'`
  - `1/4` trial returned `candidate_is_none=true`, so closure is not claimed in this implementation block
- `/tmp/booking_quality/a922-go2f-seed19-r45/policy_core_envelope_probe.json`
  - direct provider probe remained volatile even after the bounded envelope change, so this block does not claim provider stability in isolation
  - that volatility is treated as residual risk and is one reason the next admissible move is still a fresh completion replay rather than a narrative closure claim

## What changed materially
- Before the fix, fresh initial booking entry reached policy core with no seeded service, general `info_refs`, and general request budget, then frequently degraded into `initial_booking_parser` recovery on the live owner path.
- After the fix, the same bounded fresh-entry path now carries the service already present in the current message, sends no unrelated `info_refs`, and caps policy-core output tokens at `160` only for this family.
- The repair does not hide failures: timeout recovery still exists and is still covered by deterministic tests. The change only narrows the initial-entry envelope so policy core has a better chance to produce the intended collect decision before the degrade path is needed.

## Residual debt
- Closure is not yet proven. A fresh completion replay is still required.
- Live provider variance remains visible in direct probes, so this block does not claim that the runtime family is fully closed.
- Duplicate booking-prompt candidate defs remain in `truffles-api/app/services/reasoning_core.py`.
- Replay control-plane stale simulation-id contamination remains unresolved.
- Prod floor remains degraded (`truffles-outbox`, `bge-m3`).

## Next admissible move
- `rerun_consultant_core_demo_salon_seed19_r45_timeout_initial_booking_degraded_fallback_canary_replay_to_completion`
