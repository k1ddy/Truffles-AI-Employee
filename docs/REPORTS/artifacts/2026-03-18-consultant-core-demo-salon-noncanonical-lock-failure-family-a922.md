# 2026-03-18 Consultant Core Demo Salon Non-Canonical Lock Failure Family (a922)

## Verdict Summary
- **FACT:** `implement_demo_salon_noncanonical_lock_failure_family_closure_bundle` deleted the old `demo_salon` lock-admission seam where `scripts/llm_quality_guarded.sh` blocked a fresh `lock` before `ops/diagnose.py` could arbitrate the non-canonical prior lock under the run-economy contract.
- **FACT:** the bounded oracle blocker family was narrowed in `ops/diagnose.py` so booking time-guidance turns with `pending_question_act=ask_about_requested_slot` and booking-progress tags no longer infer stray info tags from text alone.
- **FACT:** targeted regressions now pass for both owner surfaces: wrapper admission, info-tag inference, and runtime booking-guidance behavior.
- **FACT:** one fresh guarded `demo_salon` lock attempt with run id `booking-lock-a922-unblock` no longer stopped on `previous run not canonical`; it reached chain-controller prepare and then fail-closed on `go_to_full_l1_evidence_missing`.
- **FACT:** no fresh canonical lock artifact was produced: `/tmp/booking_quality/booking-lock-a922-unblock/summary.json` does not exist.
- **FACT:** cheap static acceptance preflight on the current worktree is also red: `python3 ops/diagnose.py llm-quality-gates ...` returns `hardcode_core_gate:core_phrase_branching_detected` with current diff violations in frozen `truffles-api/app/routers/webhook/decision.py` and live `truffles-api/app/services/info_signal_service.py`.
- **INFERENCE:** the original blocker family is truthfully narrowed, but the block still ends as `GAP` because a fresh acceptance lock cannot start canonically without truthful `go_to_full` evidence and without clearing the surfaced hardcode-core preflight gate.

## What Changed
- **FACT:** `scripts/llm_quality_guarded.sh` now lets a fresh `lock` continue when the latest prior `lock` is non-canonical but already has `manual_audit=done` and valid artifacts, so `ops/diagnose.py` remains the admission owner for the retry contract.
- **FACT:** `ops/diagnose.py` now suppresses text-only info-tag inference for booking time-guidance turns when the active pending-question contract already proves a booking resume path.
- **FACT:** regression coverage added/updated:
  - `truffles-api/tests/test_booking_quality_guarded_wrapper.py`
  - `truffles-api/tests/test_booking_quality_info_sections.py`
  - existing runtime behavior confirmed through `truffles-api/tests/test_message_endpoint.py`
- **FACT:** `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` now documents the lock-only exception where audited non-canonical prior locks defer to `ops/diagnose.py` run-economy arbitration.

## Targeted Validation
- **FACT:** `pytest -q truffles-api/tests/test_booking_quality_info_sections.py truffles-api/tests/test_booking_quality_guarded_wrapper.py truffles-api/tests/test_booking_quality_status_gate.py -k 'non_canonical_lock_retry or pending_question or info_tag_infer or guarded_wrapper'` => `16 passed, 104 deselected`.
- **FACT:** `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_llm_policy_core_pending_question_act_time_guidance_keeps_resume_contract or test_llm_policy_core_active_time_slot_question_hours_phrase_keeps_booking_guidance'` => `4 passed, 434 deselected`.
- **FACT:** `python3 ops/diagnose.py llm-quality-gates --run-economy-gate block --quality-constant-gate block --quality-lane acceptance --mode llm --count 10 --include-media --scenario-coverage booking,info,interrupt,handoff --judge-mode all --fail-on-thresholds --output /tmp/a922-unblock-gates.json` => exit `2` with `hardcode_core_gate:core_phrase_branching_detected`.

## Fresh Lock Attempt
- **FACT:** command run:
  - `BASE_URL=http://127.0.0.1:8000 OPENAI_API_KEY=<from truffles-api container> scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-unblock --pg-checklist /tmp/booking_quality/pg_checklist-a922-unblock.json -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- **FACT:** wrapper output changed from the old blocker to the new admission path:
  - `[guard] latest prior lock is non-canonical but audited/artifact-complete; deferring lock admission to diagnose.py run-economy gate`
- **FACT:** the run stopped before runtime execution with:
  - `ERROR: go_to_full_l1_evidence_missing`
  - `ERROR: chain controller prepare failed`
- **FACT:** this failure is truthful because the current environment does not contain a real acceptance `pg_checklist` bundle with required `l1_evidence`, `l2_evidence`, and `multi_seed_evidence`; synthesizing those fields without real evidence would be fake progress.

## Surviving Preflight Blockers
- **FACT:** `scripts/quality_chain_controller.sh` requires `go_to_full` evidence before an acceptance `lock` can start, and the current `pg_checklist` lane lacks truthful `l1_evidence`, `l2_evidence`, and `multi_seed_evidence`.
- **FACT:** `/tmp/booking_quality/booking-lock-a922-unblock/summary.json` was not produced because chain-controller prepare stopped first.
- **FACT:** `/tmp/a922-unblock-gates.json` records a second blocker in the same worktree state:
  - `hardcode_core_gate.reasons = ["core_phrase_branching_detected"]`
  - violations include `truffles-api/app/routers/webhook/decision.py` and `truffles-api/app/services/info_signal_service.py`
- **INFERENCE:** even after materializing truthful `go_to_full` evidence, the current worktree would still fail acceptance preflight until the surfaced hardcode-core gate is resolved or truthfully waived by a separate admissible package.

## Expected Artifacts Not Produced
- **FACT:** the following fresh-lock artifact is still absent:
  - `/tmp/booking_quality/booking-lock-a922-unblock/summary.json`
  - `/tmp/booking_quality/booking-lock-a922-unblock/brief.md`

## Next Honest Path
1. Stop this block as `GAP`; do not fake `pg_checklist` evidence and do not weaken the acceptance gates.
2. Author one follow-up package for the surfaced acceptance preflight blockers:
   - truthful `go_to_full` evidence materialization contract for the guarded `lock`
   - current-worktree `hardcode_core_gate` blocker family
3. Re-attempt the fresh guarded `demo_salon` lock only after that follow-up package either deletes those blockers or truthfully narrows them again.

## Gap Register
- **GAP:** the old non-canonical lock blocker family is narrowed, but the block cannot prove a fresh canonical `demo_salon` lock because chain-controller prepare fails on missing `go_to_full` evidence.
- **GAP:** the current worktree also fails static acceptance preflight with `hardcode_core_gate:core_phrase_branching_detected`.
- **GAP:** no new canonical lock summary exists for `booking-lock-a922-unblock` in this block.
