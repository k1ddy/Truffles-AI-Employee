# TP-2026-03-16-consultant-core-booking-verification-policy-override-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOOKING-VERIFICATION-POLICY-OVERRIDE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-STYLE-REFERENCE-POLICY-OVERRIDE-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-style-reference-policy-override-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-RICHER-SEMANTIC-OUTCOME-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сдвинуть следующий bounded semantic outcome seam из frozen runtime в ingress path: `reasoning_core` должен заранее вычислять request-scoped `route_llm_policy_core(...)` override для явных booking-verification turns и scope it before delegate, чтобы frozen router потреблял precomputed `calendar.get_booking` policy contract вместо первого policy-core LLM pass на этих turns, при этом downstream verifier/prompt/handoff execution остаются без изменений.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-style-reference-policy-override-bridge-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/intent_routing.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/info_signal_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_intent.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/intent_routing.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/services/info_signal_service.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `truffles-api/tests/test_intent.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '120,150p' truffles-api/app/services/info_signal_service.py`
  - `sed -n '2480,2585p' truffles-api/app/services/intent_service.py`
  - `sed -n '19384,19530p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '26720,26860p' truffles-api/tests/test_message_endpoint.py`
  - `sed -n '1,260p' truffles-api/app/core/intent_routing.py`
  - `sed -n '1500,1635p' truffles-api/app/services/reasoning_core.py`
- `FACT findings`:
  - frozen `decision.py` still owns the first `route_llm_policy_core(...)` call for explicit booking-verification turns even though downstream verifier/prompt/handoff behavior already exists behind tool-contract validation.
  - routing-neutral verification detection already exists as `looks_like_booking_verification_message(...)` in `truffles-api/app/services/info_signal_service.py`.
  - `route_llm_policy_core(...)` already has a request-scoped override seam, so this slice can reuse that bridge without widening into new transport paths.
  - downstream frozen behavior already converts missing booking reference into the existing verifier prompt/handoff flow; this block does not need to reimplement any of that behavior.
- `Detected drift (docs vs code)`: ingress already owns bounded policy-core overrides for manager request, frustration, and text-only style-reference turns, but booking-verification semantics still begin with a frozen policy-core LLM call.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/contextlib.html Python ExitStack documentation`
- **Date/time (local):** `2026-03-16 11:57 +05`
- **Why this query is precise:** this block extends the existing stacked ingress override contexts and must keep request-scoped context entry/exit ordering deterministic.
- **Sources opened (from this query):**
  - `contextlib — Utilities for with-statement contexts — Python documentation` — `https://docs.python.org/3/library/contextlib.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `ExitStack` is the standard way to compose a variable number of context managers and guarantees LIFO unwinding for entered contexts.
- **Decision:** `reuse + integrate` — extend the existing `ExitStack`-based ingress override stack in `reasoning_core.py` with one more bounded policy snapshot context.
- **Rejected options:**
  - editing frozen `decision.py` to short-circuit booking verification directly
  - bypassing delegate execution with a direct response from `reasoning_core`
  - introducing a second non-ContextVar override transport
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** first policy-core semantic ownership for explicit booking-verification turns still begins inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `looks_like_booking_verification_message(...)` in `truffles-api/app/services/info_signal_service.py`.
  2. Open the verifier/prompt path in `truffles-api/app/routers/webhook/decision.py` for `calendar.get_booking` with missing reference.
  3. Open `route_llm_policy_core(...)` in `truffles-api/app/services/intent_service.py` and observe that, without an override, frozen code still owns the first policy-core call for these turns.
- **Evidence to capture:**
  - `reasoning_core` primes a bounded policy-core override before delegate execution for booking-verification turns
  - `route_llm_policy_core(...)` consumes request-scoped override payloads for the same inbound without requiring LLM/provider init
  - override state resets after delegate exit and does not leak to unrelated message text
  - downstream frozen booking-verification verifier/prompt/handoff behavior remains unchanged
- **Five Whys (or equivalent):**
  1. Why is this semantic seam still legacy-shaped? Because booking-verification turns still start with the first policy-core LLM call inside frozen runtime.
  2. Why does that matter? Because a deterministic, already productized verifier/prompt/handoff branch still depends on legacy semantic ownership before it can run.
  3. Why not cut over the full booking-verification feature now? Because verifier, prompt, tool execution, and handoff wiring already exist downstream and widening past the first policy contract would break bounded scope.
  4. Why is a bounded override safe? Because the detector already exists and downstream verifier behavior remains untouched.
  5. Why does this reduce drift? Because ingress becomes first owner of another real semantic outcome contract while frozen code becomes only the executor of that contract.
- **Root cause statement:** booking-verification semantics remain in frozen `decision.py` because `reasoning_core` does not yet prime any request-scoped `route_llm_policy_core(...)` override for that turn family, even though the detector and downstream verifier/prompt flow already exist.
- **Fix mechanism:**
  - extend bounded policy snapshot detection in `app/core/intent_routing.py`
  - reuse the existing policy-core override seam in `intent_service.py`
  - prime the snapshot from `reasoning_core.py` before delegate execution

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `PolicyCoreRouteSnapshot` / policy override seam from previous blocks
  - existing `looks_like_booking_verification_message(...)` detector in `truffles-api/app/services/info_signal_service.py`
  - existing downstream verifier/prompt/handoff branch in frozen runtime
  - existing `ExitStack`-based ingress override composition in `reasoning_core.py`
- **External reuse:**
  - official Python `contextlib` documentation
- **Why not reinvent the wheel:** the repo already has both the verification detector and the request-scoped policy override path; this block should compose them instead of creating another routing mechanism.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `21`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded semantic bridge with focused deterministic tests and no frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No LLM/provider call for overridden booking-verification policy turns.
- No override bleed across requests or unrelated message text.
- No change to downstream booking-verification verifier/prompt/handoff behavior; frozen delegate still owns execution.

## Scope
- Extend bounded policy-core snapshot detection in `truffles-api/app/core/intent_routing.py` for explicit booking-verification turns.
- Prime the existing request-scoped policy-core override from `truffles-api/app/services/reasoning_core.py`.
- Add deterministic tests in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_intent.py`.
- Sync required canon/session artifacts.

## Out of scope
- full booking-verification feature cutover
- handoff routing changes
- frozen-router edits
- proof-path work
- continuity work
- multi-pack acceptance or neutral runtime cleanup

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-booking-verification-policy-override-bridge-a922.md`
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
2. Extend bounded policy-core snapshot detection for booking-verification turns.
3. Prime the existing policy-core override from `reasoning_core.py` before delegate execution.
4. Add deterministic tests for detection, override consumption, and delegate priming.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `reasoning_core` primes a bounded booking-verification policy override before delegate execution
- `route_llm_policy_core(...)` consumes the request-scoped override without LLM/provider init
- override state resets after delegate exit and does not apply to unrelated message text
- downstream frozen booking-verification verifier/prompt/handoff behavior remains unchanged
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
- bounded booking-verification policy snapshot in `truffles-api/app/core/intent_routing.py`
- ingress priming in `truffles-api/app/services/reasoning_core.py`
- focused runtime/service tests and synced session/state artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or grows into full booking-verification execution, stop and split
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
  - active block metadata must match the actual booking-verification policy override bridge being executed.

## Rollback
- Revert this TP's core/service/test/doc changes only; keep earlier ingress bridges intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No bypass of frozen downstream booking-verification execution.
- No widening into tool verifier or handoff execution changes in this block.

## Risks/Blockers
- if detection is too broad, non-verification turns may be forced into the booking-verification path.
- if override state is not normalized-text scoped, unrelated later requests may consume stale state.
- if the override payload is not contract-compatible, frozen verifier logic could fall into an unintended generic repair path.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still owns downstream booking-verification verifier/prompt/handoff execution.
- non-booking-verification policy outcomes still begin in frozen runtime.

### Why not in this block
- widening past the first policy contract would turn this into a full booking-verification feature cutover.

### Risk if deferred
- booking-verification turns still pay for frozen policy-core ownership unless this slice lands.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-richer-semantic-outcome-bridge-a922.md` (to be created after this block)

### Expiry/trigger to stop deferral
- stop deferral when the next bounded semantic outcome can be proven safe without frozen-router edits.

## Next-block contract (mandatory)
### Next block objective
- move the next bounded semantic outcome seam after booking-verification policy override, using the same ingress override model.

### First deterministic check command
- `pytest -q truffles-api/tests/test_reasoning_core.py -k booking_verification`

### Blocked-by conditions
- booking-verification snapshot must stay bounded to explicit verification turns in this block.
- no frozen-router edits allowed.
- downstream verifier/prompt/handoff execution must remain unchanged.

### Owner role for closure
- `Top Architect`
