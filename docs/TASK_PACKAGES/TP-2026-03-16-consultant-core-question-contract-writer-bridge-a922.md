# TP-2026-03-16-consultant-core-question-contract-writer-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-QUESTION-CONTRACT-WRITER-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-TURN-PLANNER-SAFE-MASTER-QUERY-FACT-OWNER-CUTOVER-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после owner-replacement cutover: question-contract write shaping must stop living inside `truffles-api/app/routers/webhook/context_manager.py`. `DialogStateService` should become the owner of top-level expected-reply field shaping and canonical pending-question/interaction-state shaping, while `context_manager.py` stays a thin orchestration layer around conversation mutation, trace/meta side effects, and session-memory sync.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/LEGACY_SUNSET.yaml`
- `scripts/continuity_writer_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
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
  - `sed -n '250,760p' truffles-api/app/routers/webhook/context_manager.py`
  - `sed -n '220,430p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '1230,1465p' truffles-api/app/core/dialog_state_service.py`
  - `sed -n '700,930p' truffles-api/tests/test_dialog_state_service.py`
  - `sed -n '5882,5924p' truffles-api/tests/test_message_endpoint.py`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns normalization/projection primitives for expected-reply fields, canonical pending-question contract, canonical interaction state, and session-memory interaction projection.
  - `context_manager.py` still owns question-contract write shaping through `_set_expected_reply_type(...)`, `_set_expected_reply_context(...)`, and the question-contract portion of `_sync_canonical_dialog_state(...)`.
  - `_set_canonical_pending_question_contract(...)` and `_set_canonical_interaction_state(...)` are only local wrappers in `context_manager.py`; the service already has the underlying canonical setters.
  - `continuity_writer_guard` still allows `context_manager.py` to write the guarded continuity fields, so this seam remains a live fragmented writer even after earlier bridge cuts.
- `Detected drift (docs vs code)`: current strategy lock says progress must come from deleting writers or making old writers thinner; question-contract shaping is still split between `DialogStateService` and `context_manager.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy official documentation`
- **Date/time (local):** `2026-03-16 21:09 +0500`
- **Why this query is precise:** this block moves nested context/canonical payload shaping into `DialogStateService` and must preserve detached-copy semantics so canonical state mutations do not alias caller-owned dicts.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard safe mechanism for detached nested payload copies when transferring ownership of mutable dict/list structures.
- **Decision:** `reuse + integrate` — keep using detached copies inside the service rather than introducing custom copy logic or allowing caller-owned aliasing.
- **Rejected options:**
  - leaving nested canonical interaction payload shaping in `context_manager.py`
  - introducing partial in-place mutation across service/context-manager boundaries
  - widening the block into frozen `pending.py` or other legacy router edits
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** question-contract continuity writes are still split between `DialogStateService` and `context_manager.py`, so the system still has multiple live writers for the same expected-reply and canonical pending-question/interaction-state surfaces.
- **Minimal reproduction:**
  1. Call `legacy._set_expected_reply_context(...)` with a booking followup contract.
  2. Observe that `_set_expected_reply_type(...)` mutates top-level expected-reply fields in `context_manager.py`.
  3. Observe that `_sync_canonical_dialog_state(...)` also derives pending-question contract fields and canonical interaction payloads locally before calling the lower-level service setters.
- **Evidence to capture:**
  - `DialogStateService` directly shapes top-level expected-reply fields and the canonical question-contract state.
  - `context_manager.py` only orchestrates conversation/context mutation and side effects for this slice.
- **Five Whys (or equivalent):**
  1. Why does continuity remain fragmented here? Because the service owns normalization primitives but `context_manager.py` still assembles the actual question-contract writes.
  2. Why is that a problem? Because the same continuity surface still has two shaping authorities, which keeps drift risk alive.
  3. Why wasn't this already eliminated by earlier bridge slices? Because prior slices focused on carriers and canonical setters, not on the combined expected-reply question-contract write path.
  4. Why not solve it by editing `pending.py`? Because frozen router edits are explicitly out of scope for this bounded block.
  5. Why fix this now? Because the next semantic owner slices start to widen; the correct move is to complete another real writer collapse instead of farming more semantic seams.
- **Root cause statement:** the question-contract write path still lets `context_manager.py` shape expected-reply fields and canonical pending-question/interaction-state payloads directly, so `DialogStateService` is not yet the single shaping authority for this continuity seam.
- **Fix mechanism:**
  - add bounded helper methods to `DialogStateService` for top-level expected-reply field shaping and canonical question-contract state shaping
  - replace local shaping in `context_manager.py` with thin delegation
  - prove behavior parity with focused unit tests and a message-endpoint compatibility check

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `project_expected_reply_projections(...)`
  - existing `set_canonical_pending_question_contract(...)`
  - existing `set_canonical_interaction_state(...)`
  - existing `normalize_context_manager_canonical_state(...)`
  - existing `project_session_memory_interaction_state(...)`
- **External reuse:**
  - Python `copy.deepcopy(...)` behavior from official docs
- **Why not reinvent the wheel:** the missing piece is ownership consolidation, not a new context abstraction.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity-writer collapse with required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- Expected-reply compatibility and canonical dialog-state behavior stay externally unchanged.
- Nested payloads remain detached copies; no new aliasing between caller-owned structures and canonical state.

## Scope
- Add bounded `DialogStateService` helpers for question-contract write shaping.
- Make `context_manager.py` delegate expected-reply and canonical question-contract shaping to the service.
- Add regression tests for the new service ownership and compatibility.
- Sync canon/session artifacts.

## Out of scope
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- new semantic owner cutovers
- broader continuity-writer completion beyond this question-contract seam
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-question-contract-writer-bridge-a922.md`
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
2. Add bounded question-contract shaping helpers to `DialogStateService`.
3. Replace local shaping in `context_manager.py` with thin delegation.
4. Add focused tests for service-owned shaping and one compatibility test for canonical sync.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns top-level expected-reply field shaping for this path.
- `DialogStateService` owns canonical pending-question + interaction-state shaping for this path.
- `context_manager.py` remains orchestration-only for the question-contract write path.
- tests prove parity and no new aliasing/drift.

## Checks
- `pytest -q truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'canonical_dialog_state_syncs_interaction_state_from_policy_contract or consult_reply_with_service_hint_sets_service_expected_reply_for_booking_cta'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/routers/webhook/context_manager.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_message_endpoint.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- unit tests showing service-owned expected-reply and canonical question-contract shaping
- message-endpoint compatibility test showing canonical interaction-state sync still matches existing contract
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + architecture only for this bounded block
- **Stop condition:** if this slice requires frozen-router edits or widens into broader state-restore ownership, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + compatibility + architecture suites green; arch/session gates green
- **Rollback:** revert the new service helpers, context-manager delegation, tests, and doc sync
- **Post-release monitoring window:** next block should either continue writer collapse or return to owner replacement without new bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the question-contract writer bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, context-manager delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into `pending.py` or state restore rewrites
- no counting this block as done unless `context_manager.py` loses local question-contract shaping authority

## Risks / blockers
- if service helpers mutate caller-owned nested dicts in place, the block introduces aliasing regression.
- if context-manager orchestration changes behavior instead of only delegating shaping, compatibility drift can leak into booking/info flows.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity writers still remain outside this question-contract seam
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded writer-collapse slice; widening further would mix continuity cleanup with broader state-restore or semantic owner work
- **Risk if deferred:**
  - expected-reply/canonical question-contract drift remains possible because shaping authority stays split
- **Linked follow-up Task Package(s):**
  - `TP-2026-03-16-consultant-core-single-continuity-writer-next-seam-a922` (planned)
- **Expiry/trigger to stop deferral:**
  - stop deferral if the next block needs another context-manager-local writer workaround for expected-reply or canonical question-contract payloads

## Next-block contract (mandatory)
- **Next block objective:** either delete the next bounded continuity writer seam after question-contract shaping or return to richer owner-replacement work only if it deletes an old semantic authority without new bridge growth.
- **First deterministic check command:** `python3 scripts/continuity_writer_guard.py`
- **Blocked-by conditions:** frozen-router edits, need for broader state-restore rewrites, or any requirement to grow generic semantic bridge families
- **Owner role for closure:** `Top Architect`
