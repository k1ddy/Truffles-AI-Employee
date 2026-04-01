# TP-2026-03-15-consultant-core-confirmation-bridge-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONFIRMATION-BRIDGE-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-REENTRY-CONTRACT-BRIDGE-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reentry-contract-bridge-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTEXT-MANAGER-WRITER-COLLAPSE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity cut без изменения legacy happy-path semantics: confirmation-carriers (`handover_confirmation`, `reengage_confirmation`, `asr_confirmation`) перестают авториться и валидироваться ad hoc в `truffles-api/app/routers/webhook/context_manager.py` и начинают проходить через typed bridge в `truffles-api/app/core/dialog_state_service.py`.

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
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "handover_confirmation|reengage_confirmation|asr_confirmation|asked_at" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/guards.py truffles-api/app/routers/webhook/response.py`
  - `rg -n "reengage_confirmation|handover_confirmation|asr_confirm" truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_state_service.py`
- `FACT findings`:
  - `context_manager.py` still owns three nearly identical helper clusters: get/set/is_active for handover, reengage, and ASR confirmations.
  - Each cluster parses `asked_at` locally with `datetime.fromisoformat(...)` and window-specific TTL logic.
  - Payload shapes are stable and already bounded by live call sites: handover carries `status/trigger_type/trigger_value/user_message`, reengage carries `booking_messages`, ASR carries `transcript/attempt`.
  - Existing tests already pin reengage active/expiry behavior and handover clearing during pending-resume restore; the missing gap is centralized bridge ownership.
- `Detected drift (docs vs code)`: continuity bridge already owns several carriers, but confirmation-carriers still define their own payload parsing and liveness rules in router helper code.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org datetime fromisoformat python`
- **Date/time (local):** `2026-03-15 19:06 Asia/Almaty`
- **Why this query is precise:** this block centralizes confirmation-carrier liveness windows and must preserve the exact timestamp parsing semantics already used by runtime helpers.
- **Sources opened (from this query):**
  - `datetime — Basic date and time types` — `https://docs.python.org/3/library/datetime.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `datetime.fromisoformat(...)` is the standard parser for ISO strings; naive datetimes need explicit timezone attachment before delta comparison.
- **Decision:** `reuse + integrate` — keep timestamp parsing centralized in `DialogStateService` using the same `fromisoformat(...)` + UTC fallback semantics already used by router helpers.
- **Rejected options:**
  - introducing another timestamp parser/helper module
  - widening into a full context-manager rewrite
  - touching frozen legacy semantic router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** confirmation-carriers still have split normalization and liveness ownership in router helper code.
- **Minimal reproduction:**
  1. Inspect `_get/_set/_is_*_confirmation_active` helpers in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Notice three near-identical implementations for handover/reengage/ASR confirmation payloads.
  3. Compare that with the already-centralized continuity bridge patterns in `DialogStateService`.
- **Evidence to capture:**
  - `DialogStateService` owns typed normalize/set/is_active helpers for all three confirmation carriers.
  - `context_manager.py` delegates those helpers instead of authoring payload parsing locally.
  - existing confirmation compatibility tests keep passing.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because confirmation-carrier parsing/liveness rules still live in router helper code.
  2. Why is that wrong? Because `DialogState` is supposed to be the convergence point for continuity contracts.
  3. Why move these three together? Because they share the same `asked_at + TTL` pattern and can be centralized safely as one bounded slice.
  4. Why not widen into other expiring carriers now? Because that would exceed a safe bounded cut.
  5. Why does this reduce drift? Because three parallel helper branches collapse into one typed bridge surface.
- **Root cause statement:** continuity ownership is still split because handover/reengage/ASR confirmation carriers keep their own payload parsing and active-window semantics in `context_manager.py` instead of flowing through one dialog-state bridge.
- **Fix mechanism:**
  - add typed confirmation bridge helpers to `DialogStateService`
  - route `context_manager.py` get/set/is_active helpers through that bridge
  - add deterministic service coverage and reuse existing runtime compatibility tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - existing reengage confirmation tests in `truffles-api/tests/test_message_endpoint.py`
  - existing state-service pending restore test that already clears `handover_confirmation`
- **External reuse:**
  - official Python `datetime.fromisoformat(...)` docs
- **Why not reinvent the wheel:** the repo already has a continuity bridge and the router already uses one timestamp parsing pattern; this block should centralize that existing behavior, not replace it with a new protocol.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `9`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity bridge migration with narrow payload shapes and deterministic local checks.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to externally visible confirmation payload shape for valid flows.
- No widening into unrelated expiring carriers.

## Scope
- Add typed confirmation bridge helpers to `DialogStateService` for handover/reengage/ASR confirmation payloads.
- Route `context_manager.py` get/set/is_active helpers through that bridge.
- Add deterministic tests and run targeted compatibility checks.
- Sync source-of-truth/state/session docs.

## Out of scope
- full `context_manager.py` rewrite
- `asr_inflight` / `style_reference_pending` / `memory_*` carriers
- frozen router edits
- broader continuity-writer guard tightening

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-confirmation-bridge-slice-a922.md`
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
2. Add typed confirmation-carrier helpers to `DialogStateService`.
3. Route `context_manager.py` handover/reengage/ASR confirmation helpers through that bridge without changing legacy APIs.
4. Add deterministic unit coverage and run targeted compatibility checks.
5. Re-run deterministic suites/guards and sync docs.

## DoD
- `DialogStateService` owns bounded normalize/set/is_active semantics for `handover_confirmation`, `reengage_confirmation`, and `asr_confirmation`.
- `context_manager.py` no longer authors those payload/liveness rules directly.
- Existing confirmation compatibility tests keep passing.
- Deterministic tests and architecture/session guards are green.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'reengage_confirmation_active or reengage_confirmation_expires'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'preserve_context_restores_pending_resume_snapshot'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated `DialogStateService` confirmation bridge helpers
- updated `context_manager.py` delegating handover/reengage/ASR confirmation semantics
- deterministic unit coverage plus targeted reengage/state-service compatibility tests
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires frozen-router edits or broader expiring-carrier redesign, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity bridge only
- **Go/no-go signals:** confirmation bridge tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's continuity/doc/test changes only
- **Post-release monitoring window:** next continuity block should target the next remaining expiring/state carrier separately

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual confirmation bridge slice being executed.

## Rollback
- Revert this TP's `DialogStateService`, `context_manager.py`, test, and doc changes; keep already-landed governance/proof/continuity blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new proof-path authority in tests.

## Risks/Blockers
- confirmation payloads have different optional keys, so over-normalization could silently drop needed fields.
- remaining expiring/state carriers will still exist after this cut.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: remaining expiring carriers (`asr_inflight`, `style_reference_pending`, `memory_*`) and broader context-manager writer ownership remain.
- `Why not in this block`: that would exceed a safe bounded migration.
- `Risk if deferred`: continuity still has multiple helper-owned carriers even after this bridge.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-expiring-carrier-bridge-slice-a922`
- `Expiry/trigger to stop deferral`: before any new confirmation-carrier semantics or adjacent expiring carriers are added outside `DialogStateService`.

## Next-block contract (mandatory)
- `Next block objective`: collapse the next remaining expiring/state carrier after the confirmation bridge.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_dialog_state_service.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: confirmation-carrier parsing/liveness still authored in `context_manager.py`; source-of-truth not synced; targeted compatibility tests absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and unrelated expiring carriers
- `Open risks`: accidentally dropping optional payload keys while centralizing confirmation-carrier normalization
- `First command to verify`: `pytest -q truffles-api/tests/test_message_endpoint.py -k 'reengage_confirmation_active'`
