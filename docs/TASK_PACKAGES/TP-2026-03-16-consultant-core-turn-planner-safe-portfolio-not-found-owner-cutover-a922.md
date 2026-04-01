# TP-2026-03-16-consultant-core-turn-planner-safe-portfolio-not-found-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-PORTFOLIO-NOT-FOUND-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-CATALOG-FACT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-catalog-fact-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-NEXT-SAFE-CATALOG-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Расширить уже существующий safe catalog fact owner cutover ещё на один bounded normal path: deterministic `catalog.portfolio` `not_found` replies. Если existing policy override уже указывает на `portfolio` / `catalog.portfolio`, а shared tool path возвращает deterministic `portfolio_missing` reply без collect/handoff semantics, `reasoning_core` должен завершать turn напрямую и не заходить в frozen `decision.py`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-catalog-fact-owner-cutover-a922.md`
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
  - `sed -n '1220,1265p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1651,1735p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '2648,2664p' truffles-api/app/services/tool_registry_service.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k 'safe_catalog_owner'`
- `FACT findings`:
  - Existing safe catalog owner cutover only accepts `portfolio` when downstream `tool_decision == "ok"`, so deterministic `portfolio_missing` replies still fall back to frozen `decision.py`.
  - Shared `catalog.portfolio` tool path already returns a deterministic, read-only reply with `tool_decision == "not_found"` and `error_code == "portfolio_missing"`.
  - The existing generic fallback test already proves `catalog.location` `not_found` remains unsafe and should stay on legacy delegate.
- `Detected drift (docs vs code)`: a deterministic shared-tool portfolio reply still delegates to frozen legacy runtime even though the owner cutover scaffolding already exists.

## One web search (mandatory before implementation)
- **Query (exact):** `Python any function documentation site:python.org`
- **Date/time (local):** `2026-03-16 23:48 +0500`
- **Why this query is precise:** the acceptance gate for this owner cutover remains a bounded boolean envelope; the block reuses an explicit `any(...)` allowlist of safe downstream result shapes.
- **Sources opened (from this query):**
  - `Built-in Functions — any()` — `https://docs.python.org/3/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `any()` remains the standard-library primitive for a small allowlist gate without adding branching noise.
- **Decision:** `reuse + integrate` — extend the existing safe catalog acceptance gate with one additional bounded `portfolio not_found` branch instead of adding any new bridge family or owner path.
- **Rejected options:**
  - adding a new ingress bridge family for portfolio missing text
  - widening the cutover into `catalog.location` `not_found` or services-overview collect-style replies
  - touching frozen `decision.py` / `booking.py` / `pending.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** deterministic `catalog.portfolio` missing-data replies still pass through frozen `decision.py` even though the same policy override, tool execution path, and direct owner finalizer already exist.
- **Minimal reproduction:**
  1. Prime a `portfolio` / `catalog.portfolio` policy override.
  2. Return a deterministic tool result with `tool_decision == "not_found"`, `error_code == "portfolio_missing"`, and non-empty response text.
  3. Observe that `reasoning_core` falls back to the legacy delegate because `_should_accept_turn_planner_catalog_result(...)` only allows `portfolio` `ok`.
- **Evidence to capture:**
  - `reasoning_core` bypasses frozen `decision.py` for safe `portfolio not_found` replies
  - `catalog.location` `not_found` still falls back to legacy delegate
- **Five Whys (or equivalent):**
  1. Why does the deterministic reply still hit legacy? Because the safe catalog acceptance gate only whitelists `portfolio` `ok`.
  2. Why is that too strict? Because `portfolio_missing` already returns a deterministic read-only reply from the same shared tool path.
  3. Why not widen further? Because `location` `not_found` is collect-leaning and should remain on legacy.
  4. Why is this block bounded? Because it only extends one existing owner path and one acceptance gate.
  5. Why fix this now? Because it deletes another real legacy semantic seam without adding bridge growth.
- **Root cause statement:** the safe catalog owner cutover under-accepts the deterministic `portfolio_missing` reply shape, so frozen `decision.py` still owns that bounded normal path.
- **Fix mechanism:**
  - extend `_should_accept_turn_planner_catalog_result(...)` with one additional bounded `portfolio not_found` envelope
  - pass downstream `error_code` into the acceptance gate
  - keep `catalog.location` `not_found` and other non-safe outcomes on legacy fallback

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `_try_handle_turn_planner_safe_catalog_fact_owner_cutover(...)`
  - existing `TurnPlanner.build_from_policy_override(...)`
  - existing `execute_tool_action(...)`
  - existing owner-cutover finalizer and runtime metadata builders
- **External reuse:**
  - official Python `any()` semantics from the standard library docs
- **Why not reinvent the wheel:** the block only extends an existing owner path and acceptance gate.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded owner-replacement extension plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Only deterministic `portfolio not_found` becomes direct-owner; `catalog.location not_found` and other non-safe catalog outcomes still fall back to legacy delegate.
- Existing safe catalog ok-paths remain unchanged.

## Scope
- Extend the safe catalog acceptance gate for deterministic `portfolio_missing` replies.
- Preserve downstream tool decision metadata through the existing owner finalizer.
- Add focused regression coverage for `portfolio not_found` bypass while keeping the existing unsafe fallback test intact.
- Sync canon/session artifacts.

## Out of scope
- `catalog.location` `not_found`
- services-overview collect-style followups
- frozen legacy semantic files
- new semantic bridge families
- continuity-writer work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-portfolio-not-found-owner-cutover-a922.md`
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
2. Extend the safe catalog acceptance gate for deterministic `portfolio_missing` replies.
3. Keep the existing owner finalizer but pass `error_code` into the bounded acceptance check.
4. Add focused regression coverage for `portfolio not_found` bypass while preserving the unsafe fallback test.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- deterministic `portfolio not_found` replies bypass frozen `decision.py`
- `catalog.location not_found` still falls back to legacy delegate
- no frozen-router edits and no new semantic bridges are introduced
- runtime metadata records downstream `tool_decision` correctly for the owner-cutover path

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'safe_catalog_owner'`
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
- reasoning-core tests proving safe `portfolio not_found` owner bypass and unsafe `location not_found` fallback
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** reasoning-core + contracts + architecture only for this bounded block
- **Stop condition:** if `portfolio not_found` needs collect-state mutation or booking followup state beyond the existing owner finalizer, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded owner-replacement extension only; no new entrypoints or semantic bridges
- **Go/no-go signals:** reasoning-core + contracts + architecture suites green; semantic bridge growth guard green
- **Rollback:** revert the acceptance-gate extension, tests, and doc sync
- **Post-release monitoring window:** next block should either extend another safe owner seam or move to a larger planner/outcome cutover without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe portfolio not-found owner cutover and generated packet output.

## Rollback
1. Revert the `reasoning_core` acceptance-gate change, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into `catalog.location` `not_found` or collect-state semantics
- no counting this block as done unless deterministic `portfolio not_found` replies become direct-owner and `catalog.location not_found` still falls back

## Risks / blockers
- if missing-portfolio reply actually depends on hidden stateful followup semantics, direct-owner cutover would be unsafe
- if the acceptance gate is too broad, other non-safe catalog `not_found` outcomes could bypass legacy incorrectly

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader catalog/info missing-data outcomes still remain on the legacy delegate
  - richer semantic owner slices still remain in frozen `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only extends one existing safe owner envelope; broader missing-data or collect semantics would widen scope too much
- **Risk if deferred:**
  - legacy `decision.py` would keep owning another deterministic catalog reply path that the new owner already has enough information to realize safely
- **Linked follow-up Task Package(s):**
  - next bounded owner-replacement TP after this cutover, or richer planner/outcome cutover TP if no safe seam remains
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next candidate needs collect-state writes, handoff creation, or new bridge growth

## Next-block contract (mandatory)
- **Next block objective:** take the next bounded owner-replacement seam only if it deletes another legacy semantic path without new bridge growth; otherwise switch to a larger planner/outcome cutover
- **First deterministic check command:** `rg -n "_should_accept_turn_planner_catalog_result|_should_accept_turn_planner_service_query_result|_should_accept_turn_planner_booking_verification_result|tool_decision == \"not_found\"" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** if the next candidate needs collect-state mutation, handoff creation, or frozen-router edits, do not force another micro-cutover
- **Owner role for closure:** `Top Architect`
