# Consultant Core Pending Booking Continuity Terminal Handoff Authority Reset Closure Replay A922

## Result
- Closure status: failed truthfully; no new runtime edits were made in this block.
- Fresh closure replay: `/tmp/booking_quality/a922-go2f-seed19-r50`
- Strict audit: `/tmp/booking_quality/a922-go2f-seed19-r50/manual_audit.json`

## Scope
- verify runtime parity on `http://127.0.0.1:18186`
- rerun mandatory guards for the active structural block
- run exactly one fresh guarded replay on the locked `seed19` scenarios and baseline
- audit and classify the result without reopening runtime implementation inside the closure block

## Checks
- `curl -fsS http://127.0.0.1:18186/admin/health` -> `pass`
- `curl -fsS http://127.0.0.1:18186/admin/version` -> `git_commit=0d8d2078697193832a2d6cae6709a2d7489bf9ca` (matched worktree `HEAD`)
- `python3 scripts/semantic_bridge_growth_guard.py` -> `semantic_bridge_growth_guard: OK`
- `python3 scripts/continuity_writer_guard.py` -> `continuity_writer_guard: OK`
- `python3 scripts/legacy_freeze_guard.py` -> `legacy_freeze_guard: OK`
- `python3 scripts/arch_guard.py` -> `arch_guard: OK`
- `pytest -q truffles-api/tests/architecture` -> `19 passed`
- `SESSION_AGENT=a922 scripts/session_check.sh` -> `Session OK`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-go2f-seed19-r50 ...` -> completed
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r50 --status done --strict-artifacts` -> `pass`

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `r50` is the single fresh closure replay after the pending booking continuity / terminal handoff structural reset; it finished with `infra_valid=true`, `semantic_valid=false`, `dialogs=10/10`, `turns=143`, `strict_pass_rate=0.986`, and `governance_closure.valid=false`. | `/tmp/booking_quality/a922-go2f-seed19-r50/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r50/brief.md`, `/tmp/booking_quality/a922-go2f-seed19-r50/manual_audit.json` |
| FACT | The only strict-failed turns are `LLM-QUAL-a922-go2f-seed19-r50-002-09-48c6ab` and `LLM-QUAL-a922-go2f-seed19-r50-002-10-4439b1`. | `/tmp/booking_quality/a922-go2f-seed19-r50/runtime_state.json`, `/tmp/booking_quality/a922-go2f-seed19-r50/summary.json` |
| FACT | Turn `002-09` (`На какое время лучше записаться?`) still exits through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`, while the scenario still expects `booking_prompt / collect / expected_reply_type=service_choice`. | `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl`, `/tmp/booking_quality/a922-go2f-seed19-r50/trace_bundle.jsonl` |
| FACT | Turn `002-10` (`Есть ли какие-то акции на маникюр в следующем месяце?`) still exits through `turn_planner.safe_info_fact.v1` with a promotions fact reply, while the scenario still expects booking continuity with `expected_reply_type=time`. | `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl`, `/tmp/booking_quality/a922-go2f-seed19-r50/trace_bundle.jsonl` |
| FACT | `r50` still contains `40` executions of `turn_planner.safe_explicit_handoff_owner.v1`, including `24` rows with `reason_code=terminal_owner_unresolved`. | `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl` |
| FACT | The live main chain still executes `safe_info_fact` at `truffles-api/app/services/reasoning_core.py:12596` and early explicit handoff at `truffles-api/app/services/reasoning_core.py:12609` before pending continuity owners at `truffles-api/app/services/reasoning_core.py:12781`, `truffles-api/app/services/reasoning_core.py:12794`, `truffles-api/app/services/reasoning_core.py:12807`, and `truffles-api/app/services/reasoning_core.py:12820`. | `truffles-api/app/services/reasoning_core.py:12596`, `truffles-api/app/services/reasoning_core.py:12609`, `truffles-api/app/services/reasoning_core.py:12781`, `truffles-api/app/services/reasoning_core.py:12794`, `truffles-api/app/services/reasoning_core.py:12807`, `truffles-api/app/services/reasoning_core.py:12820` |
| FACT | If those owners all return `None`, the runtime still builds `terminal_handoff_snapshot` at `truffles-api/app/services/reasoning_core.py:12862` and re-enters `turn_planner.safe_explicit_handoff_owner.v1` at `truffles-api/app/services/reasoning_core.py:12874`. | `truffles-api/app/services/reasoning_core.py:12862`, `truffles-api/app/services/reasoning_core.py:12874` |
| FACT | `safe_info_fact` only self-suppresses when `conversation_snapshot.booking_active` and `reply_slot in {service,time}` are both still present at `truffles-api/app/services/reasoning_core.py:5697`-`truffles-api/app/services/reasoning_core.py:5704`; it does not consult the centralized pending booking boundary payload. | `truffles-api/app/services/reasoning_core.py:5682`, `truffles-api/app/services/reasoning_core.py:5697`, `truffles-api/app/core/booking_prompt_owner.py:500`, `truffles-api/app/core/dialog_state_service.py:1323` |
| FACT | The canonical pending booking reactivation seam exists, but it only becomes active when the runtime reaches `truffles-api/app/services/reasoning_core.py:12820` -> `truffles-api/app/services/reasoning_core.py:7059` -> `truffles-api/app/core/booking_prompt_owner.py:500`. | `truffles-api/app/services/reasoning_core.py:12820`, `truffles-api/app/services/reasoning_core.py:7059`, `truffles-api/app/core/booking_prompt_owner.py:500` |
| FACT | Turn-planner finalize still writes expected-reply state through legacy `context_manager_router._set_expected_reply_context(...)` at `truffles-api/app/services/reasoning_core.py:5132` and `truffles-api/app/services/reasoning_core.py:5154` before `DialogStateService.build_collect_owner_state(...)` runs at `truffles-api/app/services/reasoning_core.py:5146`. | `truffles-api/app/services/reasoning_core.py:4909`, `truffles-api/app/services/reasoning_core.py:5132`, `truffles-api/app/services/reasoning_core.py:5146`, `truffles-api/app/services/reasoning_core.py:5154` |
| FACT | The strict audit records `judge_alignment='conflicted'`, `winner='contract'`, and `conflict_count=24`; this remains advisory proof debt and does not change the runtime closure failure. | `/tmp/booking_quality/a922-go2f-seed19-r50/manual_audit.json` |
| INFERENCE | The structural reset improved the canonical pending reactivation seam, but it did not make the old info/handoff authority seams unreachable for the broader pending booking continuity family. | `truffles-api/app/core/booking_prompt_owner.py:500`, `truffles-api/app/services/reasoning_core.py:12596`, `truffles-api/app/services/reasoning_core.py:12609`, `truffles-api/app/services/reasoning_core.py:12862`, `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl` |
| INFERENCE | Turn `002-10` is a continuity-loss continuation of the same touched family, not an independent info bug, because `safe_info_fact` still runs before the canonical booking continuity owner and only defers on a narrow snapshot gate. | `truffles-api/app/services/reasoning_core.py:12596`, `truffles-api/app/services/reasoning_core.py:12820`, `truffles-api/app/services/reasoning_core.py:5697`, `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl` |
| UNKNOWN | Whether turn `002-09` entered `turn_planner.safe_explicit_handoff_owner.v1` from the early owner call at `truffles-api/app/services/reasoning_core.py:12609` or from the terminal fallback edge at `truffles-api/app/services/reasoning_core.py:12874` is not directly observable from the closure artifact. | `/tmp/booking_quality/a922-go2f-seed19-r50/trace_bundle.jsonl`, `truffles-api/app/services/reasoning_core.py:12609`, `truffles-api/app/services/reasoning_core.py:12874` |
| UNKNOWN | Whether turn `002-10` slipped through because `conversation_snapshot.reply_slot` was unset, `conversation_snapshot.booking_active` was false, or both, is runtime-state dependent and not directly exposed by the closure artifact. | `/tmp/booking_quality/a922-go2f-seed19-r50/trace_bundle.jsonl`, `truffles-api/app/services/reasoning_core.py:5697` |

## Failure Surface
### Turn `002-09`
- user: `На какое время лучше записаться?`
- expected: `booking_prompt / collect / expected_reply_type=service_choice`
- actual: `escalate / handoff`
- reason_code: `terminal_owner_unresolved`
- owner_cutover: `turn_planner.safe_explicit_handoff_owner.v1`
- last trace stage: `turn_planner_safe_explicit_handoff_owner`

### Turn `002-10`
- user: `Есть ли какие-то акции на маникюр в следующем месяце?`
- expected: booking continuity still active with `expected_reply_type=time`
- actual: promotions fact reply
- reason_code: `promotions_question`
- owner_cutover: `turn_planner.safe_info_fact.v1`
- last trace stage: `turn_planner_safe_info_fact`

## Exact Current Authority Map
1. The live runtime still tries `safe_info_fact` at `truffles-api/app/services/reasoning_core.py:12596` and early explicit handoff at `truffles-api/app/services/reasoning_core.py:12609` before `pending_ack` and before the pending booking continuity owners.
2. The pending booking continuity owner stack sits later in the chain: `booking_verification` at `truffles-api/app/services/reasoning_core.py:12781`, `check_booking_prompt` at `truffles-api/app/services/reasoning_core.py:12794`, `specialist_followup` at `truffles-api/app/services/reasoning_core.py:12807`, and `booking_prompt_owner` at `truffles-api/app/services/reasoning_core.py:12820`.
3. The canonical pending reactivation seed exists only inside `truffles-api/app/core/booking_prompt_owner.py:500`, which delegates to the canonical LLM booking owner after `truffles-api/app/core/booking_prompt_owner.py:94` restores boundary data from `DialogStateService.derive_pending_booking_resume_boundary_payload(...)`.
4. If the later owners still return `None`, the runtime builds `terminal_handoff_snapshot` at `truffles-api/app/services/reasoning_core.py:12862` and re-enters `turn_planner.safe_explicit_handoff_owner.v1` at `truffles-api/app/services/reasoning_core.py:12874`.
5. On follow-up info turns, `safe_info_fact` at `truffles-api/app/services/reasoning_core.py:5682` only self-suppresses when the narrow `conversation_snapshot.booking_active + reply_slot in {service,time}` gate at `truffles-api/app/services/reasoning_core.py:5697`-`truffles-api/app/services/reasoning_core.py:5704` still holds.
6. Continuity writes are still split in finalize: legacy context-manager expected-reply writes run at `truffles-api/app/services/reasoning_core.py:5132` / `truffles-api/app/services/reasoning_core.py:5154`, while `DialogStateService.build_collect_owner_state(...)` only follows at `truffles-api/app/services/reasoning_core.py:5146`.

## Closure Decision
- Closure is rejected.
- The next honest move is one delete-first authority decision block for pending booking continuity / info / handoff, then one structural implementation block.
- The next honest move is not another replay and not another local semantic branch in `truffles-api/app/services/reasoning_core.py`.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r50/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r50/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r50/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r50/trace_bundle.jsonl`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/core/dialog_state_service.py`
