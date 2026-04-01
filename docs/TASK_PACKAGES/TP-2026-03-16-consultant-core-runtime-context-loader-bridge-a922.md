# TP-2026-03-16-consultant-core-runtime-context-loader-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-RUNTIME-CONTEXT-LOADER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PREFLIGHT-CACHE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-preflight-cache-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий runtime-core seam из frozen `decision.py` в новый ingress путь: `reasoning_core` должен стать owner для initial pack/capability/truth loader на wrapped `/webhook`, а frozen delegate должен переиспользовать уже загруженный runtime context через request-scoped overrides вместо собственного первого build pass.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-preflight-cache-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/capabilities_runtime.py`
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_capabilities_runtime.py`
- `truffles-api/tests/test_knowledge_runtime.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/capabilities_runtime.py`
  - `truffles-api/app/services/knowledge_runtime.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_capabilities_runtime.py`
  - `truffles-api/tests/test_knowledge_runtime.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '9345,9390p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "build_runtime_capabilities|set_runtime_capabilities|build_runtime_truth|set_runtime_truth" truffles-api/app/services/reasoning_core.py truffles-api/app/services/capabilities_runtime.py truffles-api/app/services/knowledge_runtime.py`
  - `sed -n '1,120p' truffles-api/app/services/capabilities_runtime.py`
  - `sed -n '1,90p' truffles-api/app/services/knowledge_runtime.py`
- `FACT findings`:
  - frozen `decision.py` still performs the first runtime capability/truth load immediately after preflight, even though wrapped ingress already has the client/branch data needed to do that work before delegate.
  - `knowledge_runtime.py` already has a `ContextVar` override seam; `capabilities_runtime.py` does not.
  - the previous block already removed duplicate preflight derivation, so the next bounded seam is the initial runtime context loader.
  - `_apply_runtime_capabilities(...)` and `_apply_runtime_truth(...)` later in frozen `decision.py` still need to work for changed branch ids, so any override must be branch-aware and easy to reset.
- `Detected drift (docs vs code)`: target architecture says ingress should load pack/capabilities/dialog state before planner, but initial capability/truth loading is still owned by frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org contextvars Token reset documentation`
- **Date/time (local):** `2026-03-16 09:02 Asia/Almaty`
- **Why this query is precise:** this block needs request-scoped runtime loader overrides that are safe in async code and correctly reset after delegate exit.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** top-level `ContextVar` values are async-context-local; `set()` returns a token that must be reset to restore the previous context.
- **Decision:** `reuse + integrate` — add top-level runtime override/context-manager helpers in `capabilities_runtime.py` and `knowledge_runtime.py`, then prime them from `reasoning_core` around the wrapped delegate.
- **Rejected options:**
  - editing frozen `decision.py` to skip its initial runtime loader pass
  - process-global mutable cache without context isolation
  - storing loader state on SQLAlchemy session objects
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** wrapped `/webhook` still lets frozen `decision.py` own the first capability/truth loader pass even after preflight is already established in `reasoning_core`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/decision.py` around the first `build_runtime_capabilities(...)` / `build_runtime_truth(...)` calls.
  2. Open `truffles-api/app/services/reasoning_core.py` and observe that, after secret-safe preflight and preflight-cache bridge, delegate still enters frozen code without primed runtime loaders.
  3. Open `truffles-api/app/services/knowledge_runtime.py` and `truffles-api/app/services/capabilities_runtime.py` to see that truth has an override seam but capabilities do not.
- **Evidence to capture:**
  - `reasoning_core` primes initial runtime capabilities/truth before delegate on wrapped ingress
  - frozen `decision.py` reuses those runtime loaders through branch-aware overrides instead of doing the initial fetch itself
  - overrides reset after delegate return and do not leak across requests
- **Five Whys (or equivalent):**
  1. Why is the runtime pipeline still legacy-shaped? Because the first capability/truth load still happens inside frozen `decision.py`.
  2. Why is that a problem? Because pack/capability loader ownership remains in the old core instead of the new ingress seam.
  3. Why not edit `decision.py`? Because it is frozen.
  4. Why can an override bridge work? Because the loader services already expose context-local runtime state, and truth already has a matching override pattern.
  5. Why does this reduce drift? Because the same wrapped ingress seam that owns preflight can also own the first runtime context load, while frozen code merely consumes it.
- **Root cause statement:** initial runtime capability/truth loading still belongs to frozen `decision.py` because the new ingress seam does not yet prime branch-aware runtime loaders before delegate.
- **Fix mechanism:**
  - add branch-aware context-local override support to `capabilities_runtime.py`
  - add reset-safe context-manager helpers for both runtime loaders
  - make `reasoning_core` build and scope the initial runtime loaders around wrapped delegate execution using preflight payload data

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `ContextVar` pattern in `truffles-api/app/services/knowledge_runtime.py`
  - runtime capability/truth builders already used by frozen `decision.py`
  - wrapped preflight payload already produced by `reasoning_core`
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** the repo already uses context-local runtime state; this block only needs to add the missing override symmetry and reuse the existing builders.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `16`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded runtime-loader bridge with deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No stale runtime loader override bleed across requests.
- Branch-change refresh in frozen `decision.py` must still work when branch id changes later in the flow.

## Scope
- Add branch-aware runtime capability override helpers to `truffles-api/app/services/capabilities_runtime.py`.
- Add reset-safe runtime truth override context manager to `truffles-api/app/services/knowledge_runtime.py`.
- Prime initial runtime capability/truth loaders from `truffles-api/app/services/reasoning_core.py` around wrapped delegate execution.
- Add deterministic tests in runtime services and `truffles-api/tests/test_reasoning_core.py`.
- Sync canon/session artifacts.

## Out of scope
- richer planner/policy semantic cutover itself
- dedup/debounce bridge work
- frozen router edits
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-runtime-context-loader-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/capabilities_runtime.py`
- `truffles-api/app/services/knowledge_runtime.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_capabilities_runtime.py`
- `truffles-api/tests/test_knowledge_runtime.py`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and one web search.
2. Add branch-aware runtime capability override/context-manager helpers in `capabilities_runtime.py` and reset-safe truth override context manager in `knowledge_runtime.py`.
3. Prime initial runtime capability/truth loaders from `reasoning_core.py` around wrapped delegate execution using preflight payload data.
4. Add deterministic service/runtime tests for override reuse and reset behavior.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- wrapped `/webhook` primes initial runtime capabilities/truth before frozen delegate
- frozen initial loader pass reuses those overrides for matching branch ids
- branch-change refresh in frozen code still falls through to real builder when branch id changes
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_capabilities_runtime.py`
- `pytest -q truffles-api/tests/test_knowledge_runtime.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime capability override bridge in `truffles-api/app/services/capabilities_runtime.py`
- reset-safe truth override bridge in `truffles-api/app/services/knowledge_runtime.py`
- wrapped loader priming in `truffles-api/app/services/reasoning_core.py`
- updated runtime tests and session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or expands into policy semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** wrapped ingress runtime-loader bridge only
- **Go/no-go signals:** reasoning-core/runtime-service suites + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's runtime-loader service, reasoning_core, tests, and doc changes only
- **Post-release monitoring window:** next block should be an actual richer policy/semantic cutover, not more ingress scaffolding

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual runtime-context-loader bridge being executed.

## Rollback
- Revert this TP's `reasoning_core.py`, runtime-loader service, test, and doc changes; keep prior preflight bridge blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No process-global runtime loader cache without context isolation.
- No policy/planner semantic rewrites in this block.

## Risks/Blockers
- if branch matching is too loose, frozen code may consume stale runtime loader state after branch selection changes.
- if overrides are not reset, unrelated requests may inherit the wrong tenant runtime context.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: policy/planner semantics still live in frozen `decision.py`; dedup/debounce remain legacy-owned.
- `Why not in this block`: this block only moves the runtime context loader seam.
- `Risk if deferred`: wrapped ingress keeps delegating the first pack/capability load to frozen code.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-rich-semantic-cutover-followup-a922`
- `Expiry/trigger to stop deferral`: before claiming the new core owns ingress-to-planner runtime flow.

## Next-block contract (mandatory)
- `Next block objective`: take the next richer semantic cutover in `reasoning_core.py` now that preflight and initial runtime context loading both enter through the new ingress seam.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: runtime loader overrides not branch-aware; stale override state not reset; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
