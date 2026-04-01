# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R7 Session Reset Simulation Transport Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R7-SESSION-RESET-SIMULATION-TRANSPORT-CANARY-REPLAY-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R7-SESSION-RESET-SIMULATION-TRANSPORT-RUNTIME-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `UNLOCKS`: `classify_consultant_core_demo_salon_seed19_r10_after_simulation_transport_replay`

## Name / goal
Run one fresh exact replay on the same seed-`19` scenarios after the bounded explicit-handoff simulation transport repair. The replay is admissible only if it proves fresh runtime parity, reuses the locked scenarios/baseline, and is strict-audited before any further runtime or proof change.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- `/tmp/booking_quality/a922-go2f-seed19/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`

## Invariant
- no new runtime/proof patch before replay truth is established
- no frozen-router edits
- exact replay must reuse the locked scenario file and baseline summary
- strict audit is mandatory before any classification

## Scope
- start a fresh local runtime from the current worktree on `127.0.0.1:18186`
- verify `/admin/version.git_commit == HEAD`
- run one exact replay as `a922-go2f-seed19-r10`
- strict-audit the replay artifact
- record truthful outcome and the next admissible move

## Out of scope
- new code changes
- acceptance lock/full runs
- proof/oracle patches
- runtime patches after replay

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r10/*`

## Root cause (mandatory)
- **Symptom:** preflight session-reset traffic under `simulation_mode=True` previously hit real provider transport before any scenario turn executed.
- **Minimal reproduction:** exact replay `r7` on the locked seed-`19` scenarios plus strict audit and local runtime logs.
- **Evidence:** `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`, local provider response logs, and the bounded runtime implementation report.
- **Five Whys:** simulated reset entered the explicit-handoff owner; the live owner used direct provider send; simulation metadata was ignored; provider transport contaminated replay; blocker surfaced before turn execution.
- **Root cause statement:** the executable later explicit-handoff owner bypassed the existing simulation-safe transport contract.
- **Fix mechanism:** the live later owner now routes simulated sends through `ChatFlowAdapter().send_text(...)` with `MessageOptions(extra={"simulation_mode": True})` and records `transport_simulated`.

## Work mode (mandatory)
- `Mode`: `closure`

## Plan
1. Start a fresh local runtime from the current worktree and verify `/admin/health` plus `/admin/version`.
2. Reuse the exact seed-`19` replay command shape with only `run-id` / `output-dir` updated to `a922-go2f-seed19-r10`.
3. Strict-audit the resulting artifact.
4. Publish truthful replay verdict and the next admissible move.

## DoD
- fresh replay artifact `/tmp/booking_quality/a922-go2f-seed19-r10` exists
- `/admin/version.git_commit == HEAD` is recorded before replay
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done --strict-artifacts` passes
- next move is a classification based on fresh replay truth, not assumption

## Checks
- `git -C /home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922 rev-parse HEAD`
- `curl -sf http://127.0.0.1:18186/admin/version`
- `curl -sf http://127.0.0.1:18186/admin/health`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --quality-lane dev --count 10 --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r10 --run-id a922-go2f-seed19-r10 --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --history-max 20 --max-failures 1 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done --strict-artifacts`

## Evidence
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r10/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r10/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r10/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r10/manual_audit.json`

## Rollback
1. Stop the local listener.
2. Mark any partial replay artifact non-canonical via strict audit if needed.
3. Return to the runtime implementation block truth; do not claim replay closure.

## No-go
- no new code changes inside this block
- no scenario regeneration
- no baseline mutation
- no skipping strict audit

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duplicate owner defs remain in `truffles-api/app/services/reasoning_core.py`
- other direct-send paths may still bypass simulation-aware transport

### Why not in this block
- this block only validates the repaired explicit-handoff family on fresh replay

### Risk if deferred
- we would keep moving without truthful replay closure on the repaired family

### Linked follow-up Task Package(s)
- `classify_consultant_core_demo_salon_seed19_r10_after_simulation_transport_replay`

### Expiry/trigger to stop deferral
- stop deferral immediately if fresh replay still shows provider transport on simulated preflight traffic

## Next-block contract (mandatory)
### Next block objective
- classify the first surviving blocker from fresh replay `r10` with strict audit already complete

### First deterministic check command
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done --strict-artifacts`

### Blocked-by conditions
- local runtime is stale or `/admin/version.git_commit` does not match `HEAD`
- replay artifact `r10` is incomplete or unaudited

### Owner role for closure
- `Brain / Top Architect`
