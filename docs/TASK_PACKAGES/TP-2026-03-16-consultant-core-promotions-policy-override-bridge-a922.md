# TP-2026-03-16-consultant-core-promotions-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROMOTIONS-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DURATION-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROMOTIONS-RULES-POLICY-OVERRIDE-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded fact/info semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit generic promotions turns, чтобы frozen router потреблял precomputed `promotions`/`info` contract вместо первого policy-core LLM pass на этих turns, при этом stacking-rules, mixed info bundles, and downstream truth execution остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-policy-override-bridge-a922.md`
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
  - `sed -n '150,280p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '320,440p' truffles-api/app/core/intent_routing.py`
  - `sed -n '571,585p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '3606,3625p' truffles-api/app/services/demo_salon_knowledge.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit generic promotions turns even though downstream info execution already handles `intent="promotions"` through the `info` tool path.
  - the request-scoped policy override seam already transports `pack_refs`, `slots`, and `capability`, so this block only needs a routing-neutral promotions detector plus a bounded promotions snapshot branch.
- reusable routing-neutral primitives already exist outside frozen files via `pack_runtime_default._detect_promotion_intent(...)`, `app.routers.webhook.policy._looks_like_promotions_request(...)`, `looks_like_services_overview_message(...)`, `detect_location_policy_pack_refs(...)`, `looks_like_hours_policy_message(...)`, `_has_price_signal(...)`, and `_has_duration_signal(...)`.
  - promotions stacking/rules are a separate semantic branch with different downstream truth intent (`promotions_rules`), so generic promotions cutover must exclude those turns to stay bounded.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for manager-request, style-reference, booking-verification, services-overview, location/parking, hours, grounded pricing, and grounded duration turns, but explicit promotions semantics still begin with a frozen policy-core LLM call.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python all documentation`
- **Date/time (local):** `2026-03-16 13:05 +05`
- **Why this query is precise:** this block needs a small routing-neutral helper that excludes stacking-rule turns by requiring all configured stacking terms to be present in normalized text, so it must reuse Python’s built-in `all(...)` semantics instead of inventing a custom loop contract.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3/library/functions.html#all`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `all(iterable)` returns `True` only when every element is truthy, which fits a bounded lexicon-based `signal_all_match(...)` helper for explicit stacking-rule exclusion.
- **Decision:** `reuse + integrate` — add a tiny `signal_all_match(...)` helper in `info_signal_service.py` and reuse existing lexicon lists instead of building another promotions-specific matcher forest.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit promotions routing directly
  - depending on proof-only or booking-only promotion helpers
  - widening this block into stacking-rules or service-grounded promotions
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit generic promotions turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/info.py` and verify that downstream info execution already handles `intent="promotions"` via the `info` tool path.
  2. Open `truffles-api/app/core/intent_routing.py` and confirm that bounded policy snapshot branches cover hours, grounded pricing, and grounded duration, but not promotions.
  3. Open `truffles-api/app/services/demo_salon_knowledge.py` and confirm that generic promotions and stacking rules currently split into different truth intents.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded generic-promotions policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - the promotions snapshot carries `pack_refs=["promotions"]` and `capability="promotions"`
  - override state resets after delegate exit and does not leak to unrelated message text
  - stacking-rules, hours/location, and price/duration mixed turns remain outside this bounded slice
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because explicit promotions turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because downstream truth execution already exists, but it still depends on frozen semantic ownership before it can run.
  3. Why has ingress not taken this slice yet? Because there is no routing-neutral promotions detector in the ingress bridge.
  4. Why is a bounded cut now safe? Because generic promotions already resolve through a stable `info` path, and stacking rules can be excluded as a separate branch.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit fact contract while frozen code remains only the executor of that contract.
- **Root cause statement:** explicit generic promotions semantics remain in frozen `decision.py` because ingress still lacks a bounded routing-neutral promotions detector plus a matching `PolicyCoreRouteSnapshot` branch that excludes stacking-rule and mixed-info turns.
- **Fix mechanism:**
  - add a small routing-neutral promotions detector outside frozen runtime with stacking-rule exclusion
  - add a bounded promotions snapshot branch in `detect_policy_core_route_snapshot(...)`
  - verify delegate priming and override consumption through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing `pack_runtime_default._detect_promotion_intent(...)`
  - existing `app.routers.webhook.policy._looks_like_promotions_request(...)`
  - existing `looks_like_services_overview_message(...)`, `detect_location_policy_pack_refs(...)`, `looks_like_hours_policy_message(...)`, `_has_price_signal(...)`, `_has_duration_signal(...)`
  - existing downstream `info` promotions execution in `truffles-api/app/routers/webhook/info.py`
- **External reuse:**
  - official Python `all(...)` documentation
- **Why not reinvent the wheel:** the repo already has both the override transport and the promotions lexicon primitives; this block should compose them instead of adding another routing path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one small routing-neutral detector, one new snapshot branch, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden generic promotions turns.
- No override bleed across requests or unrelated message text.
- No widening into stacking-rules, service-grounded promotions, or price/duration bundles.
- Frozen delegate still owns downstream truth execution and side effects.

## Scope
- Add a routing-neutral explicit promotions detector outside frozen runtime that only fires for generic promotions turns.
- Add a bounded generic promotions policy snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- promotions stacking-rules cutover
- service-grounded promotions cutover
- price/duration mixed bundles
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-policy-override-bridge-a922.md`
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
2. Add a routing-neutral generic promotions detector outside frozen runtime with stacking-rule and mixed-info exclusions.
3. Add the bounded generic promotions snapshot branch in `detect_policy_core_route_snapshot(...)`.
4. Add deterministic tests for detection, media gating, stacking-rule exclusion, mixed-query exclusion, override consumption, and delegate priming.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded generic-promotions policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- the promotions snapshot carries `pack_refs=["promotions"]` and `capability="promotions"`
- override state resets after delegate exit and does not apply to unrelated message text
- stacking-rules, hours/location, and price/duration mixed turns remain outside this bounded slice
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
- bounded generic promotions policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral promotions detector in `truffles-api/app/services/info_signal_service.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires stacking-rules, service-grounded promotions, mixed-info arbitration, or frozen-router edits, stop and split
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
  - active block metadata must match the actual promotions policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream truth execution.
- No widening into stacking-rules, service-grounded promotions, or mixed price/duration arbitration in this block.

## Risks/Blockers
- A generic promotions detector could wrongly steal stacking-rules turns that should remain a separate `promotions_rules` slice.
- A detector that ignores price/duration overlap could widen into mixed info arbitration.
- A detector that overfits beauty-only discount markers would violate the pack-agnostic cutover goal.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen `decision.py` still owns stacking-rules, service-grounded promotions, mixed info bundles, broader booking arbitration, and all non-bounded policy-core semantics.
- **Why not in this block:** this slice is limited to explicit generic promotions turns so it can move a single semantic seam without touching frozen routers.
- **Risk if deferred:** promotions remains only partially ingress-owned until adjacent stacking-rules and service-grounded promotions seams are migrated.
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-rules-policy-override-evaluation-a922.md` (planned)
- **Expiry/trigger to stop deferral:** stop deferral once the next bounded fact/info seam no longer fits without stacking-rule or mixed-bundle arbitration.

## Next-block contract (mandatory)
- **Next block objective:** evaluate whether promotions stacking-rules can be migrated as the next bounded fact/info override without widening into generic promotions or proof-only heuristics.
- **First deterministic check command:** `sed -n '3606,3620p' truffles-api/app/services/demo_salon_knowledge.py`
- **Blocked-by conditions:** promotions block must land green first; rules cutover must prove a routing-neutral detector outside frozen runtime.
- **Owner role for closure:** `Top Architect`
