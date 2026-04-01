# TP-2026-03-17-consultant-core-turn-planner-safe-specialist-name-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SPECIALIST-NAME-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-ACTIVE-NAME-TIME-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-active-name-time-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SPECIALIST-DATETIME-COLLECT-OWNER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded legacy semantic seam: deterministic specialist-availability `name` collect turns should no longer enter frozen `truffles-api/app/routers/webhook/decision.py`. `reasoning_core` must consume the existing policy snapshot directly, reuse the shared collect finalizer, and send the existing deterministic specialist followup reply without adding any new bridge family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-active-name-time-collect-owner-cutover-a922.md`
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
  - `rg -n "booking_specialist_availability_followup|specialist_exact_time_followup|_build_specialist_availability_followup_response" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '6008,6375p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1088,1145p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - reasoning-core still only primes the specialist `name` collect slice for delegate
  - shared collect finalization already exists and now powers several direct collect owner cuts
  - frozen legacy already exposes a deterministic specialist followup reply helper for this exact seam
- `Detected drift (docs vs code)`: the repo already contains safe collect owner infrastructure for this slice, but the deterministic specialist `name` collect family still stops at delegate priming.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dict update official docs`
- **Date/time (local):** `2026-03-17 10:30 +0500`
- **Why this query is precise:** this block reuses helper metadata from the frozen specialist reply builder and needs the standard-library merge contract for a narrow whitelist of metadata fields without inventing a custom merge abstraction.
- **Sources opened (from this query):**
  - `Built-in Types` — `https://docs.python.org/3/library/stdtypes.html#dict.update`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dict.update(...)` is the standard-library way to fold a bounded whitelist of helper metadata into the reply metadata envelope while preserving existing keys.
- **Decision:** `reuse + integrate` — keep the block on the existing helper metadata shape and merge only the explicitly allowed fields into the owner-cutover metadata.
- **Rejected options:**
  - invent a new metadata wrapper type for specialist followups
  - keep the seam as delegate-only bridge
  - touch frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic specialist-availability `name` collect turns are still only primed for delegate; the first semantic owner for that normal path remains frozen `decision.py`.
- **Minimal reproduction:**
  1. Run the existing reasoning-core delegate priming tests for grounded specialist availability and specialist exact-time followup turns.
  2. Observe that reasoning-core sets the override but still hands the turn to `decision_router._handle_webhook_payload(...)`.
  3. Compare with existing direct collect owner cuts that already bypass frozen legacy and finalize continuity in new core.
- **Evidence to capture:**
  - direct owner path for specialist `name` collect bypasses frozen delegate
  - expected-reply / canonical dialog state stay correct through the shared collect finalizer
  - specialist followup metadata and trace survive the new owner path
- **Five Whys (or equivalent):**
  1. Why does this seam still enter legacy? Because it stopped at ingress priming.
  2. Why is that a problem? Because another deterministic booking collect normal path still depends on frozen semantic ownership.
  3. Why is this slice safe to cut over? Because the semantic decision is already made by the policy snapshot and the followup reply helper is deterministic/read-only.
  4. Why not widen into the broader specialist datetime family now? Because this block should delete one bounded authority seam without dragging in new followup families.
  5. Why now? Because the previous collect owner blocks already proved the shared collect finalizer works for deterministic booking collect seams.
- **Root cause statement:** the specialist-availability `name` collect family stopped at bridge priming and never completed owner replacement into the shared collect finalizer.
- **Fix mechanism:**
  - add a bounded candidate/handler for the safe specialist `name` collect slice
  - reuse the shared owner-cutover finalizer with the existing deterministic specialist followup reply helper
  - add focused regressions for direct bypass and bounded fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing policy snapshot detection for `booking_specialist_availability_followup` and `specialist_exact_time_followup`
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing deterministic `_build_specialist_availability_followup_response(...)` helper in frozen legacy
- **External reuse:**
  - official Python `dict.update` documentation
- **Why not reinvent the wheel:** this block should consume an already-proven snapshot, helper, and finalizer path instead of inventing a new specialist followup mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into specialist datetime/date-range/daypart/weekend/weekday followup families.
- Existing shared collect finalizer semantics must remain contract-equivalent.

## Scope
- Add a bounded direct owner path for deterministic specialist `name` collect followup replies.
- Reuse the shared collect finalizer for expected-reply / question-contract / canonical dialog state.
- Add focused reasoning-core regression coverage.
- Sync canon/session artifacts.

## Out of scope
- specialist datetime collect owner cuts
- deictic/relative active-name followup cuts
- new boundary-owner slices
- frozen legacy semantic files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-specialist-name-collect-owner-cutover-a922.md`
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
2. Add a bounded safe candidate/handler for specialist `name` collect owner cutover in `reasoning_core.py`.
3. Route the handler through the existing shared collect finalizer using the deterministic specialist followup reply helper.
4. Add focused reasoning-core regressions for grounded-specialist and specialist-exact-time bypass plus bounded fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic specialist `name` collect followups bypass frozen `decision.py`
- shared collect finalizer writes expected reply / canonical dialog state for this seam
- bounded fallback still delegates cleanly when owner conversation materialization is not safe
- no frozen-router edits and no new bridge families are introduced

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'specialist_name_collect_owner or specialist_exact_time_followup or grounded_specialist_availability_transition'`
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
- reasoning-core tests proving direct owner bypass for specialist `name` collect followups
- fallback test proving non-safe owner materialization still delegates
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused reasoning-core regressions + full reasoning-core + architecture only
- **Stop condition:** if this slice lands cleanly, the next block must either reuse the same collect finalizer for a remaining bounded specialist `datetime` collect seam or prove that a broader richer owner cut is now required
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
  - active block metadata must match the safe specialist `name` collect owner cutover and generated packet output.

## Rollback
1. Revert the new reasoning-core handler/tests and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into specialist datetime collect or broader booking availability owner cuts in this block
- no counting the block as done unless deterministic specialist `name` collect followups bypass frozen delegate

## Risks / blockers
- if specialist helper metadata drifts, downstream continuity evidence may regress even when the visible reply still looks correct
- if grounded and service-choice specialist variants diverge in metadata shape, the bounded candidate may become too narrow or too wide

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes one bounded specialist `name` collect authority seam and must not widen into broader specialist datetime or booking availability semantics
- **Risk if deferred:**
  - another deterministic specialist collect normal path remains legacy-owned even though the new core already has the required finalizer and reply helper
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-specialist-datetime-collect-owner-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block lands cleanly, the next block must either reuse the same collect finalizer for another already-existing bounded specialist datetime seam or prove that richer owner work is now required

## Next-block contract (mandatory)
- **Next block objective:** audit whether another bounded specialist `datetime` collect owner cut can reuse the same collect finalizer without new bridge growth; otherwise switch to broader richer owner replacement
- **First deterministic check command:** `rg -n "booking_specialist_availability_followup|specialist_exact_time_followup|next_question=\"datetime\"|next_question=\"name\"" truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py`
- **Blocked-by conditions:** if the next candidate needs new semantic detectors, frozen-router edits, or wider state mutation beyond the shared collect finalizer, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
