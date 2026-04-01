# 2026-03-22 — Consultant Core Demo Salon Seed19 Generated Booking Info Divergence Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-RUNTIME-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Classified fresh seed `19` as the first admissible blocker after the post-`r20` evidence-pack family.
- Truthful split: the blocker is a runtime-semantic family on active booking/check-booking info interruption, while judge/HQ1 conflict remains advisory proof debt on the same artifact.

## Key evidence
- Canonical green prerequisite still holds:
  - `/tmp/booking_quality/a922-check-booking-proof-r20/summary.json`
  - `infra_valid=true`
  - `semantic_valid=true`
- Fresh seed `7` is green and admissible for the evidence pack:
  - `/tmp/booking_quality/a922-go2f-seed7/summary.json`
  - `infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`
- Fresh seed `19` is the blocker:
  - `/tmp/booking_quality/a922-go2f-seed19/summary.json`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `run_integrity_valid=true`
  - `quality_status.threshold_breaches=['irrelevant_fact_rate']`

## Runtime-family findings
- `LLM-QUAL-a922-go2f-seed19-004-09-28263e`
  - user: `Почему я не могу записаться на выходные?`
  - scenario expect: `action=handoff`, `state=pending`
  - runtime actual: `intent=info`, `info_sections=['pricing']`, `tool_action='catalog.service_query'`
- `LLM-QUAL-a922-go2f-seed19-004-10-c4a861`
  - user: `Каковы часы работы салона?`
  - scenario expect: one of `hours|working_hours|schedule`
  - runtime actual: `intent=duration`, `info_sections=['duration']`
  - this turn is one of the two `irrelevant_fact` threshold contributors
- `LLM-QUAL-a922-go2f-seed19-007-10-55069e`
  - user: `Я слышал, что у вас есть акция на маникюр.`
  - scenario expect: one of `discounts|discount|promo|promotion` and preserved `reply_type=time`
  - runtime actual: `intent=services_overview`, `info_sections=['services_overview']`, `expected_reply_type` continuity lost
  - this turn is the second `irrelevant_fact` threshold contributor

## Layer decision
- `pack/data gap`: rejected
  - `demo_salon` already contains truthful hours and promotions facts in `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml`
- `oracle/proof gap`: rejected as the first blocker
  - audit still reports `winner=contract`, `conflict_count=24`, but the semantic red path is driven by runtime-side `irrelevant_fact` and expectation mismatches on concrete turns
- `runtime contract bug`: accepted
  - active booking/check-booking interruption should not route hours/promo/weekend follow-ups into irrelevant fact owners or drop pending continuity

## Deferred debt
- The same seed carries advisory proof noise:
  - `judge_fail` / `handoff_miss` counts remain present
  - cancel/rebook follow-up turns in dialog `2` still need later proof-or-runtime review after the first runtime family is closed
- That debt is explicitly deferred because it is not the first admissible blocker.

## Closure verdict
- The fresh seed-`19` blocker is a bounded runtime family.
- Acceptance evidence-pack work stops here.
- The next truthful move is `implement_consultant_core_demo_salon_seed19_generated_booking_info_divergence_runtime_family`.
