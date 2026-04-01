# 2026-03-30 Consultant Core Fact-Plane Materialization — A922

## Summary
Repo-side block 7 materializes the first-class fact plane on the live consultant-core hot path without widening into the `location / hours / parking` proving slice. The main changes are: explicit `FactRequestV1 / FactPlanV1 / FactResultV1` contracts plus schemas, a live `turn_executor.py` fact chain that constrains emitted scope to binding authority, and a deterministic fact-plane guard that freezes contract builders/callsites and blocks manual emitted-scope growth.

This block is now the active program block under the explicit user phase-advance waiver recorded in `docs/RECOVERY_PHASE_WAIVER.yaml` while practical truth remains `r35f`.

## What changed
- Added `contracts/runtime/fact_request.v1.jsonschema`, `contracts/runtime/fact_plan.v1.jsonschema`, and `contracts/runtime/fact_result.v1.jsonschema`.
- Added `truffles-api/app/core/fact_plane.py` with typed fact request / plan / result contracts and shared normalization/policy helpers.
- Updated `truffles-api/app/core/turn_executor.py` so the live fact path now builds `FactRequestV1`, derives `FactPlanV1`, validates `FactResultV1`, and rejects out-of-plan emitted scope instead of appending `info_sections` opportunistically.
- Updated `truffles-api/app/services/tool_registry_service.py` so fact-emitting branches accept `allowed_fact_refs` and suppress out-of-plan widening.
- Added `docs/FACT_PLANE_GUARD.yaml` plus `scripts/fact_plane_guard.py`, and wired the guard into `scripts/arch_guard.py`.
- Updated `docs/system_forensics/authority_registry.json` so the `fact_scope` mechanism now reflects the live contract chain, constrained competing writers, and new closure criteria.
- Switched the active program/canon/source-of-truth block to `TP-2026-03-30-consultant-core-fact-plane-materialization-a922.md` and regenerated `docs/_generated/AGENT_PACKET.{md,json}`.
- Added deterministic proof in `truffles-api/tests/test_consultant_core_runtime_contracts.py` and `truffles-api/tests/architecture/test_fact_plane_guard.py`.

## Machine-readable authority delta
New machine-readable truths in this block:
- the live fact hot path now carries `FactRequestV1 -> FactPlanV1 -> FactResultV1` explicitly;
- `tool_registry_service.py` must receive `allowed_fact_refs` on live app-core fact calls;
- `turn_executor.py` no longer gets to grow emitted `info_sections` via local post-resolver append logic;
- runtime metadata now exposes `fact_contract`, `fact_requested_refs`, `fact_allowed_refs`, and `fact_emitted_refs`;
- the fact-plane seam is frozen by guard rather than left narrative-only.

## Residual debt
- Pack adapters still mix selection and rendering behind the new fact contract boundary.
- `truffles-api/app/routers/webhook/info.py` remains a frozen compatibility surface outside the governed hot path.
- The first proving slice `location / hours / parking` is still open.
- Touched-slice continuity normalization and legacy drain remain open.

## Block status
- Repo status: materially complete in repo if the deterministic guard/test suite stays green.
- Program status: phase-advanced to block 8 under the explicit user waiver; any phase advance beyond block 8 still requires Brain / Top Architect acceptance.
- Next admissible block after block-8 acceptance: `touched_slice_continuity_normalization`.

## Checks
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_fact_plane_guard.py`
- `git diff --check`
