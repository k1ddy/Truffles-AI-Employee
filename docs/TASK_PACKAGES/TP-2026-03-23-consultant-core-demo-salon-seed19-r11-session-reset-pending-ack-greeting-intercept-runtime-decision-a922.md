# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R11 Session Reset Pending Ack Greeting Intercept Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R11-SESSION-RESET-PENDING-ACK-GREETING-INTERCEPT-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R7-SESSION-RESET-SIMULATION-TRANSPORT-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_runtime_family`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Classify the first surviving blocker from fresh replay `r11` after the explicit-handoff simulation transport repair. The decision is admissible only if it proves the old transport blocker is no longer first and isolates the new blocker as one bounded runtime family before any further code change.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r10/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r11/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r11/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r11/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py`

## FACT pre-check (before decision sync)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r11 --status done --strict-artifacts`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8108,8185p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15240,15258p'`
- `FACT findings`:
  - stale `r10` is non-canonical and cannot count as replay truth
  - fresh `r11` no longer stops on provider transport; replay stdout showed `Turn planner safe explicit handoff sent` with `decision_meta.transport_simulated=true`
  - fresh `r11` still fails before any scenario turn because `pending_ack` is answered by the live greeting owner and leaves the conversation `pending`
  - the executable path is non-frozen: greeting owner body at `truffles-api/app/services/reasoning_core.py:8108` and early invocation at `truffles-api/app/services/reasoning_core.py:15246`
- `Detected drift (docs vs code)`:
  - current canon still pointed at the simulation-transport implementation block before this decision sync; it must now move to the `r11` decision block

## One web search (mandatory before implementation)
- **Query (exact):** `N/A - decision-only block`
- **Date/time (local):** `2026-03-23T00:18:00+05:00`
- **Sources opened (from this query):** `reused context only: https://www.twilio.com/docs/documents/591/Twilio_Restricted_API_Keys_Permissions_-_Voice_Permissions.pdf`
- **Source quality:** `reused parent-family vendor documentation / primary source; no new query in this decision-only block`
- **Existing solutions found:** `N/A`
- **Decision:** `defer`
- **Reuse / integrate / build decision:** `defer new implementation-family query until code work starts; reuse the parent family query recorded in docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md for current context only`
- **Rejected options:** `opening a second implementation query before classification closure`

## Decision:
- `r10` is excluded as stale/non-canonical.
- `r11` is the first admissible fresh replay after the transport repair.
- The old provider-transport blocker is closed as first-stop evidence.
- The new first admissible blocker is a bounded `runtime contract bug` on pending-ack interception by the live greeting owner during session-reset preflight clear.
- The next honest move is `implement_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_runtime_family`.

## Root cause (mandatory)
- **Symptom:** fresh replay `r11` still stops before turn execution, but no longer on provider transport.
- **Minimal reproduction:** start fresh local runtime, verify `/admin/version == HEAD`, run exact replay `a922-go2f-seed19-r11`, then strict-audit the artifact.
- **Evidence:** stale `r10` manual audit, fresh `r11` summary/brief/manual audit, replay stdout showing `Turn planner safe explicit handoff sent` with `transport_simulated=true`, then repeated `pending_ack` -> `Turn planner safe greeting owner sent` while `state_after` stays `pending`.
- **Five Whys:** session reset now uses simulation-safe transport; contaminated preflight then tries to clear pending state with `ок`; the live greeting owner intercepts that smalltalk before pending-clear logic resolves it; conversation stays pending; contaminated preflight never clears; replay stays non-canonical.
- **Root cause statement:** the live greeting owner runs before pending-clear resolution and does not defer `pending_ack` traffic while the conversation is still `pending`, so preflight clear loops on greeting-owner replies instead of clearing state.
- **Fix mechanism:** expected next implementation must keep `pending_ack` traffic out of the live greeting owner path during session-reset clear, then replay the same scenarios again.

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing replay artifacts `r10` and `r11`
  - live greeting-owner path in `truffles-api/app/services/reasoning_core.py`
  - parent simulation-transport implementation TP/report for context
- External reuse:
  - reused parent-family source only; no new query in this decision block
- Why not reinvent the wheel:
  - this block is classification-only; no new implementation is admissible yet

## Work mode (mandatory)
- `Mode`: `forensic`
- `Why this mode`: the new blocker surfaced on fresh replay and must be classified before code
- `Family handled in this block`: `seed19 r11 session-reset pending-ack greeting intercept`
- `Closure artifact expected from this mode`: bounded decision TP/report and canon sync only

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `forensic`
- `Doc touch budget (files)`: `14`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: this block records replay truth and isolates the next runtime family without opening code changes

## Invariant
- no new runtime patch before classification is written down
- no frozen-router edits
- stale `r10` must stay excluded from closure evidence
- the old simulation-transport family must not be re-opened without new evidence

## Scope
- classify stale `r10` as non-canonical
- classify fresh `r11` as the first admissible post-fix replay artifact
- isolate whether the new blocker is runtime, proof, or transport
- hand off one exact next move

## Out of scope
- implementation
- replay reruns
- acceptance lock/full work
- proof/oracle patches

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Read stale `r10` and fresh `r11` artifacts together.
2. Prove whether the explicit-handoff transport blocker is still first.
3. Map the new first blocker to the live executable path.
4. Hand off one bounded runtime family and nothing broader.

## DoD
- stale `r10` is explicitly excluded from closure evidence
- fresh `r11` is classified truthfully
- the next move is one bounded runtime family, not generic replay churn

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r11 --status done --strict-artifacts`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8108,8185p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15240,15258p'`

## Evidence
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r10/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r11/{summary.json,brief.md,manual_audit.json}`
- `truffles-api/app/services/reasoning_core.py`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Fail-fast / scenario lock:** no new replay in this decision block
- **Stop condition:** if the new blocker cannot be localized to an executable non-frozen path, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** decision-only; no runtime rollout in this block
- **Go/no-go signals:** truthful replay classification is published and points to one bounded runtime family
- **Rollback:** revert this TP/report/canon sync and regenerate packet
- **Post-release monitoring window:** next block must be one bounded implementation-family TP or a truthful `GAP`

## Rollback
- revert the decision/replay docs and canon sync if this classification proves incorrect

## No-go
- no code changes
- no replay rerun before this decision is published
- no reopening the transport family without fresh evidence

## Risks/Blockers
- duplicate owner defs remain in `truffles-api/app/services/reasoning_core.py`
- the pending-clear path may still involve frozen legacy surfaces downstream even though the first intercept is non-frozen
- a later replay may surface yet another preflight family once the greeting intercept is repaired

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duplicate owner defs remain in `truffles-api/app/services/reasoning_core.py`
- contaminated preflight still depends on legacy pending-clear behavior

### Why not in this block
- this block only classifies the new first blocker after the transport repair replay

### Risk if deferred
- the team will patch the wrong family or re-run replay without a truthful blocker split

### Linked follow-up Task Package(s)
- `implement_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_runtime_family`

### Expiry/trigger to stop deferral
- stop deferral immediately if any new code change is proposed before this classification is published

## Next-block contract (mandatory)
### Next block objective
- keep pending-ack session-reset clear traffic out of the live greeting owner path so contaminated preflight can actually clear pending state

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_ack or greeting_owner"`

### Blocked-by conditions
- the greeting-owner intercept cannot be localized to an executable non-frozen path

### Owner role for closure
- `Brain / Top Architect`
