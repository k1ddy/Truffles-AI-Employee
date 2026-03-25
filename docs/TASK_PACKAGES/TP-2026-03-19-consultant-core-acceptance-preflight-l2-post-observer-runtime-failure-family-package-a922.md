# TP-2026-03-19-consultant-core-acceptance-preflight-l2-post-observer-runtime-failure-family-package-a922

## Goal
Stop the post-observer unblock loop and delete or truthfully localize the surviving runtime blocker family from `/tmp/booking_quality/l2-acceptance-preflight-a922-r14` so the next implementation block can work as one bounded A -> B -> C reconciliation bundle instead of another narrow preflight detour.

## Canon refs
- `STATE.md` NOW: consultant core `acceptance_preflight_l2_expectation_conflict_failure_family` implementation GAP
- `docs/REPORTS/artifacts/2026-03-19-consultant-core-acceptance-preflight-l2-expectation-conflict-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-l2-expectation-conflict-failure-family-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `ops/diagnose.py`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/app/routers/webhook/response.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_expected_reply_contract.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the implementation block either deletes a live post-observer runtime seam and materializes one truthful semantically valid non-acceptance `L2` summary, or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `python keyword-only arguments official docs`
- **Date/time (local):** `2026-03-19T09:35:05+05:00`
- **Sources opened (from this query):**
  - `https://docs.python.org/3/reference/compound_stmts.html#function-definitions`
  - `https://docs.python.org/3/glossary.html#term-parameter`
- **Source quality:**
  - high-signal / primary source: official Python documentation
- **Found ready-made solutions:**
  - parameters after `*` are keyword-only and old callers must pass them explicitly by keyword
  - Python does not provide an implicit compatibility bridge for new required keyword-only parameters
- **Decision:** `integrate`
  - keep the owner service signature truthful and update non-frozen caller surfaces explicitly instead of adding a new compatibility wrapper/helper around `_reuse_active_handover(...)`
- **Rejected options:**
  - widening the owner signature with another silent compatibility path: rejected because that would preserve the mixed caller seam instead of deleting it
  - adding a second helper layer around the owner service: rejected because the current blocker is adapter drift, not missing abstraction

## Root cause (mandatory)
- **Symptom:** `/tmp/booking_quality/l2-acceptance-preflight-a922-r14` is the first completed post-observer rerun with `infra_valid=true` and `run_integrity_valid=true`, but it still ends `semantic_valid=false`, so acceptance preflight still cannot reach `go_to_full`.
- **Minimal reproduction:**
  - keep the worktree runtime on `http://127.0.0.1:18184`
  - inspect `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/{summary.json,brief.md,manual_audit.md,responses.jsonl,trace_bundle.jsonl}`
  - inspect the current non-frozen owner surfaces with:
    - `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/response.py`
    - `rg -n "branch_missing|Не могу определить филиал" truffles-api/app/services/tool_registry_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_expected_reply_contract.py`
- **Evidence:**
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/summary.json` proves the remaining blocker is runtime-semantic, not transport or observer noise: `blocking_reasons={'expected_action_mismatch': 6, 'judge_fail': 15, 'handoff_miss': 10, 'booking_flow_break': 9, 'fact_without_evidence': 1, 'irrelevant_fact': 1}`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/manual_audit.md` proves the run is complete (`dialogs_seen=[1..10]`, `responses_rows=146`, `trace_rows=146`) and the oracle winner is contract, not judge (`judge_alignment=conflicted`, `winner=contract`, `conflict_count=39`)
  - representative family A rows `LLM-QUAL-l2-acceptance-preflight-a922-r14-003-11-e2d344`, `LLM-QUAL-l2-acceptance-preflight-a922-r14-004-11-7df508`, and `LLM-QUAL-l2-acceptance-preflight-a922-r14-010-11-8405e2` prove a live runtime exception path: `_reuse_active_handover() missing 1 required keyword-only argument: 'hooks'`
  - `truffles-api/app/services/handover_owner_service.py:1092` defines `_reuse_active_handover(..., *, hooks: ...)`, while non-frozen callers without `hooks` still remain in `truffles-api/app/routers/webhook/info.py:1762`, `truffles-api/app/routers/webhook/policy.py:822`, `truffles-api/app/routers/webhook/guards.py:268`, and `truffles-api/app/routers/webhook/response.py:1892`
  - representative family B rows `LLM-QUAL-l2-acceptance-preflight-a922-r14-004-04-cd55f8`, `LLM-QUAL-l2-acceptance-preflight-a922-r14-004-05-fdb8e1`, `LLM-QUAL-l2-acceptance-preflight-a922-r14-005-13-4b44aa`, and `LLM-QUAL-l2-acceptance-preflight-a922-r14-009-13-e09c34` prove `tool_registry` still emits a user-facing `branch_missing` fact reply while the booking flow expects escalation / follow-up continuity
  - `truffles-api/app/services/tool_registry_service.py:1410` and `truffles-api/app/services/tool_registry_service.py:2263` still author raw `branch_missing` product replies, while nearby contract tests already encode handoff-first behavior for blocked booking/reschedule contours in `truffles-api/tests/test_message_endpoint.py:17803` and `truffles-api/tests/test_expected_reply_contract.py:175`
  - representative family C row `LLM-QUAL-l2-acceptance-preflight-a922-r14-009-14-c51867` proves active-booking continuity is losing to consult semantics: `signal_snapshot.booking.active=true`, `expected_reply_type=service_choice`, and `session_memory_update.last_question_type=service_choice`, but `llm_policy_core.intent=greeting` and the runtime emits a `consult_reply`
- **Five Whys:**
  1. Why is acceptance preflight still blocked after the observer seam died? Because the fresh completed `L2` rerun is still semantically red.
  2. Why is the rerun still semantically red? Because the remaining bad turns are now runtime-owned `handoff_miss`, `booking_flow_break`, `expected_action_mismatch`, and `judge_fail` clusters rather than observer mismatches.
  3. Why are these clusters still live? Because three mixed runtime seams still survive across non-frozen callers: a handover adapter drift, a tool-layer branch decision seam, and a continuity-precedence seam.
  4. Why did the new architecture not already absorb them? Because these contours still cross legacy ingress/runtime adapters where old callers or tool-layer decisions bypass the intended owner contract.
  5. Why is one A -> B -> C package the next truthful move? Because another micro-unblock or rerun would only churn evidence; the remaining work is already localized to three live runtime families that must be deleted or truthfully narrowed together.
- **Root cause statement:** the surviving blocker is no longer observer/proof noise; it is a mixed post-observer runtime family from `r14` consisting of (A) `_reuse_active_handover` caller drift after the owner signature tightened, (B) `branch_missing` product decision ownership still living in `tool_registry_service.py`, and (C) active-booking continuity not dominating consult/greeting fallback when `expected_reply_type` / booking signals are already live.
- **Fix mechanism:**
  - A: update the non-frozen `_reuse_active_handover(...)` callers to the truthful owner contract and add regression coverage so the runtime exception path disappears without a new wrapper/helper
  - B: move `branch_missing` outcome ownership out of raw tool-layer user replies into one explicit runtime contract path and add contract coverage for that exact booking contour
  - C: enforce active-booking continuity precedence in the runtime owner path so live booking/question-contract state cannot degrade into consult/greeting fallback
  - after A -> B -> C, run exactly one fresh non-acceptance `L2` rerun and audit it strictly

## Invariant
- do not reopen transport, billing, observer, or old architecture-partial blocks as the main story for this package
- do not touch frozen `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- do not create a new wrapper/helper layer just to preserve the current mixed runtime seams
- do not weaken judge/oracle gates, semantic thresholds, `go_to_full`, or acceptance thresholds
- do not treat `CHATFLOW_BILLING_BLOCKED` as the fix; it is already acceptable in this unpaid dev lane
- do not run guarded acceptance `lock/replay/canary/full`, `llm-quality-matrix`, or `llm-quality-open-world-closure` in this package

## Scope
- publish one bounded reconciliation package for the surviving post-observer runtime family from `r14`
- lock the next implementation block to three families only:
  - A. `handover_reuse_adapter_drift`
  - B. `branch_missing_contract_ownership`
  - C. `active_booking_continuity_precedence`
- require that each family either deletes a live runtime seam or stops with a truthful narrower `GAP`
- allow one fresh non-acceptance `L2` rerun only after A -> B -> C implementation plus focused regression coverage

## Out of scope
- further observer/oracle refinement as the primary path
- provider billing or transport remediation as the primary path
- fresh guarded acceptance evidence
- beauty-only proof claims
- frozen-file waivers
- generic ingress bridge growth
- narrative progress without runtime seam deletion

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-post-observer-runtime-failure-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- next implementation block only:
  - `truffles-api/app/services/handover_owner_service.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/policy.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_expected_reply_contract.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/{summary.json,brief.md,manual_audit.md,responses.jsonl,trace_bundle.jsonl}`
  - existing owner surfaces in `handover_owner_service.py`, `tool_registry_service.py`, `turn_planner.py`, `dialog_state_service.py`, `state_service.py`, and `reasoning_core.py`
  - existing contract suites in `test_message_endpoint.py`, `test_expected_reply_contract.py`, `test_reasoning_core.py`, `test_dialog_state_service.py`, and `test_booking_quality_status_gate.py`
- **External reuse:**
  - official Python documentation for keyword-only argument contracts
- **Why this reuse mix is truthful:**
  - the blocker is already localized to concrete completed-run runtime rows, so the truthful path is to reuse the existing owner surfaces and tighten callers/contracts rather than inventing a new replay harness or another compatibility layer

## Plan
1. Publish and register this post-observer runtime family package, then switch canon to it.
2. Freeze the representative `r14` rows and lock the next implementation order to A -> B -> C.
3. Family A: delete `_reuse_active_handover` caller drift from non-frozen router surfaces and cover the fixed contract with focused regressions.
4. Family B: delete raw `branch_missing` product-decision ownership from the tool layer and converge that contour on one runtime contract with focused regressions.
5. Family C: delete the active-booking continuity precedence drift so live booking/question-contract state wins over consult/greeting fallback, with focused regressions.
6. Run exactly one fresh non-acceptance `L2` rerun and strict audit.
7. Publish one bounded implementation report that either proves a truthful semantically valid `L2` summary or stops with exact narrower residual families.

## DoD
- canon points to this package as the active block
- the next move is fixed to `implement_acceptance_preflight_l2_post_observer_runtime_failure_family_closure_bundle`
- the next implementation block is explicitly ordered A -> B -> C and names the rightful owner surfaces for each family
- this package makes clear that observer, transport, and billing are no longer the active blockers
- required doc/architecture/session guards pass

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r14/summary.json').read_text())
print(summary['quality_status']['infra_valid'])
print(summary['quality_status']['semantic_valid'])
print(summary['quality_status']['run_integrity_valid'])
print(summary['quality_status']['blocking_reasons'])
PY`
- `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r14/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
for mid in [
    'LLM-QUAL-l2-acceptance-preflight-a922-r14-003-11-e2d344',
    'LLM-QUAL-l2-acceptance-preflight-a922-r14-004-04-cd55f8',
    'LLM-QUAL-l2-acceptance-preflight-a922-r14-009-14-c51867',
]:
    obj = rows[mid]
    print(mid, obj['decision_meta']['action'], obj['decision_meta']['intent'])
PY`
- `rg -n "_reuse_active_handover\(" truffles-api/app/services/handover_owner_service.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/response.py`
- `rg -n "branch_missing|Не могу определить филиал" truffles-api/app/services/tool_registry_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_expected_reply_contract.py`
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
- updated package and canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `STATE.md`, `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- representative completed-run runtime evidence reused from:
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/summary.json`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/brief.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/manual_audit.md`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/responses.jsonl`
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/trace_bundle.jsonl`
- one bounded implementation report for the next block
- one fresh non-acceptance `L2` summary only if the implementation block reaches semantic green

## Token / run budget (mandatory for expensive suites)
- **Max fresh non-acceptance `L2` runs:** `1`
- **Max full runs:** `0`
- **Max guarded acceptance runs:** `0`
- **Cheap deterministic gates first:** representative-row extraction, caller/contract grep, focused regressions, runtime parity verification
- **Reuse policy:** reuse `r14` evidence; do not regenerate acceptance artifacts in this package
- **Stop condition:** if green requires frozen-file edits, gate weakening, or another wrapper/helper compatibility seam, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded dev-lane reconciliation only; regressions before one rerun
- **Go/no-go signals:**
  - Family A deletes the live handover caller drift without adding a new compatibility layer
  - Family B deletes or bypasses the live branch-missing tool-layer decision seam
  - Family C proves booking/question-contract continuity wins over consult/greeting fallback on the representative contour
  - one fresh non-acceptance `L2` summary has `infra_valid=true`, `semantic_valid=true`, and `run_integrity_valid=true`
- **Rollback:**
  - revert the implementation block changes
  - keep `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/*` untouched as blocker evidence
  - do not resume acceptance preflight until rollback state is revalidated
- **Rollback verification:**
  - rerun the focused regression subsets for A, B, and C
  - rerun `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r14 --status done --strict-artifacts`
- **Post-release monitoring window:** only until the bounded post-observer runtime report is published; if the fresh `L2` rerun remains semantic-red, reopen as `GAP`

## Rollback
- Revert the docs/canon/code files touched by this block and rerun the required guards; keep `/tmp/booking_quality/l2-acceptance-preflight-a922-r14/*` untouched as blocker evidence.

## No-go
- new wrapper/helper growth counted as progress
- another observer-only patch before A -> B -> C runtime analysis is exhausted
- another `L2` rerun without new runtime evidence or focused regressions
- billing/provider detour as the primary path
- silent contract weakening in scenario expectations, judge rules, or status gates

## Risks / blockers
- Family B may expose that the truthful branch-missing outcome is still partially frozen behind legacy `/webhook` behavior; if the only green path needs frozen files, stop and publish `GAP`
- Family C may expose that booking continuity precedence is still split between planner and legacy ingress projection; if the next slice cannot delete a live seam, stop and publish `GAP`
- the representative rows may collapse into a smaller family after A or B; that is admissible only if the deleted seam is explicit in the implementation report

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- program-level `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial in `docs/SOURCE_OF_TRUTH.yaml`
- frozen `/webhook` ingress still survives as the broader transport into legacy runtime
- final multi-pack acceptance closure is still not reached

### Why not in this block
- this package is limited to the surviving post-observer runtime family from completed `r14`
- reopening all partial architecture tracks here would turn the current blocker back into an unbounded demolition wave instead of a truthful acceptance unblock

### Risk if deferred
- if A -> B -> C does not delete a live runtime seam, the program will keep churning preflight evidence without closing the actual architecture requirements

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- next implementation block from this package
- return path to `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`

### Expiry/trigger to stop deferral
- stop deferral immediately if the next implementation block tries to solve the remaining runtime family through bridge growth, gate weakening, or frozen-file edits

## Next-block contract (mandatory)
### Next block objective
- implement one bounded A -> B -> C runtime reconciliation bundle that deletes or truthfully localizes the remaining post-observer runtime seams from `r14`, then run one strict non-acceptance `L2` rerun

### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
rows = {}
for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r14/responses.jsonl').read_text().splitlines():
    obj = json.loads(line)
    rows[obj['message_id']] = obj
checks = {
    'A_error': rows['LLM-QUAL-l2-acceptance-preflight-a922-r14-003-11-e2d344']['decision_meta']['error'],
    'B_tool_decision': rows['LLM-QUAL-l2-acceptance-preflight-a922-r14-004-04-cd55f8']['decision_meta']['tool_decision'],
    'C_expected_reply_type': rows['LLM-QUAL-l2-acceptance-preflight-a922-r14-009-14-c51867']['decision_meta']['expected_reply_type'],
    'C_llm_intent': rows['LLM-QUAL-l2-acceptance-preflight-a922-r14-009-14-c51867']['decision_meta']['llm_policy_core']['intent'],
}
print(checks)
PY`

### Blocked-by conditions
- any supposedly green path that requires edits in frozen `decision.py`, `booking.py`, or `pending.py`
- any path that resolves Family A by adding a new wrapper/helper compatibility seam instead of deleting caller drift
- any path that resolves Family B or C only by weakening expectations/judge rules without deleting a live runtime seam
- any rerun-only path without new regression coverage and runtime owner closure

### Owner role for closure
- `Top Architect / Brain / Hands`

## Execution result
- Family A executable non-frozen caller drift is now narrowed: `truffles-api/app/routers/webhook/info.py:1763`, `truffles-api/app/routers/webhook/policy.py:823`, `truffles-api/app/routers/webhook/guards.py:269`, `truffles-api/app/routers/webhook/response.py:1893`, and `truffles-api/app/routers/webhook/response.py:2204` now pass the truthful `hooks=` contract into `_reuse_active_handover(...)`, and focused regressions passed in `truffles-api/tests/test_message_endpoint.py` (`4 passed, 438 deselected`).
- Family B non-frozen raw product-decision ownership is now bypassed on the booking-completion owner path: `truffles-api/app/services/expected_reply_contract.py` marks `calendar.book_slot + branch_missing` as handoff-required, `truffles-api/app/services/reasoning_core.py` materializes the owner handoff path instead of returning the raw tool reply, and focused regressions passed in `truffles-api/tests/test_expected_reply_contract.py` (`1 passed, 23 deselected`) plus `truffles-api/tests/test_reasoning_core.py` (`1 passed` in the targeted subset).
- Family C non-frozen continuity precedence is now enforced on the booking-prompt owner path: `truffles-api/app/services/reasoning_core.py` short-circuits active booking plus live expected-reply contours before consult/greeting fallback, and the focused regression passed in `truffles-api/tests/test_reasoning_core.py` (`1 passed` in the targeted subset).
- Invalid non-acceptance probes `r15` and `r16` were closed by strict audit only; they are not closure evidence. `r15` stopped because the acceptance chain controller was still implied without an explicit dev lane. `r16` stopped as another `invalid_preflight` stub and was also closed by strict audit.
- The one admissible fresh rerun is `/tmp/booking_quality/l2-acceptance-preflight-a922-r17` on runtime fingerprint parity `HEAD=0d8d2078697193832a2d6cae6709a2d7489bf9ca == http://127.0.0.1:18184/admin/version.git_commit`. Strict audit completed with `artifact_integrity.valid=true`, `infra_valid=true`, `semantic_valid=false`, `stop_reason=max_failures_reached:1`, `responses_rows=18`, `trace_rows=18`, `dialogs_seen=[1, 2]`, `judge_alignment=conflicted`, and `winner=contract`.
- Fresh `r17` proves the surviving live blocker is now narrower and frozen: `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-05-21d51a` (`turn_text="Хотелось бы перенести на следующий понедельник."`) still degrades with `_reuse_active_handover() missing 1 required keyword-only argument: 'hooks'`. The surviving stale callers are in frozen `truffles-api/app/routers/webhook/booking.py:1702`, `truffles-api/app/routers/webhook/booking.py:2358`, `truffles-api/app/routers/webhook/booking.py:2914`, `truffles-api/app/routers/webhook/booking.py:3007`, and `truffles-api/app/routers/webhook/booking.py:3741`.
- The following turn `LLM-QUAL-l2-acceptance-preflight-a922-r17-002-06-db71cd` then surfaces only the narrower expectation residue (`expected_meta_mismatch` + `expected_trace_miss`, both at `stage=llm_policy_plan_delta`) because the preceding frozen runtime exception already reset the live booking contour.
- Block verdict: admissible progress, but `GAP`. The old non-frozen A/B/C seams died, yet the truthful green path now requires frozen `booking.py` edits. The next admissible move is `author_acceptance_preflight_l2_frozen_booking_handover_reuse_family_package_tp_from_r17_gap`.
