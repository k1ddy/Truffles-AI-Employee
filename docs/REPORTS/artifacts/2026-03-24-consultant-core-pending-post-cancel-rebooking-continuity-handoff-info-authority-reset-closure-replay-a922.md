# Consultant Core Pending Post Cancel Rebooking Continuity Handoff Info Authority Reset Closure Replay A922

## Result
- Closure status: failed truthfully; no runtime edits were made inside the replay block.
- Fresh closure replay: `/tmp/booking_quality/a922-go2f-seed19-r52`
- The prior structural block stayed valid as deterministic evidence, but live closure still failed on the same booking continuity family.

## Scope
- confirm runtime parity before replay
- run exactly one fresh closure replay on the locked `seed19` scenario set
- strict-audit the fresh artifact
- classify the surviving failure family without reopening replay-first mode

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r52 --status done --strict-artifacts` -> `pass`

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `r52` finished with `infra_valid=true`, `semantic_valid=false`, `dialogs=10`, `turns=143`, `turns_strict_failed=2`, and `strict_pass_rate=0.986`. | `/tmp/booking_quality/a922-go2f-seed19-r52/summary.json`, `/tmp/booking_quality/a922-go2f-seed19-r52/brief.md` |
| FACT | The only strict-failed rows are `LLM-QUAL-a922-go2f-seed19-r52-002-09-c14afa` and `LLM-QUAL-a922-go2f-seed19-r52-002-10-733e03`. | `/tmp/booking_quality/a922-go2f-seed19-r52/summary.json` |
| FACT | Row `002-09` still exits through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`. | `/tmp/booking_quality/a922-go2f-seed19-r52/responses.jsonl` |
| FACT | Row `002-10` still exits through `turn_planner.safe_info_fact.v1` instead of preserving booking continuity with `expected_reply_type=time`. | `/tmp/booking_quality/a922-go2f-seed19-r52/responses.jsonl`, `/tmp/booking_quality/a922-go2f-seed19-r52/scenarios.json` |
| FACT | The artifact still shows `44` executions of `turn_planner.safe_explicit_handoff_owner.v1`, including `24` rows with `reason_code=terminal_owner_unresolved`; `turn_planner.safe_info_fact.v1` executes `12` times. | `/tmp/booking_quality/a922-go2f-seed19-r52/responses.jsonl` |
| INFERENCE | The live overlap was still twofold: pending booking reentry could bypass canonical booking continuity before early handoff, and the service-grounded promotions tool-reply fast path still lost continuity writes on the normal path. | `/tmp/booking_quality/a922-go2f-seed19-r52/responses.jsonl`, `truffles-api/app/services/reasoning_core.py` pre-block mapping |
| UNKNOWN | Whether any further residual blocker remains behind rows `002-09` and `002-10` after those two seams are deleted or made unreachable. | no post-block replay exists yet |

## Failure Surface
### Row `002-09`
- user: `На какое время лучше записаться?`
- expected: `booking_prompt / collect / expected_reply_type=service_choice`
- actual: `escalate / handoff`
- owner_cutover: `turn_planner.safe_explicit_handoff_owner.v1`
- reason_code: `terminal_owner_unresolved`

### Row `002-10`
- user: `Есть ли какие-то акции на маникюр в следующем месяце?`
- expected: promotions answer while preserving booking continuity with `expected_reply_type=time`
- actual: promotions fact reply
- owner_cutover: `turn_planner.safe_info_fact.v1`
- reason_code: `promotions_question`

## Exact Current Authority Map At Closure Failure
1. The direct-owner chain still let pending booking reentry reach info and early explicit handoff before canonical booking continuity. Evidence from the pre-block code map: `truffles-api/app/services/reasoning_core.py:12155`, `truffles-api/app/services/reasoning_core.py:12169`, with pending continuity owners still later in the chain.
2. Service-grounded promotions on the booking interrupt path already used `catalog.service_query`, but the artifact fast path in `_finalize_turn_planner_owner_cutover(...)` did not apply continuity sync or booking payload persistence before send/save. That made `expected_reply_type=time` and the reactivated booking payload disappear from the touched normal path.
3. Once continuity was missing, row `002-09` could still fall into terminal explicit handoff and row `002-10` could still fall into `safe_info_fact`.

## Closure Decision
- Closure is rejected.
- The next honest move is one delete-first decision block, then one structural implementation block.
- Another replay before seam deletion would reopen the same symptom-loop.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r52/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r52/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r52/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r52/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r52/scenarios.json`
