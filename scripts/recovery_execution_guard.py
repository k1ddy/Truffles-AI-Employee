#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]

WHOLE_SYSTEM_RESET_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md'
AUTHORITY_FREEZE_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-authority-freeze-a922.md'
FACT_CONTRACT_SCHEMA_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-fact-contract-schema-a922.md'
NARROW_FACT_FAMILY_CUTOVER_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md'
CONTINUITY_STATE_NORMALIZATION_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-state-normalization-a922.md'
POST_OWNER_SEMANTIC_CONSTRICTION_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-post-owner-semantic-constriction-a922.md'
BOUNDARY_CONSTRICTION_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-boundary-constriction-a922.md'
PACK_RUNTIME_SEPARATION_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md'
LEGACY_MESH_DRAIN_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md'
SHADOW_LANE_ELIMINATION_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-shadow-lane-elimination-a922.md'
OPERATIONAL_ENTRYPOINT_DEDUPE_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md'
CLOSURE_CLAIM_TRUTH_CORRECTION_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md'
SEMANTIC_OWNER_REOPEN_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922.md'
SYSTEM_REPROOF_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md'
WHOLE_SYSTEM_GOVERNANCE_CLOSURE_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-governance-closure-a922.md'
BLOCK2_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md'
BLOCK3_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md'
BLOCK4_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md'
BLOCK5_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md'
BLOCK6_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-boundary-degrade-constriction-a922.md'
BLOCK7_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-plane-materialization-a922.md'
BLOCK8_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md'
BLOCK9_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md'
BLOCK10_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md'

BLOCK_EXPECTATIONS: dict[str, dict[str, Any]] = {
    WHOLE_SYSTEM_RESET_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system governance work inside the active block',
            '- Active block: `Consultant Core Whole-System Architecture Closure Program Reset`',
            '- complete `Authority Freeze` and `Fact Contract Schema` for whole-system closure before any replay or behavioral acceptance',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while the whole-system closure reset is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system governance work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Whole-System Architecture Closure Program Reset',
            '- complete `Authority Freeze` and `Fact Contract Schema` for whole-system closure before any replay or behavioral acceptance',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_but_system_wide_owner_extraction_and_post_owner_constriction_remain_open',
            'continuity_owner.cutover_status': 'dialog_state_remains_short_term_canonical_nucleus_but_global_continuity_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'typed_boundary_seams_exist_but_system_wide_boundary_constriction_is_not_closed',
        },
        'state_now_prefix': '- NOW (consultant-core whole-system closure program reset, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule the reset block while the lock remains active.',
        'required_open_blockers': {
            'whole_system_master_program_and_block_tp_must_remain_machine_readable_and_in_sync',
            'authority_freeze_is_the_first_runtime_admissible_block',
            'fact_contract_schema_must_precede_broad_boundary_or_legacy_cleanup',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
            'state_and_canon_sync_must_happen_only_after_full_block_completion_not_after_micro_actions',
        },
        'requires_phase_advance_waiver': True,
    },
    AUTHORITY_FREEZE_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system governance work inside the active block',
            '- Active block: `Consultant Core Authority Freeze`',
            '- freeze machine-readable semantic writers, continuity carriers, fact-scope wideners, boundary override surfaces, and frozen legacy caller surfaces before fact contract runtime work begins',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Authority Freeze is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system governance work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Authority Freeze',
            '- complete `Fact Contract Schema` before any narrow fact-family cutover or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'whole_system_semantic_owner_path_is_frozen_but_post_owner_extraction_and_constriction_remain_open',
            'continuity_owner.cutover_status': 'dialog_state_short_term_canonical_nucleus_is_frozen_and_global_continuity_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'boundary_and_degrade_surface_map_is_frozen_but_system_wide_boundary_constriction_remains_open',
        },
        'state_now_prefix': '- NOW (consultant-core authority freeze, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Authority Freeze while the lock remains active.',
        'required_open_blockers': {
            'fact_contract_schema_is_the_next_runtime_admissible_block_after_authority_freeze',
            'frozen_legacy_modules_must_not_gain_new_authority_logic',
            'legacy_caller_surface_and_governance_delta_must_remain_machine_readable_and_in_sync',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    FACT_CONTRACT_SCHEMA_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system fact-contract work inside the active block',
            '- Active block: `Consultant Core Fact Contract Schema`',
            '- materialize FactManifest plus explicit FactRequestV1 / FactPlanV1 / FactResultV1 / FactContractV1 before any narrow fact-family cutover or replay',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Fact Contract Schema is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system fact-contract work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Fact Contract Schema',
            '- complete `Narrow Fact-Family Cutover` before continuity normalization or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'whole_system_semantic_owner_path_is_frozen_but_post_owner_extraction_and_constriction_remain_open',
            'continuity_owner.cutover_status': 'dialog_state_short_term_canonical_nucleus_is_frozen_and_global_continuity_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'boundary_and_degrade_surface_map_is_frozen_but_system_wide_boundary_constriction_remains_open',
        },
        'state_now_prefix': '- NOW (consultant-core fact contract schema, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Fact Contract Schema while the lock remains active.',
        'required_open_blockers': {
            'narrow_fact_family_cutover_is_the_next_runtime_admissible_block_after_fact_contract_schema',
            'frozen_legacy_modules_must_not_gain_new_authority_logic',
            'legacy_caller_surface_and_governance_delta_must_remain_machine_readable_and_in_sync',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    NARROW_FACT_FAMILY_CUTOVER_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system narrow fact-family cutover work inside the active block',
            '- Active block: `Consultant Core Narrow Fact-Family Cutover`',
            '- targeted `location / hours / parking` turns must route through `catalog.location` on the governed fact-plane hot path even when stale binding still points elsewhere',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Narrow Fact-Family Cutover is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system narrow fact-family cutover work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Narrow Fact-Family Cutover',
            '- complete `Continuity / State Normalization` before boundary constriction or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'whole_system_semantic_owner_path_is_frozen_but_post_owner_extraction_and_constriction_remain_open',
            'continuity_owner.cutover_status': 'dialog_state_short_term_canonical_nucleus_is_frozen_and_global_continuity_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'boundary_and_degrade_surface_map_is_frozen_but_system_wide_boundary_constriction_remains_open',
        },
        'state_now_prefix': '- NOW (consultant-core narrow fact-family cutover, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Narrow Fact-Family Cutover while the lock remains active.',
        'required_open_blockers': {
            'continuity_state_normalization_is_the_next_runtime_admissible_block_after_narrow_fact_family_cutover',
            'location_hours_parking_family_must_remain_bound_to_explicit_requested_allowed_emitted_scope_contract',
            'frozen_legacy_modules_must_not_gain_new_authority_logic',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    CONTINUITY_STATE_NORMALIZATION_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system continuity/state normalization work inside the active block',
            '- Active block: `Consultant Core Continuity / State Normalization`',
            '- canonical runtime writes must reproject active-slice compatibility continuity surfaces before post-owner semantic constriction resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Continuity / State Normalization is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system continuity/state normalization work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Continuity / State Normalization',
            '- complete `Post-Owner Semantic Constriction` before boundary constriction or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'whole_system_semantic_owner_path_is_frozen_but_post_owner_extraction_and_constriction_remain_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_but_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'boundary_and_degrade_surface_map_is_frozen_but_system_wide_boundary_constriction_remains_open',
        },
        'state_now_prefix': '- NOW (consultant-core continuity/state normalization, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Continuity / State Normalization while the lock remains active.',
        'required_open_blockers': {
            'post_owner_semantic_constriction_is_the_next_runtime_admissible_block_after_continuity_state_normalization',
            'compatibility_continuity_carriers_must_remain_derived_from_canonical_runtime_state_on_the_active_path',
            'broader_carryover_and_legacy_continuity_surfaces_remain_open_beyond_the_active_slice',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    POST_OWNER_SEMANTIC_CONSTRICTION_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system post-owner semantic constriction work inside the active block',
            '- Active block: `Consultant Core Post-Owner Semantic Constriction`',
            '- owner-backed executor/runtime/state seams must preserve canonical owner-authored semantic and pending-question contracts downstream before boundary constriction begins',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Post-Owner Semantic Constriction is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system post-owner semantic constriction work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Post-Owner Semantic Constriction',
            '- complete `Boundary Constriction` before pack/runtime separation or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_turns_now_preserve_owner_authored_semantic_contracts_downstream_but_boundary_and_legacy_semantic_surfaces_remain_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_but_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'boundary_and_degrade_surface_map_is_frozen_but_system_wide_boundary_constriction_remains_open',
        },
        'state_now_prefix': '- NOW (consultant-core post-owner semantic constriction, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Post-Owner Semantic Constriction while the lock remains active.',
        'required_open_blockers': {
            'boundary_constriction_is_the_next_runtime_admissible_block_after_post_owner_semantic_constriction',
            'boundary_and_degrade_still_remain_open_system_wide',
            'pack_runtime_separation_and_broader_fact_families_remain_open',
            'legacy_mesh_drain_remains_open',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    BOUNDARY_CONSTRICTION_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system boundary constriction work inside the active block',
            '- Active block: `Consultant Core Boundary Constriction`',
            '- boundary/degrade paths must stay inside the explicit handoff/system safe envelope and may not derive visible `fact/collect` reply kinds from owner outcome',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Boundary Constriction is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system boundary constriction work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Boundary Constriction',
            '- complete `Pack / Runtime Separation Completion` before legacy-mesh drain or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_turns_now_preserve_owner_authored_semantic_contracts_downstream_while_pack_runtime_and_legacy_semantic_surfaces_remain_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_but_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_but_fact_plane_and_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core boundary constriction, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Boundary Constriction while the lock remains active.',
        'required_open_blockers': {
            'pack_runtime_separation_is_the_next_runtime_admissible_block_after_boundary_constriction',
            'boundary_hotspot_freeze_and_reply_kind_narrowing_must_remain_machine_readable_and_in_sync',
            'pack_runtime_separation_and_broader_fact_families_remain_open',
            'legacy_mesh_drain_remains_open',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    PACK_RUNTIME_SEPARATION_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system pack/runtime separation work inside the active block',
            '- Active block: `Consultant Core Pack / Runtime Separation Completion`',
            '- active fact/service runtime callers must consume only the public `pack_runtime_service` helper seam; adapter-private helper calls may not re-enter the hot path',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Pack / Runtime Separation Completion is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system pack/runtime separation work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Pack / Runtime Separation Completion',
            '- complete `Legacy Mesh Drain` before shadow-lane elimination or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_turns_now_preserve_owner_authored_semantic_contracts_downstream_while_legacy_semantic_surfaces_remain_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_but_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_while_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core pack/runtime separation completion, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Pack / Runtime Separation Completion while the lock remains active.',
        'required_open_blockers': {
            'legacy_mesh_drain_is_the_next_runtime_admissible_block_after_pack_runtime_separation_completion',
            'public_pack_runtime_helper_surface_must_remain_the_only_active_hot_path_pack_runtime_behavior_seam',
            'broader_fact_families_and_pack_specific_truth_catalog_residue_remain_open',
            'legacy_mesh_drain_remains_open',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    LEGACY_MESH_DRAIN_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system legacy-mesh-drain work inside the active block',
            '- Active block: `Consultant Core Legacy Mesh Drain`',
            '- mounted webhook package exports must not depend on `decision.py`; router legacy surfaces may survive only as shadow/test or unmounted residue until shadow-lane elimination',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Legacy Mesh Drain is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system legacy-mesh-drain work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Legacy Mesh Drain',
            '- complete `Shadow Lane Elimination` before operational entrypoint dedupe or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_turns_now_preserve_owner_authored_semantic_contracts_downstream_while_shadow_wrapper_semantic_surfaces_remain_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_and_router_legacy_mesh_is_drained_from_live_runtime_but_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_router_legacy_boundary_helpers_are_drained_from_live_runtime_while_shadow_wrapper_boundary_surfaces_remain_open',
        },
        'state_now_prefix': '- NOW (consultant-core legacy mesh drain, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Legacy Mesh Drain while the lock remains active.',
        'required_open_blockers': {
            'shadow_lane_elimination_is_the_next_runtime_admissible_block_after_legacy_mesh_drain',
            'decision_router_and_legacy_bus_must_remain_shadow_only_and_outside_live_app_runtime',
            'broader_fact_families_and_pack_specific_truth_catalog_residue_remain_open',
            'shadow_lane_elimination_remains_open',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    SHADOW_LANE_ELIMINATION_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system shadow-lane-elimination work inside the active block',
            '- Active block: `Consultant Core Shadow Lane Elimination`',
            '- runtime shadow wrapper files `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/webhook.py` are removed; only test shadow supports may preserve those contracts while router shadow surfaces remain outside live app runtime',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Shadow Lane Elimination is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system shadow-lane-elimination work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Shadow Lane Elimination',
            '- complete `Operational Entrypoint Dedupe` before whole-system governance closure or replay',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_turns_now_preserve_owner_authored_semantic_contracts_downstream_and_runtime_shadow_wrapper_lanes_are_removed_while_operational_entrypoint_dedupe_remains_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_and_runtime_shadow_wrapper_lanes_are_removed_but_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_runtime_shadow_wrapper_boundary_surfaces_are_removed_while_operational_entrypoint_dedupe_and_broader_legacy_cleanup_remain_open',
        },
        'state_now_prefix': '- NOW (consultant-core shadow lane elimination, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Shadow Lane Elimination while the lock remains active.',
        'required_open_blockers': {
            'operational_entrypoint_dedupe_is_the_next_runtime_admissible_block_after_shadow_lane_elimination',
            'decision_router_and_legacy_bus_must_remain_shadow_only_and_outside_live_app_runtime',
            'broader_fact_families_and_pack_specific_truth_catalog_residue_remain_open',
            'whole_system_governance_closure_remains_open',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    OPERATIONAL_ENTRYPOINT_DEDUPE_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system operational-entrypoint-dedupe work inside the active block',
            '- Active block: `Consultant Core Operational Entrypoint Dedupe`',
            '- runtime shadow wrapper files remain removed, router shadow surfaces remain outside live app runtime, and live outbox execution surfaces now converge on shared runtime owners while `outbox_service_app.py` remains a thin dedicated composition root',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Operational Entrypoint Dedupe is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system operational-entrypoint-dedupe work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Operational Entrypoint Dedupe',
            '- complete `Whole-System Governance Closure` before replay or human audit',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_turns_now_preserve_owner_authored_semantic_contracts_downstream_runtime_shadow_wrapper_lanes_are_removed_and_operational_execution_surfaces_are_deduped_while_whole_system_governance_closure_remains_open',
            'continuity_owner.cutover_status': 'canonical_runtime_write_path_reprojects_compatibility_continuity_on_the_active_slice_operational_execution_surfaces_are_deduped_and_broader_carrier_collapse_remains_open',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_runtime_shadow_wrapper_boundary_surfaces_are_removed_and_operational_execution_surfaces_are_deduped_while_broader_legacy_cleanup_remains_open',
        },
        'state_now_prefix': '- NOW (consultant-core operational entrypoint dedupe, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Operational Entrypoint Dedupe while the lock remains active.',
        'required_open_blockers': {
            'whole_system_governance_closure_is_the_next_runtime_admissible_block_after_operational_entrypoint_dedupe',
            'outbox_service_app_remains_a_thin_dedicated_service_composition_root_until_final_governance_closure',
            'console_outbox_process_remains_a_live_scoped_operator_surface_but_must_stay_thin',
            'broader_fact_families_and_pack_specific_truth_catalog_residue_remain_open',
            'replay_and_human_audit_remain_forbidden_until_whole_system_architecture_blocks_close',
        },
        'requires_phase_advance_waiver': True,
    },
    CLOSURE_CLAIM_TRUTH_CORRECTION_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for closure-claim truth-correction work inside the active block',
            '- Active block: `Consultant Core Closure-Claim Truth Correction And Semantic-Owner Reopen`',
            '- Prior claims that repo-side semantic, post-owner, operational, and whole-system governance closure were complete are withdrawn after live-code verification.',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while the truth-correction block is active.',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for closure-claim truth-correction work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Closure-Claim Truth Correction And Semantic-Owner Reopen',
            '- complete semantic-owner and post-owner reconstruction reopen before any replay or closure claim',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_but_live_non_owner_control_paths_and_post_owner_semantic_reconstruction_keep_closure_open',
            'continuity_owner.cutover_status': 'canonical_runtime_reprojection_exists_but_boundary_resume_restore_and_broader_competing_carriers_keep_system_wide_continuity_open',
            'boundary_owner.cutover_status': 'boundary_reply_envelope_is_narrowed_but_boundary_resume_restore_and_continuity_shaping_keep_boundary_open',
        },
        'state_now_prefix': '- NOW (consultant-core closure-claim truth correction and semantic-owner reopen, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and invalidated whole-system closure claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule the truth-correction block while the lock remains active.',
        'required_open_blockers': {
            'single_semantic_owner_is_not_proven_and_live_non_owner_control_paths_remain',
            'post_owner_semantic_reconstruction_is_not_proven_and_downstream_semantic_contract_merging_remains',
            'continuity_boundary_pack_runtime_legacy_and_operational_closure_claims_require_reproof_after_semantic_owner_reopen',
            'replay_and_human_audit_remain_forbidden_until_truth_correction_and_semantic_owner_reopen_complete',
        },
        'requires_phase_advance_waiver': True,
    },
    SEMANTIC_OWNER_REOPEN_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: semantic-owner reopen is complete repo-side; broader continuity, boundary, pack/runtime, legacy, and operational reproof remains open',
            '- Active block: `Consultant Core Semantic Owner And Post-Owner Reconstruction Reopen`',
            '- The false closure claim has already been retracted; this block proves only the reopened hot-path semantic-owner invariant.',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while the semantic-owner reopen block is active.',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: semantic-owner reopen block is complete repo-side; broader live-code reproof is the next active runtime requirement',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Semantic Owner And Post-Owner Reconstruction Reopen',
            '- complete continuity, boundary, pack/runtime, legacy, and operational reproof before any replay or renewed whole-system closure claim',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'hot_path_single_semantic_owner_is_reproven_after_system_control_demotion_and_projection_reconstruction_removal_but_broader_system_reproof_remains_open',
            'continuity_owner.cutover_status': 'canonical_runtime_reprojection_exists_but_boundary_resume_restore_and_broader_competing_carriers_require_live_code_reproof',
            'boundary_owner.cutover_status': 'boundary_reply_envelope_is_narrowed_but_boundary_restore_and_continuity_shaping_require_live_code_reproof',
        },
        'state_now_prefix': '- NOW (consultant-core semantic-owner reopen closeout, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and invalidated whole-system closure claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule the semantic-owner reopen block while the lock remains active.',
        'required_open_blockers': {
            'continuity_boundary_pack_runtime_legacy_and_operational_closure_claims_still_require_live_code_reproof',
            'whole_system_governance_closure_cannot_be_reasserted_until_broader_reproof_confirms_remaining_invariants',
            'replay_and_human_audit_remain_forbidden_until_continuity_boundary_pack_runtime_legacy_and_operational_reproof_complete',
        },
        'requires_phase_advance_waiver': True,
    },
    SYSTEM_REPROOF_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: continuity, boundary, pack/runtime, legacy, and operational reproof is complete repo-side; replay and full human semantic audit are the next admissible acceptance lane',
            '- Active block: `Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof`',
            '- This block does not claim product or practical closure; it only reproves the remaining live-code architecture claims in the reopened envelope.',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while the live-code reproof block is active.',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: broader live-code reproof is complete repo-side; acceptance is now the next admissible lane',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof',
            '- run fresh replay and full human semantic audit before any product or practical closure claim',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'hot_path_single_semantic_owner_remains_reproven_and_adjacent_runtime_reproof_is_complete_repo_side_pending_acceptance',
            'continuity_owner.cutover_status': 'canonical_runtime_continuity_and_boundary_resume_restore_are_reproven_against_live_code_pending_acceptance',
            'boundary_owner.cutover_status': 'boundary_reply_envelope_and_restore_constraints_are_reproven_against_live_code_pending_acceptance',
        },
        'state_now_prefix': '- NOW (consultant-core continuity-boundary-pack-runtime-legacy-operational reproof closeout, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and invalidated whole-system closure claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule the live-code reproof block while the lock remains active.',
        'required_open_blockers': {
            'fresh_replay_and_full_human_semantic_audit_are_required_before_product_or_practical_closure_claim',
            'current_practical_truth_remains_r35f_until_acceptance_lane_proves_improvement',
            'whole_system_done_or_green_claims_remain_forbidden_until_acceptance_lane_passes',
        },
        'requires_phase_advance_waiver': True,
    },
    WHOLE_SYSTEM_GOVERNANCE_CLOSURE_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for whole-system governance-closure work inside the active block',
            '- Active block: `Consultant Core Whole-System Governance Closure`',
            '- repo-side semantic, continuity, fact, boundary, legacy, shadow, and operational architecture recovery is closed; only replay and full human semantic audit remain admissible next',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while Whole-System Governance Closure is active',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for whole-system governance-closure work inside the active block',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials and canary-only closeout claims remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Whole-System Governance Closure',
            '- run fresh replay and full human semantic audit before any product or practical closure claim',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'whole_system_semantic_owner_authority_is_repo_closed_and_acceptance_now_depends_only_on_fresh_replay_and_full_human_semantic_audit',
            'continuity_owner.cutover_status': 'whole_system_continuity_governance_is_repo_closed_and_acceptance_now_depends_only_on_fresh_replay_and_full_human_semantic_audit',
            'boundary_owner.cutover_status': 'whole_system_boundary_governance_is_repo_closed_and_acceptance_now_depends_only_on_fresh_replay_and_full_human_semantic_audit',
        },
        'state_now_prefix': '- NOW (consultant-core whole-system governance closure, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` replay/RCA/runtime entries and canary-only closeout claims preserved below remain historical residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active whole-system program and they do not overrule Whole-System Governance Closure while the lock remains active.',
        'required_open_blockers': {
            'fresh_replay_and_full_human_semantic_audit_are_the_only_remaining_acceptance_lane',
            'product_and_practical_closure_remain_open_until_acceptance_lane_passes',
            'canonical_baseline_update_remains_forbidden_until_valid_acceptance_run',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK2_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first governance work inside the active block',
            '- Active block: `Consultant Core Authority Registry And Writer-Law Enforcement`',
            '- materialize the machine-readable authority topology and writer-law guard base before any runtime slice resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 2 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-2 governance work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Authority Registry And Writer-Law Enforcement',
            '- materialize the machine-readable authority topology and writer-law guard base before any runtime slice resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'viable_owner_path_exists_but_post_owner_semantic_reconstruction_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_but_competing_continuity_carriers_and_compatibility_writers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_seams_exist_but_deterministic_boundary_overreach_and_legacy_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core recovery execution lock, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 2 while the lock remains active.',
        'required_open_blockers': {
            'owner_status_fields_and_registry_phase_credit_must_remain_block2_honest',
        },
        'requires_phase_advance_waiver': False,
    },
    BLOCK3_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first governance work inside the active block',
            '- Active block: `Consultant Core Truth-Carrier Inventory And Freeze`',
            '- freeze the continuity carrier inventory into an enforceable writer/read precedence and no-new-writer guard before legacy mesh or runtime constriction resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 3 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-3 governance work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Truth-Carrier Inventory And Freeze',
            '- freeze the continuity carrier inventory into an enforceable writer/read precedence and no-new-writer guard before legacy mesh or runtime constriction resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'viable_owner_path_exists_but_post_owner_semantic_reconstruction_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_and_truth_carrier_freeze_law_is_active_but_competing_runtime_and_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_seams_exist_but_deterministic_boundary_overreach_and_legacy_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core truth-carrier freeze activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 3 while the lock remains active.',
        'required_open_blockers': {
            'continuity_freeze_law_and_guard_contract_must_remain_machine_readable_and_in_sync',
            'no_runtime_cutover_is_admissible_until_truth_carrier_freeze_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK4_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first governance work inside the active block',
            '- Active block: `Consultant Core Adapter-Only Legacy Mesh And Caller Proof`',
            '- freeze the legacy mesh into machine-readable caller proof and adapter-only classification before post-owner runtime constriction resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 4 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-4 governance work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Adapter-Only Legacy Mesh And Caller Proof',
            '- freeze the legacy mesh into machine-readable caller proof and adapter-only classification before post-owner runtime constriction resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'viable_owner_path_exists_but_post_owner_semantic_reconstruction_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_and_truth_carrier_freeze_law_is_active_but_competing_runtime_and_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_seams_exist_but_deterministic_boundary_overreach_and_legacy_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core legacy mesh caller-proof activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 4 while the lock remains active.',
        'required_open_blockers': {
            'legacy_mesh_caller_proof_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'behavior_owning_legacy_surfaces_remain_live_and_must_not_be_treated_as_adapter_only',
            'legacy_caller_proof_and_dead_surface_classification_must_remain_machine_readable_and_in_sync',
            'no_runtime_constriction_is_admissible_until_legacy_mesh_caller_proof_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK5_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first governance work inside the active block',
            '- Active block: `Consultant Core Post-Owner Reconstruction Constriction`',
            '- freeze the post-owner reconstruction hotspots and mutation-guard proof before boundary/degrade constriction resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 5 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-5 governance/proof work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Post-Owner Reconstruction Constriction',
            '- freeze the post-owner reconstruction hotspots and mutation-guard proof before boundary/degrade constriction resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_and_post_owner_reconstruction_guard_is_active_but_boundary_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_and_truth_carrier_freeze_law_is_active_but_competing_runtime_and_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_seams_exist_but_deterministic_boundary_overreach_and_legacy_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core post-owner reconstruction activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 5 while the lock remains active.',
        'required_open_blockers': {
            'post_owner_reconstruction_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'post_owner_hotspot_freeze_and_mutation_guard_proof_must_remain_machine_readable_and_in_sync',
            'no_boundary_or_fact_plane_phase_advance_is_admissible_until_post_owner_reconstruction_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK6_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first work inside the active block',
            '- Active block: `Consultant Core Boundary/Degrade Constriction`',
            '- freeze the boundary/degrade hotspots and narrow typed override authority before fact-plane materialization resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 6 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-6 mechanism work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Boundary/Degrade Constriction',
            '- freeze the boundary/degrade hotspots and narrow typed override authority before fact-plane materialization resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_and_post_owner_reconstruction_guard_is_active_but_boundary_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_and_truth_carrier_freeze_law_is_active_but_competing_runtime_and_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_but_fact_plane_and_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core boundary/degrade activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 6 while the lock remains active.',
        'required_open_blockers': {
            'boundary_degrade_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'boundary_hotspot_freeze_and_typed_override_narrowing_must_remain_machine_readable_and_in_sync',
            'fact_plane_materialization_is_blocked_until_boundary_degrade_constriction_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK7_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first work inside the active block',
            '- Active block: `Consultant Core Fact-Plane Materialization`',
            '- materialize the explicit fact request/fact plan/fact result contract chain before first fact-family cutover resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 7 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-7 mechanism work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Fact-Plane Materialization',
            '- materialize the explicit fact request/fact plan/fact result contract chain before first fact-family cutover resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_and_post_owner_reconstruction_guard_is_active_but_boundary_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_and_truth_carrier_freeze_law_is_active_but_competing_runtime_and_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_but_fact_plane_and_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core fact-plane activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 7 while the lock remains active.',
        'required_open_blockers': {
            'fact_plane_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'fact_plane_contract_chain_and_emitted_scope_guard_must_remain_machine_readable_and_in_sync',
            'first_fact_family_cutover_is_blocked_until_fact_plane_materialization_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK8_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first work inside the active block',
            '- Active block: `Consultant Core First Fact-Family Cutover`',
            '- normalize pending-question and interaction continuity for the touched fact-family slice before legacy drain resumes',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 8 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-8 mechanism work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core First Fact-Family Cutover',
            '- normalize pending-question and interaction continuity for the touched fact-family slice before legacy drain resumes',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_and_post_owner_reconstruction_guard_is_active_but_boundary_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_and_truth_carrier_freeze_law_is_active_but_competing_runtime_and_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_but_fact_plane_and_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core first fact-family cutover activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 8 while the lock remains active.',
        'required_open_blockers': {
            'first_fact_family_cutover_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'first_fact_family_cutover_guard_and_authority_registry_contract_must_remain_machine_readable_and_in_sync',
            'touched_slice_continuity_normalization_is_blocked_until_first_fact_family_cutover_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK9_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first work inside the active block',
            '- Active block: `Consultant Core Touched-Slice Continuity Normalization`',
            '- drain the remaining legacy behavior authority and prove old paths are adapter-only or unreachable for the touched mechanism envelope',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 9 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-9 mechanism work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Touched-Slice Continuity Normalization',
            '- drain the remaining legacy behavior authority and prove old paths are adapter-only or unreachable for the touched mechanism envelope',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_and_post_owner_reconstruction_guard_is_active_but_boundary_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'first_fact_family_touched_slice_is_normalized_into_canonical_runtime_but_broader_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_but_fact_plane_and_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core touched-slice continuity activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 9 while the lock remains active.',
        'required_open_blockers': {
            'touched_slice_continuity_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'touched_slice_continuity_guard_and_runtime_to_compatibility_projection_must_remain_machine_readable_and_in_sync',
            'legacy_drain_and_proof_closure_is_blocked_until_touched_slice_continuity_normalization_is_accepted',
        },
        'requires_phase_advance_waiver': True,
    },
    BLOCK10_TP: {
        'canon_snippets': [
            '- Current practical truth: `r35f`',
            '- Runtime implementation status: paused except for root-first work inside the active block',
            '- Active block: `Consultant Core Legacy Drain And Proof Closure`',
            '- run fresh practical replay and full human semantic audit for the recovered canary mechanism envelope',
            '- Historical residue rule: later `r36*` replay/RCA/runtime materials remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while block 10 is locked',
        ],
        'program_snippets': [
            '- practical truth: `r35f`',
            '- implementation state: runtime implementation is paused except for block-10 mechanism work',
            '- historical residue rule: later `r36*` replay/RCA/runtime materials remain non-governing history under `docs/RECOVERY_EXECUTION_LOCK.yaml`',
            '- Consultant Core Legacy Drain And Proof Closure',
            '- run fresh practical replay and full human semantic audit for the recovered canary mechanism envelope',
        ],
        'owner_status': {
            'semantic_owner.cutover_status': 'owner_backed_hot_path_exists_and_post_owner_reconstruction_guard_is_active_but_boundary_and_compatibility_pressure_remain_live',
            'continuity_owner.cutover_status': 'first_fact_family_touched_slice_is_normalized_into_canonical_runtime_and_final_legacy_drain_proof_is_active_but_broader_compatibility_carriers_remain_live',
            'boundary_owner.cutover_status': 'typed_boundary_guard_is_active_and_reply_kind_forcing_is_narrowed_but_fact_plane_and_legacy_compatibility_boundary_helpers_remain_live',
        },
        'state_now_prefix': '- NOW (consultant-core legacy drain activation, consultant-core):',
        'state_note_prefix': '- NOTE (consultant-core governing base): later `r36*` and post-block-2 runtime/RCA entries preserved below remain historical drift residue under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they are not the active program, they do not advance phase credit, and they do not overrule block 10 while the lock remains active.',
        'required_open_blockers': {
            'legacy_drain_block_remains_the_active_governing_block_until_owner_or_architect_phase_advance',
            'legacy_drain_closure_guard_and_dead_surface_registry_must_remain_machine_readable_and_in_sync',
            'practical_replay_and_full_human_semantic_audit_remain_required_after_block_10',
        },
        'requires_phase_advance_waiver': True,
    },
}

FORBIDDEN_BLOCK2_EVIDENCE = {
    'docs/SEMANTIC_BRIDGE_GUARD.yaml',
    'docs/BOUNDARY_DEGRADE_GUARD.yaml',
    'docs/FACT_PLANE_GUARD.yaml',
    'docs/FACT_FAMILY_CUTOVER_GUARD.yaml',
    'docs/TOUCHED_SLICE_CONTINUITY_GUARD.yaml',
    'docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml',
    'scripts/semantic_bridge_growth_guard.py',
    'scripts/boundary_degrade_guard.py',
    'scripts/fact_plane_guard.py',
    'scripts/fact_family_cutover_guard.py',
    'scripts/touched_slice_continuity_guard.py',
    'scripts/legacy_drain_closure_guard.py',
    'docs/REPORTS/2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md',
    'docs/REPORTS/2026-03-30-consultant-core-boundary-degrade-constriction-a922.md',
    'docs/REPORTS/2026-03-30-consultant-core-fact-plane-materialization-a922.md',
    'docs/REPORTS/2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md',
    'docs/REPORTS/2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md',
    'docs/REPORTS/2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md',
}

DISALLOWED_ACTIVE_TOKENS = [
    'r36g',
    'booking-manage temporal clue grounding',
    'consult/media cue continuity',
    'run fresh practical replay and full human semantic audit for the recovered canary mechanism envelope',
]

STATE_HISTORICAL_TOKENS = [
    'r36g',
    'consult/media cue continuity',
    'booking-manage temporal clue grounding',
]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: YAML document must be a mapping: {path}')
    return data


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: JSON document must be an object: {path}')
    return data


def _collect_block2_registry_honesty_errors(root: Path, truth: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if truth.get('active_block_tp') != BLOCK2_TP:
        return errors
    authority = _load_json(root / 'docs' / 'system_forensics' / 'authority_registry.json')
    carriers = _load_json(root / 'docs' / 'system_forensics' / 'compatibility_carrier_inventory.json')
    surfaces = _load_json(root / 'docs' / 'system_forensics' / 'dead_surface_registry.json')

    for entry in authority.get('entries', []):
        bad = sorted(FORBIDDEN_BLOCK2_EVIDENCE.intersection(entry.get('evidence', [])))
        if bad:
            errors.append(f"authority_registry entry {entry.get('mechanism_id')} still cites later-phase evidence: {', '.join(bad)}")
    for entry in carriers.get('carriers', []):
        bad = sorted(FORBIDDEN_BLOCK2_EVIDENCE.intersection(entry.get('evidence', [])))
        if bad:
            errors.append(f"compatibility_carrier_inventory entry {entry.get('carrier_id')} still cites later-phase evidence: {', '.join(bad)}")
    for key in ['freeze_guard', 'reader_precedence_law']:
        section = carriers.get(key, {})
        if isinstance(section, dict):
            bad = sorted(FORBIDDEN_BLOCK2_EVIDENCE.intersection(section.get('evidence', [])))
            if bad:
                errors.append(f"compatibility_carrier_inventory {key} still cites later-phase evidence: {', '.join(bad)}")
    bad = sorted(FORBIDDEN_BLOCK2_EVIDENCE.intersection(surfaces.get('caller_proof_law', {}).get('evidence', [])))
    if bad:
        errors.append(f"dead_surface_registry caller_proof_law still cites later-phase evidence: {', '.join(bad)}")
    for forbidden_key in ['adapter_only_for_touched_envelope', 'startup_load_drained_from_package_root', 'unreachable_for_touched_envelope']:
        if forbidden_key in surfaces.get('caller_proof_law', {}):
            errors.append(f"dead_surface_registry caller_proof_law must not expose later-phase proof key while block 2 is active: {forbidden_key}")
    return errors


def collect_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    lock = _load_yaml(root / 'docs' / 'RECOVERY_EXECUTION_LOCK.yaml')
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    waiver = _load_yaml(root / 'docs' / 'RECOVERY_PHASE_WAIVER.yaml')
    authority = _load_json(root / 'docs' / 'system_forensics' / 'authority_registry.json')
    dead_surface = _load_json(root / 'docs' / 'system_forensics' / 'dead_surface_registry.json')
    packet_json = _load_json(root / 'docs' / '_generated' / 'AGENT_PACKET.json')
    active_canon = (root / 'docs' / 'ACTIVE_CANON.md').read_text(encoding='utf-8')
    active_program = (root / 'docs' / 'ACTIVE_PROGRAM.md').read_text(encoding='utf-8')
    state_lines = (root / 'STATE.md').read_text(encoding='utf-8').splitlines()

    root_ctx = lock['root_first_context']
    expected_block = root_ctx['active_block']
    expected_block_tp = root_ctx['active_block_tp']
    expected_truth = root_ctx['current_practical_truth']
    expected_report = root_ctx['current_practical_report']
    expected_next_move = root_ctx['current_non_negotiable_next_move']
    expected_history_rule = root_ctx['historical_residue_rule']
    waiver_path = lock['phase_advance']['waiver_file']

    block_expectations = BLOCK_EXPECTATIONS.get(expected_block_tp)
    if block_expectations is None:
        return [f'unsupported active block for recovery execution guard: {expected_block_tp}']

    if truth.get('recovery_execution_lock') != 'docs/RECOVERY_EXECUTION_LOCK.yaml':
        errors.append('docs/SOURCE_OF_TRUTH.yaml must point to docs/RECOVERY_EXECUTION_LOCK.yaml')
    if truth.get('active_block_tp') != expected_block_tp:
        errors.append('docs/SOURCE_OF_TRUTH.yaml active_block_tp drifted away from the recovery execution lock')
    current_truth = truth.get('current_practical_truth', {})
    if current_truth.get('label') != expected_truth:
        errors.append('docs/SOURCE_OF_TRUTH.yaml current practical truth drifted away from the recovery execution lock')
    if current_truth.get('report') != expected_report:
        errors.append('docs/SOURCE_OF_TRUTH.yaml current practical report drifted away from the recovery execution lock')
    if truth.get('current_non_negotiable_next_move') != expected_next_move:
        errors.append('docs/SOURCE_OF_TRUTH.yaml current_non_negotiable_next_move must match the recovery execution lock')
    exec_strategy = truth.get('execution_strategy', {})
    if exec_strategy.get('current_nonnegotiable_next_move') != expected_next_move:
        errors.append('execution_strategy.current_nonnegotiable_next_move must match the recovery execution lock')
    if truth.get('program', {}).get('current_block') != expected_block:
        errors.append('program.current_block must match the recovery execution lock')
    if truth.get('program', {}).get('historical_residue_rule') != expected_history_rule:
        errors.append('program.historical_residue_rule must match the recovery execution lock')
    if lock.get('phase_advance', {}).get('waiver_file') != waiver_path:
        errors.append('recovery execution lock waiver_file must be self-consistent')

    program_open_blockers = set(truth.get('program', {}).get('open_blockers', []) or [])
    missing_open_blockers = sorted(block_expectations['required_open_blockers'].difference(program_open_blockers))
    if missing_open_blockers:
        errors.append(
            'program.open_blockers is missing active-block stop-line blockers: ' + ', '.join(missing_open_blockers)
        )

    for dotted_key, expected_value in block_expectations['owner_status'].items():
        section_name, key = dotted_key.split('.', 1)
        section = truth.get(section_name, {})
        actual_value = section.get(key) if isinstance(section, dict) else None
        if actual_value != expected_value:
            errors.append(f'docs/SOURCE_OF_TRUTH.yaml {dotted_key} drifted away from the active recovery lock')

    if block_expectations['requires_phase_advance_waiver']:
        if waiver.get('status') == 'absent':
            errors.append('docs/RECOVERY_PHASE_WAIVER.yaml must record the explicit phase advance while the active block is phase-advanced')
        if not waiver.get('allows', {}).get('phase_advance'):
            errors.append('docs/RECOVERY_PHASE_WAIVER.yaml allows.phase_advance must remain true while the active phase advance is in force')
        if not isinstance(waiver.get('approved_by'), str) or not waiver.get('approved_by'):
            errors.append('docs/RECOVERY_PHASE_WAIVER.yaml must record who approved the phase advance')
    else:
        if waiver.get('status') != 'absent':
            errors.append('docs/RECOVERY_PHASE_WAIVER.yaml must stay absent unless owner/architect explicitly advances phase')
        if waiver.get('approved_by') is not None:
            errors.append('docs/RECOVERY_PHASE_WAIVER.yaml approved_by must remain null without explicit waiver')

    allows = waiver.get('allows', {})
    if allows.get('practical_truth_advance') is not False:
        errors.append('docs/RECOVERY_PHASE_WAIVER.yaml allows.practical_truth_advance must remain false')
    if allows.get('runtime_resume') is not False:
        errors.append('docs/RECOVERY_PHASE_WAIVER.yaml allows.runtime_resume must remain false')
    if not block_expectations['requires_phase_advance_waiver'] and allows.get('phase_advance') is not False:
        errors.append('docs/RECOVERY_PHASE_WAIVER.yaml allows.phase_advance must remain false without explicit phase advance')

    if authority.get('current_practical_truth') != expected_truth:
        errors.append('authority_registry current_practical_truth must match the recovery execution lock')
    if authority.get('active_block') != expected_block:
        errors.append('authority_registry active_block must match the recovery execution lock')
    if dead_surface.get('current_practical_truth') != expected_truth:
        errors.append('dead_surface_registry current_practical_truth must match the recovery execution lock')
    if dead_surface.get('active_block') != expected_block:
        errors.append('dead_surface_registry active_block must match the recovery execution lock')

    for snippet in block_expectations['canon_snippets']:
        if snippet not in active_canon:
            errors.append(f'docs/ACTIVE_CANON.md missing required lock-aligned text: {snippet}')
    for snippet in block_expectations['program_snippets']:
        if snippet not in active_program:
            errors.append(f'docs/ACTIVE_PROGRAM.md missing required lock-aligned text: {snippet}')
    for token in DISALLOWED_ACTIVE_TOKENS:
        if token in active_canon:
            errors.append(f'docs/ACTIVE_CANON.md still contains drift token: {token}')
        if token in active_program:
            errors.append(f'docs/ACTIVE_PROGRAM.md still contains drift token: {token}')

    if len(state_lines) < 2 or not state_lines[0].startswith(block_expectations['state_now_prefix']):
        errors.append('STATE.md first line must keep the active-block recovery prefix')
    if len(state_lines) < 2 or not state_lines[1].startswith(block_expectations['state_note_prefix']):
        errors.append('STATE.md second line must keep the historical-residue note aligned to the active lock')
    for line in state_lines[:20]:
        for token in STATE_HISTORICAL_TOKENS:
            if token in line and line.startswith('- NOW ('):
                errors.append(f'STATE.md historical residue token must not appear in a NOW entry while the lock is active: {token}')

    errors.extend(_collect_block2_registry_honesty_errors(root, truth))

    if packet_json.get('active_block_tp') != expected_block_tp:
        errors.append('generated AGENT_PACKET.json active_block_tp must match the recovery execution lock')
    if packet_json.get('active_master_block') != expected_block:
        errors.append('generated AGENT_PACKET.json active_master_block must match the recovery execution lock')
    if packet_json.get('historical_residue_rule') != expected_history_rule:
        errors.append('generated AGENT_PACKET.json historical_residue_rule must match the recovery execution lock')
    source_map = packet_json.get('source_of_truth_map', {})
    if source_map.get('current_non_negotiable_next_move') != expected_next_move:
        errors.append('generated AGENT_PACKET.json current_non_negotiable_next_move must match the recovery execution lock')
    if source_map.get('recovery_execution_lock') != 'docs/RECOVERY_EXECUTION_LOCK.yaml':
        errors.append('generated AGENT_PACKET.json must expose the recovery execution lock path')
    if 'recovery_execution_lock_map' not in packet_json:
        errors.append('generated AGENT_PACKET.json must expose the recovery execution lock contents')

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'recovery_execution_guard: FAIL: {error}', file=sys.stderr)
        return 1
    print('recovery_execution_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
