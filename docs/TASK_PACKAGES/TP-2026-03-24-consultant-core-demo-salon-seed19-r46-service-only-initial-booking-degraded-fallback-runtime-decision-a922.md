# TP-2026-03-24 Consultant Core Demo Salon Seed19 R46 Service-Only Initial Booking Degraded Fallback Runtime Decision A922

## Title/goal
Classify the truthful `r46` completion replay after the bounded `r45` runtime implementation, prove exactly what survived, and choose the next block so the team does not continue ad-hoc envelope tuning inside the same duplicated owner seam.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-implementation-a922.md`
- CA_ID `a922-go2f-seed19-r46-service-only-initial-booking-degraded-fallback-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:platform.openai.com/docs latency optimization output tokens prompt size OpenAI API`
- **Date/time (local):** `2026-03-24 07:10 +05:00`
- **Sources opened (from this query):** `https://platform.openai.com/docs/guides/latency-optimization`
- **Found ready-made solutions:** the official OpenAI latency guide explicitly treats `max_tokens` as one latency lever, but also warns that reducing input tokens usually has limited effect and that higher-level architecture choices matter more than repeated prompt trimming.
- **Decision:** `reject` further same-seam budget-only tuning as the default next move; use the replay evidence to move the next implementation block up to owner-family reset.
- **Why:** `r45` implementation already applied bounded envelope tightening and `r46` still leaves one degraded row in the same duplicated owner seam.
- **Rejected options:** another same-shape token-only tweak, threshold weakening, hiding degrade flags, frozen-router edits.

## Root cause (mandatory)
- **Symptom:** truthful completion replay `r46` finishes `143/143` strict-green with `blocking_reasons.count=0` and empty `failure_families.json`, but `semantic_valid=false` remains because `degraded_fallback_rate=1.0` on one surviving initial booking row.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r46-005-01-df3da9` in `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl` and `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r46/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/initial_booking_policy_core_budget_probe_post_fix.json`
  - `truffles-api/app/services/reasoning_core.py:2190`
  - `truffles-api/app/services/reasoning_core.py:7160`
  - `truffles-api/app/services/reasoning_core.py:11898`
  - `truffles-api/tests/test_reasoning_core.py:8614`
  - `truffles-api/tests/test_reasoning_core.py:8668`
- **Five Whys:**
  1. Why is `r46` still semantically red if strict runtime is green? Because `summary.json` shows `metrics.counts.policy_core_degraded_turns=1` and `thresholds.breaches=['degraded_fallback_rate']`.
  2. Why is there still one degraded row? `LLM-QUAL-a922-go2f-seed19-r46-005-01-df3da9` still emits `policy_core_mode='degraded_fallback'` with `policy_core_guard_recovery='initial_booking_parser'` on `Я хочу записаться на маникюр.`.
  3. Why did the old `r45` implementation not close that row? It narrowed the fresh-entry envelope enough to repair rows with stronger temporal context, but the service-only fresh entry still depends on the same timeout-sensitive booking-prompt candidate owner.
  4. Why is this still the same owner family rather than a brand-new blocker? The surviving row still flows through `turn_planner.safe_booking_prompt_owner.v1` and the duplicated `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` seam in `reasoning_core.py`.
  5. Why not keep tuning the same seam again? The current replay already proves one bounded envelope tweak materially improved the family but did not close it; another same-shape tweak would continue symptom work inside the duplicated authority seam instead of reducing that seam.
- **Root cause statement:** after the bounded `r45` runtime repair, the remaining blocker is a narrowed but still runtime-owned initial-booking family: service-only fresh initial booking entry still degrades on the duplicated booking-prompt candidate seam in `reasoning_core.py`, so the next valid block should reset that owner family rather than keep stacking local envelope tweaks in place.
- **Fix mechanism:** move the next implementation block up one level to bounded initial-booking owner reset on non-frozen code, so service-only fresh entry no longer depends on the same duplicated timeout-sensitive candidate path; timeout recovery stays observable for true exceptions.

## Reuse-first plan (mandatory)
- Internal reuse: existing `turn_planner.safe_booking_prompt_owner.v1` contract, `route_llm_policy_core(...)`, current timeout-recovery tests, and target runtime modules under `truffles-api/app/core/`.
- External reuse: `https://platform.openai.com/docs/guides/latency-optimization`
- Why not reinvent the wheel: the runtime already has owner contracts and target modules; the next block should relocate authority, not add a new parallel mini-runtime.

## Invariant
Do not weaken thresholds, do not hide `policy_core_mode='degraded_fallback'`, do not reopen the repaired `r42` or `r44` families, and do not touch frozen routers.

## Scope
Truthful `r46` completion classification only.

## Out of scope
- runtime implementation inside this decision block
- proof/oracle retuning inside this decision block
- prod-floor repair
- acceptance `lock/full`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-demo-salon-seed19-r46-service-only-initial-booking-degraded-fallback-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-demo-salon-seed19-r46-service-only-initial-booking-degraded-fallback-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r46/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r46/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`

## Plan (1..N)
1. Confirm that `r46` is a truthful fresh completion replay on canonical runtime parity.
2. Prove exactly which row still degrades and compare it with the pre-fix `r45` family.
3. Decide whether the next move should remain same-seam tuning or escalate to a broader owner-family reset.
4. Publish the decision and hand off to one bounded runtime implementation family.

## DoD
- `r46` completion truth is recorded with exact file evidence
- the old `r45` family is proven narrowed from three degraded rows to one surviving row
- the surviving row is classified as a runtime-owned service-only fresh initial booking family on the same duplicated owner seam
- the next block is fixed as owner-family reset, not another same-shape micro-tune

## Work mode (mandatory)
`closure`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this decision block; `r46` already exists and is audited.
- **Max replay runs:** `0` additional.
- **Stop condition:** if `r46` were not a truthful completion replay, stop and reopen closure instead of choosing a new runtime block.

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r46 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r46/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r46/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r46/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r46/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r45/initial_booking_policy_core_budget_probe_post_fix.json`

## Release safety (mandatory for non-doc changes)
- **Strategy:** no production rollout in this decision block; classify only.
- **Go/no-go signals:** `r46` remains completion-valid, the surviving row is exactly identified, and no code changes are made in this block.
- **Rollback:** not applicable; docs/evidence only.
- **Post-release monitoring window:** not applicable.

## Rollback
Not applicable; no implementation changes are made in this block.

## No-go
- no runtime patch before the `r46` family is published truthfully
- no threshold/oracle weakening
- no frozen-router edits
- no baseline update from a semantically invalid run

## Risks/blockers
- `manual_audit.json` currently infers `judge_oracle_alignment_gap` even though `summary.json` shows a threshold-only runtime breach on `degraded_fallback_rate`; this proof/control-plane inconsistency must be recorded as residual debt, but it does not replace the surviving runtime blocker because the degraded row is directly visible in `responses.jsonl` and `trace_bundle.jsonl`.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate booking-prompt candidate defs remain unresolved; manual-audit root-cause inference still drifts toward judge conflict even when the surviving blocker is runtime threshold breach; replay control-plane simulation-id debt remains; prod floor remains degraded.
- **Why not in this block:** this block only classifies `r46` and chooses the next bounded family.
- **Risk if deferred:** the team can either resume micro-tuning the same seam or misread the surviving blocker as proof-only because `manual_audit.json` drifts.
- **Linked follow-up Task Package(s):** bounded initial-booking owner reset runtime implementation; then one fresh completion replay to prove closure truthfully.
- **Expiry/trigger to stop deferral:** immediate; the next implementation block must reduce authority overlap on this surviving owner family.

## Next-block contract (mandatory)
- **Next block objective:** implement a bounded initial-booking owner reset on non-frozen code so service-only fresh initial booking entry no longer depends on the duplicated timeout-sensitive booking-prompt candidate seam.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or initial_booking_owner_recovers_timeout_before_terminal_handoff or policy_core_tokens"`
- **Blocked-by conditions:** if the fix requires threshold weakening, frozen-router edits, or another same-shape envelope tweak that leaves the duplicated owner seam as the sole executable authority, stop and reopen the family scope.
- **Owner role for closure:** Brain / Top Architect
