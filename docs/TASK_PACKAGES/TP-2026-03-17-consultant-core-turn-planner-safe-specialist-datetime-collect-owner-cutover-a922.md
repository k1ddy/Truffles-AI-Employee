# TP-2026-03-17-consultant-core-turn-planner-safe-specialist-datetime-collect-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SPECIALIST-DATETIME-COLLECT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SPECIALIST-NAME-COLLECT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-specialist-name-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded legacy semantic seam: deterministic specialist-availability `datetime` collect turns for the existing date-range followup should no longer enter frozen `truffles-api/app/routers/webhook/decision.py`. `reasoning_core` must consume the existing policy snapshot directly, reuse the shared collect finalizer, and send the existing deterministic specialist followup reply without adding any new bridge family.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-specialist-name-collect-owner-cutover-a922.md`
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
  - `rg -n "specialist_date_range|booking_specialist_availability_followup|_build_specialist_availability_followup_response" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '5850,5945p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1105,1145p' truffles-api/app/routers/webhook/decision.py`
- `FACT findings`:
  - reasoning-core still only primes the bounded specialist date-range `datetime` collect slice for delegate
  - shared collect finalization already exists and now powers several direct collect owner cuts
  - frozen legacy already exposes a deterministic specialist followup reply helper for this exact seam
- `Detected drift (docs vs code)`: the repo already contains safe collect owner infrastructure for this slice, but the deterministic specialist date-range `datetime` collect family still stops at delegate priming.

## One web search (mandatory before implementation)
- **Query (exact):** `Python frozenset official docs`
- **Date/time (local):** `2026-03-17 11:02 +0500`
- **Why this query is precise:** this block uses a narrow immutable reason-family surface for a bounded owner candidate and should stay on the standard-library immutable-set contract instead of introducing a new wrapper or mutable registry.
- **Sources opened (from this query):**
  - `Built-in Types` — `https://docs.python.org/3/library/stdtypes.html#frozenset`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `frozenset(...)` is the standard-library immutable container for small bounded token families when the block needs stable membership checks without mutable runtime state.
- **Decision:** `reuse + integrate` — keep the candidate gate on narrow immutable token sets and do not invent a new abstraction for one bounded owner cut.
- **Rejected options:**
  - invent a custom token-family wrapper
  - widen the block into the service-choice specialist family
  - touch frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic specialist date-range `datetime` collect turns are still only primed for delegate; the first semantic owner for that normal path remains frozen `decision.py`.
- **Minimal reproduction:**
  1. Run the existing reasoning-core delegate priming test for `Какой мастер свободен на этой неделе?`.
  2. Observe that reasoning-core sets the override but still hands the turn to `decision_router._handle_webhook_payload(...)`.
  3. Compare with the already-landed direct collect owner cuts that bypass frozen legacy and finalize continuity in new core.
- **Evidence to capture:**
  - direct owner path for specialist date-range `datetime` collect bypasses frozen delegate
  - expected-reply / canonical dialog state stay correct through the shared collect finalizer
  - specialist followup metadata and trace survive the new owner path
- **Five Whys (or equivalent):**
  1. Why does this seam still enter legacy? Because it stopped at ingress priming.
  2. Why is that a problem? Because another deterministic collect normal path still depends on frozen semantic ownership.
  3. Why is this slice safe to cut over? Because the semantic decision is already made by the policy snapshot and the followup reply helper is deterministic/read-only.
  4. Why not widen into the service-choice specialist family now? Because those reasons use a different semantic contract (`info` + `clarify_missing_time`) and would mix another family into this block.
  5. Why now? Because the previous specialist `name` collect cutover already proved the same helper and shared finalizer work for this specialist followup lineage.
- **Root cause statement:** the specialist date-range `datetime` collect family stopped at bridge priming and never completed owner replacement into the shared collect finalizer.
- **Fix mechanism:**
  - add a bounded candidate/handler for the safe specialist date-range `datetime` collect slice
  - reuse the shared owner-cutover finalizer with the existing deterministic specialist followup reply helper
  - add focused regressions for direct bypass and bounded fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing policy snapshot detection for `booking_specialist_availability_followup`
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing deterministic `_build_specialist_availability_followup_response(...)` helper in frozen legacy
- **External reuse:**
  - official Python `frozenset` documentation
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
- No widening into service-choice specialist followup reasons.
- Existing shared collect finalizer semantics must remain contract-equivalent.

## Scope
- Add a bounded direct owner path for deterministic specialist date-range `datetime` collect replies.
- Reuse the shared collect finalizer for expected-reply / question-contract / canonical dialog state.
- Add focused reasoning-core regression coverage.
- Sync canon/session artifacts.

## Out of scope
- service-choice specialist datetime collect owner cuts
- specialist `name` collect owner cuts
- new boundary-owner slices
- frozen legacy semantic files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-specialist-datetime-collect-owner-cutover-a922.md`
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
2. Add a bounded safe candidate/handler for specialist date-range `datetime` collect owner cutover in `reasoning_core.py`.
3. Route the handler through the shared collect finalizer using the deterministic specialist followup reply helper.
4. Add focused reasoning-core regressions for direct bypass and bounded fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic specialist date-range `datetime` collect followups bypass frozen `decision.py`
- shared collect finalizer writes expected reply / canonical dialog state for this seam
- bounded fallback still delegates cleanly when owner conversation materialization is not safe
- no frozen-router edits and no new bridge families are introduced

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'specialist_datetime_collect_owner or specialist_date_range_availability_followup'`
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
- reasoning-core tests proving direct owner bypass for specialist date-range `datetime` collect
- fallback test proving non-safe owner materialization still delegates
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused reasoning-core regressions + full reasoning-core + architecture only
- **Stop condition:** if this slice lands cleanly, the next block must either prove a broader richer owner cut is now the right move or explicitly justify another bounded specialist collect cut without new bridge growth
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
  - active block metadata must match the safe specialist date-range `datetime` collect owner cutover and generated packet output.

## Rollback
1. Revert the new reasoning-core handler/tests and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into service-choice specialist followup families in this block
- no counting the block as done unless deterministic specialist date-range `datetime` collect followups bypass frozen delegate

## Risks / blockers
- if specialist helper metadata drifts, downstream continuity evidence may regress even when the visible reply still looks correct
- if the date-range followup contract diverges from the frozen helper, metadata or trace evidence may become inconsistent

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - richer semantic owner slices still remain in legacy `decision.py`
  - single continuity writer is still not fully closed
  - broader boundary ownership still remains beyond the bounded preflight/degrade family
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes one bounded specialist date-range `datetime` collect authority seam and must not widen into service-choice specialist families
- **Risk if deferred:**
  - another deterministic specialist collect normal path remains legacy-owned even though the new core already has the required finalizer and reply helper
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-richer-owner-replacement-audit-a922` (to be authored)
- **Expiry/trigger to stop deferral:**
  - if this block lands cleanly, the next block must either switch to richer owner replacement or explicitly prove that another bounded specialist collect seam can be deleted without bridge growth

## Next-block contract (mandatory)
- **Next block objective:** decide whether the next admissible move is a richer owner-replacement cut or another already-existing bounded specialist collect seam without new bridge growth.
- **First deterministic check command:** `rg -n "booking_specialist_availability_followup|day_followup|daypart_followup|weekday_followup|weekend_followup" truffles-api/app/services/reasoning_core.py truffles-api/app/core/intent_routing.py truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** if the next candidate would require new phrase families, frozen-router edits, or semantic reinterpretation of the service-choice specialist family, do not take it as a bounded cut.
- **Owner role for closure:** `Top Architect`
