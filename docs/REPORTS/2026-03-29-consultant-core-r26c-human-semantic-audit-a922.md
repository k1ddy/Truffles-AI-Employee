# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260329-r26c`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `explicit booking-service grounding no longer collapses on opening turns, but replay r26c stays product-red because booking completion residue, live check-booking collect residue, and parking regression remain`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260329-r26c`

## Scope
Full turn-by-turn human semantic audit of replay `r26c` after the bounded owner-side booking-service grounding fix.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 5 pass / 2 weak / 3 fail`, `turns 9 pass / 2 weak / 4 fail`
- family verdict: `owner-side booking service grounding regression` is closed on this replay; dialogs `2`, `8`, and `10` no longer re-ask the service on booking openings
- conclusion: `the bounded owner-side fix landed, but practical/product closure remains open because a downstream booking-completion residue, the live check-booking collect residue, and parking fact composition still fail`

## Turn-by-turn audit
| Dialog | Turn | User | Bot | Tooling verdict | Human verdict | Why |
|---|---:|---|---|---|---|---|
| 1 | 1 | `Сколько стоит маникюр?` | Price answer for manicure | `strict_ok=false` | `pass` | Good direct answer; strict red is taxonomy drift only. |
| 2 | 1 | `Хочу записаться на маникюр` | Asks for date/time | `strict_ok=true` | `pass` | The explicit service is grounded and the flow advances to the next missing slot. |
| 2 | 2 | `Есть ли акции?` | Promo answer | `strict_ok=true` | `pass` | Correct interrupt answer. |
| 2 | 3 | `Какая цена?` | Manicure pricing answer | `strict_ok=true` | `pass` | Correct factual interrupt while preserving the grounded service. |
| 2 | 4 | `Завтра в 15:00` | Confirms time and asks for name | `strict_ok=true` | `pass` | Correct booking progression. |
| 2 | 5 | `Алина` | Re-asks service | `strict_ok=true` | `fail` | All booking slots are already present; asking for service again breaks completion. |
| 3 | 1 | `Позовите менеджера, пожалуйста` | Transparent manager handoff | `strict_ok=false` | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | 1 | `Каковы часы работы?` | Correct hours answer | `strict_ok=false` | `pass` | Good factual answer; strict red is taxonomy drift only. |
| 5 | 1 | `Где находится салон?` | Address + hours | `strict_ok=false` | `weak` | Correct location answer, but broader than needed. |
| 6 | 1 | `Есть ли у вас парковка?` | Address + hours, no parking fact | `strict_ok=false`, `judge_fail` | `fail` | The parking question is still missed. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Accepts photo, gives consult framing, then asks about service/booking | `strict_ok=true` | `weak` | Better than a hard collapse, but still too booking-centered for a consult/media cue. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | The explicit service is grounded and the flow advances correctly. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks for phone and approximate date/time | `strict_ok=true` | `fail` | `На четверг` should already ground the temporal clue; the bot still re-asks it. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | Repeats the same generic prompt | `strict_ok=false` | `fail` | The follow-up still ignores the already supplied temporal clue. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible behavior is correct; the turn reached `datetime` rather than collapsing back to service. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `fail` | Opening service grounding is fixed, but the dialog breaks again on the final name turn. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct but still broader than needed. |
| 6 | Parking fact | `fail` | Parking is still missed. |
| 7 | Media prompt | `weak` | Improved, but still not naturally consult-first. |
| 8 | Second booking entry | `pass` | Explicit service grounding now holds. |
| 9 | Check and confirm sequence | `fail` | Temporal clue grounding/follow-up residue is still live. |
| 10 | Third booking entry | `pass` | The old service-collapse symptom is gone on the visible path. |

## Family-level verdicts

### A. Closed for this block: owner-side booking service grounding regression
- surfaced in `r25`: dialogs `2`, `8`, `10` re-asked the service despite explicit booking-service turns
- fresh replay evidence:
  - `dialog 2 / turn 1`: owner payload now carries `slots.service="маникюр"` and `next_question="datetime"`
  - `dialog 8 / turn 1`: owner payload now carries `slots.service="педикюр"` and `next_question="datetime"`
  - `dialog 10 / turn 1`: visible behavior now asks for date/time rather than service; the turn used timeout-degraded booking collect, so this row is behavioral closure rather than owner-output proof
- verdict: `closed on r26c`; this removes the original explicit-service collapse family from the surfaced blocker set

### B. Open residual: downstream booking completion residue after filled name
- surfaced by: `dialog 2 / turn 5`
- symptom: after `service + datetime + name` are all present, the final response still asks `На какую услугу хотите записаться?`
- live-path clue: the owner payload already contains `slots={"service":"маникюр","datetime":"15:00","name":"Алина"}` with reason `можно переходить к оформлению записи через календарь`, but runtime still emits a `booking_prompt` with a service-choice question
- status: `open`

### C. Open residual: live check-booking collect/fallback residue
- surfaced by: `dialog 9 / turns 1-2`
- symptom: `на четверг` is still not grounded strongly enough, and the follow-up repeats the same generic reference prompt
- status: `open`

### D. Open residual: parking fact composition regression
- surfaced by: `dialog 6 / turn 1`
- symptom: the final answer still omits parking and falls back to address/hours
- status: `open`

### E. Secondary noise: oracle action-taxonomy drift
- surfaced by: dialogs `1`, `3`, `4`, `5`
- symptom: otherwise human-correct `reply/escalate` turns remain strict-red due expectation taxonomy drift
- status: `secondary`; not the product blocker for this block

## Next actions
1. Treat the owner-side explicit-service grounding family as closed for this block.
2. RCA the downstream booking completion residue on `dialog 2 / turn 5` before touching wording or isolated dialogs.
3. Keep `check-booking collect/fallback residue` and `parking fact composition regression` explicitly open in canon truth.
