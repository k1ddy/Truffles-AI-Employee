# TP-2026-03-25 Consultant Core Resolved Handoff Re-entry Canonical Restore Gate A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-RESOLVED-HANDOFF-REENTRY-CANONICAL-RESTORE-GATE-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `0ac17f12`
- `UNLOCKS`: resolved-handoff resume restore no longer treats top-level `expected_reply_*` projections as the completion oracle when canonical re-entry state is still pending

## Название/цель
Закрыть следующий remaining semantic/state mismatch: `state_service` resolved-handoff re-entry restore still decides whether booking boundary is already restored by looking at top-level `expected_reply_type` / `expected_reply_reason`, even when canonical `pending_question_contract` plus `re_entry_required` already say the boundary still needs restoration. Это держит transport projection как semantic completion marker.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-pending-resume-canonical-question-projection-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-session-memory-canonical-question-fallback-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-webhook-question-evidence-canonicalization-a922.md`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- Worktree is clean after `0ac17f12`.
- Deterministic scan shows `state_service._prepare_resolved_handoff_resume_boundary_restore(...)` is now the remaining direct state gate that still reads top-level `context["expected_reply_type"]` / `context["expected_reply_reason"]` to decide whether restore is needed.
- Current logic:
  - projects canonical `pending_question_contract`
  - separately projects top-level `expected_reply_*`
  - returns `restored=False` when the top-level projection matches the canonical contract
- That means top-level transport fields are still acting as the restore completion oracle, even if `re_entry_required.required=true` says the boundary has not been cleared yet.
- This is a `continuity/state mismatch with the canonical protocol`, not retrieval or routing.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dataclasses official docs`
- **Date/time (local):** 2026-03-25 18:06:00 +05
- **Sources opened:**
  - Python standard library documentation, `dataclasses` — `https://docs.python.org/3/library/dataclasses.html`
- **Existing solutions found:** Python dataclasses are intended for explicit typed state carriers; frozen dataclasses remain appropriate when state transitions should be represented by pure function outputs instead of mutable flags.
- **Decision:** keep `PendingResumeBoundaryRestore` as a frozen carrier and fix the restore gate logic itself rather than introducing another mutable completion flag derived from projections.
- **Rejected options:**
  - adding a second mutable `already_restored` marker based on top-level projections
  - preserving top-level `expected_reply_*` as the restore completion oracle
  - introducing a router-only semantic repair around re-entry restore
- **Source quality:** official Python documentation

## Root cause (mandatory)
- **Classification:** `continuity/state mismatch with the canonical protocol`
- **Symptom:** resolved handoff re-entry restore can be suppressed because top-level `expected_reply_*` projections already match the canonical question contract, even though `re_entry_required` is still active.
- **Minimal reproduction:** call `_prepare_resolved_handoff_resume_boundary_restore(...)` with:
  - `re_entry_required.required=true`
  - canonical `pending_question_contract.expected_reply_type=time`
  - top-level `expected_reply_type=time`
  - booking boundary present
  Current behavior returns `restored=False` before clearing the boundary.
- **Evidence:**
  - `truffles-api/app/services/state_service.py:727`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
- **Five Whys:**
  1. Why can restore be skipped? Because the gate compares top-level projections to canonical state and bails out when they match.
  2. Why is that wrong? Because projection equality does not mean the re-entry boundary was resolved.
  3. Why does meaning drift? Because the transport projection is being treated as the completion signal for restore.
  4. Why is that a protocol defect? Because canonical `pending_question_contract` + `re_entry_required` should be the authoritative continuity contract for whether restore is pending.
  5. Why does this matter systemically? Because resume boundary logic can silently depend on stale or prefilled projections instead of the canonical continuity substrate.
- **Root cause statement:** resolved-handoff resume restore still uses top-level `expected_reply_*` projection equality as the completion oracle, so a transport field can suppress canonical re-entry restoration.
- **Fix mechanism:** remove projection-equality gating and let resolved-handoff restore depend on canonical pending-question continuity plus re-entry state.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.project_context_pending_question_contract(...)`
  - `DialogStateService.derive_pending_resume_reason(...)`
  - existing `PendingResumeBoundaryRestore` carrier
- **External reuse:** Python standard library `dataclasses`
- **Why not reinvent the wheel:** the canonical pending-question projector and frozen boundary carrier already exist; only the gating rule is wrong.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** one bounded state-service gate plus focused tests.

## Invariant
- Policy-core remains the only semantic owner.
- Re-entry restore must be decided by canonical continuity state, not by transport projection coincidence.
- No new semantic regex branches.
- No runtime semantic repair layer.
- Top-level `expected_reply_*` remain projection/transport only.

## Scope
- remove top-level projection equality as the resolved-handoff restore completion gate
- keep restore driven by canonical `pending_question_contract` + `re_entry_required`
- add focused tests proving matching top-level projections no longer suppress canonical restore

## Out of scope
- deleting all remaining top-level `expected_reply_*` fields
- broad webhook routing rewrites
- retrieval/transport changes
- acceptance baseline refresh

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-resolved-handoff-reentry-canonical-restore-gate-a922.md`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## Plan (1..N)
1. Remove the resolved-handoff restore early-return that treats matching top-level projections as restore completion.
2. Preserve restore gating only on canonical pending-question continuity and available boundary payload.
3. Add state-service and webhook integration tests proving matching projections no longer block re-entry restore.
4. Run focused plus mandatory regression suites and commit only after exact closure evidence exists.

## DoD
- `_prepare_resolved_handoff_resume_boundary_restore(...)` no longer reads top-level projection equality as the completion oracle
- canonical `pending_question_contract` + `re_entry_required` are sufficient to restore and clear the boundary
- tests prove matching top-level `expected_reply_*` do not suppress restore
- no new semantic owner or phrase branching is introduced

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff / commit
- focused pending-resume restore tests
- required local suite outputs

## Rollback
- `git revert <commit>` for this bounded resolved-handoff restore gate commit
- if restore logic regresses, reopen RCA instead of reintroducing top-level projection equality as completion truth

## No-go
- no new semantic regex branches
- no second re-entry state schema
- no transport-field completion oracle
- no broad pending-resume rewrite unrelated to the gate

## Risks/Blockers
- some tests may have implicitly relied on the previous skip behavior when projections already existed
- duplicate restore writes must remain harmless when canonical continuity truly still requires restore

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: top-level `expected_reply_*` still exist as transport/projection surfaces in webhook context and boundary payloads.
- `Why not in this block`: this slice only removes one remaining state gate that still gave those projections semantic authority.
- `Risk if deferred`: resolved handoff resume can stay semantically coupled to transport coincidence instead of canonical continuity.
- `Linked follow-up Task Package(s)`: next block should sweep remaining trace/meta and public/context consumers so projections are transport-only everywhere.
- `Expiry/trigger to stop deferral`: before claiming full `expected_reply_*` projection-only closure.

## Next-block contract (mandatory)
- `Next block objective`: sweep remaining consumers that still serialize or branch on split `expected_reply_*` without carrying canonical `pending_question_contract` alongside them.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason|pending_question_contract" truffles-api/app/routers/webhook truffles-api/app/services/state_service.py | head -n 260`
- `Blocked-by conditions`: any failing suite proving resolved handoff re-entry restore still bails out solely because top-level projections match canonical state.
- `Owner role for closure`: Brain / Top Architect
