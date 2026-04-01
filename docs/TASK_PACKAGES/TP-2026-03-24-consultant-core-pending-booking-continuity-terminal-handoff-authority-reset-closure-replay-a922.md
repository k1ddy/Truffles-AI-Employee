# TP-2026-03-24 Consultant Core Pending Booking Continuity Terminal Handoff Authority Reset Closure Replay A922

## Title/goal
Run exactly one fresh closure replay after the pending booking continuity / terminal handoff authority reset, using the locked `seed19` scenarios and baseline, to prove whether the touched family is now closed on live runtime parity or to truthfully surface the next blocker.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r49/{summary.json,brief.md,responses.jsonl,runtime_state.json}`

## Root cause (mandatory)
- **Symptom:** deterministic structural proof is green, but live closure is still unproven because the touched family has not yet been replayed once on fresh runtime parity after the authority reset.
- **Minimal reproduction:** replay the locked `seed19` scenarios against `http://127.0.0.1:18186` after confirming runtime parity and mandatory guards.
- **Evidence:** `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`, `/tmp/booking_quality/a922-go2f-seed19/summary.json`, `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`, and `/tmp/booking_quality/a922-go2f-seed19-r49/{summary.json,brief.md,responses.jsonl,runtime_state.json}`.
- **Five Whys:**
  1. Why is closure still open? Because structural proof does not replace one truthful live replay.
  2. Why can replay happen now? Because the touched authority seam has been reset and focused deterministic checks are green.
  3. Why only one replay? Because replay is closure-only now, not discovery.
  4. Why must runtime parity be checked first? Because stale runtime would invalidate any closure claim.
  5. Why reuse the locked scenarios/baseline? Because closure must stay comparable to the existing family evidence.
- **Root cause statement:** closure is blocked by missing fresh live evidence after the structural reset, not by missing deterministic proof.
- **Fix mechanism:** verify runtime parity plus mandatory guards, run one fresh guarded replay on the locked scenarios/baseline, audit the artifact, and publish closure truth without opening a new fix inside this block.

## Invariant
Do not modify runtime code in this block. Do not open a second fresh replay. Do not weaken gates or switch back into discovery mode.

## Scope
- verify runtime parity on `http://127.0.0.1:18186`
- rerun mandatory guards for the active block
- launch one fresh local replay with locked `seed19` scenarios/baseline
- audit and classify the result truthfully

## Out of scope
- new implementation
- new structural deletion block
- acceptance lock/full
- any second replay

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `/tmp/booking_quality/a922-go2f-seed19-r50/*`

## Plan (1..N)
1. Recheck runtime health/version parity and all required guards for the active structural block.
2. Run exactly one fresh guarded replay on `/tmp/booking_quality/a922-go2f-seed19/scenarios.json` against baseline `/tmp/booking_quality/a922-go2f-seed19/summary.json`.
3. Audit the fresh replay artifact with strict artifacts enabled.
4. Publish either closure success or the next truthful blocker; do not patch code in this block.

## DoD
- exactly one fresh replay artifact exists for this block
- runtime parity is recorded with exact evidence
- audit artifacts exist and truthfully classify the result
- canon is updated without code edits if closure succeeds or fails

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
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-go2f-seed19-r50 --owner-file truffles-api/app/core/booking_prompt_owner.py --owner-file truffles-api/app/services/reasoning_core.py --quick-check 'cd /home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922 && pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reactivation_candidate or pending_collect_reactivation or post_cancel_rebooking_state or promotions_interrupt_and_resumes_time_collect or explicit_handoff_owner or terminal_unresolved"' -- --base-url http://127.0.0.1:18186 --client-slug demo_salon --count 10 --scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json --baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.2 --max-wait 0.4 --allowlist-jids 77015705555@s.whatsapp.net,77785890765@s.whatsapp.net,77000000001@s.whatsapp.net,77000000002@s.whatsapp.net --jid-mode unique --allow-non-allowlist --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text 'ок' --tool-hooks auto --tool-confirm-text 'да' --tool-cancel-text 'отмена' --tool-calendar-text 'проверь запись' --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --output-dir /tmp/booking_quality/a922-go2f-seed19-r50 --history-max 20 --max-failures 0 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate off --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000 --quality-lane dev`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r50 --status done --strict-artifacts`

## Evidence
- parity check output
- guarded replay command and audit output
- `/tmp/booking_quality/a922-go2f-seed19-r50/{summary.json,brief.md,responses.jsonl,runtime_state.json,manual_audit.json}`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only replay closure; no runtime code changes.
- **Go/no-go signals:** runtime parity is exact, mandatory guards are green, and the replay artifact audits cleanly.
- **Rollback:** no code rollback; if replay is invalid/incomplete, stop and publish it as non-canonical.
- **Post-release monitoring window:** not applicable.

## Rollback
No code rollback. If the replay artifact is invalid or incomplete, classify it as non-canonical and stop.

## No-go
- no code edits in response to the replay
- no second fresh replay
- no gate weakening
- no discovery-mode follow-up inside this block

## Risks/blockers
- host shell is currently missing `OPENAI_API_KEY`; the replay is blocked unless the existing local key is sourced via explicit `--judge-api-key` or exported from available local runtime context
- runtime parity can still be invalidated if the local listener drifts after the preflight checks

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate debt and broader terminal fallback debt remain outside the touched family; a replay failure can still surface a new subfamily.
- **Why not in this block:** this block is closure-only.
- **Risk if deferred:** without one truthful replay, the team cannot claim the structural reset changed live behavior.
- **Linked follow-up Task Package(s):** if replay fails, open one new delete-first decision/implementation family; if replay passes, move to the next canonical blocker only.
- **Expiry/trigger to stop deferral:** immediate after `r50` audit.

## Next-block contract (mandatory)
- **Next block objective:** if `r50` fails, classify the first truthful blocker and open one bounded delete-first family; if `r50` passes, stop runtime work on this family.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r50 --status done --strict-artifacts`
- **Blocked-by conditions:** missing judge key, runtime parity mismatch, invalid/incomplete replay artifact, or any failed required guard.
- **Owner role for closure:** Brain / Top Architect
