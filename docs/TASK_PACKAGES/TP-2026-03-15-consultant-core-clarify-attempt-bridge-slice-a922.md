# TP-2026-03-15-consultant-core-clarify-attempt-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CLARIFY-ATTEMPT-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-COMPACT-SUMMARY-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-compact-summary-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения clarify-limit behavior: `clarify_attempts` перестаёт держать собственные read/write shaping rules в `truffles-api/app/routers/webhook/guards.py` и начинает проходить через `DialogStateService`, при сохранении existing payload shape and clarify-limit escalation behavior.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "clarify_attempts|_get_clarify_attempt_state|_set_clarify_attempt|_register_clarify_attempt|clarify_limit" truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/response.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/decision.py`
  - `rg -n "clarify_attempts|clarify_limit|clarify_attempt" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_state_service.py`
- `FACT findings`:
  - `clarify_attempts` read/write shaping still lives only in `truffles-api/app/routers/webhook/guards.py`.
  - the writer is used from live non-frozen paths in `guards.py`, then consumed by `response.py`, `info.py`, and frozen `decision.py`.
  - the stored payload shape is small and bounded: `context_manager.clarify_attempts[intent] = {"count", "last_at"}`.
  - existing tests already pin clarify-limit escalation behavior in `truffles-api/tests/test_message_endpoint.py`, but there is no deterministic bridge coverage for the payload shaping itself.
- `Detected drift (docs vs code)`: continuity canon says shaping should converge on `DialogStateService`, but `clarify_attempts` still authors its payload rules outside the bridge.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy.deepcopy documentation`
- **Date/time (local):** `2026-03-15 20:27 Asia/Almaty`
- **Why this query is precise:** this slice updates a nested per-intent map in `context_manager`, so the bridge needs one authoritative reference for detached nested copies rather than helper-local mutation assumptions.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard-library mechanism for recursively copying nested mutable structures before updates so writers do not alias old payloads.
- **Decision:** `reuse + integrate` — keep clarify-attempt bridge updates in `DialogStateService` and use deep copies for the nested attempts map instead of inventing a custom copier.
- **Rejected options:**
  - widening into a full clarify-policy refactor
  - touching frozen legacy semantic router files
  - moving clarify-limit decision thresholds in the same block
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `clarify_attempts` still retains helper-local read/write shaping in `guards.py`.
- **Minimal reproduction:**
  1. Inspect `_get_clarify_attempt_state(...)` and `_set_clarify_attempt(...)` in `truffles-api/app/routers/webhook/guards.py`.
  2. Inspect `_register_clarify_attempt(...)` and note that it persists nested payloads directly into `context_manager`.
  3. Inspect `response.py`/`info.py`/`decision.py` and note they all rely on the stored payload shape but do not need to own the shaping rules.
- **Evidence to capture:**
  - `DialogStateService` owns bounded get/set shaping for clarify attempts.
  - `guards.py` delegates payload shaping to that bridge while keeping orchestration and escalation logic unchanged.
  - existing clarify-limit integration stays green.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because clarify-attempt payload shaping still lives in router helper code.
  2. Why is that wrong? Because live continuity carriers should converge on one shaping seam in `DialogStateService`.
  3. Why not move the whole clarify flow? Because thresholds and escalation logic are runtime policy/orchestration, not the bounded continuity seam.
  4. Why is this block safe? Because it centralizes only payload shaping while preserving the existing stored contract and clarify-limit behavior.
  5. Why does this reduce drift? Because another live context carrier stops defining its own nested payload rules outside the bridge.
- **Root cause statement:** continuity ownership is still split because `clarify_attempts` keeps helper-local payload shaping in `guards.py` instead of flowing through `DialogStateService`.
- **Fix mechanism:**
  - add bounded clarify-attempt get/set helpers to `DialogStateService`
  - route `_get_clarify_attempt_state(...)` and `_set_clarify_attempt(...)` in `guards.py` through that bridge
  - keep `_register_clarify_attempt(...)` as thin orchestration for trace/meta and compact-summary side effects
  - add deterministic bridge coverage plus keep clarify-limit compatibility green

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - existing `_canonical_int(...)` helper
  - existing clarify-limit integration test in `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Python `copy.deepcopy(...)` documentation
- **Why not reinvent the wheel:** the repo already has the continuity bridge and a standard nested-copy primitive; this block should only remove duplicated clarify-attempt shaping.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `15`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration for one nested map carrier with deterministic verification.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to clarify-limit thresholds or escalation behavior.
- No widening into broader clarify-policy refactors.

## Scope
- Add bounded clarify-attempt get/set helpers to `DialogStateService`.
- Route `guards.py` clarify-attempt payload shaping through that bridge.
- Add deterministic bridge coverage and keep clarify-limit integration green.
- Sync source-of-truth/state/session docs.

## Out of scope
- clarify-limit threshold changes
- full clarify-policy refactor
- semantic router changes in frozen files
- debounce/buffer

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-clarify-attempt-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/guards.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this clarify-attempt TP with RCA and one web search.
2. Add bounded clarify-attempt get/set helpers to `DialogStateService`.
3. Route `guards.py` clarify-attempt payload shaping through that bridge without touching frozen semantic router files.
4. Add deterministic bridge coverage and run clarify-limit compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded get/set behavior for `clarify_attempts`.
- `guards.py` no longer authors clarify-attempt payload shaping directly.
- Existing clarify-limit integration remains green.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'clarify_attempt or compact_summary or LowConfidenceRetryGate'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_clarify_limit_escalates_after_two_attempts'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` clarify-attempt bridge helpers
- updated `guards.py` delegating clarify-attempt shaping
- deterministic bridge coverage plus clarify-limit integration test
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or changing clarify-limit semantics, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** dialog-state tests + clarify compatibility tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next block should either take the next safe continuity slice or switch back to proof/semantic cutover if no bounded continuity seam remains

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual clarify-attempt bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `guards.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No clarify-limit threshold changes.

## Risks/Blockers
- any change to the stored payload shape would silently affect frozen `decision.py` clarify-limit reads.
- this slice must not collapse orchestration side effects like trace/meta updates and compact-summary updates into the bridge.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader context/state writer ownership and proof-path excision still remain outside the bridge.
- `Why not in this block`: that would exceed a safe bounded migration slice.
- `Risk if deferred`: continuity still has helper-owned writers after this cut.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-writer-collapse-slice-a922`
- `Expiry/trigger to stop deferral`: before any new context/state carrier semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: take the next safe bounded continuity slice after clarify-attempts, or switch back to proof/semantic cutover if no safe writer remains.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: clarify-attempt payload shaping still authored in `guards.py`; source-of-truth not synced; deterministic bridge coverage absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and clarify-limit thresholds
- `Open risks`: accidentally changing nested `clarify_attempts` payload shape or escalate side effects
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_clarify_limit_escalates_after_two_attempts'`
