# TP-2026-03-04-e2c-canonical-replay-canary-a1

## Название/цель
Закрыть `E2c` для Block E: получить валидный acceptance `lock -> replay` на firebreak-on runtime или формально зафиксировать fail-closed blocker с полным forensic/evidence handoff без ослабления quality gates.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: `Block E / E2`)
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2a-interrupt-arbitration-owner-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2b-lexicon-resolver-hardening-a1.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/diagnose.py`
- `scripts/llm_quality_guarded.sh`
- `scripts/quality_chain_controller.sh`

## One web search (mandatory before implementation)
- Query: `OpenAI API latency optimization make fewer requests`
- Date/time (UTC): `2026-03-04T06:18Z`
- Sources opened:
  - `https://platform.openai.com/docs/guides/latency-optimization`
- Ready solutions found:
  - Reduce multi-request fan-out and expose progress for long stages.
  - Prefer deterministic progress visibility in long LLM phases.
- Decision:
  - `integrate` at process level (forensic/acceptance procedure): treat scenario-generation stall as explicit infra blocker with stop condition and chain abort reason.
- Rejected alternatives:
  - Silent retries without SLA reason-codes (breaks observability and anti-drift loop discipline).

## Root cause (mandatory)
- Symptom:
  - `E2c` acceptance `replay` could not be started canonically; lock/replay loop repeatedly failed at process gates before semantic/runtime verdict.
- Minimal reproduction:
  1. Start firebreak-on runtime on `http://127.0.0.1:18184`.
  2. Run guarded acceptance replay/lock with `scripts/llm_quality_guarded.sh`.
  3. Observe gate failures in summaries for `r14..r18` and long scenario-generation stalls in `r19/r21`.
- Evidence:
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r14/summary.json` (`stop_reason=system_exit`, early failure).
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r15/summary.json` (`stop_reason=invalid_preflight`).
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r16/summary.json` (`stop_reason=in_progress`, interrupted non-canonical lock).
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r17/summary.json` (`stop_reason=invalid_run_economy_preflight`).
  - `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r18/summary.json` (`stop_reason=invalid_quality_constant_preflight`).
  - `/tmp/booking_quality/_chain/20260304-firebreak-e2-a1-r19.json`, `/tmp/booking_quality/_chain/20260304-firebreak-e2-a1-r21.json` (manual abort with reason `manual_stop_scenario_generation_sla`).
  - Process evidence: repeated long `booking_dialog_scenarios.py --count 5` pre-runtime phases without transition to webhook-turn execution.
- Five Whys:
  1. Why no canonical replay for E2c?
     - Replay requires chain lock precondition in the same chain id.
  2. Why lock precondition did not complete canonically?
     - Multiple lock attempts were invalid/incomplete due preflight and gate conflicts.
  3. Why retries were blocked?
     - Run-economy blocked unchanged non-canonical lock fingerprint; quality-constant blocked `allow_no_code_delta` in acceptance lane.
  4. Why long attempts still failed to produce canonical lock?
     - Scenario-generation stage consumed run budget/time without reaching runtime dialog phase.
  5. Why this became systemic?
     - Acceptance process currently couples chain-precondition strictness with expensive scenario generation and lacks an explicit fast recovery path for infra/procedural non-canonical lock attempts.
- Root cause statement:
  - `E2c` is blocked by process-layer coupling (chain precondition + run-economy + quality-constant + expensive scenario-generation stage) rather than a single semantic runtime defect in policy-core.
- Fix mechanism:
  1. Keep acceptance gates fail-closed (no threshold/gate downgrade).
  2. Register `E2c` as blocked with explicit reason-codes and chain abort evidence.
  3. Move next block to deterministic closure of process blockers before semantic replay/canary.

## Invariant
- No relaxation of `run-economy`, `quality-constant`, `manual-audit`, `forensic-sla` gates.
- No semantic hardcode in runtime core.
- Acceptance evidence stays contract-first (`action/tool/trace/meta/outcome`), not text oracle fitting.

## Scope
- Guarded acceptance orchestration for `E2c` (`lock/replay` entrypoint).
- Forensic evidence capture and canonical docs sync.

## Out of scope
- New policy-core semantic fixes in this block.
- Cross-domain (`P12`) onboarding closure.

## Touch-list (files/paths)
- `docs/TASK_PACKAGES/TP-2026-03-04-e2c-canonical-replay-canary-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-19-llm-first-firebreak-program.md`
- `STATE.md`

## Plan (1..N)
1. Reproduce E2c guarded runtime attempts on firebreak-on base URL.
2. Capture exact gate/blocker reasons and run artifacts.
3. Close hanging chains/runs with explicit abort reason.
4. Sync program TP + STATE with blocked-contract and next deterministic block.

## DoD
- `E2c` status is unambiguous in canon (`done` or explicit `blocked` with evidence).
- All attempted non-canonical runs have forensic records and no dangling chain ambiguity.
- Next block contract has deterministic first check and blocked-by list.

## Checks
- `scripts/llm_quality_guarded.sh --mode replay ...`
- `scripts/llm_quality_guarded.sh --mode lock ...`
- `python3 ops/diagnose.py llm-quality-audit --run-dir ... --status done --strict-artifacts`
- `scripts/quality_chain_controller.sh abort --chain-id ... --reason ...`

## Evidence
- `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r14/summary.json`
- `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r15/summary.json`
- `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r16/summary.json`
- `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r17/summary.json`
- `/tmp/booking_quality/booking-lock-20260304-firebreak-e2-a1-r18/summary.json`
- `/tmp/booking_quality/_chain/20260304-firebreak-e2-a1-r19.json`
- `/tmp/booking_quality/_chain/20260304-firebreak-e2-a1-r21.json`

## Release safety (mandatory)
- Rollout strategy: not applicable (runtime acceptance/forensic only, no production behavior change).
- Go/no-go signals: canonical lock/replay availability vs explicit blocked reason.
- Rollback: not applicable (no runtime code path change).

## Rollback
- Docs-only: revert TP/STATE entries if evidence mapping is incorrect.

## No-go
- No manual index tampering in `/tmp/booking_quality/_index`.
- No gate disablement in acceptance lane.
- No baseline update from invalid/incomplete runs.

## Risks/Blockers
- Scenario-generation SLA remains unstable; lock can spend budget before runtime dialogs.
- Chain can be left in `running` state after manual process kill without explicit abort command.

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - Acceptance process deadlock risk between `run_economy` and `quality_constant` after non-canonical lock attempts.
  - Long opaque scenario-generation stage before runtime evaluation.
- Why not in this block:
  - This block is forensic closure and canonical status sync, not gate redesign implementation.
- Risk if deferred:
  - Repeated expensive non-canonical cycles with no semantic signal.
- Linked follow-up Task Package(s):
  - `TP-2026-03-05-e2d-acceptance-process-unblock-a1` (to create).
- Expiry/trigger to stop deferral:
  - Before next `E2c` acceptance attempt; do not run new expensive lock without process unblock artifact.

## Next-block contract (mandatory)
- Next block objective:
  - Unblock acceptance process path for canonical `E2c` lock/replay without weakening gates.
- First deterministic check command:
  - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k "run_economy or quality_constant"`
- Blocked-by conditions:
  - Any active/aborted chain with unresolved run status in `/tmp/booking_quality/_chain`.
  - Missing documented recovery rule for scenario-generation SLA breach.
- Owner role for closure:
  - Hands (implementation), Brain + Top Architect (acceptance sign-off).
