# 2026-03-30 — Consultant Core Post-Owner Reconstruction Constriction

## Summary

This block turned the existing owner-backed post-owner constriction into an active root-first operating base.

The repo now has:
- explicit phase advance from block 4 to block 5 recorded in the recovery lock / waiver layer while practical truth stays `r35f` and runtime stays paused
- a machine-readable hotspot freeze for the exact post-owner reconstruction seam set;
- an updated authority-registry entry that reflects the current post-owner carrier truth;
- deterministic runtime proof that `_plan_turn(...)` degrades when owner-backed meaning is mutated after the owner speaks;
- deterministic schema proof that owner-backed `semantic_frame` cannot be repopulated as a live carrier;
- canon and packet alignment to the post-owner reconstruction block.

No runtime behavior changed in this repo step. This block operationalizes the current runtime truth already present in the codebase and closes the missing proof/guard gaps around it.

## What Changed

### 1. Post-owner reconstruction hotspots are now frozen
`docs/SEMANTIC_BRIDGE_GUARD.yaml` now records the exact active seam set across:
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`

This makes future growth in semantic/pending-question reconstruction helpers fail deterministically unless an explicit waiver is added.

### 2. The authority registry now reflects the current post-owner carrier set
`docs/system_forensics/authority_registry.json` now records the post-owner mechanism against the current repo truth instead of an older narrative-only carrier list.

The active post-owner carrier set now explicitly names:
- `PolicyDecision.semantic_frame`
- `PolicyDecision.pending_question_contract`
- `PolicyDecision.meta.semantic_contract`
- `RuntimeExecutionResult.meta.semantic_enrichment`
- `DialogState.meta.semantic_contract`
- `ConversationProjectionV1.semantic_contract`

The entry also now carries closure criteria tied to runtime mutation-guard proof and hotspot freeze evidence.

### 3. Runtime mutation guard proof is now explicit
`truffles-api/tests/test_consultant_core_runtime_contracts.py` now proves that `ConsultantRuntime._plan_turn(...)` degrades on the live owner-backed path when post-owner mutation reaches runtime.

Covered mutations now include:
- `intent`
- `interaction.target`
- populated shadow `pending_question_contract`

This closes the previous proof gap where mutation detection existed as a helper, but live runtime degradation was not yet proven in one deterministic test slice.

### 4. Schema proof now covers owner-backed `semantic_frame`
`truffles-api/tests/test_consultant_core_runtime_contracts.py` now also proves that owner-backed populated `semantic_frame` is rejected by `policy_decision.v1`.

### 5. Canon switched to the new active block
The active operating base now points to:
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md`

That switch is reflected in:
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Residual Debt

Still open after this block by design:
- canonical continuity still carries some derived enrichment-style payloads that are not yet normalized slice-by-slice;
- deterministic boundary/degrade still needs its own constriction block;
- first-class fact plane is still missing;
- legacy compatibility readers still exist outside the owner-backed hot path.

## Checks

Executed for this block:
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_mutation or semantic_frame or owner_backed or memory_profile"`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/arch_guard.py`
- `git diff --check`

## Block Status

Implementation truth:
- this block is materially complete in repo guard config, authority registry evidence, deterministic runtime proof, packet sync, and canon sync
- this repo step did not change runtime behavior; it closes the active proof/guard layer around the current post-owner runtime truth
- this block has been phase-advanced to block 6 by explicit user instruction recorded in `docs/RECOVERY_PHASE_WAIVER.yaml`
- the next phase advance beyond block 6 still requires explicit owner/architect acceptance

This report therefore treats the block as:
- `materially_complete_in_repo`
- `phase_advanced_to_block_6_under_explicit_user_waiver`
- `program_phase_advance_beyond_block_6_pending_owner_acceptance`

## Next Admissible Block

After acceptance of this block, the exact next admissible block is:
- boundary/degrade constriction

That block must constrict deterministic boundary authority without reopening post-owner semantic reconstruction or widening into fact-plane work.
