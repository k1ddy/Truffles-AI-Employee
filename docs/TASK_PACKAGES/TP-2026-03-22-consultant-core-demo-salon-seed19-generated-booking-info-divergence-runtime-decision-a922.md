# TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-ACCEPTANCE-GO-TO-FULL-EVIDENCE-PACK-FAMILY-A922`
- `DEPENDS_ON`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_generated_booking_info_divergence_runtime_family`

## Название/цель
Truthfully classify the fresh seed-`19` generated multi-seed semantic blocker from the post-`r20` acceptance lane, split runtime vs proof debt, and lock one bounded next family before any new code.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`: no runtime or oracle code is in scope in this decision block; only docs/canon/session artifacts are touched.
- `Baseline commands`:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json, pathlib
summary = json.loads(pathlib.Path('/tmp/booking_quality/a922-go2f-seed19/summary.json').read_text())
print((summary.get('quality_status') or {}).get('blocking_reasons'))
PY`
- `FACT findings`:
  - seed `7` is fresh-green and admissible for the evidence pack
  - seed `19` is fresh semantic-red while infra and run integrity remain green
  - the blocker is visible in runtime `decision_meta` / `decision_trace`, not only in judge output

## Invariant
- Do not weaken acceptance/proof gates to recover the evidence pack.
- Do not relabel fresh seed-`19` semantic red as checklist-only debt.
- Do not touch frozen routers.

## Scope
- classify the seed-`19` blocker family
- decide whether the first admissible next move is runtime, pack/data, or proof
- sync canon to the truthful next move

## Out of scope
- runtime implementation
- proof/oracle rewrites
- fresh seed `42` run
- checklist assembly
- acceptance `lock` retry

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
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
- **Query (exact):** `Rasa forms interruptions requested slot official docs`
- **Date/time (local):** `2026-03-22T18:10:00+05:00`
- **Why this query is precise:** the surfaced seed-`19` family is about preserving requested-slot continuity through info interruptions during an active booking/check-booking flow.
- **Sources opened (from this query):**
  - `Rasa Forms documentation` — `https://rasa.com/docs/rasa/forms/`
- **Existing solutions found:** official Rasa guidance treats interruptions as expected unhappy paths and returns control to the active form/requested slot after handling the interruption.
- **Decision:** `reuse as design reference` — keep our own architecture, but use the same continuity principle: answer the interruption without losing the active requested-slot contract.
- **Rejected options:** adopting Rasa-specific workflow mechanics directly inside runtime core; this repo already has its own typed dialog-state and boundary contracts.
- **Open questions:** none before the decision handoff.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `/tmp/booking_quality/a922-go2f-seed19/{summary.json,brief.md,failure_families.json,responses.jsonl,scenarios.json}`
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- **External reuse:**
  - `https://rasa.com/docs/rasa/forms/` as continuity-reference only
- **Decision:** reuse existing local evidence and one external continuity reference; do not open implementation code in this block.
- **Rejected build scope:** new runtime/oracle changes before the layer decision is locked.

## Root cause (mandatory)
- **Symptom:** the post-`r20` go-to-full evidence pack cannot be completed because fresh seed `19` is semantic-red even though infra and run integrity are green.
- **Minimal reproduction:**
  - `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --quality-lane dev --count 10 --seed 19 ... --output-dir /tmp/booking_quality/a922-go2f-seed19 --run-id a922-go2f-seed19`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`
- **Evidence:** `/tmp/booking_quality/a922-go2f-seed19/{summary.json,brief.md,failure_families.json,responses.jsonl,scenarios.json,manual_audit.json}`
- **Five Whys:**
  1. Why did the evidence-pack family stop? Because seed `19` finished semantic-red.
  2. Why is seed `19` semantic-red? Because fresh generated dialogs surfaced blocking semantic divergence, including `irrelevant_fact_rate` threshold breach.
  3. Why is that not a checklist-only issue? Because the failing turns happen before checklist assembly and are visible in runtime `decision_meta` / `decision_trace`.
  4. Why is that not a pack/data gap? Because `demo_salon` already carries truthful hours/promotions data in `SALON_TRUTH.yaml`.
  5. Why is decision work required before code? Because the same run also contains advisory judge/HQ1 conflict, so runtime vs proof must be split truthfully.
- **Root cause statement:** fresh seed-`19` generated coverage surfaced a real runtime-semantic interruption family: under active booking/check-booking continuity, some info-style follow-ups are routed to irrelevant fact owners (`pricing`, `duration`, `services_overview`) or lose pending-question continuity instead of honoring the requested hours/promo/weekend semantics.
- **Fix mechanism:** first lock the blocker as a bounded runtime family, explicitly defer advisory oracle debt, then open one implementation-family for active-booking info interruption semantics.

## Plan
1. Extract the exact failing seed-`19` turns, scenario expectations, and runtime outputs.
2. Split runtime-semantic failures from advisory judge/HQ1 conflicts.
3. Decide the rightful owning layer.
4. Publish one decision report and sync canon to the next bounded move.

## DoD
- one truthful decision TP/report exists for seed `19`
- current blocker is classified by layer
- canon/session/packet agree on the new active block and next move

## Work mode (mandatory)
- `forensic`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`
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
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/{summary.json,brief.md,failure_families.json,responses.jsonl,scenarios.json,manual_audit.json}`

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- Max replay runs: `0`
- Max lock runs: `0`
- Max new audits: `1` (already used on seed `19`)
- Fail-fast / scenario lock: none; this block must not launch a new quality run
- Stop condition: stop as soon as the blocker is classified truthfully by layer
- Escalation path: `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** decision-only block; no runtime rollout.
- **Go/no-go signals:** canon must point at the surfaced seed-`19` blocker and no acceptance evidence claim may survive past the semantic-red run.
- **Rollback:** revert doc/canon updates only.
- **Post-release monitoring window:** none; no rollout in this block.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - block stays open until canon, session log, and generated packet all point at the same active decision TP.

## Rollback
- revert doc/canon/session updates only; preserve seed artifacts and audits

## No-go
- do not resume seed `42` before seed `19` is classified
- do not assemble the PG checklist against a semantic-red seed set
- do not reopen oracle thresholds or acceptance gates as a shortcut
- do not edit frozen routers

## Risks/Blockers
- generated multi-seed dialogs may include both runtime bugs and proof drift in the same artifact
- duplicate owner surfaces in `reasoning_core.py` may complicate later implementation scoping

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: acceptance evidence pack, seed `42`, checklist, and acceptance `lock` remain deferred; duplicate-def debt remains deferred.
- `Why not in this block`: this block is decision-only and exists to prevent the acceptance lane from hiding a new runtime family.
- `Risk if deferred`: without a clean decision, the team could either force checklist work past a runtime blocker or reopen proof/oracle churn prematurely.
- `Linked follow-up Task Package(s)`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` and one forthcoming runtime implementation TP for the seed-`19` family.
- `Expiry/trigger to stop deferral`: stop deferral immediately after the runtime family is either implemented or disproved.

## Next-block contract (mandatory)
- `Next block objective`: implement the bounded runtime family behind seed-`19` active-booking info interruption divergence.
- `First deterministic check command`: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`
- `Blocked-by conditions`: seed-`19` turns are reclassified as pure proof drift or pack/data absence; runtime owner path cannot be bounded.
- `Owner role for closure`: `Brain | Top Architect`
