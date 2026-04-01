# TP-2026-03-23 Consultant Core Demo Salon Seed19 R44 Completion Semantic Invalid Decision A922

## Title/goal
Classify the truthful `r44` completion replay after the repaired `r42` runtime family, lock the remaining semantic-invalid surfaces, and choose one bounded next block that removes false blockers before any new runtime patch.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-implementation-a922.md`
- CA_ID `a922-go2f-seed19-r44-completion-semantic-invalid-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python any iterable official documentation`
- **Date/time (local):** `2026-03-23 19:55 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3/library/functions.html#any`
- **Found ready-made solutions:** the official Python docs confirm the bounded `any(iterable)` pattern already used across the repo for phrase-marker checks; the next proof block can extend the existing marker list without adding a new matcher design.
- **Decision:** `reuse` the existing helper shape in the next bounded proof/oracle implementation block.
- **Why:** this decision block does not start code changes, but it locks the next implementation family to a small marker/parity change inside the existing helper path.
- **Rejected options:** new matcher abstractions, runtime-owner edits, threshold downgrades.

## Root cause (mandatory)
- **Symptom:** truthful completion replay `r44` is infra-valid, run-integrity-valid, and strict-green (`143/143` turns, `failure_families.json` empty), but `semantic_valid=false` still blocks closure on `blocking_reasons={'handoff_miss': 4}` plus `threshold_breaches=['degraded_fallback_rate']`.
- **Minimal reproduction:** inspect `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`, and the four contract-valid rows `LLM-QUAL-a922-go2f-seed19-r44-003-09-56bd10`, `LLM-QUAL-a922-go2f-seed19-r44-003-10-3277e4`, `LLM-QUAL-a922-go2f-seed19-r44-004-09-ceeeaa`, and `LLM-QUAL-a922-go2f-seed19-r44-008-12-42e2da` in `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/run_manifest.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/failure_families.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`
  - `ops/diagnose.py:4252`
  - `ops/diagnose.py:4261`
  - `ops/diagnose.py:9272`
  - `ops/diagnose.py:9293`
  - `ops/diagnose.py:20512`
  - `truffles-api/tests/test_booking_quality_status_gate.py:2131`
  - `truffles-api/tests/test_booking_quality_status_gate.py:2156`
  - `truffles-api/tests/test_booking_quality_status_gate.py:374`
- **Five Whys:**
  1. Why is `r44` still semantically red if strict runtime is green? Because blocking reasons still count `handoff_miss=4` and thresholds still breach on `degraded_fallback_rate`.
  2. Why do the four rows count as `handoff_miss`? Because HQ1 still treats reschedule/cancel turns as missed handoff when the collect prompt is not recognized as a contract-valid booking continuation.
  3. Why is the collect prompt not recognized? `ops/diagnose.py:4261-4268` recognizes time prompts like `какое время` / `когда вам удобно`, but not the live `точное время` phrasing used in all four `r44` rows.
  4. Why does that matter? `ops/diagnose.py:9272-9301` only suppresses `handoff_miss` when `contract_aligned_booking_collect` is true; if the prompt helper returns false, the same contract-valid row is still promoted to `handoff_miss`.
  5. Why is there still a threshold breach after the old runtime family closed? Row `LLM-QUAL-a922-go2f-seed19-r44-004-01-04d28b` records `decision_meta.policy_core_mode='degraded_fallback'` with `policy_core_degrade_reason='policy_error:timeout'`, so `ops/diagnose.py:20512-20514` truthfully computes `degraded_fallback_rate=1.0` on this completion run.
- **Root cause statement:** after the repaired `r42` runtime family, the dominant surviving blocker is now proof/oracle parity inside `ops/diagnose.py`: contract-valid time-collect booking prompts that ask for `точное время` are not recognized as follow-up prompts, so HQ1 emits false `handoff_miss` blocking reasons on four strict-green rows; a separate residual threshold blocker remains from one truthful timeout-driven `degraded_fallback` turn.
- **Fix mechanism:** first repair the bounded proof/oracle parity family in `ops/diagnose.py` and its tests so contract-valid exact-time collect prompts stop emitting `handoff_miss`; then rerun one fresh completion replay to determine whether the timeout-driven `degraded_fallback_rate` breach remains as the sole surviving blocker.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing HQ1 helpers in `ops/diagnose.py`, existing status-gate tests in `truffles-api/tests/test_booking_quality_status_gate.py`, and the truthful `r44` completion artifact.
- **External reuse:** `https://docs.python.org/3/library/functions.html#any`
- **Why not reinvent the wheel:** strict runtime evidence is already green; the next admissible change is bounded proof/oracle parity, not a new runtime branch.

## Invariant
Do not weaken semantic thresholds, do not normalize the timeout degrade as acceptable by policy, and do not reopen the repaired weekend-pricing runtime family without new evidence.

## Scope
Truthful completion-surface classification only.

## Out of scope
- runtime implementation changes before the semantic-invalid family is split truthfully
- prod-floor repair
- acceptance `lock/full`
- threshold edits or oracle downgrades

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r44-completion-semantic-invalid-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r44-completion-semantic-invalid-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/run_manifest.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`

## Plan (1..N)
1. Confirm that `r44` is a truthful completion replay with zero strict runtime failures.
2. Verify that the old `r42` weekend-pricing row is now strict-green on the same locked scenario surface.
3. Classify the remaining semantic-invalid surface into bounded proof/oracle versus residual timeout/degrade evidence.
4. Lock the next admissible implementation family and leave the other surface as explicit residual debt.

## DoD
- `r44` completion truth is recorded with exact file evidence
- the old `r42` strict runtime family is explicitly closed on `r44`
- the remaining semantic-invalid surface is split into bounded next-family work with a deterministic first check

## Work mode (mandatory)
`closure`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this decision block; `r44` already exists and is audited.
- **Max replay runs:** `0` additional.
- **Stop condition:** if `r44` were not a truthful completion replay, stop and reopen the closure lane instead of proposing a new family.

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r44 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r44/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r44/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/run_manifest.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r44/responses.jsonl`

## Release safety (mandatory for non-doc changes)
- **Strategy:** no production rollout in this decision block; classify only.
- **Go/no-go signals:** `r44` remains completion-valid, the old runtime blocker is closed, and no code changes are made in this block.
- **Rollback:** not applicable; docs/evidence only.
- **Post-release monitoring window:** not applicable.

## Rollback
Rollback: not applicable; no implementation changes are made in this block.

## No-go
- no runtime patch before the semantic-invalid completion surface is classified
- no threshold/oracle weakening
- no frozen-router edits
- no baseline update from a semantically invalid run

## Risks/blockers
- the timeout-driven `degraded_fallback_rate` breach can remain after the proof/oracle family is repaired, so a fresh completion replay is still mandatory before declaring semantic closure.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate booking-prompt owner defs remain unresolved; replay control-plane still carries stale simulation-id debt; prod floor remains degraded; one timeout-driven `degraded_fallback` turn still exists in `r44`.
- **Why not in this block:** this block only classifies the truthful completion surface and chooses the next bounded family.
- **Risk if deferred:** the team can mistake false semantic blockers for runtime regressions and keep burning time on the wrong layer.
- **Linked follow-up Task Package(s):** bounded proof/oracle parity implementation for contract-valid exact-time collect prompts; then one fresh completion replay to reclassify the residual timeout/degrade surface.
- **Expiry/trigger to stop deferral:** immediate; the next implementation block must either remove the false `handoff_miss` blockers or prove they are still runtime-owned.

## Next-block contract (mandatory)
- **Next block objective:** repair the bounded proof/oracle family so contract-valid `booking_prompt` time-collect replies that ask for `точное время` no longer emit `handoff_miss` blocking reasons.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "handoff_miss or contract_valid_reschedule_collect"`
- **Blocked-by conditions:** if the fix requires runtime/frozen-router edits or threshold changes, stop and reopen the semantic-invalid family as a broader mixed-layer decision.
- **Owner role for closure:** Brain / Top Architect
