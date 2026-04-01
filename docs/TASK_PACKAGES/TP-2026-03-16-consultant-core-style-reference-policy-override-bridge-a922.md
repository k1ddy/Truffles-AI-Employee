# TP-2026-03-16-consultant-core-style-reference-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-STYLE-REFERENCE-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-POLICY-HANDOFF-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-policy-handoff-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OUTCOME-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded semantic outcome seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для text-only style-reference turns и scope it before delegate, чтобы frozen router потреблял precomputed policy handoff contract вместо первого policy-core LLM pass на этих turn-ах, при этом downstream style-reference media prompt и pending-state execution остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-policy-handoff-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/routers/webhook/media.py`
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
  - `sed -n '336,360p' truffles-api/app/routers/webhook/media.py`
  - `sed -n '2475,2865p' truffles-api/app/services/intent_service.py`
  - `sed -n '17610,17640p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '21890,21950p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '1,260p' truffles-api/app/core/intent_routing.py`
  - `sed -n '1460,1635p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for text-only style-reference turns even though downstream execution after that call already has a dedicated style-reference branch.
  - text-only style-reference detection already exists as `_is_style_reference_request(...)` in `truffles-api/app/routers/webhook/media.py` and downstream style-reference behavior already keys off that same signal plus policy intent/reason.
  - `route_llm_policy_core(...)` already has a request-scoped override seam after the previous block, so this slice can reuse that bridge without widening into new channels.
  - downstream style-reference execution in frozen runtime already sets pending media state and booking-aware prompt text; this block does not need to reimplement any of that behavior.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core handoff overrides for explicit manager requests, but style-reference handoff semantics still begin inside frozen `decision.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/contextlib.html Python ExitStack documentation`
- **Date/time (local):** `2026-03-16 12:38 +05`
- **Why this query is precise:** this block extends the existing stacked ingress override contexts and must keep request-scoped context entry/exit ordering deterministic.
- **Sources opened (from this query):**
  - `contextlib — Utilities for with-statement contexts — Python documentation` — `https://docs.python.org/3/library/contextlib.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ExitStack` is the standard way to compose a variable number of context managers and guarantees LIFO unwinding for the entered contexts.
- **Decision:** `reuse + integrate` — extend the existing `ExitStack`-based ingress override stack in `reasoning_core.py` with one more bounded policy snapshot context.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit style-reference policy handling directly
  - bypassing delegate execution with a direct response from `reasoning_core`
  - introducing a second non-ContextVar override transport
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for text-only style-reference turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `_is_style_reference_request(...)` in `truffles-api/app/routers/webhook/media.py`.
  2. Open the style-reference handoff branch in `truffles-api/app/routers/webhook/decision.py` and observe that downstream behavior is already deterministic once a valid `handoff` policy payload exists.
  3. Open `route_llm_policy_core(...)` in `truffles-api/app/services/intent_service.py` and observe that, without an override, frozen code still owns the first policy-core call for these turns.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded policy-core override before delegate execution for text-only style-reference turns
  - `route_llm_policy_core(...)` consumes request-scoped override payloads for the same inbound without requiring LLM/provider init
  - override state resets after delegate exit and does not leak to unrelated message text
  - downstream frozen style-reference pending/media prompt behavior remains unchanged
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because text-only style-reference turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because a deterministic, already productized branch still depends on legacy semantic ownership before it can run.
  3. Why not cut over the full style-reference feature now? Because pending/media execution and response wiring already exist downstream and widening past the first policy contract would break bounded scope.
  4. Why is a bounded override safe? Because the detector already exists and downstream style-reference execution remains untouched.
  5. Why does this reduce drift? Because ingress becomes first owner of another real semantic outcome contract while frozen code becomes only the executor of that contract.
- **Root cause statement:** text-only style-reference semantics remain in frozen `decision.py` because `reasoning_core` does not yet prime any request-scoped `route_llm_policy_core(...)` override for that turn family, even though the detector and downstream execution path already exist.
- **Fix mechanism:**
  - extend bounded policy snapshot detection in `app/core/intent_routing.py`
  - reuse the existing policy-core override seam in `intent_service.py`
  - prime the snapshot from `reasoning_core.py` before delegate execution

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam from the previous block
  - existing `_is_style_reference_request(...)` detector in `truffles-api/app/routers/webhook/media.py`
  - existing downstream style-reference pending/media prompt branch in frozen runtime
  - existing `ExitStack`-based ingress override composition in `reasoning_core.py`
- **External reuse:**
  - official Python `contextlib` documentation
- **Why not reinvent the wheel:** the repo already has both the style-reference detector and the request-scoped policy override path; this block should compose them instead of creating another routing mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with focused deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden text-only style-reference policy turns.
- No override bleed across requests or unrelated message text.
- No change to downstream style-reference prompt/pending-state behavior; frozen delegate still owns execution.

## Scope
- Extend bounded policy-core snapshot detection in `truffles-api/app/core/intent_routing.py` for text-only style-reference turns.
- Prime the existing request-scoped policy-core override from `truffles-api/app/services/reasoning_core.py`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- media-attached style-reference turns
- full style-reference feature cutover
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-style-reference-policy-override-bridge-a922.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/core/__init__.py`
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
2. Extend bounded policy-core snapshot detection for text-only style-reference turns.
3. Prime the existing policy-core override from `reasoning_core.py` before delegate execution.
4. Add deterministic tests for detection, no-media gating, override consumption, and delegate priming.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded style-reference policy override before delegate execution for text-only style-reference turns
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- override state resets after delegate exit and does not apply to unrelated message text
- downstream frozen style-reference prompt/pending-state behavior remains unchanged
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
- bounded style-reference policy snapshot in `truffles-api/app/core/intent_routing.py`
- ingress priming in `truffles-api/app/services/reasoning_core.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into media-attached style-reference execution, stop and split
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
  - active block metadata must match the actual style-reference policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream style-reference execution.
- No widening into media-attached style-reference flow in this block.

## Risks/Blockers
- if detection is too broad, non-style-reference turns may be forced into the style-reference handoff path.
- if no-media gating is wrong, media-attached style-reference turns could be downgraded incorrectly.
- if override state is not normalized-text scoped, unrelated later requests may consume stale state.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still owns downstream style-reference pending/media prompt execution.
- non-style-reference policy outcomes still begin in frozen runtime.

### Why not in this block
- widening past the first policy contract would turn this into a full style-reference feature cutover.

### Risk if deferred
- text-only style-reference turns still pay for frozen policy-core ownership unless this slice lands.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-richer-semantic-outcome-bridge-a922.md` (to be created after this block)

### Expiry/trigger to stop deferral
- stop deferral when the next bounded semantic outcome can be proven safe without frozen-router edits.

## Next-block contract (mandatory)
### Next block objective
- move the next bounded semantic outcome seam after text-only style-reference handoff, using the same ingress override model.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k style_reference`

### Blocked-by conditions
- style-reference snapshot must remain text-only in this block.
- no frozen-router edits allowed.
- downstream style-reference execution must remain unchanged.

### Owner role for closure
- `Top Architect`
