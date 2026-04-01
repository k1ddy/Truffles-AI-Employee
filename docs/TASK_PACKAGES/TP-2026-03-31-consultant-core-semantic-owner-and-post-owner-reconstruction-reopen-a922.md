# TP-2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922

## Название / цель
Убрать live non-owner semantic control paths и downstream semantic reconstruction на hot path так, чтобы `single semantic owner` и `post-owner semantic reconstruction` были доказуемы по живому коду, а не по registry narrative.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com branch by abstraction legacy system incremental refactoring`
- Date/time: `2026-03-31T22:01:56+05:00`
- Sources opened:
  - `https://martinfowler.com/bliki/BranchByAbstraction.html`
- Ready solutions found:
  - branch-by-abstraction / gradual supplier replacement through one explicit abstraction seam
- Decision: `reuse/integrate`
- Reason:
  - this block needed a narrow migration seam where planner/runtime synthetic control paths could remain executable without continuing to pretend to be business semantic owner output
  - the Fowler pattern supports exactly that: explicit coexistence through one constrained abstraction while removing the old meaning-owning path
- Rejected variants:
  - broad runtime rewrite before proving the narrow hot-path invariant
  - leaving the old synthetic business-semantic shape in place and only changing docs/tests

## Root cause (mandatory)
- Symptom:
  - `single semantic owner` and `post-owner semantic reconstruction` were claimed closed, but live code still minted business-looking synthetic `PolicyDecision` objects outside the owner and still rebuilt semantic contracts downstream
- Minimal reproduction:
  - planner/runtime guard fails triggered synthetic decisions in `truffles-api/app/core/turn_planner.py`
  - runtime used those decisions on the live path in `truffles-api/app/core/consultant_runtime.py`
  - dialog-state hydration still synthesized a fallback `PolicyDecision` when rebuilding `conversation_projection`
- Evidence:
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/turn_executor.py`
  - `docs/REPORTS/2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md`
- Five Whys:
  1. Why was the invariant false? Because planner/runtime control turns still emitted business-looking semantic tuples.
  2. Why did they emit business-looking tuples? Because degrade/preflight/session-reset paths reused `PolicyDecision` as a control artifact without separating system control from business meaning.
  3. Why was downstream reconstruction still live? Because runtime/state/executor still accepted or rebuilt semantic and pending-question contracts when no canonical owner output existed.
  4. Why did that remain unnoticed? Because docs/registry/tests had been validating the declared narrative rather than the live code path.
  5. Why did closure get overstated? Because synthetic control envelopes and projection hydration had no explicit non-semantic contract boundary.
- Broken invariant:
  - non-owner paths may not mint business semantic meaning, and post-owner layers may not reconstruct meaning-bearing contracts after the owner speaks
- Shared mechanism:
  - synthetic control decisions and projection/runtime fallback logic were sharing the same meaning-bearing contract type as the owner path
- Why the surfaced family belongs to that mechanism:
  - every reopened failure came from non-owner code writing or rehydrating semantic state through `PolicyDecision`, `semantic_contract`, or `pending_question_contract` instead of preserving owner output or emitting an explicit system-control envelope
- Open-world envelope expected to improve after the fix:
  - planner/preflight/degrade/session-reset control turns
  - runtime projection/hydration without a fresh owner decision
  - owner-backed turns flowing through runtime/executor/state without semantic contract mutation
- Root cause statement:
  - the hot path still allowed non-owner control code to masquerade as business semantic output and still allowed downstream layers to rebuild semantic contracts from fallback state
- Fix mechanism:
  - demote synthetic control decisions to explicit `system_control` envelopes with `planner_control` source and `control_label`
  - suppress semantic and pending-question projection/reconstruction for synthetic control decisions
  - stop dialog-state hydration from synthesizing fallback `PolicyDecision` objects when rebuilding `conversation_projection`

## Invariant
- semantic meaning must not be authored outside the owner path
- post-owner layers may preserve or narrow, but may not reconstruct meaning-bearing contracts
- do not widen fact scope or reopen legacy semantic lanes during this block

## Scope
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `contracts/runtime/policy_decision.v1.jsonschema`
- corresponding guards/tests/registries for semantic-owner truth

## Out of scope
- replay
- human audit
- broad continuity/boundary/operational refactors beyond what is required to remove semantic co-ownership on the active hot path

## Touch-list
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `contracts/runtime/policy_decision.v1.jsonschema`
- `docs/SEMANTIC_OWNER_REOPEN_GUARD.yaml`
- `scripts/semantic_owner_reopen_guard.py`
- `truffles-api/tests/architecture/test_semantic_owner_reopen_guard.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan
1. Demote planner/runtime synthetic control decisions into explicit `system_control` envelopes with `planner_control` source and `control_label`.
2. Remove business semantic metadata from session-reset and related control-only runtime paths.
3. Suppress semantic and pending-question reconstruction for synthetic control decisions in runtime, executor, and dialog-state layers.
4. Remove dialog-state fallback `PolicyDecision` synthesis during runtime projection hydration.
5. Add a code-aware guard that checks the new system-control envelope and the suppression markers.
6. Re-run focused runtime and architecture checks.
7. Only then sync active docs/state/packet once for the full block.

## DoD
- planner and runtime control paths no longer mint business `intent` values outside the owner
- synthetic control decisions use `intent=system_control`, `source=planner_control`, and preserve exact control reason only in `control_label`
- runtime session-reset metadata is control-only and no longer writes business semantic fields
- synthetic control turns do not emit `semantic_contract` or `pending_question_contract` downstream
- dialog-state runtime-projection hydration no longer synthesizes fallback `PolicyDecision` objects
- active truth can honestly say the hot-path semantic-owner and post-owner reconstruction invariant is reproven repo-side, while broader system reproof remains open

## Checks
- `PYTHONPATH=truffles-api python3 scripts/semantic_owner_reopen_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "load_runtime_payload_builds_projection_without_synthetic_policy_decision or owner_backed_projection_sets_semantic_decision_ref or load_runtime_payload_prefers_conversation_projection_over_stale_dialog_state"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "missing_semantic_owner or missing_binding_plan or invalid_outcome or semantic_mutation or controlled_degrade or control_turn_reset or boundary_turn_outcome or block_boundary_artifact_from_request or degrade_boundary_artifact_from_request or turn_executor_builds_typed_block_boundary_turn_result or turn_executor_builds_typed_degrade_boundary_turn_result or turn_executor_builds_typed_block_boundary_artifact or turn_executor_builds_typed_degrade_boundary_artifact or preserves_explicit_boundary_handoff_on_existing_degrade_path or routes_degrade_binding_even_when_outcome_is_stale_fact or preserves_owner_decision_when_executor_requests_handoff or policy_decision_schema_requires_binding_plan_for_synthetic_decision or policy_decision_model_requires_binding_plan_for_synthetic_decision or policy_decision_schema_requires_binding_plan_for_semantic_decision or policy_decision_model_requires_binding_plan_for_semantic_decision"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "synthetic_boundary_builders_have_fixed_shape"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "build_sender_branch_ignore_artifact_uses_new_core_contracts or build_missing_remote_jid_artifact_uses_new_core_contracts or build_missing_tenant_context_artifact_uses_new_core_contracts or build_tenant_context_reject_artifact_uses_new_core_contracts or build_remote_branch_phone_ignore_artifact_uses_new_core_contracts or build_duplicate_message_artifact_uses_new_core_contracts"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_semantic_owner_reopen_guard.py`

## Evidence
- `docs/REPORTS/2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922.md`
- `docs/SEMANTIC_OWNER_REOPEN_GUARD.yaml`
- `scripts/semantic_owner_reopen_guard.py`
- `truffles-api/tests/architecture/test_semantic_owner_reopen_guard.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/boundary_validator.py`
- `contracts/runtime/policy_decision.v1.jsonschema`

## Rollback
- revert the reopen block commit if the hot-path owner-law proof fails or if synthetic control demotion breaks the typed runtime contract

## No-go
- no replay
- no product/practical closure claim
- no document-only “closure” without code proof
- no reintroduction of business semantic labels on planner/runtime control turns

## Риски / блокеры
- broader continuity, boundary, pack-runtime, legacy, and operational closure claims may still be false after this block and must not be inherited automatically
- synthetic-control demotion can surface tests that were silently assuming business `intent` labels on control turns

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- continuity, boundary, pack/runtime, legacy, and operational closure are not reproven by this block

### Why not in this block
This block only repairs the first reopened invariant: hot-path semantic ownership and downstream semantic reconstruction.

### Risk if deferred
Any broader whole-system closure claim stays untrustworthy until those remaining mechanisms are rechecked against live code.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md`

### Expiry / trigger to stop deferral
- stop deferral before any replay, human audit, or renewed whole-system closure claim

## Next-block contract (mandatory)
### Next block objective
Reprove continuity, boundary, pack/runtime, legacy, and operational closure claims against live code after semantic-owner reopen has landed.

### First deterministic check command
`python3 scripts/continuity_state_normalization_guard.py`

### Blocked-by conditions
- semantic-owner reopen closeout must be accepted
- active registries/packet must be synced to this block first

### Owner role for closure
Brain / Top Architect
