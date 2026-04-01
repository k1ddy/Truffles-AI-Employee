# 2026-03-31 Consultant Core Authority Freeze — A922

## Summary
This block completes the first whole-system implementation step after the program reset. It does not change runtime behavior. Its job is to freeze the writer/caller topology so the next block can implement the fact contract against one explicit authority map instead of canary memory, hidden caller residue, or local family symptoms.

## What changed
- Published the full block TP for Authority Freeze.
- Rebased `authority_registry.json`, `compatibility_carrier_inventory.json`, and `dead_surface_registry.json` to Authority Freeze status and whole-system scope notes.
- Added `legacy_caller_surface.json` for the frozen legacy modules and wrapper/shadow surfaces.
- Added `governance_delta.json` so this block names the exact authority it locked instead of claiming narrative progress.
- Added `scripts/authority_freeze_guard.py` and its architecture test.
- Wired packet/source-of-truth validation to the new authority-freeze artifacts.
- Phase-advanced active canon/program/lock from the reset block to Authority Freeze and kept replay closed.

## Why this was necessary
The reset block changed the governing order, but it did not yet freeze the whole-system writer/caller envelope. Without this block, later fact-contract work could still start from partial caller knowledge and leave frozen legacy modules under-specified.

## Authority delta
- Locked the whole-system semantic writer, continuity carrier, fact-scope widener, boundary override, and legacy caller inventories as machine-readable artifacts.
- Froze the immediate adapter-only legacy module set:
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/app/routers/webhook/context_manager.py`
  - `truffles-api/app/services/reasoning_core.py`
- Published exact caller-surface coverage for the frozen set plus `truffles-api/app/webhook.py`.

## Residual debt
- no runtime fact contract exists yet
- no runtime authority moved out of planner/executor/runtime shells yet
- continuity normalization remains open
- boundary constriction remains open
- pack/runtime separation remains open
- legacy drain remains open

## Block status
- Repo status: complete as the whole-system Authority Freeze block once packet/guards/tests are green.
- Program status: Authority Freeze is now the active block; `Fact Contract Schema` is the next admissible runtime block.
- Next admissible move: complete `Fact Contract Schema`, then the first narrow fact-family cutover.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_authority_freeze_guard.py`
- `git diff --check`
