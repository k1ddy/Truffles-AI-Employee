# TP-2026-03-16-consultant-core-session-memory-carryover-reset-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-CARRYOVER-RESET-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CARRYOVER-MANAGER-WRITER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-carryover-manager-writer-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после carryover-manager writer bridge: `_reset_session_memory(...)` в `truffles-api/app/routers/webhook/session_memory.py` не должен напрямую владеть delete semantics для carryover family. `DialogStateService` должен стать owner-ом reset-time clear behavior для `class_carryover`, `service_carryover`, `consult_context` и их canonical mirrors, а `session_memory.py` должен остаться thin orchestration layer.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-carryover-manager-writer-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '143,185p' truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "_reset_session_memory|class_carryover|service_carryover|consult_context" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/tests/test_dialog_state_service.py`
  - `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'context_manager_class_carryover or context_manager_service_carryover or context_manager_consult_context or sync_session_memory_interaction_state'`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns manager write/delete semantics for the carryover family in `context_manager.py`.
  - `_reset_session_memory(...)` still directly deletes `class_carryover`, `service_carryover`, and `consult_context` from the manager payload.
  - Because legacy readers now project from canonical state too, this reset seam must be centralized in the same service owner to avoid split delete authority.
- `Detected drift (docs vs code)`: single continuity writer is still blocked by carryover reset-time delete authority living in `session_memory.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dict pop method documentation site:python.org`
- **Date/time (local):** `2026-03-16 23:18 +0500`
- **Why this query is precise:** the remaining seam is a direct `manager.pop(..., None)` delete path; the block needs official semantics for safe keyed deletion while relocating that authority into `DialogStateService`.
- **Sources opened (from this query):**
  - `Built-in Types — dict.pop` — `https://docs.python.org/3/library/stdtypes.html#dict.pop`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dict.pop(key, default)` is the correct missing-key-safe delete primitive; the block should reuse that semantics behind service-owned helpers rather than keeping inline deletes in `session_memory.py`.
- **Decision:** `reuse + integrate` — move the keyed delete behavior into `DialogStateService`, keep the reset wrapper thin, and preserve the current missing-key-safe semantics.
- **Rejected options:**
  - leaving direct carryover-family deletes in `session_memory.py`
  - widening this block into broader booking/reset/state-boundary semantics
  - touching frozen `decision.py` / `booking.py` / `pending.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `_reset_session_memory(...)` still directly deletes carryover-family keys from the manager payload, so continuity delete ownership remains split between `DialogStateService` and `session_memory.py`.
- **Minimal reproduction:**
  1. Inspect `_reset_session_memory(...)` in `truffles-api/app/routers/webhook/session_memory.py`.
  2. Observe direct `manager.pop(..., None)` calls for class/service/consult carryover keys.
  3. Compare with the already centralized carryover writer behavior in `DialogStateService`.
- **Evidence to capture:**
  - service-owned reset helper clears the same family from both legacy manager keys and canonical state
  - `session_memory.py` becomes a thin delegator for this seam
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because reset-time deletes stayed local after normal manager writers were centralized.
  2. Why does that matter? Because carryover-family clear behavior now has two owners.
  3. Why is this bounded? Because it only affects the carryover family inside `_reset_session_memory(...)`.
  4. Why not widen further? Because broader reset/restore semantics would mix this block with booking-state and boundary behavior.
  5. Why fix this now? Because it deletes one more real live writer seam without adding any semantic bridge.
- **Root cause statement:** carryover-family reset deletes were left inline in `session_memory.py`, so `DialogStateService` is not yet the sole owner for that live continuity delete seam.
- **Fix mechanism:**
  - add a bounded carryover-family reset helper to `DialogStateService`
  - delegate `_reset_session_memory(...)` to that helper
  - prove parity with focused dialog-state tests, including canonical-state clearing

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing carryover-family helpers already centralized in `DialogStateService`
  - existing session-memory reset wrapper in `session_memory.py`
  - existing dialog-state tests for carryover and session-memory seams
- **External reuse:**
  - official Python `dict.pop` semantics from the standard library docs
- **Why not reinvent the wheel:** this block only deletes a remaining live writer seam; it does not introduce a new carryover model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded continuity-writer deletion plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Session-memory reset behavior stays externally compatible except for removing the split delete authority.
- Carryover-family reset must stay missing-key-safe.

## Scope
- Add bounded carryover-family reset helper to `DialogStateService`.
- Make `_reset_session_memory(...)` delegate carryover-family deletes to the service.
- Add regression tests for service-owned reset clearing and the session-memory reset wrapper.
- Sync canon/session artifacts.

## Out of scope
- broader reset/restore/state-boundary orchestration
- booking-state semantics beyond the existing reset wrapper
- frozen legacy semantic files
- new semantic owner cutovers
- proof-path rewrite

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-carryover-reset-bridge-a922.md`
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
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add a bounded carryover-family reset helper to `DialogStateService`.
3. Replace local deletes in `_reset_session_memory(...)` with service delegation.
4. Add focused dialog-state tests for service-owned carryover-family reset and wrapper behavior.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns carryover-family reset deletes for `_reset_session_memory(...)`.
- `session_memory.py` no longer directly owns carryover-family delete semantics.
- tests prove canonical carryover state is cleared through the service-owned reset path.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_service_carryover_applies_for_pricing or test_legacy_service_carryover_reads_from_canonical_dialog_state or test_legacy_class_carryover_reads_from_canonical_dialog_state or test_legacy_consult_context_reads_from_canonical_dialog_state'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/tests/test_dialog_state_service.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- dialog-state unit tests showing service-owned carryover-family reset behavior
- targeted compatibility tests showing carryover readers still project correctly from canonical state
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + targeted compatibility + architecture only for this bounded block
- **Stop condition:** if this slice requires broader reset/restore widening or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + targeted compatibility + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helper, session-memory delegation, tests, and doc sync
- **Post-release monitoring window:** next block should either finish the continuity-writer audit or return to owner-replacement cutover without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the session-memory carryover reset bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helper, session-memory delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader reset/restore/state-boundary orchestration
- no counting this block as done unless `_reset_session_memory(...)` loses local carryover-family delete authority

## Risks / blockers
- if canonical carryover clearing drifts, legacy readers can still see stale projections after reset.
- if reset wrapper semantics drift, booking reset behavior can change outside the intended bounded slice.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers may still remain outside this carryover-family reset seam
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the remaining bounded carryover-family reset writer; broader restore/state-boundary work is a separate seam
- **Risk if deferred:**
  - split reset delete authority would continue to leak stale carryover state and block single-writer closure
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-single-continuity-writer-audit-a922` (to be authored if the audit remains bounded)
  - otherwise the next owner-replacement TP after continuity audit
- **Expiry/trigger to stop deferral:**
  - stop deferral if another live writer is found in `context_manager.py` or `session_memory.py` for the same carryover family after this block

## Next-block contract (mandatory)
- **Next block objective:** audit whether any bounded live continuity writer remains after this reset seam; if none remain, return to richer owner-replacement cutover
- **First deterministic check command:** `rg -n "class_carryover|service_carryover|consult_context|manager\.pop|\[legacy\.(CLASS_CARRYOVER_KEY|SERVICE_CARRYOVER_KEY|CONSULT_CONTEXT_KEY)\]" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/core/dialog_state_service.py`
- **Blocked-by conditions:** if the next residual seam widens into broader restore/state-boundary semantics, do not force another continuity micro-bridge
- **Owner role for closure:** `Top Architect`
