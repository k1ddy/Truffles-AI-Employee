# TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-time-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SERVICE-CHOICE-SPECIALIST-TIME-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SPECIALIST-DATETIME-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-specialist-datetime-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий richer bounded legacy semantic seam: deterministic service-choice specialist followups that already resolve to `next_question="datetime"` with an empty `datetime` slot should no longer enter frozen `truffles-api/app/routers/webhook/decision.py`. `reasoning_core` must consume the existing policy snapshot directly, reuse the shared collect finalizer, and materialize the same specialist followup reply/continuity contract without adding any new bridge family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-specialist-datetime-collect-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/intent_routing.py`
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
  - `rg -n "day_followup|weekday_followup|weekend_followup|daypart_followup|specialist_exact_time_followup" truffles-api/app/core/intent_routing.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
  - `sed -n '6722,6865p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '22060,22610p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - frozen `decision.py` already collapses service-choice specialist `day` / `weekday` / `weekend` followups into the same booking-side specialist availability collect outcome
  - existing shared collect finalizer already materializes the required expected-reply / question-contract / canonical dialog-state artifacts
  - `daypart_followup` is not shape-equivalent because it carries a prefilled `datetime` token that the shared collect finalizer does not currently persist into booking context
- `Detected drift (docs vs code)`: the repo already has the safe specialist followup helper and shared owner finalizer, but three deterministic service-choice specialist time-collect reasons still stop at delegate priming.

## One web search (mandatory before implementation)
- **Query (exact):** `Python frozenset official docs`
- **Date/time (local):** `2026-03-17 11:12 +0500`
- **Why this query is precise:** this block needs a narrow immutable reason-family gate for an already-existing bounded snapshot family and should stay on the standard-library immutable-set contract rather than introducing a mutable registry.
- **Sources opened (from this query):**
  - `Built-in Types` — `https://docs.python.org/3/library/stdtypes.html#frozenset`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `frozenset(...)` is the standard-library immutable container for small bounded token families when the block needs stable membership checks without runtime mutation.
- **Decision:** `reuse + integrate` — keep the candidate gate on a narrow immutable reason set and do not invent a new abstraction for one bounded owner cut.
- **Rejected options:**
  - invent a custom reason-family wrapper
  - widen this block into `daypart_followup`
  - touch frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic service-choice specialist `day` / `weekday` / `weekend` time-collect turns are still only primed for delegate; the first semantic owner for those normal paths remains frozen `decision.py`.
- **Minimal reproduction:**
  1. Run the existing reasoning-core delegate-priming tests for `Какой мастер будет делать маникюр в субботу?`, `...по будням?`, and `...на выходных?`.
  2. Observe that reasoning-core sets the override but still hands the turn to `decision_router._handle_webhook_payload(...)`.
  3. Inspect frozen `decision.py` and confirm it normalizes those three reasons into the same specialist-availability collect outcome before persistence.
- **Evidence to capture:**
  - direct owner path bypasses frozen delegate for the already-existing empty-datetime service-choice specialist family
  - expected-reply / canonical dialog state stay equivalent to the legacy collect outcome
  - legacy fallback still works when owner conversation materialization is unavailable
- **Five Whys (or equivalent):**
  1. Why do these turns still enter legacy? Because they stopped at ingress priming.
  2. Why is that a problem? Because three deterministic specialist collect normal paths still depend on frozen semantic ownership.
  3. Why is this slice safe to cut over? Because frozen `decision.py` already maps those reasons into one booking-side specialist availability collect contract with no prefilled datetime slot.
  4. Why not include `daypart_followup` now? Because that reason carries a prefilled `datetime` token and would require extra booking-state persistence beyond the current shared finalizer.
  5. Why now? Because the specialist `name` and specialist `date_range datetime` owner cuts already proved the same helper/finalizer lineage works for this followup family.
- **Root cause statement:** the empty-datetime service-choice specialist time-collect family stopped at bridge priming and never completed owner replacement into the shared collect finalizer, even though frozen legacy already collapses it into the same specialist availability collect contract.
- **Fix mechanism:**
  - add a bounded candidate/handler for the safe empty-datetime service-choice specialist family
  - reuse the shared owner-cutover finalizer with the existing deterministic specialist followup reply helper
  - add focused regressions for direct bypass across the day/weekday/weekend family and bounded fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing policy snapshot detection for `day_followup`, `weekday_followup`, and `weekend_followup`
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing deterministic `_build_specialist_availability_followup_response(...)` helper in frozen legacy
- **External reuse:**
  - official Python `frozenset` documentation
- **Why not reinvent the wheel:** this block should consume an already-proven snapshot family, helper, and finalizer path instead of inventing a new specialist followup mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded but broader owner-replacement slice plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into `daypart_followup` or other prefilled-datetime families.
- Existing shared collect finalizer semantics must remain contract-equivalent.

## Scope
- Add a bounded direct owner path for deterministic service-choice specialist `day` / `weekday` / `weekend` collect replies.
- Reuse the shared collect finalizer for expected-reply / question-contract / canonical dialog state.
- Add focused reasoning-core regression coverage.
- Sync canon/session artifacts.

## Out of scope
- `daypart_followup`
- specialist `name` collect owner cuts
- specialist `date_range` collect owner cuts
- new boundary-owner slices
- frozen legacy semantic files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-time-collect-owner-cutover-a922.md`
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
2. Add a bounded safe candidate/handler for empty-datetime service-choice specialist time-collect owner cutover in `reasoning_core.py`.
3. Route the handler through the shared collect finalizer using the deterministic specialist followup reply helper.
4. Add focused reasoning-core regressions for direct bypass and bounded fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic service-choice specialist `day` / `weekday` / `weekend` followups bypass frozen `decision.py`
- shared collect finalizer writes expected reply / canonical dialog state for this family
- bounded fallback still delegates cleanly when owner conversation materialization is not safe
- no frozen-router edits and no new bridge families are introduced

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'service_choice_specialist_time_collect_owner or service_choice_specialist_day_followup or service_choice_specialist_weekday_followup or service_choice_specialist_weekend_followup'`
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
- reasoning-core tests proving direct owner bypass for the empty-datetime service-choice specialist family
- fallback test proving non-safe owner materialization still delegates
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused reasoning-core regressions + full reasoning-core + architecture only
- **Stop condition:** if this slice lands cleanly, the next block must either switch to a richer owner cut beyond specialist micro-families or explicitly justify why `daypart_followup` is still deferrable without bridge growth
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
  - active block metadata must match the safe service-choice specialist time-collect owner cutover and generated packet output.

## Rollback
1. Revert the new reasoning-core handler/tests and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into `daypart_followup` in this block
- no counting the block as done unless deterministic service-choice specialist `day` / `weekday` / `weekend` followups bypass frozen delegate

## Risks / blockers
- if the owner path fails to preserve the legacy booking-side question contract, followup continuity could drift even when the visible reply still looks correct
- if this block silently includes a prefilled-datetime reason, booking-state continuity would regress because the shared finalizer does not yet persist that slot family

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
  - `daypart_followup` still remains legacy-owned because it requires slot-preserving collect continuity
- **Why not in this block:**
  - this block only deletes the already-existing empty-datetime service-choice specialist family and must not widen into prefilled-datetime continuity semantics
- **Risk if deferred:**
  - three deterministic specialist collect normal paths remain legacy-owned even though frozen `decision.py` already collapses them into the same collect contract
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-richer-owner-replacement-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block lands cleanly, the next block must either move to a richer owner cut or explicitly prove why `daypart_followup` cannot yet be deleted without expanding continuity ownership

## Next-block contract (mandatory)
- **Next block objective:** decide whether the next admissible move is a richer owner-replacement cut or a bounded slot-preserving collect cut for a prefilled-datetime family.
- **First deterministic check command:** `rg -n "daypart_followup|specialist_availability_followup|build_collect_owner_state|booking_state\[" truffles-api/app/services/reasoning_core.py truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** if the next candidate would require new phrase families, frozen-router edits, or silent continuity downgrades for prefilled datetime tokens, do not take it as a bounded cut.
- **Owner role for closure:** `Top Architect`
