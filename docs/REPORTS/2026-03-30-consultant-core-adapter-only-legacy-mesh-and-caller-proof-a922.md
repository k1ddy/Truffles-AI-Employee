# 2026-03-30 — Consultant Core Adapter-Only Legacy Mesh And Caller Proof

## Summary

This block turned legacy-mesh caller proof into a machine-readable governance base.

The repo now has:
- explicit phase advance from block 3 to block 4 recorded in the recovery lock / waiver layer while practical truth stays `r35f` and runtime stays paused
- exact caller-proof coverage for mounted, unmounted, shadow-only, and removed legacy surfaces
- an updated legacy authority entry that reflects the actual live legacy behavior gates
- deterministic guard coverage for static app importers and test-only importers of tracked legacy surfaces
- canon and packet alignment to the adapter-only legacy-mesh block

No runtime behavior changed in this block.

## What Changed

### 1. Dead-surface registry became a caller-proof base
`docs/system_forensics/dead_surface_registry.json` moved from a small status scaffold to a caller-proof registry:
- `schema_version: v4`
- `status: machine_readable_legacy_caller_proof_base`
- top-level `caller_proof_law`
- nineteen tracked surfaces instead of only the earlier ingress/shadow subset
- per-surface:
  - `authority_mode`
  - `caller_proof_status`
  - `live_runtime_callers`
  - `static_app_importers`
  - `test_only_importers`
  - `route_registration_paths`
  - `hot_path_reachable`

### 2. The legacy authority map was corrected to live code
`docs/system_forensics/authority_registry.json` no longer treats `decision.py` / `_legacy.py` / `response.py` as the current primary legacy actors.

The registry now names the actual live legacy behavior gates:
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/routers/webhook/session_memory.py`

The remaining frozen webhook-era surfaces are now explicitly recorded as competing legacy helper or compatibility surfaces instead of being treated as the live ingress owner.

### 3. Machine-readable caller proof is now guarded
New deterministic guard:
- `scripts/legacy_mesh_caller_guard.py`

It compares the machine-readable caller lists in `dead_surface_registry.json` against the current repo import graph for:
- app-runtime importers
- test-only importers

This guard is now part of:
- `scripts/arch_guard.py`

### 4. Canon switched to the new active block
The active operating base now points to:
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md`

That switch is reflected in:
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Caller-Proof Coverage

The caller-proof registry now distinguishes:
- mounted ingress surfaces
- live behavior-owning legacy surfaces
- live observer-only legacy surfaces
- startup-loaded unmounted legacy helpers
- unmounted sibling legacy helpers
- shadow-only runtime delegates
- unmounted compatibility wrappers
- removed runtime owner residue
- shadow-only test residue

Key corrected truths now machine-readable:
- `truffles-api/app/main.py` and `truffles-api/app/routers/webhook/__init__.py` remain the mounted ingress composition/package surfaces
- `truffles-api/app/routers/webhook/http.py` is the real mounted ingress router and still holds live preflight behavior
- `truffles-api/app/routers/webhook/session_memory.py` is still a live legacy behavior gate through `consultant_runtime`
- `truffles-api/app/routers/webhook/trace.py` is live but adapter-only/observer
- `truffles-api/app/routers/webhook/decision.py` is unmounted and no longer on the mounted ingress path
- `truffles-api/app/routers/webhook/_legacy.py` has zero app-runtime importers and is test/shadow-only
- `truffles-api/app/services/reasoning_core.py` has zero app-runtime importers and remains a shadow delegate
- `truffles-api/app/webhook.py` is unmounted and test-only inside the repo

## Residual Debt

Still open after this block by design:
- `http.py` preflight remains a live legacy behavior gate
- `session_memory.py` remains a live legacy behavior gate
- several frozen webhook-era helper files still exist as sibling compatibility surfaces
- post-owner reconstruction is still open
- boundary/degrade constriction is still open
- first-class fact plane is still missing

## Checks

Executed for this block:
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `git diff --check`

## Block Status

Implementation truth:
- this block is materially complete in repo registries, guard coverage, tests, packet, and canon sync
- behavior-owning legacy surfaces still remain live; this block proves and freezes them, it does not yet constrict them
- this block has been phase-advanced to block 5 by explicit user instruction recorded in `docs/RECOVERY_PHASE_WAIVER.yaml`
- the next phase advance beyond block 5 still requires explicit owner/architect acceptance

This report therefore treats the block as:
- `materially_complete_in_repo`
- `phase_advanced_to_block_5_under_explicit_user_waiver`
- `program_phase_advance_beyond_block_5_pending_owner_acceptance`

## Next Admissible Block

After acceptance of this block, the exact next admissible block is:
- post-owner reconstruction constriction

That block must start from the now-frozen legacy caller envelope and remove semantic-adjacent reconstruction from planner / executor / runtime shell without reopening legacy caller ambiguity.
