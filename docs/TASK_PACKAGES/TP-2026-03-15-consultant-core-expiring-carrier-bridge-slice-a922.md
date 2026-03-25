# TP-2026-03-15-consultant-core-expiring-carrier-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-EXPIRING-CARRIER-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONFIRMATION-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-confirmation-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-MANAGER-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: expiring carriers (`asr_inflight`, `style_reference_pending`) перестают авториться и истекать ad hoc в `truffles-api/app/routers/webhook/context_manager.py` и начинают проходить через typed bridge в `truffles-api/app/core/dialog_state_service.py`.

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
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "_get_asr_inflight|_set_asr_inflight|_get_style_reference_pending|_set_style_reference_pending|expires_at" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/decision.py truffles-api/app/services/state_service.py`
  - `rg -n "asr_inflight|style_reference_pending" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_state_service.py`
- `FACT findings`:
  - `context_manager.py` still owns two expiring-carrier helper clusters built around `expires_at` parsing.
  - `asr_inflight` is a small TTL carrier with `started_at`/`expires_at`; `style_reference_pending` is a richer TTL carrier with nested media payload and storage/public URL metadata.
  - Existing runtime tests already pin both lanes: audio inflight blocking in `test_message_endpoint.py` and style-reference media handoff binding in `test_state_service.py`.
  - These carriers are continuity/runtime state, but their normalize/expire rules still bypass `DialogStateService`.
- `Detected drift (docs vs code)`: continuity bridge already owns several carriers, but expiring-carrier parsing and expiry decisions still live in router helper code.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org library copy deepcopy python`
- **Date/time (local):** `2026-03-15 19:12 Asia/Almaty`
- **Why this query is precise:** `style_reference_pending` carries nested media payload and storage metadata, so the bridge must avoid aliasing nested mutable state while preserving compatibility.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3.9/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard way to detach nested mutable structures so bridge normalization cannot accidentally share later mutations with the original payload.
- **Decision:** `reuse + integrate` — use the existing dialog-state bridge and apply `deepcopy(...)` where nested expiring payloads need isolation.
- **Rejected options:**
  - introducing another expiring-payload helper module
  - widening into a full context-manager rewrite
  - touching frozen legacy semantic router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** expiring-carriers still have split normalization and expiry ownership in router helper code.
- **Minimal reproduction:**
  1. Inspect `_get/_set_asr_inflight(...)` and `_get/_set_style_reference_pending(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Notice local `expires_at` parsing and direct payload passthrough in both carriers.
  3. Compare that with already-centralized continuity bridge patterns in `DialogStateService`.
- **Evidence to capture:**
  - `DialogStateService` owns typed normalize/get-active/set semantics for both expiring carriers.
  - `context_manager.py` delegates those helpers instead of parsing expiry locally.
  - existing inflight/style-reference compatibility tests keep passing.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because expiring-carrier normalize/expire logic still lives in router helper code.
  2. Why is that wrong? Because `DialogState` is supposed to be the convergence point for continuity contracts.
  3. Why move these two together? Because both share the same `expires_at` lifecycle pattern and can be centralized safely as one bounded slice.
  4. Why not widen into `memory_*` carriers now? Because that would exceed a safe bounded cut.
  5. Why does this reduce drift? Because another pair of helper-owned continuity carriers stops defining its own expiry semantics.
- **Root cause statement:** continuity ownership is still split because `asr_inflight` and `style_reference_pending` keep their own payload/expiry rules in `context_manager.py` instead of flowing through one dialog-state bridge.
- **Fix mechanism:**
  - add typed expiring-carrier bridge helpers to `DialogStateService`
  - route `context_manager.py` get/set helpers through that bridge
  - add deterministic service coverage and reuse existing runtime compatibility tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - existing `test_asr_inflight_blocks_new_audio` in `truffles-api/tests/test_message_endpoint.py`
  - existing `style_reference_pending` handoff binding test in `truffles-api/tests/test_state_service.py`
- **External reuse:**
  - official Python `copy.deepcopy(...)` docs for nested payload isolation
- **Why not reinvent the wheel:** the repo already has a continuity bridge and a standard nested-copy primitive; this block should centralize existing behavior, not invent another expiring-state protocol.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `9`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration with nested payload compatibility and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to externally visible expiring payload shape for valid flows.
- No widening into `memory_*` carriers.

## Scope
- Add typed expiring-carrier helpers to `DialogStateService` for `asr_inflight` and `style_reference_pending`.
- Route `context_manager.py` get/set helpers through that bridge.
- Add deterministic tests and run targeted compatibility checks.
- Sync source-of-truth/state/session docs.

## Out of scope
- full `context_manager.py` rewrite
- `memory_profile` / `memory_pending`
- frozen router edits
- broader continuity-writer guard tightening

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-expiring-carrier-bridge-slice-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STRUCTURE.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`

## Plan (1..N)
1. Publish this continuity TP with RCA and one web search.
2. Add typed expiring-carrier helpers to `DialogStateService`.
3. Route `context_manager.py` `asr_inflight` and `style_reference_pending` helpers through that bridge without changing legacy APIs.
4. Add deterministic unit coverage and run targeted compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded normalize/get-active/set semantics for `asr_inflight` and `style_reference_pending`.
- `context_manager.py` no longer authors those payload/expiry rules directly.
- Existing expiring-carrier compatibility tests keep passing.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'asr_inflight_blocks_new_audio'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'style_reference_pending'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` expiring-carrier bridge helpers
- updated `context_manager.py` delegating `asr_inflight` and `style_reference_pending` semantics
- deterministic unit coverage plus targeted inflight/style-reference tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or broader expiring-carrier redesign, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** expiring-carrier bridge tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target the remaining `memory_*` carriers separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual expiring-carrier bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new proof-path authority in tests.

## Risks/Blockers
- `style_reference_pending` carries nested media payload and URL metadata, so over-normalization could silently drop fields.
- remaining `memory_*` carriers will still exist after this cut.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: remaining `memory_profile` / `memory_pending` carriers and broader context-manager writer ownership remain.
- `Why not in this block`: that would exceed a safe bounded migration.
- `Risk if deferred`: continuity still has helper-owned expiring carriers even after this bridge.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-memory-carrier-bridge-slice-a922`
- `Expiry/trigger to stop deferral`: before any new expiring-carrier semantics are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the remaining `memory_*` carriers after the expiring-carrier bridge.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: expiring-carrier parsing/expiry still authored in `context_manager.py`; source-of-truth not synced; targeted compatibility tests absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated `memory_*` carriers
- `Open risks`: accidentally dropping nested style-reference media fields while centralizing the bridge
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'asr_inflight_blocks_new_audio'`
