# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260330-r35f`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `r35f closes the re-opened parking owner-grounding family on the visible path, but the replay remains human-semantic amber because location and parking replies are still broader than needed while the deterministic contract lane stays red on secondary oracle/validation residue`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260330-r35f`

## Scope
Full turn-by-turn human semantic audit of replay `r35f` after the bounded owner-contract fix for branch-fact grounding specificity.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 8 pass / 2 weak / 0 fail`, `turns 13 pass / 2 weak / 0 fail`
- family verdict: the re-opened `parking owner-grounding` family is closed on the visible path; the remaining visible product residue is over-composition on location/parking replies, not a parking miss
- conclusion: `no clear human-semantic fail turns remain, but practical/product closure stays open because the replay is still amber and the deterministic contract lane remains red`

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
| 6 | 1 | `Есть ли у вас парковка?` | Parking answer that also carries address + hours | `strict_ok=false` | `weak` | The asked parking fact is back on the visible path, but the reply still over-composes adjacent branch facts. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Explicitly accepts photo/reference and asks for the photo + request | `strict_ok=true` | `pass` | The bot now acknowledges the offered photo directly and keeps the consult path natural. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | Explicit service grounding still holds. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks only for name or phone number | `strict_ok=true` | `pass` | The temporal clue stays grounded and the bot collects only the missing identity/reference slot. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | `Чтобы подтвердить запись, подскажите имя или номер телефона.` | `strict_ok=false` | `pass` | The visible reply is confirm-aware and stays on the same missing slot; strict red comes from secondary contract override residue, not visible product behavior. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible booking opening remains correct. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `pass` | Booking continuity remains correct through the covered flow. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good hours answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct, but still broader than needed. |
| 6 | Parking fact | `weak` | Parking is answered again, but the reply still carries adjacent address/hours content. |
| 7 | Media prompt | `pass` | The bot now explicitly acknowledges the offered photo/reference. |
| 8 | Second booking entry | `pass` | Explicit service grounding remains correct. |
| 9 | Check and confirm sequence | `pass` | Both turns stay on the correct missing identity/reference slot; turn 2 is confirm-aware on the visible path. |
| 10 | Third booking entry | `pass` | Booking opening remains correct. |

## Family-level verdicts

### A. Closed for this block: re-opened parking owner-grounding family
- surfaced in `r34d`: `dialog 6 / turn 1` answered a parking question with contact/Instagram and omitted the parking fact
- RCA conclusion for the scoped family: `owner_error`
- exact mechanism:
  - `branch fact grounding specificity`
- exact root cause:
  - the active policy-core owner contract under-specified branch-fact specificity, so an explicit parking question could emit a valid `info` payload with sibling `pack_refs=["contact"]`; runtime then preserved that wrong owner meaning unchanged into the final reply
- bounded fix:
  - strengthen the owner prompt/fallback contract so that when one explicit concrete branch fact is requested, owner must keep that fact in `pack_refs` and must not substitute a sibling branch fact unless the user also asked for it
- deterministic evidence:
  - `truffles-api/tests/test_intent.py` now covers `test_policy_core_prompt_branch_fact_specificity_contract`
  - the bounded prompt/fallback sync remains green under the targeted prompt-contract suite
- fresh replay evidence on `r35f`:
  - `dialog 6 / turn 1` owner output now grounds `intent="parking"`, `pack_refs=["parking"]`, `resolution_mode="policy_fact"`
  - the visible reply now includes `Парковка: Бесплатная парковка во дворе, обычно 5–6 мест.`
- verdict: `closed as scoped`

### B. Open weak product residue: fact over-composition on location/parking replies
- surfaced by:
  - `dialog 5 / turn 1`
  - `dialog 6 / turn 1`
- symptom:
  - the asked fact is answered, but the visible reply still carries broader adjacent branch facts than the user requested
- mechanism:
  - `fact selection / fact composition`
- status:
  - `weak`
- note:
  - this is now the first visible mechanism-level product residue on the current truth

### C. Secondary contract residue: booking verification confirm follow-up override
- surfaced by:
  - `dialog 9 / turn 2`
- symptom:
  - owner still plans `handoff`, validation raises `handoff_not_allowed`, and the boundary overrides the turn into a collect prompt even though the visible reply is acceptable
- status:
  - `secondary`
- note:
  - keep this separate from product-path blocker claims while the visible reply remains confirm-aware and useful

### D. Secondary oracle/evaluator drift
- surfaced by:
  - dialogs `1`, `3`, `4`, `5`, `6`, `9`
- symptom:
  - otherwise acceptable visible turns remain strict-red because of action/meta taxonomy drift and judge disagreement
- status:
  - `secondary`; do not treat this as proof of a new product blocker family

## Next actions
1. Treat the re-opened `parking owner-grounding` family as closed for this block.
2. Update current practical truth to `r35f` and record that there are no visible fail turns, but practical/product closure remains open because the run is still human-semantic amber and deterministic contract-red.
3. If continuing product work, start the next mechanism-first block from `fact over-composition on location/parking replies`.
4. Keep `dialog 9 / turn 2` contract residue and the broader oracle/evaluator drift separate from product-path closure decisions.
