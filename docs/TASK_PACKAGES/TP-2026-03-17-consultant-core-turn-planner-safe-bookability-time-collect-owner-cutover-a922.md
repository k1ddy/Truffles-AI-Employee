# TP-2026-03-17-consultant-core-turn-planner-safe-bookability-time-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-BOOKABILITY-TIME-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-EXECUTOR-BOUNDARY-DECISION-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-decision-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOOKING-COLLECT-OWNER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded legacy semantic seam: deterministic `booking` collect path for `missing_temporal_scope` should no longer enter frozen `truffles-api/app/routers/webhook/decision.py`. `reasoning_core` must consume the existing policy snapshot directly, reuse the shared collect finalizer, and send the existing deterministic slot-guidance reply without adding any new bridge family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-executor-boundary-decision-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "bookability_time_collect|missing_temporal_scope|safe_bookability" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
  - `sed -n '4780,4860p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1590,1760p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - reasoning-core already primes a bounded `missing_temporal_scope` policy override for delegate
  - shared collect finalization already exists and is used by pricing/duration/master-query collect owner cuts
  - this slice is deterministic and does not require new tool execution or new phrase routing
- `Detected drift (docs vs code)`: the bounded bookability time collect seam is still bridge-only progress; frozen `decision.py` remains the semantic owner even though the new core already has the required collect finalizer.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dict get official docs`
- **Date/time (local):** `2026-03-17 09:59 +0500`
- **Why this query is precise:** this block reuses narrow dict metadata surfaces from policy snapshots and reply metadata; standard-library mapping access is sufficient and preferable to introducing a new internal wrapper type for one bounded owner cut.
- **Sources opened (from this query):**
  - `Built-in Types` — `https://docs.python.org/3/library/stdtypes.html#dict.get`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dict.get` is the standard-library way to safely consume optional metadata keys without widening the control surface or adding exception-driven branching.
- **Decision:** `reuse + integrate` — keep this block on the existing policy snapshot / reply-meta dict surfaces and add only the bounded owner cutover logic.
- **Rejected options:**
  - add a new wrapper model just for this collect seam
  - keep the seam as delegate-only bridge
  - touch frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic `missing_temporal_scope` booking collect turns are still only primed for delegate; the first semantic owner for that normal path remains frozen `decision.py`.
- **Minimal reproduction:**
  1. Run the existing reasoning-core test for bookability time collect priming.
  2. Observe that reasoning-core sets the override but still hands the turn to `decision_router._handle_webhook_payload(...)`.
  3. Compare with existing direct collect owner cuts for pricing/duration/master-query, which already bypass frozen legacy and finalize collect continuity in new core.
- **Evidence to capture:**
  - direct owner path for `missing_temporal_scope` bypasses frozen delegate
  - expected-reply / canonical dialog state stay correct through the shared collect finalizer
- **Five Whys (or equivalent):**
  1. Why does this seam still enter legacy? Because only the bridge was implemented originally.
  2. Why is that a problem? Because it leaves another deterministic normal path under frozen semantic ownership.
  3. Why is this slice safe to cut over? Because the semantic decision is already made by the policy snapshot and the reply is deterministic slot-guidance.
  4. Why not widen into broader booking followups now? Because this block should delete one bounded authority seam without dragging in more stateful availability families.
  5. Why now? Because boundary micro-seams are no longer the main bottleneck, and this is the next reusable collect-owner slice.
- **Root cause statement:** the `missing_temporal_scope` booking collect family stopped at ingress priming and never completed the owner replacement into the shared collect finalizer.
- **Fix mechanism:**
  - add a bounded candidate/handler for the safe `missing_temporal_scope` collect slice
  - align the existing policy snapshot so the shared collect finalizer receives the canonical `pending_question_*` contract for time guidance
  - reuse the shared owner-cutover finalizer with deterministic slot-guidance reply text and canonical collect state
  - add focused regressions for direct bypass and bounded fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing policy snapshot detection for `missing_temporal_scope`
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing deterministic slot-guidance prompt already exposed by frozen runtime helpers
- **External reuse:**
  - official Python `dict.get` documentation
- **Why not reinvent the wheel:** this block should consume an already-proven snapshot and finalizer path instead of inventing a new booking collect mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into broader booking followup families.
- Existing shared collect finalizer semantics must remain contract-equivalent.

## Scope
- Add a bounded direct owner path for deterministic `missing_temporal_scope` booking collect replies.
- Reuse the shared collect finalizer for expected-reply / question-contract / canonical dialog state.
- Add focused reasoning-core regression coverage.
- Sync canon/session artifacts.

## Out of scope
- deictic/exact-time/date-range booking followup owner cuts
- new boundary-owner slices
- continuity work outside shared collect finalization
- frozen legacy semantic files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-bookability-time-collect-owner-cutover-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add a bounded safe candidate/handler for `missing_temporal_scope` collect owner cutover in `reasoning_core.py`.
3. Route the handler through the existing shared collect finalizer using the deterministic slot-guidance reply.
4. Add focused reasoning-core regressions for bypass + bounded fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic `missing_temporal_scope` booking collect turns bypass frozen `decision.py`
- shared collect finalizer writes expected reply / canonical dialog state for this seam
- bounded fallback still delegates cleanly when the snapshot envelope is not safe
- no frozen-router edits and no new bridge families are introduced

## Checks
- `pytest -q truffles-api/tests/test_intent.py -k 'bookability_time_collect_policy_snapshot'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'bookability_time_collect_owner or skips_bookability_time_collect_override_without_booking_active'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reasoning-core tests proving direct owner bypass for `missing_temporal_scope`
- fallback test proving non-safe envelope still delegates
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused reasoning-core regressions + full reasoning-core + architecture only
- **Stop condition:** if this slice lands cleanly, the next block must be another direct owner cut that reuses the same collect finalizer, or an audit proving richer owner work is now required
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** focused reasoning-core regressions + full reasoning-core + architecture green; packet/session gates green
- **Rollback:** revert the new reasoning-core owner handler/tests and doc sync
- **Post-release monitoring window:** next block should stay on direct owner deletion or broader owner work, not return to bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe bookability time collect owner cutover and generated packet output.

## Rollback
1. Revert the new reasoning-core handler/tests and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into active-name/specialist availability followup owner cuts in this block
- no counting the block as done unless deterministic `missing_temporal_scope` turns bypass frozen delegate

## Risks / blockers
- if expected-reply reason drifts, booking continuity evidence may regress even when the visible reply still looks correct
- if slot-guidance reply text or metadata diverges from current runtime behavior, downstream contract evidence may become inconsistent

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes one bounded booking collect authority seam and must not widen into broader booking state semantics
- **Risk if deferred:**
  - another deterministic collect normal path remains legacy-owned even though the new core already has the required finalizer
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-booking-collect-owner-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block lands cleanly, the next block must either reuse the same collect finalizer for another bounded booking collect seam or prove that a broader richer owner cut is now required

## Next-block contract (mandatory)
- **Next block objective:** audit whether another bounded booking collect owner cut can reuse the same collect finalizer without new bridge growth; otherwise switch to broader richer owner replacement
- **First deterministic check command:** `rg -n "missing_temporal_scope|booking_time_availability_followup|booking_specialist_availability_followup" truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py`
- **Blocked-by conditions:** if the next candidate needs new semantic detectors, frozen-router edits, or wider state mutation beyond the shared collect finalizer, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
