# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R14 Session Reset Pending Ack Terminal Unresolved Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R14-SESSION-RESET-PENDING-ACK-TERMINAL-UNRESOLVED-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R14-SESSION-RESET-PENDING-ACK-TERMINAL-UNRESOLVED-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_r14_session_reset_pending_ack_terminal_unresolved_canary_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime repair so pending-state `pending_ack` session-reset traffic stops falling through to terminal unresolved fallback and instead reuses the existing pending continuity contract already codified in `state_service.py`. The fix is admissible only if it lands on a non-frozen path, proves deterministic behavior locally, and hands off exactly one fresh replay next.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r14/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
- `Baseline commands`:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r14 --status done --strict-artifacts`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '7414,7568p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15473,15498p'`
  - `nl -ba truffles-api/app/services/state_service.py | sed -n '1097,1179p'`
  - `nl -ba truffles-api/app/routers/webhook/pending.py | sed -n '82,110p'`
- `FACT findings`:
  - fresh replay `r14` no longer stops on greeting or explicit-handoff interception; the new first blocker is terminal unresolved fallback before any dialog turn starts
  - the executable non-frozen gap is now in `truffles-api/app/services/reasoning_core.py`: no owner picks up `pending_ack` after the greeting and explicit-handoff defer guards, so the request falls through to terminal unresolved
  - the repo already carries the correct continuity contract in `truffles-api/app/services/state_service.py:_resolve_pending_ack(...)` and frozen `pending.py` already consumes the same text via that contract
  - therefore the bounded repair is reuse/integration of the existing continuity owner contract, not a new semantic branch
- `Detected drift (docs vs code)`:
  - current canon still points to the decision block; successful implementation must promote this implementation block and hand off one replay

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs conversation resumed paused events official`
- **Date/time (local):** `2026-03-23T08:53:17+05:00`
- **Sources opened (from this query):** `https://rasa.com/docs/reference/primitives/events/`
- **Source quality:** `vendor documentation / primary source`
- **Existing solutions found:** paused/resumed conversation flow is modeled as an explicit evented state transition, not as a generic fallback; resume is a first-class continuity contract.
- **Decision:** `reuse/integrate`
- **Reuse / integrate / build decision:** `reuse the repo's existing pending continuity contract in state_service and integrate one non-frozen owner path in reasoning_core so pending-ack resume is handled explicitly before terminal fallback`
- **Rejected options:** `new phrase hardcode in reasoning_core`, `patch frozen pending.py`, `proof/oracle detour first`, `broad terminal fallback suppression`

## Root cause (mandatory)
- **Symptom:** fresh replay `r14` remains non-canonical before any dialog turn because session-reset preflight sends `ок`, no live owner handles it after the recent defer guards, and runtime falls into terminal unresolved.
- **Minimal reproduction:** replay the locked seed-`19` artifact on fresh runtime, inspect `/tmp/booking_quality/a922-go2f-seed19-r14/manual_audit.json`, then inspect the direct-owner chain in `truffles-api/app/services/reasoning_core.py`.
- **Evidence:** `r14` records `Reasoning core terminal unresolved response skipped`, `state_before=pending`, `state_after=pending`, `cleared=false`, `dialogs_seen=0`; `reasoning_core.py` now defers greeting and explicit-handoff for `pending_ack`; `state_service.py:_resolve_pending_ack(...)` already codifies the right pending-resume transition.
- **Five Whys:** contaminated preflight needs to acknowledge and clear `pending`; greeting no longer consumes `ок`; explicit handoff no longer consumes `ок`; no live continuity owner handles the same bounded path; execution falls through to terminal unresolved instead of reusing the existing pending-resume contract.
- **Root cause statement:** `reasoning_core.py` lacks a non-frozen continuity owner path that reuses `state_service._resolve_pending_ack(...)` after the greeting and explicit-handoff defer guards, so `pending_ack` session-reset traffic falls through to terminal unresolved even though the repo already has the correct continuity contract.
- **Fix mechanism:** add one bounded direct-owner helper in `reasoning_core.py` that detects `pending_ack` while `conversation.state == pending`, reuses `PendingContinuityRuntimeHooks + _resolve_pending_ack(...)`, sends the standard pending-ack reply through the existing transport pattern, and returns a `WebhookResponse` before terminal unresolved.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `truffles-api/app/services/state_service.py:_resolve_pending_ack(...)`
  - `truffles-api/app/services/state_service.py:PendingContinuityRuntimeHooks`
  - `truffles-api/app/routers/webhook/pending.py:_build_transport_webhook_response(...)`
  - existing pending-ack defer guards in `truffles-api/app/services/reasoning_core.py`
- External reuse:
  - the one official Rasa source recorded above
- Why not reinvent the wheel:
  - the repo already defines the continuity transition; only the current live owner chain fails to call it on this bounded path.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: the blocker is now one bounded non-frozen runtime contract gap with a clear reuse target.
- `Family handled in this block`: `seed19 r14 session-reset pending-ack terminal-unresolved`
- `Closure artifact expected from this mode`: implementation TP/report, focused deterministic proof, and replay handoff only.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `15`
- `Code dominance`: `on`
- `Override token`: `none`
- `Why this profile fits`: the block lands one bounded runtime helper plus one regression and canon sync.

## Invariant
- do not edit frozen webhook routers
- do not weaken replay/manual-audit/acceptance gates
- do not add semantic phrase branching beyond the existing pending continuity classifier reuse
- do not broaden the fix beyond pending-ack continuity before terminal unresolved

## Scope
- add one non-frozen pending-ack continuity owner path in `reasoning_core.py`
- wire that path into the live owner chain before terminal unresolved
- add focused deterministic regression proving pending state clears instead of falling through to terminal unresolved
- sync canon/session/packet to the implementation result and hand off replay

## Out of scope
- replay itself
- proof/oracle changes
- acceptance evidence-pack work
- frozen-router edits
- generic duplicate-def cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan (1..N)
1. Publish this implementation TP and promote canon/session references to the runtime implementation family.
2. Land one non-frozen pending-ack continuity owner in `reasoning_core.py` by reusing `state_service._resolve_pending_ack(...)`.
3. Add focused deterministic regression proving pending state clears before terminal unresolved on the bounded path.
4. Run focused tests and the mandatory guard/session stack.
5. Hand off one fresh exact replay on the same locked seed-`19` scenarios.

## DoD
- `pending_ack` while `conversation.state == pending` is handled before terminal unresolved fallback
- focused deterministic regression passes
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes one fresh exact replay

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_ack_continuity_family_clears_pending_before_terminal_unresolved or explicit_handoff_owner_family_defers_pending_ack or greeting_owner_family_defers_pending_ack"`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic proof only; fresh replay stays in the next block
- **Stop condition:** if the fix requires frozen-router edits, a broader pending-state redesign, or duplicate-def cleanup beyond the executable owner chain, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused deterministic coverage, then mandatory guards
- **Go/no-go signals:** new pending-ack continuity regression passes; existing greeting/explicit-handoff defer regressions stay green; architecture/session guards stay green
- **Rollback:** revert `reasoning_core.py`, `test_reasoning_core.py`, TP/report/canon sync; regenerate packet; rerun guards
- **Post-release monitoring window:** next block must be one fresh exact replay on the same locked seed-`19` scenarios

## Rollback
1. Revert the non-frozen runtime/test changes.
2. Revert this TP/report/canon sync.
3. Rebuild packet and rerun mandatory checks.

## No-go
- no frozen-router edits
- no second web query
- no proof/oracle patch first
- no broad terminal fallback suppression
- no replay claim without fresh evidence

## Risks/Blockers
- `reasoning_core.py` still carries duplicate top-level defs; the repair must stay on the executable later owner chain only
- fresh replay may surface another preflight family once terminal unresolved is repaired
- pending state may still have other owner collisions; they are out of scope unless the next replay proves they survive

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- other pending-state owner collisions may still exist outside the exact `pending_ack` contract
- `reasoning_core.py` still carries duplicate top-level owner defs

### Why not in this block
- this block only repairs the surfaced terminal-unresolved continuity gap

### Risk if deferred
- contaminated preflight clear remains blocked before any scenario turn can execute on fresh replay

### Linked follow-up Task Package(s)
- `rerun_consultant_core_demo_salon_seed19_r14_session_reset_pending_ack_terminal_unresolved_canary_replay`

### Expiry/trigger to stop deferral
- stop deferral immediately if the next fresh replay still leaves `pending_ack` traffic on terminal unresolved fallback

## Next-block contract (mandatory)
### Next block objective
- prove on one fresh exact replay that pending-state `pending_ack` now clears preflight instead of falling through to terminal unresolved

### First deterministic check command
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r15 --status done --strict-artifacts`

### Blocked-by conditions
- no fresh replay artifact exists after the runtime repair

### Owner role for closure
- `Brain / Top Architect`
