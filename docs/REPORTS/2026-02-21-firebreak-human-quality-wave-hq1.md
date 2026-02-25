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

## Forensic Addendum (2026-02-23, last 14h)
- scope: all `booking-human-*` run directories in `/tmp/booking_quality` modified in last 14 hours.
- runs analyzed: `13`
- aggregate: `responses=281`, `trace_rows=280`, `strict_fail=6`, `judge_fail=7`, `suppressed_judge_fail=1`.
- key hidden defects (user-visible despite partial strict green):
- `degraded=47`
- `requested_date_time_like=13`
- `stale_prompt_date_mismatch=9`
- `clarify_after_slots=14`
- `mix_info_booking=7`
- weak scenario contract remains high (`11/15` weak expectation turns in micro, `79/112` in L1 scenario).
- detailed evidence:
- `/tmp/booking_quality/deep14/deep_report.md`
- `/tmp/booking_quality/deep14/run_metrics.tsv`
- `/tmp/booking_quality/deep14/dialog_metrics_joined.tsv`
- `/tmp/booking_quality/deep14/anomalies_turns.tsv`
- `/tmp/booking_quality/deep14/judge_fail_turns.tsv`

## Invalid Run Quarantine
- run: `booking-human-nojudge-hq1-l1-contract-first-a1-r8`
- status: `INVALID`
- reasons:
- missing required artifacts: `summary.json`, `brief.md`
- run completion gap: `responses=101`, `expected=112`
- trace parity mismatch: `trace_rows=100`, `responses=101`
- missing trace message_id: `LLM-QUAL-booking-human-nojudge-hq1-l1-contract-first-a1-r8-008-03-c286cf`
- policy:
- run is excluded from baseline/comparison and acceptance.
- remediation work continues only from valid replay chain.

## Last 3h File+Dialog Forensics (2026-02-23)
- window (UTC): `08:56:36` .. `11:20:31`.
- runs analyzed: `8` (`6` complete + `2` empty/invalid).
- files analyzed (non-summary included): `30` (`responses.jsonl`, `trace_bundle.jsonl`, `brief.md`, `scenarios.json`).
- dialogs analyzed: `30` (all dialog rows from complete runs).
- aggregate metrics: `turns=406`, `strict_fail=30`, `judge_fail=6`, `suppressed_judge_fail=4`, `weak_oracle=77`, `tool_time_mismatch=18`, `answer_timeout_or_empty=48`.
- empty/invalid runs: `r23`, `r23b` (`missing_summary_json|empty_run_directory`).
- dominant dialog-level defects:
- `answer_empty_value=18`
- `tool_time_mismatch=5`
- `answer_timeout=3`
- `strict_fail=3`
- `tool_not_found_fallback=3`
- `judge_fail=2`
- forensic artifacts:
- `/tmp/booking_quality/last3h_file_matrix.tsv`
- `/tmp/booking_quality/last3h_dialog_table.tsv`
- `/tmp/booking_quality/last3h_run_metrics.tsv`
- `/tmp/booking_quality/last3h_full_file_dialog_forensics.json`
- `/tmp/booking_quality/last3h_detailed_dialog_report.md`

## Step7 Validation Chain (2026-02-23)
- runtime commit locked: `ffda113634409f3cd9fde7b9065753b18d60f4c1` (`http://127.0.0.1:18100/admin/version`).
- replay isolation enforced on every run: `--jid-mode unique` + `--reset-before-dialog`.

### Gate check: legacy micro scenario
- run_id: `booking-replay-20260223-slotfix-a1-r16-nojudge-ffda-step7`
- result: `INVALID` (`stop_reason=invalid_scenario_contract_preflight`)
- reason: `weak_oracle_turn` in legacy scenario (`weak_expectation_turns=3/15`).
- artifact: `/tmp/booking_quality/booking-replay-20260223-slotfix-a1-r16-nojudge-ffda-step7/summary.json`

### Contractized micro replay (no-judge)
- run_id: `booking-replay-20260223-contractized-a1-micro1-nojudge-ffda-step7`
- result: `PASS`
- quality: `infra_valid=true`, `semantic_valid=true`, `strict_pass_rate=1.0`, `blocking_reason_count=0`, `weak_oracle_turn_count=0`, `unobserved_turn_count=0`.
- artifact dir: `/tmp/booking_quality/booking-replay-20260223-contractized-a1-micro1-nojudge-ffda-step7`

### Contractized critical replay (L2)
- run_id: `booking-replay-20260223-contractized-a1-micro1-critical-ffda-step7`
- result: `PASS`
- quality: `infra_valid=true`, `semantic_valid=true`, `strict_pass_rate=1.0`, `judge.counts.fail=0`, `blocking_reason_count=0`, `hq1_bad_turn_count=0`.
- artifact dir: `/tmp/booking_quality/booking-replay-20260223-contractized-a1-micro1-critical-ffda-step7`

### Run-economy anti-burn proof
- run_id: `booking-replay-20260223-contractized-a1-micro1-critical-ffda-step7-testmode1`
- result: `INVALID`
- reason: `run economy gate failed (replay_fingerprint_unchanged)`.
- artifact: `/tmp/booking_quality/booking-replay-20260223-contractized-a1-micro1-critical-ffda-step7-testmode1/summary.json`

### TEST_MODE=1 confirmation (explicit override)
- run_id: `booking-replay-20260223-contractized-a1-micro1-critical-ffda-step7-testmode1-r2`
- launch note: one-time override `--allow-no-code-delta` used only to bypass replay-fingerprint lock for verification.
- result: `PASS`
- quality: `infra_valid=true`, `semantic_valid=true`, `strict_pass_rate=1.0`, `judge.counts.fail=0`, `blocking_reason_count=0`.
- artifact dir: `/tmp/booking_quality/booking-replay-20260223-contractized-a1-micro1-critical-ffda-step7-testmode1-r2`

## Last 3h Forensics (Corrected Snapshot, 2026-02-23T13:32Z)
- source of truth: `/tmp/booking_quality/analysis-last-3h.json`, `/tmp/booking_quality/analysis-last-3h.md`.
- window: last 180 minutes.
- runs in window: `14`.
- complete runs with full artifacts (`brief/scenarios/responses/trace/summary`): `10`.
- runs with missing dialog artifacts (`missing_scenarios|missing_responses|missing_trace_bundle`): `4`.

### Corrected aggregate
- total observed turns across runs with `responses.jsonl`: `416`.
- strict fails: `5`.
- hard fails: `1`.
- judge fails: `4`.
- all judge fails are concentrated in one run: `booking-human-critical-hq1-l2-slotfix-a1-r24-ffda-awo` (dialogs `6/7/8`).

### Dialog-level quality status
- `booking-human-nojudge-hq1-l1-slotfix-a1-r23c-ffda-awo`: `8/8` dialogs strict green, no hard fails.
- `booking-replay-20260223-contractized-a1-full-nojudge-ffda-step7`: `8/8` dialogs strict green, no hard fails.
- `booking-human-critical-hq1-l2-slotfix-a1-r24-ffda-awo`: `4` judge fails (`missed_question`) in dialogs `6/7/8`.
- `booking-replay-20260223-contractized-a1-full-critical-ffda-step7{,b,c,d}`: incomplete (`signal_15/signal_2`, `run_completion_gap`) and excluded from acceptance.

### Critical infra/process finding
- replay runs `step7b/step7c` were started on runtime without effective test simulation path; observed symptom set:
- runtime log: `Simulation metadata ignored for non-test traffic`,
- transport side-effect: `ChatFlow ... "Your plan has been expired please renew."`,
- consequence: invalid critical runs (`run_completion_gap`, webhook/transport contamination).
- remediation path: enforce runtime parity gate (`TEST_MODE=1` + simulation allowed) before expensive full-critical replay.

### Acceptance state
- quality claim “каждый диалог проходит логически и семантически” is **not proven** for full critical chain in this window.
- current proven floor:
- deterministic + full no-judge replay are green (`8/8` dialogs).
- semantic judge-critical full replay remains blocked by incomplete runs and infra contamination.

## Contract-First Remediation Progress (2026-02-24)
- scope: TP-2026-02-21 steps `2/3/6/7/8/10/13` hardening in active worktree.
- runtime regression fixed: resolver trace hook no longer crashes on bool/non-iterable in `_record_contract_traces`.
- hardcode prevention gate validated in `block` mode on current diff:
- `valid=true`, `enforced=true`, `reasons=[]`, `violations=[]`.
- removed phrase-coupled followup guard branch from core (`decision.py`), kept followup behavior contract-driven via expected_reply + slots.
- deterministic contour re-run (post-fix):
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking or expected_reply or session_memory or policy_core"` -> `124 passed`
- `pytest -q truffles-api/tests/test_booking_quality_*.py` -> `167 passed`
- `pytest -q truffles-api/tests/test_calendar_slot_response_contract.py truffles-api/tests/test_master_info_flow.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_pack_grounding_contract.py` -> `52 passed`
- note: full critical replay remains frozen until next lock/replay evidence cycle on canonical baseline.
- replay dry-run gate proof:
- run_id: `hq1-remediation-dryrun-20260224-a1-r2`
- result: `INVALID` (expected), reason `weak_oracle_turn` from scenario-contract preflight.
- artifacts: `/tmp/booking_quality/hq1-remediation-dryrun-20260224-a1-r2/{summary.json,brief.md}`.
- replay micro critical proof:
- run_id: `booking-replay-20260224-contractized-a1-micro1-critical-r1`
- result: `FAIL` (`semantic_valid=false`), reason `regression_breach` (`degraded_fallback_rate delta=+0.10 vs baseline`).
- quality snapshot: `infra_valid=true`, `judge.fail=0`, `run_integrity_valid=true`, `hardcode_core_gate_valid=true`.
- artifacts: `/tmp/booking_quality/booking-replay-20260224-contractized-a1-micro1-critical-r1/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`.

## Post-Merge Validation (2026-02-24, commit `ba4dcef`)
- runtime parity restored on dedicated container:
- image/container: `truffles-api-firebreak-hq1-ba4dcef1` / `truffles-api-firebreak-hq1-ba4dcef1`
- endpoint: `http://127.0.0.1:18161/admin/version`
- version: `git_commit=ba4dcef173839c6d3565cdbf630e6174f6110c07`, `TEST_MODE=1`.
- deterministic contour on merged head:
- `test_booking_quality_status_gate + scenario_contract_gate + response_guard` -> `77 passed`
- `test_calendar_slot_response_contract + test_master_info_flow + test_pack_runtime_service + test_pack_grounding_contract` -> `52 passed`
- `test_message_endpoint -k "booking or expected_reply or session_memory or policy_core"` -> `125 passed`
- `test_booking_quality_*.py` -> `167 passed`
- `llm-quality-gates` on merged head: all gates valid (`lexicon_regex_delta_gate`, `hardcode_core_gate`, `run_economy_gate=off`).

### Replay gate status after merge
- canonical human full scenario (`/tmp/booking_quality/blocking_scenarios_human.json`) remains blocked by contract preflight:
- run_id: `booking-human-nojudge-hq1-20260224-a1-r1b`
- result: `INVALID`
- reason: `weak_oracle_turn`
- this confirms freeze policy from TP and keeps full HQ1 replay blocked until scenario re-canonicalization.

### Contractized micro replay chain (canonical baseline)
- L1 no-judge:
- run_id: `booking-replay-20260224-contractized-a1-micro1-nojudge-r1`
- quality: `infra_valid=true`, `semantic_valid=true`, `blocking_reason_count=0`, `hq1_bad_turn_count=0`, `run_integrity_valid=true`
- artifacts: `/tmp/booking_quality/booking-replay-20260224-contractized-a1-micro1-nojudge-r1/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`
- L2 critical:
- run_id: `booking-replay-20260224-contractized-a1-micro1-critical-r2`
- quality: `infra_valid=true`, `semantic_valid=true`, `blocking_reason_count=0`, `hq1_bad_turn_count=0`, `judge.counts.fail=0`, `run_integrity_valid=true`
- artifacts: `/tmp/booking_quality/booking-replay-20260224-contractized-a1-micro1-critical-r2/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`

### Before/After delta (critical)
- baseline fail run: `booking-human-critical-hq1-l2-contract-first-a1-r1`
- prior snapshot: `blocking_reason_count=22`, `judge_fail=6`, `handoff_miss=1`, `non_actionable_reply=1`, `booking_flow_break=6`
- current micro critical snapshot: all above classes reduced to `0` (`blocking_reason_count=0`, `judge_fail=0`)

### Current acceptance state
- micro contract chain is green on merged commit with runtime parity.
- full HQ1 human chain is still blocked by scenario-contract quality (`weak_oracle_turn`) and requires re-canonicalized full scenarios before `L1/L2/L3` acceptance.
