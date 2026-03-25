# TP-2026-03-16-consultant-core-protective-lexical-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROTECTIVE-LEXICAL-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DOMAIN-ROUTER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-domain-router-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded lexical-semantics seam из frozen runtime в wrapped ingress: `reasoning_core` должен вычислять `opt_out` и `frustration` до delegate and scope them as request-local overrides, so frozen `decision.py` and `classify_intent(...)` consume precomputed protective lexical state instead of owning the first pass themselves.

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
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1688,1765p' truffles-api/app/services/intent_service.py`
  - `sed -n '1,130p' truffles-api/app/core/intent_routing.py`
  - `sed -n '17554,17645p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1448,1488p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still performs the first direct `is_opt_out_message(...)` and `is_frustration_message(...)` checks in protective routing branches.
  - `classify_intent(...)` already short-circuits on those same lexical guards before any LLM path, but the first ownership of those guards still begins inside frozen runtime.
  - the existing intent-semantic override bridge already scopes `normalized_text`, `intent`, and `is_human_request`; it can be extended without frozen-file edits.
  - `reasoning_core` already primes lexical and domain overrides, so another bounded lexical guard bridge fits the current ingress seam.
- `Detected drift (docs vs code)`: ingress owns greeting/thanks/ack/low-signal/status/human-request and domain routing, but `opt_out` and `frustration` still start in frozen runtime.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python contextvars ContextVar reset token documentation`
- **Date/time (local):** `2026-03-16 08:56 +05`
- **Why this query is precise:** this block extends request-scoped override state again and must preserve token/reset safety across async delegate execution.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ContextVar.set()` must be paired with `reset(token)` and is appropriate for per-request async-local override scopes.
- **Decision:** `reuse + integrate` — extend the existing intent-semantic override payload instead of introducing another process-global or request-mutable channel.
- **Rejected options:**
  - editing frozen `decision.py` to skip protective lexical checks directly
  - process-global shared lexical caches
  - introducing a second separate protective override channel when the current intent-semantic override already matches by normalized text
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** the first `opt_out` / `frustration` lexical safety checks still happen inside frozen runtime.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/intent_service.py` and observe that `classify_intent(...)` short-circuits on `is_opt_out_message(...)` and `is_frustration_message(...)`.
  2. Open `truffles-api/app/routers/webhook/decision.py` and observe direct uses of those functions in early routing branches.
  3. Open `truffles-api/app/services/reasoning_core.py` and observe that the current lexical override bridge does not carry `opt_out` or `frustration` flags.
- **Evidence to capture:**
  - `reasoning_core` scopes protective lexical flags before delegate execution
  - `intent_service.is_opt_out_message(...)` and `intent_service.is_frustration_message(...)` consume request-scoped overrides for matching text
  - `classify_intent(...)` consumes the same override payload and returns `Intent.REJECTION` / `Intent.FRUSTRATION` without owning the first lexical pass
  - override state resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is frozen runtime still owning a semantic seam? Because the protective lexical checks still start there.
  2. Why does that matter? Because those checks steer rejection/handoff behavior before richer routing and LLM paths.
  3. Why not edit `decision.py`? Because the file is frozen.
  4. Why can a bridge work? Because the same heuristics already live in reusable service functions and the normalized-text-scoped override channel already exists.
  5. Why does this reduce drift? Because another repeated lexical authority moves to wrapped ingress and frozen code becomes only a consumer of precomputed state.
- **Root cause statement:** `opt_out` and `frustration` authority remains in frozen runtime because the current ingress override bridge does not carry those lexical guard signals into `intent_service` before delegate execution.
- **Fix mechanism:**
  - extend `app/core/intent_routing.py` to detect `opt_out` / `frustration`
  - extend `intent_service` override consumption for `is_opt_out_message(...)` and `is_frustration_message(...)`
  - prime the richer override from `reasoning_core.py` around delegate execution

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `use_intent_semantic_override(...)` request-local bridge
  - existing `is_opt_out_message(...)` / `is_frustration_message(...)` heuristics
  - existing `detect_intent_routing_primitives(...)` ingress bridge structure
- **External reuse:**
  - official Python `contextvars` documentation
- **Why not reinvent the wheel:** the repo already has the lexical guard heuristics and the override channel; this block only widens the existing payload.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `17`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded code-first ingress bridge with focused tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No override bleed across requests or unrelated text.
- No change to lexical heuristic definitions themselves in this block.
- No change to downstream stateful response execution; frozen delegate still owns later routing and effects.

## Scope
- Extend `truffles-api/app/core/intent_routing.py` with `opt_out` / `frustration` detection.
- Extend `truffles-api/app/services/intent_service.py` override consumption for those protective lexical guards.
- Prime the richer override from `truffles-api/app/services/reasoning_core.py` around delegate execution.
- Add deterministic tests in `truffles-api/tests/test_intent.py` and `truffles-api/tests/test_reasoning_core.py`.
- Sync required canon/session artifacts.

## Out of scope
- controller-route or action-resolution bridge work
- domain-router changes
- debounce/buffer migration
- booking/pending runtime migration
- proof/eval excision
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-protective-lexical-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
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
2. Extend `app/core/intent_routing.py` to detect `opt_out` / `frustration` and encode them into the existing override payload.
3. Extend `intent_service.py` so `is_opt_out_message(...)` and `is_frustration_message(...)` consume the request-local override for matching text.
4. Reuse the current `reasoning_core` lexical bridge so delegate execution sees the richer override payload.
5. Add deterministic service/runtime tests for override matching, reset behavior, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` scopes `opt_out` / `frustration` lexical state before delegate execution
- `intent_service.is_opt_out_message(...)` and `intent_service.is_frustration_message(...)` consume request-scoped override state for matching text
- `classify_intent(...)` returns `Intent.REJECTION` / `Intent.FRUSTRATION` from the same override payload when applicable
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
- richer lexical detector in `truffles-api/app/core/intent_routing.py`
- override consumption in `truffles-api/app/services/intent_service.py`
- delegate priming in `truffles-api/app/services/reasoning_core.py`
- focused service/runtime tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into controller-route ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped protective lexical override extension only
- **Go/no-go signals:** reasoning-core + intent tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep the previous ingress bridges intact
- **Post-release monitoring window:** next block should move a richer controller/action seam, not reopen continuity work

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual protective lexical bridge being executed.

## Rollback
- Revert this TP's `intent_routing.py`, `reasoning_core.py`, `intent_service.py`, test, and doc changes; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new lexical heuristics or phrase-hardcodes in runtime core beyond reuse of existing service heuristics.
- No second parallel override channel for the same normalized-text lexical state.

## Risks/Blockers
- if override matching is too broad, unrelated message text may consume stale protective lexical state.
- if lexical precedence diverges from `classify_intent(...)`, direct guard calls and intent classification could disagree.
- if the block grows into controller/action ownership, it exceeds bounded scope and must be split.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: controller-route ownership, class-router result ownership, action-resolution ownership, and booking/pending semantics still live in frozen `decision.py`; debounce/buffer remains legacy-owned.
- `Why not in this block`: this block only moves another bounded lexical guard family.
- `Risk if deferred`: frozen runtime keeps owning protective lexical routing seams after the current ingress bridges.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming ingress owns protective lexical + controller routing.

## Next-block contract (mandatory)
- `Next block objective`: move the next richer semantic seam after the protective lexical bridge, likely controller-route ownership, without touching frozen files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: override state not text-scoped; lexical precedence mismatch; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
