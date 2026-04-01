# TP-2026-03-23 Consultant Core Demo Salon Seed19 R44 Handoff Miss Collect Prompt Oracle Parity Proof Implementation A922

## Title/goal
Repair the bounded proof/oracle family from truthful completion replay `r44` so contract-valid `booking_prompt` time-collect replies that ask for `точное время` no longer emit false `handoff_miss` blocking reasons.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r44-completion-semantic-invalid-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r44-completion-semantic-invalid-decision-a922.md`
- CA_ID `a922-go2f-seed19-r44-handoff-miss-collect-prompt-oracle-parity-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python str casefold documentation`
- **Date/time (local):** `2026-03-23 20:07 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3/library/stdtypes.html#str.casefold`
- **Found ready-made solutions:** Python's official docs define `str.casefold()` as the aggressive caseless normalization primitive for string matching. The repo already uses casefolded prompt comparisons, so the bounded fix is to extend the existing prompt-marker tuple instead of introducing a new matcher.
- **Decision:** `reuse` the existing follow-up prompt helper in `ops/diagnose.py` and extend the `time` markers with the live exact-time phrasing.
- **Why:** the surfaced blocker is a proof/oracle parity gap inside the current helper path; new regex or runtime logic is unnecessary.
- **Rejected options:** threshold downgrades, runtime-owner edits, frozen-router edits, new classifier abstractions.

## Root cause (mandatory)
- **Symptom:** `r44` is strict-green but semantically red because `blocking_reasons={'handoff_miss': 4}` still fires on four contract-valid exact-time collect rows.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r44-003-09-56bd10`, `LLM-QUAL-a922-go2f-seed19-r44-003-10-3277e4`, `LLM-QUAL-a922-go2f-seed19-r44-004-09-ceeeaa`, and `LLM-QUAL-a922-go2f-seed19-r44-008-12-42e2da` in `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`
  - `ops/diagnose.py:4252`
  - `ops/diagnose.py:4261`
  - `ops/diagnose.py:9293`
  - `truffles-api/tests/test_booking_quality_status_gate.py:2131`
  - `truffles-api/tests/test_booking_quality_status_gate.py:2156`
- **Five Whys:**
  1. Why do four rows still block semantic closure? Because HQ1 still emits `handoff_miss`.
  2. Why does HQ1 emit `handoff_miss` on strict-green rows? Because the collect prompt is not recognized as a contract-valid booking continuation.
  3. Why is the collect prompt not recognized? `_llm_quality_has_expected_followup_prompt(...)` does not include the live `точное время` phrasing in its `time` prompt markers.
  4. Why does that create a blocker? `_llm_quality_collect_hq1_classes(...)` only suppresses `handoff_miss` when `contract_aligned_booking_collect` is true; without a recognized follow-up prompt it still promotes the row to a blocker.
  5. Why is this the right next family? `failure_families.json` is empty on `r44`; the old runtime family is already closed, so the remaining `handoff_miss` blockers are proof/oracle-owned.
- **Root cause statement:** the proof/oracle follow-up prompt helper in `ops/diagnose.py` is missing the exact-time phrasing used on four contract-valid `r44` rows, so HQ1 still misclassifies them as `handoff_miss` even though strict runtime evidence is green.
- **Fix mechanism:** extend the `time` prompt markers in `_llm_quality_has_expected_followup_prompt(...)` with `точное время`, add bounded status-gate regressions for exact-time reschedule/cancel collect continuations, and then rerun one fresh completion replay.

## Reuse-first plan (mandatory)
- **Internal reuse:** `_llm_quality_has_expected_followup_prompt(...)`, `_llm_quality_collect_hq1_classes(...)`, and `truffles-api/tests/test_booking_quality_status_gate.py`.
- **External reuse:** `https://docs.python.org/3/library/stdtypes.html#str.casefold`
- **Why not reinvent the wheel:** the existing helper path already does casefolded phrase checks; the bug is one missing prompt marker, not a missing subsystem.

## Invariant
Do not touch runtime routing, do not weaken thresholds, and do not relabel the timeout-driven `degraded_fallback_rate` residual as solved in this block.

## Scope
- bounded proof/oracle parity fix in `ops/diagnose.py`
- focused deterministic regressions in `truffles-api/tests/test_booking_quality_status_gate.py`

## Out of scope
- runtime code changes
- timeout/degraded-fallback repair
- prod-floor repair
- acceptance `lock/full`

## Touch-list
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r44-handoff-miss-collect-prompt-oracle-parity-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r44-handoff-miss-collect-prompt-oracle-parity-proof-implementation-a922.md`

## Plan (1..N)
1. Extend the `time` follow-up prompt markers to accept `точное время` in the existing helper.
2. Add focused regressions proving exact-time reschedule/cancel collect continuations no longer emit `handoff_miss`.
3. Run focused deterministic validation.
4. Publish the implementation report and hand off to one fresh completion replay.

## DoD
- exact-time collect prompts are recognized by the HQ1 follow-up helper
- targeted status-gate regressions are green
- the next move is one fresh completion replay, not another proof patch by default

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this implementation block.
- **Max replay runs:** `0` here; closure replay is the next block.
- **Stop condition:** if the fix requires runtime/frozen-router edits or threshold changes, stop and reopen the family scope before further changes.

## Checks
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "handoff_miss or contract_valid_reschedule_collect or exact_time_prompt"`
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_status_gate.py`

## Evidence
- code diff in `ops/diagnose.py`
- focused proof regressions in `truffles-api/tests/test_booking_quality_status_gate.py`
- implementation report for this block

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only proof/oracle repair; no production rollout in this block.
- **Go/no-go signals:** focused deterministic proof is green and no runtime/frozen file is touched.
- **Rollback:** revert the bounded prompt-marker change and the paired tests.
- **Post-release monitoring window:** not applicable.

## Rollback
Revert the bounded prompt-marker change and its paired regressions.

## No-go
- no runtime-owner edits
- no threshold/oracle weakening
- no frozen-router edits
- no timeout/degrade tuning inside this block

## Risks/blockers
- `degraded_fallback_rate` can remain the only blocker after this proof family is repaired, so replay closure is still mandatory.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** the timeout-driven `degraded_fallback` row in `r44` remains unresolved; duplicate booking-prompt owner defs remain; replay control-plane stale simulation-id debt remains; prod floor remains degraded.
- **Why not in this block:** this block removes only the false `handoff_miss` blockers.
- **Risk if deferred:** runtime timeout debt can remain hidden behind proof noise or reappear as the sole blocker on the next replay.
- **Linked follow-up Task Package(s):** fresh completion replay after this proof fix; then a timeout/degrade decision block if the threshold breach survives.
- **Expiry/trigger to stop deferral:** immediate after focused proof validation; the next block must rerun completion replay.

## Next-block contract (mandatory)
- **Next block objective:** rerun one fresh completion replay to verify the false `handoff_miss` blockers are gone and to truthfully reclassify the residual timeout/degrade surface.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r45 --status done --strict-artifacts`
- **Blocked-by conditions:** fresh local runtime parity must be preserved; if focused proof tests fail, do not run the replay.
- **Owner role for closure:** Brain / Top Architect
