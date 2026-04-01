# Consultant Core Pending Booking Continuity Info Handoff Authority Reset Closure Replay A922

## Result
- Closure status: failed truthfully; no new runtime edits were made in this block.
- Fresh closure replay: `/tmp/booking_quality/a922-go2f-seed19-r51`
- Prior structural evidence remains valid, but it did not make the live post-cancel rebooking family converge.

## Scope
- confirm runtime parity before replay
- run exactly one fresh closure replay on the locked `seed19` scenario set
- audit the fresh artifact with strict artifact validation
- classify the surviving failure family without reopening runtime edits inside the closure block

## Checks
- `curl -fsS http://127.0.0.1:18186/admin/version` -> `git_commit=0d8d2078697193832a2d6cae6709a2d7489bf9ca` (matched worktree `HEAD`)
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 ... --output-dir /tmp/booking_quality/a922-go2f-seed19-r51 --run-id a922-go2f-seed19-r51 ...` -> completed
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r51 --status done --strict-artifacts` -> `pass`

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `r51` is the first fresh closure replay after the pending booking continuity info/handoff structural block; it finished with `infra_valid=true`, `semantic_valid=false`, `turns=143`, and `strict_pass_rate=0.986`. | `/tmp/booking_quality/a922-go2f-seed19-r51/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r51/brief.md` |
| FACT | The only strict-failed turns remain dialog `2` turn `9` and turn `10`: `LLM-QUAL-a922-go2f-seed19-r51-002-09-c838ba` and `LLM-QUAL-a922-go2f-seed19-r51-002-10-b85502`. | `/tmp/booking_quality/a922-go2f-seed19-r51/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r51/brief.md` |
| FACT | Live continuity already collapses one turn earlier: dialog `2` turn `8` (`Когда я могу записаться снова?`) stays in `pending` and routes through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=semantic_arbitration_needs_manager`, while `current_goal` and `expected_reply_type` are absent. | `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl` |
| FACT | Turn `002-09` still exits through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved` instead of reactivating booking collect continuity. | `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl` |
| FACT | Turn `002-10` still exits through `turn_planner.safe_info_fact.v1` with `reason_code=promotions_question`, and the expected booking reply contract `time` is missing. | `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl`, `/tmp/booking_quality/a922-go2f-seed19-r51/scenarios.json` |
| FACT | `r51` still contains `40` executions of `turn_planner.safe_explicit_handoff_owner.v1`, including `23` rows with `reason_code=terminal_owner_unresolved`. | `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl` |
| FACT | The run still breaches `degraded_fallback_rate=1.0` on two strict-green initial booking rows: `LLM-QUAL-a922-go2f-seed19-r51-006-01-68ccdd` and `LLM-QUAL-a922-go2f-seed19-r51-008-01-749dfd`. | `/tmp/booking_quality/a922-go2f-seed19-r51/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl` |
| INFERENCE | The structural block did not make pending post-cancel rebooking continuity executable before semantic handoff, terminal handoff, and later info fallback. | `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl`, `truffles-api/app/services/reasoning_core.py:8173`, `truffles-api/app/services/reasoning_core.py:9938`, `truffles-api/app/services/reasoning_core.py:12849` |
| UNKNOWN | Whether the continuity gap is entirely a missing live booking-state/current-goal projection on turn `002-08`, or whether a second owner gate inside the booking reactivation stack is also rejecting the family after projection. | needs exact delete-first code mapping in the next decision block |

## Failure Surface
### Turn `002-08` — first live continuity collapse indicator
- user: `Когда я могу записаться снова?`
- actual: `turn_planner.safe_explicit_handoff_owner.v1`
- reason_code: `semantic_arbitration_needs_manager`
- conversation_state: `pending`
- live contract loss visible in artifact:
  - `decision_meta.expected_reply_type = null`
  - `decision_meta.expected_reply_reason = null`
  - `decision_meta.current_goal = null`

### Turn `002-09`
- user: `На какое время лучше записаться?`
- expected: `booking_prompt / collect / expected_reply_type=service_choice`
- actual: `escalate / handoff`
- owner_cutover: `turn_planner.safe_explicit_handoff_owner.v1`
- reason_code: `terminal_owner_unresolved`

### Turn `002-10`
- user: `Есть ли какие-то акции на маникюр в следующем месяце?`
- expected: booking progression still active with `expected_reply_type=time`
- actual: promotions fact reply
- owner_cutover: `turn_planner.safe_info_fact.v1`
- reason_code: `promotions_question`

## Exact Current Authority Map
1. The post-cancel rebooking turn enters the live path in `pending` without projected booking contract, so the artifact already shows `current_goal=None` and no expected reply before the family re-enters handoff. Evidence: `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl`.
2. `safe_check_booking_prompt_owner` only activates for verification-like text at `truffles-api/app/services/reasoning_core.py:8173`-`truffles-api/app/services/reasoning_core.py:8181`, so turn `002-08` never uses that owner.
3. `safe_booking_prompt_owner` can only reactivate collect continuity after it gets enough booking seed/context to build a pending reactivation candidate; the live family still returns `None` before semantic handoff. Evidence: `truffles-api/app/services/reasoning_core.py:7081`-`truffles-api/app/services/reasoning_core.py:7096`, `truffles-api/app/core/booking_prompt_owner.py:94`, `truffles-api/app/core/booking_prompt_owner.py:500`.
4. Semantic arbitration still routes `needs_manager` turns straight into explicit handoff at `truffles-api/app/services/reasoning_core.py:9938`-`truffles-api/app/services/reasoning_core.py:9960`.
5. If continuity still does not reactivate, terminal unresolved explicit handoff remains reachable at `truffles-api/app/services/reasoning_core.py:12849`-`truffles-api/app/services/reasoning_core.py:12875`.
6. Once the question contract is gone, `safe_info_fact` remains executable on the next promo turn at `truffles-api/app/services/reasoning_core.py:5641`-`truffles-api/app/services/reasoning_core.py:5667` and from the main direct-owner chain at `truffles-api/app/services/reasoning_core.py:12569`-`truffles-api/app/services/reasoning_core.py:12580`.

## Closure Decision
- Closure is rejected.
- The next honest move is not another replay and not another hotspot patch inside `reasoning_core.py`.
- The next honest move is one delete-first authority decision block for the pending post-cancel rebooking continuity / handoff / info family, then one structural implementation block.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r51/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r51/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r51/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r51/scenarios.json`
- `/tmp/booking_quality/a922-go2f-seed19-r51/failure_families.json`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
