# 2026-03-31 Consultant Core Semantic Owner And Post-Owner Reconstruction Reopen

## Summary
- Reproved the hot-path semantic-owner invariant by removing business-looking synthetic control decisions from planner/runtime control turns.
- Reproved the hot-path post-owner reconstruction invariant by suppressing synthetic-control semantic and pending-question projection downstream.
- Removed dialog-state runtime-projection fallback `PolicyDecision` synthesis.
- Kept replay and broader whole-system closure blocked; continuity, boundary, pack/runtime, legacy, and operational claims now move to a dedicated live-code reproof block.

## What Changed
- planner synthetic builders now emit explicit `system_control` envelopes with `source=planner_control` and `meta.control_label`
- runtime session-reset control path now writes control-only metadata instead of business semantic fields
- runtime, executor, and dialog-state layers stop emitting or reconstructing `semantic_contract` and `pending_question_contract` for synthetic control decisions
- dialog-state `load_runtime_payload(...)` no longer synthesizes a fallback `PolicyDecision` when rebuilding `conversation_projection`
- added block guard:
  - `docs/SEMANTIC_OWNER_REOPEN_GUARD.yaml`
  - `scripts/semantic_owner_reopen_guard.py`
  - `truffles-api/tests/architecture/test_semantic_owner_reopen_guard.py`

## Why Necessary
- the truth-correction block established that previous semantic-owner closure claims were false
- live code still allowed non-owner control code to masquerade as business semantic output
- downstream runtime/state layers still reconstructed semantic artifacts after the owner spoke
- without removing those paths, broader reproof and any later replay would still run from a false base

## Authority Delta
- non-owner planner/runtime control turns are no longer business semantic writers on the hot path
- synthetic control decisions are explicit system-control envelopes only
- owner-backed turns now preserve owner-authored semantic/pending contracts through runtime/executor/state on the active hot path
- broader continuity, boundary, pack/runtime, legacy, and operational claims are not inherited as closed; they are moved to the next live-code reproof block

## Residual Architecture Debt
- continuity closure is not yet reproven live-code-wide
- boundary closure is not yet reproven live-code-wide
- pack/runtime separation is not yet reproven live-code-wide
- legacy mesh closure is not yet reproven live-code-wide
- operational entrypoint dedupe is not yet reproven live-code-wide
- replay and human semantic audit remain blocked

## Block Status
- Repo status: complete for hot-path semantic-owner and post-owner reconstruction reopen
- Active block: `Consultant Core Semantic Owner And Post-Owner Reconstruction Reopen`
- Next admissible move: `Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof`

## Evidence
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
- `truffles-api/tests/test_dialog_state_service.py`

## Validation
- `PYTHONPATH=truffles-api python3 scripts/semantic_owner_reopen_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "load_runtime_payload_builds_projection_without_synthetic_policy_decision or owner_backed_projection_sets_semantic_decision_ref or load_runtime_payload_prefers_conversation_projection_over_stale_dialog_state"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "missing_semantic_owner or missing_binding_plan or invalid_outcome or semantic_mutation or controlled_degrade or control_turn_reset or boundary_turn_outcome or block_boundary_artifact_from_request or degrade_boundary_artifact_from_request or turn_executor_builds_typed_block_boundary_turn_result or turn_executor_builds_typed_degrade_boundary_turn_result or turn_executor_builds_typed_block_boundary_artifact or turn_executor_builds_typed_degrade_boundary_artifact or preserves_explicit_boundary_handoff_on_existing_degrade_path or routes_degrade_binding_even_when_outcome_is_stale_fact or preserves_owner_decision_when_executor_requests_handoff or policy_decision_schema_requires_binding_plan_for_synthetic_decision or policy_decision_model_requires_binding_plan_for_synthetic_decision or policy_decision_schema_requires_binding_plan_for_semantic_decision or policy_decision_model_requires_binding_plan_for_semantic_decision"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "synthetic_boundary_builders_have_fixed_shape"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "build_sender_branch_ignore_artifact_uses_new_core_contracts or build_missing_remote_jid_artifact_uses_new_core_contracts or build_missing_tenant_context_artifact_uses_new_core_contracts or build_tenant_context_reject_artifact_uses_new_core_contracts or build_remote_branch_phone_ignore_artifact_uses_new_core_contracts or build_duplicate_message_artifact_uses_new_core_contracts"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_semantic_owner_reopen_guard.py`
