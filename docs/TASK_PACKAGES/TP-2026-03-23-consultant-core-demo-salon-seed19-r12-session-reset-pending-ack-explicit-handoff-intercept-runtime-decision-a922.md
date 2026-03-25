# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R12 Session Reset Pending Ack Explicit Handoff Intercept Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R12-SESSION-RESET-PENDING-ACK-EXPLICIT-HANDOFF-INTERCEPT-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R11-SESSION-RESET-PENDING-ACK-GREETING-INTERCEPT-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_r12_session_reset_pending_ack_explicit_handoff_intercept_runtime_family`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Classify the first surviving blocker from fresh replay `r12` after the bounded pending-ack greeting-intercept repair. The decision is admissible only if it proves the old greeting-owner blocker is no longer first and isolates the new blocker as one bounded runtime family before any further code change.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r12/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r12/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r12/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py`

## FACT pre-check (before decision sync)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r12 --status done --strict-artifacts`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8217,8285p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15275,15308p'`
- `FACT findings`:
  - fresh `r12` no longer routes `pending_ack` through the greeting owner; replay stdout now returns `Turn planner safe explicit handoff sent` on the same preflight path
  - fresh `r12` still fails before any scenario turn because `pending_ack` remains unresolved and `state_after` stays `pending`
  - the executable live path is non-frozen: explicit-handoff owner body at `truffles-api/app/services/reasoning_core.py:8217` and early invocation at `truffles-api/app/services/reasoning_core.py:15300`
  - the live owner still permits `conversation.state == pending` at `truffles-api/app/services/reasoning_core.py:8278`, so contaminated preflight can re-enter the handoff owner instead of clearing state
- `Detected drift (docs vs code)`:
  - current canon still points to the `r11` implementation block before this decision sync; it must now move to the `r12` decision block

## One web search (mandatory before implementation)
- **Query (exact):** `N/A - decision-only block`
- **Date/time (local):** `2026-03-23T07:48:00+05:00`
- **Sources opened (from this query):** `reused parent-family source only: https://rasa.com/docs/rasa/forms/`
- **Source quality:** `reused parent-family vendor documentation / primary source`
- **Existing solutions found:** `N/A`
- **Decision:** `defer`
- **Reuse / integrate / build decision:** `defer new implementation-family query until code work starts; reuse the parent family context only for this classification block`
- **Rejected options:** `opening a second implementation query before classification closure`

## Decision:
- `r12` is the first admissible fresh replay after the bounded greeting-owner repair.
- The old greeting-owner blocker is closed as first-stop evidence.
- The new first admissible blocker is a bounded `runtime contract bug` on pending-ack interception by the live explicit-handoff owner during session-reset preflight clear.
- The next honest move is `implement_consultant_core_demo_salon_seed19_r12_session_reset_pending_ack_explicit_handoff_intercept_runtime_family`.

## Root cause (mandatory)
- **Symptom:** fresh replay `r12` still stops before turn execution, but no longer on greeting-owner smalltalk.
- **Minimal reproduction:** start fresh local runtime, verify `/admin/version == HEAD` and `/admin/health`, run exact replay `a922-go2f-seed19-r12`, then strict-audit the artifact.
- **Evidence:** `r12` summary/brief/manual audit plus replay stdout showing `pending_ack` now returns `Turn planner safe explicit handoff sent` while `state_after` stays `pending` and contamination reasons still include `reset_ack_missing`.
- **Five Whys:** session reset enters `pending`; preflight clear sends `ок`; the greeting owner now defers correctly; the next live owner path is explicit handoff; that owner is still allowed in `pending` state and re-sends handoff instead of clearing the state; contaminated preflight never clears, so replay stays non-canonical.
- **Root cause statement:** after the greeting-owner defer repair, the executable later explicit-handoff owner in `truffles-api/app/services/reasoning_core.py` still accepts pending-state `pending_ack` traffic during session-reset clear, so it reopens/reuses handoff instead of letting the pending-clear contract resolve the acknowledgement.
- **Fix mechanism:** the next implementation must keep pending-state `pending_ack` traffic out of the live explicit-handoff owner path during session-reset clear, then replay the same scenarios again.

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing replay artifact `r12`
  - live explicit-handoff owner path in `truffles-api/app/services/reasoning_core.py`
  - parent `r11` implementation/replay family docs
- External reuse:
  - reused parent-family source only; no new query in this decision block
- Why not reinvent the wheel:
  - this block is classification-only; no new implementation is admissible yet

## Work mode (mandatory)
- `Mode`: `forensic`
- `Why this mode`: the new blocker surfaced on fresh replay and must be classified before code
- `Family handled in this block`: `seed19 r12 session-reset pending-ack explicit-handoff intercept`
- `Closure artifact expected from this mode`: bounded decision TP/report and canon sync only

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `forensic`
- `Doc touch budget (files)`: `16`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: this block records replay truth and isolates the next runtime family without opening code changes

## Invariant
- no new runtime patch before classification is written down
- no frozen-router edits
- the old greeting-owner family must stay closed unless fresh evidence reopens it
- the new blocker must be localized to an executable non-frozen path

## Scope
- classify fresh `r12` as the first admissible post-fix replay artifact
- isolate whether the new blocker is runtime, proof, or transport
- localize the executable explicit-handoff path and shadow-risk
- hand off one exact next move

## Out of scope
- implementation
- replay reruns
- acceptance lock/full work
- proof/oracle patches

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md`
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
1. Read fresh `r12` replay artifacts and strict audit together.
2. Prove whether the greeting-owner blocker is still first.
3. Map the new first blocker to the live executable explicit-handoff path and record the shadow-risk.
4. Hand off one bounded runtime family and nothing broader.

## DoD
- fresh `r12` is classified truthfully
- the old greeting-owner family is explicitly closed as first-stop evidence
- the next move is one bounded runtime family, not replay churn or proof drift

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r12 --status done --strict-artifacts`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8217,8285p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15275,15308p'`

## Evidence
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r12/{summary.json,brief.md,manual_audit.json}`
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
- no reopening the greeting-owner family without fresh evidence

## Risks/Blockers
- explicit-handoff owner remains a duplicate/shadowed top-level family in `truffles-api/app/services/reasoning_core.py` (`3296` shadowed by executable later body at `8217`)
- pending-clear may still involve deeper legacy continuity surfaces after this intercept is repaired
- a later replay may surface yet another preflight family once the explicit-handoff intercept is repaired

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duplicate owner defs remain in `truffles-api/app/services/reasoning_core.py`
- contaminated preflight still depends on legacy pending-clear behavior downstream of the explicit-handoff intercept

### Why not in this block
- this block only classifies the new first blocker after the fresh replay

### Risk if deferred
- the team will patch the wrong family or rerun replay without truthful blocker split

### Linked follow-up Task Package(s)
- `implement_consultant_core_demo_salon_seed19_r12_session_reset_pending_ack_explicit_handoff_intercept_runtime_family`

### Expiry/trigger to stop deferral
- stop deferral immediately if any new code change is proposed before this classification is published

## Next-block contract (mandatory)
### Next block objective
- keep pending-ack session-reset clear traffic out of the live explicit-handoff owner path so contaminated preflight can actually clear pending state

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "explicit_handoff_owner"`

### Blocked-by conditions
- the explicit-handoff intercept cannot be localized to an executable non-frozen path

### Owner role for closure
- `Brain / Top Architect`
