# 2026-02-21 Firebreak Human Quality Wave HQ1

## Status
- verdict: `NO_GO`
- date: `2026-02-21`
- canonical scenarios: `/tmp/booking_quality/blocking_scenarios_human.json`
- note: L2 (`judge-mode critical`) was executed as diagnostics even though L1 was already red.

## Evidence Sources
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1-r1/summary.json`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1-r1/brief.md`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1-r1/responses.jsonl`
- `/tmp/booking_quality/booking-human-nojudge-hq1-l1-contract-first-a1-r1/trace_bundle.jsonl`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r1/summary.json`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r1/brief.md`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r1/responses.jsonl`
- `/tmp/booking_quality/booking-human-critical-hq1-l2-contract-first-a1-r1/trace_bundle.jsonl`
- `docs/evidence/2026-02-21-hq1-bad-turn-catalog.tsv`

## L1 Result (No-Judge)
- run_id: `booking-human-nojudge-hq1-l1-contract-first-a1-r1`
- stop_reason: `max_failures_reached:5`
- duration: `1989.28s`
- infra_valid: `false` (`webhook_errors`, `decision_meta_errors`)
- semantic_valid: `false` (`blocking_reason`, `threshold_breach`)
- blocking_reason_count: `8`
- hq1_bad_turn_count: `5`
- hq1_class_counts: `handoff_miss=1`, `non_actionable_reply=1`, `booking_flow_break=3`, `wrong_action=0`, `hallucinated_fact=0`
- top strict failures: `expected_action_mismatch=1`, `booking_slot_stall=1`, `decision_meta_missing=1`, `expected_reply_type_mismatch=2`

## L2 Result (Judge Critical)
- run_id: `booking-human-critical-hq1-l2-contract-first-a1-r1`
- stop_reason: `max_failures_reached:10`
- duration: `2532.72s`
- infra_valid: `true`
- semantic_valid: `false` (`blocking_reason`)
- blocking_reason_count: `22`
- hq1_bad_turn_count: `8`
- hq1_class_counts: `handoff_miss=1`, `non_actionable_reply=1`, `booking_flow_break=6`, `wrong_action=0`, `hallucinated_fact=0`
- judge_fail: `6`
- rewrite_governance_valid: `false` (`post_llm_semantic_rewrite_budget_exceeded`)

## Blocking Set Verdict
- `wrong_action`: `0` (L1), `0` (L2)
- `handoff_miss`: `1` (L1), `1` (L2)
- `non_actionable_reply`: `1` (L1), `1` (L2)
- `booking_flow_break`: `3` (L1), `6` (L2)
- `hallucinated_fact`: `0` (L1), `0` (L2)

## Concrete Bad Turns (Client -> Bot -> Problem)
- `LLM-QUAL-booking-human-nojudge-hq1-l1-contract-first-a1-r1-003-09-2d3a63`: `Я хочу изменить время записи.` -> `Чтобы проверить, перенести или отменить запись...` -> `handoff_miss` (`calendar.reschedule/verifier_blocked`, expected `handoff + pending`).
- `LLM-QUAL-booking-human-nojudge-hq1-l1-contract-first-a1-r1-004-13-02a1f7`: `Меня зовут Лена.` -> `Отлично, время подходит. Как вас зовут?` -> `booking_flow_break` (`booking_slot_stall`, повторный вопрос имени).
- `LLM-QUAL-booking-human-nojudge-hq1-l1-contract-first-a1-r1-006-03-14ab2e`: `Есть ли у вас акции на услуги?` -> no observed reply/meta -> `non_actionable_reply` (`decision_meta_missing`, `unknown_state`, `info_section_miss`).
- `LLM-QUAL-booking-human-nojudge-hq1-l1-contract-first-a1-r1-007-01-24c0c9`: `Я хочу записаться на стрижку на завтра.` -> slot dump -> `booking_flow_break` (`expected_reply_type_mismatch`).
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r1-006-01-d9aa53`: `Какой у вас ассортимент услуг?` -> `Не удалось подтвердить действие автоматически...` -> `non_actionable_reply` (judge fail `missed_question`, `tool_decision=contract_invalid`).
- `LLM-QUAL-booking-human-critical-hq1-l2-contract-first-a1-r1-007-03-36585e`: `А можно записаться на 15:00?` -> `На 15:00 свободных окон нет...` -> `booking_flow_break` (`expected_reply_type_mismatch` after conflict branch).

## Acceptance Gate Check
- `hq1_bad_turn_count == 0`: `FAILED` (`5` on L1, `8` on L2)
- `expected_action_mismatch == 0`: `FAILED` (`1` on L1/L2)
- `judge_fail == 0` (critical): `FAILED` (`6`)
- Brain/Top Architect sign-off against catalog: `PENDING` (cannot sign-off with red L1/L2)

## Decision
- release gate for HQ1 remains `NO_GO`.
- required next step: targeted behavior fixes for `handoff_miss`, `non_actionable_reply`, `booking_flow_break` before any new acceptance replay.
