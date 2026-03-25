# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R14 Session Reset Pending Ack Terminal Unresolved Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R14-SESSION-RESET-PENDING-ACK-TERMINAL-UNRESOLVED-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R12-SESSION-RESET-PENDING-ACK-EXPLICIT-HANDOFF-INTERCEPT-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_r14_session_reset_pending_ack_terminal_unresolved_runtime_family`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Classify the first surviving blocker from fresh replay `r14` after the bounded pending-ack explicit-handoff-intercept repair. The decision is admissible only if it proves the old explicit-handoff blocker is no longer first and isolates the new blocker as one bounded runtime family before any further code change.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r13/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r14/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r14/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r14/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py`

## FACT pre-check (before decision sync)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r14 --status done --strict-artifacts`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8188,8290p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15578,15645p'`
- `FACT findings`:
  - invalid `r13` is now explicitly inadmissible because its strict audit records `invalid_runtime_fingerprint_preflight` with `admin_version_unreachable`
  - fresh `r14` no longer routes `pending_ack` through either the greeting owner or the explicit-handoff owner; preflight response is now `Reasoning core terminal unresolved response skipped`
  - fresh `r14` still fails before any scenario turn because `state_after` remains `pending` and contaminated preflight never clears
  - the executable live path is non-frozen: greeting / explicit-handoff defer guards now return `None`, and terminal unresolved closure returns the response at `truffles-api/app/services/reasoning_core.py:15639`
- `Detected drift (docs vs code)`:
  - current canon still points to the `r12` implementation block before this decision sync; it must now move to the `r14` decision block

## One web search (mandatory before implementation)
- **Query (exact):** `N/A - decision-only block`
- **Date/time (local):** `2026-03-23T08:19:38+05:00`
- **Sources opened (from this query):** `reused parent-family source only: https://rasa.com/docs/rasa/forms/`
- **Source quality:** `reused parent-family vendor documentation / primary source`
- **Existing solutions found:** `N/A`
- **Decision:** `defer`
- **Reuse / integrate / build decision:** `defer new implementation-family query until code work starts; reuse the parent family context only for this classification block`
- **Rejected options:** `opening a second implementation query before classification closure`

## Decision:
- `r14` is the first admissible fresh replay after the bounded explicit-handoff defer repair.
- The old explicit-handoff blocker is closed as first-stop evidence.
- The new first admissible blocker is a bounded `runtime contract bug` on pending-ack session-reset clear falling through to the terminal unresolved response path.
- The next honest move is `implement_consultant_core_demo_salon_seed19_r14_session_reset_pending_ack_terminal_unresolved_runtime_family`.

## Root cause (mandatory)
- **Symptom:** fresh replay `r14` still stops before turn execution, but no longer on explicit-handoff reuse/create.
- **Minimal reproduction:** start fresh local runtime, verify `/admin/version == HEAD` and `/admin/health`, strict-audit invalid `r13`, run exact replay `a922-go2f-seed19-r14`, then strict-audit the artifact.
- **Evidence:** `r14` summary/brief/manual audit plus replay stdout showing `pending_ack` now returns `Reasoning core terminal unresolved response skipped` with `bot_response="Извините, произошла ошибка. Попробуйте позже."` while `state_after` stays `pending` and contamination reasons still include recent pending / trace-bearing conversations.
- **Five Whys:** session reset enters `pending`; preflight clear sends `ок`; the greeting owner now defers correctly; the explicit-handoff owner also now defers correctly; no direct owner claims the ack; the request falls into terminal unresolved fallback, which emits a generic error/skip response instead of clearing pending state; replay stays non-canonical.
- **Root cause statement:** after the greeting-owner and explicit-handoff defer repairs, the executable runtime has no bounded pending-clear owner for `pending_ack`, so the request falls through to the terminal unresolved closure in `truffles-api/app/services/reasoning_core.py` and leaves the conversation contaminated in `pending` state.
- **Fix mechanism:** the next implementation must keep pending-state `pending_ack` traffic out of the terminal unresolved fallback and route it through a bounded pending-clear contract so session-reset preflight can actually resolve.

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing replay artifacts `r13` and `r14`
  - live terminal unresolved closure in `truffles-api/app/services/reasoning_core.py`
  - parent `r12` implementation/replay family docs
- External reuse:
  - reused parent-family source only; no new query in this decision block
- Why not reinvent the wheel:
  - this block is classification-only; no new implementation is admissible yet

## Work mode (mandatory)
- `Mode`: `forensic`
- `Why this mode`: the new blocker surfaced on fresh replay and must be classified before code
- `Family handled in this block`: `seed19 r14 session-reset pending-ack terminal unresolved`
- `Closure artifact expected from this mode`: bounded decision TP/report and canon sync only

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `forensic`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: this block records replay truth and isolates the next runtime family without opening code changes

## Invariant
- no new runtime patch before classification is written down
- no frozen-router edits
- the old explicit-handoff family must stay closed unless fresh evidence reopens it
- the new blocker must be localized to an executable non-frozen path

## Scope
- classify fresh `r14` as the first admissible post-fix replay artifact
- isolate whether the new blocker is runtime, proof, or transport
- localize the executable terminal unresolved path and shadow-risk
- hand off one exact next move

## Out of scope
- implementation
- replay reruns
- acceptance lock/full work
- proof/oracle patches

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
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
1. Read strict audit for invalid `r13` and fresh replay `r14` together.
2. Prove whether the explicit-handoff blocker is still first.
3. Map the new first blocker to the live terminal unresolved path and record the shadow/defer context.
4. Hand off one bounded runtime family and nothing broader.

## DoD
- invalid `r13` is explicitly excluded as non-canonical
- fresh `r14` is classified truthfully
- the old explicit-handoff family is explicitly closed as first-stop evidence
- the next move is one bounded runtime family, not replay churn or proof drift

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r13 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r14 --status done --strict-artifacts`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8188,8290p'`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15578,15645p'`

## Evidence
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r13/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r14/{summary.json,brief.md,manual_audit.json}`
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
- no reopening the explicit-handoff family without fresh evidence

## Risks/Blockers
- duplicate owner defs remain in `truffles-api/app/services/reasoning_core.py`
- pending-clear may still involve deeper legacy continuity surfaces after terminal unresolved is repaired
- a later replay may surface yet another preflight family once terminal unresolved is repaired

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duplicate owner defs remain in `truffles-api/app/services/reasoning_core.py`
- contaminated preflight still depends on legacy pending-clear behavior downstream of greeting + explicit-handoff defer

### Why not in this block
- this block only classifies the new first blocker after the fresh replay

### Risk if deferred
- the team will patch the wrong family or rerun replay without truthful blocker split

### Linked follow-up Task Package(s)
- `implement_consultant_core_demo_salon_seed19_r14_session_reset_pending_ack_terminal_unresolved_runtime_family`

### Expiry/trigger to stop deferral
- stop deferral immediately if any new code change is proposed before this classification is published

## Next-block contract (mandatory)
### Next block objective
- keep pending-ack session-reset clear traffic out of the terminal unresolved fallback so contaminated preflight can actually clear pending state

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "explicit_handoff_owner_family_defers_pending_ack or greeting_owner_family_defers_pending_ack"`

### Blocked-by conditions
- the terminal unresolved fallback cannot be localized to an executable non-frozen path

### Owner role for closure
- `Brain / Top Architect`
