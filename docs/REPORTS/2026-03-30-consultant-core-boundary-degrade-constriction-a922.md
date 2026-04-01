# 2026-03-30 Consultant Core Boundary/Degrade Constriction — A922

## Summary
Repo-side block 6 constricts the live typed boundary/degrade path without widening into fact-plane or continuity work. The main changes are: a machine-readable boundary/degrade hotspot guard, a live runtime narrowing that no longer lets degrade force `fact/collect` reply kinds, and explicit typed boundary proof for the `planner:invalid_outcome` path.

This block is now the active program block under the explicit user phase-advance waiver recorded in `docs/RECOVERY_PHASE_WAIVER.yaml` while practical truth remains `r35f`.

## What changed
- Added `docs/BOUNDARY_DEGRADE_GUARD.yaml` to freeze the current live boundary/degrade seam set, override-meta reads, and boundary-author callsites.
- Added `scripts/boundary_degrade_guard.py` and wired it into `scripts/arch_guard.py`.
- Narrowed `truffles-api/app/core/boundary_validator.py` so non-boundary-safe `reply_kind` override values are stripped.
- Narrowed `truffles-api/app/core/response_realizer.py` so degrade overrides may only force `handoff` or `system`; `fact/collect` now fall back to the owner decision outcome.
- Made `truffles-api/app/core/consultant_runtime.py` emit one explicit typed boundary override for `planner:invalid_outcome`.
- Updated `docs/system_forensics/authority_registry.json` so the boundary/degrade entry reflects the live hot-path actors and the shadow-only boundary builders separately.
- Switched the active program/canon/source-of-truth block to `TP-2026-03-30-consultant-core-boundary-degrade-constriction-a922.md` and regenerated the agent packet.
- Added deterministic proof in `truffles-api/tests/test_consultant_core_runtime_contracts.py` and `truffles-api/tests/architecture/test_boundary_degrade_guard.py`.

## Machine-readable authority delta
New machine-readable truths in this block:
- the live boundary/degrade hotspot set is frozen;
- `consultant_runtime.py` is the only live hot-path boundary author caller;
- `turn_executor.py` request-based boundary builders and `reasoning_core.py` artifact builders are tracked as shadow/compatibility surfaces rather than live hot-path writers;
- boundary override reply shaping is narrowed to boundary-safe kinds only.

## Residual debt
- `turn_executor.py` still contains request-based boundary artifact builders for shadow/test compatibility surfaces.
- `reasoning_core.py` still exports compatibility boundary artifact helpers, even though they are not part of the live app runtime path.
- Later fact-plane and touched-slice continuity normalization blocks remain open.
- Legacy drain and proof closure remain open.

## Block status
- Repo status: materially complete in repo if the deterministic guard/test suite stays green.
- Program status: phase-advanced to block 7 under the explicit user waiver; any phase advance beyond block 7 still requires Brain / Top Architect acceptance.
- Next admissible block after block-7 acceptance: `first_fact_family_cutover`.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "boundary or invalid_outcome or handoff or ignored_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `git diff --check`
