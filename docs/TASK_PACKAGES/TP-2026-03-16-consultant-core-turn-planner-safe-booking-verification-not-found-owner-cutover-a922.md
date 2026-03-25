# TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-not-found-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-BOOKING-VERIFICATION-NOT-FOUND-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-BOOKING-VERIFICATION-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-NEXT-SAFE-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Расширить уже существующий owner-replacement cutover для `calendar.get_booking` ещё на один bounded normal path: safe `not_found` booking-verification replies. Если existing policy override уже указывает на `check_booking` / `calendar.get_booking`, а downstream tool result даёт deterministic `not_found` reply без collect/handoff semantics, `reasoning_core` должен завершать turn напрямую и не заходить в frozen `decision.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/semantic_bridge_growth_guard.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1339,1365p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1878,1965p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1567,1622p' truffles-api/app/services/tool_registry_service.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'booking_verification_owner'`
- `FACT findings`:
  - Existing safe owner cutover only accepts `tool_decision == "ok"` with `appointment_id`, so deterministic `not_found` replies still fall back to frozen `decision.py`.
  - `calendar.get_booking` `not_found` replies already come from the shared read-only tool path with non-empty response text, `tool_decision == "not_found"`, and `error_code == "appointment_not_found"`.
  - Human-request handoff precedence is already handled earlier in policy priming, so this bounded slice only affects non-handoff booking-verification turns.
- `Detected drift (docs vs code)`: a safe downstream booking-verification reply still delegates to legacy runtime even though the owner cutover scaffolding already exists.

## One web search (mandatory before implementation)
- **Query (exact):** `Python all function documentation site:python.org`
- **Date/time (local):** `2026-03-16 23:33 +0500`
- **Why this query is precise:** the acceptance gate for this owner cutover remains a small conjunction of invariants; the block reuses an explicit all-of contract for the safe envelope.
- **Sources opened (from this query):**
  - `Built-in Functions — all()` — `https://docs.python.org/3/library/functions.html#all`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `all()` remains the standard-library primitive for an explicit conjunction gate without introducing extra control-flow noise.
- **Decision:** `reuse + integrate` — extend the existing acceptance gate with one additional bounded `not_found` branch instead of adding a new bridge family or rewriting the owner path.
- **Rejected options:**
  - adding a new ingress bridge family for booking-verification not-found text
  - widening the cutover into time-mismatch, provider-unavailable, or collect/handoff booking semantics
  - touching frozen `decision.py` / `booking.py` / `pending.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** safe `calendar.get_booking` not-found replies still pass through frozen `decision.py` even though the owner cutover already has the same policy override, same tool execution path, and the same finalizer available.
- **Minimal reproduction:**
  1. Prime a `check_booking` / `calendar.get_booking` policy override.
  2. Return a deterministic tool result with `tool_decision == "not_found"`, `error_code == "appointment_not_found"`, and non-empty response text.
  3. Observe that `reasoning_core` falls back to the legacy delegate because `_should_accept_turn_planner_booking_verification_result(...)` only allows the `ok` branch.
- **Evidence to capture:**
  - `reasoning_core` bypasses frozen `decision.py` for safe `not_found` replies
  - `time_mismatch` still falls back to legacy delegate
- **Five Whys (or equivalent):**
  1. Why does the safe reply still hit legacy? Because the owner acceptance gate only whitelists `ok`.
  2. Why is that too strict? Because `not_found` is already a deterministic read-only reply in the same tool path.
  3. Why not widen further? Because `time_mismatch` and handoff-adjacent outcomes may carry broader routing semantics.
  4. Why is this block bounded? Because it only extends one existing owner path and one acceptance gate.
  5. Why fix this now? Because it deletes another real legacy semantic seam without adding bridge growth.
- **Root cause statement:** the current booking-verification owner cutover under-accepts safe downstream results, so the legacy router still owns the deterministic `not_found` reply path.
- **Fix mechanism:**
  - extend the safe booking-verification acceptance gate to allow the deterministic `not_found` envelope
  - propagate downstream tool decision metadata through the existing finalizer
  - keep `time_mismatch` and other non-safe outcomes on legacy fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `_try_handle_turn_planner_safe_booking_verification_owner_cutover(...)`
  - existing `TurnPlanner.build_from_policy_override(...)`
  - existing `execute_tool_action(...)`
  - existing owner-cutover finalizer and runtime metadata builders
- **External reuse:**
  - official Python `all()` semantics from the standard library docs
- **Why not reinvent the wheel:** the block only extends an existing owner path; it does not introduce a new owner mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement extension plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Only the safe `not_found` booking-verification path becomes direct-owner; other booking-verification outcomes still fall back to legacy delegate.
- Existing `ok` booking-verification owner cutover remains unchanged.

## Scope
- Extend the safe booking-verification acceptance gate for deterministic `not_found` tool results.
- Preserve downstream metadata in the existing owner finalizer.
- Add focused regression coverage for `not_found` bypass and `time_mismatch` fallback.
- Sync canon/session artifacts.

## Out of scope
- booking verification handoff semantics
- time mismatch / provider unavailable / collect-state cutovers
- frozen legacy semantic files
- new semantic bridge families
- continuity-writer work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-not-found-owner-cutover-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Extend the booking-verification safe acceptance gate for deterministic `not_found` replies.
3. Keep the existing owner finalizer but pass through downstream `tool_decision` dynamically.
4. Add focused regression coverage for `not_found` bypass and `time_mismatch` fallback.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- safe booking-verification `not_found` replies bypass frozen `decision.py`
- `time_mismatch` still falls back to legacy delegate
- no frozen-router edits and no new semantic bridges are introduced
- runtime metadata records downstream `tool_decision` correctly for the owner-cutover path

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'booking_verification_owner'`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- reasoning-core tests proving safe `not_found` owner bypass and `time_mismatch` fallback
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** reasoning-core + contracts + architecture only for this bounded block
- **Stop condition:** if `not_found` requires collect/handoff state mutation beyond the existing owner finalizer, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement extension only; no new entrypoints or semantic bridges
- **Go/no-go signals:** reasoning-core + contracts + architecture suites green; semantic bridge growth guard green
- **Rollback:** revert the acceptance-gate extension, tests, and doc sync
- **Post-release monitoring window:** next block should either extend another safe owner seam or return to the continuity audit outcome without new bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the booking-verification not-found owner cutover and generated packet output.

## Rollback
1. Revert the `reasoning_core` acceptance/finalizer change, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into time-mismatch, handoff, provider-unavailable, or collect-state semantics
- no counting this block as done unless safe `not_found` replies become direct-owner and `time_mismatch` still falls back

## Risks / blockers
- if not-found path actually needs stateful handoff semantics in some hidden branch, direct-owner cutover would be unsafe
- if acceptance gate is too broad, non-safe booking-verification outcomes could bypass legacy incorrectly

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader booking-verification outcomes still remain on the legacy delegate
  - richer semantic owner slices still remain in frozen `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only extends one existing safe owner envelope; broader booking semantics would widen scope too much
- **Risk if deferred:**
  - legacy `decision.py` would keep owning another deterministic normal path that the new owner already has enough information to realize safely
- **Linked follow-up Task Package(s):**
  - next bounded owner-replacement TP after this cutover, or continuity-audit closeout TP if no safe owner seam remains
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate seam needs state mutation or new phrase-bridge growth

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded owner-replacement seam only if it deletes another legacy semantic path without new bridge growth; otherwise close the continuity audit and move to a richer planner cutover
- **First deterministic check command:** `rg -n "_should_accept_turn_planner_.*result|_try_handle_turn_planner_safe_.*owner_cutover|tool_decision == \"not_found\"|tool_decision == \"time_mismatch\"" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** if the next candidate needs collect-state writes, handoff creation, or frozen-router edits, do not force a micro-cutover
- **Owner role for closure:** `Top Architect`
