# 2026-03-22 - Consultant Core Demo Salon Seed19 R4 Contract-Aligned Confirm Hook Proof Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONTRACT-ALIGNED-CONFIRM-HOOK-PROOF-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Landed one bounded proof-only implementation family in `ops/diagnose.py`; runtime code and frozen routers were left untouched.
- Synthetic confirm-hook eligibility now mirrors the strict confirm-evidence contract for `confirm`-tagged status-check alias turns.
- Added deterministic proof in `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` for `check_booking`, `check_record`, and strict alias evidence acceptance.
- The next honest move is now one fresh exact replay on the original seed-`19` blocker scenarios.

## Code changes
### `ops/diagnose.py`
- `_llm_quality_should_send_confirm_hook(...)` now treats `confirm`-tagged `check_booking` and `check_record` the same way as `calendar.get_booking` for synthetic confirm-hook eligibility.
- This closes the parity gap with `_llm_quality_build_tool_evidence_status(...)`, which already counted those alias intents as confirm opportunities under strict evidence.

### `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- Added regression proving `confirm`-tagged `check_booking` turns now send confirm hooks.
- Added regression proving `confirm`-tagged `check_record` turns now send confirm hooks.
- Added strict-policy regression proving alias confirm evidence is accepted when hooks are present.

## Deterministic evidence
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py` -> `pass`
- `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"` -> `6 passed, 14 deselected`

## Canon result
- Active block moves from proof decision to proof implementation.
- No runtime family was reopened.
- The next admissible move is one fresh exact replay on `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`.

## Residual debt
- downstream semantic mismatch on dialog `2`, turn `9` is still unclassified until the replay becomes infra-valid
- acceptance evidence-pack materialization and seed `42` remain deferred
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt

## Next move
- `rerun_consultant_core_demo_salon_seed19_r4_confirm_hook_canary_replay`
