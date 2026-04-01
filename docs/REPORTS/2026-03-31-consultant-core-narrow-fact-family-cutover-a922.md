# 2026-03-31 Consultant Core Narrow Fact-Family Cutover — A922

## Summary
This block closes the first governed whole-system fact family `location / hours / parking` on top of the explicit fact contract. It does not claim broader continuity normalization, boundary constriction, or legacy drain closure.

## What changed
- Promoted `location / hours / parking` to the active whole-system family cutover block.
- Confirmed the executor reroutes the targeted family to `catalog.location` on the governed fact-plane hot path even when stale binding still points elsewhere.
- Confirmed the targeted family no longer falls through to direct-truth or pack-runtime sibling replies.
- Confirmed `catalog.location` obeys binding-authorized `allowed_fact_refs` and does not re-infer `parking` when parking is out of scope.
- Rebased the whole-system authority registry so `fact_scope` now closes the family cutover honestly and advances `continuity_state_normalization` as the next phase.

## Authority delta
- The first governed family no longer relies on stale binding tool actions outside the explicit family resolver.
- The first governed family no longer permits direct-truth or pack-runtime sibling authority on the hot path.
- The resolver-side emitted scope for the family is now constrained by binding-authorized `allowed_fact_refs`.

## Residual debt
- continuity normalization remains open
- boundary constriction remains open
- broader fact families remain mixed
- broader legacy drain remains open
- legacy `webhook/info.py` and direct truth/render helpers remain frozen residual surfaces outside the governed hot path

## Block status
- Repo status: complete.
- Program status: `Narrow Fact-Family Cutover` is the active block; `Continuity / State Normalization` is the next admissible runtime move.
- Next admissible move: complete continuity/state normalization before boundary constriction or replay.

## Evidence
- `python3 scripts/build_agent_packet.py` — pass
- `python3 scripts/build_agent_packet.py --check` — pass
- `python3 scripts/recovery_execution_guard.py` — pass
- `python3 scripts/authority_freeze_guard.py` — pass
- `python3 scripts/fact_plane_guard.py` — pass
- `python3 scripts/fact_family_cutover_guard.py` — pass
- `python3 scripts/arch_guard.py` — pass
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_manifest or fact_contract or fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"` — `5 passed, 118 deselected`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "location_base_bundle or stale_service_query_binding or direct_truth_and_pack_bypass or reinfer_parking_outside_allowed_scope or fact_family"` — `6 passed, 117 deselected`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py truffles-api/tests/architecture/test_authority_registry.py truffles-api/tests/architecture/test_recovery_execution_guard.py truffles-api/tests/architecture/test_fact_family_cutover_guard.py` — `7 passed`
- `git diff --check` — pass
