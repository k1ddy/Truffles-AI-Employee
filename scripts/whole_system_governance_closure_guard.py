#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: invalid YAML mapping: {path}')
    return data


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: invalid JSON object: {path}')
    return data


def collect_errors(root: Path = ROOT) -> list[str]:
    config = _load_yaml(root / 'docs' / 'WHOLE_SYSTEM_GOVERNANCE_CLOSURE_GUARD.yaml')
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    if truth.get('active_block_tp') != config['active_block_tp']:
        return []

    errors: list[str] = []
    authority = _load_json(root / 'docs' / 'system_forensics' / 'authority_registry.json')
    carriers = _load_json(root / 'docs' / 'system_forensics' / 'compatibility_carrier_inventory.json')
    surfaces = _load_json(root / 'docs' / 'system_forensics' / 'dead_surface_registry.json')
    caller_surface = _load_json(root / 'docs' / 'system_forensics' / 'legacy_caller_surface.json')
    delta = _load_json(root / 'docs' / 'system_forensics' / 'governance_delta.json')

    if truth.get('current_non_negotiable_next_move') != config['next_move']:
        errors.append('current_non_negotiable_next_move must point to replay + full human semantic audit only')
    if truth.get('program', {}).get('current_block') != config['active_block']:
        errors.append('program.current_block must match whole-system governance closure')

    registry_map = {
        'authority_registry': authority,
        'compatibility_carrier_inventory': carriers,
        'dead_surface_registry': surfaces,
        'legacy_caller_surface': caller_surface,
        'governance_delta': delta,
    }
    for key, expected_status in (config.get('required_registry_statuses') or {}).items():
        actual = registry_map[key].get('status')
        if actual != expected_status:
            errors.append(f'{key}.status must be {expected_status}, got {actual}')
        active_block = registry_map[key].get('active_block')
        if active_block and active_block != config['active_block']:
            errors.append(f'{key}.active_block must match whole-system governance closure')

    expected_phase = config['required_authority_next_phase']
    for entry in authority.get('entries', []):
        mechanism_id = entry.get('mechanism_id')
        if entry.get('next_phase_required') != expected_phase:
            errors.append(f'authority_registry entry {mechanism_id} must point to {expected_phase}')

    open_blockers = set(truth.get('program', {}).get('open_blockers', []) or [])
    for blocker in config.get('required_program_open_blockers') or []:
        if blocker not in open_blockers:
            errors.append(f'program.open_blockers missing final acceptance blocker: {blocker}')

    expected_deferred = config.get('required_deferred_next_blocks') or []
    if delta.get('deferred_next_blocks') != expected_deferred:
        errors.append('governance_delta.deferred_next_blocks must contain only replay_and_human_audit_acceptance')

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'whole_system_governance_closure_guard: FAIL: {error}', file=sys.stderr)
        return 1
    print('whole_system_governance_closure_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
