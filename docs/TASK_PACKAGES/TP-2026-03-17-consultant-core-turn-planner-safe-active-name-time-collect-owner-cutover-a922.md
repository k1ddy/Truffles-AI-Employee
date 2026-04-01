# TP-2026-03-17-consultant-core-turn-planner-safe-active-name-time-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-ACTIVE-NAME-TIME-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-BOOKABILITY-TIME-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-bookability-time-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-BOOKING-COLLECT-OWNER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded legacy semantic seam: deterministic active-name specific-time availability followup should no longer enter frozen `truffles-api/app/routers/webhook/decision.py`. `reasoning_core` must consume the existing policy snapshot directly, reuse the shared collect finalizer, and send the existing deterministic active-name followup reply without adding any new bridge family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-bookability-time-collect-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "active_name_time_availability_followup|booking_time_availability_followup|_build_active_name_time_availability_followup_response" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '5070,5188p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1145,1205p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - reasoning-core already primes a bounded active-name specific-time availability followup override for delegate
  - shared collect finalization already exists and is used by pricing/duration/master-query/bookability collect owner cuts
  - frozen legacy already exposes a deterministic reply helper for this exact seam
- `Detected drift (docs vs code)`: this slice is still bridge-only progress even though the new core already has the required collect finalizer and the reply helper is deterministic/read-only.

## One web search (mandatory before implementation)
- **Query (exact):** `Python str strip official docs`
- **Date/time (local):** `2026-03-17 10:14 +0500`
- **Why this query is precise:** this block reuses narrow string token surfaces for current/alternate datetime slots and should stay on the existing normalized string contract without adding a wrapper type.
- **Sources opened (from this query):**
  - `Built-in Types` — `https://docs.python.org/3/library/stdtypes.html#str.strip`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `str.strip()` is the standard-library way to normalize optional current/alternate slot strings before contract comparison and metadata projection.
- **Decision:** `reuse + integrate` — keep the block on the existing string/token surfaces and only add the bounded owner cutover logic.
- **Rejected options:**
  - add a new wrapper model for current/alternate slot state
  - keep the seam as delegate-only bridge
  - touch frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic active-name specific-time availability followups are still only primed for delegate; the first semantic owner for that normal path remains frozen `decision.py`.
- **Minimal reproduction:**
  1. Run the existing reasoning-core priming test for `А есть ли свободные слоты на 15:00?`.
  2. Observe that reasoning-core sets the override but still hands the turn to `decision_router._handle_webhook_payload(...)`.
  3. Compare with existing direct collect owner cuts that already bypass frozen legacy and finalize continuity in new core.
- **Evidence to capture:**
  - direct owner path for active-name specific-time followup bypasses frozen delegate
  - expected-reply / canonical dialog state stay correct through the shared collect finalizer
  - current/alternate datetime metadata survive the new owner path
- **Five Whys (or equivalent):**
  1. Why does this seam still enter legacy? Because it stopped at ingress priming.
  2. Why is that a problem? Because another deterministic booking collect normal path still depends on frozen semantic ownership.
  3. Why is this slice safe to cut over? Because the semantic decision is already made by the policy snapshot and the followup reply is deterministic.
  4. Why not widen into broader availability families now? Because this block should delete one bounded authority seam without dragging in additional followup families.
  5. Why now? Because the previous block proved the shared booking collect finalizer works for this family of deterministic booking collect seams.
- **Root cause statement:** the active-name specific-time availability followup family stopped at bridge priming and never completed owner replacement into the shared collect finalizer.
- **Fix mechanism:**
  - add a bounded candidate/handler for the safe active-name specific-time followup slice
  - reuse the shared owner-cutover finalizer with the existing deterministic active-name followup reply helper
  - add focused regressions for direct bypass and bounded fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing policy snapshot detection for `booking_time_availability_followup`
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing deterministic `_build_active_name_time_availability_followup_response(...)` helper in frozen legacy
- **External reuse:**
  - official Python `str.strip` documentation
- **Why not reinvent the wheel:** this block should consume an already-proven snapshot, helper, and finalizer path instead of inventing a new availability-followup mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into deictic/relative-date/daypart specialist followup families.
- Existing shared collect finalizer semantics must remain contract-equivalent.

## Scope
- Add a bounded direct owner path for deterministic active-name specific-time availability followup replies.
- Reuse the shared collect finalizer for expected-reply / question-contract / canonical dialog state.
- Add focused reasoning-core regression coverage.
- Sync canon/session artifacts.

## Out of scope
- deictic/relative-date/daypart active-name followup owner cuts
- specialist-availability owner cuts
- new boundary-owner slices
- frozen legacy semantic files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-active-name-time-collect-owner-cutover-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add a bounded safe candidate/handler for active-name specific-time followup owner cutover in `reasoning_core.py`.
3. Route the handler through the existing shared collect finalizer using the deterministic active-name followup reply helper.
4. Add focused reasoning-core regressions for bypass + bounded fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic active-name specific-time availability followups bypass frozen `decision.py`
- shared collect finalizer writes expected reply / canonical dialog state for this seam
- bounded fallback still delegates cleanly when owner conversation materialization is not safe
- no frozen-router edits and no new bridge families are introduced

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'active_name_time_collect_owner or skips_active_name_time_availability_followup_override_without_resume_reason'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reasoning-core tests proving direct owner bypass for active-name specific-time followup
- fallback test proving non-safe owner materialization still delegates
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused reasoning-core regressions + full reasoning-core + architecture only
- **Stop condition:** if this slice lands cleanly, the next block must either reuse the same collect finalizer for another bounded booking collect seam or prove that a broader richer owner cut is now required
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
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe active-name specific-time collect owner cutover and generated packet output.

## Rollback
1. Revert the new reasoning-core handler/tests and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into deictic/relative-date/daypart or specialist availability owner cuts in this block
- no counting the block as done unless deterministic active-name specific-time followups bypass frozen delegate

## Risks / blockers
- if current/alternate datetime metadata drifts, downstream continuity evidence may regress even when the visible reply still looks correct
- if active-name followup reply text diverges from current runtime behavior, downstream contract evidence may become inconsistent

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes one bounded booking collect authority seam and must not widen into broader availability or specialist semantics
- **Risk if deferred:**
  - another deterministic booking collect normal path remains legacy-owned even though the new core already has the required finalizer and reply helper
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-booking-collect-owner-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block lands cleanly, the next block must either reuse the same collect finalizer for another already-existing bounded booking collect seam or prove that richer owner work is now required

## Next-block contract (mandatory)
- **Next block objective:** audit whether another bounded booking collect owner cut can reuse the same collect finalizer without new bridge growth; otherwise switch to broader richer owner replacement
- **First deterministic check command:** `rg -n "booking_time_availability_followup|booking_specialist_availability_followup|missing_temporal_scope" truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py`
- **Blocked-by conditions:** if the next candidate needs new semantic detectors, frozen-router edits, or wider state mutation beyond the shared collect finalizer, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
