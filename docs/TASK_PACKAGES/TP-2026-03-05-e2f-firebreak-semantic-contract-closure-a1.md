# TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1

## Название/цель
Закрыть semantic blockers после `E2e` (`booking-lock-20260305-firebreak-e2-a1-r22`), чтобы вернуть acceptance lock в canonical-state и разблокировать `replay -> canary`.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: `Block E / E2 runtime evidence`)
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2e-firebreak-canonical-lock-replay-a1.md`
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/trace.py`

## One web search (mandatory before implementation)
- Query: `OpenTelemetry semantic conventions span events attributes errors best practices`
- Date/time (UTC): `2026-03-04T08:00Z`
- Sources opened:
  - `https://opentelemetry.io/docs/specs/semconv/`
- Ready solutions found:
  - Failures in orchestration chains should be captured with explicit reason-codes at boundary transitions.
  - Contract transitions should be observable as structured events, not inferred from free text.
- Decision:
  - `integrate`: add/strengthen deterministic contract transitions (`tool outcome -> expected_reply/state`) with explicit reason-codes and tests.
- Rejected alternatives:
  - Prompt-only mitigation without boundary-contract changes.

## Root cause (mandatory)
- Symptom:
  - `E2e` lock ended with `semantic_valid=false`; blockers: `calendar_tool_contract_miss=2`, `stale_booking_carryover=1`, `judge_fail=1`.
  - Degraded path budget breached (`degraded_fallback_rate=0.1783`) and degraded turns in artifacts have missing explicit reason-codes (`policy_core_guard` unresolved).
- Minimal reproduction:
  1. Run acceptance lock `booking-lock-20260305-firebreak-e2-a1-r22`.
  2. Inspect `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/summary.json`.
  3. Inspect top-failure turns in `brief.md` and `responses.jsonl`.
- Evidence:
  - `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/summary.json`
  - `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/brief.md`
  - `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r22/manual_audit.json`
- Five Whys:
  1. Почему lock non-canonical? — Semantic blockers in booking-calendar path remain.
  2. Почему calendar blocker остается? — Tool success and follow-up state transitions are not terminally enforced for all branches.
  3. Почему stale carryover появляется? — Previous expected booking state leaks into next turn/branch in edge paths.
  4. Почему degraded fallback breaches budget? — Fallback path is entered too often under active booking interruptions.
  5. Почему это не поймали раньше? — Existing deterministic tests cover slices, но не весь combined edge-set from `r22` top failures.
- Root cause statement:
  - Boundary contract between `tool outcome`, `expected_reply`, and downstream booking follow-up is still split across branches, allowing stale-state carryover and non-terminal behavior under real acceptance dialogs.
- Fix mechanism:
  1. Add deterministic boundary guard(s) for `calendar.book_slot=ok` terminal clear invariants across all booking follow-up paths.
  2. Add deterministic stale-carryover rejection logic with explicit reason-code in decision trace/meta.
  3. Restore graceful-degrade observability: enforce non-empty degrade `reason_code` on fallback turns.
  4. Add/extend regression tests for `calendar_tool_contract_miss`, stale carryover, and degrade reason-code classes.
  5. Rerun acceptance lock (`r23`) and audit.

## Invariant
- Никаких semantic hardcode/keyword branching в core для бизнес-смысла.
- Только boundary-contract fixes + observability + deterministic tests.
- Acceptance gates remain fail-closed.

## Scope
- Booking decision boundary fixes.
- Deterministic regression coverage for `calendar_tool_contract_miss` and stale carryover.
- Degrade reason-code observability for fallback turns.
- Acceptance lock rerun evidence.

## Out of scope
- Canary/full rollout.
- Wide refactor of all booking flows outside blocker classes.

## Touch-list (файлы/таблицы)
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `STATE.md`

## Plan (1..N)
1. Extract failing turn signatures from `r22` artifacts and map to deterministic boundary points.
2. Implement minimal boundary fix for terminal clear + stale carryover guard.
3. Add deterministic regression tests for both blocker classes.
4. Run deterministic suite.
5. Run acceptance lock (`r23`) + strict audit.
6. Update canon docs with verdict and next step.

## DoD
- `calendar_tool_contract_miss` and `stale_booking_carryover` deterministic tests exist and pass.
- Acceptance lock `r23` is executed with strict artifacts and audit.
- E2 status in canon docs updated with factual verdict.

## Checks
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "llm_policy_core_calendar_book_slot_ok_terminal_clear_blocks_followup_expected_reply or policy_collect_interrupt_arbitration_rewrites_master_query_to_info"`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-20260305-firebreak-e2-a1-r23 --pg-checklist /tmp/booking_quality/pg_checklist-firebreak-e2-a1.json --allow-pending-previous -- --base-url http://127.0.0.1:18184 --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --allow-non-allowlist --judge-mode all --quality-lane acceptance --run-economy-gate block --allow-non-canonical-lock-retry --fail-on-thresholds`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r23 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/booking-lock-20260305-firebreak-e2-a1-r23/*`
- Updated canon docs (`STATE.md`, program TP)

## Release safety (mandatory)
- Rollout strategy: local acceptance only, no prod mutation.
- Go/no-go:
  - lock `infra_valid=true`, `semantic_valid=true`, `run_integrity_valid=true`.
- Rollback:
  - Revert boundary fix commit and keep E2 as blocked.

## Rollback
- `git revert <fix-commit>` (if change merged).
- Keep previous canonical evidence as active baseline.

## No-go
- No prompt-only mitigation as primary fix.
- No gate weakening (`fail-on-thresholds`, `run_economy`, `quality_constant`).

## Риски/блокеры
- Multiple blocker classes may require split-fix (E2f.1/E2f.2) if one fix reintroduces another.
- Acceptance run duration remains high; avoid unnecessary reruns without deterministic delta.

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - Combined booking edge orchestration still spans multiple modules.
- Why not in this block:
  - Goal is blocker closure with minimal change radius.
- Risk if deferred:
  - Repeated semantic invalid locks, no canary progression.
- Linked follow-up Task Package(s):
  - `TP-2026-03-06-e2g-booking-orchestration-unification-a1` (if E2f closes blockers but architecture remains fragmented).
- Expiry/trigger to stop deferral:
  - Two consecutive acceptance locks with new blocker classes from same boundary layer.

## Next-block contract (mandatory)
- Next block objective:
  - If `r23` canonical, run replay in same chain; else split fix into `E2f.1`/`E2f.2` by blocker class.
- First deterministic check command:
  - `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/trace.py`
- Blocked-by conditions:
  - Missing firebreak runtime on `127.0.0.1:18184`.
  - Runtime profile mismatch: active `truffles-api` on `:8000` without firebreak flags; acceptance lock requires firebreak-on runtime on `:18184`.
- Owner role for closure:
  - Hands (implementation + evidence), Brain/Top Architect (acceptance sign-off).

## Execution log (E2f.1, 2026-03-04)
- Delivered deterministic remediation slice for two blocker classes from `r22`:
  - `calendar_tool_contract_miss` false-positive path fixed in quality evaluator (`ops/diagnose.py`): `booking_blocked_reason` no longer overrides explicit calendar success decisions (`not_found/ok/time_mismatch/...`) when deriving `tool_signals.calendar.outcome`.
  - stale booking sidecar suppression expanded in discounts policy path (`truffles-api/app/routers/webhook/decision.py`) for active `expected_reply_type=intent_choice` and existing intent-queue transitions (`pending_intent_queue` / `intent_queue_event`), preventing `Ещё был вопрос по записи...` leakage into FACT/info discounts replies.
- Added deterministic regressions:
  - `truffles-api/tests/test_booking_quality_response_guard.py::test_calendar_outcome_not_found_not_forced_to_failure_by_booking_blocked_reason`
  - `truffles-api/tests/test_booking_quality_response_guard.py::test_calendar_outcome_without_decision_keeps_blocked_reason_failure`
  - `truffles-api/tests/test_message_endpoint.py::test_discounts_reply_with_expected_intent_choice_suppresses_booking_sidecar`
- Checks run:
  - `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_booking_quality_response_guard.py truffles-api/tests/test_message_endpoint.py`
  - `pytest -q truffles-api/tests/test_booking_quality_response_guard.py` (`55 passed`)
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_info_interrupt or discounts_reply_with_expected_intent_choice_suppresses_booking_sidecar"` (`6 passed`)
  - `ruff check ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_booking_quality_response_guard.py truffles-api/tests/test_message_endpoint.py` (`All checks passed`)
- Status after E2f.1:
  - deterministic layer for these two classes is green locally;
  - canonical acceptance lock `r23` remains pending as the next mandatory gate.
