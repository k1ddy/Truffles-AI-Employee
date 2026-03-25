# TP-2026-03-16-consultant-core-turn-planner-safe-catalog-fact-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-CATALOG-FACT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-INFO-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-info-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SERVICE-QUERY-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий owner-replacement cutover после safe-info slice: turns already covered by existing policy overrides for `services_overview`, `location`, and `portfolio` must stop delegating their first semantic owner step into frozen `truffles-api/app/routers/webhook/decision.py`. `turn_planner` should keep owning the typed `PolicyDecision`, and `reasoning_core` should directly realize/save/send these bounded read-only fact replies via existing tool/info truth helpers so the legacy router becomes unreachable for this slice on the normal runtime path.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-info-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1120,1385p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1265,1660p' truffles-api/app/services/tool_registry_service.py`
  - `rg -n 'services_overview|location|portfolio|owner_cutover' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - the first owner-replacement slice is already active for safe `tool_action="info"` fact intents, proving the fallback-safe direct owner path works.
  - `services_overview`, `location`, and `portfolio` already have existing policy overrides plus existing read-only truth/tool builders, but they still delegate through frozen `decision.py`.
  - `tool_registry_service.py` already contains bounded read-only execution for `catalog.service_query` (`services_overview`), `catalog.location`, and `catalog.portfolio`, so the missing piece is owner replacement, not new signal detection.
- `Detected drift (docs vs code)`: the execution strategy says progress requires old-authority deletion or unreachability, but these read-only fact tool slices still only prime overrides instead of bypassing frozen legacy routing.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.sqlalchemy.org SQLAlchemy 2.0 order_by select official docs`
- **Date/time (local):** `2026-03-16 20:30 +0500`
- **Why this query is precise:** this block reuses existing read-only service overview/catalog query helpers; the implementation should stay on the standard ORM read pattern and avoid widening into a persistence refactor.
- **Sources opened (from this query):**
  - `SQLAlchemy ORM Querying Guide (SELECT)` — `https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html`
- **Source quality:** official SQLAlchemy documentation.
- **Existing solutions found:** the standard ORM read/query pattern already used by the existing safe catalog helpers is sufficient for this owner replacement; no new repository or persistence abstraction is needed.
- **Decision:** `reuse + integrate` — consume the existing read-only tool/info builders and keep the bounded cutover inside `reasoning_core`.
- **Rejected options:**
  - adding a new repository layer for catalog reads
  - adding another detector family in `info_signal_service.py`
  - widening the block into service-query semantic refactoring
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** even after the first owner-replacement slice, read-only fact turns for `services_overview`, `location`, and `portfolio` still route their first semantic owner step through frozen `decision.py`.
- **Minimal reproduction:**
  1. Send `Какие у вас услуги?`, `Где вы находитесь?`, or `Покажите примеры работ` into `reasoning_core.handle_webhook_payload(...)`.
  2. Observe that `detect_policy_core_route_snapshot(...)` builds a complete fact override for those turns.
  3. Observe that the runtime still delegates into `decision_router._handle_webhook_payload(...)` instead of using `turn_planner` + direct read-only realization.
- **Evidence to capture:**
  - `reasoning_core` now returns a direct owner-cutover response for bounded `services_overview` / `location` / `portfolio` fact turns without calling frozen `decision.py`.
  - if direct tool/info realization cannot produce a safe reply, the runtime falls back to the legacy delegate before persistence.
- **Five Whys (or equivalent):**
  1. Why does the legacy router still own these safe turns? Because the direct owner path currently accepts only `tool_action="info"` fact intents.
  2. Why are these slices still safe to cut over? Because their downstream realization is already read-only and already implemented in shared truth/tool helpers.
  3. Why is delegation a problem? Because bridge priming alone does not remove old authority; the first semantic owner still lives in frozen `decision.py`.
  4. Why not solve this with another detector? Because the strategy lock forbids new generic bridge growth and requires owner replacement.
  5. Why fix this now? Because these read-only fact slices are the next bounded owner seams with existing realization helpers and no mutation risk.
- **Root cause statement:** the runtime still lacked a bounded direct owner path for existing read-only fact tool actions beyond `tool_action="info"`, so frozen `decision.py` remained the first semantic owner for `services_overview`, `location`, and `portfolio` even though their realization logic already existed elsewhere.
- **Fix mechanism:**
  - keep using `turn_planner.build_from_policy_override(...)`
  - add a bounded direct owner path in `reasoning_core` for read-only fact tool actions already covered by existing shared builders
  - reuse `tool_registry_service` / existing truth helpers for reply generation
  - preserve fallback to the legacy delegate whenever direct realization cannot safely complete

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot.to_override()` payload shape
  - existing `tool_registry_service.execute_tool_action(...)`
  - existing `_format_services_overview_reply(...)`, `_catalog_location(...)`, and `_catalog_portfolio(...)` downstream helpers via tool registry
  - existing persistence/transport helpers already used by the safe-info owner cutover
- **External reuse:**
  - standard SQLAlchemy ORM read-query pattern from official docs
- **Why not reinvent the wheel:** this block must delete another legacy semantic seam, not grow new routing or persistence abstractions.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded owner replacement for existing read-only fact tool slices plus required canon/session sync.

## Invariant
- No new generic ingress phrase-bridge family.
- No edit to frozen legacy semantic files.
- If direct owner realization cannot safely complete, runtime falls back to existing delegate path before persistence.
- Product contract remains FACT/COLLECT/HANDOFF; this block only cuts over bounded FACT slices.

## Scope
- Add a bounded direct owner path in `reasoning_core` for `services_overview`, `location`, and `portfolio` fact turns already covered by existing policy overrides.
- Reuse existing tool/info truth builders.
- Add regression tests proving frozen `decision.py` is unreachable for the chosen slice on the normal path.
- Sync canon/session artifacts.

## Out of scope
- new semantic detector families
- collect/handoff owner cutover
- pricing/duration/master-query/tool-mutation ownership
- continuity writer completion
- boundary owner cutover
- proof-path rewrite
- frozen-router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-catalog-fact-owner-cutover-a922.md`
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
2. Extend `reasoning_core` with a bounded direct owner path for existing read-only catalog/info fact tool slices beyond `tool_action="info"`.
3. Reuse existing shared tool/info helpers to realize those replies without delegating into frozen `decision.py`.
4. Add tests proving the direct owner path bypasses frozen `decision.py` and falls back cleanly when direct realization is unavailable.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` directly handles safe `services_overview`, `location`, and `portfolio` fact intents without delegating into frozen `decision.py` on the normal path.
- runtime falls back to the legacy delegate if direct realization cannot produce a safe reply.
- tests prove both owner-cutover and fallback behavior.
- no new detector family is added.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime unit tests showing frozen delegate is not called for the cutover slice
- fallback test showing no early persistence when direct realization cannot complete
- updated source-of-truth / packet showing the new active block and cutover status

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + architecture only for this bounded block
- **Stop condition:** if this cutover requires a new detector family, a frozen-router edit, or mutation-heavy tool ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded runtime cutover behind existing safe policy overrides only
- **Go/no-go signals:** reasoning-core + contract + architecture suites green; arch/session gates green
- **Rollback:** revert the new direct-owner path and tests only
- **Post-release monitoring window:** next block must continue owner replacement or single continuity writer work, not bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe catalog fact owner cutover block and packet output.

## Rollback
1. Revert the new `reasoning_core` direct owner path, tests, and canon/session sync.
2. Regenerate packet.
3. Re-run contract/architecture/session gates.

## No-go
- no new `detect_*` or `looks_like_*` families
- no frozen-router edit
- no widening into continuity/proof refactors
- no counting a new override as progress unless the legacy semantic seam becomes unreachable for this slice

## Risks / blockers
- if direct owner path starts persisting before tool realization is proven safe, fallback can become unsafe; realization must finish before persistence.
- if `catalog.service_query` expands beyond `services_overview` within this block, it becomes a wider service-query semantic refactor and must stop.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader planner/outcome ownership still remains in legacy `decision.py`
  - continuity still has fragmented writers
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is another bounded owner replacement slice; widening further would mix safe fact tools with richer semantic refactors
- **Risk if deferred:**
  - if read-only fact tool slices keep delegating, the repo keeps carrying unnecessary frozen-router authority on common informational turns
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-turn-planner-safe-service-query-owner-cutover-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral once the next block can delete another richer semantic seam or switch to single continuity writer completion

## Next-block contract (mandatory)
- **Next block objective:** continue owner replacement with the next bounded semantic seam that can make a legacy `decision.py` branch unreachable without new detector growth, or move to single continuity writer completion if owner replacement stalls without deletion value
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** need for new hotspot bridge growth, need for frozen-router edits, or inability to prove old-seam unreachability
- **Owner role for closure:** `Top Architect`
