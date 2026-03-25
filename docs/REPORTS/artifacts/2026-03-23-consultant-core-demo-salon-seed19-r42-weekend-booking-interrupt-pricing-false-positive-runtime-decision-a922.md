# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R42 Weekend Booking Interrupt Pricing False Positive Runtime Decision A922

## Truthful input artifacts
- `/tmp/booking_quality/a922-go2f-seed19-r42/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r42/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`

## Classification
- `r42` is a truthful completion replay: all 10 dialogs are present, `143/143` turns are materialized, `infra_valid=true`, and `run_integrity_valid=true`.
- The first surviving strict blocker is a `runtime/model` family, not a proof/preflight family.
- `manual_audit.json` still records broader judge/HQ1 conflict debt, but the surviving strict family in `failure_families.json` is isolated to one row on `stage=booking_interrupt`.

## Why it is runtime
- `failure_families.json` isolates the surviving strict family to `reason:expected_action_mismatch|type:turn|category:expectation|stage:booking_interrupt|state:bot_active` with sample turn `LLM-QUAL-a922-go2f-seed19-r42-004-09-e29405`.
- The failing row is not an incomplete or infra-invalid artifact; it is part of the full-completion replay.
- The runtime path is directly traceable into live code: `_has_price_signal(...)` -> `_detect_info_class_intents(...)` -> booking interrupt priority -> tool reply finalization.

## Fresh failing row
- Row: `LLM-QUAL-a922-go2f-seed19-r42-004-09-e29405`
- User: `Почему я не могу записаться на выходные?`
- Expected: `handoff`, state `pending`
- Actual: `decision_meta.action='reply'`, `tool_action='catalog.service_query'`, `outbox_text='Дизайн ногтей — от 300 ₸.'`
- `decision_meta.booking_prompt_interrupt_recovery='active_time_pricing_interrupt'`
- `decision_meta.turn_outcome.meta.reason_code='booking_interrupt'`
- `decision_meta.turn_outcome.meta.owner_cutover='turn_executor.tool_reply_turn_outcome.v1'`
- `decision_meta.turn_outcome.meta.interaction_owner='booking_interrupt_info'`

## Root cause evidence
- `truffles-api/app/services/demo_salon_knowledge.py:1200` uses raw substring matching in `_contains_any(...)`.
- `truffles-api/app/services/demo_salon_knowledge.py:1586` uses that substring matcher for `price_keywords` in `_has_price_signal(...)`.
- The system lexicon contains `почем`, and raw substring matching makes `почем` match inside `почему`.
- `truffles-api/app/routers/webhook/info.py:238` and `truffles-api/app/routers/webhook/info.py:332` therefore emit `pricing` on the failing text.
- `truffles-api/app/services/reasoning_core.py:10499` prioritizes `pricing` ahead of `hours` in the active booking interrupt path.
- `truffles-api/app/services/reasoning_core.py:10732` then finalizes the pricing `catalog.service_query` reply instead of staying on the weekend/handoff route.

## Advisory, not blocker
- `hq1_bad_turn_count=4` remains in `summary.json`, but three `handoff_miss` rows are still `strict_ok=true`; they are advisory debt under contract-first arbitration, not the first surviving blocker.

## Next admissible move
- `implement_consultant_core_demo_salon_seed19_r42_weekend_booking_interrupt_pricing_false_positive_runtime_family`
