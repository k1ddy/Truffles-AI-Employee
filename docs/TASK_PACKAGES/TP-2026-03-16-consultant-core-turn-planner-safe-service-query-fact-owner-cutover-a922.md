# TP-2026-03-16-consultant-core-turn-planner-safe-service-query-fact-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SERVICE-QUERY-FACT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-CATALOG-FACT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-catalog-fact-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-RICHER-SERVICE-QUERY-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий owner-replacement cutover после safe catalog facts: grounded read-only `catalog.service_query` fact turns already covered by existing policy overrides for pricing and duration must stop delegating their first semantic owner step into frozen `truffles-api/app/routers/webhook/decision.py`. `turn_planner` should keep owning the typed `PolicyDecision`, and `reasoning_core` should directly realize/save/send only the bounded safe pricing and duration fact replies via existing read-only `execute_tool_action(...)` behavior, so the legacy router becomes unreachable for this slice on the normal runtime path.

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
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/core/turn_planner.py`
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
  - `sed -n '1140,1455p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '2235,2605p' truffles-api/app/services/tool_registry_service.py`
  - `sed -n '1768,1905p' truffles-api/tests/test_reasoning_core.py`
- `FACT findings`:
  - the new owner path already bypasses frozen `decision.py` for bounded safe `info`, `services_overview`, `location`, and `portfolio` facts.
  - grounded pricing and duration overrides already exist and already resolve into read-only `catalog.service_query` executions.
  - `execute_tool_action(...)` already contains the needed read-only pricing and duration behavior; the missing piece is consuming those bounded outputs directly in `reasoning_core`.
- `Detected drift (docs vs code)`: the strategy lock requires owner deletion/unreachability, but grounded pricing/duration still only prime overrides and still route their first semantic owner step through frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python set issubset official docs`
- **Date/time (local):** `2026-03-16 20:30 +0500`
- **Why this query is precise:** this block needs a strict bounded allowlist for accepted `pack_refs` so the direct owner path stays narrow and does not expand into mixed fact seams.
- **Sources opened (from this query):**
  - `Built-in Types — Python 3.14.3 documentation` — `https://docs.python.org/3/library/stdtypes.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `set.issubset()` / explicit set comparisons are sufficient to keep accepted `pack_refs` narrow without inventing a new helper layer.
- **Decision:** `reuse + integrate` — use strict set-based matching for accepted pack refs and keep the block bounded to pricing and duration facts only.
- **Rejected options:**
  - broad “any ok service_query fact” acceptance
  - new detector growth in `info_signal_service.py`
  - widening the block into master-query or collect ownership
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** even after the safe info and safe catalog owner cutovers, grounded pricing and duration facts still route their first semantic owner step through frozen `decision.py`.
- **Minimal reproduction:**
  1. Send `Сколько стоит маникюр?` or `Сколько длится маникюр?` into `reasoning_core.handle_webhook_payload(...)`.
  2. Observe that `detect_policy_core_route_snapshot(...)` builds a complete fact override with `tool_action="catalog.service_query"` and a grounded `service_query`.
  3. Observe that the runtime still delegates into `decision_router._handle_webhook_payload(...)` instead of using `turn_planner` + direct read-only realization.
- **Evidence to capture:**
  - `reasoning_core` now returns a direct owner-cutover response for bounded grounded pricing/duration fact turns without calling frozen `decision.py`.
  - if the shared `catalog.service_query` result falls outside the safe allowlist, the runtime falls back to the legacy delegate before persistence.
- **Five Whys (or equivalent):**
  1. Why does the legacy router still own these turns? Because the direct owner path currently stops at `info`, `services_overview`, `location`, and `portfolio`.
  2. Why are pricing/duration the next safe seam? Because they already use read-only `catalog.service_query` execution with grounded service input.
  3. Why not accept every `catalog.service_query` response? Because that would widen the owner path into mixed semantic cases and recreate bridge-farming in another form.
  4. Why is the old path a problem? Because bridge priming alone does not remove semantic authority; frozen `decision.py` still owns the first normal-path semantic decision here.
  5. Why fix this now? Because grounded pricing/duration are the next bounded read-only fact seam with existing runtime helpers and no new detector growth.
- **Root cause statement:** the runtime still lacked a bounded direct owner path for grounded read-only `catalog.service_query` fact slices, so frozen `decision.py` remained the first semantic owner for grounded pricing and duration turns even though their downstream read-only execution already existed.
- **Fix mechanism:**
  - add a bounded direct owner path in `reasoning_core` for grounded pricing and duration `catalog.service_query` facts
  - keep acceptance narrow via explicit allowed `pack_refs` plus downstream tool-decision allowlists
  - preserve fallback to the legacy delegate whenever the read-only service-query result is outside the bounded safe envelope

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot.to_override()` payload shape
  - existing `turn_planner.build_from_policy_override(...)`
  - existing `execute_tool_action(...)`
  - existing shared owner-cutover finalizer in `reasoning_core`
- **External reuse:**
  - Python built-in set comparison rules from official docs
- **Why not reinvent the wheel:** this block must delete another legacy semantic seam, not add new routing or execution abstractions.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded owner replacement for grounded service-query fact slices plus required canon/session sync.

## Invariant
- No new generic ingress phrase-bridge family.
- No edit to frozen legacy semantic files.
- If direct owner realization cannot safely complete, runtime falls back to existing delegate path before persistence.
- Product contract remains FACT/COLLECT/HANDOFF; this block only cuts over bounded grounded FACT slices.

## Scope
- Add a bounded direct owner path in `reasoning_core` for grounded pricing and duration fact turns already covered by existing `catalog.service_query` policy overrides.
- Reuse existing shared service-query read-only behavior.
- Add regression tests proving frozen `decision.py` is unreachable for the chosen slice on the normal path.
- Sync canon/session artifacts.

## Out of scope
- new semantic detector families
- collect/handoff owner cutover
- master-query owner cutover
- continuity writer completion
- boundary owner cutover
- proof-path rewrite
- frozen-router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-service-query-fact-owner-cutover-a922.md`
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
2. Extend `reasoning_core` with a bounded direct owner path for grounded pricing and duration `catalog.service_query` facts.
3. Reuse existing shared service-query read-only execution and keep acceptance narrow with explicit downstream allowlists.
4. Add tests proving the direct owner path bypasses frozen `decision.py` and falls back cleanly when downstream results fall outside the safe envelope.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` directly handles safe grounded pricing and duration fact turns without delegating into frozen `decision.py` on the normal path.
- runtime falls back to the legacy delegate if direct realization cannot produce a bounded safe reply.
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
- runtime unit tests showing frozen delegate is not called for grounded pricing/duration cutover turns
- fallback test showing no early persistence when downstream service-query output is outside the safe envelope
- updated source-of-truth / packet showing the new active block and cutover status

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + architecture only for this bounded block
- **Stop condition:** if this cutover requires new detector growth, frozen-router edits, or widening into master-query/collect ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded runtime cutover behind existing safe grounded policy overrides only
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
  - active block metadata must match the safe service-query fact owner cutover block and packet output.

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
- if the direct owner path accepts too many downstream `catalog.service_query` variants, it becomes a semantic widening block instead of bounded owner replacement.
- if persistence happens before downstream acceptance is proven safe, fallback can become unsafe.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader planner/outcome ownership still remains in legacy `decision.py`
  - continuity still has fragmented writers
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is another bounded owner replacement slice; widening further would mix safe grounded facts with richer service-query semantics
- **Risk if deferred:**
  - grounded pricing and duration remain common informational turns still owned first by frozen legacy routing
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-turn-planner-richer-service-query-owner-cutover-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral once the next block can delete another richer semantic seam or switch to single continuity writer completion

## Next-block contract (mandatory)
- **Next block objective:** continue owner replacement with the next bounded semantic seam that can make a legacy `decision.py` branch unreachable without new detector growth, or move to single continuity writer completion if owner replacement stalls without deletion value
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py`
- **Blocked-by conditions:** need for new hotspot bridge growth, need for frozen-router edits, or inability to prove old-seam unreachability
- **Owner role for closure:** `Top Architect`
