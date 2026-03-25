# TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-RUNTIME-DECISION-A922`
- `DEPENDS_ON`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_generated_booking_info_divergence_canary_replay`

## Название/цель
Repair the bounded seed-`19` runtime family where active booking/check-booking continuity is preempted by generated info/service-query owners, so hours/promo/weekend follow-ups stop leaking into irrelevant fact owners and canary re-entry can resume truthfully.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19/manual_audit.json`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`

## Invariant
- Preserve the already-green `r20` / seed-`7` runtime families.
- Do not weaken acceptance thresholds, judge gates, or seed generation.
- Do not touch frozen routers.
- Keep active requested-slot continuity (`service`/`time`) observable in `decision_meta` / `decision_trace`.

## Scope
- active booking/check-booking side-owner deferral for the seed-`19` divergence family
- explicit hours/promo follow-up resolution under booking continuity
- deterministic regressions for the surfaced seed-`19` phrases

## Out of scope
- PG checklist materialization
- seed `42`
- acceptance `lock` retry
- new oracle/judge work
- duplicate-def cleanup beyond touched live owners

## Touch-list
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_master_info_flow.py`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa forms unhappy paths interruptions continue form official docs`
- **Date/time (local):** `2026-03-22T18:55:00+05:00`
- **Why this query is precise:** the family is about preventing side-question handlers from stealing control from an active requested-slot owner during booking continuity.
- **Sources opened (from this query):**
  - `Rasa documentation / form unhappy-path guidance` — `https://rasa.com/docs/rasa/forms/`
- **Existing solutions found:** flow/form systems treat interruptions as temporary detours and then return control to the active requested slot rather than letting a side owner permanently replace the continuation.
- **Decision:** `reuse as design reference` — apply the same continuity rule in Truffles by deferring side owners that would preempt active booking continuity and by preferring the explicit interrupt intent when it exists.
- **Rejected options:** adopting external workflow primitives or a new dialog manager; this block is bounded to the existing runtime owner chain.
- **Open questions:** whether weekend follow-up will fully close once side-owner preemption is removed; closure will be proven only by replay.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing booking-interrupt owner path in `truffles-api/app/services/reasoning_core.py`
  - existing info resolver in `truffles-api/app/routers/webhook/info.py`
  - existing contracts/tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_master_info_flow.py`
- **External reuse:**
  - `https://rasa.com/docs/rasa/forms/`
- **Decision:** reuse the current booking-interrupt owner and info resolver; extend them rather than introducing a new owner path.
- **Rejected build scope:** no new runtime subsystem, no new acceptance tooling.

## Root cause (mandatory)
- **Symptom:** seed `19` generated dialogs route active booking/check-booking follow-ups into `pricing`, `duration`, or `services_overview` owners instead of preserving booking continuity and answering the intended hours/promo/weekend semantics.
- **Minimal reproduction:**
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`
  - inspect message ids `LLM-QUAL-a922-go2f-seed19-004-09-28263e`, `LLM-QUAL-a922-go2f-seed19-004-10-c4a861`, `LLM-QUAL-a922-go2f-seed19-007-10-55069e`
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19/trace_bundle.jsonl`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/info.py`
- **Five Whys:**
  1. Why did seed `19` fail? Because active booking turns were answered by irrelevant fact owners.
  2. Why did those owners win? Because direct catalog/service-query owners run before booking continuity recovery and lack the active-booking deferral guard.
  3. Why did booking continuity not recover the turn? Because `booking_prompt_owner` only sees the turn if those direct owners return `None`.
  4. Why did hours/promo still diverge even inside interruption semantics? Because explicit hours phrasing can coexist with false-positive `duration`, and promo phrasing with service mention can be suppressed by the current resolver.
  5. Why is this a runtime family instead of proof debt? Because the wrong owner and wrong `decision_meta/decision_trace` are emitted in live runtime artifacts.
- **Root cause statement:** the live owner chain lets direct side owners (`catalog_fact` / `service_query_fact`) preempt active booking continuity, and the current interrupt intent resolution undercovers explicit hours/promo variants, so the runtime answers with irrelevant fact owners before the booking/check-booking continuity owner can recover the turn.
- **Fix mechanism:** defer direct side owners when an active booking requested-slot (`service`/`time`) is open, then harden explicit hours/promo resolution so the booking interruption owner receives the correct intent and preserves the expected-reply contract.

## Plan
1. Add one bounded helper in `reasoning_core` that defers direct side owners under active booking requested-slot continuity.
2. Apply that guard to the live direct owners that surfaced in seed `19`.
3. Harden explicit hours/promo detection so the booking interruption owner resolves the right interrupt intent.
4. Add deterministic regressions for the exact seed-`19` phrases and the direct-owner deferral behavior.
5. Sync canon/session/packet and hand off to one guarded replay.

## DoD
- direct side owners no longer preempt active booking requested-slot continuity for the surfaced seed-`19` family
- explicit hours/promo follow-ups resolve through the bounded booking interruption path with preserved `expected_reply_type`
- deterministic regressions cover the seed-`19` phrases and the deferral contract
- canon/session/packet point at the implementation block and next replay move

## Work mode (mandatory)
- `implementation`

## Checks
- `pytest -q truffles-api/tests/test_master_info_flow.py -k "hours or promotions"`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or booking_prompt_owner_answers_explicit_hours_interrupt or direct_service_query_fact_defers_active_booking_interrupt or direct_catalog_fact_defers_active_booking_interrupt"`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated deterministic test output
- code diff in `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/routers/webhook/info.py`
- report in `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- Max replay runs: `0`
- Max lock runs: `0`
- Max new audits: `0`
- Fail-fast / scenario lock: deterministic-only in this block
- Stop condition: stop after deterministic regressions and governance stack are green; replay is the next block
- Escalation path: `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only bounded runtime fix, no rollout.
- **Go/no-go signals:** surfaced deterministic regressions pass and governance stack stays green.
- **Rollback:** revert the touched runtime/resolver/tests/docs files.
- **Post-release monitoring window:** guarded replay in the next block.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - block stays open until code, tests, canon, session log, and generated packet agree on the new replay handoff.

## Rollback
- revert touched runtime/resolver/tests/docs files; keep seed artifacts unchanged

## No-go
- do not retry acceptance `lock`
- do not run seed `42`
- do not relax oracle/thresholds
- do not patch frozen routers

## Risks/Blockers
- the seed `19` weekend turn may surface a second bounded runtime debt after the direct-owner preemption is removed
- live duplicate owner definitions in `reasoning_core.py` still increase read-path complexity

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: acceptance evidence-pack materialization, seed `42`, and duplicate-def cleanup stay deferred.
- `Why not in this block`: this block is bounded to the first surfaced runtime family and its deterministic closure surface.
- `Risk if deferred`: acceptance re-entry stays blocked until replay proves the runtime family closed.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one forthcoming replay TP.
- `Expiry/trigger to stop deferral`: stop deferral immediately if replay still surfaces a runtime blocker after this implementation.

## Next-block contract (mandatory)
- `Next block objective`: rerun the guarded seed replay family after the runtime fix.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or booking_prompt_owner_answers_explicit_hours_interrupt or direct_service_query_fact_defers_active_booking_interrupt or direct_catalog_fact_defers_active_booking_interrupt"`
- `Blocked-by conditions`: deterministic regressions stay red or root cause splits into a second independent family before replay.
- `Owner role for closure`: `Brain | Top Architect`
