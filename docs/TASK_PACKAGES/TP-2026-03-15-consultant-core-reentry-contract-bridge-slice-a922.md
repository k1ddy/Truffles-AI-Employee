# TP-2026-03-15-consultant-core-reentry-contract-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-REENTRY-CONTRACT-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CANONICAL-DIALOG-STATE-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-canonical-dialog-state-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-MANAGER-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: `re_entry_required` перестаёт авториться ad hoc в `truffles-api/app/routers/webhook/context_manager.py` и внутри `restore_pending_resume_payload(...)`, а проходит через один typed bridge в `truffles-api/app/core/dialog_state_service.py`.

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
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "re_entry_required|_set_re_entry_required|_clear_re_entry_required|restore_pending_resume_payload" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/app/services/state_service.py`
  - `rg -n "re_entry_required" truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_message_endpoint.py`
- `FACT findings`:
  - `context_manager.py` still owns `re_entry_required` set/clear helpers and raw payload reads.
  - `DialogStateService.restore_pending_resume_payload(...)` also authors the same `re_entry_required` payload shape directly.
  - `pending.py` and `decision.py` already consume the `context_manager` helper path, so a bridge cut here can narrow authorship without touching frozen semantic router files.
  - Existing tests already pin both restore (`pending_resume`) and clear-on-question behavior.
- `Detected drift (docs vs code)`: continuity ownership moved several carriers into `DialogStateService`, but `re_entry_required` still has split write semantics across router helper code and dialog-state restore logic.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev model_validate extra forbid pydantic`
- **Date/time (local):** `2026-03-15 19:03 Asia/Almaty`
- **Why this query is precise:** this block adds one more typed continuity bridge in `DialogStateService` and should reuse the repo's existing Pydantic-based normalization seam instead of inventing another ad hoc dict sanitizer.
- **Sources opened (from this query):**
  - `Models` — `https://docs.pydantic.dev/latest/concepts/models/`
- **Source quality:** official Pydantic documentation.
- **Existing solutions found:** `model_validate(...)` plus `extra="forbid"` is the standard way to keep typed payload normalization fail-closed while reusing the existing model-based seam.
- **Decision:** `reuse + integrate` — keep the new `re_entry_required` bridge inside `DialogStateService` with typed normalization semantics that match the service's current role.
- **Rejected options:**
  - adding another standalone continuity helper module
  - widening into a full context-manager rewrite
  - touching frozen legacy semantic router files
- **Open questions:** none for this bounded continuity slice.

## Root cause (mandatory)
- **Symptom:** `re_entry_required` still has multiple writers and raw payload shape logic even after the recent continuity bridge cuts.
- **Minimal reproduction:**
  1. Inspect `_set_re_entry_required(...)` / `_clear_re_entry_required(...)` in `truffles-api/app/routers/webhook/context_manager.py` and see local payload construction.
  2. Inspect `restore_pending_resume_payload(...)` in `truffles-api/app/core/dialog_state_service.py` and see the same `re_entry_required` payload shape authored again.
  3. Search tests for `re_entry_required` and see both pending-resume restore and resolved-handoff resume flows depending on that shared shape.
- **Evidence to capture:**
  - `DialogStateService` owns typed `re_entry_required` normalization/set/clear helpers
  - `context_manager.py` delegates read/write helpers to that bridge instead of authoring the payload locally
  - existing restore/clear compatibility tests keep passing
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because `re_entry_required` payload shape is still authored in more than one place.
  2. Why is that wrong? Because `DialogState` is supposed to be the single continuity authority.
  3. Why choose `re_entry_required` now? Because it already crosses pending-resume restore and active question flows, so it removes another real split writer without touching frozen files.
  4. Why not collapse all remaining context-manager writers now? Because that would exceed a safe bounded cut.
  5. Why does this reduce drift? Because another live continuity carrier stops defining its own payload contract in multiple modules.
- **Root cause statement:** continuity ownership is still split because `re_entry_required` payload normalization and write semantics live both in `context_manager.py` and in dialog-state restore logic instead of flowing through one typed bridge.
- **Fix mechanism:**
  - add typed `re_entry_required` bridge helpers to `DialogStateService`
  - route `_get_re_entry_required(...)`, `_is_re_entry_required(...)`, `_set_re_entry_required(...)`, and `_clear_re_entry_required(...)` through that bridge
  - make `restore_pending_resume_payload(...)` reuse the same bridge helpers
  - run deterministic unit coverage plus existing restore/clear compatibility tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - existing `pending_resume` restore path in `truffles-api/app/services/state_service.py`
  - existing restore/clear tests in `truffles-api/tests/test_state_service.py` and `truffles-api/tests/test_message_endpoint.py`
- **External reuse:**
  - official Pydantic model docs for typed normalization pattern already used in the service layer
- **Why not reinvent the wheel:** the repo already has a typed dialog-state bridge; this block should extend that same seam rather than add another ad hoc continuity sanitizer.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `9`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration with compatibility-sensitive runtime behavior and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to externally visible `re_entry_required` payload shape for valid flows.
- No widening into generic `context_manager.py` cleanup.

## Scope
- Add typed `re_entry_required` bridge helpers to `DialogStateService`.
- Route context-manager `re_entry_required` read/write helpers through that bridge.
- Reuse the same bridge inside pending-resume restore.
- Add deterministic tests and run targeted compatibility checks.
- Sync source-of-truth/state/session docs.

## Out of scope
- full `context_manager.py` rewrite
- changing resolved-handoff boundary semantics
- frozen router edits
- broader continuity-writer guard tightening

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reentry-contract-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this continuity TP with RCA and one web search.
2. Add typed `re_entry_required` bridge helpers to `DialogStateService`.
3. Route `context_manager.py` read/write helpers through those bridge methods without changing legacy APIs.
4. Reuse the same bridge inside pending-resume restore and add deterministic unit coverage.
5. Run targeted compatibility tests, rerun deterministic suites/guards, and sync docs.

## DoD
- `DialogStateService` owns bounded `re_entry_required` normalization/set/clear semantics.
- `context_manager.py` no longer authors that payload shape directly.
- pending-resume restore reuses the same bridge.
- Existing restore/clear compatibility tests keep passing.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume or preserve_context_restores_pending_resume_snapshot'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary or provider_unavailable_human_request_pending_resume_skips_restore_without_booking_boundary'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` `re_entry_required` bridge helpers
- updated `context_manager.py` delegating `re_entry_required` semantics
- deterministic unit coverage plus targeted pending-resume/resolved-handoff tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or a broader state redesign, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** targeted restore/clear tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target the next remaining context-manager/state writer separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual `re_entry_required` bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new proof-path authority in tests.

## Risks/Blockers
- `re_entry_required` is read in multiple runtime paths, so payload-shape drift would break resume/clear boundaries.
- remaining context-manager/state writers will still exist after this cut.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: broader context-manager writer ownership and other continuity carriers still remain after this cut.
- `Why not in this block`: a full writer collapse would exceed a safe bounded migration.
- `Risk if deferred`: continuity still has multiple writers even though another shared carrier is centralized.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-context-manager-writer-collapse-a922`
- `Expiry/trigger to stop deferral`: before any new `re_entry_required` semantics or adjacent context-manager continuity fields are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the next remaining context-manager/state continuity writer after the `re_entry_required` bridge.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume' && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: `re_entry_required` still authored in multiple modules; source-of-truth not synced; targeted restore/clear tests absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated context-manager helpers
- `Open risks`: accidentally changing `re_entry_required` payload shape while centralizing the bridge
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary'`
