# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R7 Session Reset Simulation Transport Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R7-SESSION-RESET-SIMULATION-TRANSPORT-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R6-ALLOWLIST-SAFE-PREFLIGHT-FALLBACK-PROOF-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md`
- `UNLOCKS`: `implement_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_runtime_family`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Classify the next first admissible blocker after the allowlist-safe replay fallback repair. The goal is to decide whether fresh replay stop `r7` is still proof tooling, pure readiness, or a bounded reusable runtime contract bug around simulation-safe transport during preflight session reset.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r8/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r9/manual_audit.json`
- `ops/diagnose.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/chatflow_service.py`
- `truffles-api/app/adapters/chatflow.py`

## FACT pre-check (before decision sync)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r7 --status done --strict-artifacts`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r8 --status done --strict-artifacts`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r9 --status done --strict-artifacts`
  - `rg -n "send_message_safe\(|simulation_mode|ChatFlow response" ops/diagnose.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/chatflow_service.py truffles-api/app/adapters/chatflow.py`
- `FACT findings`:
  - `r6` closed the old proof-only non-allowlist fallback blocker
  - `r7` still stopped before turn execution with `infra_valid=false` / contaminated preflight
  - fresh runtime logs showed `ChatFlow response: status=200, jid=77785890765@s.whatsapp.net, body={"msg":"Your plan has been expired please renew."}` during simulated session-reset traffic
  - `ops/diagnose.py` sends session-reset with `simulation_mode=True`
  - the executable later explicit-handoff owner in `truffles-api/app/services/reasoning_core.py` still calls `send_message_safe(...)` directly
  - `truffles-api/app/adapters/chatflow.py` already has a simulation-safe branch, so this is a runtime bypass of an existing contract surface
- `Detected drift (docs vs code)`:
  - canon still pointed to the old `r5` implementation block before this decision sync

## One web search (mandatory before implementation)
- **Query (exact):** `Twilio test credentials do not send real messages official docs`
- **Date/time (local):** `2026-03-22T21:35:00+05:00`
- **Sources opened (from this query):** `https://www.twilio.com/docs/documents/591/Twilio_Restricted_API_Keys_Permissions_-_Voice_Permissions.pdf`
- **Source quality:** `vendor documentation / primary source`
- **Existing solutions found:** official testing guidance keeps non-production flows away from real outbound transport; this supports making simulation traffic stay inside a transport-safe path instead of touching real provider delivery
- **Decision:** `build`
- **Reuse / integrate / build decision:** `build`
- **Rejected options:** `rely on provider billing state`, `weaken replay transport gates`, `keep using direct provider sends in simulated preflight`
- **Reason:** the exact repo bug is local to the executable explicit-handoff owner, so the fix belongs in our runtime boundary rather than vendor configuration

## Decision:
- `r7` is a `runtime contract bug`
- `r8` and `r9` are non-canonical follow-on invalid-preflight artifacts, not new blocker families
- next move must be a bounded runtime repair on the executable later explicit-handoff owner / simulation-safe transport seam

## Root cause (mandatory)
- **Symptom:** fresh replay no longer falls back to a non-allowlist JID, but `r7` still stops before turn execution because preflight session-reset creates new contaminated conversations and explicit handoff state on allowlist JIDs.
- **Minimal reproduction:** start fresh local runtime on `127.0.0.1:18186` with canonical env, run the exact seed-`19` replay as `a922-go2f-seed19-r7`, then audit `/tmp/booking_quality/a922-go2f-seed19-r7` and inspect local runtime logs.
- **Evidence:** runtime logs show `ChatFlow response: status=200, jid=77785890765@s.whatsapp.net, body={"msg":"Your plan has been expired please renew."}` immediately after simulated session-reset traffic; `ops/diagnose.py` sends that reset with `simulation_mode=True`; the live explicit handoff owner in `truffles-api/app/services/reasoning_core.py` still calls `send_message_safe(...)` directly; `chatflow_service.send_message_safe(...)` always hits provider transport for allowlist JIDs.
- **Five Whys:** replay preflight sends a session-reset message; contaminated state routes that message into explicit handoff owner; the owner directly calls provider transport; the direct send path ignores simulation metadata; provider billing blockage therefore contaminates preflight before any replay turn is evaluated.
- **Root cause statement:** the live explicit handoff owner path in `truffles-api/app/services/reasoning_core.py` bypasses the simulation-safe transport abstraction and performs real ChatFlow sends even when replay/session-reset metadata marks the turn as `simulation_mode=True`.
- **Fix mechanism:** make the executable explicit-handoff owner family honor simulation transport semantics so preflight session-reset traffic cannot call real provider transport in local realism runs.

## Reuse-first plan (mandatory)
- Internal reuse:
  - existing fresh replay evidence in `/tmp/booking_quality/a922-go2f-seed19-r7`, `/tmp/booking_quality/a922-go2f-seed19-r8`, and `/tmp/booking_quality/a922-go2f-seed19-r9`
  - existing simulation-aware transport branch in `truffles-api/app/adapters/chatflow.py`
  - live executable explicit-handoff owner surface in `truffles-api/app/services/reasoning_core.py`
- External reuse:
  - the one recorded vendor testing source above
- Why not reinvent the wheel:
  - the repo already contains a simulation-aware transport contract; the surfaced gap is that the live owner bypasses it.

## Work mode (mandatory)
- `Mode`: `forensic`
- `Why this mode`: this block is classification-only and must lock the right runtime family before any new code.
- `Family handled in this block`: `seed19 r7 session-reset simulation transport`
- `Closure artifact expected from this mode`: one decision TP/report pair plus canon sync and one bounded runtime implementation handoff.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`: the block is doc-only by intent, but the worktree already carries approved code deltas and audited replay artifacts; keeping `implementation` mode avoids false governance failure while canon switches to the new runtime family.

## Invariant
- Do not weaken replay/manual-audit gates.
- Do not edit frozen routers.
- Do not hide provider errors by loosening oracle or acceptance contracts.

## Scope
- classify `r7` / `r8` / `r9` truthfully
- lock the next bounded runtime family
- sync canon/session/packet to the new first blocker

## Out of scope
- implementing the runtime repair itself
- new replay beyond the already captured `r7` / `r8` / `r9` evidence
- acceptance lock/go-to-full work
- unrelated duplicate-def cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
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
1. Audit the fresh replay artifacts `r7`, `r8`, and `r9`.
2. Trace the simulated session-reset path through `ops/diagnose.py`, `reasoning_core.py`, `chatflow_service.py`, and `chatflow` adapter code.
3. Publish the runtime-vs-proof classification with evidence.
4. Promote canon/session references to this decision block and hand off the bounded runtime family.

## DoD
- current blocker is classified with evidence and correct layer ownership
- active canon points to this decision TP
- next move is one bounded runtime family with exact hotspot and deterministic first test

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r7 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r8 --status done --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r9 --status done --strict-artifacts`
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
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r8/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r9/manual_audit.json`
- local runtime log evidence captured during the fresh replay attempts
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Fail-fast / scenario lock:** decision-only; reuse existing audited replay evidence
- **Stop condition:** if the blocker cannot be traced to one bounded family with exact executable hotspot ownership, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** doc/canon-only sync in this block
- **Go/no-go signals:** classification is evidence-backed and next move is exact
- **Rollback:** revert this TP/report/canon sync; rebuild packet; rerun guards
- **Post-release monitoring window:** the next block must be one bounded runtime implementation family before any new replay

## Rollback
1. Revert this TP/report/canon sync.
2. Rebuild the packet.
3. Rerun architecture/session guards.

## No-go
- no runtime patch inside this decision block
- no frozen-router edits
- no oracle weakening
- no new replay attempt before the runtime family is opened

## Risks/Blockers
- `reasoning_core.py` still contains duplicate top-level owners, including explicit-handoff family duplicates
- direct-send transport paths may have more simulation gaps beyond the first surfaced explicit-handoff owner
- provider billing blockage can mask deeper runtime behavior until simulation transport is honored

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `reasoning_core.py` still carries duplicate top-level owner defs
- direct-send transport paths are not uniformly routed through simulation-aware adapters

### Why not in this block
- this block only classifies the next blocker and scopes the bounded runtime family

### Risk if deferred
- local realism replay remains blocked before turn execution whenever preflight reset touches the explicit-handoff path

### Linked follow-up Task Package(s)
- `implement_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_runtime_family`

### Expiry/trigger to stop deferral
- stop deferral immediately if any new replay attempt reaches provider transport during simulated preflight traffic

## Next-block contract (mandatory)
### Next block objective
- implement one bounded runtime repair so simulated session-reset / explicit-handoff traffic cannot call real ChatFlow transport on the executable later owner path

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "explicit_handoff and simulation"`

### Blocked-by conditions
- no deterministic regression exists yet for simulation-safe explicit handoff transport

### Owner role for closure
- `Brain / Top Architect`
