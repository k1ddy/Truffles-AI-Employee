# 2026-03-22 — Consultant Core Demo Salon Main Canary R19 Contract-Aligned Oracle Proof Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-PROOF-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Landed one bounded proof-only implementation family in `ops/diagnose.py`; runtime code and frozen routers were left untouched.
- Judge suppression now recognizes the surfaced contract-valid follow-up envelopes on `r19`:
  - active booking `booking_prompt` with a deterministic follow-up prompt
  - `check_booking_prompt` with `expected_reply_reason=calendar_get_booking_collect_reference`
  - `master_service_not_found` collect inside active booking continuity
- HQ1 no longer over-classifies `handoff_miss` for contract-valid active booking continuations that intentionally keep collection alive.
- Targeted deterministic proof is green, and a helper probe on the existing `r19` artifact now returns `suppress=True` and `hq1=[]` for turns `6`, `9`, `11`, and `12`.

## Code changes
### `ops/diagnose.py`
- `ops/diagnose.py:4322-4378`
  - normalized `meta_action` inside judge suppression
  - added explicit suppression for contract-valid `booking_prompt` follow-up turns without requiring extra reason-code noise
  - added explicit suppression for `check_booking_prompt` reference-collection turns
  - added explicit suppression for `master_service_not_found` collect turns that keep booking continuity alive
- `ops/diagnose.py:9183-9220`
  - taught HQ1 to recognize contract-aligned booking collect continuity before emitting `handoff_miss`
  - preserved blocking behavior when strict `expected_action_mismatch` still exists

### Targeted regressions
- `truffles-api/tests/test_booking_quality_judge_suppression.py:126-187`
  - added coverage for booking-prompt follow-up suppression, check-booking collect-reference suppression, and master-service-not-found collect suppression
- `truffles-api/tests/test_booking_quality_status_gate.py:2051-2098`
  - added coverage proving HQ1 ignores contract-valid reschedule collect continuations both with and without explicit handoff expectation

## Deterministic evidence
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py` → `pass`
- `pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py -k "missed_question or handoff_miss"` → `15 passed, 111 deselected`
- Helper probe on `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`:
  - turn `6` → `{'suppress': True, 'hq1': []}`
  - turn `9` → `{'suppress': True, 'hq1': []}`
  - turn `11` → `{'suppress': True, 'hq1': []}`
  - turn `12` → `{'suppress': True, 'hq1': []}`

## Canon result
- Active block now moves from proof decision to proof implementation.
- No runtime family was reopened.
- The next honest move is one fresh replay on the same locked canary surface.

## Residual debt
- fresh replay after the oracle parity fix is still pending
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt
- final program acceptance / open-world closure remain pending

## Next move
- `rerun_consultant_core_demo_salon_r19_contract_aligned_oracle_canary_replay`
