# 2026-03-31 Consultant Core Fact Contract Schema — A922

## Summary
This block completes the whole-system fact contract schema layer. It does not claim narrow family cutover closure. Its job is to make the declarative fact envelope explicit and executable so later family migration cannot rely on helper memory or undeclared payload shape.

## What changed
- Added `FactManifestV1` and `FactContractV1` to the typed fact-plane contracts.
- Extended `FactRequestV1`, `FactPlanV1`, and `FactResultV1` with composition mode, allowed emitted sets, manifest id, renderer/provenance, and exact emitted-set legality.
- Published runtime schemas for `fact_manifest` and `fact_contract`, and regenerated the existing request/plan/result schemas.
- Added block-specific `FACT_CONTRACT_SCHEMA_GUARD` plus `fact_contract_schema_guard.py` and test coverage.
- Rebased the whole-system authority registry so `fact_scope` now closes the schema block honestly and names `narrow_fact_family_cutover` as the next phase.

## Why this was necessary
Authority Freeze locked the writer/caller topology, but the fact contract still lacked a declarative manifest and a top-level schema envelope. Without this block, the next family cutover would still build on partial contract shape.

## Authority delta
- Fact-side truth is now declared through `FactManifestV1` plus `FactRequestV1 -> FactPlanV1 -> FactResultV1 -> FactContractV1`.
- The emitted fact set is now checked against explicit `allowed_emitted_sets`, not only against a flat union list.
- Runtime meta now records `fact_manifest_id` and `fact_allowed_sets` in addition to requested/allowed/emitted refs.

## Residual debt
- narrow `location / hours / parking` cutover remains the next block
- continuity normalization remains open
- boundary constriction remains open
- pack/runtime separation remains open
- legacy drain remains open

## Block status
- Repo status: complete.
- Program status: `Fact Contract Schema` is the active block; `Narrow Fact-Family Cutover` is the next admissible runtime move.
- Next admissible move: complete the narrow family cutover before continuity normalization or replay.

## Evidence
- `python3 scripts/build_agent_packet.py` — pass
- `python3 scripts/build_agent_packet.py --check` — pass
- `python3 scripts/recovery_execution_guard.py` — pass
- `python3 scripts/authority_freeze_guard.py` — pass
- `python3 scripts/fact_contract_schema_guard.py` — pass
- `python3 scripts/fact_plane_guard.py` — pass
- `python3 scripts/arch_guard.py` — pass
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_manifest or fact_contract or fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"` — `5 passed, 117 deselected`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py` — `1 passed`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py` — `4 passed`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py truffles-api/tests/architecture/test_fact_contract_schema_guard.py` — `2 passed`
- `git diff --check` — pass

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/fact_contract_schema_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_manifest or fact_contract or fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_contract_schema_guard.py`
- `git diff --check`
