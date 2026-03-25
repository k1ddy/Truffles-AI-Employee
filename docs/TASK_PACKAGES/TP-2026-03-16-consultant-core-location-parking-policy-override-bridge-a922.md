# TP-2026-03-16-consultant-core-location-parking-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-LOCATION-PARKING-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SERVICES-OVERVIEW-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-services-overview-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OUTCOME-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded richer semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для явных location/parking turns и scope it before delegate, чтобы frozen router потреблял precomputed `catalog.location` policy contract вместо первого policy-core LLM pass на этих turns, при этом downstream `catalog.location` execution and followup handling остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-services-overview-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,140p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '120,220p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '1209,1265p' truffles-api/app/services/tool_registry_service.py`
  - `sed -n '250,360p' truffles-api/app/core/intent_routing.py`
  - `sed -n '1588,1638p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit location/parking turns even though downstream `catalog.location` execution already exists and does not require tool args.
  - reusable routing-neutral signal primitives already exist in `truffles-api/app/services/info_signal_service.py`, and the existing info classifier in `truffles-api/app/routers/webhook/info.py` proves the same location/parking lexicon family is already productized outside the frozen files.
  - `PolicyCoreRouteSnapshot` currently hardcodes empty `pack_refs`, which blocks bounded richer semantic overrides that need to carry location/parking context through the existing request-scoped seam.
  - `reasoning_core` already scopes policy overrides generically before delegate execution, so the only new runtime work in this block should be a richer snapshot plus focused signal detection.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for manager-request, style-reference, booking-verification, and services-overview turns, but explicit location/parking semantics still begin with a frozen policy-core LLM call.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/dataclasses.html Python dataclasses default_factory documentation`
- **Date/time (local):** `2026-03-16 12:18 +05`
- **Why this query is precise:** this block likely needs richer immutable dataclass fields on `PolicyCoreRouteSnapshot`, and mutable default sharing is not acceptable in request-scoped semantic override payloads.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes — Python documentation` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dataclasses.field(default_factory=...)` is the standard way to define collection defaults without shared mutable state.
- **Decision:** `reuse + integrate` — extend `PolicyCoreRouteSnapshot` with `field(default_factory=...)` for richer optional collections instead of inventing a second snapshot type.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit location/parking routing directly
  - introducing a second override payload type just for richer info routes
  - bypassing the frozen delegate with a direct `reasoning_core` reply
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit location/parking turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/tool_registry_service.py` and verify that `catalog.location` already owns downstream execution.
  2. Open `truffles-api/app/services/info_signal_service.py` and `truffles-api/app/routers/webhook/info.py` and verify that reusable location/parking signal primitives already exist outside the frozen files.
  3. Open `truffles-api/app/core/intent_routing.py` and confirm that `PolicyCoreRouteSnapshot` cannot yet carry richer `pack_refs` for bounded info routes.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded `catalog.location` policy override before delegate execution for explicit location/parking turns
  - `route_llm_policy_core(...)` consumes the request-scoped override payload without provider init
  - the override carries bounded `pack_refs` for location/parking semantics
  - override state resets after delegate exit and does not leak to unrelated message text
  - downstream frozen `catalog.location` execution and followup handling remain unchanged
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because explicit location/parking turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because a deterministic dedicated tool path already exists, but it still depends on legacy semantic ownership before it can run.
  3. Why not cut over the full info path now? Because mixed info bundles and broader info arbitration are wider than a bounded single-tool contract.
  4. Why is a bounded override safe? Because `catalog.location` already owns downstream execution and the required lexicon family already exists outside the frozen files.
  5. Why does this reduce drift? Because ingress becomes first owner of another real fact contract while frozen code remains only the executor of that contract.
- **Root cause statement:** explicit location/parking semantics remain in frozen `decision.py` because ingress still lacks a richer `PolicyCoreRouteSnapshot` that can carry bounded location/parking context through the existing request-scoped override seam.
- **Fix mechanism:**
  - extend `PolicyCoreRouteSnapshot` for richer optional `pack_refs`
  - add a routing-neutral location/parking signal helper outside frozen runtime
  - prime the richer snapshot from `reasoning_core.py` before delegate execution

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` `ExitStack`-based priming path
  - existing location/parking signal primitives in `truffles-api/app/services/info_signal_service.py`
  - existing info classifier semantics in `truffles-api/app/routers/webhook/info.py`
  - existing downstream `catalog.location` execution in `truffles-api/app/services/tool_registry_service.py`
- **External reuse:**
  - official Python `dataclasses` documentation
- **Why not reinvent the wheel:** the repo already has both the request-scoped override transport and the location/parking lexicon family; this block should extend the existing snapshot contract rather than add another routing layer.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one small snapshot enrichment, one routing-neutral helper, and focused deterministic tests.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden location/parking policy turns.
- No override bleed across requests or unrelated message text.
- No change to downstream `catalog.location` execution or followup behavior; frozen delegate still owns execution.

## Scope
- Extend `PolicyCoreRouteSnapshot` with bounded richer optional collections.
- Add a routing-neutral explicit location/parking signal helper outside frozen runtime.
- Prime a bounded `catalog.location` policy snapshot from `reasoning_core.py` before delegate execution.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- mixed location+hours bundle cutover
- broader info arbitration cutover
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-location-parking-policy-override-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
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
2. Enrich `PolicyCoreRouteSnapshot` with bounded optional `pack_refs`.
3. Add a routing-neutral location/parking detector outside frozen runtime.
4. Prime the richer `catalog.location` override from `reasoning_core.py` before delegate execution.
5. Add deterministic tests for detection, override consumption, pack-ref transport, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded location/parking policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- the richer snapshot carries bounded `pack_refs` through the existing override seam
- override state resets after delegate exit and does not apply to unrelated message text
- downstream frozen `catalog.location` execution and followup handling remain unchanged
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
- richer bounded policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral signal helper in `truffles-api/app/services/info_signal_service.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into mixed info arbitration, stop and split
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
  - active block metadata must match the actual location/parking policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream `catalog.location` execution.
- No widening into mixed location/hours arbitration in this block.

## Risks/Blockers
- if detection is too broad, mixed info turns may be forced into `catalog.location` too early.
- if richer snapshot fields are mutable by default, override payload state may leak across requests.
- if pack refs do not match downstream expectations, frozen execution may take a generic repair path instead of the dedicated location tool path.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still owns downstream `catalog.location` execution and broader mixed info arbitration.
- non-location/parking policy outcomes still begin in frozen runtime.

### Why not in this block
- widening beyond explicit location/parking turns would turn this into a mixed-info cutover.

### Risk if deferred
- explicit location/parking turns still pay for frozen policy-core ownership unless this slice lands.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-richer-semantic-outcome-bridge-a922.md` (to be created after this block)

### Expiry/trigger to stop deferral
- stop deferral when the next bounded richer semantic outcome can be proven safe without frozen-router edits.

## Next-block contract (mandatory)
### Next block objective
- move the next bounded richer semantic outcome seam after location/parking policy override, using the same ingress override model.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k location`

### Blocked-by conditions
- the location/parking snapshot must stay bounded to explicit `catalog.location` turns in this block.
- no frozen-router edits allowed.
- downstream `catalog.location` execution and followup handling must remain unchanged.

### Owner role for closure
- `Top Architect`
