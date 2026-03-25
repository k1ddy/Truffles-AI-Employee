# TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-SESSION-MEMORY-FRESHNESS-BRIDGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CANONICAL-REFERENT-BRIDGE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-canonical-referent-bridge-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-SINGLE-CONTINUITY-WRITER-NEXT-SEAM-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded continuity block после canonical referent bridge: session-memory freshness shaping must stop living in `truffles-api/app/routers/webhook/session_memory.py`. `DialogStateService` should become the owner of `last_updated_at` / `ttl_hours` touch semantics and bounded expiry evaluation for live session-memory payloads, while `session_memory.py` stays as a thin orchestration layer.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-canonical-referent-bridge-a922.md`
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
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1,320p' truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "last_updated_at|ttl_hours|_is_session_memory_expired|_sync_session_memory_interaction_state|_update_session_memory_on_" truffles-api/app/routers/webhook/session_memory.py truffles-api/app/core/dialog_state_service.py`
  - `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'session_memory'`
  - `python3 scripts/continuity_writer_guard.py`
- `FACT findings`:
  - `DialogStateService` already owns session-memory content shaping (`interaction_state`, question bookkeeping, normalization), but `session_memory.py` still stamps live payload freshness fields (`last_updated_at`, `ttl_hours`) locally after every update.
  - `session_memory.py` also still owns bounded expiry evaluation through local ISO parsing and ttl comparison, so a live session-memory writer/read seam remains outside `DialogStateService`.
  - This seam is bounded because it only covers freshness envelope fields and expiry evaluation around existing session-memory payloads; it does not require widening into reset/restore orchestration.
- `Detected drift (docs vs code)`: single continuity writer completion is still blocked by session-memory freshness living in `session_memory.py`.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org datetime.fromisoformat Python official documentation`
- **Date/time (local):** `2026-03-16 21:52 +0500`
- **Why this query is precise:** the block moves bounded iso-datetime parsing and freshness evaluation into `DialogStateService`; it must preserve Python's official `datetime.fromisoformat(...)` behavior for stored `last_updated_at` payloads.
- **Sources opened (from this query):**
  - `datetime — Basic date and time types` — `https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat`
- **Source quality:** official Python documentation.
- **Existing solutions found:** the standard-library parsing contract is the correct baseline for bounded `last_updated_at` parsing; no custom parser should be introduced.
- **Decision:** `reuse + integrate` — keep Python's built-in ISO parsing semantics while relocating freshness/expiry ownership into `DialogStateService`.
- **Rejected options:**
  - leaving freshness shaping in `session_memory.py`
  - widening this block into broader session-memory reset or pending-resume restore semantics
  - touching frozen `pending.py` / `decision.py` / `booking.py`
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** session-memory freshness fields and expiry checks are still owned by `session_memory.py`, so `DialogStateService` is not yet the sole shaping authority for this live continuity seam.
- **Minimal reproduction:**
  1. Call `_update_session_memory_on_question(...)` or `_update_session_memory_on_answer(...)`.
  2. Observe that `session_memory.py` locally writes `last_updated_at` and `ttl_hours` after delegating the content update.
  3. Call `_is_session_memory_expired(...)` and observe that ttl fallback + ISO parsing are also still computed locally.
- **Evidence to capture:**
  - `DialogStateService` directly owns freshness stamping and bounded expiry evaluation.
  - `session_memory.py` becomes a thin wrapper around service-owned freshness helpers.
- **Five Whys (or equivalent):**
  1. Why is continuity still fragmented here? Because only the nested session-memory content moved into `DialogStateService`; freshness envelope logic stayed local.
  2. Why is that a problem? Because a live session-memory payload still has multiple shaping authorities.
  3. Why can this block stay bounded? Because freshness fields and expiry evaluation are a narrow envelope around an already-owned payload.
  4. Why not widen into all reset/restore paths? Because those paths mix bounded freshness ownership with broader orchestration and state-boundary semantics.
  5. Why fix this now? Because it removes another live writer from `session_memory.py` on the single continuity writer path.
- **Root cause statement:** `session_memory.py` still decides how live session-memory freshness is stamped and expired, so `DialogStateService` is not yet the sole owner of that continuity envelope.
- **Fix mechanism:**
  - add bounded freshness touch and expiry helpers to `DialogStateService`
  - delegate `session_memory.py` live freshness writes/checks to those helpers
  - prove parity with focused service tests and targeted compatibility checks

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing session-memory content helpers in `DialogStateService`
  - existing `_parse_iso_datetime(...)` utility in `DialogStateService`
  - existing message-endpoint tests that cover session-memory expected-reply flows
- **External reuse:**
  - official Python `datetime.fromisoformat(...)` contract
- **Why not reinvent the wheel:** this is ownership consolidation, not a new session-memory model.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `22`
- **Code dominance:** `code-heavy`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity-writer collapse with required canon/session sync.

## Invariant
- No frozen-router edits.
- No new semantic detector/phrase-bridge family.
- External session-memory behavior stays unchanged for existing question/answer and pending-resume flows.
- ISO parsing and ttl fallback semantics stay unchanged.

## Scope
- Add bounded session-memory freshness touch and expiry helpers to `DialogStateService`.
- Make `session_memory.py` delegate live freshness stamping/checks to the service.
- Add regression tests for the new service ownership and reuse existing compatibility tests.
- Sync canon/session artifacts.

## Out of scope
- edits to `truffles-api/app/routers/webhook/pending.py`
- edits to frozen legacy semantic files
- broader session-memory reset/restore orchestration
- new semantic owner cutovers
- proof-path rewrite
- boundary owner cutover

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
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
2. Add bounded freshness touch/expiry helpers to `DialogStateService`.
3. Replace local freshness stamping/checks in `session_memory.py` with thin delegation.
4. Add focused service tests and rerun targeted message-endpoint compatibility checks.
5. Sync canon/session artifacts and rerun required checks.

## DoD
- `DialogStateService` owns session-memory freshness stamping and bounded expiry evaluation for this seam.
- `session_memory.py` stays orchestration-only for session-memory payload injection.
- tests prove parity for freshness touch and expiry behavior.
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
- unit tests showing service-owned session-memory freshness touch/expiry
- targeted message-endpoint checks showing expected-reply/session-memory behavior is unchanged
- updated source-of-truth / packet showing the new active block

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** unit + targeted compatibility + architecture only for this bounded block
- **Stop condition:** if this slice requires broader reset/restore widening or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded continuity-writer collapse only; no new runtime entrypoints or semantic routing
- **Go/no-go signals:** dialog-state + targeted compatibility + architecture suites green; continuity/session gates green
- **Rollback:** revert the new service helpers, session-memory delegation, tests, and doc sync
- **Post-release monitoring window:** next block should continue writer collapse or return to owner replacement without bridge growth

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the session-memory freshness bridge and generated packet output.

## Rollback
1. Revert the new `DialogStateService` helpers, session-memory delegation, tests, and doc sync.
2. Regenerate packet.
3. Re-run architecture/session gates.

## No-go
- no frozen-router edit
- no new detector family
- no widening into broader reset/restore/state-boundary semantics
- no counting this block as done unless `session_memory.py` loses local freshness shaping authority

## Risks / blockers
- if the helper changes ttl fallback or iso parsing semantics, pending-resume / question-contract flows can drift.
- if the helper widens into reset orchestration, the block stops being bounded and must be split.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - broader continuity seams still remain outside this freshness envelope
  - richer semantic owner slices still remain in legacy `decision.py`
  - proof path is still not fully black-box
- **Why not in this block:**
  - this is a bounded freshness-ownership slice; widening further would mix payload shaping with broader reset/restore orchestration
- **Risk if deferred:**
  - session-memory continuity remains split across the service and router helper
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- **Expiry/trigger to stop deferral:**
  - if the next continuity slice requires reset/restore widening, switch back to richer owner-replacement cutover instead of continuing micro-bridges

## Next-block contract (mandatory)
- **Next block objective:** either remove one more live continuity writer after this freshness seam, or return to richer owner-replacement cutover if the next continuity candidate widens into reset/restore semantics
- **First deterministic check command:** `rg -n "last_updated_at|ttl_hours|_is_session_memory_expired|_parse_session_memory_time" truffles-api/app/routers/webhook/session_memory.py truffles-api/app/core/dialog_state_service.py`
- **Blocked-by conditions:** next slice would require frozen-router edits, new bridge families, or broader reset/restore/state-boundary behavior
- **Owner role for closure:** `Top Architect`
