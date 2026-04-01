# 2026-03-30 Consultant Core Legacy Drain And Proof Closure — A922

## Summary
Repo-side block 10 narrows the mounted webhook package surface so the already-governed `location / hours / parking` mechanism no longer startup-loads broader legacy helper surfaces by default. The main delta is in `truffles-api/app/routers/webhook/__init__.py`: booking/context-manager/dedup/response helper exports are now lazy compatibility exports instead of eager startup imports, and a dedicated legacy-drain closure guard now freezes the exact allowed legacy seam for the touched envelope.

## What changed
- Activated `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md` as the current block in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_CANON.md`, and `docs/ACTIVE_PROGRAM.md`.
- Updated `truffles-api/app/routers/webhook/__init__.py` so only the mounted router and non-legacy runtime primitives load eagerly; legacy helper exports for booking/context-manager/dedup/response now resolve lazily through `__getattr__`.
- Added `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`, `scripts/legacy_drain_closure_guard.py`, and `truffles-api/tests/architecture/test_legacy_drain_closure_guard.py` and wired the guard into `scripts/arch_guard.py`.
- Added runtime proof in `truffles-api/tests/test_consultant_core_runtime_contracts.py` that normal first-family fact questions do not enter the reset-only control-turn path and that the reset seam clears touched-slice carryover canonically.
- Updated `docs/system_forensics/dead_surface_registry.json` so the touched envelope now records adapter-only surfaces, unreachable surfaces, and startup-load-drained package-root surfaces explicitly.
- Updated `docs/system_forensics/authority_registry.json` and `docs/system_forensics/compatibility_carrier_inventory.json` so the final legacy-drain proof is recorded as the current closure step for the touched canary envelope.

## Machine-readable authority delta
New machine-readable truths in this block:
- the mounted `app.routers.webhook` package root no longer startup-loads legacy booking/context-manager/dedup/response helpers on the runtime path;
- for the touched `location / hours / parking` envelope, the only remaining legacy live seam is adapter-only ingress preflight plus reset-only session-memory control helper usage;
- touched-envelope legacy sibling helpers are now explicitly recorded as unreachable in the dead-surface registry;
- final legacy-drain proof for the canary envelope is frozen by a dedicated guard rather than narrative-only reasoning.

## Residual debt
- this closes the implementation sequence for the touched canary envelope only; global legacy surfaces still remain elsewhere in the repo
- fresh practical replay and full human semantic audit are still required before any product-ready or full program closure claim
- distributed semantic authority and broader mixed continuity/fact debt outside the canary slice are still open as program-level residual architecture debt

## Block status
- Repo status: materially complete in repo if the legacy-drain closure guard/test suite stays green.
- Program status: still open until Brain / Top Architect accept the block and fresh practical replay + full human semantic audit are completed.
- Next admissible step: no further root-first implementation block; acceptance moves to practical replay and full human semantic audit for the recovered canary mechanism envelope.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/legacy_drain_closure_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "control_turn_gate_does_not_claim_first_fact_family_question or reset_runtime_context_clears_touched_slice_carryover or projects_touched_slice_class_carryover or persists_semantic_runtime_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`
- `git diff --check`
