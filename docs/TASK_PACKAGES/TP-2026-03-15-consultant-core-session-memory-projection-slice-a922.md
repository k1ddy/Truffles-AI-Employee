# TP-2026-03-15-consultant-core-session-memory-projection-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-PROJECTION-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-PATH-AST-BLACKBOX-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-path-ast-blackbox-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-EXPECTED-REPLY-PROJECTION-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать первый реальный continuity cut без изменения legacy happy-path semantics: `session_memory.interaction_state` перестает нормализоваться ad hoc внутри `session_memory.py` и начинает проецироваться через `truffles-api/app/core/dialog_state_service.py` как projection-only lane.

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
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/services/state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,220p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '40,260p' truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "interaction_state|expected_reply_type|pending_resume" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/state_service.py truffles-api/app/core/dialog_state_service.py`
- `FACT findings`:
  - `truffles-api/app/core/dialog_state_service.py` already claims future continuity ownership, but it currently only builds bounded new-core artifacts and does not own legacy `session_memory.interaction_state` projection.
  - `truffles-api/app/routers/webhook/session_memory.py` still contains the full normalization and write logic for `interaction_state`, so continuity authority is still split.
  - `truffles-api/app/routers/webhook/context_manager.py` and legacy paths still call `_sync_session_memory_interaction_state(...)`, which means this helper is the safest bridge point for the first continuity cut.
  - `docs/SOURCE_OF_TRUTH.yaml` currently marks continuity as `fragmented_writers`, so a bounded projection cut is required before broader writer collapse.
- `Detected drift (docs vs code)`: `session_memory.interaction_state` is documented as projection-only, but the projection semantics still live in `session_memory.py`, not in `DialogStateService`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic model_dump exclude_none`
- **Date/time (local):** `2026-03-15 18:24 Asia/Almaty`
- **Why this query is precise:** this block moves a legacy projection into `DialogStateService`, and the projection must preserve omit-null behavior instead of widening the legacy shape with extra `None` fields.
- **Sources opened (from this query):**
  - `Pydantic BaseModel API` — `https://docs.pydantic.dev/latest/api/base_model/#pydantic.main.BaseModel.model_dump`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** `model_dump(..., exclude_none=True)` is the built-in way to emit compatibility projections without reintroducing ad hoc `None` cleanup logic.
- **Decision:** `reuse + integrate` — keep the existing `DialogStateService`, add one projection-normalization method there, and have `session_memory.py` delegate to it instead of inventing a second projection authority.
- **Rejected options:**
  - widening this block into `expected_reply_*` migration
  - rewriting legacy callers in `decision.py`
  - changing persisted session-memory shape in this block
- **Open questions:** none for this bounded continuity slice.

## Root cause (mandatory)
- **Symptom:** `session_memory.interaction_state` is still normalized and authored in `session_memory.py`, so continuity truth remains split even though `DialogStateService` already exists.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/core/dialog_state_service.py` and confirm it does not own legacy `session_memory.interaction_state` projection yet.
  2. Inspect `truffles-api/app/routers/webhook/session_memory.py` and see `_normalize_interaction_state(...)` plus `_sync_session_memory_interaction_state(...)` performing normalization and persistence directly.
  3. Compare with `docs/SOURCE_OF_TRUTH.yaml`: `session_memory.interaction_state` should be projection-only.
- **Evidence to capture:**
  - `DialogStateService` contains the projection-normalization logic for `session_memory.interaction_state`
  - `session_memory.py` delegates to that service instead of cleaning the payload itself
  - legacy context shape remains unchanged for valid data
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because projection semantics still live in router/session-memory helpers.
  2. Why is that wrong? Because projection-only fields should not carry their own semantic authority.
  3. Why not cut all writers at once? Because `decision.py` and `state_service.py` still depend on legacy bridges and wider cutover would be unsafe in one block.
  4. Why is `session_memory.py` the right bridge point? Because all current legacy callers already flow through `_sync_session_memory_interaction_state(...)`.
  5. Why does this reduce future drift? Because one live continuity carrier stops deciding its own normalization rules after merge.
- **Root cause statement:** continuity ownership is still split because `session_memory.py` both decides and writes `interaction_state`, instead of delegating projection semantics to the emerging canonical `DialogStateService`.
- **Fix mechanism:**
  - add a bounded `session_memory.interaction_state` projection-normalization method to `DialogStateService`
  - route `_normalize_interaction_state(...)` and `_sync_session_memory_interaction_state(...)` through that method
  - add deterministic tests proving the projection is normalized in one place and preserves legacy shape

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- **External reuse:**
  - official Pydantic `model_dump` documentation for omit-null projections
- **Why not reinvent the wheel:** the repo already has a canonical dialog-state service and legacy session-memory bridge; this block should connect them rather than adding a third continuity helper.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `7`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity migration with compatibility constraints and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to persisted `session_memory.interaction_state` shape for already-valid payloads.
- No widening into `expected_reply_*` or `pending_resume` in this block.

## Scope
- Add one projection-normalization method to `DialogStateService` for `session_memory.interaction_state`.
- Delegate `session_memory.py` normalization/sync to that service.
- Add deterministic tests for the projection helper and the legacy bridge behavior.
- Sync source-of-truth/state/session docs.

## Out of scope
- `expected_reply_type` / `expected_reply_reason` migration
- `pending_resume` migration
- changing `decision.py`, `booking.py`, or `pending.py`
- state-service resume restore refactor

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-session-memory-projection-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this continuity TP with RCA and one web search.
2. Add `session_memory.interaction_state` projection-normalization to `DialogStateService`.
3. Route `session_memory.py` through that projection method without changing legacy caller APIs.
4. Add deterministic tests for normalized projection and bridge behavior.
5. Re-run continuity/proof/packet/session gates and sync docs.

## DoD
- `DialogStateService` owns the normalization/projection semantics for `session_memory.interaction_state`.
- `session_memory.py` no longer cleans that payload ad hoc.
- Valid legacy projection shape is preserved.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` with session-memory projection helper
- updated `session_memory.py` bridge using that helper
- deterministic test coverage for the projection and compatibility shape
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires changing frozen legacy router files or widening into `expected_reply_*`, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity projection cut only
- **Go/no-go signals:** projection tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP’s continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target `expected_reply_*` projection-only lane separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual continuity slice being executed.

## Rollback
- Revert this TP’s `DialogStateService`, `session_memory.py`, test, and doc changes; keep already-landed governance/proof/runtime-slice blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No changes to external session-memory keys beyond `interaction_state` projection authority.
- No new proof-path authority in tests.

## Risks/Blockers
- legacy callers may rely on exact omission behavior for `None` fields, so the projection helper must preserve that behavior.
- `confirmation_state` currently exists only in the legacy shape, so this block must treat it as compatibility projection data, not widen the runtime contract.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `expected_reply_*`, `pending_resume`, and wider continuity write ownership remain fragmented after this slice.
- `Why not in this block`: they are separate carriers with different restore/write semantics and need their own bounded cutovers.
- `Risk if deferred`: continuity remains multi-writer, even though one projection carrier is now centralized.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-expected-reply-projection-slice-a922`
- `Expiry/trigger to stop deferral`: before any new continuity behavior is added to `session_memory.py`, `state_service.py`, or `context_manager.py`.

## Next-block contract (mandatory)
- `Next block objective`: move `expected_reply_*` projection semantics behind the same dialog-state authority without touching frozen legacy router semantics.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: `session_memory.interaction_state` projection not centralized; source-of-truth not synced; continuity tests absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: `decision.py`, `booking.py`, `pending.py`, and proof-only files
- `Open risks`: accidentally widening the runtime `DialogState` contract instead of implementing a compatibility projection helper
- `First command to verify`: `pytest -q truffles-api/tests/test_dialog_state_service.py`
