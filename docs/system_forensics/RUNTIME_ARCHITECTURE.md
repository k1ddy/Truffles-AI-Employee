# Consultant Core Runtime Architecture

## Purpose
Explain how the live runtime currently works without requiring source access.

## Current hot path
The active consultant-core runtime spine is:
- `consultant_core_v2`
- `consultant_runtime`
- `turn_planner`
- `intent_service`
- `turn_executor`
- `dialog_state_service`

This is the clearest current candidate for the future runtime kernel.

## What each layer currently does
- `consultant_core_v2`: top-level compatibility cutover shell
- `consultant_runtime`: live orchestration shell for planning, execution, persistence, trace, and reply flow
- `turn_planner`: adapts runtime context into typed owner/boundary decision intake
- `intent_service`: policy-core owner gateway and semantic input assembly
- `turn_executor`: binding/execution stage that still reconstructs some semantic execution context
- `dialog_state_service`: canonical-state and projection service plus compatibility reconciliation

## Still-live legacy surfaces
Outside the spine, a large compatibility mesh remains live:
- `decision.py`
- `_legacy.py`
- `context_manager.py`
- `response.py`
- `booking.py`
- `info.py`
- `pending.py`
- `policy.py`
- `guards.py`
- `dedup.py`

These files are not all equal, but together they explain why the repo is still hard to govern as one architecture.

## Why the runtime is still difficult
1. The hot path is narrower than before, but not yet singular.
2. Legacy modules still host real product behavior and continuity logic.
3. Boundary and execution stages still rebuild or normalize meaning-bearing artifacts.
4. Fact-side behavior still depends on broad reply helpers and mixed pack/runtime logic.

## Key evidence anchors
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/files/app_core_consultant_runtime.md`
- `docs/system_forensics/files/app_core_turn_planner.md`
- `docs/system_forensics/files/app_services_intent_service.md`
- `docs/system_forensics/files/app_core_turn_executor.md`
- `docs/system_forensics/files/app_core_dialog_state_service.md`
