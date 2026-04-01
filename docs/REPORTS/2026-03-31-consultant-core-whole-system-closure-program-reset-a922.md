# 2026-03-31 Consultant Core Whole-System Closure Program Reset — A922

## Summary
This block replaces the active canary-closeout operating base with a whole-system architecture-closure program. It does not change runtime behavior. Its job is to make the next execution move unambiguous: `Authority Freeze`, then `Fact Contract Schema`, then the first narrow fact-family cutover. Replay is now explicitly blocked until the whole architecture program closes.

## What changed
- Added a new governing DEC for whole-system closure.
- Added a new whole-system master program TP.
- Added a new active reset block TP.
- Repointed active canon/program/source-of-truth/lock away from `block 10 -> replay next` and toward whole-system closure.
- Added a block-specific guard so the active docs cannot silently drift back to canary replay-first behavior.
- Locked in the rule that `STATE.md`, active canon, packet, and reports update only after one full block completes, not after each micro-fix inside an unfinished block.

## Why this was necessary
The canary sequence closed a touched envelope, not the whole system. The audits still show open blocker families across semantic ownership, continuity carriers, fact architecture, boundary authority, legacy mesh, and duplicated operational entrypoints.

## Residual debt
- no runtime authority moved in this block
- whole-system implementation still starts with `Authority Freeze`
- replay and human audit remain deferred until the architecture program closes

## Block status
- Repo status: complete as a governance/program reset block once packet/guards/tests are green.
- Program status: active governing base updated; first admissible implementation block is now `Authority Freeze`.
- Next admissible move: complete `Authority Freeze` and then `Fact Contract Schema`.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/whole_system_program_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_whole_system_program_guard.py`
- `git diff --check`
