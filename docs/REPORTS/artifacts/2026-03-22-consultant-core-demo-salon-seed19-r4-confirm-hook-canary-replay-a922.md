# 2026-03-22 - Consultant Core Demo Salon Seed19 R4 Confirm Hook Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R4-CONFIRM-HOOK-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Started a fresh local runtime from the current worktree on `127.0.0.1:18186` and proved `/admin/version.git_commit == HEAD` before replay.
- Reused the exact `r4` replay command shape with only `run_id` / `output_dir` changed and produced fresh artifact `/tmp/booking_quality/a922-go2f-seed19-r5`.
- Strict audit on `r5` restores infra/tool-evidence truth:
  - `infra_valid=true`
  - `tool_evidence.valid=true`
  - `confirm_hook_events=1`
  - `confirm_hook_missing` no longer survives
- The first surviving blocker is now runtime-only on dialog `1`, turn `13`, not proof/tooling.

## Fresh replay evidence
- Runtime parity:
  - `0d8d2078697193832a2d6cae6709a2d7489bf9ca == /admin/version.git_commit`
- Fresh replay artifact:
  - `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r5/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r5/manual_audit.json`
- Exact replay contract preserved:
  - `--scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json`
  - `--baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json`
  - `--max-failures 1`

## Truthful split
- The bounded proof family is closed on replay truth.
  - `r4` blocker was `tool_evidence:confirm_hook_missing`
  - `r5` now records `tool_evidence.valid=true` and observes confirm evidence on the surfaced alias row:
    - dialog `1`, turn `12`
    - `turn_tags=['confirm']`
    - `tool_signals.calendar.intent='check_booking'`
    - `tool_hooks=['confirm', 'calendar']`
- The first surviving blocker is now dialog `1`, turn `13`:
  - user: `Можно на 18:30?`
  - previous turn `12` had already restored `booking_slots.service='Маникюр'`, `booking_slots.datetime='15:00'`, and `expected_reply_type=name`
  - runtime on turn `13` reopens generic booking collect:
    - `decision_meta.action='booking_prompt'`
    - `decision_meta.source='llm_policy_core'`
    - `decision_meta.expected_reply_type='service_choice'`
    - `booking_slots={'datetime': '18:30'}`
  - strict fail reason: `expected_state_mismatch`
- This is therefore a fresh runtime continuity bug, not a proof/tooling blocker.

## Classification
- `r5` is admissible fresh replay evidence for blocker classification:
  - `infra_valid=true`
  - `tool_evidence.valid=true`
  - identical scenario file / baseline reuse
  - fresh runtime parity proved before replay
- `semantic_valid=false` and `run_completion_gap` are expected consequences of fail-fast replay with `--max-failures 1`; they do not reclassify the first surviving blocker back into proof/tooling.
- First surviving blocker class:
  - `runtime contract bug`
  - family: post-verification exact-time reschedule must preserve grounded service and keep `expected_reply_type=name`

## Shadow-risk note
- The failing live path crosses shadowed top-level owner names already tracked by the architecture guard:
  - `_try_handle_turn_planner_safe_booking_prompt_owner_cutover` at `truffles-api/app/services/reasoning_core.py:4933` and `truffles-api/app/services/reasoning_core.py:9774`
  - `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover` at `truffles-api/app/services/reasoning_core.py:6005` and `truffles-api/app/services/reasoning_core.py:10846`
- Python executes the later definitions, so the next bounded runtime block must write only against the live later defs and add deterministic coverage for this exact continuity contract.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "confirm_hook or check_booking_intent_to_confirm_signal or strict_policy_accepts_check_booking_alias_confirm_hook"` → `6 passed, 14 deselected`
- runtime parity probe against `http://127.0.0.1:18186/admin/version` → `match=True`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 ... --output-dir /tmp/booking_quality/a922-go2f-seed19-r5 --run-id a922-go2f-seed19-r5 ...` → completed with `stop_reason=max_failures_reached:1`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r5 --status done --strict-artifacts`

## Closure verdict
- No more proof-only work is admissible on this family first.
- The next honest move is `classify_consultant_core_demo_salon_seed19_r5_post_verification_reschedule_runtime_family`.
