# 2026-03-19 Consultant Core Acceptance Preflight L2 Expectation Conflict (a922)

## Verdict Summary
- **FACT:** `implement_acceptance_preflight_l2_expectation_conflict_failure_family_closure_bundle` deleted the old observer-owned direct `question_contract` / duplicate meta-trace expectation seam in `ops/diagnose.py`: completed rerun `/tmp/booking_quality/l2-acceptance-preflight-a922-r14` reduced `expected_trace_miss` from `59` to `6` and `expected_meta_mismatch` from `52` to `5` while keeping `infra_valid=true` and `run_integrity_valid=true`.
- **FACT:** the observer now accepts canonical new-core evidence for booking-progress continuity: `_llm_quality_has_resume_contract_meta_trace_fallback(...)` recognizes `session_memory` `question_set`, service-clarify question-contract traces, and grounded `catalog.service_query` sidecar replies; `_chaos_matches_action(...)` and `_chaos_action_fallback_ok(...)` also accept `turn_outcome.action` and `branch_missing` booking fallback replies.
- **FACT:** focused regressions are green: `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k 'resume_contract or sidecar or branch_missing or turn_outcome'` => `4 passed, 101 deselected`; `pytest -q truffles-api/tests/test_booking_quality_status_gate.py` => `105 passed`.
- **FACT:** runtime parity stayed truthful on `http://127.0.0.1:18184`: `/admin/version` still matches worktree `HEAD` (`0d8d2078697193832a2d6cae6709a2d7489bf9ca`).
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r12` is not evidence: the operator polluted the output dir before launch, so `llm-quality` stopped with `output-dir already contains artifacts` and produced no scenario execution.
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r13` is also not evidence: it was launched in acceptance lane by mistake and truthfully stopped on `chain_controller_required` before any dialogs ran.
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r14` is the only fresh completed non-acceptance `L2` rerun from this block: `summary.json` records `infra_valid=true`, `run_integrity_valid=true`, `responses_rows=146`, `trace_rows=146`, and `manual_audit.md` records `dialogs_seen=[1..10]`.
- **FACT:** `r14` still ends as a truthful `GAP`: `semantic_valid=false`, `semantic_reasons=['blocking_reason', 'threshold_breach']`, `judge_fail=15`, `expected_action_mismatch=6`, `handoff_miss=10`, `booking_flow_break=9`, and audit findings `pipeline_budget_exceeded` (`turns=3`) plus `judge_eval_conflict` (`turns=39`).
- **INFERENCE:** this block made admissible progress because the old observer seam is no longer the dominant blocker family, but it still stops as `GAP` because a narrower post-observer runtime family surfaced on `r14`.

## What Changed
- **FACT:** `ops/diagnose.py` now treats `session_memory` `question_set` and `service_clarify` traces as canonical resume-contract evidence in `_llm_quality_has_resume_contract_meta_trace_fallback(...)`.
- **FACT:** `ops/diagnose.py` now treats grounded `catalog.service_query` `duration` / `truth_fallback` replies as valid sidecar evidence in `_llm_quality_has_catalog_service_answer_sidecar_fallback(...)`.
- **FACT:** `ops/diagnose.py` now recognizes `turn_outcome.action` inside `_chaos_matches_action(...)` and accepts `branch_missing` booking fallback replies inside `_chaos_action_fallback_ok(...)` when the runtime is still in booking-active state.
- **FACT:** `truffles-api/tests/test_booking_quality_status_gate.py` now covers the new observer fallbacks for `session_memory` question-set evidence, `service_clarify` question contracts, catalog sidecar fact replies, `turn_outcome.action`, and `branch_missing` booking fallback replies.

## Bounded Run Truth
- **FACT:** `r12` is an operator-invalid probe only; it proves the output-dir guard correctly rejects polluted output directories.
- **FACT:** `r13` is an acceptance-lane probe only; it proves the chain-controller gate correctly blocks direct acceptance-lane invocation from this dev `L2` path.
- **FACT:** `r14` is the first fresh completed rerun after the observer-seam changes:
  - `quality_status.infra_valid=true`
  - `quality_status.run_integrity_valid=true`
  - `responses_rows=146`
  - `trace_rows=146`
  - `dialogs_seen=[1,2,3,4,5,6,7,8,9,10]`
- **FACT:** `r14` proves the old dominant observer mismatch family is no longer live:
  - `expected_trace_miss`: `59 -> 6`
  - `expected_meta_mismatch`: `52 -> 5`
  - `judge_fail`: `21 -> 15`
- **FACT:** top failure families moved away from `session_memory` observer mismatch and are now:
  - `judge_fail` on `stage=escalation` / `state=bot_active` x6
  - `judge_fail` on `stage=session_memory` / `state=bot_active` x4
  - `expected_action_mismatch` on `stage=escalation` / `state=bot_active` x3
  - `expected_meta_mismatch` on `stage=marketing_reply_context` / `state=bot_active` x3
  - `expected_trace_miss` on `stage=marketing_reply_context` / `state=bot_active` x3

## Remaining Failure Family
- **FACT:** the dominant surviving runtime slice in `r14` is `branch_missing` booking escalation/reply behavior:
  - 5 failing rows with `action=reply`, `intent=booking`, `source=tool_registry`, `last_stage=escalation`
  - plus 2 more booking rows at `last_stage=session_memory`
  - representative outbox: `Не могу определить филиал для записи. Уточните, пожалуйста, филиал.`
  - representative reasons: `expected_action_mismatch`, `judge_fail`, and bounded `expected_info_section_miss` / `info_section_miss`
- **FACT:** the second surviving slice is `marketing_reply_context` / `internal_error` on cancellation turns:
  - 4 failing rows with `action=error`, `intent=internal_error`, `source=reasoning_core`, `last_stage=marketing_reply_context`
  - representative outbox: `Извините, уведомление не доставилось из-за технической ошибки. Попробуйте позже.`
- **FACT:** smaller surviving slices remain:
  - one repeated-name `booking_slot_stall` row (`dialog 6 turn 13`)
  - one promo/info misroute row (`dialog 7 turn 7`)
  - one `fact_without_evidence` `consult_reply` row (`dialog 9 turn 14`)
  - one `missing_bot_reply` internal-error row (`dialog 2 turn 1`)
- **FACT:** the audit keeps contract-first arbitration on `r14`: `judge_alignment=conflicted`, `winner=contract`, `conflict_count=39`.

## Expected Artifacts Not Produced
- **FACT:** no semantically valid non-acceptance `L2` summary exists yet for `go_to_full`, because `r14` is complete but still semantic-red.
- **FACT:** no guarded `demo_salon` acceptance `lock` was started from this block because `go_to_full` still lacks a semantically valid fresh `L2` row.

## Next Honest Path
1. Stop this implementation block as `GAP`; do not claim `go_to_full` closure.
2. Author one bounded follow-up package for the narrower post-observer runtime failure family surfaced by `r14`.
3. Return to acceptance preflight only after that package either deletes the surfaced runtime family or truthfully narrows it again.

## Gap Register
- **GAP:** no semantically valid non-acceptance `L2` summary exists yet for `go_to_full`.
- **GAP:** the surviving blocker is no longer the old observer expectation seam; it is the narrower post-observer runtime family surfaced by `r14` (`branch_missing` booking escalation replies, `marketing_reply_context` internal-error cancellation turns, and a few bounded residual rows).
- **GAP:** no fresh guarded `demo_salon` `lock` was started from this package because acceptance preflight still cannot truthfully go green.
