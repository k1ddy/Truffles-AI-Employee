# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R44 Completion Semantic Invalid Decision A922

## Truthful input artifacts
- `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/run_manifest.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`

## Non-canonical side artifact
- `/tmp/booking_quality/a922-go2f-seed19-r43` is explicitly non-canonical and not closure evidence because the replay was resumed into the same output directory after an incomplete first attempt, creating overlapping-writer risk.

## Completion classification
- `r44` is the first truthful completion replay after the repaired `r42` runtime family: `infra_valid=true`, `run_integrity_valid=true`, `manual_audit_status='done'`, `turns_strict_failed=0`, and `failure_families.json` is empty.
- The old `r42` blocker is closed on the live replay surface: `LLM-QUAL-a922-go2f-seed19-r44-004-09-ceeeaa` now records `decision_meta.action='booking_prompt'`, `tool_action='collect'`, and `strict_ok=true` instead of the old pricing `catalog.service_query` reply.
- `r44` remains semantically invalid, but not because of a surviving strict runtime family.

## Remaining semantic-invalid surfaces
- `summary.json` records `blocking_reasons={'handoff_miss': 4}` and `threshold_breaches=['degraded_fallback_rate']` while `manual_audit.json` records `judge_alignment='conflicted'`, `winner='contract'`, `conflict_count=23`, and `analyst_root_causes=['judge_oracle_alignment_gap']`.
- The four `handoff_miss` rows are all contract-valid booking continuations, not strict failures:
  - `LLM-QUAL-a922-go2f-seed19-r44-003-09-56bd10`
  - `LLM-QUAL-a922-go2f-seed19-r44-003-10-3277e4`
  - `LLM-QUAL-a922-go2f-seed19-r44-004-09-ceeeaa`
  - `LLM-QUAL-a922-go2f-seed19-r44-008-12-42e2da`
- On each row, `conversation_state='bot_active'`, `decision_meta.action='booking_prompt'`, `decision_meta.tool_action='collect'`, `decision_meta.expected_reply_type='time'`, and the outbox asks for `точное время`.
- `ops/diagnose.py:4252-4278` does not treat `точное время` as a valid `time` follow-up marker, so `contract_aligned_booking_collect` stays false and `ops/diagnose.py:9293-9301` still emits `handoff_miss`.

## Residual timeout/degrade evidence
- Row `LLM-QUAL-a922-go2f-seed19-r44-004-01-04d28b` is strict-green but truthful degraded evidence: `decision_meta.policy_core_mode='degraded_fallback'`, `decision_meta.policy_core_degrade_reason='policy_error:timeout'`, and `decision_meta.policy_core_guard_recovery='initial_booking_parser'`.
- `ops/diagnose.py:20512-20514` therefore computes `degraded_fallback_rate=1.0` on this run, so the threshold breach is real residual debt, not oracle drift.

## Verdict
- The old weekend-pricing runtime family is closed.
- The next admissible block is no longer runtime-owner repair.
- The dominant remaining blocker is proof/oracle parity in `ops/diagnose.py`: contract-valid exact-time collect prompts still produce false `handoff_miss` blocking reasons.
- Timeout-driven `degraded_fallback_rate` remains residual and must be rechecked on the next truthful completion replay after the proof/oracle family is repaired.

## Next admissible move
- `implement_consultant_core_demo_salon_seed19_r44_handoff_miss_collect_prompt_oracle_parity_proof_family`
