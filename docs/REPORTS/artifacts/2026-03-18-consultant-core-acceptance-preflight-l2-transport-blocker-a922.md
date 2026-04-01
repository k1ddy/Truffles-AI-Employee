# 2026-03-18 Consultant Core Acceptance Preflight L2 Transport Blocker (a922)

## Verdict Summary
- **FACT:** `implement_acceptance_preflight_l2_transport_blocker_closure_bundle` deleted the old runner-owned synthetic non-allowlist unique-JID seam from `ops/diagnose.py`: `_llm_quality_pick_jid(...)` in `unique` mode now prefers allowlist JIDs whenever they are available, so the old `999...@s.whatsapp.net` transport path is no longer the live path for truthful dev `L2`.
- **FACT:** the same block restored the strict confirm-hook status path for booking verification: `_llm_quality_should_send_confirm_hook(...)` now still sends a confirm hook for `calendar.get_booking` turns even when the scenario turn is tagged `confirm`.
- **FACT:** focused regressions are green: `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py` => `23 passed`; `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "allow_non_allowlist or run_completion_gap or tool_evidence"` => `1 passed, 100 deselected`.
- **FACT:** worktree runtime parity stayed truthful on `http://127.0.0.1:18184`: `curl -s http://127.0.0.1:18184/admin/version` returned `git_commit=0d8d2078697193832a2d6cae6709a2d7489bf9ca`, which matches `git rev-parse HEAD`.
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r7` removed the old `confirm_hook_missing` blocker but remained non-canonical: `summary.json` records `infra_valid=true`, `tool_evidence_reasons=[]`, `run_integrity_reasons=['run_completion_gap']`, and `manual_audit.md` records `dialogs_seen=2/10`.
- **FACT:** repo truth already treats `CHATFLOW_BILLING_BLOCKED` as an expected external-block contour rather than a runtime defect: `ops/diagnose.py` contains the billing-waiver detector and delivery-acceptance contract, and `truffles-api/tests/test_booking_quality_status_gate.py` proves delivery acceptance can stay valid under `delivery_waiver_billing`.
- **FACT:** the correction attempts `/tmp/booking_quality/l2-acceptance-preflight-a922-r9` and `/tmp/booking_quality/l2-acceptance-preflight-a922-r10` were invalid preflight rows only: `r9` hit the acceptance chain-controller gate, and `r10` hit `lock_fingerprint_unchanged_after_non_canonical` until the audited infra-recovery override was used.
- **FACT:** the bounded corrected rerun `/tmp/booking_quality/l2-acceptance-preflight-a922-r11` completed all dialogs and closed the transport blocker family truthfully: `summary.json` records `infra_valid=true`, `run_integrity_valid=true`, `tool_evidence_reasons=[]`, `responses_rows=144`, `trace_rows=144`, and `manual_audit.md` records `dialogs_seen=[1..10]` with no transport or run-integrity blocker remaining.
- **FACT:** `r11` also proves that unpaid-provider billing is not the live blocker for this dev lane: response rows still carry `CHATFLOW_BILLING_BLOCKED` on allowlist JIDs (`107` rows) plus `fallback_send_failed` (`5` rows), but `delivery_acceptance.status='pass'` and `quality_status.infra_valid=true` remain green.
- **FACT:** `r11` still ends as a truthful `GAP` because the remaining blocker is now semantic, not transport: `summary.json` records `semantic_valid=false`, `semantic_reasons=['blocking_reason', 'threshold_breach']`, blocking counts `judge_fail=21`, `handoff_miss=12`, `booking_flow_break=6`, and top failure families `expected_trace_miss` / `expected_meta_mismatch` centered on `session_memory`, with `manual_audit.md` recording `judge_alignment=conflicted`, `winner=contract`, and `judge_eval_conflict: turns=52`.
- **INFERENCE:** this package made admissible progress because the old unique-JID transport seam died and the L2 transport blocker family is now closed, but the package still ends as `GAP` because a narrower completed-run expectation/judge conflict family surfaced on `r11`.

## What Changed
- **FACT:** `ops/diagnose.py` now prefers allowlist JIDs in `_llm_quality_pick_jid(...)` for `--jid-mode unique`, using a stable run-scoped offset only inside the allowlist rather than forcing a synthetic `999...` JID whenever uniqueness is requested.
- **FACT:** `ops/diagnose.py` now routes the auto confirm hook through `_llm_quality_should_send_confirm_hook(...)`, so `calendar.get_booking` status checks still produce the confirm hook needed by the strict tool-evidence contract even on `confirm`-tagged turns.
- **FACT:** `truffles-api/tests/test_booking_quality_jid_mode.py` now covers allowlist preference for `unique` mode.
- **FACT:** `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` now covers the restored confirm-hook behavior for `calendar.get_booking` vs. ordinary `confirm`-tagged booking turns.

## Bounded Run Truth
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r7` is the first post-fix bounded run with full artifacts:
  - `quality_status.infra_valid=true`
  - `quality_status.tool_evidence_reasons=[]`
  - `quality_status.run_integrity_reasons=['run_completion_gap']`
  - response rows still use synthetic non-allowlist JIDs and transport reasons `CHATFLOW_ERROR` / `fallback_send_failed`
- **FACT:** `r7` therefore proves the confirm-hook family is closed but transport truth was still mixed with the old synthetic JID seam.
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r9` is an invalid acceptance-lane probe only; it proves the chain-controller gate correctly blocks direct acceptance-lane invocation from the dev L2 path.
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r10` is an invalid run-economy probe only; it proves a completed rerun on the same fingerprint requires the explicit audited non-canonical-lock retry override.
- **FACT:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r11` is the first corrected full rerun under billing-waiver truth:
  - `quality_status.infra_valid=true`
  - `quality_status.run_integrity_valid=true`
  - `quality_status.tool_evidence_reasons=[]`
  - `responses_rows=144`
  - `trace_rows=144`
  - `dialogs_seen=[1,2,3,4,5,6,7,8,9,10]`
- **FACT:** `r11` no longer fails on transport, tool evidence, or run integrity; it now fails only on semantic/threshold contours.

## Remaining Failure Family
- **FACT:** the top completed-run failure families from `r11` are:
  - `expected_trace_miss` x44
  - `expected_meta_mismatch` x37
  - `judge_fail` x17
- **FACT:** the highest-frequency families are centered on `session_memory` expectation evidence under `bot_active`, with smaller follow-on families around `llm_policy_plan_delta`, `question_contract`, and bounded fact-owner stages.
- **FACT:** the manual audit confirms this is no longer a transport story: the remaining findings are `semantic_invalid`, `pipeline_budget_exceeded` (`turns=1`), and `judge_eval_conflict` (`turns=52`).

## Expected Artifacts Not Produced
- **FACT:** no truthful green non-acceptance `L2` summary exists yet for checklist reuse, because `r11` is complete but semantically invalid.
- **FACT:** no fresh guarded `demo_salon` `lock` was started from this package because `go_to_full` still lacks a semantically valid `L2` row.

## Next Honest Path
1. Stop this package as `GAP`; do not claim `go_to_full` closure.
2. Author one bounded follow-up package for the surfaced completed-run expectation/judge conflict family from `r11`.
3. Return to acceptance preflight only after that package either deletes the surfaced family or truthfully narrows it again.

## Gap Register
- **GAP:** no semantically valid non-acceptance `L2` summary exists yet for `go_to_full`.
- **GAP:** the surviving blocker family is no longer transport or billing; it is the completed-run expectation/judge conflict family surfaced by `r11`.
- **GAP:** no fresh guarded `demo_salon` `lock` was started from this package because preflight still cannot truthfully go green.
