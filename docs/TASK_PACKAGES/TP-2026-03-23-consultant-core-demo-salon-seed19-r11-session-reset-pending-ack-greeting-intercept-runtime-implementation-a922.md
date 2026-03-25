# TP-2026-03-23 - Consultant Core Demo Salon Seed19 R11 Session Reset Pending Ack Greeting Intercept Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R11-SESSION-RESET-PENDING-ACK-GREETING-INTERCEPT-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R11-SESSION-RESET-PENDING-ACK-GREETING-INTERCEPT-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_canary_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime repair so contaminated session-reset clear traffic with `pending_ack` text does not get consumed by the live greeting owner while the conversation is still `pending`. The fix is admissible only if the executable later greeting owner defers this contract-valid pending-ack path, the bounded deterministic regression proves it, and no frozen router is edited.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r11/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r11 --status done --strict-artifacts`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8108,8188p'`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '15240,15256p'`
  - `nl -ba truffles-api/app/routers/webhook/pending.py | sed -n '60,90p'`
  - `rg -n "greeting_owner|pending_ack" truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - fresh replay `r11` no longer stops on simulation transport; the first surviving blocker is pending-clear interception before any dialog turn executes
  - the executable later greeting owner at `truffles-api/app/services/reasoning_core.py:8108` answers `ок` as smalltalk while `conversation.state == pending`
  - frozen pending continuity already defines `pending_ack` semantics in `truffles-api/app/routers/webhook/pending.py`, so the bounded runtime repair can reuse that contract instead of adding new phrase logic
  - the live invocation point remains non-frozen at `truffles-api/app/services/reasoning_core.py:15246`
- `Detected drift (docs vs code)`:
  - current canon still points to the decision block; successful implementation must promote the implementation block and hand off one fresh replay

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs active form unexpected input unhappy paths official`
- **Date/time (local):** `2026-03-23T07:16:20+05:00`
- **Sources opened (from this query):** `https://rasa.com/docs/rasa/forms/`
- **Source quality:** `vendor documentation / primary source`
- **Existing solutions found:** active slot-collection flows should treat off-path input as an unhappy-path interruption and then return control to the active collection owner instead of silently consuming the turn as unrelated smalltalk.
- **Decision:** `reuse/integrate`
- **Reuse / integrate / build decision:** `reuse the existing pending-ack contract from the frozen pending continuity surface and integrate one defer guard into the live later greeting owner instead of widening smalltalk ownership or adding new phrase branches`
- **Rejected options:** `patching frozen pending.py`, `broadly disabling greeting owner in pending state`, `proof/oracle patch first`, `new regex or phrase hardcode in reasoning_core`

## Root cause (mandatory)
- **Symptom:** fresh replay `r11` stays non-canonical before any scenario turn because session-reset clear sends `ок`, the greeting owner answers it as smalltalk, and conversation state remains `pending`.
- **Minimal reproduction:** run the exact `seed19` replay after the simulation transport repair, then inspect `/tmp/booking_quality/a922-go2f-seed19-r11/manual_audit.json` plus the live greeting-owner path in `truffles-api/app/services/reasoning_core.py`.
- **Evidence:** replay stdout shows `Turn planner safe greeting owner sent` after `pending_ack`; decision/replay docs localize the live path to `reasoning_core.py:8108` and `:15246`; frozen pending continuity already recognizes the same text as `pending_ack` in `pending.py`.
- **Five Whys:** contaminated preflight needs to clear a pending conversation; it sends `ок`; the live greeting owner classifies `ок` as smalltalk; it finalizes a bot reply before pending continuity handles the turn; the conversation remains `pending` and the replay never starts.
- **Root cause statement:** the executable later greeting owner in `truffles-api/app/services/reasoning_core.py` does not defer `pending_ack` traffic while `conversation.state == pending`, so it steals a continuity-owned acknowledgement turn and prevents session-reset clear from completing.
- **Fix mechanism:** reuse the existing pending-ack contract to short-circuit the live greeting owner for `pending` conversations, then add a focused regression proving the owner returns `None` on that bounded path while existing bot-active ack smalltalk behavior stays covered by the current greeting-owner tests.

## Reuse-first plan (mandatory)
- Internal reuse:
  - pending-ack classifier in `truffles-api/app/routers/webhook/pending.py`
  - live later greeting-owner path in `truffles-api/app/services/reasoning_core.py`
  - existing greeting-owner regressions in `truffles-api/tests/test_reasoning_core.py`
- External reuse:
  - the one official Rasa forms source recorded above
- Why not reinvent the wheel:
  - the repo already has the continuity contract for `pending_ack`; the bug is that the live greeting owner does not honor it on the bounded pending-state path.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: the blocker is now a bounded live runtime contract bug on one executable owner family.
- `Family handled in this block`: `seed19 r11 session-reset pending-ack greeting intercept`
- `Closure artifact expected from this mode`: one implementation TP/report pair, focused deterministic proof, and replay handoff.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `15`
- `Code dominance`: `on`
- `Override token`: `none`
- `Why this profile fits`: the block makes one bounded non-frozen runtime change plus focused tests and canon sync.

## Invariant
- do not edit frozen webhook routers
- do not weaken replay/manual-audit/acceptance gates
- do not broaden the fix beyond pending-ack interception on the executable later greeting owner
- do not regress existing bot-active greeting/thanks/ack smalltalk behavior

## Scope
- patch the live later greeting owner so `pending_ack` traffic is deferred while the conversation state is `pending`
- add focused deterministic regression coverage for the bounded defer behavior
- sync canon/session/packet to the implementation result and hand off replay

## Out of scope
- replay itself
- proof/oracle changes
- acceptance evidence-pack work
- frozen-router edits
- generic cleanup of duplicate owner defs

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
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
2. Patch the executable later greeting owner so `pending_ack` traffic in `pending` state returns `None` before smalltalk finalization.
3. Add focused regression coverage proving the greeting owner defers the bounded pending-ack path and existing greeting-owner bot-active coverage stays intact.
4. Run focused tests and the mandatory guard/session stack.
5. Hand off one fresh exact replay on the same seed-`19` scenarios.

## DoD
- the live later greeting owner no longer consumes `pending_ack` while `conversation.state == pending`
- focused deterministic regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes one fresh exact replay

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "greeting_owner_family_defers_pending_ack or greeting_owner_family_bypasses_frozen_delegate"`
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
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic proof only; fresh replay stays in the next block
- **Stop condition:** if the fix requires frozen-router edits, generic pending-state smalltalk redesign, or broader duplicate-def cleanup outside the executable later greeting owner family, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused deterministic coverage, then mandatory guards
- **Go/no-go signals:** new pending-ack defer regression passes; existing greeting-owner bot-active regression remains green; architecture/session guards stay green
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
- no broad disable of greeting owner across all pending traffic
- no replay claim without fresh evidence

## Risks/Blockers
- `reasoning_core.py` still carries duplicate top-level defs, so the repair must stay on the executable later greeting owner only
- fresh replay may surface a deeper preflight family once pending-ack interception is repaired
- pending state may still have other smalltalk collisions; they are out of scope unless fresh replay proves they survive after this fix

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- other pending-state smalltalk collisions may still exist outside the exact `pending_ack` contract
- `reasoning_core.py` still carries duplicate top-level owner defs

### Why not in this block
- this block only repairs the exact surfaced pending-ack interception path

### Risk if deferred
- contaminated preflight clear remains blocked before any scenario turn can execute on fresh replay

### Linked follow-up Task Package(s)
- `rerun_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_canary_replay`

### Expiry/trigger to stop deferral
- stop deferral immediately if the next fresh replay still leaves `pending_ack` traffic on the greeting-owner path

## Next-block contract (mandatory)
### Next block objective
- prove the repaired pending-ack defer path on one fresh exact replay over the same seed-`19` scenarios

### First deterministic check command
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r12 --status done --strict-artifacts`

### Blocked-by conditions
- no fresh replay artifact exists after the runtime repair

### Owner role for closure
- `Brain / Top Architect`
