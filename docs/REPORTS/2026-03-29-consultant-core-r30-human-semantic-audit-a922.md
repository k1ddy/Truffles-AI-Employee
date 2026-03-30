# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260329-r30`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `r30 closes the booking datetime continuity family; replay stays product-red only because the live check-booking collect/fallback residue remains`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260329-r30`

## Scope
Full turn-by-turn human semantic audit of replay `r30` after the bounded boundary fix for the surfaced family `booking datetime continuity loss under policy-core degrade` / shared mechanism `booking slot continuity across degrade / answer matching / commit handoff`.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 8 pass / 1 weak / 1 fail`, `turns 12 pass / 1 weak / 2 fail`
- family verdict: the original `booking datetime continuity loss under policy-core degrade` family is closed on this replay; `dialog 2 / turn 4` no longer diverts a matched datetime reply into `hours`
- conclusion: `the bounded boundary fix removed the live datetime-continuity break; practical/product closure remains open only because dialog 9 still shows live check-booking collect/fallback residue`

## Turn-by-turn audit
| Dialog | Turn | User | Bot | Tooling verdict | Human verdict | Why |
|---|---:|---|---|---|---|---|
| 1 | 1 | `Сколько стоит маникюр?` | Manicure pricing answer | `strict_ok=false` | `pass` | Good direct answer; strict red is taxonomy drift only. |
| 2 | 1 | `Хочу записаться на маникюр` | Asks for date/time | `strict_ok=true` | `pass` | Booking opening remains correct; explicit service grounding stays closed. |
| 2 | 2 | `Есть ли акции?` | Promo answer | `strict_ok=true` | `pass` | Correct factual interrupt while preserving booking flow. |
| 2 | 3 | `Какая цена?` | Manicure pricing answer | `strict_ok=true` | `pass` | Correct pricing interrupt. |
| 2 | 4 | `Завтра в 15:00` | `Отлично, время подходит. Как вас зовут?` | `strict_ok=true` | `pass` | The matched datetime now continues booking correctly; the old `hours` diversion is gone. |
| 2 | 5 | `Алина` | Transparent manager escalation | `strict_ok=true` | `pass` | Visible behavior is acceptable product handoff after collecting the booking details; the old continuity break is no longer user-visible. |
| 3 | 1 | `Позовите менеджера, пожалуйста` | Transparent manager handoff | `strict_ok=false` | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | 1 | `Каковы часы работы?` | Correct hours answer | `strict_ok=false` | `pass` | Good factual answer; strict red is taxonomy drift only. |
| 5 | 1 | `Где находится салон?` | Address + hours | `strict_ok=false` | `weak` | Correct location answer, but still broader than needed. |
| 6 | 1 | `Есть ли у вас парковка?` | Address + hours + parking fact | `strict_ok=false` | `pass` | Main parking question is answered directly on this replay. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Accepts photo/reference and asks for the photo + brief | `strict_ok=true` | `pass` | Natural consult-first behavior; no collapse into generic booking collection. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | Explicit service grounding still holds. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks for phone and approximate date/time | `strict_ok=true` | `fail` | `На четверг` should already ground the temporal clue; the bot still re-asks it. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | Repeats the same generic prompt | `strict_ok=false` | `fail` | The follow-up still ignores the already supplied temporal clue. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible booking opening remains correct. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `pass` | The old datetime-continuity break is gone; the final transparent handoff remains product-acceptable on this replay. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct but still broader than needed. |
| 6 | Parking fact | `pass` | Parking is answered directly on this replay. |
| 7 | Media prompt | `pass` | Natural consult/media handling on the visible path. |
| 8 | Second booking entry | `pass` | Explicit service grounding remains correct. |
| 9 | Check and confirm sequence | `fail` | Temporal-clue grounding/follow-up residue is still live. |
| 10 | Third booking entry | `pass` | Booking opening remains correct. |

## Family-level verdicts

### A. Closed for this block: booking datetime continuity loss under policy-core degrade
- surfaced in `r27`: `dialog 2 / turns 4-5` matched `datetime` but degraded into `hours`, then broke booking continuity
- fresh replay evidence:
  - `dialog 2 / turn 4` now responds `Отлично, время подходит. Как вас зовут?`
  - `dialog 2 / turn 4` trace shows `question_contract` matched `datetime`, `llm_policy_core` stayed valid, and runtime emitted booking prompt for `name`
  - no live `booking_interrupt info_reply` on `hours` remains on the covered turn
- deterministic evidence:
  - `truffles-api/tests/test_message_endpoint.py` covers the degrade-time matched-time interrupt skip path
- verdict: `closed as scoped`; the original datetime-continuity break is no longer the live practical blocker

### B. Open residual: live check-booking collect/fallback residue
- surfaced by: `dialog 9 / turns 1-2`
- symptom:
  - `на четверг` is still not grounded strongly enough as an already supplied temporal clue
  - follow-up repeats the same generic prompt instead of advancing reference collection
- status: `open`

### C. Not reproduced on this replay: parking fact composition regression
- `dialog 6 / turn 1` includes the parking fact directly on `r30`
- verdict: `not reproduced on r30`; no closure claim is made here because this block did not RCA the parking mechanism

### D. Secondary noise: oracle action-taxonomy drift
- surfaced by: dialogs `1`, `3`, `4`, `5`, `6`
- symptom: otherwise human-correct `reply/escalate` turns remain strict-red due expectation taxonomy drift
- status: `secondary`; not the product blocker for this block

### E. Residual technical debt, not current practical blocker: transparent-handoff commit residue
- `dialog 2 / turn 5` trace still records `appointment_skip_reason=datetime_parse_failed` before the transparent manager handoff
- human verdict on the visible turn remains `pass` because the user-facing response is acceptable `HANDOFF`
- status: `trace-visible debt`; keep out of next blocker ordering unless it becomes human-visible again

## Next actions
1. Treat `booking datetime continuity loss under policy-core degrade` as closed for this block.
2. Open the next mechanism-first TP for `live check-booking collect/fallback residue`, framed as `booking-manage temporal clue grounding / follow-up continuity`.
3. Keep `parking fact composition regression` out of closure claims until it gets its own family-level RCA block.
4. Keep the trace-visible `datetime_parse_failed` residue as technical debt, not as the next practical blocker, unless it starts harming visible behavior again.
