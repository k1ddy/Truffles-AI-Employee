# TP-2026-03-24 Consultant Core Booking Pending Handoff Authority Reset Closure Replay A922

## Title/goal
Run exactly one fresh local closure replay after the booking/pending/handoff authority reset, using the locked `seed19` scenarios and baseline, to prove whether the touched family is closed on live runtime parity or to truthfully surface the next blocker.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-booking-pending-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-structural-implementation-a922.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`

## Root cause (mandatory)
- **Symptom:** structural proof is green, but live closure is still unproven because `r47` was intentionally interrupted and cannot count as canon.
- **Minimal reproduction:** replay the locked `seed19` scenarios against fresh runtime parity after the structural reset.
- **Evidence:** `/tmp/booking_quality/a922-go2f-seed19-r47/{summary.json,runtime_state.json,responses.jsonl}` plus the structural report and deterministic proofs from the previous block.
- **Five Whys:**
  1. Why is closure still open? Because `r47` stopped by signal and is non-canonical.
  2. Why can we replay now? Because the touched authority seam is structurally reset and guards are green.
  3. Why only one replay? Because replay is closure-only now, not discovery.
  4. Why audit `r47` first? Because pending manual-audit debt must not contaminate the next run.
  5. Why reuse the locked scenarios? Because closure must be comparable to the previous family evidence.
- **Root cause statement:** closure is blocked by missing fresh live evidence, not by missing local structural proof.
- **Fix mechanism:** audit the frozen `r47` artifact, verify runtime parity, run one fresh comparable replay, audit the new artifact, and publish closure truth.

## Invariant
Do not modify runtime code in this block. Do not resume `r47`. Do not launch more than one fresh replay. Do not weaken gates or switch to discovery mode.

## Scope
- audit the frozen non-canonical `r47` replay
- verify runtime parity on `http://127.0.0.1:18186`
- launch one fresh local replay with locked `seed19` scenarios/baseline
- audit and classify the result

## Out of scope
- new implementation
- new structural deletion block
- acceptance lock/canary/full
- classifying future surfaced rows before the replay exists

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `/tmp/booking_quality/a922-go2f-seed19-r47/manual_audit.md`
- `/tmp/booking_quality/a922-go2f-seed19-r47/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r48/*`

## Plan (1..N)
1. Resolve the pending manual audit on `r47` without resuming it.
2. Verify runtime health/version parity and the required local guards.
3. Run one fresh comparable replay against `/tmp/booking_quality/a922-go2f-seed19/scenarios.json` and baseline `/tmp/booking_quality/a922-go2f-seed19/summary.json`.
4. Run post-run audit on the fresh replay artifact.
5. Publish either closure or the next truthful blocker; no follow-up implementation inside this block.

## DoD
- `r47` is audited and remains explicitly non-canonical
- exactly one fresh replay run is produced
- the fresh replay has summary/brief/manual audit artifacts
- closure outcome is documented with evidence and no code changes

## Work mode (mandatory)
`closure`

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `curl -fsS http://127.0.0.1:18186/admin/health`
- `curl -fsS http://127.0.0.1:18186/admin/version`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r47 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 --client-slug demo_salon --quality-lane dev --count 10 --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --allowlist-jids 77015705555@s.whatsapp.net,77785890765@s.whatsapp.net,77000000001@s.whatsapp.net,77000000002@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text ок --tool-hooks auto --tool-confirm-text да --tool-cancel-text отмена --tool-calendar-text проверь запись --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r49 --run-id a922-go2f-seed19-r49 --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --history-max 20 --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r49 --status done --strict-artifacts`

## Evidence
- `r47` manual audit artifacts
- `r49` summary, brief, responses, trace bundle, manual audit
- parity check output
- report file for this closure block

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only replay closure; no runtime code changes.
- **Go/no-go signals:** `r48` completes with valid artifacts and truthfully classifies the touched family.
- **Rollback:** no code rollback needed; discard non-canonical replay if run integrity fails.
- **Post-release monitoring window:** not applicable.

## Rollback
No code rollback. If a replay artifact is invalid/incomplete, stop and publish it as non-canonical instead of interpreting it as progress.

## No-go
- do not resume `r47`
- do not patch code in response to the fresh replay within this block
- do not open a second fresh replay
- do not use acceptance shortcuts or guard overrides

## Risks/blockers
- local runtime at `18186` may not yet reflect the latest worktree process state
- missing judge key would block the replay
- previous non-canonical replay audit debt can block the manual-audit gate until resolved

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate debt and global fallback debt remain outside the touched family; the broader pending booking continuity / terminal handoff cluster remains unimplemented here even after `r49` classification.
- **Why not in this block:** this is closure-only.
- **Risk if deferred:** if `r48` surfaces a new blocker, the next block must classify whether it belongs to the same hotspot or a different family.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-decision-a922.md`
- **Expiry/trigger to stop deferral:** immediate after `r49` audit.

## Next-block contract (mandatory)
- **Next block objective:** closure is already rejected by `r49`; publish the blocker and switch canon to the delete-first decision block.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r47 --status done --strict-artifacts`
- **Blocked-by conditions:** runtime parity mismatch, missing judge key, or incomplete `r47`/`r49` audit.
- **Owner role for closure:** Brain / Top Architect

## Execution outcome
- `r47`: audited, non-canonical, no replay resumed.
- `r48`: invalid `runtime_fingerprint_preflight`, audited as non-canonical.
- `r49`: fresh closure replay completed with `infra_valid=true`, `semantic_valid=false`, `responses_rows=143`, `dialogs_seen=10/10`, `strict_pass_rate=0.986`, and failure rows `002-09` plus `002-10`.
- Follow-up block opened: `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-decision-a922.md`
