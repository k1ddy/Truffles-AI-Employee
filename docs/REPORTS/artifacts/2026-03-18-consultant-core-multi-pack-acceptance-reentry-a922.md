# 2026-03-18 Consultant Core Multi-Pack Acceptance Re-entry (a922)

## Verdict Summary
- **FACT:** `implement_multi_pack_acceptance_reentry_closure_bundle` is blocked before any new guarded `demo_salon` run starts.
- **FACT:** the first locked acceptance command stopped immediately with `ERROR: previous run not canonical (mode=lock run_id=p1.6o224-l2-dev-20260315-a1-r1 status=incomplete). Resolve artifacts/manual audit before new run or pass --allow-pending-previous.`
- **FACT:** the blocking prior lock `p1.6o224-l2-dev-20260315-a1-r1` is strict-audited but remains non-canonical: `infra_valid=true`, `semantic_valid=false`, `stop_reason=max_failures_reached:1`, and `run_integrity_reasons=["run_completion_gap"]`.
- **FACT:** the blocking run surfaced one top failure family: `reason:info_section_miss|type:turn|category:data|stage:contract|state:bot_active`.
- **FACT:** no new `booking-lock-a922-reentry`, `booking-replay-a922-reentry`, `booking-canary-a922-reentry`, `booking-full-a922-reentry`, deterministic scenario bundle, `llm-quality-matrix`, or `llm-quality-open-world-closure` artifact was produced in this block.
- **FACT:** no old authority seam became deleted or unreachable in this block.
- **INFERENCE:** the remaining blocker for multi-pack closure is no longer runtime target materialization; it is the surviving `demo_salon` guarded-lock failure family plus non-canonical run-integrity state that prevents truthful acceptance re-entry.
- **Recommendation:** stop this implementation block here and author one new package for the surfaced `demo_salon` non-canonical lock failure family before any further multi-pack acceptance rerun.

## What Was Run
- **FACT:** deterministic inventory and contract check:
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands`
  - `rg -n "demo_salon/main|clinic_pack/main|generic/main|llm-quality-matrix|llm-quality-open-world-closure|lock/replay/canary/full" docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- **FACT:** first locked guarded command:
  - `BASE_URL=http://127.0.0.1:8000 scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-reentry --pg-checklist /tmp/booking_quality/pg_checklist-a922-reentry.json -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- **FACT:** wider artifact inventory used only to identify the blocking canonical state after the guarded command stopped:
  - `python3 scripts/quality_artifact_report.py --hours 168 --show-commands`
  - targeted reads of `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/{summary.json,run_manifest.json,brief.md,manual_audit.md,manual_audit.json}`
- **FACT:** expected re-entry artifact presence check confirmed all required outputs remain absent.

## Blocking Run Truth
- **FACT:** `python3 scripts/quality_artifact_report.py --hours 72 --show-commands` still returns only the header row, so there is no recent audited guarded baseline inside the intended reuse window.
- **FACT:** `python3 scripts/quality_artifact_report.py --hours 168 --show-commands` reveals the latest relevant lock run:
  - `finished_at=2026-03-15T07:24:16.762166+00:00`
  - `mode=lock`
  - `run_id=p1.6o224-l2-dev-20260315-a1-r1`
  - `status=incomplete`
  - `infra_valid=True`
  - `manual_audit=done`
  - `artifacts_valid=True`
- **FACT:** `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/summary.json` records:
  - `semantic_valid=false`
  - `stop_reason=max_failures_reached:1`
  - `failure_families.family_count=1`
  - top family `reason=info_section_miss`
- **FACT:** `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/manual_audit.md` records:
  - `dialog_coverage_gap: dialogs_seen=1/10`
  - `run_integrity_reasons=['run_completion_gap']`
  - inferred/analyst root causes `['judge_oracle_alignment_gap', 'non_canonical_partial_dialog_execution']`
- **FACT:** `/tmp/booking_quality/p1.6o224-l2-dev-20260315-a1-r1/brief.md` records `governance_closure_valid=false` with reasons `['semantic_invalid_or_missing', 'run_integrity_invalid_or_missing']`.

## Why Re-entry Cannot Continue
- **FACT:** the TP requires the guarded canary lane to fail closed on invalid preflight / judge / artifact integrity / failure-family conditions and forbids runtime/core patches inside this evidence-only block.
- **FACT:** the prior lock that blocks a fresh run is not an infra-only process failure; it is semantic-invalid and non-canonical.
- **INFERENCE:** the narrow unchanged-fingerprint retry admission for infra-invalid previous locks is not truthful for `p1.6o224-l2-dev-20260315-a1-r1`, so using it here would be a gate bypass rather than admissible progress.
- **FACT:** because the lock step never started, the ordered sequence cannot truthfully advance to `replay`, `canary`, `full`, deterministic scenario generation, `llm-quality-matrix`, or `llm-quality-open-world-closure`.

## Expected Artifacts Not Produced
- **FACT:** all required outputs for this block remain absent:
  - `/tmp/booking_quality/booking-lock-a922-reentry/summary.json`
  - `/tmp/booking_quality/booking-replay-a922-reentry/summary.json`
  - `/tmp/booking_quality/booking-canary-a922-reentry/summary.json`
  - `/tmp/booking_quality/booking-full-a922-reentry/summary.json`
  - `/tmp/booking_quality/multi-pack-seed-ru-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-kk-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-mixed-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-translit-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-reentry-a922/matrix_summary.json`
  - `/tmp/booking_quality/multi-pack-closure-a922-reentry.json`

## Next Honest Path
1. Publish this block as a truthful GAP, not as partial closure evidence.
2. Author one new package for the surfaced `demo_salon` non-canonical guarded-lock failure family (`info_section_miss` + `run_completion_gap`) that blocks acceptance re-entry.
3. Re-enter the multi-pack acceptance bundle only after that package either deletes the surfaced family or truthfully proves a different admissible blocker.

## Gap Register
- **GAP:** the multi-pack acceptance re-entry bundle cannot start because the latest relevant `demo_salon` guarded lock remains non-canonical and blocks a fresh canonical lock attempt.
- **GAP:** the surfaced blocking family is `info_section_miss` under `bot_active` contract state, coupled with `run_completion_gap` / `dialogs_seen=1/10`.
- **GAP:** no new re-entry acceptance evidence exists for `demo_salon`, `clinic_pack`, or `generic` in this block.
