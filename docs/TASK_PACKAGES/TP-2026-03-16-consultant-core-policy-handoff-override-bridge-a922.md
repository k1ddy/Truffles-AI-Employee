# TP-2026-03-16-consultant-core-policy-handoff-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-POLICY-HANDOFF-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-controller-route-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OUTCOME-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий richer semantic outcome seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять bounded `route_llm_policy_core(...)` override для явных manager-request turns (`human_request` и `frustration`) и scope it as request-local state, чтобы frozen router потреблял precomputed policy handoff contract вместо первого policy-core LLM pass на этих turn-ах.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-controller-route-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/schemas/intent.py`
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
  - `sed -n '2381,2865p' truffles-api/app/services/intent_service.py`
  - `sed -n '12920,13720p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1260,1625p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,240p' truffles-api/app/core/intent_routing.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit manager-request turns.
  - ingress already primes lexical intent primitives and controller-route/domain snapshots before delegate, so it already has enough signal to recognize explicit handoff requests without the policy-core LLM.
  - `route_llm_policy_core(...)` in `intent_service.py` has no request-local override seam today, so explicit `human_request` / `frustration` turns still require frozen router to own the first semantic handoff contract.
  - downstream handoff execution, escalation policy, and conversation-state transitions already live after `route_llm_policy_core(...)`; this block can reuse them unchanged if it only injects a valid policy payload.
- `Detected drift (docs vs code)`: ingress owns lexical/controller precomputation, but first policy-core handoff semantics still begin inside frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/contextvars.html Python contextvars ContextVar reset token documentation`
- **Date/time (local):** `2026-03-16 12:20 +05`
- **Why this query is precise:** this block needs one more request-scoped async-local override, and it must reset safely after delegate exit.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ContextVar.set()` returns a token and the previous value must be restored with `reset(token)`; this is the correct mechanism for per-request async-local policy override state.
- **Decision:** `reuse + integrate` — add a reset-safe policy-core override in `intent_service.py` and prime it from `reasoning_core.py`.
- **Rejected options:**
  - editing frozen `decision.py` to skip policy-core directly
  - process-global override state
  - bypassing downstream escalation flow by returning early from `reasoning_core` for this block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic handoff ownership for explicit manager-request turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `route_llm_policy_core(...)` in `truffles-api/app/services/intent_service.py`.
  2. Observe that it always loads prompt/API-key/budget/provider path because there is no request-local override seam.
  3. Open the policy-core stage in `truffles-api/app/routers/webhook/decision.py` and note that explicit `human_request` / `frustration` turns still depend on this first policy-core call before downstream handoff execution.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded policy-core override before delegate execution for explicit manager-request turns
  - `route_llm_policy_core(...)` consumes request-scoped override payloads for the same inbound without requiring LLM/provider init
  - override state resets after delegate exit and does not leak to unrelated message text
  - downstream frozen handoff execution still runs unchanged
- **Five Whys (or equivalent):**
  1. Why is richer semantic outcome ownership still legacy-shaped? Because explicit handoff semantics still begin inside frozen `decision.py` via the first policy-core call.
  2. Why does that matter? Because clear manager-request turns still pay for legacy policy-core ownership before any richer semantic cutover.
  3. Why not cut over the whole handoff path now? Because that would widen into escalation/state execution and break bounded scope.
  4. Why is a bounded override safe? Because `human_request` and `frustration` are already explicit ingress signals and downstream handoff execution/validation remains unchanged.
  5. Why does this reduce drift? Because ingress becomes first owner of one real semantic outcome contract (`handoff`) while frozen code becomes a consumer of precomputed policy state.
- **Root cause statement:** explicit manager-request handoff semantics remain in frozen `decision.py` because `reasoning_core` does not yet prime any request-scoped `route_llm_policy_core(...)` override, even for lexical `human_request` / `frustration` turns that ingress already recognizes deterministically.
- **Fix mechanism:**
  - add bounded policy-core handoff snapshot detection to `app/core/intent_routing.py`
  - add reset-safe policy-core override helpers to `intent_service.py`
  - prime the override from `reasoning_core.py` using already-resolved ingress lexical state

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing lexical primitive detector in `truffles-api/app/core/intent_routing.py`
  - existing `route_llm_policy_core(...)` contract validator in `truffles-api/app/services/intent_service.py`
  - existing ContextVar override patterns already used for intent/domain/controller bridges
  - existing downstream handoff execution in frozen router
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** the repo already has request-scoped override patterns and a validated policy-core contract path; this block should reuse them instead of inventing a parallel seam.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with focused deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden explicit manager-request policy-core turns.
- No override bleed across requests or unrelated message text.
- No change to downstream handoff execution/state transitions; frozen delegate still owns escalation execution.

## Scope
- Add bounded policy-core handoff snapshot detection to `truffles-api/app/core/intent_routing.py`.
- Add request-scoped policy-core override helpers to `truffles-api/app/services/intent_service.py`.
- Prime the override from `truffles-api/app/services/reasoning_core.py` using ingress lexical primitives.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- full policy-core cutover
- booking/info/consult policy ownership
- early return from `reasoning_core` for handoff execution
- frozen-router edits
- proof-path work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-policy-handoff-override-bridge-a922.md`
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
2. Add bounded policy-core handoff snapshot detection + export in `app/core/intent_routing.py`.
3. Add reset-safe policy-core override helpers in `intent_service.py`.
4. Prime the override from `reasoning_core.py` around delegate execution.
5. Add deterministic tests for override matching, reset behavior, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded policy-core handoff override before delegate execution for explicit manager-request turns
- `route_llm_policy_core(...)` consumes request-scoped override payloads for the same inbound without LLM/provider init
- override state resets after delegate exit and does not apply to unrelated message text
- downstream frozen handoff execution remains unchanged
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
- bounded policy-core handoff snapshot in `truffles-api/app/core/intent_routing.py`
- request-scoped policy-core override helpers in `truffles-api/app/services/intent_service.py`
- delegate priming in `truffles-api/app/services/reasoning_core.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into booking/info/consult policy ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should move the next richer semantic outcome seam, not continuity/proof micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual policy handoff override bridge being executed.

## Rollback
- Revert this TP's `intent_routing.py`, `reasoning_core.py`, `intent_service.py`, test, and doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No process-global semantic cache without context isolation.
- No widening into booking/info/consult policy ownership in this block.
- No early `reasoning_core` handoff execution in this block.

## Risks/Blockers
- if override matching is too broad, non-manager-request turns may be forced into handoff incorrectly.
- if the override payload is not schema-valid, frozen policy validation will degrade or misclassify the turn.
- if override state is not normalized-text scoped, unrelated later requests may consume stale state.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still owns downstream policy validation and handoff execution.
- non-handoff policy-core semantics still begin in frozen runtime.

### Why not in this block
- widening past bounded manager-request handoff would turn this into a full policy-core cutover block.

### Risk if deferred
- other clear semantic outcomes still depend on frozen policy-core ownership.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-richer-semantic-outcome-bridge-a922.md` (to be created after this block)

### Expiry/trigger to stop deferral
- stop deferral when the next bounded semantic outcome can be proven safe without frozen-router edits.

## Next-block contract (mandatory)
### Next block objective
- move the next bounded semantic outcome seam after explicit manager-request handoff, using the same ingress override model.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k handoff`

### Blocked-by conditions
- policy override payload must validate through `validate_llm_policy_core_output()`.
- no frozen-router edits allowed.
- downstream handoff execution must remain unchanged.

### Owner role for closure
- `Top Architect`
