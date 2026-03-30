# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260330-r32g`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `r32g closes the live check-booking temporal-clue continuity family on the visible product path; replay stays product-red only because parking fact composition still fails, while dialog 9 strict-red residue is now oracle/evaluator drift`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260330-r32g`

## Scope
Full turn-by-turn human semantic audit of replay `r32g` after the bounded check-booking mechanism fix and the bounded replay-evaluator/tool-evidence corrections for the same surfaced family.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 7 pass / 2 weak / 1 fail`, `turns 12 pass / 2 weak / 1 fail`
- family verdict: the original `live check-booking collect/fallback residue` family is closed on the visible product path; the remaining strict-red on `dialog 9 / turn 2` is oracle/evaluator residue, not a live temporal-clue regression
- conclusion: `the check-booking temporal-clue grounding / follow-up continuity block is closed as scoped; practical/product closure remains open because parking fact composition is again the only human-semantic fail family on current truth`

## Turn-by-turn audit
| Dialog | Turn | User | Bot | Tooling verdict | Human verdict | Why |
|---|---:|---|---|---|---|---|
| 1 | 1 | `Сколько стоит маникюр?` | Manicure pricing answer with the standard after-hours banner | `strict_ok=false` | `pass` | Good direct price answer; strict red is action/meta taxonomy drift only. |
| 2 | 1 | `Хочу записаться на маникюр` | Asks for date/time | `strict_ok=true` | `pass` | Booking opening remains correct; explicit service grounding stays closed. |
| 2 | 2 | `Есть ли акции?` | Promo answer | `strict_ok=true` | `pass` | Correct factual interrupt while preserving booking flow. |
| 2 | 3 | `Какая цена?` | Manicure pricing answer | `strict_ok=true` | `pass` | Correct pricing interrupt. |
| 2 | 4 | `Завтра в 15:00` | `Отлично, время подходит. Как вас зовут?` | `strict_ok=true` | `pass` | Matched datetime still continues booking correctly. |
| 2 | 5 | `Алина` | Transparent manager escalation | `strict_ok=true` | `pass` | Visible handoff remains product-acceptable after collected booking details. |
| 3 | 1 | `Позовите менеджера, пожалуйста` | Transparent manager handoff | `strict_ok=false` | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | 1 | `Каковы часы работы?` | Correct hours answer with after-hours banner | `strict_ok=false` | `pass` | Good factual answer; strict red is taxonomy drift only. |
| 5 | 1 | `Где находится салон?` | Address + hours | `strict_ok=false` | `weak` | Correct location answer, but still broader than needed. |
| 6 | 1 | `Есть ли у вас парковка?` | Address + hours, no parking fact | `strict_ok=false` | `fail` | The visible reply still misses the asked parking fact. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Accepts photo/reference and asks for the photo + brief | `strict_ok=true` | `pass` | Natural consult-first behavior; no collapse into generic booking collection. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | Explicit service grounding still holds. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks only for name or phone number | `strict_ok=true` | `pass` | The temporal clue is no longer re-asked; the missing identity/reference slot is collected directly. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | Repeats the identity-only prompt | `strict_ok=false` | `weak` | Still somewhat generic, but it no longer asks for time/date and stays on the correct missing identity slot. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible booking opening remains correct. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `pass` | Booking continuity remains correct through the covered flow. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good hours answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct but still broader than needed. |
| 6 | Parking fact | `fail` | Parking remains the only visible fail family on this replay. |
| 7 | Media prompt | `pass` | Natural consult/media handling on the visible path. |
| 8 | Second booking entry | `pass` | Explicit service grounding remains correct. |
| 9 | Check and confirm sequence | `weak` | The temporal-clue regression is gone; the follow-up is still generic, but product-acceptable. |
| 10 | Third booking entry | `pass` | Booking opening remains correct. |

## Family-level verdicts

### A. Closed for this block: live check-booking collect/fallback residue
- surfaced in `r30`: `dialog 9 / turns 1-2` re-asked temporal information even though the user had already grounded `на четверг`
- product-path RCA conclusion for the original family: `boundary_fallback_error`
- replay-evaluator RCA extension after `r31`: synthetic `confirm/calendar` tool hooks were being auto-emitted from `check_booking_prompt` reference-collect turns, which distorted the replay path; that secondary residue was `oracle_or_evaluator_error`
- fresh replay evidence on `r32g`:
  - `dialog 9 / turn 1` now replies `Чтобы проверить, перенести или отменить запись, подскажите имя или номер телефона.`
  - `dialog 9 / turn 1` trace keeps `llm_policy_core.temporal_scope=weekday`, `policy_core_guard.decision=collect_slot_order_collect_prompt`, and `question_contract.reason=calendar_get_booking_collect_reference`
  - `dialog 9 / turn 2` stays on `action=check_booking_prompt`, `source=booking_verification`, `expected_reply_type=name`
  - `dialog 9 / turns 1-2` show `tool_signals={}` and no synthetic tool-hook detour anymore
- deterministic evidence:
  - `truffles-api/tests/test_message_endpoint.py` covers the runtime boundary selector for weekday-grounded booking verification collect prompts
  - `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` now covers suppression of replay tool hooks for `check_booking_prompt` reference collection and the corresponding tool-evidence accounting
- verdict: `closed as scoped`; the live temporal-clue grounding / follow-up continuity regression is no longer the product blocker

### B. Open product blocker: parking fact composition regression
- surfaced by: `dialog 6 / turn 1`
- symptom: the visible reply still answers with location/hours instead of the asked parking fact
- status: `open`

### C. Secondary oracle/evaluator drift
- surfaced by: dialogs `1`, `3`, `4`, `5`, `9`
- symptom: otherwise human-pass/weak turns remain strict-red due action/meta taxonomy drift and judge overreach on acceptable identity-only booking-verification recovery
- status: `secondary`; not the product blocker for this block

### D. Residual technical debt, not current practical blocker: transparent-handoff commit residue
- `dialog 2 / turn 5` still ends in the same transparent handoff family
- visible behavior remains acceptable on this replay
- status: `trace-visible debt`; do not promote it above parking unless it becomes user-visible again

## Next actions
1. Treat `live check-booking collect/fallback residue` as closed for this block.
2. Open the next mechanism-first TP for `parking fact composition regression`, framed as `fact selection / fact composition`.
3. Keep the remaining `dialog 9` strict-red as oracle/evaluator drift unless it becomes user-visible again.
4. Keep the trace-visible booking handoff residue as technical debt, not as the next practical blocker.
