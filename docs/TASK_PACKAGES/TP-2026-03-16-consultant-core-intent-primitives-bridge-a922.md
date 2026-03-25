# TP-2026-03-16-consultant-core-intent-primitives-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-INTENT-PRIMITIVES-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-RUNTIME-CONTEXT-LOADER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-runtime-context-loader-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-CUTOVER-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть первый live semantic-routing seam из frozen `decision.py` в новый ingress путь: `reasoning_core` должен вычислять lexical intent-routing primitives для inbound до delegate, а frozen router должен только потреблять request-scoped overrides для fast-intent и early signal routing вместо собственного первого semantic pass.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-runtime-context-loader-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_ai_service.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/core/__init__.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/ai_service.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_ai_service.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '542,670p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '23340,23760p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1860,2035p' truffles-api/app/services/ai_service.py`
  - `sed -n '1706,1760p' truffles-api/app/services/intent_service.py`
  - `sed -n '1175,1415p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first lexical semantic pass for `fast_intent` and `_detect_intent_signals(...)`, even after wrapped ingress already owns secret-safe preflight, duplicate-preflight reuse, and initial runtime loader priming.
  - the actual semantic primitives are already expressed through reusable service functions (`is_greeting_message`, `is_thanks_message`, `is_acknowledgement_message`, `is_low_signal_message`, `is_bot_status_question`, `is_human_request_message`).
  - `reasoning_core` currently delegates without priming any semantic override seam, so frozen code still performs the first intent-routing primitive evaluation itself.
  - a bounded bridge is available without touching frozen files if those service functions consume request-scoped overrides primed by `reasoning_core`.
- `Detected drift (docs vs code)`: target ingress says planner enters after pack/capability/dialog state load under new-core ownership; current code still leaves the first lexical semantic routing pass inside frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python contextvars ContextVar async context manager reset token documentation`
- **Date/time (local):** `2026-03-16 08:33 Asia/Almaty`
- **Why this query is precise:** this block needs request-scoped semantic override state that is safe across async delegate execution and guaranteed to reset after exit.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ContextVar.set()` returns a token and the previous value must be restored with `reset(token)`; the storage is task-local and appropriate for per-request async overrides.
- **Decision:** `reuse + integrate` — add reset-safe ContextVar override helpers in `ai_service.py` and `intent_service.py`, then prime them from `reasoning_core` around delegate execution.
- **Rejected options:**
  - editing frozen `decision.py` to bypass its lexical routing functions directly
  - process-global mutable semantic caches
  - threading semantic override state through SQLAlchemy session objects
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** the first lexical semantic decisions for `fast_intent` and early intent signal routing still happen inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/decision.py` around `_detect_fast_intent(...)` and `_detect_intent_signals(...)`.
  2. Open `truffles-api/app/services/reasoning_core.py` and observe that delegate handoff currently primes preflight/runtime loader seams but no semantic-routing seam.
  3. Open `truffles-api/app/services/ai_service.py` and `truffles-api/app/services/intent_service.py` and observe that the semantic primitives are service functions with no request-scoped override bridge.
- **Evidence to capture:**
  - `reasoning_core` computes lexical intent-routing primitives before delegate
  - frozen router consumes request-scoped overrides for the same inbound instead of owning the first primitive pass
  - override state resets after delegate exit and does not leak to later requests
- **Five Whys (or equivalent):**
  1. Why is semantic ownership still too legacy-shaped? Because the first lexical intent-routing pass still lives in frozen `decision.py`.
  2. Why is that important? Because fast-intent and early signal routing are semantic authority, not transport plumbing.
  3. Why not edit `decision.py` directly? Because it is frozen for new semantics.
  4. Why can a bridge work? Because the actual primitive detectors already live in reusable service functions and can consume request-scoped overrides.
  5. Why does this reduce drift? Because the new ingress seam becomes the first owner of these primitives while frozen code becomes a consumer of precomputed state.
- **Root cause statement:** lexical intent-routing authority remains in frozen `decision.py` because `reasoning_core` does not yet prime any request-scoped semantic primitive override before delegate execution.
- **Fix mechanism:**
  - add a new-core lexical primitive detector in `app/core/intent_routing.py`
  - add reset-safe request-scoped override helpers to `ai_service.py` and `intent_service.py`
  - prime those overrides from `reasoning_core` around delegate execution so frozen router reuses them

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing lexical semantic functions in `truffles-api/app/services/ai_service.py`
  - existing human-request heuristic in `truffles-api/app/services/intent_service.py`
  - existing ContextVar bridge pattern already used in runtime-loader blocks
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** the repo already has the semantic primitive detectors; the missing piece is only a new-core orchestrator plus request-scoped override plumbing.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `18`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** the block is a real runtime semantic seam cutover with focused service/runtime tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No override bleed across requests or across unrelated message text.
- No change to outbound side effects or response text; frozen delegate still sends/saves, new ingress only owns the first lexical primitive pass.

## Scope
- Add a new-core lexical intent-routing primitive detector in `truffles-api/app/core/intent_routing.py`.
- Add request-scoped semantic override helpers to `truffles-api/app/services/ai_service.py` and `truffles-api/app/services/intent_service.py`.
- Prime intent-routing overrides from `truffles-api/app/services/reasoning_core.py` around delegate execution.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_ai_service.py`, and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- changing frozen `decision.py` logic
- richer LLM/policy-core planner cutover
- debounce/buffer bridge work
- booking/pending runtime migration
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-intent-primitives-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/ai_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_ai_service.py`
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
2. Add `app/core/intent_routing.py` with a bounded lexical primitive detector and export it from `app/core/__init__.py`.
3. Add reset-safe ContextVar override helpers in `ai_service.py` and `intent_service.py`.
4. Prime the overrides from `reasoning_core.py` around delegate execution.
5. Add deterministic tests for override matching, reset behavior, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` computes lexical intent-routing primitives before delegate execution
- frozen router consumes request-scoped primitive overrides for the same inbound without changing frozen files
- override state resets after delegate exit and does not apply to unrelated message text
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_ai_service.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- new lexical primitive detector in `truffles-api/app/core/intent_routing.py`
- request-scoped override helpers in `truffles-api/app/services/ai_service.py` and `truffles-api/app/services/intent_service.py`
- delegate priming in `truffles-api/app/services/reasoning_core.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into LLM/policy-core cutover, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped lexical primitive override bridge only
- **Go/no-go signals:** reasoning-core + ai-service + intent tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should cut a richer semantic outcome lane, not add more generic scaffolding

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual intent-primitives bridge being executed.

## Rollback
- Revert this TP's `app/core/intent_routing.py`, `reasoning_core.py`, `ai_service.py`, `intent_service.py`, test, and doc changes; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No process-global semantic cache without context isolation.
- No response text changes or silent fallback weakening in this block.

## Risks/Blockers
- if override matching is too broad, unrelated message text may consume stale semantic primitives.
- if override state is not reset, later requests may inherit wrong lexical routing.
- if the bridge starts to approximate richer planner behavior, it will exceed the bounded scope and must be split.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: richer intent/action resolution, boundary ownership, and booking/pending semantics still live in frozen `decision.py`; debounce/buffer remains legacy-owned.
- `Why not in this block`: this block only moves the first lexical routing primitive pass.
- `Risk if deferred`: frozen `decision.py` keeps owning the earliest semantic routing seam even after preflight and runtime-loader cutovers.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-rich-semantic-cutover-followup-a922`
- `Expiry/trigger to stop deferral`: before claiming the new core owns ingress-to-planner semantic routing.

## Next-block contract (mandatory)
- `Next block objective`: move the next richer semantic outcome lane out of frozen `decision.py` now that lexical intent primitives enter through the new ingress seam.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: override state not text-scoped; override reset not deterministic; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
