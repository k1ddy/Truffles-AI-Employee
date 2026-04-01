# TP-2026-03-18-consultant-core-acceptance-preflight-l2-expectation-conflict-failure-family-package-a922

## Goal
Delete or truthfully localize the surviving completed-run expectation / judge conflict family from `/tmp/booking_quality/l2-acceptance-preflight-a922-r11` so one fresh non-acceptance `demo_salon` `L2` summary can satisfy the remaining `go_to_full` evidence contract without reopening transport, billing, or old architecture packages.

## Canon refs
- `STATE.md` NOW: consultant core `acceptance_preflight_l2_transport_blocker` implementation GAP
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/diagnose.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the implementation block either materializes one truthful semantically valid non-acceptance `L2` summary or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `pytest parametrize ids official docs`
- **Date/time (local):** `2026-03-18T23:37:31+05:00`
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/example/parametrize.html`
  - `https://docs.pytest.org/en/stable/how-to/parametrize.html`
- **Source quality:**
  - high-signal / primary source: official `pytest` documentation
- **Found ready-made solutions:**
  - `pytest` already supports stable per-row IDs through `ids=...` and `pytest.param(..., id=...)`
  - parametrized focused rows can isolate representative failure-family turns without inventing a separate harness
  - `pytest_generate_tests` exists if the implementation needs bounded dynamic row generation from the frozen `r11` evidence
- **Decision:** `reuse`
  - reuse the existing owner suites with explicit parametrized representative rows for `r11` failure families instead of building a new replay or expectation harness
- **Rejected options:**
  - broad suite reruns without representative row isolation: rejected because the surfaced blocker is already localized to a small completed-run family set
  - bespoke row-runner tooling: rejected because `pytest` already provides stable focused parametrization primitives

## Root cause (mandatory)
- **Symptom:** the corrected dev `L2` rerun `/tmp/booking_quality/l2-acceptance-preflight-a922-r11` is complete and transport-valid, but `go_to_full` still cannot close because no semantically valid fresh non-acceptance `L2` summary exists.
- **Minimal reproduction:**
  - keep the worktree runtime on `http://127.0.0.1:18184`
  - run `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18184 --client-slug demo_salon --count 10 --seed 42 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r11 --run-id l2-acceptance-preflight-a922-r11 --history-max 20 --fail-on-thresholds --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate block --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --allow-non-canonical-lock-retry --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
  - audit with `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r11 --status done --strict-artifacts`
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-a922.md` proves the transport blocker family is already closed: the old synthetic unique-JID seam is dead, `CHATFLOW_BILLING_BLOCKED` is acceptable in this test lane, and `r11` finished with `infra_valid=true` plus `run_integrity_valid=true`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/summary.json` proves the surviving blocker is semantic: `semantic_valid=false`, `semantic_reasons=["blocking_reason","threshold_breach"]`, top reasons `expected_trace_miss=59`, `expected_meta_mismatch=52`, `judge_fail=21`, and failure families centered on `stage=session_memory`, `state=bot_active`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/manual_audit.md` proves the run is complete but conflicted: `dialogs_seen=[1..10]`, `responses_rows=144`, `trace_rows=144`, `judge_alignment=conflicted`, `winner=contract`, `conflict_count=52`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/responses.jsonl` and `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/trace_bundle.jsonl` prove this is a completed runtime path rather than another transport or artifact-integrity stop
  - `ops/diagnose.py` proves the remaining failure-family accounting lives in the expectation / judge / contract observer lane, while runtime owner surfaces for the dominant stages now sit behind `DialogStateService`, `state_service`, `turn_planner`, and `reasoning_core`
- **Five Whys:**
  1. Why is `go_to_full` still blocked after transport closure? Because no fresh semantically valid non-acceptance `L2` summary exists.
  2. Why is the fresh `L2` summary still invalid? Because `r11` breaches semantic thresholds on completed turns through `expected_trace_miss`, `expected_meta_mismatch`, `judge_fail`, `handoff_miss`, and `booking_flow_break`.
  3. Why is this no longer a transport or billing story? Because `r11` is complete, `infra_valid=true`, `run_integrity_valid=true`, and delivery acceptance still passes under the unpaid-provider contour.
  4. Why does the family stay unresolved? Because the completed-run evidence now mixes three possible owners: runtime contract drift on the surfaced stages, stale scenario expectation / contract drift, or diagnose/judge observer drift.
  5. Why is this the next truthful package? Because acceptance preflight can only resume by deleting or localizing this completed-run expectation / judge family; reopening billing, transport, or old architecture partials would not move the current blocker.
- **Root cause statement:** the surviving blocker family is a completed-run expectation / judge contract divergence on `r11`, concentrated in `session_memory` / `bot_active` rows with smaller `llm_policy_plan_delta`, `question_contract`, and bounded fact-owner slices; transport, delivery, and run integrity are already green, but the current scenario / oracle contract does not align with canonical runtime evidence on those turns.
- **Fix mechanism:**
  - freeze the current completed-run evidence from `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/*`
  - isolate representative failure-family rows with stable IDs and determine whether each row is owned by runtime contract drift, scenario-contract drift, or observer/judge drift
  - fix only the rightful non-frozen owner surfaces, with an explicit stop if the only green path requires frozen files, scenario/oracle weakening, or stale-evidence waiver
  - materialize one fresh non-acceptance `L2` summary with `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`

## Invariant
- do not reopen transport, billing, hardcode-core, or old architecture partials as the main story for this block
- do not weaken scenario expectations, judge gates, semantic thresholds, `go_to_full`, or acceptance thresholds
- do not treat the billing waiver as the fix; it is already an accepted external contour in this test lane
- do not touch frozen `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`; if the only truthful green path requires that, stop and publish `GAP`
- do not fake trace/meta evidence, judge outcomes, or manual audits
- do not rerun guarded acceptance `lock/replay/canary/full` in this package

## Scope
- publish one package-level implementation plan for the surfaced completed-run expectation / judge conflict family
- lock the next implementation block to the surviving non-frozen owner surfaces around:
  - scenario expectation / family accounting in `ops/diagnose.py`
  - scenario-contract normalization in `truffles-api/app/services/llm_quality_contracts.py` and `scripts/booking_dialog_scenarios.py` only if the evidence proves stale expectation generation
  - runtime owner surfaces for the dominant stages in `truffles-api/app/core/dialog_state_service.py`, `truffles-api/app/services/state_service.py`, `truffles-api/app/core/turn_planner.py`, and `truffles-api/app/services/reasoning_core.py`
- allow one fresh non-acceptance `L2` run only after deterministic evidence extraction and focused regression coverage

## Out of scope
- transport / billing remediation as a primary goal
- guarded acceptance `lock`, `replay`, `canary`, `full`
- `llm-quality-matrix` or `llm-quality-open-world-closure`
- reopening hardcode-core or unique-JID transport closure work
- broad runtime safety redesign
- frozen-file waivers
- gate weakening, stale-evidence reuse, or judge prompt dilution

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-l2-expectation-conflict-failure-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `ops/diagnose.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-a922.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/summary.json`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/brief.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/manual_audit.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/responses.jsonl`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/trace_bundle.jsonl`
  - existing expectation / contract owner surfaces in `ops/diagnose.py`, `truffles-api/app/services/llm_quality_contracts.py`, `truffles-api/app/core/dialog_state_service.py`, `truffles-api/app/services/state_service.py`, `truffles-api/app/core/turn_planner.py`, and `truffles-api/app/services/reasoning_core.py`
  - existing focused suites in `truffles-api/tests/test_booking_quality_status_gate.py`, `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`, `truffles-api/tests/test_booking_quality_response_guard.py`, `truffles-api/tests/test_dialog_state_service.py`, `truffles-api/tests/test_reasoning_core.py`, and `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official pytest parametrization guidance from `docs.pytest.org`
- **Why this reuse mix is truthful:**
  - the blocker is already localized to completed-run expectation families, so the truthful path is to reuse the existing observer/runtime owner surfaces and add stable representative rows instead of inventing a new replay system

## Plan
1. Publish and register this expectation-conflict package, then switch canon to it.
2. Freeze the completed-run blocker evidence from `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/{summary.json,brief.md,manual_audit.md,responses.jsonl,trace_bundle.jsonl}` and extract representative family IDs / turns.
3. Determine whether each representative row is owned by runtime contract drift, scenario-contract drift, observer/judge drift, or a mixed family; stop if the only truthful green path requires frozen files or gate weakening.
4. Add or tighten the smallest regression rows with stable IDs for the representative families.
5. Implement the smallest non-frozen owner closure for the surfaced family.
6. Materialize one fresh non-acceptance `L2` run on worktree runtime parity and audit it strictly.
7. Publish one bounded implementation report that either proves one truthful green `L2` summary or stops with exact narrower `reasons` / `failure_families`.

## DoD
- this TP locks one truthful implementation path for the surfaced completed-run expectation / judge conflict family
- the next implementation block is bounded to non-frozen runtime / scenario / observer owner surfaces only
- the TP names the exact blocker evidence, representative family slices, rightful owner options, and one-run proof contract
- canon/session docs point at this package and the next move to implement it
- required architecture/session guards pass

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r11/summary.json').read_text())
print(summary['quality_status']['infra_valid'])
print(summary['quality_status']['semantic_valid'])
print(summary['quality_status']['run_integrity_valid'])
print(summary['failure_counts']['expected_trace_miss'])
print(summary['failure_counts']['expected_meta_mismatch'])
print(summary['failure_counts']['judge_fail'])
PY`
- `python3 - <<'PY'
from pathlib import Path
text = Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r11/manual_audit.md').read_text()
for needle in ['judge_alignment: `conflicted`', 'winner: `contract`', 'conflict_count: `52`', 'dialogs_seen: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`']:
    print(needle, needle in text)
PY`
- `rg -n "expected_trace_miss|expected_meta_mismatch|judge_fail|judge_eval_conflict|session_memory|llm_policy_plan_delta|question_contract" ops/diagnose.py truffles-api/app/services/llm_quality_contracts.py scripts/booking_dialog_scenarios.py truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/app/core/turn_planner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_response_guard.py`
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
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- blocker evidence reused from:
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-a922.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/summary.json`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/brief.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/manual_audit.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/responses.jsonl`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/trace_bundle.jsonl`
- one bounded implementation report for the next block
- one fresh non-acceptance `L2` summary if the implementation block reaches semantic green
- `STATE.md` entry naming either the deleted expectation-conflict seam or the exact narrower `GAP`

## Token / run budget (mandatory for expensive suites)
- **Max fresh non-acceptance `L2` runs:** `1`
- **Max full runs:** `0`
- **Max guarded acceptance runs:** `0`
- **Cheap deterministic gates first:** summary/manual-audit extraction, owner-surface grep, focused regressions, runtime parity verification before any new `L2` run
- **Reuse policy:** reuse the completed `r11` artifacts; do not regenerate acceptance evidence in this package
- **Stop condition:** if green `L2` requires frozen-file edits, scenario/judge gate weakening, or stale-scenario waiver, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded dev-lane unblock only; cheap gates and focused regressions before one fresh `L2` run
- **Go/no-go signals:**
  - one non-frozen owner surface is proven for the representative expectation / judge family rows
  - focused regressions are green
  - one fresh non-acceptance `L2` summary has `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`
  - no new blocker family appears that would force another architectural detour inside this block
- **Rollback:**
  - revert this block's code/doc changes
  - keep `/tmp/booking_quality/l2-acceptance-preflight-a922-r11/*` untouched as blocker evidence
  - do not resume acceptance preflight until the rollbacked state is revalidated
- **Rollback verification:**
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** only until the bounded `L2` expectation-conflict report is published; if the fresh `L2` run remains semantic-invalid, reopen as `GAP`

## Rollback
- Revert the docs/canon/code files touched by this block and rerun the required guards; do not remove or rewrite blocker evidence.

## No-go
- Do not reopen transport or billing remediation as the main work for this package.
- Do not rerun guarded acceptance `lock/replay/canary/full` in this package.
- Do not claim `go_to_full` closure from this package alone.
- Do not weaken expectation, judge, or semantic gates.
- Do not fake trace/meta evidence, judge outputs, or audit artifacts.
- Do not touch frozen `decision.py`, `booking.py`, or `pending.py` in this package.

## Risks / blockers
- the representative families may prove mixed, requiring a truthful stop and a narrower follow-up package instead of one direct runtime fix
- the only green path may terminate at stale scenario-oracle contract assumptions rather than runtime owners
- the fresh `L2` rerun may expose one smaller surviving runtime family after the dominant expectation/judge cluster is deleted

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- acceptance preflight overall remains incomplete until `go_to_full` is rebuilt from fresh `L1 + L2`
- final multi-pack acceptance re-entry remains open
- broader semantic / continuity / boundary residuals remain outside this package

### Why not in this block
- this block only isolates the surviving completed-run expectation / judge conflict family
- guarded acceptance reruns still belong to the acceptance-preflight and multi-pack re-entry lanes

### Risk if deferred
- the program remains blocked even though transport and run integrity are already green
- teams can drift into repeated complete-but-semantic-red `L2` reruns instead of deleting the real blocker family
- `go_to_full` stays structurally incomplete even after truthful transport closure

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`

### Expiry/trigger to stop deferral
- stop deferral as soon as a fresh `L2` rerun still fails after the representative families are localized; that outcome must become either a truthful narrower `GAP` report or the next bounded follow-up TP

## Next-block contract (mandatory)
### Next block objective
- implement one bounded closure bundle for the completed-run expectation / judge conflict family so acceptance preflight can earn one semantically valid non-acceptance `L2` summary

### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r11/summary.json').read_text())
print(summary['quality_status']['infra_valid'], summary['quality_status']['semantic_valid'], summary['quality_status']['run_integrity_valid'])
for family in summary['failure_families']['top_families'][:5]:
    print(family['family_id'], family['count'])
PY`

### Blocked-by conditions
- the only truthful green path requires frozen-file edits
- the only truthful green path requires expectation / judge gate weakening without equivalent contract evidence
- the only available fix is stale scenario regeneration that does not delete a live old seam or contract drift
- a fresh rerun reopens transport, artifact-integrity, or preflight blocker families instead of staying inside the localized expectation/judge family

### Owner role for closure
- `Top Architect / Brain`
