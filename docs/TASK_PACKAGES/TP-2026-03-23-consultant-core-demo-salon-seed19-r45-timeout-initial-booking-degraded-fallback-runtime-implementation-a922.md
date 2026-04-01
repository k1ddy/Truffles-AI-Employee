# TP-2026-03-23 Consultant Core Demo Salon Seed19 R45 Timeout Initial Booking Degraded Fallback Runtime Implementation A922

## Title/goal
Remove timeout-driven `degraded_fallback` as the dominant outcome on simple initial booking entry by tightening the bounded fresh-entry policy-core envelope on the existing owner path: seed the service from the current message, drop unrelated `info_refs`, and cap output tokens while preserving LLM-first semantic ownership and observable degrade semantics for real exceptions.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-decision-a922.md`
- CA_ID `a922-go2f-seed19-r45-timeout-initial-booking-degraded-fallback-family`

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI API latency optimization max_tokens`
- **Date/time (local):** `2026-03-23 21:37 +05:00`
- **Sources opened (from this query):** `https://platform.openai.com/docs/guides/predicted-outputs`
- **Found ready-made solutions:** the official OpenAI docs treat output-side budgeting as a latency lever, so the next bounded block should tighten the existing policy-core request envelope on the proven owner path before considering any semantic-owner replacement.
- **Decision:** `reuse` the existing policy-core route and tighten its bounded fresh-entry envelope for initial booking entry.
- **Why:** the surviving family is timeout-driven on a proven owner path; the bounded fix should reduce timeout pressure without replacing policy-core semantic ownership.
- **Rejected options:** deterministic booking-owner replacement, threshold weakening, frozen-router edits, proof-only tuning.

## Root cause (mandatory)
- **Symptom:** truthful completion replay `r45` is strict-green but semantically red because three simple initial booking entry rows degrade into `policy_core_mode='degraded_fallback'` with `policy_core_guard_recovery='initial_booking_parser'`.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r45-001-01-3996bc`, `LLM-QUAL-a922-go2f-seed19-r45-002-01-a5a212`, and `LLM-QUAL-a922-go2f-seed19-r45-006-01-83a5c9` in `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl` and `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r45/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/policy_core_latency_probe.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/initial_booking_policy_core_budget_probe_post_fix.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r45/policy_core_envelope_probe.json`
  - `truffles-api/app/services/reasoning_core.py:7225`
  - `truffles-api/app/services/reasoning_core.py:7507`
  - `truffles-api/app/services/reasoning_core.py:11831`
  - `truffles-api/app/services/intent_service.py:353`
  - `truffles-api/app/services/intent_service.py:2476`
- **Five Whys:**
  1. Why is `r45` still semantically red if strict runtime is green? Because `degraded_fallback_rate=1.0` on the three surfaced initial booking rows.
  2. Why do those rows degrade? Because the initial booking owner reaches `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)`, policy core times out, and the owner falls into `initial_booking_parser` recovery.
  3. Why does policy core still time out on a simple booking request? The current route reaches policy core with a general fresh-entry envelope even though the expected contract output is a short collect decision and the current message already contains the service hint.
  4. Why is that the right bounded runtime family? `r45` has no blocking reasons and no proof-family residuals; only the timeout-degrade threshold survives.
  5. Why not replace semantic ownership with deterministic booking logic? The contract explicitly keeps semantic ownership in policy core; parser recovery is allowed only as an observable exception path.
- **Root cause statement:** simple initial booking entry still reaches policy core with an unnecessarily wide fresh-entry envelope: it does not pre-seed the service from the current message and still carries general `info_refs`, so live policy-core calls can exceed the runtime timeout window or return unusable output on a short collect-only contract and degrade into `initial_booking_parser` recovery.
- **Fix mechanism:** on fresh initial booking entry only, pre-seed `slot_state.service` from the current message, send no `info_refs`, and apply a bounded max-token cap; prove that this narrower envelope is sent only on the surfaced family and keep timeout recovery unchanged if the bounded request still fails.

## Reuse-first plan (mandatory)
- Internal reuse: existing `route_llm_policy_core(...)` path in `truffles-api/app/services/intent_service.py`, current initial-booking owner flow in `truffles-api/app/services/reasoning_core.py`, existing service hint extraction in frozen `decision.py`, and existing timeout-recovery regressions in `truffles-api/tests/test_reasoning_core.py`.
- External reuse: `https://platform.openai.com/docs/guides/predicted-outputs`
- Why not reinvent the wheel: the runtime already has the semantic owner and the degrade path; this block only tightens the bounded fresh-entry request envelope on the proven hotspot.

## Invariant
Do not weaken semantic thresholds, do not hide `policy_core_mode='degraded_fallback'`, do not replace policy-core semantic ownership with deterministic booking routing, and do not touch frozen routers.

## Scope
- bounded runtime change on the initial-booking policy-core owner path
- focused deterministic regressions for the new bounded fresh-entry envelope behavior
- local-first realism probe on the same initial booking message

## Out of scope
- proof/oracle edits
- acceptance `lock/full`
- prod-floor repair
- duplicate-def cleanup beyond the touched family

## Touch-list
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r45-timeout-initial-booking-degraded-fallback-runtime-implementation-a922.md`

## Plan (1..N)
1. Add a bounded policy-core max-token override hook that can be applied without changing semantic ownership.
2. On fresh initial booking entry only, pre-seed `service` from the current message and drop `info_refs` before policy core runs.
3. Add deterministic regressions proving the bounded envelope is sent on the surfaced family and does not replace timeout recovery semantics.
4. Run focused deterministic tests and a local realism probe against the live provider path.
5. Publish the implementation report and hand off to one fresh completion replay.

## DoD
- the bounded initial-booking owner path sends the narrower fresh-entry policy-core envelope on fresh entry: seeded service, empty `info_refs`, and reduced output budget
- timeout recovery semantics remain unchanged if policy core still times out
- focused deterministic regressions are green
- at least one local realism probe proves the bounded path returns a semantic collect decision without degraded fallback on the surfaced message
- the next move is one fresh completion replay, not another runtime patch by default

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this implementation block.
- **Max replay runs:** `0` here; closure replay is the next block.
- **Stop condition:** if the bounded fix requires frozen-router edits, threshold changes, deterministic replacement of policy-core semantics, or widening the change beyond fresh initial booking entry, stop and reopen the family.

## Checks
- `pytest -q truffles-api/tests/test_intent.py -k "policy_core and max_tokens_override"`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or initial_booking_owner_recovers_timeout_before_terminal_handoff or policy_core_tokens"`
- `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py`

## Evidence
- code diff in `truffles-api/app/services/intent_service.py`
- code diff in `truffles-api/app/services/reasoning_core.py`
- focused deterministic regressions in `truffles-api/tests/test_intent.py` and `truffles-api/tests/test_reasoning_core.py`
- local realism probe artifacts under `/tmp/booking_quality/a922-go2f-seed19-r45/`
- implementation report for this block

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime repair; no production rollout in this block.
- **Go/no-go signals:** focused deterministic proof is green, the local realism probe shows a non-degraded collect decision on the surfaced message, and no frozen file is touched.
- **Rollback:** revert the bounded fresh-entry envelope change and paired regressions.
- **Post-release monitoring window:** not applicable.

## Rollback
Revert the bounded fresh-entry policy-core envelope change and its paired regressions.

## No-go
- no frozen-router edits
- no threshold/oracle weakening
- no deterministic booking-owner replacement
- no replay/baseline update inside this implementation block

## Risks/blockers
- tightening the fresh-entry envelope too aggressively can distort semantic output or make live provider variance surface as `invalid_json`; the fix must stay bounded to the fresh initial-booking collect contract and be validated with live provider evidence.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate booking-prompt candidate defs remain unresolved; timeout recovery logic remains duplicated in `reasoning_core.py`; replay control-plane simulation-id debt remains; prod floor remains degraded.
- **Why not in this block:** this block only removes timeout-driven degraded fallback as the dominant outcome on the surfaced owner path.
- **Risk if deferred:** the team can keep getting semantically red closure artifacts even after already-closed runtime/proof families are fixed.
- **Linked follow-up Task Package(s):** fresh completion replay after this implementation block; then a new decision block if any blocker survives.
- **Expiry/trigger to stop deferral:** immediate after focused validation; the next block must rerun completion replay.

## Next-block contract (mandatory)
- **Next block objective:** rerun one fresh completion replay to confirm the bounded initial-booking timeout/degrade family is closed and to classify any surviving blocker truthfully.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r46 --status done --strict-artifacts`
- **Blocked-by conditions:** fresh local runtime parity must be preserved; if focused tests or the realism probe fail, do not run the replay.
- **Owner role for closure:** Brain / Top Architect
