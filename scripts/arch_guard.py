#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"ERROR: cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_top_level_consistency(root: Path, truth: dict, legacy: dict) -> list[str]:
    build_agent_packet = load_module('build_agent_packet', root / 'scripts' / 'build_agent_packet.py')
    errors = build_agent_packet.collect_source_of_truth_errors(root, truth, legacy)
    errors.extend(build_agent_packet.collect_governance_registry_errors(root, truth))
    errors.extend(build_agent_packet.collect_recovery_execution_lock_errors(root, truth))
    return errors


def guard_scripts_for_active_block(truth: dict) -> list[str]:
    active_block_tp = truth.get('active_block_tp')
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md':
        return ['recovery_execution_guard.py', 'whole_system_program_guard.py']
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-authority-freeze-a922.md':
        return ['recovery_execution_guard.py', 'authority_freeze_guard.py', 'legacy_freeze_guard.py']
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-fact-contract-schema-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_contract_schema_guard.py',
            'fact_plane_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-state-normalization-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-post-owner-semantic-constriction-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-boundary-constriction-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'pack_runtime_separation_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'pack_runtime_separation_guard.py',
            'legacy_mesh_drain_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-shadow-lane-elimination-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'pack_runtime_separation_guard.py',
            'legacy_mesh_drain_guard.py',
            'shadow_lane_elimination_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-operational-entrypoint-dedupe-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'pack_runtime_separation_guard.py',
            'legacy_mesh_drain_guard.py',
            'shadow_lane_elimination_guard.py',
            'operational_entrypoint_dedupe_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-closure-claim-truth-correction-and-semantic-owner-reopen-a922.md':
        return [
            'recovery_execution_guard.py',
            'closure_claim_truth_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-semantic-owner-and-post-owner-reconstruction-reopen-a922.md':
        return [
            'recovery_execution_guard.py',
            'semantic_owner_reopen_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_state_normalization_guard.py',
            'boundary_degrade_guard.py',
            'pack_runtime_separation_guard.py',
            'legacy_mesh_drain_guard.py',
            'operational_entrypoint_dedupe_guard.py',
            'system_reproof_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-governance-closure-a922.md':
        return [
            'recovery_execution_guard.py',
            'authority_freeze_guard.py',
            'legacy_freeze_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'continuity_state_normalization_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'pack_runtime_separation_guard.py',
            'legacy_mesh_drain_guard.py',
            'shadow_lane_elimination_guard.py',
            'operational_entrypoint_dedupe_guard.py',
            'whole_system_governance_closure_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md':
        return ['recovery_execution_guard.py', 'authority_registry_block_guard.py']
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md':
        return ['recovery_execution_guard.py', 'continuity_writer_guard.py']
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md':
        return ['recovery_execution_guard.py', 'continuity_writer_guard.py', 'legacy_mesh_caller_guard.py']
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'semantic_bridge_growth_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-boundary-degrade-constriction-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-plane-materialization-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'fact_plane_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md':
        return [
            'recovery_execution_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'semantic_bridge_growth_guard.py',
            'boundary_degrade_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'legacy_drain_closure_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-g-operational-final-dedupe-a922.md':
        return [
            'recovery_execution_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'legacy_freeze_guard.py',
            'boundary_degrade_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'operational_entrypoint_dedupe_guard.py',
            'proof_path_guard.py',
            'semantic_bridge_growth_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-booking-manage-temporal-clue-grounding-followup-continuity-a922.md':
        return [
            'recovery_execution_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'legacy_freeze_guard.py',
            'boundary_degrade_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'operational_entrypoint_dedupe_guard.py',
            'proof_path_guard.py',
            'semantic_bridge_growth_guard.py',
        ]
    if active_block_tp == 'docs/TASK_PACKAGES/TP-2026-04-01-consultant-core-block-h1b-file-replay-scenario-contract-materialization-a922.md':
        return [
            'recovery_execution_guard.py',
            'fact_plane_guard.py',
            'fact_family_cutover_guard.py',
            'touched_slice_continuity_guard.py',
            'legacy_freeze_guard.py',
            'boundary_degrade_guard.py',
            'continuity_writer_guard.py',
            'legacy_mesh_caller_guard.py',
            'operational_entrypoint_dedupe_guard.py',
            'proof_path_guard.py',
            'semantic_bridge_growth_guard.py',
        ]
    return [
        'recovery_execution_guard.py',
        'fact_plane_guard.py',
        'fact_family_cutover_guard.py',
        'touched_slice_continuity_guard.py',
        'legacy_freeze_guard.py',
        'boundary_degrade_guard.py',
        'continuity_writer_guard.py',
        'legacy_mesh_caller_guard.py',
        'legacy_drain_closure_guard.py',
        'proof_path_guard.py',
        'semantic_bridge_growth_guard.py',
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', default=None)
    parser.add_argument('--base-ref', default=None)
    parser.add_argument('--head-ref', default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    build_agent_packet = load_module('build_agent_packet', root / 'scripts' / 'build_agent_packet.py')
    truth = build_agent_packet.load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    legacy = build_agent_packet.load_yaml(root / 'docs' / 'LEGACY_SUNSET.yaml')
    errors = validate_top_level_consistency(root, truth, legacy)
    if errors:
        for error in errors:
            print(f'arch_guard: FAIL: {error}', file=sys.stderr)
        return 1

    shadow_removal_dependency_truth = root / 'scripts' / 'shadow_removal_dependency_truth.py'
    if shadow_removal_dependency_truth.exists():
        subprocess.run([sys.executable, str(shadow_removal_dependency_truth), '--repo-root', str(root)], cwd=root, check=True)

    tool_inventory_guard = root / 'scripts' / 'tool_inventory_guard.py'
    if tool_inventory_guard.exists():
        subprocess.run([sys.executable, str(tool_inventory_guard), '--repo-root', str(root)], cwd=root, check=True)

    decision_ledger_guard = root / 'scripts' / 'decision_ledger_guard.py'
    if decision_ledger_guard.exists():
        subprocess.run([sys.executable, str(decision_ledger_guard), '--repo-root', str(root)], cwd=root, check=True)

    product_work_map_guard = root / 'scripts' / 'product_work_map_guard.py'
    if product_work_map_guard.exists():
        subprocess.run([sys.executable, str(product_work_map_guard), '--repo-root', str(root)], cwd=root, check=True)

    subprocess.run([sys.executable, str(root / 'scripts' / 'build_agent_packet.py'), '--check'], cwd=root, check=True)

    for script_name in guard_scripts_for_active_block(truth):
        script = root / 'scripts' / script_name
        cmd = [sys.executable, str(script)]
        if args.base_ref:
            cmd.extend(['--base-ref', args.base_ref])
        if args.head_ref:
            cmd.extend(['--head-ref', args.head_ref])
        subprocess.run(cmd, cwd=root, check=True)

    single_owner_guard = root / 'scripts' / 'single_semantic_owner_guard.py'
    if single_owner_guard.exists():
        subprocess.run([sys.executable, str(single_owner_guard)], cwd=root, check=True)

    print('arch_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
