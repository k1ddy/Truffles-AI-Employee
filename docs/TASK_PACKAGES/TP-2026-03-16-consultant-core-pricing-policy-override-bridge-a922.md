# TP-2026-03-16-consultant-core-pricing-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PRICING-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-HOURS-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-hours-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DURATION-POLICY-OVERRIDE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded richer semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для explicit service-grounded pricing turns, чтобы frozen router потреблял precomputed `catalog.service_query` pricing contract вместо первого policy-core LLM pass на этих turns, при этом mixed-info arbitration, booking-flow ownership, and downstream tool execution остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-hours-policy-override-bridge-a922.md`
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
  - `truffles-api/app/services/pack_runtime_default.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '100,170p' truffles-api/app/services/pack_runtime_default.py`
  - `sed -n '473,530p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '260,390p' truffles-api/app/core/intent_routing.py`
  - `sed -n '2500,2585p' truffles-api/app/services/intent_service.py`
  - `sed -n '1595,1635p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit service-grounded pricing turns even though downstream tool execution already accepts `catalog.service_query` with `pack_refs=["pricing"]` and `capability="pricing"`.
  - the request-scoped policy override seam already transports `tool_args`, `pack_refs`, and `capability`, but `PolicyCoreRouteSnapshot` still hardcodes empty `tool_args`, so ingress cannot yet express a grounded service query contract.
  - reusable routing-neutral pricing primitives already exist outside the frozen files via `_has_price_signal(...)`, `_has_duration_signal(...)`, and `get_pack_service_hint(...)`.
  - `reasoning_core` already scopes policy overrides generically before delegate execution, so this block only needs a bounded service-grounded pricing detector plus a richer snapshot contract.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for manager-request, style-reference, booking-verification, services-overview, location/parking, and hours turns, but explicit grounded pricing semantics still begin with a frozen policy-core LLM call.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/dataclasses.html Python dataclasses field default_factory mutable default documentation`
- **Date/time (local):** `2026-03-16 12:39 +05`
- **Why this query is precise:** this block extends the existing snapshot dataclass with grounded `tool_args`, so the contract must add a mutable payload field without shared defaults across request-scoped overrides.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes — Python documentation` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** dataclass mutable fields should use `field(default_factory=...)`; appending another defaulted field to an existing dataclass keeps field-order validity while isolating per-instance dictionary payloads.
- **Decision:** `reuse + integrate` — extend the existing `PolicyCoreRouteSnapshot` with bounded `tool_args` instead of introducing a second pricing-specific snapshot type.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit explicit pricing routing directly
  - overloading `slots` to smuggle `service_query` into downstream tool execution
  - bypassing frozen delegate execution with a direct `reasoning_core` reply
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit service-grounded pricing turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/info.py` and verify that downstream info execution already handles pricing via `catalog.service_query` or service-hint fallback.
  2. Open `truffles-api/app/services/intent_service.py` and verify that the request-scoped policy override seam already validates and transports `tool_args`.
  3. Open `truffles-api/app/core/intent_routing.py` and confirm that `PolicyCoreRouteSnapshot` still cannot carry grounded `tool_args.service_query`.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded grounded-pricing policy override before delegate execution
  - `route_llm_policy_core(...)` consumes that request-scoped override without provider init
  - the richer snapshot carries `tool_args.service_query`, `pack_refs=["pricing"]`, and `capability="pricing"`
  - override state resets after delegate exit and does not leak to unrelated message text
  - mixed duration/location/hours/promotions turns remain outside this bounded slice
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because explicit service-grounded pricing turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because downstream service-query execution already exists, but it still depends on frozen semantic ownership before it can run.
  3. Why has ingress not taken this slice yet? Because the current snapshot contract cannot carry grounded `tool_args.service_query`.
  4. Why is a bounded cut now safe? Because reusable pricing primitives and service-hint grounding already exist outside the frozen files.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit fact contract while frozen code remains only the executor of that contract.
- **Root cause statement:** explicit grounded pricing semantics remain in frozen `decision.py` because ingress still lacks a bounded pricing detector plus a `PolicyCoreRouteSnapshot` that can carry grounded `tool_args.service_query` through the existing request-scoped override seam.
- **Fix mechanism:**
  - extend `PolicyCoreRouteSnapshot` with bounded `tool_args`
  - add a routing-neutral service-grounded pricing detector outside frozen runtime
  - prime the richer pricing snapshot from `reasoning_core.py` before delegate execution

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` `ExitStack`-based priming path
  - existing `_has_price_signal(...)`, `_has_duration_signal(...)`, and `get_pack_service_hint(...)` helpers in `pack_runtime_default`
  - existing downstream `catalog.service_query` pricing execution in `truffles-api/app/routers/webhook/info.py`
- **External reuse:**
  - official Python `dataclasses` documentation
- **Why not reinvent the wheel:** the repo already has both the request-scoped override transport and the deterministic pricing/service-hint primitives; this block should extend the existing snapshot contract instead of adding another routing path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one small snapshot enrichment, one grounded detector, and focused deterministic tests.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden grounded pricing turns.
- No override bleed across requests or unrelated message text.
- No widening into duration, promotions, hours/location bundles, or booking-followup arbitration.
- Frozen delegate still owns downstream execution and booking-side effects.

## Scope
- Extend `PolicyCoreRouteSnapshot` with bounded `tool_args`.
- Add a routing-neutral explicit pricing detector outside frozen runtime that only fires when service grounding is already available.
- Prime a bounded grounded-pricing policy snapshot from `reasoning_core.py` before delegate execution.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- duration cutover
- mixed price+duration bundles
- booking-progress / interrupt ownership changes
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-policy-override-bridge-a922.md`
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
2. Extend `PolicyCoreRouteSnapshot` with bounded `tool_args`.
3. Add a routing-neutral service-grounded pricing detector outside frozen runtime.
4. Prime the richer pricing policy snapshot from the existing ingress seam.
5. Add deterministic tests for detection, tool-arg transport, media gating, override consumption, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded grounded-pricing policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- the richer snapshot carries `tool_args.service_query`, `pack_refs=["pricing"]`, and `capability="pricing"`
- override state resets after delegate exit and does not apply to unrelated message text
- mixed duration/location/hours/promotions turns remain outside this bounded slice
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
- richer bounded grounded-pricing policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral grounded-pricing detector in `truffles-api/app/services/info_signal_service.py`
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
  - active block metadata must match the actual pricing policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream tool execution.
- No widening into duration, promotions, or booking-followup arbitration in this block.

## Risks/Blockers
- if detection is too broad, mixed duration/location/hours turns may be forced into the pricing path too early.
- if service grounding is too weak, ingress may precompute a wrong `service_query` and create drift relative to the current LLM payload.
- if `tool_args` isolation is incorrect, stale grounded service queries may leak between requests.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still owns downstream pricing execution and broader mixed-info arbitration.
- explicit duration and promotions semantics still begin in frozen runtime.

### Why not in this block
- widening beyond explicit grounded pricing turns would turn this into a mixed-info or booking-followup cutover.

### Risk if deferred
- explicit grounded pricing turns still pay for frozen policy-core ownership unless this slice lands.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-policy-override-bridge-a922.md` (to be created after this block)

### Expiry/trigger to stop deferral
- stop deferral when the next bounded service-grounded info seam can be proven safe without frozen-router edits.

## Next-block contract (mandatory)
### Next block objective
- move the next bounded service-grounded info seam after pricing, most likely duration, using the richer snapshot contract with `tool_args`.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k pricing_policy_override`

### Blocked-by conditions
- the pricing snapshot must stay bounded to explicit service-grounded pricing turns in this block.
- no frozen-router edits allowed.
- mixed duration/location/hours/promotions turns must remain outside this slice.

### Owner role for closure
- `Top Architect`
