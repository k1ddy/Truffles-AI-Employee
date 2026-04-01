# 2026-03-22 - Consultant Core Demo Salon Seed19 R5 Post Verification Reschedule Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-RUNTIME-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Re-audited fresh exact replay `/tmp/booking_quality/a922-go2f-seed19-r5` after the proof-only confirm-hook parity fix.
- Locked the old `confirm_hook_missing` blocker as closed on fresh replay truth.
- Classified the first surviving blocker as a runtime continuity bug on dialog `1`, turn `13`.
- Recorded explicit shadow-risk on the live owner surfaces in `truffles-api/app/services/reasoning_core.py` so the next bounded runtime block writes only to the executable later defs.

## Decision
- `r5` restores proof/tool-evidence parity and is no longer blocked by confirm-hook materialization.
- The next honest move is not more proof work and not acceptance evidence work.
- The next honest move is one bounded runtime implementation family for post-verification exact-time reschedule continuity.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r5/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py:4933`
- `truffles-api/app/services/reasoning_core.py:6005`
- `truffles-api/app/services/reasoning_core.py:9774`
- `truffles-api/app/services/reasoning_core.py:10846`
- `truffles-api/tests/test_reasoning_core.py:10777`

## Verdict
- `turn 13` = `runtime contract bug`
- surviving family = post-verification exact-time reschedule must preserve grounded `service` and keep `expected_reply_type=name`
- next move = `implement_consultant_core_demo_salon_seed19_r5_post_verification_reschedule_runtime_family`
