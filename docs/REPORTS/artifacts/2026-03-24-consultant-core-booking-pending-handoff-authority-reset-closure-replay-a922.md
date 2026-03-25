# Consultant Core Booking Pending Handoff Authority Reset Closure Replay A922

## Result
- Closure status: failed truthfully; no new runtime edits were made in this block.
- Fresh closure replay: `/tmp/booking_quality/a922-go2f-seed19-r49`
- Non-canonical preflight artifact: `/tmp/booking_quality/a922-go2f-seed19-r48`

## Scope
- audit the frozen `r47` artifact
- resolve the invalid preflight debt on `r48`
- run exactly one fresh local replay on runtime parity
- classify the result without starting a new runtime fix inside the closure block

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r47 --status done --strict-artifacts` -> `pass`
- `curl -fsS http://127.0.0.1:18186/admin/version` -> `git_commit=0d8d2078697193832a2d6cae6709a2d7489bf9ca` (matched worktree `HEAD`)
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r48 --status done --strict-artifacts` -> audited as non-canonical invalid preflight artifact
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 ... --output-dir /tmp/booking_quality/a922-go2f-seed19-r49 --run-id a922-go2f-seed19-r49 ...` -> completed
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r49 --status done --strict-artifacts` -> `pass`

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `r47` is audited and remains non-canonical forensic evidence only. | `/tmp/booking_quality/a922-go2f-seed19-r47/manual_audit.json` |
| FACT | `r48` is not closure: it failed `invalid_runtime_fingerprint_preflight`, then was manually audited as non-canonical. | `/tmp/booking_quality/a922-go2f-seed19-r48/manual_audit.json` |
| FACT | `r49` is the first fresh closure replay after the structural block; it finished with `infra_valid=true`, `semantic_valid=false`, `responses_rows=143`, `dialogs_seen=10/10`, `strict_pass_rate=0.986`. | `/tmp/booking_quality/a922-go2f-seed19-r49/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r49/manual_audit.json` |
| FACT | `r49` failed semantic closure on `blocking_reason` + `threshold_breach`; the threshold breach is `degraded_fallback_rate`. | `/tmp/booking_quality/a922-go2f-seed19-r49/summary.json` |
| FACT | The only strict-failed turns are `LLM-QUAL-a922-go2f-seed19-r49-002-09-489e4e` and `LLM-QUAL-a922-go2f-seed19-r49-002-10-674439`. | `/tmp/booking_quality/a922-go2f-seed19-r49/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r49/brief.md` |
| FACT | Turn `002-09` exited through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved` while the scenario still expected `booking_prompt / collect / expected_reply_type=service_choice`. | `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl` |
| FACT | Turn `002-10` exited through `turn_planner.safe_info_fact.v1` with a promotions fact reply while the scenario still expected booking continuity `expected_reply_type=time`. | `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl` |
| FACT | `r49` still contains `40` executions of `turn_planner.safe_explicit_handoff_owner.v1`, including `24` rows with `reason_code=terminal_owner_unresolved`. | `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl` |
| INFERENCE | The structural block did not make the old explicit-handoff seam unreachable for the broader pending booking/check/cancel/resume family; the seam is still live on the normal runtime path. | `truffles-api/app/services/reasoning_core.py:13245`, `truffles-api/app/services/reasoning_core.py:13257`, plus `r49` artifact facts |
| INFERENCE | Turn `002-10` is not an independent info bug; it is a booking continuity-loss continuation, because live `safe_info_fact` only self-suppresses when `conversation_snapshot.booking_active` and `reply_slot in {service,time}` are still present. | `truffles-api/app/services/reasoning_core.py:6065`, `truffles-api/app/services/reasoning_core.py:6081`, `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl` |
| UNKNOWN | Whether all `24` `terminal_owner_unresolved` rows collapse into one executable pending-continuity family or split into multiple subfamilies after exact code mapping. | needs the next delete-first decision block |

## Failure Surface
### Turn `002-09`
- user: `На какое время лучше записаться?`
- expected: `booking_prompt / collect / expected_reply_type=service_choice`
- actual: `escalate / handoff`
- reason_code: `terminal_owner_unresolved`
- owner_cutover: `turn_planner.safe_explicit_handoff_owner.v1`
- current runtime seam:
  - terminal unresolved reason constant: `truffles-api/app/services/reasoning_core.py:132`
  - explicit handoff owner handler: `truffles-api/app/services/reasoning_core.py:5787`
  - terminal fallback snapshot build: `truffles-api/app/services/reasoning_core.py:13245`
  - terminal explicit handoff cutover call: `truffles-api/app/services/reasoning_core.py:13257`

### Turn `002-10`
- user: `Есть ли какие-то акции на маникюр в следующем месяце?`
- expected: booking progression still active with `expected_reply_type=time`
- actual: promotions fact reply
- reason_code: `promotions_question`
- owner_cutover: `turn_planner.safe_info_fact.v1`
- current runtime seam:
  - live info fact owner: `truffles-api/app/services/reasoning_core.py:6065`
  - booking-continuity suppression guard: `truffles-api/app/services/reasoning_core.py:6081`
  - central expected-reply writer still lives on the allowed path: `truffles-api/app/routers/webhook/context_manager.py:292`, `truffles-api/app/core/dialog_state_service.py:872`

## Exact Current Authority Map
1. Main runtime still builds direct owner responses in `truffles-api/app/services/reasoning_core.py:12992` through `truffles-api/app/services/reasoning_core.py:13257`.
2. Pending booking family owners sit after the early handoff path: `booking_verification` at `truffles-api/app/services/reasoning_core.py:13164`, `check_booking_prompt` at `truffles-api/app/services/reasoning_core.py:13177`, `specialist_followup` at `truffles-api/app/services/reasoning_core.py:13190`, `booking_prompt_owner` at `truffles-api/app/services/reasoning_core.py:13203`.
3. If none of those owners return a reply, the runtime materializes `PolicyCoreRouteSnapshot(... reason='terminal_owner_unresolved' ...)` at `truffles-api/app/services/reasoning_core.py:13245` and immediately re-enters `turn_planner.safe_explicit_handoff_owner.v1` at `truffles-api/app/services/reasoning_core.py:13257`.
4. On later info turns, `turn_planner.safe_info_fact.v1` at `truffles-api/app/services/reasoning_core.py:6065` only defers if `conversation_snapshot.booking_active` and the reply slot is still `service` or `time`; once continuity is missing, info fact becomes the normal path.

## Closure Decision
- Closure is rejected.
- The next honest move is not replay and not another local patch in `reasoning_core.py`.
- The next honest move is one delete-first authority decision block for the broader pending booking continuity / terminal handoff family, then one structural implementation block.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r47/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r48/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r49/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r49/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r49/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/core/dialog_state_service.py`
