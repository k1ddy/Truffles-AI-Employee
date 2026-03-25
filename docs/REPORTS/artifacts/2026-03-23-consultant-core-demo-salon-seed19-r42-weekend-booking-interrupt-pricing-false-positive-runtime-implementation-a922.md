# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R42 Weekend Booking Interrupt Pricing False Positive Runtime Implementation A922

## Input truth
- `/tmp/booking_quality/a922-go2f-seed19-r42/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/failure_families.json`
- `/tmp/booking_quality/a922-go2f-seed19-r42/responses.jsonl`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r42-weekend-booking-interrupt-pricing-false-positive-runtime-decision-a922.md`

## Implemented repair
- `truffles-api/app/services/demo_salon_knowledge.py`
  - added token-aware price keyword matching so single-token colloquials like `почем` no longer match inside unrelated words such as `почему`
  - preserved real price-intent coverage via bounded stem handling for `цена -> цен*` and `стоимость -> стоимост*`
- `truffles-api/app/routers/webhook/info.py`
  - stopped resurrecting a `pricing` anchor intent when `price_signal` is already false, so anchor-only false positives cannot override the resolver result
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
  - mirrored the same bounded token-aware price-signal fix on the neutral adapter
- `truffles-api/tests/test_booking_info_interrupt_contract.py`
  - added coverage proving `Почему я не могу записаться на выходные?` is not a pricing query and that the neutral adapter keeps `Почем маникюр?` as a true positive while rejecting the false positive
- `truffles-api/tests/test_reasoning_core.py`
  - added a regression proving the active booking prompt owner no longer routes the surfaced weekend message through `catalog.service_query`

## Deterministic evidence
- `pytest -q truffles-api/tests/test_booking_info_interrupt_contract.py -k "weekend or price_signal"`
  - `1 passed, 8 deselected`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pricing_interrupt or weekend_booking_followup or direct_service_query_fact_defers_active_booking_interrupt"`
  - `6 passed, 199 deselected`
- direct post-fix probe on the live resolver code:
  - `legacy._has_price_signal("Почему я не могу записаться на выходные?") == False`
  - `info_router._detect_info_class_intents(...) == ['hours']`
  - `neutral_false_positive == False`
  - `neutral_true_positive == True`

## What changed materially
- Before the fix, the surfaced text produced `pricing + hours`, then `reasoning_core.py` prioritized `pricing` and emitted `catalog.service_query`.
- After the fix, the same text no longer produces `pricing` in the resolver path, so the active booking interrupt path cannot take the pricing tool-reply branch on that message.

## Residual debt
- Fresh replay proof is still required. Deterministic tests prove the bounded family locally, but they do not replace the next truthful closure replay.
- Duplicate booking-prompt owner defs remain in `truffles-api/app/services/reasoning_core.py`.
- Replay control-plane stale simulation-id contamination remains unresolved.
- Prod floor remains degraded (`truffles-outbox`, `bge-m3`).

## Next admissible move
- `rerun_consultant_core_demo_salon_seed19_r42_weekend_booking_interrupt_pricing_false_positive_canary_replay`
