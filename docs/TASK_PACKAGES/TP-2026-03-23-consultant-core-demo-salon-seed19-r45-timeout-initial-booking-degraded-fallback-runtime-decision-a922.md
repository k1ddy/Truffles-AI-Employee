# TP-2026-03-23 Consultant Core Demo Salon Seed19 R45 Timeout Initial Booking Degraded Fallback Runtime Decision A922

## Title/goal
Classify the first truthful completion replay after the repaired `r44` proof family, lock the remaining runtime-owned semantic blocker, and choose one bounded next block that removes timeout-driven `degraded_fallback` on simple initial booking entry without weakening the contract.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r44-handoff-miss-collect-prompt-oracle-parity-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r44-handoff-miss-collect-prompt-oracle-parity-proof-implementation-a922.md`
- CA_ID `a922-go2f-seed19-r45-timeout-initial-booking-degraded-fallback-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:platform.openai.com/docs latency optimization OpenAI API max output tokens`
- **Date/time (local):** `2026-03-23 21:35 +05:00`
- **Sources opened (from this query):** `https://platform.openai.com/docs/guides/rate-limits/retrying-with-exponential-backoff%20.eot`
- **Found ready-made solutions:** the official OpenAI docs explicitly treat `max_tokens` as a first-class request budget component, so the next runtime block should prefer bounded output-budget control on the existing policy-core path over a new semantic owner.
- **Decision:** `reuse` the existing policy-core route and tune its bounded request budget inside the next implementation family instead of replacing semantic ownership.
- **Why:** this decision block does not start code, but it locks the next runtime block to a bounded policy-core latency/budget lever rather than a new deterministic booking path.
- **Rejected options:** new deterministic booking owner, threshold weakening, frozen-router edits, proof-only retuning.

## Root cause (mandatory)
- **Symptom:** truthful completion replay `r45` is infra-valid, strict-green (`143/143` turns, `failure_families.json` empty), and has no blocking reasons, but `semantic_valid=false` remains because `degraded_fallback_rate=1.0` on three initial booking turns.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r45-001-01-3996bc`, `LLM-QUAL-a922-go2f-seed19-r45-002-01-a5a212`, and `LLM-QUAL-a922-go2f-seed19-r45-006-01-83a5c9` in `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl` and `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r45/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/run_manifest.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/failure_families.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`
  - `truffles-api/app/services/reasoning_core.py:7225`
  - `truffles-api/app/services/reasoning_core.py:7507`
  - `truffles-api/app/services/reasoning_core.py:11831`
  - `truffles-api/app/services/reasoning_core.py:11980`
  - `truffles-api/tests/test_reasoning_core.py:8614`
  - `truffles-api/tests/test_reasoning_core.py:17033`
- **Five Whys:**
  1. Why is `r45` still semantically red if strict runtime is green? Because `summary.json` records `policy_core_turns=3`, `policy_core_degraded_turns=3`, and `degraded_fallback_rate=1.0`.
  2. Why do those turns count as degraded? Because the initial booking owner records `policy_core_mode='degraded_fallback'` and `policy_core_guard_recovery='initial_booking_parser'` on the three surfaced rows.
  3. Why does the initial booking owner emit degraded fallback? `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` calls `route_llm_policy_core(...)`, and on `timeout` / `deadline_exceeded` it falls through `_resolve_turn_planner_safe_initial_booking_timeout_collect_candidate(...)` instead of getting a semantic answer from policy core.
  4. Why is that still the first truthful blocker after the repaired `r44` proof family? `r45` has `failure_families.json` empty and `blocking_reasons.count=0`, so the old false `handoff_miss` family is closed; only the timeout-degrade threshold survives.
  5. Why is the remaining family runtime-owned rather than proof-owned? The degrade flags and `policy_core_guard` trace entries are emitted by `reasoning_core.py` on the live reply path before the oracle reads them.
- **Root cause statement:** after the repaired `r44` proof family, the surviving blocker is a runtime-owned timeout/degrade family on fresh initial booking entry: simple booking turns still depend on `_try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(...)`, and when `route_llm_policy_core(...)` times out, the live path degrades into deterministic `initial_booking_parser` recovery that keeps rows contract-green but semantically red under `degraded_fallback_rate`.
- **Fix mechanism:** keep LLM-first semantic ownership, but bound the initial-booking policy-core path so simple fresh booking entry can finish within budget without falling into timeout-driven degraded recovery; parser recovery remains only as an observable exception path, not the dominant outcome.

## Reuse-first plan (mandatory)
- Internal reuse: existing `route_llm_policy_core(...)` path in `truffles-api/app/services/intent_service.py`, the current initial-booking owner in `truffles-api/app/services/reasoning_core.py`, and the existing timeout-recovery regressions in `truffles-api/tests/test_reasoning_core.py`.
- External reuse: `https://platform.openai.com/docs/guides/rate-limits/retrying-with-exponential-backoff%20.eot`
- Why not reinvent the wheel: the product surface and semantic owner already exist; the next block must reduce timeout/degrade on this bounded owner path, not replace it with a new deterministic booking subsystem.

## Invariant
Do not weaken semantic thresholds, do not hide `policy_core_mode='degraded_fallback'`, do not re-open the repaired `r42` or `r44` families, and do not move semantic ownership out of policy core.

## Scope
Truthful `r45` completion classification only.

## Out of scope
- runtime implementation before this decision is published
- proof/oracle edits
- prod-floor repair
- acceptance `lock/full`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r45/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r45/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/run_manifest.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`

## Plan (1..N)
1. Confirm that `r45` is the first truthful completion replay after the repaired `r44` proof family.
2. Verify that the old `handoff_miss` proof blocker and the old weekend-pricing runtime blocker remain closed on the same replay surface.
3. Classify the surviving semantic-invalid surface into one bounded runtime timeout/degrade family.
4. Lock the next implementation block to that family only.

## DoD
- `r45` completion truth is recorded with exact file evidence
- the old `r44` proof family is explicitly closed on `r45`
- the surviving semantic-invalid surface is classified as one runtime-owned timeout/degrade family with a deterministic next block

## Work mode (mandatory)
`closure`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this decision block; `r45` already exists and is audited.
- **Max replay runs:** `0` additional.
- **Stop condition:** if `r45` were not a truthful completion replay, stop and reopen closure instead of selecting a new runtime family.

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r45 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r45/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r45/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/run_manifest.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`

## Release safety (mandatory for non-doc changes)
- **Strategy:** no production rollout in this decision block; classify only.
- **Go/no-go signals:** `r45` remains completion-valid, the old proof blocker is closed, and no code changes are made in this block.
- **Rollback:** not applicable; docs/evidence only.
- **Post-release monitoring window:** not applicable.

## Rollback
Rollback: not applicable; no implementation changes are made in this block.

## No-go
- no runtime patch before the `r45` family is published truthfully
- no threshold/oracle weakening
- no frozen-router edits
- no baseline update from a semantically invalid run

## Risks/blockers
- the next runtime block can regress into “hide the degrade” instead of removing the timeout cause; that would violate the contract and must be rejected.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate booking-prompt candidate defs remain unresolved; policy-core timeout recovery remains duplicated inside `reasoning_core.py`; replay control-plane stale simulation-id debt remains; prod floor remains degraded.
- **Why not in this block:** this block only classifies the truthful completion surface and chooses the next bounded family.
- **Risk if deferred:** the team can keep spending runtime effort on already-closed proof families instead of removing the remaining timeout-degrade owner path.
- **Linked follow-up Task Package(s):** bounded runtime implementation for `r45` initial-booking timeout/degrade family; then one fresh completion replay to confirm the threshold closure.
- **Expiry/trigger to stop deferral:** immediate; the next implementation block must either reduce the timeout-driven degraded family or prove a different runtime owner causes the same rows.

## Next-block contract (mandatory)
- **Next block objective:** remove timeout-driven `degraded_fallback` on simple initial booking entry while preserving policy-core semantic ownership and observable degrade semantics for true exceptions.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or initial_booking_owner_recovers_timeout_before_terminal_handoff"`
- **Blocked-by conditions:** if the fix requires threshold weakening, frozen-router edits, or replacing policy-core semantic ownership with deterministic booking routing, stop and reopen the family scope.
- **Owner role for closure:** Brain / Top Architect
