#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_BLOCK_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-authority-freeze-a922.md'
ACTIVE_BLOCK = 'Consultant Core Authority Freeze'
NEXT_MOVE = 'complete_fact_contract_schema_for_whole_system_architecture_closure_before_any_narrow_family_cutover_or_replay'
FROZEN_ADAPTER_ONLY_MODULES = [
    'truffles-api/app/routers/webhook/info.py',
    'truffles-api/app/routers/webhook/decision.py',
    'truffles-api/app/routers/webhook/response.py',
    'truffles-api/app/routers/webhook/context_manager.py',
    'truffles-api/app/services/reasoning_core.py',
]
REQUIRED_CALLER_SURFACE_MODULES = FROZEN_ADAPTER_ONLY_MODULES + ['truffles-api/app/webhook.py']
REQUIRED_MECHANISMS = [
    'semantic_turn_meaning',
    'post_owner_semantic_reconstruction',
    'continuity_state',
    'boundary_and_degrade',
    'fact_scope',
    'legacy_behavior_authority',
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



def collect_errors(root: Path = ROOT) -> list[str]:
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    if truth.get('active_block_tp') != ACTIVE_BLOCK_TP:
        return []

    errors: list[str] = []
    program = truth.get('program') or {}
    governance = truth.get('governance_registries') or {}
    authority = _load_json(root / truth['authority_registry'])
    compatibility = _load_json(root / truth['compatibility_carrier_inventory'])
    surfaces = _load_json(root / truth['dead_surface_registry'])
    caller_surface = _load_json(root / truth['legacy_caller_surface'])
    governance_delta = _load_json(root / truth['governance_delta'])

    if program.get('current_block') != ACTIVE_BLOCK:
        errors.append('program.current_block must point to Consultant Core Authority Freeze')
    if truth.get('current_non_negotiable_next_move') != NEXT_MOVE:
        errors.append('current_non_negotiable_next_move must advance to Fact Contract Schema after Authority Freeze closes')

    required_checks = set(program.get('required_checks') or [])
    for check in [
        'python3 scripts/recovery_execution_guard.py',
        'python3 scripts/authority_freeze_guard.py',
        'python3 scripts/arch_guard.py',
        'pytest -q truffles-api/tests/architecture/test_authority_freeze_guard.py',
    ]:
        if check not in required_checks:
            errors.append(f'program.required_checks missing authority-freeze check: {check}')
    if not set(FROZEN_ADAPTER_ONLY_MODULES).issubset(set(program.get('forbidden_touch') or [])):
        errors.append('program.forbidden_touch must include the frozen adapter-only legacy modules')

    authority_section = governance.get('authority') or {}
    if authority_section.get('required_status') != 'machine_readable_authority_freeze_base':
        errors.append('governance_registries.authority.required_status must be machine_readable_authority_freeze_base')
    caller_section = governance.get('legacy_caller_surface') or {}
    if caller_section.get('required_status') != 'machine_readable_legacy_caller_freeze_base':
        errors.append('governance_registries.legacy_caller_surface.required_status must be machine_readable_legacy_caller_freeze_base')
    delta_section = governance.get('governance_delta') or {}
    if delta_section.get('required_status') != 'machine_readable_governance_delta_base':
        errors.append('governance_registries.governance_delta.required_status must be machine_readable_governance_delta_base')

    if authority.get('status') != 'machine_readable_authority_freeze_base':
        errors.append('authority_registry must expose machine_readable_authority_freeze_base during Authority Freeze')
    if authority.get('active_block') != ACTIVE_BLOCK:
        errors.append('authority_registry active_block drifted from Consultant Core Authority Freeze')
    freeze_scope = authority.get('freeze_scope') or {}
    if freeze_scope.get('frozen_legacy_modules') != FROZEN_ADAPTER_ONLY_MODULES:
        errors.append('authority_registry.freeze_scope.frozen_legacy_modules must match the frozen adapter-only set')

    if compatibility.get('status') != 'machine_readable_compatibility_carrier_freeze_base':
        errors.append('compatibility_carrier_inventory must expose machine_readable_compatibility_carrier_freeze_base during Authority Freeze')
    if compatibility.get('active_block') != ACTIVE_BLOCK:
        errors.append('compatibility_carrier_inventory active_block drifted from Consultant Core Authority Freeze')
    if not isinstance(compatibility.get('authority_freeze_scope'), dict):
        errors.append('compatibility_carrier_inventory must expose authority_freeze_scope during Authority Freeze')

    if surfaces.get('status') != 'machine_readable_surface_authority_freeze_base':
        errors.append('dead_surface_registry must expose machine_readable_surface_authority_freeze_base during Authority Freeze')
    if surfaces.get('active_block') != ACTIVE_BLOCK:
        errors.append('dead_surface_registry active_block drifted from Consultant Core Authority Freeze')
    surface_freeze_scope = surfaces.get('authority_freeze_scope') or {}
    if surface_freeze_scope.get('frozen_adapter_only_modules') != FROZEN_ADAPTER_ONLY_MODULES:
        errors.append('dead_surface_registry.authority_freeze_scope.frozen_adapter_only_modules must match the frozen adapter-only set')

    if caller_surface.get('status') != 'machine_readable_legacy_caller_freeze_base':
        errors.append('legacy_caller_surface must expose machine_readable_legacy_caller_freeze_base')
    if caller_surface.get('active_block') != ACTIVE_BLOCK:
        errors.append('legacy_caller_surface active_block drifted from Consultant Core Authority Freeze')
    freeze_policy = caller_surface.get('freeze_policy') or {}
    if freeze_policy.get('frozen_adapter_only_modules') != FROZEN_ADAPTER_ONLY_MODULES:
        errors.append('legacy_caller_surface.freeze_policy.frozen_adapter_only_modules must match the frozen adapter-only set')
    entry_paths = {entry.get('module_path') for entry in caller_surface.get('entries', []) if isinstance(entry, dict)}
    if entry_paths != set(REQUIRED_CALLER_SURFACE_MODULES):
        errors.append('legacy_caller_surface entry module set must match the required authority-freeze caller-surface set')

    if governance_delta.get('status') != 'machine_readable_governance_delta_base':
        errors.append('governance_delta must expose machine_readable_governance_delta_base')
    if governance_delta.get('active_block') != ACTIVE_BLOCK:
        errors.append('governance_delta active_block drifted from Consultant Core Authority Freeze')
    if governance_delta.get('locked_mechanisms') != REQUIRED_MECHANISMS:
        errors.append('governance_delta.locked_mechanisms must match the authority mechanism set')
    if set(governance_delta.get('new_machine_readable_artifacts') or []) != {
        'docs/system_forensics/legacy_caller_surface.json',
        'docs/system_forensics/governance_delta.json',
    }:
        errors.append('governance_delta.new_machine_readable_artifacts must declare the authority-freeze artifacts exactly')

    return errors



def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'authority_freeze_guard: FAIL: {error}', file=sys.stderr)
        return 1
    print('authority_freeze_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
