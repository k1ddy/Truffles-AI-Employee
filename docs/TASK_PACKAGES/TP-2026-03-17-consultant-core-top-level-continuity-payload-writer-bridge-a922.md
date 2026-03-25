# TP-2026-03-17-consultant-core-top-level-continuity-payload-writer-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-TOP-LEVEL-CONTINUITY-PAYLOAD-WRITER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-SERVICE-NOT-FOUND-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-service-not-found-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-FINAL-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded live continuity writer seam: top-level `session_memory` и `re_entry_required` payload writes больше не должны жить в `truffles-api/app/routers/webhook/session_memory.py` и `truffles-api/app/routers/webhook/context_manager.py`. `DialogStateService` должен стать owner-ом этих top-level context payload setters, а legacy helpers должны остаться thin delegation layer.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-carryover-reset-bridge-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-question-contract-writer-bridge-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-service-not-found-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "context\[legacy\.SESSION_MEMORY_KEY\]|context\.pop\(legacy\.SESSION_MEMORY_KEY|context\[legacy\.RE_ENTRY_REQUIRED_KEY\]" truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '29,60p' truffles-api/app/routers/webhook/session_memory.py`
  - `sed -n '434,463p' truffles-api/app/routers/webhook/context_manager.py`
  - `rg -n "_set_optional_context_payload|set_re_entry_required|clear_re_entry_required|normalize_session_memory_payload" truffles-api/app/core/dialog_state_service.py`
  - `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'session_memory_normalization or re_entry_required'`
- `FACT findings`:
  - `DialogStateService` already has reusable `_set_optional_context_payload(...)` and owns payload shaping for many top-level continuity carriers.
  - `truffles-api/app/routers/webhook/session_memory.py` still directly writes/removes `context[SESSION_MEMORY_KEY]`.
  - `truffles-api/app/routers/webhook/context_manager.py` still directly writes `context[RE_ENTRY_REQUIRED_KEY]` even though `DialogStateService` already owns re-entry payload shaping.
- `Detected drift (docs vs code)`: continuity cutover claims `re_entry` and session-memory families as migrated, but top-level payload write authority is still split across legacy wrappers.

## One web search (mandatory before implementation)
- **Query (exact):** `Python copy.deepcopy official docs`
- **Date/time (local):** `2026-03-17 08:21 +0500`
- **Why this query is precise:** the remaining seam is about top-level payload write ownership with detached nested copy semantics; this block must keep the current no-aliasing behavior when moving the setter into `DialogStateService`.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy()` is the standard-library mechanism for recursive detached copy semantics on nested mutable payloads.
- **Decision:** `reuse + integrate` — reuse the existing `_set_optional_context_payload(...)` service helper, keep deep-copy behavior centralized in `DialogStateService`, and delete the remaining direct top-level writes from legacy wrappers.
- **Rejected options:**
  - leaving `session_memory.py` and `context_manager.py` as top-level payload writers
  - widening this block into broader restore/state-boundary orchestration
  - touching frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** top-level continuity payload writes for `session_memory` and `re_entry_required` still live in legacy webhook helpers instead of the declared continuity owner.
- **Minimal reproduction:**
  1. Inspect `_set_session_memory(...)` in `truffles-api/app/routers/webhook/session_memory.py`.
  2. Inspect `_set_re_entry_required(...)` / `_clear_re_entry_required(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  3. Observe that both helpers still mutate `context[...]` directly even though `DialogStateService` already owns payload shaping and deep-copy helpers.
- **Evidence to capture:**
  - new service-owned top-level setters preserve detached nested copies
  - legacy wrappers lose direct `context[...] = ...` / `context.pop(...)` authority for these payloads
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because some top-level payload writes stayed in legacy wrappers after payload shaping moved into the service.
  2. Why does that matter? Because a live writer seam still exists outside `DialogStateService`.
  3. Why is this block bounded? Because it only targets the top-level `session_memory` and `re_entry_required` payload setters.
  4. Why not widen further? Because broader manager envelope and trace/restore semantics are separate seams with different risk.
  5. Why fix this now? Because it deletes another real continuity writer without adding any semantic bridge growth.
- **Root cause statement:** continuity ownership is still split because top-level `session_memory` and `re_entry_required` writes remained inline in legacy webhook helpers instead of being routed through the service-owned context payload setter seam.
- **Fix mechanism:**
  - add service-owned top-level context setter helpers for `session_memory` and `re_entry_required`
  - delegate legacy wrappers to those helpers
  - prove detached-copy and clear semantics with focused dialog-state tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `_set_optional_context_payload(...)` in `DialogStateService`
  - existing `set_re_entry_required(...)` / `clear_re_entry_required(...)`
  - existing session-memory normalization and freshness helpers
  - existing dialog-state tests for context payload setters
- **External reuse:**
  - official Python `copy.deepcopy` documentation
- **Why not reinvent the wheel:** this block only centralizes two remaining top-level payload writers through the service-owned setter mechanism that already exists.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded continuity-writer deletion plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Top-level payload write semantics stay externally compatible, including detached nested copies and missing-key-safe clears.
- This block must not widen into broader restore or manager-envelope orchestration.

## Scope
- Add service-owned top-level context setter for `session_memory`.
- Add service-owned top-level context setters for `re_entry_required` set/clear payloads.
- Delegate legacy wrappers in `session_memory.py` and `context_manager.py` to those helpers.
- Add focused dialog-state regression coverage.
- Sync canon/session artifacts.

## Out of scope
- broader `context_manager` manager-envelope ownership
- `message_count` shaping
- trace merge/retention
- frozen legacy semantic files
- new planner/semantic owner cutovers
- proof-path work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-top-level-continuity-payload-writer-bridge-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish this TP with RCA and the required single web search.
2. Add service-owned top-level context setter helpers for `session_memory` and `re_entry_required`.
3. Replace the remaining direct legacy wrapper writes with service delegation.
4. Add focused dialog-state tests for detached-copy and clear semantics.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns top-level context write/remove semantics for `session_memory` and `re_entry_required`.
- `session_memory.py` and `context_manager.py` no longer directly own those top-level payload writes.
- tests prove detached nested copy behavior and clear semantics are preserved.
- no frozen-router edits and no new bridge families are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- dialog-state regression tests covering service-owned top-level setters for `session_memory` and `re_entry_required`
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** dialog-state + contracts + architecture only for this bounded block
- **Stop condition:** if the block starts requiring broader restore/state-boundary changes, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + contracts + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service setters, wrapper delegation, tests, and doc sync
- **Post-release monitoring window:** next block should either finish the single-writer audit or return to broader owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the top-level continuity payload writer bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` setters, wrapper delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader restore/state-boundary orchestration
- no counting this block as done unless the remaining direct top-level `session_memory` and `re_entry_required` writes are deleted from legacy wrappers

## Risks / blockers
- if setter semantics accidentally normalize more than before, legacy wrappers could change behavior outside the bounded writer seam
- if detached-copy semantics drift, nested payload aliasing could leak between callers and stored context

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity ownership still remains around manager envelope, trace merge, and restore semantics
  - richer semantic owner slices still remain in legacy `decision.py`
  - boundary owner is still partial
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes two remaining top-level continuity payload writers; broader restore and manager-envelope ownership is a separate seam
- **Risk if deferred:**
  - split payload-write authority would continue to block honest single-writer closure and keep legacy wrappers as live continuity owners
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-single-continuity-writer-final-audit-a922` (to be authored if the remaining seams stay bounded)
- **Expiry/trigger to stop deferral:**
  - if another continuity block would need new local `context[...]` / `manager[...]` writes outside `DialogStateService`, stop and audit remaining writers first

## Next-block contract (mandatory)
- **Next block objective:** determine whether a final bounded continuity-writer deletion still exists after this top-level payload bridge, otherwise switch back to broader owner-replacement or boundary-owner cutover
- **First deterministic check command:** `rg -n "context\[[^]]+\] =|context\.pop\(|manager\[[^]]+\] =|manager\.pop\(" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py`
- **Blocked-by conditions:** if the remaining writes are only trace-retention or broader manager-envelope orchestration, do not force another continuity micro-bridge
- **Owner role for closure:** `Top Architect`
