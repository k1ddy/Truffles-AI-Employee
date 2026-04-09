from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'scripts'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_agent_packet_and_top_level_consistency() -> None:
    build_agent_packet = load_module('build_agent_packet', SCRIPTS / 'build_agent_packet.py')
    arch_guard = load_module('arch_guard', SCRIPTS / 'arch_guard.py')

    truth = build_agent_packet.load_yaml(ROOT / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    legacy = build_agent_packet.load_yaml(ROOT / 'docs' / 'LEGACY_SUNSET.yaml')
    build_agent_packet.validate_source_of_truth(ROOT, truth, legacy)
    packet = build_agent_packet.build_packet(ROOT, truth, legacy)
    markdown = build_agent_packet.render_markdown(packet)

    assert packet['active_dec'].endswith('whole-system-architecture-closure-governing-decision.md')
    assert packet['active_master_tp'] == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md'
    assert packet['active_block_tp'] == 'docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h1b-file-replay-scenario-contract-materialization-a922.md'
    assert packet['active_master_block'] == 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization'
    assert packet['recovery_execution_lock_map']['root_first_context']['active_block'] == 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization'
    assert packet['historical_residue_rule'] == 'older_whole_system_reproof_and_invalidated_closure_claims_remain_non_governing_history_while_the_block_plan_is_active'
    assert packet['source_of_truth_map']['current_non_negotiable_next_move'] == 'rerun_block_h_final_acceptance_after_closing_block_h1b_file_replay_scenario_contract_materialization_20260401'
    assert packet['source_of_truth_map']['semantic_owner']['cutover_status'] == 'owner_path_is_real_and_block_a_interrupt_arbitration_plus_block_e5_owner_service_referent_grounding_are_closed_on_touched_envelopes_but_full_single_semantic_owner_closure_still_remains_partial'
    assert packet['source_of_truth_map']['continuity_owner']['cutover_status'] == 'block_c_closed_proven_on_touched_followup_resume_paths_compatibility_carriers_are_now_derived_only'
    assert packet['source_of_truth_map']['boundary_owner']['cutover_status'] == 'block_d_boundary_purification_is_closed_on_live_runtime_path_and_stale_boundary_restore_helpers_are_guarded_as_non_runtime_residue'
    assert packet['current_runtime_cutover_status']['authority_topology'] == 'block_plan_execution_has_block_a_block_b_block_c_block_c5_block_d_block_e_block_e5_block_e6_block_f_block_g_booking_manage_temporal_clue_followup_continuity_block_h1_oracle_scenario_contract_alignment_and_block_h1b_file_replay_scenario_contract_materialization_closed_proven_block_h_is_next'
    assert 'python3 scripts/recovery_execution_guard.py' in packet['required_checks']
    assert 'PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_diagnose_run_command.py -k "scenarios_file or materialize"' in packet['required_checks']
    assert 'fresh_replay_and_full_human_semantic_audit_are_required_before_product_or_practical_closure_claim' in packet['open_blockers']
    assert 'whole_system_done_or_green_claims_remain_forbidden_until_acceptance_lane_passes' in packet['open_blockers']
    assert 'block_h_final_acceptance_replay_and_full_human_semantic_audit_remain_open_after_block_h1b_file_replay_scenario_contract_materialization_closeout' in packet['open_blockers']
    assert packet['machine_readable_governance']['authority_registry']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['compatibility_carrier_inventory']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['dead_surface_registry']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['legacy_caller_surface']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['governance_delta']['status'] == 'machine_readable_system_reproof_delta'
    assert 'Consultant Core Block H.1B — File Replay Scenario Contract Materialization' in markdown
    assert 'AGENT PACKET' in markdown
    assert arch_guard.validate_top_level_consistency(ROOT, truth, legacy) == []
