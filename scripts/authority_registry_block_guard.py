#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BLOCK2_TP = 'docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md'
BLOCK2_REQUIRED_ALLOWED_TOUCH = {
    'scripts/authority_registry_block_guard.py',
    'truffles-api/tests/architecture/test_authority_registry_block_guard.py',
}
BLOCK2_REQUIRED_CHECKS = {
    'python3 scripts/authority_registry_block_guard.py',
    'pytest -q truffles-api/tests/architecture/test_authority_registry_block_guard.py',
}
BLOCK2_REQUIRED_OPEN_BLOCKERS = {
    'owner_status_fields_and_registry_phase_credit_must_remain_block2_honest',
}
BLOCK2_REQUIRED_HISTORICAL_RULE = (
    'later_r36_star_replay_rca_and_runtime_materials_remain_non_governing_history_while_block_2_lock_is_active'
)
BLOCK2_OWNER_STATUS_EXPECTATIONS = {
    'semantic_owner.cutover_status': 'viable_owner_path_exists_but_post_owner_semantic_reconstruction_and_compatibility_pressure_remain_live',
    'continuity_owner.cutover_status': 'canonical_dialog_state_candidate_exists_but_competing_continuity_carriers_and_compatibility_writers_remain_live',
    'boundary_owner.cutover_status': 'typed_boundary_seams_exist_but_deterministic_boundary_overreach_and_legacy_boundary_helpers_remain_live',
}
FORBIDDEN_LATER_PHASE_EVIDENCE = {
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
REQUIRED_NEXT_PHASES = {
    'semantic_turn_meaning': 'post_owner_reconstruction_constriction',
    'post_owner_semantic_reconstruction': 'post_owner_reconstruction_constriction',
    'continuity_state': 'truth_carrier_inventory_and_freeze',
    'boundary_and_degrade': 'boundary_degrade_constriction',
    'fact_scope': 'fact_plane_materialization',
    'legacy_behavior_authority': 'adapter_only_legacy_mesh_and_caller_proof',
}


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


def collect_errors(root: Path = ROOT) -> list[str]:
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    if truth.get('active_block_tp') != BLOCK2_TP:
        return []

    errors: list[str] = []
    program = truth.get('program', {})
    allowed_touch = set(program.get('allowed_touch', [])) if isinstance(program, dict) else set()
    required_checks = set(program.get('required_checks', [])) if isinstance(program, dict) else set()
    open_blockers = set(program.get('open_blockers', [])) if isinstance(program, dict) else set()
    authority = _load_json(root / 'docs' / 'system_forensics' / 'authority_registry.json')
    carriers = _load_json(root / 'docs' / 'system_forensics' / 'compatibility_carrier_inventory.json')
    surfaces = _load_json(root / 'docs' / 'system_forensics' / 'dead_surface_registry.json')

    missing_allowed_touch = sorted(BLOCK2_REQUIRED_ALLOWED_TOUCH.difference(allowed_touch))
    if missing_allowed_touch:
        errors.append(
            'program.allowed_touch is missing block-2 guard artifacts: ' + ', '.join(missing_allowed_touch)
        )
    missing_required_checks = sorted(BLOCK2_REQUIRED_CHECKS.difference(required_checks))
    if missing_required_checks:
        errors.append(
            'program.required_checks is missing block-2 guard checks: ' + ', '.join(missing_required_checks)
        )
    missing_open_blockers = sorted(BLOCK2_REQUIRED_OPEN_BLOCKERS.difference(open_blockers))
    if missing_open_blockers:
        errors.append(
            'program.open_blockers is missing block-2 honesty blockers: ' + ', '.join(missing_open_blockers)
        )
    if program.get('historical_residue_rule') != BLOCK2_REQUIRED_HISTORICAL_RULE:
        errors.append('program.historical_residue_rule drifted away from the block-2 historical residue rule')

    for dotted_key, expected_value in BLOCK2_OWNER_STATUS_EXPECTATIONS.items():
        section_name, key = dotted_key.split('.', 1)
        section = truth.get(section_name, {})
        actual_value = section.get(key) if isinstance(section, dict) else None
        if actual_value != expected_value:
            errors.append(
                f'{dotted_key} drift -> expected {expected_value}, got {actual_value}'
            )

    if authority.get('status') != 'machine_readable_governance_base':
        errors.append('authority_registry status must remain machine_readable_governance_base in block 2')
    if carriers.get('status') != 'machine_readable_compatibility_carrier_inventory_base':
        errors.append('compatibility_carrier_inventory status must remain machine_readable_compatibility_carrier_inventory_base in block 2')
    if surfaces.get('status') != 'machine_readable_dead_surface_registry_base':
        errors.append('dead_surface_registry status must remain machine_readable_dead_surface_registry_base in block 2')

    mechanisms = {entry['mechanism_id']: entry for entry in authority.get('entries', [])}
    if set(mechanisms) != set(REQUIRED_NEXT_PHASES):
        errors.append('authority_registry mechanism set drifted from the active block-2 mechanism envelope')
    for mechanism_id, expected_phase in REQUIRED_NEXT_PHASES.items():
        entry = mechanisms.get(mechanism_id)
        if not entry:
            continue
        if entry.get('next_phase_required') != expected_phase:
            errors.append(
                f'authority_registry {mechanism_id} next_phase_required drift -> expected {expected_phase}, got {entry.get("next_phase_required")}'
            )
        bad = sorted(FORBIDDEN_LATER_PHASE_EVIDENCE.intersection(entry.get('evidence', [])))
        if bad:
            errors.append(f'authority_registry {mechanism_id} cites later-phase evidence: {", ".join(bad)}')

    for section_name in ['freeze_guard', 'reader_precedence_law']:
        section = carriers.get(section_name, {})
        bad = sorted(FORBIDDEN_LATER_PHASE_EVIDENCE.intersection(section.get('evidence', [])))
        if bad:
            errors.append(f'compatibility_carrier_inventory {section_name} cites later-phase evidence: {", ".join(bad)}')
    for carrier in carriers.get('carriers', []):
        if carrier.get('confidence') != 'high':
            errors.append(f'compatibility_carrier_inventory {carrier.get("carrier_id")} must not remain low-confidence in active block 2')
        bad = sorted(FORBIDDEN_LATER_PHASE_EVIDENCE.intersection(carrier.get('evidence', [])))
        if bad:
            errors.append(f'compatibility_carrier_inventory {carrier.get("carrier_id")} cites later-phase evidence: {", ".join(bad)}')

    caller_proof = surfaces.get('caller_proof_law', {})
    bad = sorted(FORBIDDEN_LATER_PHASE_EVIDENCE.intersection(caller_proof.get('evidence', [])))
    if bad:
        errors.append(f'dead_surface_registry caller_proof_law cites later-phase evidence: {", ".join(bad)}')
    for forbidden_key in ['adapter_only_for_touched_envelope', 'startup_load_drained_from_package_root', 'unreachable_for_touched_envelope']:
        if forbidden_key in caller_proof:
            errors.append(f'dead_surface_registry caller_proof_law must not expose later-phase proof key during block 2: {forbidden_key}')

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'authority_registry_block_guard: FAIL: {error}', file=sys.stderr)
        return 1
    print('authority_registry_block_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
