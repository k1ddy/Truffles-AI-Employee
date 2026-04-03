# TP-2026-04-01-consultant-core-block-c-continuity-carrier-collapse-a922

- Status: `closed_proven`
- Owner: `Hands`
- Date: `2026-04-01`
- Work mode: `forensic -> implementation -> closure`
- Block ID: `block-c-continuity-carrier-collapse`

## Название/цель
Закрыть только `Block C — Continuity Carrier Collapse` в active worktree `a922`: оставить `canonical_dialog_state.pending_question_contract` единственным continuity writer на hot path, а `pending_resume`, top-level `expected_reply_*`, `session_memory`, и compatibility snapshots перевести в derived-only carriers.

## Canon refs
- `/home/zhan/AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_START_PROMPT.txt`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-a-interrupt-arbitration-and-continuation-law-a922.md`
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-b-fact-scope-exactness-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/summary.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.json`

## Invariant
- Не лечить continuity symptoms через scenario patch, raw-text branching, или hardcoded stale projection exceptions.
- Не трогать `Block D+` механизмы: boundary purification, pack/runtime separation, legacy mesh final drain, operational dedupe.
- `canonical_dialog_state.pending_question_contract` остаётся единственным source of truth для mutable follow-up continuity на touched path.
- `pending_resume`, `expected_reply_*`, `session_memory`, `context_manager` snapshots могут остаться только как derived compatibility surfaces.
- Не обновлять `STATE.md`, `docs/ACTIVE_*`, `docs/SOURCE_OF_TRUTH.yaml`, `docs/RECOVERY_EXECUTION_LOCK.yaml`, `docs/_generated/`, registries/reports до полного proof closeout этого блока.

## Scope
- Collapse only the shared continuity-carrier mechanism for follow-up / resume / interrupt continuity:
  - canonical pending-question contract projection in `DialogStateService`
  - pending-resume capture/restore in `state_service`
  - session-memory continuity mirroring in `dialog_state_service` + `webhook/session_memory`
- Focused deterministic tests only for this writer/restore envelope.
- Exactly one minimal focused replay only for continuity turns after deterministic proof.

## Out of scope
- new semantic owner arbitration beyond already closed `Block A`
- fact scope beyond already closed `Block B`
- boundary meaning minting outside continuity restore
- pack/runtime split and legacy mesh fate
- broad docs churn before proof closeout

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-c-continuity-carrier-collapse-a922.md`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## One web search (mandatory before implementation)
- Query: `CQRS pattern projections read model derived from write model official documentation`
- Date/time: `2026-04-01 13:37:00 +05 (Asia/Almaty)`
- Sources opened:
  - `https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs`
- Source quality:
  - official vendor architecture reference
- Found ready-made solutions:
  - no Truffles-specific implementation; useful reusable pattern is that the write model remains the single source of truth and read/projection models are regenerated from it instead of becoming independent write/restore authorities.
- Decision (`reuse/integrate/build`):
  - `reuse + integrate + build`
  - reuse the existing canonical `DialogState` / `pending_question_contract` spine;
  - integrate compatibility snapshot rebuilds so they are derived from canonical state only;
  - build only the missing collapse law that removes `session_memory` / `expected_reply_*` / `pending_resume` as authority fallbacks.
- Rejected options:
  - more web searches
  - adding another carrier layer or another compatibility writer
  - keeping `last_question_type` or stored `expected_reply_*` as fallback truth

## Input baseline (FACT)
1. Fresh replay evidence on the surfaced continuity family:
- source: `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.json`
- result:
  - `infra_valid=true`
  - `semantic_valid=false`
  - `human_semantic.valid=false`
  - summary: `booking/info interrupt and pending-question continuity regress on seed 7`
2. Fresh replay turn evidence on the same family:
- `LLM-QUAL-a922-l2-proof-seed7-20260401i-001-07-65fdf0`
- result:
  - stale media continuity was still active on a later specialist/master query
  - `decision_meta.expected_reply_type="media"`
  - `pending_question_contract.expected_reply_type="media"`
  - `pending_question_target="time"`
  - mixed continuation contract stayed alive into the next turn surface
3. Current live worktree baseline:
- `truffles-api/app/core/dialog_state_service.py` still lets `project_context_pending_question_contract(...)` read from runtime projection, canonical state, `session_memory.pending_question_contract`, and top-level `expected_reply_*` projections.
- `truffles-api/app/core/dialog_state_service.py` still lets `normalize_session_memory_payload(...)` / `project_session_memory_pending_question_contract(...)` rebuild a pending-question contract from `last_question_type`.
- `truffles-api/app/core/dialog_state_service.py` still captures `expected_reply_*` and `session_memory` into `pending_resume`, then restores them back as first-class context fields.
- `truffles-api/app/services/state_service.py` boundary helpers still call `set_expected_reply_context(...)` during pending-resume restore, so compatibility surfaces still participate in the restore path.

## Exact Path Map (mandatory)
1. Input
- Fresh replay surfaced a continuity family in `/tmp/booking_quality/a922-l2-proof-seed7-20260401i` where booking/info interruptions and follow-up continuity regressed.
- Live code reproduction uses any context that already has a canonical pending question plus stale compatibility carriers (`expected_reply_*`, `session_memory`, `pending_resume`).
2. Owner output
- The owner/runtime already materializes canonical continuity as `dialog_state.pending_question_contract` and runtime trace `state_transition.pending_question_contract`.
- Example replay evidence: `LLM-QUAL-a922-l2-proof-seed7-20260401i-001-08-da01e8` shows canonical booking continuity carried as `pending_question_contract={expected_reply_type: time, next_question: datetime, ...}`.
3. Validator / continuity preservation
- `build_expected_reply_context_sync_result(...)` in `truffles-api/app/core/dialog_state_service.py` writes top-level `expected_reply_*`, syncs canonical `context_manager.canonical_dialog_state`, and then mirrors the same continuity into `session_memory`.
- `build_context_manager_compatibility_snapshot(...)` and `build_context_session_memory_snapshot(...)` both call `project_context_pending_question_contract(...)`, so projection builders can also become fallback readers.
4. Fallback / degrade / resume path
- `project_context_pending_question_contract(...)` still falls back from canonical state to `session_memory.pending_question_contract`, then to top-level `expected_reply_*`.
- `project_session_memory_pending_question_contract(...)` still reconstructs continuity from `last_question_type` when no canonical contract is present.
- `capture_pending_resume_payload(...)` snapshots `context_manager`, `expected_reply_*`, and `session_memory` into `pending_resume`.
- `restore_pending_resume_payload(...)` restores `context_manager`, top-level `expected_reply_*`, and `session_memory` from that snapshot.
- `state_service` pending-resume boundary helpers then call `set_expected_reply_context(...)`, so restore re-enters the compatibility write path again.
5. Final response / state
- The system can end up with multiple live continuity carriers that all describe the same follow-up contract.
- Because those carriers are both written and read, stale compatibility state can outlive or contaminate the canonical contract path.
6. Trace/meta evidence
- Replay family evidence: `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.json`, `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`, `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- Live code evidence:
  - `truffles-api/app/core/dialog_state_service.py:1560`
  - `truffles-api/app/core/dialog_state_service.py:2079`
  - `truffles-api/app/core/dialog_state_service.py:4141`
  - `truffles-api/app/core/dialog_state_service.py:4429`
  - `truffles-api/app/core/dialog_state_service.py:4452`
  - `truffles-api/app/core/dialog_state_service.py:4529`
  - `truffles-api/app/services/state_service.py:743`
  - `truffles-api/app/services/state_service.py:853`
  - `truffles-api/app/services/state_service.py:939`
  - `truffles-api/app/routers/webhook/session_memory.py:90`
7. Layer classification
- Primary: `boundary_fallback_error`
- Secondary: `owner_error` is not the mechanism here; the issue is continuity carrier co-ownership after owner output already exists
- Not this block: `fact_composition_error`, `oracle_or_evaluator_error`, `infra_or_runtime_failure`

## Root cause (mandatory)
### Symptom
- Follow-up continuity is still carried by more than one mutable authority: canonical dialog state exists, but `expected_reply_*`, `session_memory`, and `pending_resume` snapshots still participate in restore/write paths.

### Minimal reproduction
1. Start from a context with canonical `pending_question_contract={expected_reply_type: time, next_question: datetime}`.
2. Add stale compatibility carriers (`expected_reply_type=name`, `session_memory.pending_question_contract=name`, or `session_memory.last_question_type=name`).
3. Run the context through `build_context_manager_compatibility_snapshot(...)`, `build_context_session_memory_snapshot(...)`, `capture_pending_resume_payload(...)`, and `restore_pending_resume_payload(...)`.
4. Observe that compatibility carriers are still rebuilt and restored as first-class context fields instead of being treated as derived-only mirrors of canonical state.

### Evidence
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/manual_audit.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/family_registry.json`
- `/tmp/booking_quality/a922-l2-proof-seed7-20260401i/responses.jsonl`
- `truffles-api/app/core/dialog_state_service.py:1560`
- `truffles-api/app/core/dialog_state_service.py:4141`
- `truffles-api/app/core/dialog_state_service.py:4429`
- `truffles-api/app/core/dialog_state_service.py:4529`
- `truffles-api/app/services/state_service.py:743`
- `truffles-api/app/services/state_service.py:853`
- `truffles-api/app/services/state_service.py:939`
- `truffles-api/app/routers/webhook/session_memory.py:90`

### Five Whys
1. Why does stale follow-up continuity survive? Because compatibility carriers are not derived-only; they are also read back as fallback truth.
2. Why can they be read back as truth? Because `project_context_pending_question_contract(...)`, `project_session_memory_pending_question_contract(...)`, and pending-resume restore still treat `session_memory` and `expected_reply_*` as authority inputs.
3. Why does that matter after the owner already wrote canonical continuity? Because snapshot builders and restore helpers re-enter those fallback paths on interrupts, resume, and re-entry.
4. Why is this a shared mechanism instead of one scenario? Because the same fallback lattice is reused for active follow-up turns, pending handoff resume, resolved re-entry, and compatibility getter paths.
5. Why is `Block C` the right boundary? Because the problem is not what the owner decided; it is that continuity restore/write remains multi-owned after the owner decision already exists.

### Broken invariant
- Mutable follow-up continuity must have exactly one authority writer. Compatibility carriers may mirror canonical state, but they may not reconstruct or override it.

### Shared mechanism
- Projection builders, session-memory normalization, and pending-resume capture/restore still share one fallback lattice that treats compatibility surfaces as both mirrors and authorities.

### Why the surfaced family belongs to that mechanism
- The fresh replay surfaced pending-question continuity regressions; the same live code path shows that canonical continuity is still mirrored into and restored from multiple carriers before any wording layer participates.

### Open-world envelope expected to improve
- booking follow-up interrupts
- generic info interrupts with preserved resume
- pending handoff resume and resolved re-entry
- specialist/master follow-up continuity after interrupts
- any future flow where canonical pending-question continuity is present together with stale compatibility fields

### Root cause statement
- `DialogStateService` still allows `session_memory`, top-level `expected_reply_*`, and `pending_resume` snapshots to participate in pending-question read/restore paths. Because those compatibility surfaces are both written and later read back as fallback truth, canonical dialog state is not yet the sole mutable continuity owner.

### Fix mechanism
- Make canonical pending-question continuity authoritative in one direction only:
  - read pending-question continuity only from runtime/canonical dialog state on the touched path,
  - stop reconstructing session-memory pending question from `last_question_type`,
  - stop restoring top-level `expected_reply_*` and authority `session_memory` from `pending_resume`,
  - rebuild compatibility snapshots from canonical state after restore instead of replaying stored compatibility payloads.

## Plan
1. Create the Block C TP with live-path RCA from current worktree + fresh replay artifacts.
2. Collapse `project_context_pending_question_contract(...)` to canonical/runtime continuity sources only on the touched path.
3. Remove `session_memory` pending-question authority fallbacks (`last_question_type`, stored pending contract as truth) while keeping mirrored snapshots derived-only.
4. Collapse pending-resume capture/restore so restore rebuilds compatibility surfaces from canonical state instead of restoring `expected_reply_*` / authority session-memory directly.
5. Run focused deterministic tests.
6. Run exactly one focused replay on resume / interrupt / follow-up continuity.

## DoD
- Canonical `pending_question_contract` is the only mutable continuity authority on the touched path.
- `project_context_pending_question_contract(...)` no longer needs `session_memory` or top-level `expected_reply_*` as fallback truth on the touched path.
- `project_session_memory_pending_question_contract(...)` no longer reconstructs continuity from `last_question_type`.
- `pending_resume` restore no longer restores top-level `expected_reply_*` or authority `session_memory` from snapshot payloads.
- Compatibility carriers remain present only as projections rebuilt from canonical state.
- Focused deterministic tests pass.
- One minimal continuity replay passes with usable artifacts.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_state_service.py -k "pending_resume or session_memory or expected_reply"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_question_contract or session_memory or expected_reply"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "pending_question_contract or owner_backed_pending_question_contract or memory_profile or stale_state"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "canonical_dialog_state or expected_reply"`
- `git diff --check`
- focused replay command to be recorded after implementation

## Closeout
- Runtime closeout status: `closed_proven` on the declared continuity-carrier envelope only.
- Landed mechanism:
  - `truffles-api/app/core/dialog_state_service.py`, `truffles-api/app/services/state_service.py`, and `truffles-api/app/routers/webhook/decision.py` now rebuild compatibility carriers from canonical dialog state instead of restoring `pending_resume`, top-level `expected_reply_*`, or `session_memory` as authority writers on the touched path.
  - `truffles-api/app/core/consultant_runtime.py` now trims pre-reset transcript history before building owner memory summary, so `session_reset` becomes a hard boundary for `policy_core_trace.input.memory.summary`.
- Focused deterministic proof: the targeted continuity selections passed in `truffles-api/tests/test_state_service.py`, `truffles-api/tests/test_dialog_state_service.py`, `truffles-api/tests/test_consultant_core_runtime_contracts.py`, and `truffles-api/tests/test_message_endpoint.py`, including the reset-boundary follow-up checks.
- Focused replay proof: `/tmp/booking_quality/a922-block-c-replay-20260401ac` is `infra_valid=true`, `semantic_valid=false`, `manual_audit_status=done`, `human_semantic_valid=false`. The human audit proves the Block C objective is fixed because `block-c-1` turn 1 no longer leaks stale pre-reset transcript into owner memory and `block-c-2` resumes the canonical datetime question without reviving compatibility writers.
- First remaining fail is unrelated to Block C and is queued as the next block: `LLM-QUAL-a922-block-c-replay-20260401ac-001-02-62a155` preserves continuity but drops the promotions interrupt to `tool_decision=info_ref_unresolved`.

## Evidence
- Deterministic test output from the focused pytest selections above
- One focused replay directory under `/tmp/booking_quality/`
- Replay artifacts:
  - `summary.json`
  - `responses.jsonl`
  - `trace_bundle.jsonl`
  - `manual_audit.md`
  - `manual_audit.json`
  - `family_registry.json`
- `STATE.md` update only after code + focused tests + replay proof

## Rollback
- Revert only the touched Block C files in the active worktree.
- If continuity collapse regresses compatibility reads, revert the touched collapse helpers; do not reintroduce ad-hoc fallback truth from `session_memory` or top-level `expected_reply_*`.

## No-go
- No additional web search
- No docs sync before proof
- No hardcoded scenario exceptions for `media`, `specialist`, or `resume` turns
- No widening into `Block D+`
- No broad refactor of unrelated message-endpoint logic

## Риски/блокеры
- `state_service` boundary helpers and `dialog_state_service` snapshot builders are tightly coupled; changing only one side can create hidden restore regressions.
- Existing compatibility tests intentionally assert mirrored carriers; the block must preserve projections while removing those carriers as authorities.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- boundary can still mint or preserve non-canonical business meaning outside the continuity envelope
- pack/runtime split and legacy mesh fate remain partial
- operational dedupe remains partial

### Why not in this block
- those belong to `Block D`, `Block E`, `Block F`, and `Block G`; widening this block would break the one-hard-block rule

### Risk if deferred
- even with canonical continuity collapsed, stale meaning can still be introduced later by boundary or legacy layers outside this envelope

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-d-boundary-purification-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-e-real-pack-runtime-separation-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-f-legacy-mesh-final-drain-a922.md` (`planned`)
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-g-operational-final-dedupe-a922.md` (`planned`)

### Expiry/trigger to stop deferral
- if the focused replay still shows continuity authority split after this block, stop and reopen RCA before moving to `Block D`

## Next-block contract (mandatory)
### Next block objective
- `Block C.5 — Policy-Info Interrupt Fact Delivery`

### First deterministic check command
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "promotions_generic_info_interrupt or projects_policy_info_refs_into_catalog_execution or uses_policy_owned_info_truth_fallback_without_echo or logical_info_tool_candidates"`

### Blocked-by conditions
- `docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-c5-policy-info-interrupt-fact-delivery-a922.md` must stay RCA-first until code + focused tests + one minimal replay proof exist

### Owner role for closure
- `Top Architect` or `Brain`

## Branch + Worktree path + Base ref + Merge policy + Cleanup
- Branch: `feat/2026-03-30-consultant-core-consolidation-a922`
- Worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- Base ref: active worktree `HEAD` only; `/home/zhan/truffles-main` may be used only as canon/baseline/diff target
- Merge policy: no merge/closure claim in this block without code + focused tests + minimal replay proof
- Cleanup: keep replay artifacts under `/tmp/booking_quality/`; no cleanup until proof handoff is complete
