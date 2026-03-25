# TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-FACT-OWNER-CUTOVER-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-SERVICE-QUERY-FACT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-service-query-fact-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-TURN-PLANNER-RICHER-MASTER-OR-BOOKING-OWNER-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий owner-replacement cutover после safe grounded pricing/duration: grounded `master_query` fact turns already covered by the existing policy override must stop delegating their first semantic owner step into frozen `truffles-api/app/routers/webhook/decision.py`. `turn_planner` should keep owning the typed `PolicyDecision`, and `reasoning_core` should directly realize/save/send only the bounded safe master-service-match fact replies via existing read-only pack helpers, so the legacy router becomes unreachable for this slice on the normal runtime path.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-service-query-fact-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_info_master_long_hair.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/pack_runtime_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1170,1695p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '901,1175p' truffles-api/app/services/pack_runtime_service.py`
  - `sed -n '2575,3065p' truffles-api/tests/test_reasoning_core.py`
  - `sed -n '1,80p' truffles-api/tests/test_info_master_long_hair.py`
- `FACT findings`:
  - `reasoning_core` already bypasses frozen `decision.py` for bounded safe `info`, safe catalog, and grounded pricing/duration fact slices.
  - grounded `master_query` policy overrides already exist and already carry a concrete `service_query` plus `pack_refs=("master",)`.
  - read-only pack helpers already exist for master resolution and reply shaping: `resolve_master_intent(...)` and `build_master_reply_from_pack(...)`.
  - current safe service-query owner cutover intentionally excludes `pack_refs={"master"}`, so grounded master fact turns still delegate their first semantic owner step through frozen `decision.py`.
- `Detected drift (docs vs code)`: the execution strategy lock now forbids counting new bridge growth as progress; grounded master-query fact still only primes an override and therefore has not deleted legacy semantic authority yet.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python all built-in function official docs`
- **Date/time (local):** `2026-03-16 21:22 +0500`
- **Why this query is precise:** this block needs a strict conjunction of bounded acceptance predicates so the owner cutover only accepts master service-match replies and falls back on any collect/not-found path.
- **Sources opened (from this query):**
  - `Built-in Functions — Python 3 documentation` — `https://docs.python.org/3/library/functions.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `all(...)` is sufficient for expressing a strict contract gate over several required reply predicates without adding another helper abstraction or hidden partial acceptance.
- **Decision:** `reuse + integrate` — use explicit conjunctive acceptance checks for `master_query_contract`, `master_reply_mode`, action class, and `info_sections` membership.
- **Rejected options:**
  - widening the safe service-query owner cutover to accept every `pack_refs={"master"}` result
  - adding any new detector/phrase bridge family
  - widening the block into collect ownership for service-clarify or service-not-found master paths
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** even after safe info, safe catalog, and safe grounded pricing/duration owner cutovers, grounded `master_query` fact turns still route their first semantic owner step through frozen `decision.py`.
- **Minimal reproduction:**
  1. Send a grounded master question like `Какие мастера делают маникюр?` into `reasoning_core.handle_webhook_payload(...)`.
  2. Observe that `detect_policy_core_route_snapshot(...)` already builds a complete fact override with `intent="master_query"`, `tool_action="catalog.service_query"`, `tool_args.service_query`, and `pack_refs=("master",)`.
  3. Observe that the runtime still delegates into `decision_router._handle_webhook_payload(...)` instead of using `turn_planner` + direct read-only pack realization.
- **Evidence to capture:**
  - `reasoning_core` returns a direct owner-cutover response for bounded grounded master-service-match turns without calling frozen `decision.py`.
  - if the shared master pack helpers resolve into `service_clarify`, `service_not_found`, or no reply, the runtime falls back to the legacy delegate before persistence.
- **Five Whys (or equivalent):**
  1. Why does the legacy router still own these turns? Because the direct owner path currently stops at safe info, safe catalog, and grounded pricing/duration slices.
  2. Why is grounded `master_query` the next safe seam? Because policy override priming already exists and the downstream master reply helpers are read-only and pack-driven.
  3. Why not accept every grounded master reply? Because `service_clarify` and `service_not_found` are COLLECT-like semantics and widening into them would recreate semantic seam farming.
  4. Why is the current path a problem? Because bridge priming alone does not delete semantic authority; frozen `decision.py` still owns the first normal-path semantic decision for grounded master-service-match turns.
  5. Why fix this now? Because it deletes another live legacy fact seam without adding new ingress bridge families or touching frozen router files.
- **Root cause statement:** the runtime still lacked a bounded direct owner path for grounded `master_query` fact slices, so frozen `decision.py` remained the first semantic owner for service-grounded master-match turns even though read-only pack helpers for master resolution and reply shaping already existed.
- **Fix mechanism:**
  - add a bounded direct owner path in `reasoning_core` for grounded `master_query` fact turns
  - reuse `resolve_master_intent(...)` and `build_master_reply_from_pack(...)`
  - accept only strict FACT/service-match replies and fall back to the legacy delegate for collect-like or empty outcomes before persistence

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot.to_override()` payload shape
  - existing `turn_planner.build_from_policy_override(...)`
  - existing shared owner-cutover finalizer in `reasoning_core`
  - existing `resolve_master_intent(...)`
  - existing `build_master_reply_from_pack(...)`
- **External reuse:**
  - Python built-in `all(...)` semantics from official docs
- **Why not reinvent the wheel:** this block must delete another legacy semantic seam, not add new routing or execution abstractions.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded owner replacement for grounded master fact turns plus required canon/session sync.

## Invariant
- No new generic ingress phrase-bridge family.
- No edit to frozen legacy semantic files.
- If direct owner realization cannot safely complete, runtime falls back to existing delegate path before persistence.
- Product contract remains FACT/COLLECT/HANDOFF; this block only cuts over bounded grounded FACT master-service-match replies.

## Scope
- Add a bounded direct owner path in `reasoning_core` for grounded `master_query` fact turns already covered by existing policy overrides.
- Reuse existing read-only master pack helpers.
- Add regression tests proving frozen `decision.py` is unreachable for the chosen slice on the normal path.
- Sync canon/session artifacts.

## Out of scope
- new semantic detector families
- collect/handoff owner cutover
- widening into service_clarify or service_not_found master ownership
- continuity writer completion
- boundary owner cutover
- proof-path rewrite
- frozen-router edits

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md`
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
2. Extend `reasoning_core` with a bounded direct owner path for grounded `master_query` fact turns.
3. Reuse existing master pack helpers and keep acceptance narrow with explicit FACT/service-match predicates.
4. Add tests proving the direct owner path bypasses frozen `decision.py` and falls back cleanly when the master helper result is collect-like or empty.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` directly handles safe grounded `master_query` fact turns without delegating into frozen `decision.py` on the normal path.
- runtime falls back to the legacy delegate if direct realization cannot produce a bounded safe FACT/service-match reply.
- tests prove both owner-cutover and fallback behavior.
- no new detector family is added.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/pack_runtime_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime unit tests showing frozen delegate is not called for grounded master-service-match cutover turns
- fallback tests showing no early persistence when master helpers produce collect-like or empty outcomes
- updated source-of-truth / packet showing the new active block and cutover status

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + architecture only for this bounded block
- **Stop condition:** if this cutover requires new detector growth, frozen-router edits, or widening into collect ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded runtime cutover behind existing grounded master-query policy overrides only
- **Go/no-go signals:** reasoning-core + contract + architecture suites green; arch/session gates green
- **Rollback:** revert the new direct-owner path and tests only
- **Post-release monitoring window:** next block must continue owner replacement or switch to single continuity writer work, not bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the safe master-query fact owner cutover block and packet output.

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
- if the direct owner path accepts collect-like master replies, it becomes semantic widening instead of bounded owner replacement.
- if persistence happens before master reply acceptance is proven safe, fallback can become unsafe.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader planner/outcome ownership still remains in legacy `decision.py`
  - continuity still has fragmented writers
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is another bounded owner replacement slice; widening further would mix safe master facts with collect ownership and continuity writes
- **Risk if deferred:**
  - grounded master-service-match turns remain common informational questions still owned first by frozen legacy routing
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-turn-planner-richer-master-or-booking-owner-cutover-a922` (to be created after closure of this block)
- **Expiry/trigger to stop deferral:**
  - stop deferral once the next block can delete another richer semantic seam or switch to single continuity writer completion

## Next-block contract (mandatory)
- **Next block objective:** either take the next real owner-replacement slice after safe master fact cutover or switch to single continuity writer completion if the next semantic slice widens into collect/state ownership.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k 'turn_planner_safe_master_query'`
- **Blocked-by conditions:** any need for new detector growth, frozen-router edits, or collect/state ownership inside this block.
- **Owner role for closure:** `Top Architect`
