# TP-2026-03-16-consultant-core-hours-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-HOURS-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-LOCATION-PARKING-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-location-parking-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OUTCOME-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded richer semantic seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для явных hours turns и scope it before delegate, чтобы frozen router потреблял precomputed `info`/`hours` policy contract вместо первого policy-core LLM pass на этих turns, при этом downstream info execution and followup handling остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-location-parking-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/routers/webhook/info.py`
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
  - `sed -n '1,180p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '120,220p' truffles-api/app/routers/webhook/info.py`
  - `sed -n '5960,6035p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '250,380p' truffles-api/app/core/intent_routing.py`
  - `sed -n '1590,1640p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit hours turns even though downstream info execution already accepts `hours` via `pack_refs` and capability-derived refs.
  - reusable routing-neutral hour lexicon primitives already exist outside the frozen files in `truffles-api/app/services/info_signal_service.py` and `truffles-api/app/routers/webhook/info.py`.
  - `PolicyCoreRouteSnapshot` already carries bounded `pack_refs`, but it does not yet transport bounded `capability`, which frozen downstream logic uses for info-ref and capability-contract derivation.
  - `reasoning_core` already scopes policy overrides generically before delegate execution, so this block only needs a bounded detector plus a slightly richer snapshot contract.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for manager-request, style-reference, booking-verification, services-overview, and location/parking turns, but explicit hours semantics still begin with a frozen policy-core LLM call.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/dataclasses.html Python dataclasses field order defaults documentation`
- **Date/time (local):** `2026-03-16 12:24 +05`
- **Why this query is precise:** this block extends the existing snapshot dataclass again, and field ordering/default behavior must stay correct when adding another optional scalar beside existing defaulted fields.
- **Sources opened (from this query):**
  - `dataclasses — Data Classes — Python documentation` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** dataclass fields are processed in definition order, and defaulted fields remain valid when additional defaulted fields are appended; `field(default_factory=...)` remains the right way to keep collection defaults isolated.
- **Decision:** `reuse + integrate` — extend the existing `PolicyCoreRouteSnapshot` dataclass with another optional defaulted field instead of creating a second snapshot type.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit hours routing directly
  - adding a new override payload type just for info-capability turns
  - bypassing frozen delegate execution with a direct `reasoning_core` reply
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit hours turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/routers/webhook/info.py` and verify that reusable hours lexicon logic already exists outside the frozen files.
  2. Open `truffles-api/app/routers/webhook/decision.py` and verify that downstream info-ref derivation already accepts `policy_capability="hours"` and `pack_refs=["hours"]`.
  3. Open `truffles-api/app/core/intent_routing.py` and confirm that `PolicyCoreRouteSnapshot` does not yet transport bounded capability metadata for an hours override.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded hours policy override before delegate execution
  - `route_llm_policy_core(...)` consumes the request-scoped override without provider init
  - the richer snapshot carries `capability="hours"` and bounded `pack_refs`
  - override state resets after delegate exit and does not leak to unrelated message text
  - downstream frozen info execution and followup handling remain unchanged
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because explicit hours turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because downstream info execution already exists, but it still depends on legacy semantic ownership before it can run.
  3. Why not cut over mixed hours/location bundles now? Because mixed info arbitration is broader than a bounded single-capability cut.
  4. Why is a bounded override safe? Because reusable hours lexicon logic already exists outside the frozen files and downstream info execution already handles `hours` refs.
  5. Why does this reduce drift? Because ingress becomes first owner of another explicit info capability contract while frozen code remains only the executor of that contract.
- **Root cause statement:** explicit hours semantics remain in frozen `decision.py` because ingress still lacks a bounded hours detector plus a `PolicyCoreRouteSnapshot` that can carry the `hours` capability through the existing request-scoped override seam.
- **Fix mechanism:**
  - add a bounded routing-neutral hours detector outside frozen runtime
  - extend `PolicyCoreRouteSnapshot` with optional `capability`
  - prime the richer hours snapshot from `reasoning_core.py` before delegate execution

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam
  - existing `reasoning_core` `ExitStack`-based priming path
  - existing hours lexicon logic in `truffles-api/app/services/info_signal_service.py` and `truffles-api/app/routers/webhook/info.py`
  - existing downstream info-ref derivation in `truffles-api/app/routers/webhook/decision.py`
- **External reuse:**
  - official Python `dataclasses` documentation
- **Why not reinvent the wheel:** the repo already has both the request-scoped override transport and the reusable hours lexicon family; this block should extend the existing snapshot contract instead of adding another routing path.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with one small snapshot enrichment, one routing-neutral detector, and focused deterministic tests.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden hours policy turns.
- No override bleed across requests or unrelated message text.
- No change to downstream info execution or followup behavior; frozen delegate still owns execution.

## Scope
- Extend `PolicyCoreRouteSnapshot` with bounded optional `capability`.
- Add a routing-neutral explicit hours detector outside frozen runtime.
- Prime a bounded hours policy snapshot from `reasoning_core.py` before delegate execution.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- mixed location/hours bundle cutover
- booking-time followup cutover
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-hours-policy-override-bridge-a922.md`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
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
2. Extend `PolicyCoreRouteSnapshot` with bounded optional `capability`.
3. Add a routing-neutral explicit hours detector outside frozen runtime.
4. Prime the richer hours policy snapshot from `reasoning_core.py` before delegate execution.
5. Add deterministic tests for detection, capability transport, media gating, override consumption, and delegate priming.
6. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded hours policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- the richer snapshot carries `capability="hours"` and bounded `pack_refs`
- override state resets after delegate exit and does not apply to unrelated message text
- downstream frozen info execution and followup handling remain unchanged
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
- richer bounded hours policy snapshot in `truffles-api/app/core/intent_routing.py`
- routing-neutral hours detector in `truffles-api/app/services/info_signal_service.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into mixed-info arbitration, stop and split
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
  - active block metadata must match the actual hours policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream info execution.
- No widening into mixed location/hours or booking-time arbitration in this block.

## Risks/Blockers
- if detection is too broad, mixed service-duration or mixed location/hours turns may be forced into the hours path too early.
- if capability transport is omitted or malformed, frozen downstream logic may derive weaker info refs than the current LLM payload contract expects.
- if override state is not normalized-text scoped, unrelated later requests may consume stale state.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still owns downstream info execution and broader mixed-info arbitration.
- non-hours policy outcomes still begin in frozen runtime.

### Why not in this block
- widening beyond explicit hours turns would turn this into a mixed-info or booking-followup cutover.

### Risk if deferred
- explicit hours turns still pay for frozen policy-core ownership unless this slice lands.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-richer-semantic-outcome-bridge-a922.md` (to be created after this block)

### Expiry/trigger to stop deferral
- stop deferral when the next bounded richer semantic outcome can be proven safe without frozen-router edits.

## Next-block contract (mandatory)
### Next block objective
- move the next bounded richer semantic outcome seam after the hours policy override, using the same ingress override model.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k hours_policy_override`

### Blocked-by conditions
- the hours snapshot must stay bounded to explicit hours turns in this block.
- no frozen-router edits allowed.
- downstream info execution and followup handling must remain unchanged.

### Owner role for closure
- `Top Architect`
