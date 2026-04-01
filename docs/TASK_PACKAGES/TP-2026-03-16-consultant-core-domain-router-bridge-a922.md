# TP-2026-03-16-consultant-core-domain-router-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DOMAIN-ROUTER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-INTENT-PRIMITIVES-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-intent-primitives-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий semantic-routing seam из frozen `decision.py` в новый ingress путь: `reasoning_core` должен вычислять domain-router classification before delegate and scope it as request-local override, so frozen router consumes precomputed domain routing instead of owning the first domain pass itself.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-intent-primitives-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/core/__init__.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '2740,2855p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '2898,3015p' truffles-api/app/services/intent_service.py`
  - `sed -n '7994,8135p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1175,1415p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `classify_domain_with_scores(...)` pass during `_run_class_router_stage(...)`.
  - the actual domain classifier already lives in reusable `truffles-api/app/services/intent_service.py` and depends only on `message_text` plus `client_config`.
  - `reasoning_core` already owns preflight, runtime-loader priming, and lexical intent primitives, so it now has the information needed to precompute domain routing before delegate.
  - a bounded bridge is available without frozen-file edits if `classify_domain_with_scores(...)` consumes a request-scoped override.
- `Detected drift (docs vs code)`: ingress ownership has moved forward, but the first domain-routing semantic classification still begins inside frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python contextvars set reset token async task local documentation`
- **Date/time (local):** `2026-03-16 08:45 Asia/Almaty`
- **Why this query is precise:** this block again depends on request-scoped async-local override state that must be guaranteed to reset after delegate exit.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ContextVar.set()` returns a token and the previous value must be restored with `reset(token)`; async-task-local scope is appropriate for per-request overrides.
- **Decision:** `reuse + integrate` — add reset-safe domain-routing override helpers in `intent_service.py` and prime them from `reasoning_core`.
- **Rejected options:**
  - editing frozen `decision.py` to skip domain classification directly
  - process-global domain cache
  - carrying domain-routing state on SQLAlchemy sessions
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** the first domain-routing classification still happens inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `_run_class_router_stage(...)` in `truffles-api/app/routers/webhook/decision.py`.
  2. Observe the direct call to `legacy.classify_domain_with_scores(...)` before class-router result assembly.
  3. Open `truffles-api/app/services/reasoning_core.py` and note that wrapped ingress already primes earlier semantic/runtime seams but not domain routing.
- **Evidence to capture:**
  - `reasoning_core` computes domain routing before delegate
  - frozen router consumes request-scoped domain routing override for the same inbound instead of owning the first pass
  - override state resets after delegate exit and does not leak to later requests
- **Five Whys (or equivalent):**
  1. Why is semantic ownership still legacy-shaped? Because domain routing still begins in frozen `decision.py`.
  2. Why does that matter? Because domain routing affects out-of-domain vs in-domain semantic flow before richer action resolution.
  3. Why not edit `decision.py`? Because it is frozen.
  4. Why can a bridge work? Because the classifier already lives in a reusable service and needs only text plus client config.
  5. Why does this reduce drift? Because the new ingress seam becomes the first owner of domain classification while frozen code becomes a consumer of precomputed state.
- **Root cause statement:** domain-routing authority remains in frozen `decision.py` because `reasoning_core` does not yet prime any request-scoped domain-classification override before delegate execution.
- **Fix mechanism:**
  - add bounded domain-routing detection to `app/core/intent_routing.py`
  - add reset-safe request-local domain override helpers to `intent_service.py`
  - prime domain overrides from `reasoning_core.py` using the same client config that frozen router would later consume

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `classify_domain_with_scores(...)` in `truffles-api/app/services/intent_service.py`
  - `Client.config` already resolved by preflight or queryable through `client_id`
  - existing ContextVar bridge patterns already used in current ingress blocks
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** the repo already has the domain classifier; this block only moves where the first call is owned.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `17`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic-routing bridge with focused deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No override bleed across requests or across unrelated message text.
- No change to downstream side effects or response text; frozen delegate still owns stateful response execution.

## Scope
- Extend `truffles-api/app/core/intent_routing.py` with bounded domain-routing detection.
- Add request-scoped domain override helpers to `truffles-api/app/services/intent_service.py`.
- Prime domain-routing overrides from `truffles-api/app/services/reasoning_core.py` around delegate execution.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- richer LLM/policy-core planner cutover
- controller-route override work
- debounce/buffer bridge work
- booking/pending runtime migration
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-domain-router-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
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
2. Extend `app/core/intent_routing.py` with bounded domain-routing detection and export it if needed.
3. Add reset-safe domain override helpers in `intent_service.py`.
4. Prime the override from `reasoning_core.py` around delegate execution using resolved client config.
5. Add deterministic tests for override matching, reset behavior, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` computes domain routing before delegate execution
- frozen router consumes request-scoped domain routing override for the same inbound without frozen-file edits
- override state resets after delegate exit and does not apply to unrelated message text
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded domain-routing detector in `truffles-api/app/core/intent_routing.py`
- request-scoped domain override helpers in `truffles-api/app/services/intent_service.py`
- delegate priming in `truffles-api/app/services/reasoning_core.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into controller/policy-core cutover, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped domain-router override bridge only
- **Go/no-go signals:** reasoning-core + intent tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should move a richer semantic outcome or controller seam, not generic scaffolding

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual domain-router bridge being executed.

## Rollback
- Revert this TP's `intent_routing.py`, `reasoning_core.py`, `intent_service.py`, test, and doc changes; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No process-global semantic cache without context isolation.
- No controller/policy-core behavior changes in this block.

## Risks/Blockers
- if override matching is too broad, unrelated message text may consume stale domain routing.
- if resolved client config differs from frozen delegate inputs, domain routing may drift.
- if this block expands into controller-route ownership, it exceeds bounded scope and must be split.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: richer class-router resolution, controller-route ownership, boundary ownership, and booking/pending semantics still live in frozen `decision.py`; debounce/buffer remains legacy-owned.
- `Why not in this block`: this block only moves the first domain-routing classification pass.
- `Risk if deferred`: frozen `decision.py` keeps owning the next semantic-routing seam after lexical primitives.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming the new core owns ingress-to-class-router semantic routing.

## Next-block contract (mandatory)
- `Next block objective`: move the next richer semantic seam after domain routing, likely controller-route or action-resolution ownership, without touching frozen files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: override state not text-scoped; client-config resolution mismatch; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
