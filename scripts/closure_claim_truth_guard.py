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
    config = _load_yaml(root / 'docs' / 'CLOSURE_CLAIM_TRUTH_GUARD.yaml')
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    if truth.get('active_block_tp') != config['active_block_tp']:
        return []

    errors: list[str] = []
    authority = _load_json(root / 'docs' / 'system_forensics' / 'authority_registry.json')
    carriers = _load_json(root / 'docs' / 'system_forensics' / 'compatibility_carrier_inventory.json')
    surfaces = _load_json(root / 'docs' / 'system_forensics' / 'dead_surface_registry.json')
    callers = _load_json(root / 'docs' / 'system_forensics' / 'legacy_caller_surface.json')
    delta = _load_json(root / 'docs' / 'system_forensics' / 'governance_delta.json')

    if truth.get('current_non_negotiable_next_move') != config['next_move']:
        errors.append('current_non_negotiable_next_move must point to semantic-owner reopen, not replay')
    if truth.get('program', {}).get('current_block') != config['active_block']:
        errors.append('program.current_block must match closure-claim truth-correction block')

    registry_map = {
        'authority_registry': authority,
        'compatibility_carrier_inventory': carriers,
        'dead_surface_registry': surfaces,
        'legacy_caller_surface': callers,
        'governance_delta': delta,
    }
    for key, expected_status in (config.get('required_registry_statuses') or {}).items():
        actual = registry_map[key].get('status')
        if actual != expected_status:
            errors.append(f'{key}.status must be {expected_status}, got {actual}')
        active_block = registry_map[key].get('active_block')
        if active_block and active_block != config['active_block']:
            errors.append(f'{key}.active_block must match truth-correction block')

    entries = {entry.get('mechanism_id'): entry for entry in authority.get('entries', [])}
    semantic_entry = entries.get('semantic_turn_meaning') or {}
    post_owner_entry = entries.get('post_owner_semantic_reconstruction') or {}

    if semantic_entry.get('next_phase_required') != config['required_authority_next_phase']:
        errors.append('semantic_turn_meaning must point next to semantic_owner_and_post_owner_reconstruction_reopen')
    if post_owner_entry.get('next_phase_required') != config['required_authority_next_phase']:
        errors.append('post_owner_semantic_reconstruction must point next to semantic_owner_and_post_owner_reconstruction_reopen')

    semantic_competing = set(semantic_entry.get('current_competing_writer_paths') or [])
    for path in config.get('required_semantic_competing_writer_paths') or []:
        if path not in semantic_competing:
            errors.append(f'semantic_turn_meaning.current_competing_writer_paths missing {path}')

    post_owner_live = set(post_owner_entry.get('current_live_caller_paths') or [])
    for path in config.get('required_post_owner_live_paths') or []:
        if path not in post_owner_live:
            errors.append(f'post_owner_semantic_reconstruction.current_live_caller_paths missing {path}')

    canon_text = (root / 'docs' / 'ACTIVE_CANON.md').read_text(encoding='utf-8')
    program_text = (root / 'docs' / 'ACTIVE_PROGRAM.md').read_text(encoding='utf-8')
    for phrase in config.get('forbidden_canon_phrases') or []:
        if phrase in canon_text:
            errors.append(f'ACTIVE_CANON.md still contains forbidden closure phrase: {phrase}')
        if phrase in program_text:
            errors.append(f'ACTIVE_PROGRAM.md still contains forbidden closure phrase: {phrase}')

    open_blockers = set(truth.get('program', {}).get('open_blockers', []) or [])
    for blocker in config.get('required_program_open_blockers') or []:
        if blocker not in open_blockers:
            errors.append(f'program.open_blockers missing truth-correction blocker: {blocker}')

    for marker in config.get('required_code_markers') or []:
        marker_path = root / marker['path']
        text = marker_path.read_text(encoding='utf-8')
        if marker['pattern'] not in text:
            errors.append(f'live-code marker missing: {marker["path"]} -> {marker["pattern"]}')

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'closure_claim_truth_guard: FAIL: {error}', file=sys.stderr)
        return 1
    print('closure_claim_truth_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
