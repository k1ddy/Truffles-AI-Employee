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
    assert packet['active_block_tp'] == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md'
    assert packet['active_master_block'] == 'Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof'
    assert packet['recovery_execution_lock_map']['root_first_context']['active_block'] == 'Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof'
    assert packet['historical_residue_rule'] == 'later_r36_star_and_invalidated_whole_system_closure_claims_remain_non_governing_history_while_the_live_code_reproof_block_is_active'
    assert packet['source_of_truth_map']['current_non_negotiable_next_move'] == 'run_replay_and_full_human_semantic_audit_before_any_product_or_practical_closure_claim'
    assert packet['source_of_truth_map']['semantic_owner']['cutover_status'] == 'hot_path_single_semantic_owner_remains_reproven_and_adjacent_runtime_reproof_is_complete_repo_side_pending_acceptance'
    assert packet['source_of_truth_map']['continuity_owner']['cutover_status'] == 'canonical_runtime_continuity_and_boundary_resume_restore_are_reproven_against_live_code_pending_acceptance'
    assert packet['source_of_truth_map']['boundary_owner']['cutover_status'] == 'boundary_reply_envelope_and_restore_constraints_are_reproven_against_live_code_pending_acceptance'
    assert packet['current_runtime_cutover_status']['authority_topology'] == 'continuity_boundary_pack_runtime_legacy_and_operational_reproof_is_complete_repo_side_pending_acceptance'
    assert 'python3 scripts/system_reproof_guard.py' in packet['required_checks']
    assert 'PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_system_reproof_guard.py' in packet['required_checks']
    assert 'fresh_replay_and_full_human_semantic_audit_are_required_before_product_or_practical_closure_claim' in packet['open_blockers']
    assert 'whole_system_done_or_green_claims_remain_forbidden_until_acceptance_lane_passes' in packet['open_blockers']
    assert packet['machine_readable_governance']['authority_registry']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['compatibility_carrier_inventory']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['dead_surface_registry']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['legacy_caller_surface']['status'] == 'machine_readable_system_reproof_base'
    assert packet['machine_readable_governance']['governance_delta']['status'] == 'machine_readable_system_reproof_delta'
    assert 'Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof' in markdown
    assert 'AGENT PACKET' in markdown
    assert arch_guard.validate_top_level_consistency(ROOT, truth, legacy) == []
