# TP-2026-03-16-consultant-core-duration-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DURATION-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PRICING-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROMOTIONS-POLICY-OVERRIDE-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded richer semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-grounded duration turns, чтобы frozen router потреблял precomputed `catalog.service_query` duration contract вместо первого policy-core LLM pass на этих turns, при этом mixed-info arbitration, service-clarify behavior, and downstream tool execution остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '120,240p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '268,420p' truffles-api/app/core/intent_routing.py`
  - `sed -n '583,655p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '1595,1635p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit service-grounded duration turns even though downstream info execution already handles `intent="duration"` through `catalog.service_query` plus `tool_args.service_query`.
  - the request-scoped policy override seam already transports `tool_args`, `pack_refs`, and `capability`, so the remaining gap is a routing-neutral duration detector plus a bounded duration snapshot branch.
  - reusable routing-neutral duration primitives already exist outside frozen files via `_has_duration_signal(...)`, `_has_price_signal(...)`, `looks_like_services_overview_message(...)`, `looks_like_hours_policy_message(...)`, `detect_location_policy_pack_refs(...)`, and `get_pack_service_hint(...)`.
  - the pricing bridge already established the grounded service-query contract shape, so this block can reuse the same override transport without changing downstream execution.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for manager-request, style-reference, booking-verification, services-overview, location/parking, hours, and grounded pricing turns, but explicit grounded duration semantics still begin with a frozen policy-core LLM call.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/stdtypes.html Python str.strip documentation`
- **Date/time (local):** `2026-03-16 12:47 +05`
- **Why this query is precise:** this block reuses grounded `service_query` trimming before building a duration snapshot, so it must keep Python’s built-in string-boundary normalization semantics rather than inventing a new custom trim rule.
- **Sources opened (from this query):**
  - `Built-in Types — Python documentation` — `https://docs.python.org/3/library/stdtypes.html#str.strip`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `str.strip()` removes leading and trailing whitespace/characters without changing internal content, which matches the bounded service-hint normalization contract already used by the pricing bridge.
- **Decision:** `reuse + integrate` — reuse the existing `service_query.strip()` contract for duration snapshots instead of adding a new normalization path.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit explicit duration routing directly
  - inventing a duration-specific regex cleaner for service hints
  - bypassing frozen delegate execution with a direct `reasoning_core` reply
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit service-grounded duration turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/info.py` and verify that downstream info execution already handles `intent="duration"` via `catalog.service_query` and `tool_args.service_query`.
  2. Open `truffles-api/app/core/intent_routing.py` and confirm that the bounded policy snapshot branches cover hours and grounded pricing, but not grounded duration.
  3. Open `truffles-api/app/services/info_signal_service.py` and confirm that there is no routing-neutral grounded duration detector yet.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded grounded-duration policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - the duration snapshot carries `tool_args.service_query`, `pack_refs=["duration"]`, and `capability="duration"`
  - override state resets after delegate exit and does not leak to unrelated message text
  - mixed price/duration, location/hours, and services-overview turns remain outside this bounded slice
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because explicit service-grounded duration turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because downstream service-query execution already exists, but it still depends on frozen semantic ownership before it can run.
  3. Why has ingress not taken this slice yet? Because the current routing-neutral helpers do not expose a bounded grounded duration detector.
  4. Why is a bounded cut now safe? Because reusable duration, price, hours, and service-hint primitives already exist outside the frozen files.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit fact contract while frozen code remains only the executor of that contract.
- **Root cause statement:** explicit grounded duration semantics remain in frozen `decision.py` because ingress still lacks a bounded routing-neutral duration detector plus a matching `PolicyCoreRouteSnapshot` branch that carries grounded `tool_args.service_query` through the existing request-scoped override seam.
- **Fix mechanism:**
  - add a routing-neutral explicit grounded duration detector outside frozen runtime
  - add a bounded duration snapshot branch in `detect_policy_core_route_snapshot(...)`
  - verify delegate priming and override consumption through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing `_has_duration_signal(...)`, `_has_price_signal(...)`, `looks_like_services_overview_message(...)`, `detect_location_policy_pack_refs(...)`, `looks_like_hours_policy_message(...)`, and `get_pack_service_hint(...)`
  - existing downstream `catalog.service_query` duration execution in `truffles-api/app/routers/webhook/info.py`
- **External reuse:**
  - official Python `str.strip()` documentation
- **Why not reinvent the wheel:** the repo already has both the override transport and the duration/service-hint primitives; this block should compose them instead of creating another routing path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one new routing-neutral detector, one new snapshot branch, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden grounded duration turns.
- No override bleed across requests or unrelated message text.
- No widening into price+duration bundles, promotions, or booking-followup arbitration.
- Frozen delegate still owns downstream execution and service-clarify side effects.

## Scope
- Add a routing-neutral explicit duration detector outside frozen runtime that only fires when service grounding is already available.
- Add a bounded grounded-duration policy snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- price+duration mixed bundles
- promotions cutover
- booking-progress / interrupt ownership changes
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
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
2. Add a routing-neutral grounded-duration detector outside frozen runtime.
3. Add the bounded grounded-duration snapshot branch in `detect_policy_core_route_snapshot(...)`.
4. Add deterministic tests for detection, media gating, mixed-query exclusion, override consumption, and delegate priming.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded grounded-duration policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- the duration snapshot carries `tool_args.service_query`, `pack_refs=["duration"]`, and `capability="duration"`
- override state resets after delegate exit and does not apply to unrelated message text
- mixed price/duration, location/hours, and services-overview turns remain outside this bounded slice
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
- bounded grounded-duration policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral grounded-duration detector in `truffles-api/app/services/info_signal_service.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires mixed-info arbitration, booking-followup ownership changes, or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's core/service/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual duration policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream tool execution.
- No widening into promotions, mixed price+duration arbitration, or booking-followup arbitration in this block.

## Risks/Blockers
- A false-positive duration detector could steal hours/work-schedule turns that must stay outside this bounded slice.
- A duration detector that ignores price overlap could widen into mixed duration+price arbitration, which belongs to later blocks.
- If service grounding is weak, the override could push downstream execution into clarify responses more often than intended.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen `decision.py` still owns mixed info bundles, broader booking arbitration, and all non-bounded policy-core semantics.
- **Why not in this block:** this slice is limited to explicit service-grounded duration turns so it can move a single semantic seam without touching frozen routers.
- **Risk if deferred:** duration remains only partially ingress-owned until adjacent mixed-bundle and promotions seams are migrated.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-policy-override-evaluation-a922.md` (planned)
- **Expiry/trigger to stop deferral:** stop deferral once the next bounded fact/info seam no longer fits without mixed-bundle arbitration.

## Next-block contract (mandatory)
- **Next block objective:** evaluate whether explicit promotions can be migrated as the next bounded fact/info policy override without widening into copy-fitting or proof-only heuristics.
- **First deterministic check command:** `sed -n '3000,3160p' truffles-api/app/services/demo_salon_knowledge.py`
- **Blocked-by conditions:** duration block must land green first; promotions must prove a routing-neutral grounded detector outside frozen runtime.
- **Owner role for closure:** `Top Architect`
