# TP-2026-03-16-consultant-core-preflight-cache-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PREFLIGHT-CACHE-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SECRET-SAFE-PREFLIGHT-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-secret-safe-preflight-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-INGRESS-PREFLIGHT-AUTHORITY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Убрать дублирующий non-secret preflight pass после secret-safe bridge без правок frozen router files: повторный вызов `truffles-api/app/routers/webhook/http.py:_run_preflight(...)` из frozen `decision.py` должен переиспользовать уже вычисленный preflight payload для того же wrapped `/webhook` запроса вместо повторного branch/tenant validation и side-effect-free rework.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-secret-safe-preflight-cutover-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/tests/test_reasoning_core.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/tests/test_reasoning_core.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '9310,9345p' truffles-api/app/routers/webhook/decision.py`
  - `rg -n "_run_secret_enforced_preflight|enforce_secret=False if secret_preflight_passed|_run_preflight\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/http.py`
  - `sed -n '1,120p' truffles-api/app/services/capabilities_runtime.py`
- `FACT findings`:
  - the previous block made wrapped `/webhook` secret-safe, but successful bridge handoff still enters frozen `decision.py`, which immediately calls `http._run_preflight(...)` again with `enforce_secret=False`.
  - this second pass is not unsafe anymore, but it keeps duplicate preflight ownership and repeated branch/tenant/payload derivation work behind the frozen seam.
  - `http.py` is non-frozen and can host a request-scoped cache bridge; the repo already uses module-level `ContextVar` patterns in runtime services.
  - `decision.py` is frozen, so the bounded fix must avoid editing its call-site.
- `Detected drift (docs vs code)`: wrapped ingress is now secret-safe, but the claimed ingress cutover is still architecturally incomplete because the frozen router performs a second preflight derivation after the bridge succeeds.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org contextvars ContextVar Python documentation`
- **Date/time (local):** `2026-03-16 08:39 Asia/Almaty`
- **Why this query is precise:** this block needs one request-scoped async-safe bridge for cached preflight payload reuse, and the standard-library `ContextVar` contract determines whether that state can be safely set/reset around delegate calls.
- **Sources opened (from this query):**
  - `contextvars — Context Variables — Python documentation` — `https://docs.python.org/3/library/contextvars.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python recommends top-level `ContextVar` objects for context-local state in async code; `set()` returns a token that must be reset to restore the prior context value.
- **Decision:** `reuse + integrate` — add a top-level request-scoped preflight cache `ContextVar` in `truffles-api/app/routers/webhook/http.py` and reset it around the wrapped delegate call.
- **Rejected options:**
  - editing frozen `decision.py` to skip the second preflight call
  - storing cache state on the pydantic payload object itself
  - using process-global mutable state without async context isolation
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** after the secret-safe bridge passes, wrapped `/webhook` still runs a second non-secret preflight inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Open `truffles-api/app/services/reasoning_core.py` and observe that successful `_run_secret_enforced_preflight(...)` delegates into `decision_router._handle_webhook_payload(..., enforce_secret=False)`.
  2. Open `truffles-api/app/routers/webhook/decision.py` and observe that it unconditionally calls `http._run_preflight(...)` before continuing.
  3. Open `truffles-api/app/routers/webhook/http.py:_run_preflight(...)` and observe that, with `enforce_secret=False`, it still repeats the full payload/tenant/branch derivation path.
- **Evidence to capture:**
  - wrapped delegate calls reuse cached preflight payload through a non-frozen seam
  - `http._run_preflight(...)` short-circuits only when the request-scoped bridge is present and matches the same payload/db/conversation
  - cache is reset after the delegate path so unrelated requests cannot see stale preflight state
- **Five Whys (or equivalent):**
  1. Why is ingress cutover still incomplete? Because the frozen legacy router still derives preflight data a second time after the bridge already did it.
  2. Why is that undesirable? Because authority is still split across the new ingress seam and the frozen preflight path.
  3. Why not remove the call in `decision.py`? Because `decision.py` is frozen.
  4. Why does a request-scoped cache help? Because the frozen call-site can stay untouched while `_run_preflight(...)` reuses the already validated payload for that exact request.
  5. Why does this reduce drift? Because the wrapped ingress path stops recomputing legacy preflight state after the new seam already established it.
- **Root cause statement:** the secret-safe bridge moved hard preflight authority to `reasoning_core`, but the frozen delegate still re-enters legacy `_run_preflight(...)` and recomputes the same non-secret preflight payload because there is no non-frozen request-scoped reuse seam.
- **Fix mechanism:**
  - add a top-level request-scoped preflight cache bridge in `truffles-api/app/routers/webhook/http.py`
  - wrap the wrapped delegate call in `reasoning_core` so the cache is set only for the successful bridge handoff window
  - make `_run_preflight(...)` reuse that cached payload only when payload/db/conversation match and `enforce_secret=False`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/webhook/http.py:_run_preflight(...)`
  - `truffles-api/app/services/reasoning_core.py:_run_secret_enforced_preflight(...)`
  - existing repo `ContextVar` patterns in `truffles-api/app/services/capabilities_runtime.py` and `truffles-api/app/services/knowledge_runtime.py`
- **External reuse:**
  - official Python `contextvars.ContextVar` documentation
- **Why not reinvent the wheel:** the repo already uses top-level `ContextVar` for request-scoped runtime state, so the bounded bridge should reuse the same async-safe pattern instead of inventing a custom global cache.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `15`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded ingress bridge follow-up with a small non-frozen seam and deterministic tests.

## Invariant
- No edits in frozen legacy semantic router files.
- No weakening of secret-safe preflight enforcement.
- No stale cross-request preflight cache bleed.

## Scope
- Add a request-scoped preflight cache bridge in `truffles-api/app/routers/webhook/http.py`.
- Use that bridge from `truffles-api/app/services/reasoning_core.py` only around successful wrapped delegate handoff.
- Update `truffles-api/tests/test_reasoning_core.py` for cache reuse and reset behavior.
- Sync canon/session artifacts.

## Out of scope
- richer semantic planner cutover
- dedup/debounce bridge work
- frozen router edits
- direct webhook (`/webhook/{client_slug}`) path changes beyond unaffected compatibility

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-preflight-cache-bridge-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/tests/test_reasoning_core.py`
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
2. Add a request-scoped preflight cache bridge in `truffles-api/app/routers/webhook/http.py`.
3. Wrap the successful secret-safe delegate handoff in `truffles-api/app/services/reasoning_core.py` with that bridge.
4. Add deterministic tests for cache reuse, sender-branch regression safety, and reset behavior where bounded.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- successful secret-safe wrapped handoff does not recompute non-secret preflight payload in legacy `_run_preflight(...)`
- cache bridge is scoped to the exact wrapped request and reset after delegate return
- secret enforcement behavior from the previous block stays unchanged
- required deterministic checks are green

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- request-scoped preflight cache bridge in `truffles-api/app/routers/webhook/http.py`
- updated wrapped handoff in `truffles-api/app/services/reasoning_core.py`
- updated `truffles-api/tests/test_reasoning_core.py`
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires frozen-router edits or expands into dedup/debounce bridge work, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** wrapped `/webhook` bridge follow-up only
- **Go/no-go signals:** reasoning-core suite + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's `http.py` / `reasoning_core.py` / tests / docs changes only
- **Post-release monitoring window:** next block should either move richer semantic cutover forward or keep shrinking legacy ingress authority without touching frozen files

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual preflight-cache bridge being executed.

## Rollback
- Revert this TP's `http.py`, `reasoning_core.py`, test, and doc changes; keep the prior secret-safe bridge block intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No process-global mutable cache without async context isolation.
- No dedup/debounce cutover in this block.

## Risks/Blockers
- if the cache bridge key is too loose, stale preflight payload could bleed into unrelated requests.
- if the bridge is not reset around delegate exit, the fix becomes architecturally unsafe even if tests pass locally.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: richer semantic planner slices still live in frozen `decision.py`; dedup/debounce remain legacy-owned.
- `Why not in this block`: this block is only about removing duplicate preflight derivation after the secret-safe bridge.
- `Risk if deferred`: wrapped ingress remains partially legacy-authored even after the hard secret gate moved.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-rich-semantic-cutover-followup-a922`
- `Expiry/trigger to stop deferral`: before claiming ingress cutover completion or before attempting debounce/dedup migration.

## Next-block contract (mandatory)
- `Next block objective`: take the next richer semantic cutover in `truffles-api/app/services/reasoning_core.py` now that wrapped ingress can reuse the bridge payload without duplicate preflight derivation.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: duplicate preflight payload reuse not working; stale bridge state not reset; source-of-truth not synced.
- `Owner role for closure`: `Top Architect`
