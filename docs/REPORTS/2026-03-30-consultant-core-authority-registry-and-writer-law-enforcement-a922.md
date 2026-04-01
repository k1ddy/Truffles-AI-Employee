# 2026-03-30 — Consultant Core Authority Registry And Writer-Law Enforcement

## Summary

This block materialized the machine-readable authority base required by the root-first consultant-core recovery program.

The repo now has one live governance substrate for the active block:
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`

Those registries are now wired into:
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/build_agent_packet.py`
- `scripts/arch_guard.py`
- `scripts/authority_registry_block_guard.py`
- `scripts/recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_authority_registry_block_guard.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`

No runtime behavior changed in this block.

## What Changed

### 1. Authority topology became machine-readable
`docs/system_forensics/authority_registry.json` now names, for the full active mechanism envelope:
- mounted ingress truth (`main.py` -> `routers/webhook/__init__.py` -> `routers/webhook/http.py`)
- the real hot path (`consultant_core_v2 -> consultant_runtime -> turn_planner -> intent_service -> turn_executor -> dialog_state_service`)
- current semantic owners and competing writers
- current fact-scope wideners
- current boundary/degrade overreach surfaces
- current legacy behavior owners
- target owner, next phase, full-closure phase, and closure criteria for each mechanism

### 2. Continuity truth competitors became machine-readable
`docs/system_forensics/compatibility_carrier_inventory.json` now records the major continuity and compatibility carriers with:
- truth rank
- known writers
- known readers
- target fate
- full-closure phase

That includes the canonical runtime nucleus plus the known competing or derived carriers:
- `consultant_runtime.dialog_state`
- `consultant_runtime.conversation_projection`
- `consultant_runtime.turn_journal`
- `runtime_trace_contract.state_transition`
- `context_manager.canonical_dialog_state`
- `context.expected_reply_fields`
- `context.current_goal`
- legacy carryover and session-memory carriers

### 3. Dead/shadow surface truth became machine-readable
`docs/system_forensics/dead_surface_registry.json` now distinguishes:
- mounted live ingress surfaces
- `truffles-api/app/webhook.py` as `unmounted_legacy_wrapper`
- `truffles-api/app/core/booking_prompt_owner.py` as `removed_runtime_owner_surface`
- `truffles-api/tests/support_booking_prompt_owner_shadow.py` as `shadow_only_test_residue`

This preserves the already-corrected truths that:
- `truffles-api/app/webhook.py` is not the mounted ingress owner
- `booking_prompt_owner.py` is not a live runtime owner anymore

### 4. Guard and packet drift now fail deterministically
The packet / guard layer now validates and publishes the authority base directly:
- `scripts/build_agent_packet.py` loads and validates the registries, embeds them in the generated packet, and fails on stale authority-topology claims
- `scripts/arch_guard.py` reuses the same validation logic before running the other architecture guards
- `truffles-api/tests/architecture/test_arch_guard_packet.py` and `truffles-api/tests/architecture/test_authority_registry.py` now prove that the operating base matches the registry layer


### 5. Governing-base drift is now explicitly frozen
`docs/RECOVERY_EXECUTION_LOCK.yaml` now freezes the higher-precedence governing base so derived active docs cannot silently advance the practical truth, active block, or runtime phase.

`docs/RECOVERY_PHASE_WAIVER.yaml` now records that no owner/architect waiver is active, which means runtime implementation remains paused outside block-2 governance work.

`scripts/recovery_execution_guard.py` and `truffles-api/tests/architecture/test_recovery_execution_guard.py` now fail if `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_CANON.md`, `docs/ACTIVE_PROGRAM.md`, or `docs/_generated/AGENT_PACKET.*` drift away from that governing lock.

### 6. Block-2-only honesty is now guarded separately
`scripts/authority_registry_block_guard.py` and `truffles-api/tests/architecture/test_authority_registry_block_guard.py` now fail if the active block-2 operating base drifts in any of the following ways:
- block-2 registry statuses stop matching the neutral base statuses
- required block-2 guard files/checks are no longer wired into `docs/SOURCE_OF_TRUTH.yaml`
- owner-status fields in `docs/SOURCE_OF_TRUTH.yaml` regress back to later-phase completion language
- block-2 registries start citing later-phase runtime/proof artifacts as if they were block-2 evidence
- the machine-readable `historical residue` rule disappears from the lock/source-of-truth/packet chain

This keeps the active packet and source-of-truth wording honest even while later-phase residue still exists in the worktree as non-governing history.

## Current Block-2 Interpretation

These registries may still name later recovery phases in `next_phase_required` and `full_closure_phase`, but the active block-2 payloads no longer rely on later-phase implementation reports or later-phase guard artifacts as proof.

Interpretation rule:
- the registry layer may name future closure requirements
- it may not claim that those future phases are already complete
- later runtime/proof artifacts remain historical residue unless the owner/architect explicitly advances the phase

## Machine-Readable Gaps Closed

These gaps were previously narrative-only or partially implied and are now explicit in machine-readable form:
- the real mounted ingress chain
- the real hot path
- the six major live authority mechanisms
- the difference between canonical continuity state and competing compatibility carriers
- the mounted vs unmounted vs removed vs shadow-only status of the key stale authority surfaces
- the phase that must close before each mechanism can claim recovery

## Low-Confidence Entries Still Present

None currently remain at machine-readable `medium` or `low` confidence in the active registry layer.

Important note:
- later blocks may still split or narrow some grouped compatibility buckets, but those follow-up refinements are not currently represented as low-confidence placeholders in the active registry payloads
- if a future session finds a real unresolved carrier or writer bucket, it must be added back to the registry layer explicitly rather than only described in prose

## Checks

Executed for this block:
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_registry_block_guard.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry_block_guard.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `git diff --check`

## Residual Debt

Still open after this block by design:
- runtime authority is still distributed
- compatibility carriers still compete with canonical continuity
- planner/executor/runtime shell still reconstruct semantic-adjacent artifacts after owner output
- boundary/degrade still carries too much behavioral authority
- fact behavior is still not routed through a first-class fact plane
- legacy webhook-era modules still co-own visible behavior

## Block Status

Implementation truth:
- the active block is materially complete in repo artifacts, deterministic guards, generated packet, report, and state/structure sync
- this block has been phase-advanced by explicit user instruction recorded in `docs/RECOVERY_PHASE_WAIVER.yaml`
- later phases still remain blocked on explicit owner/architect acceptance for each further advance

This report therefore treats the block as:
- `materially_complete_in_repo`
- `accepted_for_phase_advance_to_block_3_under_explicit_user_waiver`

## Next Admissible Block

After acceptance of this block, the exact next admissible block is:
- truth-carrier inventory and freeze

That next block must start from the now-materialized compatibility-carrier inventory rather than from any visible fact family.
