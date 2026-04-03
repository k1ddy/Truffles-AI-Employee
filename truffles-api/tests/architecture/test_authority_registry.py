from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def _load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def _load_yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text(encoding='utf-8'))


def test_authority_registry_matches_truth_correction_block_and_hot_path() -> None:
    truth = _load_yaml('docs/SOURCE_OF_TRUTH.yaml')
    authority_registry = _load_json(truth['authority_registry'])

    assert authority_registry['schema_version'] == 'v2'
    assert authority_registry['status'] == 'machine_readable_system_reproof_base'
    assert authority_registry['active_block'] == 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization'
    assert authority_registry['current_practical_truth'] == 'r35f'
    assert authority_registry['mounted_runtime_topology']['hot_path'] == [
        'truffles-api/app/core/consultant_core_v2.py',
        'truffles-api/app/core/consultant_runtime.py',
        'truffles-api/app/core/turn_planner.py',
        'truffles-api/app/services/intent_service.py',
        'truffles-api/app/core/turn_executor.py',
        'truffles-api/app/core/dialog_state_service.py',
    ]

    entries = {entry['mechanism_id']: entry for entry in authority_registry['entries']}
    assert entries['semantic_turn_meaning']['current_primary_actor_paths'] == [
        'truffles-api/app/services/intent_service.py',
        'truffles-api/app/core/turn_planner.py',
    ]
    assert entries['semantic_turn_meaning']['current_competing_writer_paths'] == []
    assert entries['semantic_turn_meaning']['next_phase_required'] == 'replay_and_human_audit_acceptance'
    assert entries['semantic_turn_meaning']['full_closure_phase'] == 'semantic_owner_and_post_owner_reconstruction_reopen'
    assert 'docs/SEMANTIC_OWNER_REOPEN_GUARD.yaml' in entries['semantic_turn_meaning']['evidence']
    assert 'scripts/semantic_owner_reopen_guard.py' in entries['semantic_turn_meaning']['evidence']
    assert entries['post_owner_semantic_reconstruction']['current_live_caller_paths'] == [
        'truffles-api/app/core/consultant_runtime.py',
        'truffles-api/app/core/turn_planner.py',
        'truffles-api/app/core/turn_executor.py',
        'truffles-api/app/core/dialog_state_service.py',
    ]
    assert entries['post_owner_semantic_reconstruction']['current_competing_writer_paths'] == []
    assert entries['post_owner_semantic_reconstruction']['next_phase_required'] == 'replay_and_human_audit_acceptance'
    assert entries['continuity_state']['next_phase_required'] == 'replay_and_human_audit_acceptance'
    assert entries['boundary_and_degrade']['next_phase_required'] == 'replay_and_human_audit_acceptance'
    assert entries['fact_scope']['next_phase_required'] == 'replay_and_human_audit_acceptance'
    assert entries['legacy_behavior_authority']['next_phase_required'] == 'replay_and_human_audit_acceptance'


def test_compatibility_carrier_inventory_and_truth_show_reopened_status() -> None:
    truth = _load_yaml('docs/SOURCE_OF_TRUTH.yaml')
    inventory = _load_json(truth['compatibility_carrier_inventory'])

    assert truth['semantic_owner']['cutover_status'] == 'owner_path_is_real_and_block_a_interrupt_arbitration_plus_block_e5_owner_service_referent_grounding_are_closed_on_touched_envelopes_but_full_single_semantic_owner_closure_still_remains_partial'
    assert truth['continuity_owner']['cutover_status'] == 'block_c_closed_proven_on_touched_followup_resume_paths_compatibility_carriers_are_now_derived_only'
    assert truth['boundary_owner']['cutover_status'] == 'block_d_boundary_purification_is_closed_on_live_runtime_path_and_stale_boundary_restore_helpers_are_guarded_as_non_runtime_residue'
    assert truth['program']['current_block'] == 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization'
    assert inventory['status'] == 'machine_readable_system_reproof_base'
    assert inventory['active_block'] == 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization'


def test_dead_surface_and_legacy_caller_registries_no_longer_claim_final_closure() -> None:
    truth = _load_yaml('docs/SOURCE_OF_TRUTH.yaml')
    dead = _load_json(truth['dead_surface_registry'])
    callers = _load_json(truth['legacy_caller_surface'])
    delta = _load_json(truth['governance_delta'])

    assert dead['status'] == 'machine_readable_system_reproof_base'
    assert callers['status'] == 'machine_readable_system_reproof_base'
    assert delta['status'] == 'machine_readable_system_reproof_delta'
    assert delta['active_block'] == 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization'
    assert delta['deferred_next_blocks'] == ['block_h_final_acceptance']
