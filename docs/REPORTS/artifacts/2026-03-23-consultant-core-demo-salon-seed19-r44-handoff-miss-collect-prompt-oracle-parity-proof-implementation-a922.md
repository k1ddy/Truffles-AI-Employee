# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R44 Handoff Miss Collect Prompt Oracle Parity Proof Implementation A922

## Input truth
- `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r44-completion-semantic-invalid-decision-a922.md`

## Implemented repair
- `ops/diagnose.py`
  - extended `_llm_quality_has_expected_followup_prompt(...)` so `reply_type='time'` now accepts the live `точное время` phrasing already emitted by the bounded booking collect path
- `truffles-api/tests/test_booking_quality_status_gate.py`
  - added focused regressions proving the helper accepts exact-time prompts and that both reschedule and cancel collect continuations no longer emit false `handoff_miss`

## Deterministic evidence
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "handoff_miss or contract_valid_reschedule_collect or exact_time_prompt"`
  - `5 passed, 112 deselected`
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`
  - `pass`

## What changed materially
- Before the fix, the exact-time collect rows in `r44` asked `Подскажите, пожалуйста, точное время.`, but `ops/diagnose.py` did not treat that phrase as a valid `time` follow-up prompt.
- After the fix, the same helper path recognizes that phrasing, so contract-valid exact-time collect continuations can satisfy `contract_aligned_booking_collect` and stop promoting false `handoff_miss` blockers.

## Residual debt
- Fresh replay proof is still required. Deterministic coverage proves the bounded oracle family locally, but it does not replace one truthful completion replay.
- The timeout-driven `degraded_fallback_rate` residual from `LLM-QUAL-a922-go2f-seed19-r44-004-01-04d28b` remains unresolved.
- Duplicate booking-prompt owner defs remain in `truffles-api/app/services/reasoning_core.py`.
- Replay control-plane stale simulation-id contamination remains unresolved.
- Prod floor remains degraded (`truffles-outbox`, `bge-m3`).

## Next admissible move
- `rerun_consultant_core_demo_salon_seed19_r44_handoff_miss_collect_prompt_oracle_parity_canary_replay_to_completion`
