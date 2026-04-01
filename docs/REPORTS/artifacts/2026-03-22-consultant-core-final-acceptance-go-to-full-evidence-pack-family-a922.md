# 2026-03-22 — Consultant Core Final Acceptance Go-To-Full Evidence Pack Family A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-ACCEPTANCE-GO-TO-FULL-EVIDENCE-PACK-FAMILY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Materialized one fresh post-`r20` `L1` JUnit at `/tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`.
- Closed one stale non-canonical seed artifact `a922-go-to-full-seed7` after it fail-closed at preflight because the `run_id` token `go-to-full` was parsed as acceptance `full` mode.
- Produced one fresh green multi-seed summary for seed `7`: `/tmp/booking_quality/a922-go2f-seed7/summary.json`.
- The family then stopped truthfully on seed `19`, where `/tmp/booking_quality/a922-go2f-seed19/summary.json` finished `infra_valid=true`, `run_integrity_valid=true`, but `semantic_valid=false`.
- Because the TP stop-condition forbids continuing past a fresh semantic blocker, seed `42`, checklist materialization, and acceptance `lock` retry were not executed.

## What Was Run
- `pytest -q truffles-api/tests/test_booking_quality_guarded_wrapper.py -k 'allows_fresh_lock_after_audited_non_canonical_latest_run' --junitxml /tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go-to-full-seed7 --status done --notes 'Non-canonical seed attempt blocked at preflight: run_id token go-to-full resolved to acceptance full mode and triggered chain_controller_required.' --root-cause 'run_id contained full token; direct dev-lane llm-quality was therefore misclassified as acceptance full preflight.' --next-step 'Rerun the seed with neutral run_id under quality_lane=dev.' --oracle-judge-alignment not_applicable --oracle-winner not_applicable --oracle-resolution-summary 'No semantic artifact was evaluated; this was an invalid preflight-only run.'`
- `python3 ops/diagnose.py llm-quality ... --seed 7 --quality-lane dev --output-dir /tmp/booking_quality/a922-go2f-seed7 --run-id a922-go2f-seed7`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed7 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality ... --seed 19 --quality-lane dev --output-dir /tmp/booking_quality/a922-go2f-seed19 --run-id a922-go2f-seed19`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19 --status done --strict-artifacts`

## Truthful Result
- Fresh green seed `7` now exists:
  - `/tmp/booking_quality/a922-go2f-seed7/summary.json`
  - `infra_valid=true`
  - `semantic_valid=true`
  - `run_integrity_valid=true`
  - `manual_audit_status=done`
- Fresh seed `19` is the new blocker:
  - `/tmp/booking_quality/a922-go2f-seed19/summary.json`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `run_integrity_valid=true`
  - `quality_status.semantic_reasons=['blocking_reason', 'threshold_breach']`
  - `quality_status.threshold_breaches=['irrelevant_fact_rate']`
- Fresh seed `19` surfaced runtime-semantic divergence on generated multi-seed coverage, not checklist assembly failure:
  - `LLM-QUAL-a922-go2f-seed19-004-09-28263e`: `Почему я не могу записаться на выходные?` -> `decision_meta.intent=info`, `info_sections=['pricing']`
  - `LLM-QUAL-a922-go2f-seed19-004-10-c4a861`: `Каковы часы работы салона?` -> `decision_meta.intent=duration`, `info_sections=['duration']`
  - `LLM-QUAL-a922-go2f-seed19-007-10-55069e`: `Я слышал, что у вас есть акция на маникюр.` -> `decision_meta.intent=services_overview`, `info_sections=['services_overview']`
- The pack already contains truthful hours/promotions knowledge, so this is not a missing-data blocker:
  - `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`

## Classification
- This block no longer stops on acceptance-preflight checklist materialization.
- The first surviving blocker is now a fresh generated multi-seed semantic family on demo-salon booking/check-booking interruption.
- Current truthful split:
  - runtime-semantic family: wrong fact/info routing under active booking continuity (`irrelevant_fact`, `expected_action_mismatch`, `expected_reply_type_mismatch`)
  - advisory proof family: judge/HQ1 conflict remains present on the same run (`winner=contract`, `conflict_count=24`) but is not the first admissible move
- Therefore the acceptance evidence-pack family stops here and hands off to a bounded runtime decision block.

## Closure Verdict
- No truthful `go_to_full` checklist exists yet.
- No truthful post-`r20` acceptance `lock` retry was admissible after seed `19` turned semantic-red.
- The next honest move is seed-19 runtime-family classification before any new evidence-pack or acceptance work.

## Evidence
- `/tmp/booking_quality/l1-go-to-full-a922/pytest-junit.xml`
- `/tmp/booking_quality/a922-go-to-full-seed7/{summary.json,manual_audit.json,manual_audit.md}`
- `/tmp/booking_quality/a922-go2f-seed7/{summary.json,brief.md,manual_audit.json,responses.jsonl,trace_bundle.jsonl}`
- `/tmp/booking_quality/a922-go2f-seed19/{summary.json,brief.md,failure_families.json,manual_audit.json,responses.jsonl,trace_bundle.jsonl}`

## Next move
- `author_consultant_core_demo_salon_seed19_generated_booking_info_divergence_runtime_decision`
