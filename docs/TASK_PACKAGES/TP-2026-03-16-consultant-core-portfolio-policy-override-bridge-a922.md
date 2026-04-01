# TP-2026-03-16-consultant-core-portfolio-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PORTFOLIO-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-MASTER-QUERY-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-NEXT-FACT-SEAM-EVALUATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded fact/info semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit portfolio/examples-of-work turns, чтобы frozen router потреблял precomputed `portfolio` / `catalog.portfolio` contract вместо первого policy-core LLM pass на этих turns, при этом style-reference handoff, mixed pricing/duration turns, guest/location/hours/promotions neighbors, and booking specialist-selection semantics остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
- `truffles-api/app/routers/webhook/media.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_cross_domain_signal_contract_suite.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_cross_domain_signal_contract_suite.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '318,520p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '300,520p' truffles-api/app/core/intent_routing.py`
  - `sed -n '1220,1275p' truffles-api/app/services/tool_registry_service.py`
  - `rg -n "portfolio|catalog.portfolio|style_reference" truffles-api/tests/test_intent.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_cross_domain_signal_contract_suite.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - downstream execution already has a direct `catalog.portfolio` tool path in `tool_registry_service._catalog_portfolio(...)`.
  - the policy schema already accepts bounded fact contracts for `intent="portfolio"`, `action="fact"`, `tool_action="catalog.portfolio"`, `capability="portfolio"`, and optional `tool_args.service_query`.
  - clinic and dental packs already expose `portfolio_question_keywords`, but demo/runtime fallback lexicons do not, so ingress still lacks a pack-neutral bounded detector for explicit portfolio turns.
  - style-reference text requests still have an earlier bounded handoff branch in `detect_policy_core_route_snapshot(...)`, so this block must stay narrow: explicit examples-of-work / portfolio asks only, no style-reference handoff capture, no mixed pricing/duration turns.
- `Detected drift (docs vs code)`: ingress already owns neighboring fact/info seams, but explicit portfolio/example-of-work questions still begin with the first policy-core LLM call inside frozen `decision.py` even though the direct tool path and schema-valid contract already exist.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/functions.html Python any documentation`
- **Date/time (local):** `2026-03-16 14:14 +05`
- **Why this query is precise:** this block needs a tight short-circuit exclusion gate over neighboring info seams while keeping the detector as a thin composition layer instead of another custom branching forest.
- **Sources opened (from this query):**
  - `Built-in Functions — Python documentation` — `https://docs.python.org/3.10/library/functions.html#any`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python built-in `any(iterable)` matches the existing short-circuit helper style already used in routing-neutral signal helpers and is sufficient for bounded portfolio keyword/exclusion composition.
- **Decision:** `reuse + integrate` — reuse existing short-circuit helper style, existing signal lexicon loaders, and the existing request-scoped policy override seam; add only one bounded portfolio detector and snapshot branch.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit portfolio routing directly
  - widening the block into style-reference handoff or booking/media handling
  - hardcoding demo-only portfolio branches instead of using reusable lexicon-backed signals
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit portfolio/example-of-work questions still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/tool_registry_service.py` and confirm `_catalog_portfolio(...)` already serves bounded `catalog.portfolio` replies.
  2. Open `truffles-api/app/schemas/intent.py` and confirm `intent="portfolio"` + `tool_action="catalog.portfolio"` validates.
  3. Open `truffles-api/app/core/intent_routing.py` and confirm there is no bounded portfolio snapshot branch yet.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded `portfolio` policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - explicit portfolio/example-of-work turns route to `intent="portfolio"`, `action="fact"`, `tool_action="catalog.portfolio"`, `capability="portfolio"`
  - optional grounded service mention is preserved via `tool_args.service_query`
  - style-reference text turns do not get hijacked by the portfolio slice
  - mixed pricing/duration turns do not trigger this override
  - override state resets after delegate exit and does not leak to unrelated text
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because explicit portfolio/example-of-work turns still start with the first policy-core LLM pass inside frozen runtime.
  2. Why does that matter? Because the repo already has both a direct `catalog.portfolio` tool path and a schema-valid policy contract for `portfolio`.
  3. Why has ingress not taken this slice yet? Because there is no bounded routing-neutral detector/snapshot branch for portfolio turns.
  4. Why not just widen into all style-reference/photo semantics? Because style-reference handoff and media flows carry separate runtime semantics and would widen the block beyond a safe bounded cut.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit fact contract while legacy runtime keeps only downstream orchestration.
- **Root cause statement:** explicit portfolio/example-of-work semantics remain in frozen `decision.py` because ingress still lacks a bounded detector that maps those turns to the existing `catalog.portfolio` contract while excluding style-reference and neighboring info seams.
- **Fix mechanism:**
  - add a routing-neutral bounded portfolio detector outside frozen runtime
  - add a bounded `portfolio` snapshot branch in `detect_policy_core_route_snapshot(...)`
  - backfill reusable lexicon fallback data in `SYSTEM_LEXICONS.yaml`
  - verify override consumption, delegate priming, and exclusion behavior through deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` delegate priming path
  - existing `tool_registry_service._catalog_portfolio(...)`
  - existing signal lexicon loading helpers in `info_signal_service.py`
  - existing style-reference ingress branch in `detect_policy_core_route_snapshot(...)`
  - existing service hint extraction via `get_pack_service_hint(...)`
- **External reuse:**
  - official Python `any(...)` documentation
- **Why not reinvent the wheel:** the repo already has the direct portfolio tool path, contract schema, signal loaders, and request-scoped override transport; this block only needs a narrow ingress contract on top.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one routing-neutral detector, one snapshot branch, one lexicon fallback addition, focused tests, and mandatory canon/session sync.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden `portfolio` turns.
- No override bleed across requests or unrelated message text.
- No widening into style-reference/media handoff, pricing/duration mixed turns, or booking specialist-selection semantics.
- Frozen delegate still owns downstream truth execution and side effects.

## Scope
- Add a routing-neutral bounded portfolio detector outside frozen runtime.
- Add a bounded `portfolio` policy snapshot branch in `detect_policy_core_route_snapshot(...)`.
- Add reusable fallback lexicon data for explicit portfolio/example-of-work phrasing.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py`, `truffles-api/tests/test_intent.py`, and `truffles-api/tests/test_cross_domain_signal_contract_suite.py`.
- Sync required canon/session artifacts.

## Out of scope
- style-reference handoff/media routing
- booking or specialist availability semantics
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-portfolio-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_cross_domain_signal_contract_suite.py`
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
2. Add a routing-neutral bounded portfolio detector with data-backed lexicon fallback and service-query preservation.
3. Add the bounded `portfolio` snapshot branch in `detect_policy_core_route_snapshot(...)`.
4. Add deterministic tests for detection, media gating, style-reference precedence, mixed-query exclusion, cross-pack signal coverage, override consumption, and delegate priming.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded `portfolio` policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without provider init
- explicit portfolio/example-of-work turns route to `intent="portfolio"`, `action="fact"`, `tool_action="catalog.portfolio"`, `capability="portfolio"`
- grounded service mention is preserved in `tool_args.service_query` when present
- style-reference text turns and mixed pricing/duration turns remain outside this slice
- override state resets after delegate exit and does not apply to unrelated message text
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_intent.py`
- `pytest -q truffles-api/tests/test_cross_domain_signal_contract_suite.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- bounded portfolio policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral portfolio detector in `truffles-api/app/services/info_signal_service.py`
- fallback lexicon data in `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
- focused runtime/signal tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the slice requires frozen-router edits, style-reference/media ownership, or booking specialist-selection semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** request-scoped bounded policy-core override bridge only
- **Go/no-go signals:** reasoning-core + intent + cross-domain suite + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's signal/test/doc changes only; keep previous ingress bridges intact
- **Post-release monitoring window:** next block should continue richer semantic cutover, not return to micro-slices

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual portfolio policy override bridge being executed.

## Rollback
- Revert this TP's service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- direct edits in frozen `decision.py`, `booking.py`, or `pending.py`
- widening this block into style-reference/media routing
- widening this block into booking specialist selection or availability routing
- adding new proof/eval or continuity work in the same block

## Risks / blockers
- explicit portfolio phrasing can sit close to style-reference/photo language; the detector must stay narrow enough to avoid hijacking style-reference handoff turns.
- demo-salon lacks pack-local portfolio keywords today, so the fallback must stay system-level and reusable rather than demo-hardcoded.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader style-reference/media semantics still live outside this slice.
- richer portfolio filtering/rendering remains downstream and legacy-owned.

### Why not in this block
- this block is only for the explicit portfolio/examples-of-work fact seam that already has a direct tool path and a schema-valid contract.

### Risk if deferred
- frozen runtime remains first semantic owner for another explicit fact seam and keeps paying the first policy-core LLM pass for turns that already have a direct tool contract.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- next bounded fact seam TP after portfolio bridge

### Expiry/trigger to stop deferral
- stop deferral once the next adjacent fact seam is selected or if explicit portfolio turns still show drift in deterministic replay evidence.

## Next-block contract (mandatory)
### Next block objective
- select the next bounded fact/info semantic seam after explicit portfolio/example-of-work questions without returning to proof/continuity micro-slices.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k portfolio_policy_override`

### Blocked-by conditions
- this block widens into style-reference/media ownership
- this block requires frozen-router edits
- deterministic portfolio exclusions are not provable with focused tests

### Owner role for closure
- `Top Architect`
