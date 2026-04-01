# Report - 2026-03-23 - Consultant Core Demo Salon Seed19 R11 Session Reset Pending Ack Greeting Intercept Runtime Implementation A922

## Outcome
- Complete.
- The bounded runtime repair is landed on the executable later greeting owner in `truffles-api/app/services/reasoning_core.py`.
- The next honest move is `rerun_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_canary_replay`.

## What changed
- Patched the live later `_try_handle_turn_planner_safe_greeting_owner_cutover(...)` owner so `pending_ack` traffic is deferred while `conversation.state == pending`.
- Reused the existing pending continuity contract via the frozen `pending.py` classifier instead of adding new phrase branching in core.
- Added a focused regression in `truffles-api/tests/test_reasoning_core.py` proving the bounded pending-ack path returns `None` before greeting-owner finalization, while the existing bot-active greeting-owner coverage stays green.

## Truthful result
- The surfaced family remains bounded to the executable later greeting owner.
- The repair does not touch frozen routers.
- The repair does not weaken replay/oracle gates.
- Focused deterministic proof is green:
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k "greeting_owner_family_defers_pending_ack or greeting_owner_family_bypasses_frozen_delegate"` -> `4 passed`
- Mandatory guards are green:
  - `python3 scripts/build_agent_packet.py` -> `OK`
  - `python3 scripts/build_agent_packet.py --check` -> `OK`
  - `python3 scripts/semantic_bridge_growth_guard.py` -> `OK`
  - `python3 scripts/continuity_writer_guard.py` -> `OK`
  - `python3 scripts/legacy_freeze_guard.py` -> `OK`
  - `python3 scripts/arch_guard.py` -> `OK`
  - `pytest -q truffles-api/tests/architecture` -> `19 passed`
  - `git diff --check` -> pass
  - `SESSION_AGENT=a922 scripts/session_check.sh` -> `Session OK`

## Evidence
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Residual debt
- `truffles-api/app/services/reasoning_core.py` still carries duplicate top-level defs; this block repaired only the live later greeting owner.
- Other pending-state smalltalk collisions may still exist, but they remain out of scope until a fresh replay proves they survive after this exact repair.

## Next block
- Run one fresh exact replay on the same seed-`19` scenarios and strict-audit it before any further runtime change.
