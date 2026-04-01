# TP-2026-03-16-consultant-core-controller-route-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DOMAIN-ROUTER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-domain-router-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OUTCOME-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий semantic seam из frozen `decision.py` в ingress path: `reasoning_core` должен заранее вычислять bounded `route_dialogue_controller(...)` override для low-risk controller classes (`greeting` и strong `out_of_domain`) и scope it as request-local state, чтобы frozen router потреблял precomputed controller route вместо первого controller LLM route pass для этих случаев.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-domain-router-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/__init__.py`
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
  - `sed -n '2740,2865p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1910,2238p' truffles-api/app/services/intent_service.py`
  - `sed -n '1260,1605p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1,220p' truffles-api/app/core/intent_routing.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_dialogue_controller(...)` call whenever controller attempt is allowed.
  - ingress already primes lexical intent primitives and domain-router snapshots before delegate, so it now has enough information to precompute a bounded controller route for low-risk classes.
  - `route_dialogue_controller(...)` in `intent_service.py` has no request-local override seam today, so even obvious greeting and strong out-of-domain turns still require the frozen router to own the first controller route decision.
  - bounded low-risk controller classes already have deterministic ingress signals: greeting/thanks/ack come from lexical primitives, and strong out-of-domain comes from the existing domain-router snapshot with `out_hits > 0` and `strict_in_hits == 0`.
- `Detected drift (docs vs code)`: wrapped ingress owns more early semantic seams now, but first controller-route ownership still starts inside frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/contextvars.html Python contextvars documentation`
- **Date/time (local):** `2026-03-16 11:24 +05`
- **Why this query is precise:** this block needs one more request-scoped async-local override, and it must reset safely after delegate exit.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ContextVar.set()` returns a token and the previous value must be restored with `reset(token)`; this is the correct mechanism for per-request async-local overrides.
- **Decision:** `reuse + integrate` — add a reset-safe dialogue-controller override in `intent_service.py` and prime it from `reasoning_core.py`.
- **Rejected options:**
  - editing frozen `decision.py` to skip controller routing directly
  - process-global override state
  - widening immediately into booking/info/consult controller ownership
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first controller-route ownership still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `_run_class_router_stage(...)` in `truffles-api/app/routers/webhook/decision.py`.
  2. Observe that when controller attempt is allowed, frozen code directly calls `legacy.route_dialogue_controller(...)`.
  3. Open `truffles-api/app/services/reasoning_core.py` and note that ingress already primes lexical/domain overrides but not controller-route overrides.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded controller-route override before delegate execution
  - `route_dialogue_controller(...)` consumes request-scoped override payloads for the same inbound without requiring LLM/provider init
  - override state resets after delegate exit and does not leak to unrelated message text
- **Five Whys (or equivalent):**
  1. Why is richer semantic ownership still legacy-shaped? Because controller-route still starts in frozen `decision.py`.
  2. Why does that matter? Because greeting and strong out-of-domain turns still pay for legacy controller ownership before any richer planner cutover.
  3. Why not cut over all controller classes now? Because that would widen into booking/info/consult semantics and break bounded scope.
  4. Why is a bounded bridge safe? Because greeting and strong out-of-domain already have deterministic ingress signals and do not require new runtime side effects.
  5. Why does this reduce drift? Because the new ingress path becomes first owner of another semantically meaningful route slice while frozen code becomes a consumer of precomputed state.
- **Root cause statement:** controller-route authority remains in frozen `decision.py` because `reasoning_core` does not yet prime any request-scoped `route_dialogue_controller(...)` override, even for low-risk classes already derivable from ingress lexical/domain snapshots.
- **Fix mechanism:**
  - add bounded controller-route snapshot detection to `app/core/intent_routing.py`
  - add reset-safe dialogue-controller override helpers to `intent_service.py`
  - prime the override from `reasoning_core.py` using already-resolved lexical/domain ingress state

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing lexical primitive detector in `truffles-api/app/core/intent_routing.py`
  - existing domain-routing snapshot in `truffles-api/app/core/intent_routing.py`
  - existing `route_dialogue_controller(...)` payload builder in `truffles-api/app/services/intent_service.py`
  - existing ContextVar override patterns already used for intent/domain bridges
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** the repo already has request-scoped override patterns and the controller payload builder; this block should reuse them instead of inventing a new bridge channel.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded controller-route bridge with focused deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden greeting/strong-out-of-domain controller routes.
- No override bleed across requests or unrelated message text.
- No change to downstream response text or stateful execution; frozen delegate still owns response execution.

## Scope
- Add bounded controller-route snapshot detection to `truffles-api/app/core/intent_routing.py`.
- Add request-scoped dialogue-controller override helpers to `truffles-api/app/services/intent_service.py`.
- Prime the override from `truffles-api/app/services/reasoning_core.py` using ingress lexical/domain snapshots.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- booking/info/consult controller ownership
- richer planner or policy-core cutover
- debounce/buffer bridge
- frozen-router edits
- proof-path work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-controller-route-bridge-a922.md`
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
2. Add bounded controller-route snapshot detection + export in `app/core/intent_routing.py`.
3. Add reset-safe dialogue-controller override helpers in `intent_service.py`.
4. Prime the override from `reasoning_core.py` around delegate execution.
5. Add deterministic tests for override matching, reset behavior, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded controller-route override before delegate execution
- `route_dialogue_controller(...)` consumes request-scoped override payloads for the same inbound without LLM/provider init
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
- bounded controller-route snapshot in `truffles-api/app/core/intent_routing.py`
- request-scoped dialogue-controller override helpers in `truffles-api/app/services/intent_service.py`
- delegate priming in `truffles-api/app/services/reasoning_core.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into booking/info/consult controller ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded controller-route override bridge only
- **Go/no-go signals:** reasoning-core + intent tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should move a richer semantic outcome seam, not generic scaffolding

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual controller-route bridge being executed.

## Rollback
- Revert this TP's `intent_routing.py`, `reasoning_core.py`, `intent_service.py`, test, and doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No process-global semantic cache without context isolation.
- No widening into booking/info/consult controller ownership in this block.

## Risks/Blockers
- if override matching is too broad, mixed messages may get forced into greeting/out-of-domain incorrectly.
- if out-of-domain gating is too weak, in-domain turns may bypass the controller LLM incorrectly.
- if override state is not normalized-text scoped, unrelated later requests may consume stale state.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: booking/info/consult controller ownership, richer planner ownership, boundary ownership, and booking/pending semantics still live in frozen `decision.py`; debounce/buffer remains legacy-owned.
- `Why not in this block`: this block only moves bounded greeting + strong out-of-domain controller-route ownership.
- `Risk if deferred`: frozen `decision.py` keeps owning the first controller-route pass even for low-risk classes already derivable from ingress.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-richer-semantic-outcome-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming ingress owns controller-route semantics beyond lexical/domain precomputation.

## Next-block contract (mandatory)
- `Next block objective`: move the next richer semantic outcome seam after the bounded controller-route bridge, without touching frozen files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: override state not text-scoped; out-of-domain gating too broad; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
