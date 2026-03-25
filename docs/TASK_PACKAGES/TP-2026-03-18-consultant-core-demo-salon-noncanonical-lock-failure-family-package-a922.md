# TP-2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-package-a922

## Goal
Delete the surviving `demo_salon` non-canonical guarded-lock blocker family exposed by the multi-pack acceptance re-entry GAP so one fresh canonical `demo_salon` lock can start truthfully, without broad bypasses, before the final multi-pack acceptance bundle is retried.

## Canon refs
- `STATE.md` NOW: consultant core `multi_pack_acceptance_reentry` closure bundle GAP
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/llm_quality_guarded.sh`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_info_sections.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the implementation block either proves one fresh canonical `demo_salon` lock can start without broad bypasses or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `pytest parametrize ids official docs`
- **Date/time (local):** `2026-03-18T20:08:21+05:00`
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/example/parametrize.html`
  - `https://docs.pytest.org/en/stable/how-to/parametrize.html`
- **Source quality:**
  - high-signal / primary source: official `pytest` documentation
- **Found ready-made solutions:**
  - `pytest.mark.parametrize(..., ids=...)` / `pytest.param(..., id=...)` keep regression rows stable and attributable when one blocker family must be reproduced across multiple exact cases
  - stable ids are preferable to ad-hoc duplicated tests when the implementation block must distinguish wrapper-gate cases from turn-classification cases
- **Decision:** `reuse`
  - reuse the existing pytest surfaces and add stable-id rows to the smallest existing test modules that already own guarded-wrapper admission and info-tag / expected-reply classification behavior
- **Rejected options:**
  - a bespoke repro script as the primary regression harness: rejected because the repo already has stable owner tests for the guarded wrapper, status gate, evaluator, and webhook behavior
  - narrative-only RCA without executable regression rows: rejected because the next block must prove which owner still holds the blocker family

## Root cause (mandatory)
- **Symptom:** `implement_multi_pack_acceptance_reentry_closure_bundle` cannot start because the first guarded `demo_salon` lock is blocked by the latest prior non-canonical lock `p1.6o224-l2-dev-20260315-a1-r1`.
- **Minimal reproduction:**
  - `python3 scripts/quality_artifact_report.py --hours 168 --show-commands && python3 - <<'PY'
import json, pathlib
base = pathlib.Path('/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1')
summary = json.loads((base / 'summary.json').read_text())
rows = [json.loads(line) for line in (base / 'responses.jsonl').read_text().splitlines()]
print({
    'run_id': summary.get('run_id'),
    'semantic_valid': summary.get('semantic_valid'),
    'stop_reason': summary.get('stop_reason'),
    'run_integrity_reasons': (summary.get('quality_status') or {}).get('run_integrity_reasons'),
    'top_failure': ((summary.get('top_failures') or [{}])[0]).get('reason'),
    'turn2_expected_reply_matched': rows[1].get('decision_meta', {}).get('expected_reply_matched'),
    'turn2_expected_reply_blocked_by_info': rows[1].get('decision_meta', {}).get('expected_reply_blocked_by_info'),
    'turn2_pending_question_act': rows[1].get('decision_meta', {}).get('pending_question_act'),
})
PY && rg -n "previous run not canonical|allow-pending-previous|allow_non_canonical_lock_retry|lock_fingerprint_unchanged_after_non_canonical|ask_about_requested_slot|info_section_miss" scripts/llm_quality_guarded.sh ops/diagnose.py docs/runbooks/BOOKING_CONFIRM_VERIFY.md truffles-api/tests/test_booking_quality_guarded_wrapper.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_info_sections.py`
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md` proves the evidence-only re-entry bundle stopped before any new guarded run could start
  - `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/summary.json` proves the latest relevant lock is non-canonical: `semantic_valid=false`, `stop_reason=max_failures_reached:1`, `run_integrity_reasons=["run_completion_gap"]`, and top failure family `info_section_miss`
  - `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/responses.jsonl` proves the failing turn is not a pure missing-response case: turn `LLM-QUAL-p1.6o224-l2-dev-20260315-a1-r1-001-02-88fc56` keeps `pending_question_act=ask_about_requested_slot` and `expected_reply_type=time`, but `expected_reply_matched=false` and `expected_reply_blocked_by_info=true`
  - `scripts/llm_quality_guarded.sh` blocks a new lock purely from `latest_by_mode/lock.json` status before the fingerprint-aware non-canonical retry contract in `ops/diagnose.py` can arbitrate whether a fresh lock is admissible after a bounded fix
  - `truffles-api/tests/test_booking_quality_info_sections.py` currently covers pending-question suppression for `slot_constraint`, but there is no dedicated regression row for the `ask_about_requested_slot` + specialist/master wording that surfaced in the blocking run
  - `truffles-api/tests/test_booking_quality_guarded_wrapper.py` currently exercises chain-token injection and controller failure, but it does not cover the current latest-run admission blocker contract
- **Five Whys:**
  1. Why is the acceptance re-entry TP still blocked? Because the first `demo_salon` lock cannot start while the latest relevant prior lock remains non-canonical.
  2. Why is that prior lock non-canonical? Because it combined a turn-level `info_section_miss` / `expected_reply_blocked_by_info` mismatch with `run_completion_gap`, so governance closure stayed invalid.
  3. Why can the team not simply rerun the lock after fixing code? Because `scripts/llm_quality_guarded.sh` fail-closes on the latest run status before a fresh lock can prove that the blocker family was actually removed.
  4. Why is `--allow-pending-previous` not the truthful answer? Because the runbook limits it to stale unrelated blockers, and the surfaced run is the current blocker family rather than historical noise.
  5. Why is this package the truthful next move? Because the remaining residual is no longer multi-pack targeting; it is one bounded `demo_salon` blocker family spanning exact turn classification evidence and guarded-lock admission semantics.
- **Root cause statement:** the current repo truth still carries one live `demo_salon` blocker family where a booking time-followup turn was classified as an info-blocked miss inside the non-canonical prior lock, and the guarded wrapper then treats that non-canonical lock as the latest blocking status before a fresh canonical lock can start under a fingerprint-aware contract.
- **Fix mechanism:**
  - reproduce the exact failing turn and the exact guarded-wrapper admission blocker from the blocking run artifacts
  - add stable regression rows that separate turn-classification ownership from wrapper admission ownership
  - delete the still-live blocker seam in the rightful owner surface(s) only, so a fresh canonical `demo_salon` lock can start without `--allow-pending-previous`, direct index cleanup, or acceptance-gate weakening
  - prove the unblock with one fresh canonical guarded `demo_salon` lock and a bounded report, then return to the original multi-pack acceptance re-entry TP

## Invariant
- no reopening of old architecture package work unrelated to this blocker family
- no runtime/core/proof-owner patching “along the way” unless it is the proven rightful owner of the surfaced blocker family
- no frozen-file edits in `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`; if the blocker can only be fixed there, stop and publish `GAP`
- no direct index cleanup, manual deletion of `/tmp/booking_quality/_index`, or broad `--allow-pending-previous` bypass to fake progress
- no acceptance gate weakening (`judge`, `semantic_valid`, `run_integrity_valid`, thresholds, failure-family gates)
- `demo_salon` remains only the canary/unblock surface in this package; do not rerun multi-pack matrix/closure here

## Scope
- publish one package-level implementation plan for the surfaced `demo_salon_noncanonical_lock_failure_family`
- lock the next implementation block to one bounded unblock lane around:
  - the exact failing turn classification from `p1.6o224-l2-dev-20260315-a1-r1`
  - the guarded-wrapper latest-lock admission contract
- require one fresh canonical `demo_salon` guarded `lock` only after the blocker seam is deleted or bypassed truthfully
- require a bounded report that either proves the unblock or stops with a narrower `GAP`

## Out of scope
- rerunning `replay`, `canary`, `full`, `llm-quality-matrix`, or `llm-quality-open-world-closure` in this package
- reopening runtime target materialization or other old architectural packages
- beauty-only closure claims
- any frozen-file waiver or broad acceptance wrapper redesign
- changing `platform_evidence_requirement` or the final re-entry TP contract

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-a922.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/llm_quality_guarded.sh`
- `ops/diagnose.py`
- `truffles-api/app/services/expected_reply_contract.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_info_sections.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,run_manifest.json}` for the exact blocker reproduction
  - `scripts/llm_quality_guarded.sh` as the canonical guarded-wrapper owner surface
  - `ops/diagnose.py` as the existing run-economy / quality-status / info-tag evaluator owner surface
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` for the existing guarded-run policy contract
  - `truffles-api/tests/test_booking_quality_guarded_wrapper.py` for wrapper admission coverage
  - `truffles-api/tests/test_booking_quality_status_gate.py` for fingerprint-aware non-canonical retry coverage
  - `truffles-api/tests/test_booking_quality_info_sections.py` for info-tag inference suppression coverage
  - `truffles-api/tests/test_message_endpoint.py` for runtime expected-reply / pending-question regression coverage
- **External reuse:**
  - official `pytest` parametrization guidance from the single mandatory query above for stable regression ids
- **Why this reuse mix is truthful:**
  - the repo already contains the blocker artifacts, the guarded wrapper, the run-economy evaluator, and the relevant regression suites
  - reusing those owners keeps the unblock inside one bounded family instead of inventing a new acceptance wrapper or another architecture detour

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. In the implementation block, freeze the exact blocker evidence from `p1.6o224-l2-dev-20260315-a1-r1`, including the failing turn and the wrapper latest-run admission preflight.
3. Add stable regression rows that distinguish:
   - turn-level booking followup classification (`ask_about_requested_slot` + specialist/master wording)
   - guarded-wrapper latest-run admission after a non-canonical lock
4. Determine the rightful surviving owner surface from reproduction evidence:
   - if the failing turn still reproduces on current code, fix the smallest non-frozen runtime/eval owner that still misclassifies it
   - if the turn no longer reproduces, converge guarded-wrapper admission onto the existing fingerprint-aware non-canonical lock contract so a fresh lock can start truthfully after a bounded fix
5. Run one fresh guarded `demo_salon` `lock` with a new unblock run id and no broad bypass flags.
6. Publish one bounded report that either proves the fresh lock is canonical or stops with exact narrower `reasons` / `failure_families`.
7. Return to `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md` only after the unblock report is truthful.

## DoD
- this TP locks one truthful unblock path for the surfaced `demo_salon` non-canonical lock family
- the next implementation block is bounded to the blocker family and does not reopen old architecture packages
- the TP makes the exact blocker evidence, rightful owner surfaces, and lock-only proof requirement explicit
- canon/session docs point at this package and the next move to implement it
- required architecture/session guards pass

## Checks
- `python3 scripts/quality_artifact_report.py --hours 168 --show-commands`
- `python3 - <<'PY'
import json, pathlib
base = pathlib.Path('/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1')
summary = json.loads((base / 'summary.json').read_text())
rows = [json.loads(line) for line in (base / 'responses.jsonl').read_text().splitlines()]
print({
    'run_id': summary.get('run_id'),
    'semantic_valid': summary.get('semantic_valid'),
    'stop_reason': summary.get('stop_reason'),
    'run_integrity_reasons': (summary.get('quality_status') or {}).get('run_integrity_reasons'),
    'top_failure': ((summary.get('top_failures') or [{}])[0]).get('reason'),
    'turn2_expected_reply_matched': rows[1].get('decision_meta', {}).get('expected_reply_matched'),
    'turn2_expected_reply_blocked_by_info': rows[1].get('decision_meta', {}).get('expected_reply_blocked_by_info'),
    'turn2_pending_question_act': rows[1].get('decision_meta', {}).get('pending_question_act'),
})
PY`
- `rg -n "previous run not canonical|allow-pending-previous|allow_non_canonical_lock_retry|lock_fingerprint_unchanged_after_non_canonical|ask_about_requested_slot|info_section_miss" scripts/llm_quality_guarded.sh ops/diagnose.py docs/runbooks/BOOKING_CONFIRM_VERIFY.md truffles-api/tests/test_booking_quality_guarded_wrapper.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_info_sections.py`
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
- one bounded implementation report in `docs/REPORTS/artifacts/2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-a922.md`
- blocker evidence reused from `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,run_manifest.json}`
- targeted regression outputs from the implementation block for the wrapper admission and turn-classification owner surfaces
- one fresh guarded canonical-lock artifact from the implementation block:
  - `/tmp/booking_quality/booking-lock-a922-unblock/summary.json`
  - `/tmp/booking_quality/booking-lock-a922-unblock/brief.md`
- `STATE.md` entry naming either the deleted blocker seam or the exact narrower `GAP`

## Token / run budget (mandatory for expensive suites)
- **Max guarded lock runs:** `1`
- **Max full runs:** `0`
- **Max replay/canary/full runs:** `0`
- **Cheap deterministic gates first:** artifact inventory, exact blocker extraction, and targeted regression tests before any new guarded lock
- **Reuse policy:** reuse the blocking run artifacts; do not regenerate a matrix or closure bundle here
- **Stop condition:** if the blocker can only be fixed via frozen-file edits, broad `--allow-pending-previous`, direct index cleanup, or unrelated architecture work, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded unblock only; one fresh `demo_salon` lock and targeted regression coverage before returning to the original acceptance re-entry package
- **Go/no-go signals:**
  - the exact blocker regression rows pass in the rightful owner surfaces
  - one fresh guarded `demo_salon` lock starts and finishes canonical without broad bypass flags
  - no frozen files are edited
  - no new failure family appears that would force another architecture/package detour inside this block
- **Rollback:**
  - revert this block's code/doc changes
  - leave `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1` untouched as blocker evidence
  - do not resume the acceptance re-entry package until the rollbacked state is revalidated
- **Rollback verification:**
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** only until the unblock report and the fresh canonical `demo_salon` lock are published; if the lock is still non-canonical, reopen as `GAP`

## Rollback
- Revert the docs/canon/code files touched by this block and rerun the required guards; do not remove or rewrite historical blocker artifacts.

## No-go
- Do not rerun the full multi-pack acceptance bundle inside this package.
- Do not use `--allow-pending-previous` to bypass the current blocker family.
- Do not delete or rewrite `/tmp/booking_quality/_index` or the blocking run directory.
- Do not weaken `semantic_valid`, `run_integrity_valid`, threshold, or failure-family gates.
- Do not touch frozen `decision.py`, `booking.py`, or `pending.py` in this package.
- Do not claim final consultant closure or re-entry closure from this block alone.

## Risks / blockers
- the exact turn-level blocker may already be fixed on current code, leaving guarded-wrapper admission as the only surviving seam
- the exact turn-level blocker may still require a frozen-file change, which would force a truthful `GAP`
- the fresh guarded `demo_salon` lock may expose a different blocker family once this one is removed
- the wrapper / run-economy contract may need careful alignment so lock admission becomes truthful without reopening repeat-fingerprint shortcuts

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- full multi-pack acceptance re-entry remains open
- broader semantic/continuity/boundary legacy residuals still exist outside this blocker family
- the final machine-readable closure artifact still does not exist

### Why not in this block
- this block only locks the truthful unblock lane for the `demo_salon` non-canonical lock family
- the final re-entry bundle belongs to the already-authored multi-pack acceptance re-entry TP and must stay separate

### Risk if deferred
- the program remains blocked before any new canonical lock can start
- teams can drift into bypass-based reruns or architecture detours again
- the final acceptance TP remains unexecutable despite truthful runtime targets already existing

### Linked follow-up Task Package(s)
- implementation of this package
- return to `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md` after truthful unblock proof

### Expiry/trigger to stop deferral
- stop deferral immediately if anyone tries to rerun the full acceptance bundle before publishing the unblock report or if the blocker can only be moved into a new mixed hotspot

## Next-block contract (mandatory)
### Next block objective
- implement one bounded `demo_salon` unblock bundle that deletes the surfaced non-canonical lock blocker family or proves a narrower truthful `GAP`, then return to the original multi-pack acceptance re-entry TP

### First deterministic check command
- `python3 scripts/quality_artifact_report.py --hours 168 --show-commands && python3 - <<'PY'
import json, pathlib
base = pathlib.Path('/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1')
summary = json.loads((base / 'summary.json').read_text())
rows = [json.loads(line) for line in (base / 'responses.jsonl').read_text().splitlines()]
print({
    'run_id': summary.get('run_id'),
    'semantic_valid': summary.get('semantic_valid'),
    'stop_reason': summary.get('stop_reason'),
    'run_integrity_reasons': (summary.get('quality_status') or {}).get('run_integrity_reasons'),
    'top_failure': ((summary.get('top_failures') or [{}])[0]).get('reason'),
    'turn2_expected_reply_matched': rows[1].get('decision_meta', {}).get('expected_reply_matched'),
    'turn2_expected_reply_blocked_by_info': rows[1].get('decision_meta', {}).get('expected_reply_blocked_by_info'),
    'turn2_pending_question_act': rows[1].get('decision_meta', {}).get('pending_question_act'),
})
PY && rg -n "previous run not canonical|allow-pending-previous|allow_non_canonical_lock_retry|lock_fingerprint_unchanged_after_non_canonical|ask_about_requested_slot|info_section_miss" scripts/llm_quality_guarded.sh ops/diagnose.py docs/runbooks/BOOKING_CONFIRM_VERIFY.md truffles-api/tests/test_booking_quality_guarded_wrapper.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_info_sections.py`

### Blocked-by conditions
- the only truthful fix requires frozen-file edits
- the only way to start a fresh lock is broad `--allow-pending-previous`, direct index cleanup, or gate weakening
- the exact blocker cannot be reproduced or localized to a rightful owner surface
- the fresh guarded `demo_salon` lock exposes a different blocker family before this one is deleted

### Owner role for closure
- Brain / Top Architect
