# 2026-03-22 - Consultant Core Demo Salon Seed19 R5 Post Verification Reschedule Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Landed the bounded runtime repair for the fresh seed-`19` replay blocker at dialog `1`, turn `13`.
- Rehydrated missing snapshot-grounded `service` / `datetime` inside the live later booking-prompt owner before recomputing the next missing slot.
- Mirrored the same continuity repair in the adjacent semantic booking recovery lane.
- Added one focused deterministic regression for post-verification exact-time reschedule continuity.

## Implementation
- `truffles-api/app/services/reasoning_core.py`
  - live later booking-prompt owner now restores snapshot-grounded `service` / `datetime` before `_next_booking_prompt(...)` on post-verification exact-time reschedule
  - semantic booking recovery now mirrors the same snapshot service/datetime rehydration before missing-slot recomputation
- `truffles-api/tests/test_reasoning_core.py`
  - added deterministic regression proving `Можно на 18:30?` keeps `service='Маникюр'`, updates `datetime='18:30'`, and leaves `expected_reply_type=name` while name is still pending

## Evidence
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule or updates_grounded_datetime_while_name_pending or check_booking_prompt_owner"`

## Result
- bounded runtime family is now landed locally
- focused deterministic coverage is green
- next honest move is one fresh exact replay on the same seed-`19` scenarios

## Next move
- `rerun_consultant_core_demo_salon_seed19_r5_post_verification_reschedule_canary_replay`
