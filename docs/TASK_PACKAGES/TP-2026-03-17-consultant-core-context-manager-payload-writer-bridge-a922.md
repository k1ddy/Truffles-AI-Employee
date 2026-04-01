# TP-2026-03-17-consultant-core-context-manager-payload-writer-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTEXT-MANAGER-PAYLOAD-WRITER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TOP-LEVEL-CONTINUITY-PAYLOAD-WRITER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-top-level-continuity-payload-writer-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-FINAL-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Удалить следующий bounded continuity writer seam: `truffles-api/app/routers/webhook/context_manager.py` больше не должен напрямую владеть top-level `context_manager` payload write и `message_count` bump semantics. `DialogStateService` должен стать owner-ом этих двух операций, а legacy helper должен остаться thin delegation layer.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-top-level-continuity-payload-writer-bridge-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_dialog_state_service.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "context\[legacy\.CONTEXT_MANAGER_KEY\]|manager\[\"message_count\"\]" truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '568,584p' truffles-api/app/routers/webhook/context_manager.py`
  - `rg -n "_canonical_int|_set_optional_context_payload|context_manager" truffles-api/app/core/dialog_state_service.py`
  - `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'context_manager'`
- `FACT findings`:
  - `DialogStateService` already owns many `context_manager` nested writer/prune semantics and already has `_set_optional_context_payload(...)` plus `_canonical_int(...)`.
  - `context_manager.py` still directly writes `context[CONTEXT_MANAGER_KEY] = manager`.
  - `context_manager.py` still directly bumps `manager["message_count"]` with local int-coercion logic.
- `Detected drift (docs vs code)`: continuity cutover claims `context_manager`-owned state is increasingly centralized, but the top-level manager payload setter and message-count bump still live in the legacy wrapper.

## One web search (mandatory before implementation)
- **Query (exact):** `Python int built-in function official docs`
- **Date/time (local):** `2026-03-17 08:24 +0500`
- **Why this query is precise:** the remaining bounded seam includes the `message_count` bump and its current local integer coercion; this block must keep the same missing/invalid-value-safe `int(...)` behavior when moving the operation into `DialogStateService`.
- **Sources opened (from this query):**
  - `Built-in Functions — int()` — `https://docs.python.org/3/library/functions.html#int`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `int(value)` with `TypeError`/`ValueError` handling is the standard-library normalization primitive for integer coercion; the block should reuse the existing service-side `_canonical_int(...)` wrapper instead of keeping local coercion in the legacy helper.
- **Decision:** `reuse + integrate` — move the top-level manager setter and message-count increment into `DialogStateService`, reusing `_set_optional_context_payload(...)` and `_canonical_int(...)`.
- **Rejected options:**
  - leaving local `message_count` coercion in `context_manager.py`
  - widening into trace merge or simulation retention semantics
  - touching frozen router files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** `context_manager.py` still directly owns top-level manager payload writes and the `message_count` increment despite `DialogStateService` already owning most `context_manager` shaping semantics.
- **Minimal reproduction:**
  1. Inspect `_set_context_manager(...)` in `truffles-api/app/routers/webhook/context_manager.py`.
  2. Inspect `_increment_context_message_count(...)` in the same file.
  3. Observe direct `context[...] = ...` and `manager["message_count"] = ...` writes outside `DialogStateService`.
- **Evidence to capture:**
  - service-owned setter preserves detached nested copies for `context_manager`
  - service-owned increment preserves safe integer coercion and non-negative bump behavior
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented? Because the legacy wrapper still owns two live top-level manager write operations.
  2. Why does that matter? Because single-writer closure is still false while these writes remain outside `DialogStateService`.
  3. Why is this block bounded? Because it only targets `context_manager` top-level set and `message_count` bump.
  4. Why not widen further? Because trace merge and simulation retention are broader restore/observability seams, not simple continuity writer deletions.
  5. Why fix this now? Because it deletes another real writer without introducing any semantic bridge growth.
- **Root cause statement:** `context_manager.py` retained the generic manager payload setter and message-count bump after nested continuity shaping moved into `DialogStateService`, so write authority is still split for this bounded manager seam.
- **Fix mechanism:**
  - add service-owned top-level `context_manager` setter and message-count increment helpers
  - delegate legacy wrappers to those helpers
  - verify detached-copy and increment parity with focused tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_set_optional_context_payload(...)`
  - `_canonical_int(...)`
  - existing `DialogStateService` manager-related helpers
- **External reuse:**
  - official Python `int()` documentation
- **Why not reinvent the wheel:** this block only centralizes remaining writer operations through service helpers that already match the rest of the continuity architecture.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** one bounded continuity-writer deletion plus required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- `context_manager` payload writes must keep detached-copy semantics.
- `message_count` increment must stay invalid-value-safe and non-negative.

## Scope
- Add service-owned top-level `context_manager` payload setter.
- Add service-owned `message_count` increment helper.
- Delegate `_set_context_manager(...)` and `_increment_context_message_count(...)` through the service.
- Add focused dialog-state tests.
- Sync canon/session artifacts.

## Out of scope
- decision-trace merge/retention
- simulation field preservation
- broader restore/state-boundary orchestration
- frozen legacy semantic files
- new planner/semantic owner cutovers

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-context-manager-payload-writer-bridge-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
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
2. Add service-owned top-level `context_manager` setter and `message_count` increment helpers.
3. Replace the remaining direct legacy writes with service delegation.
4. Add focused dialog-state regression tests for detached-copy and increment semantics.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns top-level `context_manager` write/remove semantics.
- `DialogStateService` owns `message_count` increment semantics.
- `context_manager.py` no longer directly performs those two write operations.
- tests prove detached-copy and increment parity.
- no frozen-router edits and no new bridge families are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- dialog-state regression tests covering service-owned `context_manager` setter and `message_count` bump
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** dialog-state + contracts + architecture only for this bounded block
- **Stop condition:** if the next remaining continuity seam is only trace/restore semantics, stop continuity micro-bridges and switch back to richer owner replacement or boundary cutover
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + contracts + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helpers, wrapper delegation, tests, and doc sync
- **Post-release monitoring window:** next block should be a final writer audit or a switch back to broader owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the context-manager payload writer bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, wrapper delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into trace merge, simulation retention, or broader restore/state-boundary orchestration
- no counting this block as done unless the direct `context_manager` setter and `message_count` bump are deleted from the legacy wrapper

## Risks / blockers
- if detached-copy semantics drift, nested manager payload aliasing could leak between callers and stored context
- if integer coercion drifts, invalid stored `message_count` values could change behavior in follow-up TTL logic

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity ownership still remains around trace merge and restore semantics
  - richer semantic owner slices still remain in legacy `decision.py`
  - boundary owner is still partial
  - proof path is still not fully black-box
- **Why not in this block:**
  - this block only deletes the bounded manager payload setter and counter bump; trace and restore semantics are separate seams
- **Risk if deferred:**
  - legacy `context_manager.py` would remain a live writer for another manager family and keep single-writer closure dishonest
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-17-consultant-core-single-continuity-writer-final-audit-a922` (to be authored if remaining seams stay bounded)
- **Expiry/trigger to stop deferral:**
  - if the remaining continuity writes are only trace/restore semantics, stop micro-bridge work and switch block type

## Next-block contract (mandatory)
- **Next block objective:** determine whether a final bounded continuity writer still exists after deleting the top-level `context_manager` payload seam; otherwise switch back to richer owner-replacement or boundary-owner work
- **First deterministic check command:** `rg -n "context\[[^]]+\] =|context\.pop\(|manager\[[^]]+\] =|manager\.pop\(" truffles-api/app/routers/webhook/context_manager.py truffles-api/app/routers/webhook/session_memory.py`
- **Blocked-by conditions:** if remaining writes are only trace-retention or broader restore semantics, do not force another continuity micro-bridge
- **Owner role for closure:** `Top Architect`
