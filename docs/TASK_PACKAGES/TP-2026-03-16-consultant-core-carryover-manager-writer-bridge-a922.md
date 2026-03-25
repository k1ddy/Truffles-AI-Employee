# TP-2026-03-16-consultant-core-carryover-manager-writer-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CARRYOVER-MANAGER-WRITER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ANCILLARY-CONTEXT-CARRIER-WRITER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ancillary-context-carrier-writer-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после ancillary context-carrier writer bridge: manager-level write/delete semantics for legacy `class_carryover`, `service_carryover`, and `consult_context` must stop living in `truffles-api/app/routers/webhook/context_manager.py`. `DialogStateService` should become the owner of manager payload sync/clear behavior for this carryover family, while `context_manager.py` stays a thin orchestration layer around legacy key names and trace/meta side effects.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ancillary-context-carrier-writer-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '560,1040p' truffles-api/app/routers/webhook/context_manager.py`
  - `rg -n "class_carryover|service_carryover|consult_context|canonical_dialog_state" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_message_endpoint.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_service_carryover_applies_for_pricing or test_legacy_service_carryover_reads_from_canonical_dialog_state or test_legacy_class_carryover_setter_syncs_canonical_dialog_state or test_legacy_consult_context_setter_syncs_canonical_dialog_state'`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns payload building/getters plus canonical mirrors for class/service/consult carryover families.
  - `context_manager.py` still owns manager-level `manager[key]=...` / `manager.pop(...)` semantics and canonical sync/clear behavior for these live carryover writers.
  - This seam is bounded because it only affects manager payload mutation for existing carryover families; trace/meta orchestration and frozen-router readers remain unchanged.
- `Detected drift (docs vs code)`: single continuity writer completion is still blocked by manager-level carryover write/delete authority living in `context_manager.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy official documentation`
- **Date/time (local):** `2026-03-16 22:24 +0500`
- **Why this query is precise:** the block moves manager payload ownership into `DialogStateService` and must preserve detached-copy semantics for nested carryover payloads while clearing or syncing canonical mirrors.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy` remains the correct baseline for manager payload isolation while relocating write/delete ownership.
- **Decision:** `reuse + integrate` — preserve existing detached-copy semantics while relocating manager-level carryover write/delete authority into `DialogStateService`.
- **Rejected options:**
  - leaving manager key mutation in `context_manager.py`
  - widening this block into broader reset/restore/state-boundary semantics
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `context_manager.py` still owns manager-level write/delete semantics for legacy class/service/consult carryover families, so `DialogStateService` is not yet the single writer for those live continuity seams.
- **Minimal reproduction:**
  1. Call `_set_class_carryover(...)`, `_set_service_carryover(...)`, or `_set_consult_context(...)` in `context_manager.py`.
  2. Observe that `DialogStateService` only builds or reads normalized payloads, while `context_manager.py` still decides whether the legacy key and canonical mirror are written or cleared.
  3. Call `_prune_*` helpers and observe that `context_manager.py` still decides when the legacy key and canonical mirror are removed.
- **Evidence to capture:**
  - `DialogStateService` directly owns manager write/delete behavior for these carryover families.
  - `context_manager.py` becomes a thin wrapper around trace/meta and legacy constants.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because payload construction moved, but manager-level mutation did not.
  2. Why is that a problem? Because live carryover state still has split write/delete authority.
  3. Why is this bounded? Because the affected helpers only mutate carryover keys plus their canonical mirrors.
  4. Why not widen into broader canonical sync? Because booking/restore/state-boundary semantics are a separate riskier seam.
  5. Why fix this now? Because it deletes another real live writer family without adding any semantic bridge.
- **Root cause statement:** `context_manager.py` still decides how legacy class/service/consult carryover payloads and their canonical mirrors are written or removed from the manager, so `DialogStateService` is not yet the sole writer for that carryover family.
- **Fix mechanism:**
  - add bounded manager write/delete helpers to `DialogStateService` for class/service/consult carryover families
  - replace local manager mutation in `context_manager.py` with thin delegation
  - prove parity with focused dialog-state tests and targeted message-endpoint compatibility checks

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing carryover payload builders/getters in `DialogStateService`
  - existing canonical class/service/consult state helpers in `DialogStateService`
  - existing targeted endpoint tests for carryover compatibility
- **External reuse:**
  - official Python `copy.deepcopy` semantics from the standard library docs
- **Why not reinvent the wheel:** this is continuity-owner consolidation, not a new carryover model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded carryover-writer collapse plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Existing class/service/consult carryover behavior stays externally unchanged.
- Detached-copy semantics stay unchanged for nested carryover payloads.

## Scope
- Add bounded manager write/delete helpers to `DialogStateService` for class/service/consult carryover families.
- Make `context_manager.py` delegate carryover manager mutation to the service.
- Add regression tests for the new service-owned writer behavior.
- Sync canon/session artifacts.

## Out of scope
- broader reset/restore/state-boundary semantics
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- new semantic owner cutovers
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-carryover-manager-writer-bridge-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add bounded manager write/delete helpers to `DialogStateService` for class/service/consult carryover families.
3. Replace local manager mutation in `context_manager.py` with thin delegation.
4. Add focused dialog-state tests and rerun targeted carryover compatibility checks.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns manager write/delete behavior for legacy class/service/consult carryover families.
- `context_manager.py` stays orchestration-only for those seams.
- tests prove parity for payload sync and prune/clear semantics.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_service_carryover_applies_for_pricing or test_legacy_service_carryover_reads_from_canonical_dialog_state or test_legacy_class_carryover_setter_syncs_canonical_dialog_state or test_legacy_consult_context_setter_syncs_canonical_dialog_state'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- dialog-state unit tests showing service-owned manager writer behavior for class/service/consult carryover families
- targeted message-endpoint checks showing carryover compatibility remains unchanged
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + targeted compatibility + architecture only for this bounded block
- **Stop condition:** if this slice requires broader reset/restore/state-boundary widening or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + targeted compatibility + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helpers, context-manager delegation, tests, and doc sync
- **Post-release monitoring window:** next block should continue writer collapse or return to owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the carryover manager writer bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, context-manager delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader restore/reset/state-boundary orchestration
- no counting this block as done unless `context_manager.py` loses local manager write/delete authority for class/service/consult carryover families

## Risks / blockers
- if manager-clear semantics drift, stale carryover payloads can remain live longer than before.
- if canonical sync behavior drifts, carryover readers can split between legacy and canonical views.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers still remain outside this carryover family
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded carryover-writer slice; widening further would mix manager mutation with broader canonical sync or restore semantics
- **Risk if deferred:**
  - continuity would keep split write/delete authority for the carryover family and make final single-writer closure harder
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - stop deferral once the next bounded live writer can be removed without widening into broader state-boundary semantics

## Next-block contract (mandatory)
- **Next block objective:** either remove the next remaining bounded continuity writer seam, or return to a direct owner-replacement cutover if no safe writer-collapse slice remains
- **First deterministic check command:** `rg -n "_set_class_carryover|_set_service_carryover|_set_consult_context|_prune_class_carryover|_prune_service_carryover|_prune_consult_context" truffles-api/app/routers/webhook/context_manager.py`
- **Blocked-by conditions:** block if the next seam requires frozen-router edits, new generic bridge families, or broader reset/restore semantics
- **Owner role for closure:** `Top Architect`
