# Consultant Core Pending Booking Reentry Booking Prompt Authority Reset Closure Replay A922

## Result
- Closure status: failed truthfully; no runtime edits were made inside the replay block.
- Fresh closure replay: `/tmp/booking_quality/a922-go2f-seed19-r53`
- The prior structural block stays valid as deterministic evidence, but live closure still fails on the same pending booking reentry / booking-prompt family.

## Scope
- confirm runtime parity before replay
- run exactly one fresh closure replay on the locked `seed19` scenario set
- strict-audit the fresh artifact
- classify the surviving failure family without reopening replay-first mode

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r53 --status done --strict-artifacts` -> `pass`

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `r53` finished with `infra_valid=true`, `semantic_valid=false`, `dialogs=10`, `turns=143`, `turns_strict_failed=5`, and `strict_pass_rate=0.965`. | `/tmp/booking_quality/a922-go2f-seed19-r53/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r53/brief.md` |
| FACT | The strict-failed rows are `LLM-QUAL-a922-go2f-seed19-r53-002-09-bf0a7d`, `LLM-QUAL-a922-go2f-seed19-r53-002-10-864323`, `LLM-QUAL-a922-go2f-seed19-r53-003-01-f32c28`, `LLM-QUAL-a922-go2f-seed19-r53-003-02-a02bfb`, and `LLM-QUAL-a922-go2f-seed19-r53-006-01-0835dc`. | `/tmp/booking_quality/a922-go2f-seed19-r53/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r53/failure_families.json` |
| FACT | Rows `002-09`, `003-01`, and `006-01` still exit through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`. | `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl` |
| FACT | Row `002-10` still exits through `turn_planner.safe_info_fact.v1` with `reason_code=promotions_question`, and row `003-02` still exits through `turn_planner.safe_service_query_fact.v1` with `reason_code=pricing_query`, while the scenario still expects booking continuity to preserve `expected_reply_type=time`. | `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl`, `/tmp/booking_quality/a922-go2f-seed19-r53/scenarios.json` |
| FACT | `booking_prompt_owner` still hard-requires a live `conversation_snapshot` at `truffles-api/app/services/reasoning_core.py:6457`, while early explicit handoff still fires at `truffles-api/app/services/reasoning_core.py:12095` before late `initial_booking_prompt_owner` at `truffles-api/app/services/reasoning_core.py:12307`. | `truffles-api/app/services/reasoning_core.py:6457`, `truffles-api/app/services/reasoning_core.py:12095`, `truffles-api/app/services/reasoning_core.py:12307` |
| FACT | Pending service-choice reactivation still routes through `booking_prompt_owner.resolve_pending_booking_reactivation_candidate(...)`, but `resolve_llm_booking_prompt_candidate(...)` only rescues `timeout` / `deadline_exceeded` at `truffles-api/app/core/booking_prompt_owner.py:284`; a reproducible direct probe for `На какое время лучше записаться?` returns `error=invalid_schema` with a collect payload instead of a recovered collect contract. | `truffles-api/app/core/booking_prompt_owner.py:284`, local direct probe recorded during `r53` classification |
| FACT | The repo already has a non-frozen reusable invalid-schema booking recovery surface in `truffles-api/app/services/policy_validation_boundary_service.py`; frozen `decision.py` calls it for `policy_core_invalid_schema_service_grounded_booking` at `truffles-api/app/routers/webhook/decision.py:14342`. | `truffles-api/app/services/policy_validation_boundary_service.py`, `truffles-api/app/routers/webhook/decision.py:14342` |
| INFERENCE | `r53` did not surface a new family. It proved the same pending booking reentry family is still live on two adjacent seams: pending-state initial booking entry still bypasses canonical booking ownership before early explicit handoff, and pending reactivation with a recoverable `invalid_schema` collect payload still has no turn-planner boundary recovery before the same handoff seam. | `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl`, `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/core/booking_prompt_owner.py` |
| INFERENCE | Rows `002-10` and `003-02` are downstream continuity symptoms of the same family, because the booking collect contract was never restored before those promo/price interrupts ran. | `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl`, `truffles-api/app/services/reasoning_core.py:6457`, `truffles-api/app/services/reasoning_core.py:12095`, `truffles-api/app/services/reasoning_core.py:12307` |
| UNKNOWN | Whether the promo/price follow-up rows disappear completely once both reentry seams are deleted, or whether a smaller independent info-continuity family remains behind them. | no post-fix replay exists yet |

## Failure Surface
### Rows `002-09`, `003-01`, `006-01`
- user: `На какое время лучше записаться?`, `Я хочу записаться на маникюр.`, `Мне нужно записаться на маникюр.`
- expected: `booking_prompt / collect`
- actual: `escalate / handoff`
- owner_cutover: `turn_planner.safe_explicit_handoff_owner.v1`
- reason_code: `terminal_owner_unresolved`

### Rows `002-10`, `003-02`
- user: `Есть ли какие-то акции на маникюр в следующем месяце?`, `Какова цена на маникюр?`
- expected: fact reply while preserving booking continuity with `expected_reply_type=time`
- actual: fact reply without the booking continuity contract
- owner_cutover: `turn_planner.safe_info_fact.v1`, `turn_planner.safe_service_query_fact.v1`
- reason_code: `promotions_question`, `pricing_query`

## Exact Current Authority Map At Closure Failure
1. `booking_prompt_owner` runs early in the direct-owner chain, but it returns `None` immediately when `conversation_snapshot is None` at `truffles-api/app/services/reasoning_core.py:6457`. That makes it incapable of claiming pending-state initial booking entry turns like rows `003-01` and `006-01`.
2. Early explicit handoff still runs at `truffles-api/app/services/reasoning_core.py:12095` before `initial_booking_prompt_owner` is even consulted at `truffles-api/app/services/reasoning_core.py:12307`. Therefore pending initial booking entry can still fall through the old handoff seam before canonical booking ownership is exhausted.
3. For row `002-09`, `pending_booking_reactivation_candidate` still depends on `resolve_llm_booking_prompt_candidate(...)`. When `route_llm_policy_core(...)` returns `error=invalid_schema`, that path has no recovery except timeout/deadline handling, so it returns `None` instead of turning the recoverable collect payload into a booking prompt.
4. Once these turns miss canonical booking ownership, later promo/price interrupts route through `safe_info_fact` / `safe_service_query_fact` without restored `expected_reply_type=time`, producing rows `002-10` and `003-02`.

## Closure Decision
- Closure is rejected.
- This is the same family continuation, so no new decision TP is justified.
- The next honest move is to switch canon back to the existing decision TP and execute one delete-first structural block after one precise web search.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r53/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r53/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r53/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r53/scenarios.json`
- `/tmp/booking_quality/a922-go2f-seed19-r53/failure_families.json`
