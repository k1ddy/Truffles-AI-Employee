# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R7 Session Reset Simulation Transport Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R7-SESSION-RESET-SIMULATION-TRANSPORT-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R7-SESSION-RESET-SIMULATION-TRANSPORT-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_canary_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime repair so simulated preflight session-reset traffic cannot call real ChatFlow transport on the executable later explicit-handoff owner path. The fix is admissible only if `simulation_mode=True` reuses a simulation-safe transport surface, direct provider transport is bypassed in that family, and focused deterministic coverage proves the contract.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`
- `ops/diagnose.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/chatflow_service.py`
- `truffles-api/app/adapters/chatflow.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r7 --status done --strict-artifacts`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '8143,8365p'`
  - `nl -ba truffles-api/app/adapters/chatflow.py | sed -n '1,60p'`
  - `rg -n "Turn planner safe explicit handoff sent|explicit_handoff" truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - `r7` stops before turn execution because simulated session-reset traffic still reaches provider transport
  - the executable later explicit-handoff owner directly calls `send_message_safe(...)`
  - `ChatFlowAdapter.send_text(...)` already has a simulation-safe branch keyed by `options.extra.simulation_mode`
  - the bounded fix can stay on the live later owner surface and reuse that adapter contract
- `Detected drift (docs vs code)`:
  - current canon is on the decision block; successful implementation must promote the implementation block and hand off one fresh replay

## One web search (mandatory before implementation)
- **Query (exact):** `Twilio test credentials do not send real messages official docs`
- **Date/time (local):** `2026-03-22T21:35:00+05:00`
- **Sources opened (from this query):** `https://www.twilio.com/docs/documents/591/Twilio_Restricted_API_Keys_Permissions_-_Voice_Permissions.pdf`
- **Source quality:** `vendor documentation / primary source`
- **Existing solutions found:** non-production/test flows should not hit real outbound transport; simulated delivery must stay on a transport-safe path
- **Decision:** `reuse/integrate`
- **Reuse / integrate / build decision:** `reuse existing simulation-aware transport surface in ChatFlow adapter and integrate it into the live explicit-handoff owner path`
- **Rejected options:** `provider billing workaround`, `oracle weakening`, `environment-only workaround`, `new transport abstraction unrelated to the surfaced owner path`

## Root cause (mandatory)
- **Symptom:** fresh replay `r7` stops in preflight because session-reset traffic with `simulation_mode=True` still creates explicit handoff traffic that reaches real provider transport.
- **Minimal reproduction:** run the exact seed-`19` replay after the fallback proof fix; inspect `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json` and local runtime logs.
- **Evidence:** runtime logs show provider responses on allowlist JIDs during simulated reset traffic; the live later explicit-handoff owner still calls `send_message_safe(...)`; the adapter layer already supports simulation-safe sends.
- **Five Whys:** replay uses simulated session reset; contaminated state routes into explicit handoff owner; that owner bypasses the adapter; the direct send path ignores simulation metadata; provider transport contaminates the replay before any scenario turn can be evaluated.
- **Root cause statement:** the executable later explicit-handoff owner in `truffles-api/app/services/reasoning_core.py` bypasses the existing simulation-aware ChatFlow adapter and calls direct provider transport even when webhook metadata marks the turn as simulated.
- **Fix mechanism:** route simulated explicit-handoff sends through the simulation-aware adapter contract and expose transport simulation evidence in trace/meta.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `truffles-api/app/adapters/chatflow.py`
  - `truffles-api/app/ports/messaging.py`
  - existing explicit-handoff tests in `truffles-api/tests/test_reasoning_core.py`
- External reuse:
  - the one vendor testing source recorded above
- Why not reinvent the wheel:
  - the repo already contains the simulation-safe transport branch; the bug is that the live owner bypasses it.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: the blocker is now a bounded live runtime contract bug on one executable owner family.
- `Family handled in this block`: `seed19 r7 session-reset simulation transport`
- `Closure artifact expected from this mode`: one implementation TP/report pair, focused deterministic proof, and replay handoff.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `15`
- `Code dominance`: `on`
- `Override token`: `none`
- `Why this profile fits`: the block makes one bounded non-frozen runtime change plus focused tests and canon sync.

## Invariant
- do not edit frozen webhook routers
- do not weaken replay/manual-audit gates
- do not widen duplicate-def cleanup beyond the executable later explicit-handoff owner family
- do not change provider billing classification or acceptance thresholds

## Scope
- patch the live later explicit-handoff owner so `simulation_mode=True` uses simulation-safe transport
- add focused deterministic regression coverage for explicit handoff simulation transport
- sync canon/session/packet to the implementation result and hand off replay

## Out of scope
- replay itself
- proof/oracle changes
- acceptance evidence-pack work
- frozen-router edits
- unrelated transport cleanup outside the surfaced owner family

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
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
2. Patch the executable later explicit-handoff owner so simulated sends reuse the simulation-aware ChatFlow adapter instead of direct provider transport.
3. Add focused regression coverage proving direct `send_message_safe(...)` is bypassed when `simulation_mode=True`.
4. Run focused tests and the mandatory guard/session stack.
5. Hand off one fresh exact replay on the same seed-`19` scenarios.

## DoD
- simulated explicit-handoff transport no longer calls real provider send in the executable later owner path
- focused deterministic regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes one fresh exact replay

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "explicit_handoff_owner_bypasses_frozen_delegate_create_path or explicit_handoff_owner_uses_simulation_safe_transport or explicit_handoff_owner_bypasses_frozen_delegate_reuse_path"`
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
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic proof only; fresh replay stays in the next block
- **Stop condition:** if the fix requires frozen-router edits or broader transport refactor outside the executable later explicit-handoff owner family, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused deterministic coverage, then mandatory guards
- **Go/no-go signals:** new simulation transport regression passes; adjacent explicit-handoff regression stays green; architecture/session guards stay green
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
- no provider-billing workaround instead of runtime simulation fix
- no replay claim without fresh evidence

## Risks/Blockers
- the hotspot still carries duplicate top-level defs, so the repair must stay on the executable later explicit-handoff owner only
- fresh replay may surface a deeper downstream family once simulated preflight transport is repaired
- adjacent direct-send paths may still carry similar simulation gaps; they are out of scope unless the focused regression proves otherwise

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- other direct-send transport paths may still bypass simulation-aware adapters
- `reasoning_core.py` still carries duplicate top-level owner defs

### Why not in this block
- this block only repairs the exact surfaced explicit-handoff simulation path

### Risk if deferred
- local realism replay remains blocked before turn execution whenever preflight reset hits this owner family

### Linked follow-up Task Package(s)
- `rerun_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_canary_replay`

### Expiry/trigger to stop deferral
- stop deferral immediately if the next fresh replay still hits provider transport under simulated preflight traffic

## Next-block contract (mandatory)
### Next block objective
- prove the repaired explicit-handoff simulation transport family on one fresh exact replay over the same seed-`19` scenarios

### First deterministic check command
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done --strict-artifacts`

### Blocked-by conditions
- no fresh replay artifact exists after the runtime repair

### Owner role for closure
- `Brain / Top Architect`
