#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_BLOCK_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-fact-contract-schema-a922.md'
ACTIVE_BLOCK = 'Consultant Core Fact Contract Schema'
NEXT_MOVE = 'complete_narrow_fact_family_cutover_for_location_hours_parking_before_continuity_state_normalization_or_replay'
REQUIRED_CHECKS = [
    'python3 scripts/recovery_execution_guard.py',
    'python3 scripts/authority_freeze_guard.py',
    'python3 scripts/fact_contract_schema_guard.py',
    'python3 scripts/fact_plane_guard.py',
    'python3 scripts/arch_guard.py',
    'pytest -q truffles-api/tests/architecture/test_fact_contract_schema_guard.py',
]
REQUIRED_FACT_SCOPE_EVIDENCE = {
    'contracts/runtime/fact_manifest.v1.jsonschema',
    'contracts/runtime/fact_request.v1.jsonschema',
    'contracts/runtime/fact_plan.v1.jsonschema',
    'contracts/runtime/fact_result.v1.jsonschema',
    'contracts/runtime/fact_contract.v1.jsonschema',
    'docs/FACT_CONTRACT_SCHEMA_GUARD.yaml',
    'docs/REPORTS/2026-03-31-consultant-core-fact-contract-schema-a922.md',
    'scripts/fact_contract_schema_guard.py',
    'scripts/fact_plane_guard.py',
    'truffles-api/tests/architecture/test_fact_contract_schema_guard.py',
    'truffles-api/tests/architecture/test_fact_plane_guard.py',
    'truffles-api/tests/test_consultant_core_runtime_contracts.py',
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


def _exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__all__' and isinstance(node.value, (ast.List, ast.Tuple)):
                    values: set[str] = set()
                    for item in node.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            values.add(item.value)
                    return values
    return set()


def collect_errors(root: Path = ROOT) -> list[str]:
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    if truth.get('active_block_tp') != ACTIVE_BLOCK_TP:
        return []

    errors: list[str] = []
    config = _load_yaml(root / 'docs' / 'FACT_CONTRACT_SCHEMA_GUARD.yaml')
    program = truth.get('program') or {}
    authority = _load_json(root / truth['authority_registry'])
    compatibility = _load_json(root / truth['compatibility_carrier_inventory'])
    surfaces = _load_json(root / truth['dead_surface_registry'])
    caller_surface = _load_json(root / truth['legacy_caller_surface'])
    delta = _load_json(root / truth['governance_delta'])

    if program.get('current_block') != ACTIVE_BLOCK:
        errors.append('program.current_block must point to Consultant Core Fact Contract Schema')
    if truth.get('current_non_negotiable_next_move') != NEXT_MOVE:
        errors.append('current_non_negotiable_next_move must advance to Narrow Fact-Family Cutover after Fact Contract Schema closes')

    required_checks = set(program.get('required_checks') or [])
    for check in REQUIRED_CHECKS:
        if check not in required_checks:
            errors.append(f'program.required_checks missing fact-contract-schema check: {check}')

    if authority.get('status') != 'machine_readable_fact_contract_schema_base':
        errors.append('authority_registry must expose machine_readable_fact_contract_schema_base during Fact Contract Schema')
    if authority.get('active_block') != ACTIVE_BLOCK:
        errors.append('authority_registry active_block drifted from Consultant Core Fact Contract Schema')
    entries = {item.get('mechanism_id'): item for item in authority.get('entries', []) if isinstance(item, dict)}
    fact_scope = entries.get('fact_scope') or {}
    if fact_scope.get('target_contract') != config.get('required_target_contract'):
        errors.append('authority_registry fact_scope.target_contract must match FACT_CONTRACT_SCHEMA_GUARD target contract')
    if fact_scope.get('next_phase_required') != config.get('required_next_phase'):
        errors.append('authority_registry fact_scope.next_phase_required must match FACT_CONTRACT_SCHEMA_GUARD next phase')
    if not REQUIRED_FACT_SCOPE_EVIDENCE.issubset(set(fact_scope.get('evidence') or [])):
        errors.append('authority_registry fact_scope evidence must contain the fact-contract schema evidence set')

    if compatibility.get('status') != 'machine_readable_compatibility_carrier_freeze_base':
        errors.append('compatibility_carrier_inventory must preserve machine_readable_compatibility_carrier_freeze_base during Fact Contract Schema')
    if compatibility.get('active_block') != ACTIVE_BLOCK:
        errors.append('compatibility_carrier_inventory active_block drifted from Consultant Core Fact Contract Schema')
    if surfaces.get('status') != 'machine_readable_surface_authority_freeze_base':
        errors.append('dead_surface_registry must preserve machine_readable_surface_authority_freeze_base during Fact Contract Schema')
    if surfaces.get('active_block') != ACTIVE_BLOCK:
        errors.append('dead_surface_registry active_block drifted from Consultant Core Fact Contract Schema')
    if caller_surface.get('status') != 'machine_readable_legacy_caller_freeze_base':
        errors.append('legacy_caller_surface must preserve machine_readable_legacy_caller_freeze_base during Fact Contract Schema')
    if caller_surface.get('active_block') != ACTIVE_BLOCK:
        errors.append('legacy_caller_surface active_block drifted from Consultant Core Fact Contract Schema')

    if delta.get('active_block') != ACTIVE_BLOCK:
        errors.append('governance_delta active_block drifted from Consultant Core Fact Contract Schema')
    if 'narrow_fact_family_cutover' not in (delta.get('deferred_next_blocks') or []):
        errors.append('governance_delta.deferred_next_blocks must contain narrow_fact_family_cutover')

    for rel in config.get('required_schema_files') or []:
        if not (root / rel).exists():
            errors.append(f'missing fact schema file: {rel}')

    exports = _exports(root / 'truffles-api/app/core/__init__.py')
    for name in config.get('required_fact_models') or []:
        if name not in exports:
            errors.append(f'truffles-api/app/core/__init__.py missing export: {name}')

    fact_plane_text = (root / 'truffles-api/app/core/fact_plane.py').read_text(encoding='utf-8')
    for key in config.get('required_meta_keys') or []:
        if f'"{key}"' not in fact_plane_text:
            errors.append(f'truffles-api/app/core/fact_plane.py missing required fact meta key literal: {key}')

    return errors


if __name__ == '__main__':
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'fact_contract_schema_guard: FAIL: {error}', file=sys.stderr)
        raise SystemExit(1)
    print('fact_contract_schema_guard: OK')
