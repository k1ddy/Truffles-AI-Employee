# TP-2026-03-15-consultant-core-expected-reply-projection-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-EXPECTED-REPLY-PROJECTION-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-PROJECTION-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-session-memory-projection-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PENDING-RESUME-PROJECTION-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: `expected_reply_type` и `expected_reply_reason` перестают нормализоваться ad hoc в `context_manager.py` и начинают проецироваться через `truffles-api/app/core/dialog_state_service.py` как projection-only fields.

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
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_webhook_booking.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_webhook_booking.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '800,970p' truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '1,220p' truffles-api/app/core/dialog_state_service.py`
  - `rg -n "_set_expected_reply_type|EXPECTED_REPLY_REASON_KEY|expected_reply_reason|expected_reply_type" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/core/dialog_state_service.py`
- `FACT findings`:
  - `context_manager.py` still strips and writes `expected_reply_type` / `expected_reply_reason` directly, so those projection-only fields still carry local normalization authority there.
  - `DialogStateService` already owns bounded continuity projections for `session_memory.interaction_state`, but not yet `expected_reply_*`.
  - `_set_expected_reply_context(...)` is the safest bridge point because legacy callers already flow through it, and `_set_expected_reply_type(...)` is the narrow write helper shared through the legacy export surface.
  - `docs/SOURCE_OF_TRUTH.yaml` still marks continuity as fragmented, so this block should remove one more projection authority without touching `pending_resume` or frozen semantic routers.
- `Detected drift (docs vs code)`: `expected_reply_type` and `expected_reply_reason` are documented as projection-only, but their normalization still lives in `context_manager.py` instead of `DialogStateService`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic model_copy update`
- **Date/time (local):** `2026-03-15 18:31 Asia/Almaty`
- **Why this query is precise:** this block centralizes projection-only fields inside `DialogStateService`, and the implementation should update an existing projection model without mutating unrelated fields like `session_memory_interaction_state`.
- **Sources opened (from this query):**
  - `Pydantic BaseModel API` — `https://docs.pydantic.dev/latest/api/base_model/#pydantic.main.BaseModel.model_copy`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** `model_copy(update=...)` is the built-in way to derive an updated projection model while preserving existing fields; it fits this bounded cut because we only need to replace normalized `expected_reply_*` values and leave the rest of the projections intact.
- **Decision:** `reuse + integrate` — extend the existing `DialogStateService` with an `expected_reply` projection helper and route `context_manager.py` through it instead of adding another normalization path.
- **Rejected options:**
  - widening this block into `pending_resume`
  - editing frozen legacy semantic router files
  - changing stored key names or removing `expected_reply_*` compatibility fields in this block
- **Open questions:** none for this bounded continuity slice.

## Root cause (mandatory)
- **Symptom:** `expected_reply_type` and `expected_reply_reason` are still normalized and written in `context_manager.py`, so continuity truth remains split even after the first session-memory projection cut.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/context_manager.py` and see `_set_expected_reply_type(...)`, `_get_expected_reply_type(...)`, `_get_expected_reply_reason(...)`, and `_set_expected_reply_context(...)` normalizing/writing these fields directly.
  2. Inspect `truffles-api/app/core/dialog_state_service.py` and confirm it does not yet own expected-reply projection normalization.
  3. Compare with `docs/SOURCE_OF_TRUTH.yaml`: `expected_reply_*` are projection-only.
- **Evidence to capture:**
  - `DialogStateService` contains the normalization/projection logic for `expected_reply_*`
  - `context_manager.py` delegates to that service instead of deciding the normalization itself
  - existing legacy context shape and helper behavior stay compatible
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because expected-reply projections still decide their own normalization inside the router helper.
  2. Why is that wrong? Because projection-only fields should not keep independent semantic cleanup logic.
  3. Why not cut `pending_resume` too? Because restore semantics are a separate carrier and would widen the block unsafely.
  4. Why is `context_manager.py` the right bridge point? Because it is the existing narrow writer path for `expected_reply_*` compatibility fields.
  5. Why does this reduce drift? Because one more live continuity carrier stops owning its own normalization rules after merge.
- **Root cause statement:** continuity ownership is still split because `context_manager.py` both normalizes and writes `expected_reply_*`, instead of delegating those projection-only semantics to `DialogStateService`.
- **Fix mechanism:**
  - add a bounded `expected_reply_*` projection helper to `DialogStateService`
  - route read/write helpers in `context_manager.py` through that helper
  - add deterministic tests proving projection normalization is centralized and legacy helper behavior remains compatible

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_webhook_booking.py`
- **External reuse:**
  - official Pydantic `model_copy` documentation for projection updates
- **Why not reinvent the wheel:** the repo already has a dialog-state service and a narrow expected-reply bridge; this block should connect them rather than add a new helper forest.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `8`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity migration with strict compatibility boundaries and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No changes to external key names for `expected_reply_type` / `expected_reply_reason`.
- No widening into `pending_resume` or state-service restore semantics.

## Scope
- Add one expected-reply projection helper to `DialogStateService`.
- Route `context_manager.py` expected-reply read/write helpers through that helper.
- Add deterministic tests for the new projection helper and legacy compatibility helper behavior.
- Sync source-of-truth/state/session docs.

## Out of scope
- `pending_resume` migration
- `state_service.py` restore refactor
- `decision.py`, `booking.py`, or `pending.py` edits
- removing compatibility fields from context

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-expected-reply-projection-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_webhook_booking.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this continuity TP with RCA and one web search.
2. Add `expected_reply_*` projection normalization to `DialogStateService`.
3. Route `context_manager.py` read/write helpers through that projection helper without changing legacy APIs.
4. Add deterministic tests for the projection helper and compatibility behavior.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns normalization/projection semantics for `expected_reply_type` and `expected_reply_reason`.
- `context_manager.py` no longer normalizes those values ad hoc.
- Existing legacy helper behavior stays compatible.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_webhook_booking.py -k 'expected_reply_type_round_trip'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` with expected-reply projection helper
- updated `context_manager.py` bridge using that helper
- deterministic test coverage for projection normalization and legacy compatibility
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires touching frozen semantic routers or widening into `pending_resume`, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity projection cut only
- **Go/no-go signals:** projection tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP’s continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target `pending_resume` or another isolated restore carrier separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual expected-reply slice being executed.

## Rollback
- Revert this TP’s `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No changes to `pending_resume` semantics.
- No new proof-path authority in tests.

## Risks/Blockers
- legacy callers may rely on exact clearing behavior where setting `expected_reply_type` also clears `expected_reply_reason`; the bridge must preserve that.
- expected-reply values are used widely in tests and traces, so normalization must stay byte-compatible after trimming.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `pending_resume`, restore semantics in `state_service.py`, and broader multi-writer continuity ownership remain fragmented.
- `Why not in this block`: they are distinct carriers with restore behavior beyond simple projection normalization.
- `Risk if deferred`: continuity remains multi-writer even though another projection carrier is centralized.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-pending-resume-projection-slice-a922`
- `Expiry/trigger to stop deferral`: before any new expected-reply continuity behavior is added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: isolate the next continuity carrier, likely `pending_resume` restore projection, without touching frozen semantic router files.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: expected-reply projection still normalized in `context_manager.py`; source-of-truth not synced; continuity tests absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: `decision.py`, `booking.py`, `pending.py`, `state_service.py`, and proof-only files
- `Open risks`: accidentally changing legacy clear/write order for expected-reply fields
- `First command to verify`: `pytest -q truffles-api/tests/test_webhook_booking.py -k 'expected_reply_type_round_trip'`
