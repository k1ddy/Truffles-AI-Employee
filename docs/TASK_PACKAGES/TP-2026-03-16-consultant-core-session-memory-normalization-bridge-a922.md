# TP-2026-03-16-consultant-core-session-memory-normalization-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-NORMALIZATION-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-QUESTION-WRITER-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-question-writer-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после session-memory question writer bridge: session-memory payload normalization must stop living in `truffles-api/app/routers/webhook/session_memory.py`. `DialogStateService` should become the owner of normalized shaping and validation for the live `session_memory` payload while `session_memory.py` stays as a thin compatibility wrapper around the new service helper.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-question-writer-bridge-a922.md`
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
  - `sed -n '1,180p' truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "_normalize_session_memory|_normalize_interaction_state|MemoryContract" truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py`
  - `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'session_memory'`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns session-memory interaction-state projection plus bounded question bookkeeping writes, but payload normalization for `mode`, `summary`, timestamps, ttl fields, `goal_stack`, `unanswered_questions`, `slots`, `pending_slots`, and `interaction_state` still lives in `_normalize_session_memory(...)` inside `session_memory.py`.
  - Frozen `decision.py` still calls `legacy._normalize_session_memory(...)`, so keeping normalization local leaves another live continuity shaping seam outside `DialogStateService`.
  - The slice is bounded because `_normalize_session_memory(...)` is a single helper with existing `MemoryContract` validation and no frozen-router edits are needed.
- `Detected drift (docs vs code)`: strategy lock says single continuity writer completion is the non-negotiable move, but session-memory payload normalization is still owned by `session_memory.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy dict shallow copy official documentation`
- **Date/time (local):** `2026-03-16 21:34 +0500`
- **Why this query is precise:** the block moves session-memory payload normalization into `DialogStateService` and must preserve dict/list copy semantics instead of introducing accidental in-place mutation or wider deep-copy behavior.
- **Sources opened (from this query):**
  - `Built-in Types — dict.copy()` — `https://docs.python.org/3/library/stdtypes.html#dict.copy`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python’s standard dict/list copy semantics are the correct baseline for detached top-level normalization without inventing a custom copy layer.
- **Decision:** `reuse + integrate` — preserve the existing shallow normalization semantics while relocating ownership into `DialogStateService`.
- **Rejected options:**
  - leaving normalization in `session_memory.py`
  - widening this block into expiry/reset orchestration
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** session-memory payload normalization is still shaped in `session_memory.py`, so `DialogStateService` is not yet the primary normalization authority for this live continuity seam.
- **Minimal reproduction:**
  1. Call `_normalize_session_memory(...)` with invalid `ttl_hours`, dirty `goal_stack`, `pending_slots`, and malformed `interaction_state`.
  2. Observe that `session_memory.py` trims, drops, and validates the payload locally before `decision.py` uses it.
  3. Observe that `DialogStateService` is bypassed for this normalization path even though it already owns related session-memory shaping logic.
- **Evidence to capture:**
  - `DialogStateService` directly normalizes session-memory payloads.
  - `session_memory.py` becomes a thin wrapper for this normalization seam.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented here? Because question writes moved, but payload normalization stayed local.
  2. Why is that a problem? Because one live continuity payload still has two shaping owners.
  3. Why can this block stay bounded? Because `_normalize_session_memory(...)` is isolated and only depends on `MemoryContract` plus interaction-state projection.
  4. Why not widen into expiry/reset? Because that would mix normalization ownership with orchestration and state-transition semantics.
  5. Why fix this now? Because the current strategy lock requires real continuity-owner collapse before taking broader semantic slices.
- **Root cause statement:** session-memory payload normalization still lets `session_memory.py` decide how live `session_memory` fields are cleaned and validated, so `DialogStateService` is not yet the sole shaping authority for this continuity seam.
- **Fix mechanism:**
  - add a bounded session-memory normalization helper to `DialogStateService`
  - replace `_normalize_session_memory(...)` in `session_memory.py` with thin delegation
  - prove parity with focused unit coverage and existing gates

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `DialogStateService.project_session_memory_interaction_state(...)`
  - existing `MemoryContract` validation
  - existing session-memory writer helpers already moved into `DialogStateService`
- **External reuse:**
  - official Python dict/list copy semantics from the standard library docs
- **Why not reinvent the wheel:** this is authority consolidation, not a new memory model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity normalization ownership cut with required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- External session-memory normalization behavior stays unchanged.
- Error reasons and `MemoryContract` validation semantics stay unchanged.

## Scope
- Add bounded session-memory normalization ownership to `DialogStateService`.
- Make `session_memory.py` delegate `_normalize_session_memory(...)` to the service.
- Add focused regression tests for the new service-owned normalization path.
- Sync canon/session artifacts.

## Out of scope
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- expiry/reset/session restore orchestration
- new semantic owner cutovers
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-normalization-bridge-a922.md`
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
2. Add bounded session-memory payload normalization to `DialogStateService`.
3. Replace local normalization in `session_memory.py` with thin delegation.
4. Add focused unit tests for parity and detached top-level copy behavior.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns session-memory payload normalization for this seam.
- `session_memory.py` stays a thin wrapper for `_normalize_session_memory(...)`.
- tests prove parity for normalization and error reporting.
- no frozen-router edits and no new semantic bridges are introduced.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'expected_reply_contract_bypasses_human_request or expected_reply_time_slot_mismatch_captures_alternate_name_without_clearing_time or test_llm_policy_core_get_booking_ok_clears_expected_reply_contract_without_escalation'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- unit tests showing service-owned session-memory normalization and unchanged error reasons
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + targeted compatibility + architecture only for this bounded block
- **Stop condition:** if this slice requires expiry/reset widening or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity normalization ownership only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + targeted compatibility + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helper, session-memory delegation, tests, and doc sync
- **Post-release monitoring window:** next block should continue writer collapse or return to owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the session-memory normalization bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` normalization helper, session-memory delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into expiry/reset/state-restore orchestration
- no counting this block as done unless `session_memory.py` loses local normalization authority

## Risks / blockers
- if the helper changes existing shallow normalization semantics, compatibility drift can leak into session resume and booking followup paths.
- if the helper changes error reason ordering, existing diagnostics can drift.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers still remain outside this session-memory normalization seam
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded normalization-ownership slice; widening further would mix payload cleanup with expiry/reset/state-transition semantics
- **Risk if deferred:**
  - session-memory drift remains possible because normalization authority stays split
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-single-continuity-writer-next-seam-a922` (planned)
- **Expiry/trigger to stop deferral:**
  - stop deferral if another block needs to add new session-memory-local payload cleanup or validation logic

## Next-block contract (mandatory)
- **Next block objective:** either delete the next bounded continuity writer seam after session-memory normalization or return to richer owner-replacement work only if it deletes an old semantic authority without new bridge growth.
- **First deterministic check command:** `python3 scripts/continuity_writer_guard.py`
- **Blocked-by conditions:** expiry/reset widening, frozen-router edits, or any need to grow generic semantic bridge families
- **Owner role for closure:** `Top Architect`
