# TP-2026-03-25 Consultant Core Pending Resume Canonical Question Projection A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-PENDING-RESUME-CANONICAL-QUESTION-PROJECTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `bc7be303`
- `UNLOCKS`: pending-resume restore/boundary flows consume the same canonical pending-question contract as runtime and router source-of-truth

## Название/цель
Убрать следующий semantic protocol mismatch: `pending_resume` continuity carryover уже хранит canonical `pending_question_contract` внутри `context_manager.canonical_dialog_state`, но `state_service` / `dialog_state_service` pending-resume helpers продолжают жить на top-level `expected_reply_type/reason` и `booking.last_question`, поэтому restore/boundary flows могут читать другой язык active question, чем runtime/router canon.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-router-canonical-question-projection-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`

## FACT pre-check (before implementation)
- Worktree was clean after `bc7be303`.
- `DialogStateService.capture_pending_resume_payload()` snapshots `expected_reply_type/reason` only from top-level fields, even when canonical `pending_question_contract` already exists in `context_manager` or `session_memory`.
- `DialogStateService.restore_pending_resume_payload()` restores top-level expected-reply projections without reading canonical `pending_question_contract` first.
- `DialogStateService.derive_pending_booking_resume_boundary_payload()` still derives boundary type from top-level `expected_reply_type` and then falls back to `booking.last_question` instead of consuming canonical pending-question state first.
- `state_service._prepare_pending_handoff_resume_boundary_restore()` and `_prepare_resolved_handoff_resume_boundary_restore()` still treat top-level `expected_reply_*` as source-of-truth.

## One web search (mandatory before implementation)
- **Query (exact):** `Python dataclasses replace official docs`
- **Date/time (local):** 2026-03-25 23:48:00 +05
- **Sources opened:**
  - Python standard library documentation, `dataclasses.replace` — `https://docs.python.org/3/library/dataclasses.html#dataclasses.replace`
- **Existing solutions found:** frozen dataclass updates should reuse `dataclasses.replace(...)` rather than mutating or reimplementing copy semantics.
- **Decision:** keep the pending-resume restore objects immutable and solve the actual defect at the canonical question-contract projector seam; do not add a new mutable pending-resume repair object.
- **Rejected options:**
  - introducing a pending-resume-only semantic object separate from canonical `pending_question_contract`
  - continuing to rely on top-level `expected_reply_type/reason` and `booking.last_question` as semantic source-of-truth
  - adding a runtime semantic repair pass after restore
- **Source quality:** official Python documentation

## Root cause (mandatory)
- **Classification:** `semantic protocol/model` plus `continuity/state mismatch`; not retrieval, transport, or evaluation/process.
- **Symptom:** pending-resume restore and boundary activation can reconstruct a different active-question meaning than the canonical runtime contract already carried in continuity.
- **Minimal reproduction:** inspect `DialogStateService.capture_pending_resume_payload()`, `restore_pending_resume_payload()`, `derive_pending_booking_resume_boundary_payload()`, and `state_service._prepare_*pending*_resume_boundary_restore()`.
- **Evidence:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
- **Five Whys:**
  1. Why does pending-resume drift from runtime question state? Because restore/boundary helpers read top-level `expected_reply_*` and booking slot inference first.
  2. Why is that wrong? Because the canonical `pending_question_contract` is already carried inside `context_manager.canonical_dialog_state` and optionally `session_memory`.
  3. Why is meaning lost? Because snapshot/restore helpers do not project expected-reply fields from that canonical contract, so the carryover payload can expose stale or empty projections.
  4. Why does boundary logic drift? Because `state_service` gates restoration off the projected top-level fields instead of the canonical question contract.
  5. Why is this a protocol defect? Because adjacent continuity layers are still allowed to treat the same active question as two different schemas.
- **Root cause statement:** pending-resume continuity carries canonical question state, but pending-resume snapshot/restore/boundary helpers still speak an older projection dialect and therefore can ignore or overwrite the canonical active-question contract.
- **Fix mechanism:** add one canonical projector from context -> pending-question contract, make pending-resume snapshot/restore/boundary helpers consume it first, and keep top-level `expected_reply_*` as compatibility projections only.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.project_pending_question_contract(...)`
  - `DialogStateService.project_expected_reply_projections(...)`
  - existing canonical dialog-state normalization inside `context_manager.canonical_dialog_state`
- **External reuse:** Python standard library `dataclasses.replace` guidance for immutable dataclass updates
- **Why not reinvent the wheel:** the codebase already has the canonical pending-question projector; the defect is that pending-resume helpers bypass it.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** bounded continuity/source-of-truth alignment for pending-resume, without broad router or transport rewrites.

## Invariant
- Policy-core remains the semantic owner.
- Pending-resume helpers may validate, project, or persist canonical question state; they must not invent new semantics.
- Top-level `expected_reply_type/reason` remain compatibility projections, not pending-resume source-of-truth.
- Booking boundary inference may only be a contractual fallback when canonical pending-question state is absent.

## Scope
- add one canonical context -> pending-question projector in `DialogStateService`
- make pending-resume snapshot/restore consume canonical pending-question state first
- make pending-resume boundary restore logic gate off canonical pending-question state first
- update focused pending-resume tests

## Out of scope
- deleting all remaining webhook `expected_reply_*` fields
- acceptance baseline refresh
- retrieval, transport, or pack behavior changes
- remaining webhook surfaces outside pending-resume/state-service

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-pending-resume-canonical-question-projection-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_dialog_state_service.py`

## Plan (1..N)
1. Add a canonical context projector for `pending_question_contract` and use it in pending-resume snapshot/restore helpers.
2. Route pending-resume boundary activation and re-entry restore through that canonical projector instead of top-level expected-reply fields.
3. Update focused tests to prove pending-resume prefers canonical question state over stale/missing top-level projections.
4. Run the required local suite set and commit only after closure evidence exists.

## DoD
- pending-resume snapshot/restore derive `expected_reply_type/reason` from canonical pending-question state first
- pending-resume boundary restore skips or restores based on canonical question state first
- session-memory carryover no longer drops or leaves raw `pending_question_contract` unnormalized
- tests prove canonical question state wins over stale or missing top-level expected-reply projections in pending-resume flows

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
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
- focused pending-resume test output
- required local suite outputs

## Rollback
- `git revert <commit>` for this bounded pending-resume canonical-question alignment commit
- if pending-resume restore regresses, reopen RCA instead of reintroducing projection-first source-of-truth

## No-go
- no new semantic regex branches
- no pending-resume-only semantic schema
- no runtime semantic repair layer after restore
- no continued use of top-level `expected_reply_*` as pending-resume source-of-truth when canonical contract exists

## Risks/Blockers
- older tests assert pending-resume payload only through top-level projection fields
- some resume boundary behavior still legitimately falls back to `booking.last_question` when no canonical contract exists

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: remaining webhook surfaces outside pending-resume/state-service still expose or read top-level `expected_reply_*` as compatibility projections.
- `Why not in this block`: this block closes the pending-resume continuity family first; deleting all remaining projections is a separate surface cleanup.
- `Risk if deferred`: non-pending-resume webhook paths can still keep a second projection dialect alive even after pending-resume is canonicalized.
- `Linked follow-up Task Package(s)`: next block should remove or strictly projection-limit remaining webhook `expected_reply_*` consumers outside `state_service`.
- `Expiry/trigger to stop deferral`: before claiming full webhook question-state dialect closure.

## Next-block contract (mandatory)
- `Next block objective`: delete or projection-limit remaining webhook `expected_reply_*` consumers in `booking.py` / `info.py` / `response.py` / remaining `decision.py` call-sites once pending-resume continuity is canonical.
- `First deterministic check command`: `rg -n "expected_reply_type|expected_reply_reason" truffles-api/app/routers/webhook/booking.py truffles-api/app/routers/webhook/info.py truffles-api/app/routers/webhook/response.py truffles-api/app/routers/webhook/decision.py`
- `Blocked-by conditions`: any failing suite that proves pending-resume still reconstructs question state from projection fields when canonical contract exists.
- `Owner role for closure`: Brain / Top Architect
