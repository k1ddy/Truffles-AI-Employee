# TP-2026-03-16-consultant-core-ancillary-context-carrier-writer-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ANCILLARY-CONTEXT-CARRIER-WRITER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-FRESHNESS-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после session-memory freshness bridge: top-level context-carrier shaping for confirmations, ASR/style pending carriers, and memory carriers must stop living in `truffles-api/app/routers/webhook/context_manager.py`. `DialogStateService` should become the owner of context set/pop semantics for these normalized payloads, while `context_manager.py` stays a thin orchestration layer around key lookup and legacy compatibility helpers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

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
  - `sed -n '1140,1365p' truffles-api/app/routers/webhook/context_manager.py`
  - `rg -n "handover_confirmation|reengage_confirmation|asr_confirmation|asr_inflight|style_reference_pending|memory_profile|memory_pending" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_asr_inflight_blocks_new_audio or test_style_reference_sets_pending or test_handover_confirmation_active or test_reengage_confirmation_active'`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns normalization/get/set for `handover_confirmation`, `reengage_confirmation`, `asr_confirmation`, `asr_inflight`, `style_reference_pending`, `memory_profile`, and `memory_pending` payload bodies.
  - `context_manager.py` still owns the top-level context mutation semantics for those same live carriers via repeated `context[key]=normalized` / `context.pop(key, None)` branches.
  - This seam is bounded: it only concerns top-level context carrier write/delete semantics and existing getter/expiry semantics already remain in `DialogStateService`.
- `Detected drift (docs vs code)`: single continuity writer completion is still blocked by these remaining context-manager live writers.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy official documentation`
- **Date/time (local):** `2026-03-16 22:14 +0500`
- **Why this query is precise:** the block moves top-level context payload ownership into `DialogStateService` and must preserve detached-copy semantics for nested confirmation/style/memory carriers.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy` remains the correct baseline for preserving isolated nested payloads while moving write ownership.
- **Decision:** `reuse + integrate` — preserve the existing detached-copy behavior while relocating top-level context write authority into `DialogStateService`.
- **Rejected options:**
  - leaving the context key set/pop logic in `context_manager.py`
  - widening this block into broader restore/reset/state-boundary semantics
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `context_manager.py` still owns top-level write/delete semantics for several normalized live carriers, so `DialogStateService` is not yet the single continuity writer for those seams.
- **Minimal reproduction:**
  1. Call `_set_handover_confirmation(...)`, `_set_asr_inflight(...)`, `_set_style_reference_pending(...)`, or `_set_memory_profile(...)` in `context_manager.py`.
  2. Observe that `DialogStateService` only normalizes the payload body, while `context_manager.py` still decides whether and how the key is written or removed from the context.
  3. Compare with newer continuity bridges where `DialogStateService` owns both shaping and top-level projection semantics.
- **Evidence to capture:**
  - `DialogStateService` directly owns context write/remove behavior for these carriers.
  - `context_manager.py` becomes a thin wrapper around legacy key names and getter/expiry helpers.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because normalized payload bodies moved, but key-level context mutation stayed local.
  2. Why is that a problem? Because live continuity state still has two write authorities for the same carrier family.
  3. Why is this bounded? Because the affected helpers only set or clear one top-level context key at a time.
  4. Why not widen into restore/reset logic? Because reset/state-boundary semantics are a separate riskier seam.
  5. Why fix this now? Because it deletes multiple remaining live continuity writers without adding any new semantic bridge.
- **Root cause statement:** `context_manager.py` still decides how normalized confirmation/ASR/style/memory carriers are written to or deleted from the live context, so `DialogStateService` is not yet the sole writer for those continuity seams.
- **Fix mechanism:**
  - add bounded context write/remove helpers to `DialogStateService` for the affected carriers
  - replace local set/pop logic in `context_manager.py` with thin delegation
  - prove parity with focused service tests and targeted endpoint compatibility checks

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing payload normalizers/setters in `DialogStateService`
  - existing context-manager getters and active-window readers
  - existing dialog-state tests for carrier normalization and detached copies
- **External reuse:**
  - official Python `copy.deepcopy` semantics from the standard library docs
- **Why not reinvent the wheel:** this is continuity-owner consolidation, not a new carrier model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded continuity-writer deletion across a closely related carrier family plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- External confirmation/ASR/style/memory carrier payload semantics stay unchanged.
- Detached-copy semantics stay unchanged for nested payloads.

## Scope
- Add bounded top-level context write/remove helpers to `DialogStateService` for confirmations, ASR/style pending carriers, and memory carriers.
- Make `context_manager.py` delegate those top-level writer seams.
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
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ancillary-context-carrier-writer-bridge-a922.md`
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
2. Add bounded context write/remove helpers to `DialogStateService` for the targeted carrier family.
3. Replace local key set/pop logic in `context_manager.py` with thin delegation.
4. Add focused dialog-state tests and rerun targeted endpoint compatibility checks.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns top-level context write/remove behavior for the targeted confirmation/ASR/style/memory carriers.
- `context_manager.py` stays orchestration-only for those seams.
- tests prove parity for detached-copy and key-removal semantics.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'test_asr_inflight_blocks_new_audio or test_style_reference_sets_pending or test_handover_confirmation_active or test_reengage_confirmation_active'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- dialog-state unit tests showing service-owned top-level writer behavior for these carriers
- targeted endpoint checks showing ASR/style/confirmation compatibility remains unchanged
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
  - active block metadata must match the ancillary context-carrier writer bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, context-manager delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader restore/reset/state-boundary orchestration
- no counting this block as done unless `context_manager.py` loses local write/delete authority for the targeted carrier family

## Risks / blockers
- if the helper changes key-removal semantics, stale carrier payloads can survive longer than before.
- if detached-copy behavior regresses, nested payload mutation bugs can leak into live context.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers still remain outside this carrier family
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded context-writer slice; widening further would mix top-level carrier writes with reset/restore orchestration
- **Risk if deferred:**
  - continuity would keep split write authority for these carriers and make final single-writer closure harder
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - stop deferral once the next bounded live writer can be removed without widening into broader state-boundary semantics

## Next-block contract (mandatory)
- **Next block objective:** either remove the next remaining bounded continuity writer seam, or return to a direct owner-replacement cutover if no safe writer-collapse slice remains
- **First deterministic check command:** `rg -n "def _set_|def _update_|def _clear_" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py`
- **Blocked-by conditions:** block if the next seam requires frozen-router edits, new generic bridge families, or broader reset/restore semantics
- **Owner role for closure:** `Top Architect`
