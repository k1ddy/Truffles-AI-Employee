# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260330-r34d`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `r34d closes the scoped booking-verification confirm recovery family on the visible path, but the replay is human-semantic red because dialog 6 re-surfaces a parking miss with an irrelevant contact answer while location breadth and media/photo acknowledgement remain weak`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260330-r34d`

## Scope
Full turn-by-turn human semantic audit of replay `r34d` after the bounded invalid-schema booking-verification continuity fix.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 7 pass / 2 weak / 1 fail`, `turns 12 pass / 2 weak / 1 fail`
- family verdict: the scoped `booking verification confirm recovery under degraded invalid_schema` family is closed on the visible path
- conclusion: `the scoped booking-verification family is fixed, but current truth re-opens parking as the first clear product blocker, so practical/product closure remains open`

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
| 5 | 1 | `Где находится салон?` | Address + hours | `strict_ok=false` | `weak` | Correct location answer, but it is still broader than the asked fact. |
| 6 | 1 | `Есть ли у вас парковка?` | Contact/Instagram answer without parking fact | `strict_ok=false` | `fail` | This misses the asked parking fact and is the only clear product fail turn on the current truth. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Service clarification | `strict_ok=true` | `weak` | It moves the conversation forward, but it still does not explicitly acknowledge the media/photo offer. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | Explicit service grounding still holds. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks only for name or phone number | `strict_ok=true` | `pass` | The temporal clue stays grounded and the bot collects only the missing identity/reference slot. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | `Чтобы подтвердить запись, подскажите имя или номер телефона.` | `strict_ok=false` | `pass` | The degraded follow-up now preserves confirm-aware continuity on the same missing slot; strict red is stale scenario taxonomy, not product behavior. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible booking opening remains correct. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `pass` | Booking continuity remains correct through the covered flow. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good hours answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct, but still broader than needed. |
| 6 | Parking fact | `fail` | Current truth re-surfaces the parking miss with an irrelevant contact answer. |
| 7 | Media prompt | `weak` | Service-first clarification is acceptable, but it does not explicitly acknowledge the offered photo. |
| 8 | Second booking entry | `pass` | Explicit service grounding remains correct. |
| 9 | Check and confirm sequence | `pass` | Both turns stay on the correct missing identity/reference slot, and turn 2 is now confirm-aware. |
| 10 | Third booking entry | `pass` | Booking opening remains correct. |

## Family-level verdicts

### A. Closed for this block: booking verification confirm recovery under degraded invalid_schema
- surfaced in `r33`: `dialog 9 / turn 2` stayed on the right missing slot but repeated the generic `check` prompt under degraded `invalid_schema`
- RCA conclusion for the scoped family: `boundary_fallback_error`
- exact mechanism:
  - `question_contract` bypass on booking verification follow-up cleared the active expected reply
  - `llm_policy_core` failed with `policy_error:invalid_schema`
  - degraded collect re-entered booking verification without preserving confirm-vs-check mode
  - `_select_booking_verification_collect_prompt(...)` therefore chose a generic reference prompt
- bounded fix:
  - preserve `booking_verification_mode` across booking-verification bypass/degrade paths
  - let `_select_booking_verification_collect_prompt(...)` choose a confirm-aware identity/reference prompt when the follow-up mode is `confirm`
- deterministic evidence:
  - `truffles-api/tests/test_message_endpoint.py` now covers `test_invalid_schema_check_booking_confirm_followup_preserves_confirm_prompt_mode`
  - the broader booking-verification prompt set remains green under the targeted suite
- fresh replay evidence on `r34d`:
  - `dialog 9 / turn 2` now answers `Чтобы подтвердить запись, подскажите имя или номер телефона.`
  - `decision_meta.booking_verification_mode="confirm"`
  - `decision_meta.expected_reply_type="name"`
  - `decision_meta.policy_core_mode="degraded_fallback"`
  - `decision_meta.policy_core_degrade_reason="policy_error:invalid_schema"`
- verdict: `closed as scoped`

### B. Re-opened product blocker on current truth: parking fact composition regression
- surfaced on `r34d`:
  - `dialog 6 / turn 1`
- symptom:
  - a parking question receives an irrelevant contact/Instagram answer and omits the parking fact
- status:
  - `fail`
- note:
  - this block did not reopen parking RCA; it only records that the current truth re-surfaces the family and makes it the first product blocker again

### C. Open weak product residue: fact over-composition on location replies
- surfaced by:
  - `dialog 5 / turn 1`
- symptom:
  - correct location answer still carries broader-than-needed adjacent context
- status:
  - `weak`

### D. Open weak product residue: media/photo clarification remains service-first
- surfaced by:
  - `dialog 7 / turn 1`
- symptom:
  - the bot clarifies service but does not explicitly acknowledge the offered photo/media cue
- status:
  - `weak`

### E. Secondary oracle/evaluator drift
- surfaced by:
  - dialogs `1`, `3`, `4`, `5`, `9`
- symptom:
  - otherwise acceptable visible turns remain strict-red because of action/meta taxonomy drift and judge disagreement
- status:
  - `secondary`; do not treat this as proof of a new product blocker family

## Next actions
1. Treat `booking verification confirm recovery under degraded invalid_schema` as closed for this block.
2. Update current practical truth to `r34d` and explicitly record that parking is the first product blocker again.
3. If continuing product work, start the next mechanism-first block from `parking fact composition regression` using `manual_audit_workspace.*`, `family_registry.json`, `judge_conflicts.jsonl`, and `llm-quality-trends`.
4. Keep oracle/evaluator drift separate from product-path closure decisions.
