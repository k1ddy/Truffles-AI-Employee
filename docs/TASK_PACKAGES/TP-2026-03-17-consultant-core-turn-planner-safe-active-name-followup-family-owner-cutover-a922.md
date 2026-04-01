# TP-2026-03-17-consultant-core-turn-planner-safe-active-name-followup-family-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-ACTIVE-NAME-FOLLOWUP-FAMILY-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-daypart-collect-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-OWNER-REPLACEMENT-AUDIT-POST-ACTIVE-NAME-FAMILY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий admissible richer semantic owner family: remaining deterministic active-name booking-time availability followups should no longer enter frozen `truffles-api/app/routers/webhook/decision.py` before persistence. This block must complete the bounded active-name family (`deictic_time`, `deictic_day`, `relative_date`, `relative_daypart`) by reusing the existing shared collect finalizer and `_build_active_name_time_availability_followup_response(...)`, while restoring legacy parity for booking-state preservation: safe owner materialization should preserve the current booking slot and trace the alternate/probed slot separately.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-service-choice-specialist-daypart-collect-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/dialog_state_service.py`
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
  - `rg -n "primes_active_name_(deictic_time|deictic_day|relative_date|relative_daypart)|_try_handle_turn_planner_safe_active_name_time_collect_owner_cutover|booking_time_availability_followup" truffles-api/tests/test_reasoning_core.py truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `sed -n '6854,6915p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '22390,22595p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '2260,2375p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` already treats the remaining active-name followup family as one preserved-owner family under `booking_time_availability_followup`
  - current `reasoning_core` active-name owner handler already matches the same `PolicyDecision` family contract, but test coverage still proves only the specific-time path
  - legacy collect materialization preserves the current booking slot in `booking_state` and traces the alternate/probed slot separately; the new owner path should preserve that parity when seeding booking context from snapshot data
- `Detected drift (docs vs code)`: active-name direct owner code is broader than current canon/test evidence, and the current owner seeding logic risks materializing the alternate slot as booking state when the owner conversation lacks preexisting booking context.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dict.setdefault official docs`
- **Date/time (local):** `2026-03-17 12:19 +0500`
- **Why this query is precise:** the block needs explicit “preserve existing value, seed only missing booking slot state” semantics while aligning the owner path with legacy booking-state materialization.
- **Sources opened (from this query):**
  - `Built-in Types — dict.setdefault` — `https://docs.python.org/3/library/stdtypes.html#dict.setdefault`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dict.setdefault` expresses the same “only seed missing state” rule used by the legacy booking-state materialization path.
- **Decision:** `reuse/integrate conceptually, build explicitly` — keep explicit normalized branching in `reasoning_core` / `DialogStateService` instead of literally switching to `setdefault`, because the owner path also needs normalization and snapshot fallback ordering.
- **Rejected options:**
  - seeding the alternate/probed slot into booking state unconditionally
  - introducing a new active-name bridge family instead of extending the existing owner family
  - widening directly into a generic booking-prompt LLM owner cutover
- **Open questions:** none for this bounded block.

## Root cause (mandatory)
- **Symptom:** the remaining active-name followup family still depends on frozen `decision.py` in canon/tests, and the current owner seeding path can materialize the alternate slot into booking state when the owner conversation lacks the original booking context.
- **Minimal reproduction:**
  1. Inspect the remaining delegate-priming tests for `А есть ли у вас места в это время?`, `У вас есть свободные слоты на этот день?`, `У вас есть свободные слоты на завтра?`, and `У вас есть свободные слоты на завтра вечером?`.
  2. Compare them to `_should_preserve_active_name_time_availability_followup_owner(...)` in frozen `decision.py` and `_is_turn_planner_safe_active_name_time_collect_candidate(...)` in `reasoning_core`.
  3. Observe that the family contract is already shared, but the owner path seeds booking slot state from the alternate slot rather than preserving the current slot if canonical booking context is absent.
- **Evidence to capture:**
  - direct owner bypass for all remaining active-name family turns
  - booking state preserves the current slot while trace/meta carries the alternate/probed slot
  - existing fallback-to-delegate tests remain green when owner conversation materialization is unavailable
- **Five Whys (or equivalent):**
  1. Why do these turns still count as legacy-owned? Because only the specific-time member of the family is covered by direct-owner tests and canon evidence.
  2. Why is the family admissible as one block? Because frozen `decision.py` preserves it under one owner gate with one reply helper and one question-contract shape.
  3. Why is current booking-slot seeding a problem? Because materializing the alternate slot as `booking.datetime` changes continuity semantics compared with legacy, even if the visible prompt still looks plausible.
  4. Why not take a broader booking cut instead? Because the current admissible surface is still the policy-snapshot family already enforced by `TurnPlanner`.
  5. Why now? Because this is the next richer owner deletion after the daypart specialist cutover and closes four remaining legacy seams with one shared owner path.
- **Root cause statement:** the active-name booking followup family already shares one deterministic owner contract, but repo evidence still treats most of the family as legacy-delegate-only and the current owner seeding logic does not yet preserve the current booking slot with legacy parity when context must be reconstructed from snapshot data.
- **Fix mechanism:**
  - extend the existing active-name owner path to preserve the current booking slot strictly from snapshot booking-state data (`booking_datetime_value`) so owner materialization stays aligned with legacy parity
  - add direct-owner coverage for the remaining active-name family members
  - sync canon to count the entire family as deleted legacy authority only after the broader owner path is proven

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `_try_handle_turn_planner_safe_active_name_time_collect_owner_cutover(...)`
  - existing shared collect finalizer in `truffles-api/app/services/reasoning_core.py`
  - existing `_build_active_name_time_availability_followup_response(...)` in frozen legacy
- **External reuse:**
  - official Python `dict.setdefault` docs as the reference semantics for “seed only missing state”
- **Why not reinvent the wheel:** this block should extend the existing active-name owner family, not create a new handler family or a new bridge family.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one richer owner-family deletion plus parity fix in shared owner materialization.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- No widening into generic booking-prompt LLM extraction.
- Active-name owner path must keep current-slot vs alternate-slot semantics aligned with legacy materialization.

## Scope
- Extend the existing active-name owner path to preserve the current booking slot with snapshot fallback.
- Add direct-owner coverage for the remaining active-name family members.
- Sync canon/session artifacts if the broader family cutover is green.

## Out of scope
- generic booking-prompt LLM owner cutover
- frozen router files
- specialist followup family changes
- broader booking restore / timeout semantics

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-turn-planner-safe-active-name-followup-family-owner-cutover-a922.md`
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
2. Audit the existing active-name owner path against frozen legacy owner semantics.
3. Update the owner path so booking-state seeding preserves the current booking slot strictly from `booking_datetime_value`, while keeping the alternate/probed slot only in trace/meta.
4. Add direct-owner tests for the remaining active-name family members.
5. Re-run focused and full validations.
6. Sync canon/session artifacts only if the broader family cutover is green.

## DoD
- remaining active-name family turns bypass frozen `decision.py` through the existing owner path
- owner materialization preserves current booking slot semantics with legacy parity
- fallback-to-delegate tests remain green when owner conversation materialization is unavailable
- no new bridge families and no frozen-router edits

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'active_name_time_collect_owner or active_name_deictic_time or active_name_deictic_day or active_name_relative_date or active_name_relative_daypart'`
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
- direct-owner reasoning-core tests for the remaining active-name family
- green full reasoning-core/runtime-contract/architecture checks
- updated source-of-truth / packet showing the broader active-name family cutover

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** focused reasoning-core family regressions first, then full reasoning-core + contracts + architecture
- **Stop condition:** if the active-name family cannot be deleted through the existing owner path, stop and return to a richer audit instead of introducing another micro-slice
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-family deletion only; no new entrypoints
- **Go/no-go signals:** focused active-name family regressions + full reasoning-core/contracts/architecture green; packet/session gates green
- **Rollback:** revert the owner-path update, tests, and doc sync
- **Post-release monitoring window:** next block should prefer richer owner deletion over another family micro-slice

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - canon must count the broader active-name family as deleted only if direct owner coverage and owner-materialization parity are both proven.

## Rollback
1. Revert the reasoning-core/test/doc changes for this block.
2. Regenerate packet.
3. Re-run guards.

## No-go
- no frozen-router edit
- no new detector family
- no generic booking cutover in this block
- do not count the block as done unless the broader active-name family is proven through direct owner tests

## Risks / blockers
- if current-slot preservation is wrong, booking continuity can silently drift even while response text looks acceptable
- if the family cannot be proven through the existing owner path, forcing it would reintroduce micro-slice behavior under a different name

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader generic booking-prompt ownership still remains legacy-owned
  - single continuity writer is still not fully closed
  - boundary owner remains only partially cut over
- **Why not in this block:**
  - this block is limited to the next richer admissible owner family already exposed by the current policy-snapshot surface
- **Risk if deferred:**
  - active-name family progress remains undercounted or, worse, continuity parity drifts under owner materialization
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - once the active-name family is closed, the next move must return to a richer owner audit instead of another family micro-slice

## Next-block contract (mandatory)
- **Next block objective:** `richer_owner_replacement_audit_after_safe_active_name_followup_family_owner_cutover`
- **First deterministic check command:** `rg -n "primes_.*override_for_delegate|_try_handle_turn_planner_safe_" truffles-api/tests/test_reasoning_core.py truffles-api/app/services/reasoning_core.py`
- **Blocked-by conditions:** lack of a broader admissible owner seam without new bridge growth
- **Owner role for closure:** `Top Architect`
