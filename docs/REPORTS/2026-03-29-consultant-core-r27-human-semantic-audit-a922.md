# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260329-r27`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `stale service-choice reprompt after final-name fill is gone, but replay r27 stays product-red because booking datetime continuity breaks under policy-core degrade and check-booking collect residue remains`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260329-r27`

## Scope
Full turn-by-turn human semantic audit of replay `r27` after the bounded boundary fix for the surfaced family `downstream booking completion residue after filled name` / shared mechanism `collect->commit transition when required booking slots are already complete`.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 7 pass / 1 weak / 2 fail`, `turns 10 pass / 1 weak / 4 fail`
- family verdict: the original stale `service_choice` reprompt on the final name turn is closed on this replay; `dialog 2 / turn 5` no longer reopens the service question
- conclusion: `the bounded boundary fix removed the original collect->commit stale-service residue, but practical/product closure remains open because dialog 2 now fails through booking datetime continuity loss under policy-core degrade, and dialog 9 still shows live check-booking collect residue`

## Turn-by-turn audit
| Dialog | Turn | User | Bot | Tooling verdict | Human verdict | Why |
|---|---:|---|---|---|---|---|
| 1 | 1 | `Сколько стоит маникюр?` | Price answer for manicure | `strict_ok=false` | `pass` | Good direct answer; strict red is taxonomy drift only. |
| 2 | 1 | `Хочу записаться на маникюр` | Asks for date/time | `strict_ok=true` | `pass` | Booking opening is correct; service is no longer re-asked. |
| 2 | 2 | `Есть ли акции?` | Promo answer | `strict_ok=true` | `pass` | Correct interrupt answer. |
| 2 | 3 | `Какая цена?` | Manicure pricing answer | `strict_ok=true` | `pass` | Correct factual interrupt while preserving booking context. |
| 2 | 4 | `Завтра в 15:00` | Hours answer | `strict_ok=true` | `fail` | The datetime reply is matched in trace, but policy-core degrades and the fallback answers `hours` instead of continuing booking. |
| 2 | 5 | `Алина` | Transparent manager escalation | `strict_ok=true` | `fail` | The old service reprompt is gone, but the dialog is already broken: runtime lost booking datetime continuity and escalates after `datetime_parse_failed` instead of booking progression. |
| 3 | 1 | `Позовите менеджера, пожалуйста` | Transparent manager handoff | `strict_ok=false` | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | 1 | `Каковы часы работы?` | Correct hours answer | `strict_ok=false` | `pass` | Good factual answer; strict red is taxonomy drift only. |
| 5 | 1 | `Где находится салон?` | Address + hours | `strict_ok=false` | `weak` | Correct location answer, but still broader than needed. |
| 6 | 1 | `Есть ли у вас парковка?` | Address + hours + parking fact | `strict_ok=false`, `judge_pass` | `pass` | Main parking question is now answered on this replay; strict red is taxonomy drift only. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Accepts photo/reference and asks for the photo + brief | `strict_ok=true` | `pass` | Natural consult-first behavior; no collapse into generic booking collection. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | Explicit service grounding still holds. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks for phone and approximate date/time | `strict_ok=true` | `fail` | `На четверг` should already ground the temporal clue; the bot still re-asks it. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | Repeats the same generic prompt | `strict_ok=false` | `fail` | The follow-up still ignores the already supplied temporal clue. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible behavior is correct; explicit-service grounding remains closed. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `fail` | The old service-loop residue is gone, but the dialog now breaks on datetime continuity under degrade. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct but still broader than needed. |
| 6 | Parking fact | `pass` | Parking is answered on this replay. |
| 7 | Media prompt | `pass` | Natural consult/media handling on the visible path. |
| 8 | Second booking entry | `pass` | Explicit service grounding remains correct. |
| 9 | Check and confirm sequence | `fail` | Temporal-clue grounding/follow-up residue is still live. |
| 10 | Third booking entry | `pass` | The old service-collapse symptom remains closed. |

## Family-level verdicts

### A. Closed for this block: collect->commit stale-service reprompt after final-name fill
- surfaced in `r26c`: `dialog 2 / turn 5` reopened `service` after `service + datetime + name` were already present
- fresh replay evidence:
  - `dialog 2 / turn 5` no longer emits `На какую услугу хотите записаться?`
  - the final turn now reaches `booking_escalated` after `appointment_skip_reason=datetime_parse_failed`; the old stale `service_choice` reprompt is absent
- deterministic evidence:
  - `truffles-api/tests/test_message_endpoint.py` now covers `collect + complete booking slots + no open questions -> continue booking flow`
- verdict: `closed as originally scoped`; the exact stale-service collect residue is no longer the live blocker

### B. New surfaced blocker on current truth: booking datetime continuity loss under policy-core degrade
- surfaced by: `dialog 2 / turns 4-5`
- symptom:
  - `dialog 2 / turn 4`: `Завтра в 15:00` is matched as `datetime`, but `llm_policy_core` ends in `deadline_exceeded` and degraded fallback answers `hours`
  - the same turn still updates question state to `name`, so `dialog 2 / turn 5` consumes `Алина` while booking context is semantically inconsistent
  - `dialog 2 / turn 5`: booking commit is skipped with `appointment_skip_reason=datetime_parse_failed`, then runtime escalates
- status: `open`

### C. Open residual: live check-booking collect/fallback residue
- surfaced by: `dialog 9 / turns 1-2`
- symptom: `на четверг` is still not grounded strongly enough, and the follow-up repeats the same generic reference prompt
- status: `open`

### D. Not reproduced on this replay: parking fact composition regression
- surfaced previously in `r25`/`r26c`, but on `r27` `dialog 6 / turn 1` includes the parking fact directly
- verdict: `not reproduced on r27`; no closure claim is made here because this block did not RCA the parking mechanism

### E. Secondary noise: oracle action-taxonomy drift
- surfaced by: dialogs `1`, `3`, `4`, `5`, `6`
- symptom: otherwise human-correct `reply/escalate` turns remain strict-red due expectation taxonomy drift
- status: `secondary`; not the product blocker for this block

## Next actions
1. Treat the original collect->commit stale-service reprompt family as closed for this block.
2. Open the next mechanism-first TP for `booking datetime continuity loss under policy-core degrade` using `dialog 2 / turns 4-5` as the surfaced evidence family.
3. Keep `live check-booking collect/fallback residue` explicitly open in canon truth.
4. Do not claim parking closed yet; it was green on this replay, but this block did not perform family-level RCA for parking.
