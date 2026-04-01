# 2026-03-18 Consultant Core Acceptance Preflight Blocker (a922)

## Verdict Summary
- **FACT:** `implement_acceptance_preflight_blocker_closure_bundle` deleted the live code-owned phrase/prefix hardcode seam from `truffles-api/app/services/info_signal_service.py`: the surfaced raw availability/time/day/date prefix family now exits through `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml` instead of staying as inline owner literals.
- **FACT:** the hardcode-core preflight blocker is now green on the current worktree: `python3 ops/diagnose.py llm-quality-gates ... --output /tmp/a922-preflight-gates-after-hardcode.json` reports `quality_status.valid=true`, `blocking_reasons=[]`, and `hardcode_core_gate.valid=true`.
- **FACT:** fresh L1 evidence now exists: `pytest -q truffles-api/tests/test_booking_quality_guarded_wrapper.py::test_guarded_wrapper_allows_fresh_lock_after_audited_non_canonical_latest_run --junitxml=/tmp/booking_quality/l1-acceptance-preflight-a922/pytest-junit.xml` passed and produced `/tmp/booking_quality/l1-acceptance-preflight-a922/pytest-junit.xml`.
- **FACT:** runtime parity for non-acceptance L2 was reestablished on a worktree-owned API at `http://127.0.0.1:18184`; `curl -sf http://127.0.0.1:18184/admin/version` returned `git_commit=0d8d2078697193832a2d6cae6709a2d7489bf9ca`, which matches `git rev-parse HEAD` in this worktree.
- **FACT:** fresh L2 evidence was not materialized. The furthest dev run, `/tmp/booking_quality/l2-acceptance-preflight-a922-r3`, remained non-canonical: `summary.json` records `infra_valid=false`, `semantic_valid=false`, `tool_evidence_reasons=['confirm_hook_missing']`, `run_integrity_reasons=['run_completion_gap']`, and `stop_reason='signal_15'`; `manual_audit.md` records `run_incomplete`, `dialogs_seen=2/10`, and `judge_alignment=conflicted` with `winner=contract`.
- **FACT:** worktree runtime logs from the parity session show repeated `Outbound guard: TEST_MODE enabled, SKIP message to jid=...` for the unique test JIDs used by `l2-acceptance-preflight-a922-r3`, so the surviving blocker family is no longer hardcode preflight; it is the L2 transport / observability path under `TEST_MODE`.
- **INFERENCE:** this block made admissible architectural progress because the old live hardcode authority seam in `info_signal_service.py` died, but the package still ends as `GAP` because `go_to_full` cannot go green without one truthful non-acceptance L2 summary.

## What Changed
- **FACT:** `ops/diagnose.py` now ignores interpolation-only f-string literals during hardcode scans and only treats bare `=` as a phrase-branching signal inside signal-service files, which removes the false positive on the frozen `decision.py` fallback assignment without weakening the gate for actual signal-owner files.
- **FACT:** `truffles-api/app/services/info_signal_service.py` no longer hardcodes the surfaced availability/time/day/date phrase families inline; it now reads those families from cached lexicon getters backed by `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`.
- **FACT:** `truffles-api/tests/test_booking_quality_status_gate.py` now has focused regressions for the narrowed hardcode detector and the surviving signal-owner rows.

## Hardcode Gate Closure
- **FACT:** `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k 'hardcode_core or phrase_branching'` => `11 passed, 90 deselected`.
- **FACT:** `/tmp/a922-preflight-gates-after-hardcode.json` now records:
  - `quality_status.valid=true`
  - `quality_status.blocking_reasons=[]`
  - `hardcode_core_gate.valid=true`
  - `hardcode_core_gate.violations=[]`
- **FACT:** the old live code-owned seam that triggered `hardcode_core_gate:core_phrase_branching_detected` is therefore deleted or unreachable in the current worktree state.

## Fresh L1 Evidence
- **FACT:** the exact L1 target test required by the package passed and wrote machine-readable evidence to `/tmp/booking_quality/l1-acceptance-preflight-a922/pytest-junit.xml`.
- **FACT:** this satisfies the L1 side of `go_to_full` truthfully; no stale JUnit artifact was reused.

## Runtime Parity And L2 Attempts
- **FACT:** the first direct dev L2 attempt, `/tmp/booking_quality/l2-acceptance-preflight-a922`, failed on runtime fingerprint preflight because `http://127.0.0.1:8000/admin/version` was still serving commit `dbbf7c6929e4b98a2b18927c381a16a8ab7c4d49` instead of the worktree `HEAD`.
- **FACT:** the second attempt, `/tmp/booking_quality/l2-acceptance-preflight-a922-r1`, remained invalid because the previous failed run still required manual audit before another dev run could proceed.
- **FACT:** the third attempt, `/tmp/booking_quality/l2-acceptance-preflight-a922-r2`, localized a second preflight contract: `--jid-mode unique` required `--skip-outbox` or `--allow-non-allowlist`.
- **FACT:** the fourth attempt, `/tmp/booking_quality/l2-acceptance-preflight-a922-r3`, used `--allow-non-allowlist` and produced full artifacts, but it still did not yield truthful L2 evidence:
  - `summary.json`: `infra_valid=false`, `semantic_valid=false`, `tool_evidence_reasons=['confirm_hook_missing']`, `run_integrity_reasons=['run_completion_gap']`, `blocking_reasons={'judge_fail': 1, 'handoff_miss': 1, 'run_completion_gap': 119}`
  - `brief.md`: `stop_reason=signal_15`, `strict_pass_rate=0.75`, top failure families `expected_meta_mismatch`, `expected_trace_miss`, `expected_info_section_miss`
  - `manual_audit.md`: `run_incomplete`, `dialogs_seen=2/10`, `responses_rows=23`, `trace_rows=23`, `judge_alignment=conflicted`, `winner=contract`
- **FACT:** the worktree API log for that same run shows `Outbound guard: TEST_MODE enabled, SKIP message to jid=...` on the unique L2 JIDs, so the surviving blocker family is now localized to the TEST_MODE unique-JID transport / observability path rather than to hardcode preflight or stale runtime fingerprint.

## Expected Artifacts Not Produced
- **FACT:** no truthful non-acceptance L2 summary exists yet for `go_to_full`:
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r3/summary.json` exists but is invalid for checklist use
  - no fresh guarded `demo_salon` `lock` was attempted after the hardcode/L1 work because `go_to_full` still lacked a green L2 evidence row

## Next Honest Path
1. Stop this block as `GAP`; do not claim green preflight because L2 evidence is still non-canonical.
2. Author one bounded follow-up package for the surviving L2 transport / observability blocker family under worktree runtime `TEST_MODE`.
3. Return to the acceptance-preflight checklist only after that package either materializes one truthful L2 summary or narrows the blocker again.

## Gap Register
- **GAP:** fresh non-acceptance L2 evidence was not materialized, so `go_to_full` is still incomplete.
- **GAP:** the surviving blocker family is now the L2 transport / observability path under `TEST_MODE` with unique JIDs, not the hardcode-core preflight gate.
- **GAP:** no fresh guarded `demo_salon` `lock` was started from this block because preflight could not truthfully go green.
