# LLM Quality Manual Audit

- run_id: `a922-practical-proof-20260330-r33`
- analyst: `a922`
- status: `done`
- human_semantic_valid: `false`
- human_semantic_summary: `r33 closes parking fact composition on the visible path; the replay has no outright human-semantic fail turns, but it remains human-semantic amber because some fact answers are still broader than needed, the media/photo clarification is service-first, and the check-booking confirm follow-up stays generic under degraded invalid_schema`
- run_dir: `/tmp/booking_quality/a922-practical-proof-20260330-r33`

## Scope
Full turn-by-turn human semantic audit of replay `r33` after the bounded parking fact-composition fix on the policy-info -> info-class handoff.

## Executive verdict
- tooling verdict: `infra_valid=true`, `semantic_valid=false`
- human verdict: `dialogs 6 pass / 4 weak / 0 fail`, `turns 11 pass / 4 weak / 0 fail`
- family verdict: the scoped `parking fact composition regression` family is closed on the visible product path
- conclusion: `parking is no longer the practical blocker, but the lane is still not practically closed because the visible product path remains weak in several places and the deterministic contract lane is still red`

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
| 6 | 1 | `Есть ли у вас парковка?` | Address + hours + parking | `strict_ok=false` | `weak` | The parking fact is now present, so the fail family is closed; the answer is still somewhat over-composed. |
| 7 | 1 | `Я могу прислать фото своих ногтей.` | Service clarification | `strict_ok=true` | `weak` | It moves the conversation forward, but it does not explicitly acknowledge the media/photo offer. |
| 8 | 1 | `Хочу записаться на педикюр` | Asks for date/time | `strict_ok=true` | `pass` | Explicit service grounding still holds. |
| 9 | 1 | `Проверьте мою запись на четверг.` | Asks only for name or phone number | `strict_ok=true` | `pass` | The temporal clue is preserved and the bot collects only the missing identity/reference slot. |
| 9 | 2 | `Подтвердите, пожалуйста, мою запись на четверг.` | Repeats the identity-only prompt | `strict_ok=false` | `weak` | It stays on the right missing slot, but the confirmation follow-up is still generic and comes from degraded fallback. |
| 10 | 1 | `Хочу записаться на стрижку` | Asks for date/time | `strict_ok=true` | `pass` | Visible booking opening remains correct. |

## Dialog-level verdicts
| Dialog | Goal | Verdict | Notes |
|---|---|---|---|
| 1 | Simple fact price | `pass` | Good answer; strict red is oracle/action drift. |
| 2 | Booking with info interrupts and completion | `pass` | Booking continuity remains correct through the covered flow. |
| 3 | Explicit human handoff | `pass` | Correct handoff; strict red is taxonomy drift only. |
| 4 | Hours fact | `pass` | Good hours answer; strict red is taxonomy drift only. |
| 5 | Location fact | `weak` | Correct, but still broader than needed. |
| 6 | Parking fact | `weak` | Parking is now answered directly, but the response still bundles extra location/hours context. |
| 7 | Media prompt | `weak` | Service-first clarification is acceptable, but it does not explicitly acknowledge the offered photo. |
| 8 | Second booking entry | `pass` | Explicit service grounding remains correct. |
| 9 | Check and confirm sequence | `weak` | The temporal-clue regression stays closed, but the confirm follow-up remains generic under degraded fallback. |
| 10 | Third booking entry | `pass` | Booking opening remains correct. |

## Family-level verdicts

### A. Closed for this block: parking fact composition regression
- surfaced in `r32g`: `dialog 6 / turn 1` answered a parking question with location/hours only
- RCA conclusion for the scoped family: `fact_composition_error`
- exact mechanism:
  - owner grounded `pack_refs=["parking"]`
  - policy-info handoff delegated into `info_class` with empty `info_class_meta`
  - downstream composition lost `info_signals["parking"]`
  - the visible reply fell back to the default location/hours bundle
- bounded fix:
  - preserve owner-grounded info-section signals when `policy_tool_action=info` delegates into `info_class`
- deterministic evidence:
  - `truffles-api/tests/test_message_endpoint.py` now covers `_build_policy_info_class_meta(...)`
  - `truffles-api/tests/test_message_endpoint.py` now covers the policy-info -> info-class handoff preserving `info_signals["parking"]=true`
  - existing parking hint tests remain green
- fresh replay evidence on `r33`:
  - `dialog 6 / turn 1` now answers with `... Парковка: Бесплатная парковка во дворе, обычно 5–6 мест.`
  - `decision_meta.info_sections=["address","hours","parking"]`
  - `decision_meta.fact_refs=["address","hours","parking"]`
- verdict: `closed as scoped`

### B. Open weak product residue: fact over-composition on info replies
- surfaced by:
  - `dialog 5 / turn 1`
  - `dialog 6 / turn 1`
- symptom:
  - correct fact answers still carry broader-than-needed adjacent sections (`hours`, extra location context)
- status:
  - `weak`, not an outright product fail family

### C. Open weak product residue: media/photo clarification remains service-first
- surfaced by:
  - `dialog 7 / turn 1`
- symptom:
  - the bot clarifies service but does not explicitly acknowledge the offered photo/media cue
- status:
  - `weak`

### D. Open weak product residue: booking verification confirm recovery under degraded invalid_schema
- surfaced by:
  - `dialog 9 / turn 2`
- symptom:
  - the response stays on the correct missing identity/reference slot, but the confirm follow-up is still generic and comes from degraded fallback rather than a cleaner confirmation-aware recovery
- status:
  - `weak`

### E. Secondary oracle/evaluator drift
- surfaced by: dialogs `1`, `3`, `4`, `5`, `6`, `9`
- symptom:
  - otherwise acceptable visible turns remain strict-red due action/meta taxonomy mismatch and judge disagreement
- status:
  - `secondary`; do not treat this as proof of a new product blocker family

## Next actions
1. Treat `parking fact composition regression` as closed for this block.
2. Update current practical truth to `r33` with explicit `parking closed` language and explicit weak residual families.
3. If continuing product work, take the next mechanism-first block as `booking verification confirm recovery under degraded invalid_schema`.
4. Keep oracle/evaluator drift separate from product-path closure decisions.
