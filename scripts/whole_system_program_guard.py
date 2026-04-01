#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_BLOCK_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md'
ACTIVE_MASTER_TP = 'docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md'
ACTIVE_DEC = 'docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md'
NEXT_MOVE = 'complete_authority_freeze_and_fact_contract_schema_for_whole_system_architecture_closure_before_any_replay_or_behavioral_acceptance'


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: YAML document must be a mapping: {path}')
    return data


def collect_errors(root: Path = ROOT) -> list[str]:
    truth = _load_yaml(root / 'docs' / 'SOURCE_OF_TRUTH.yaml')
    if truth.get('active_block_tp') != ACTIVE_BLOCK_TP:
        return []

    errors: list[str] = []
    canon = (root / 'docs' / 'ACTIVE_CANON.md').read_text(encoding='utf-8')
    program = (root / 'docs' / 'ACTIVE_PROGRAM.md').read_text(encoding='utf-8')
    master_tp = (root / ACTIVE_MASTER_TP).read_text(encoding='utf-8')
    block_tp = (root / ACTIVE_BLOCK_TP).read_text(encoding='utf-8')

    if truth.get('active_dec') != ACTIVE_DEC:
        errors.append('active_dec must point to the whole-system closure governing decision')
    if truth.get('active_master_tp') != ACTIVE_MASTER_TP:
        errors.append('active_master_tp must point to the whole-system closure master TP')
    if truth.get('current_non_negotiable_next_move') != NEXT_MOVE:
        errors.append('current_non_negotiable_next_move must point to Authority Freeze + Fact Contract Schema, not replay')
    if truth.get('execution_strategy', {}).get('block_closeout_rule') != (
        'state_canon_packet_and_report_sync_only_after_full_block_completion_never_after_micro_actions'
    ):
        errors.append('execution_strategy.block_closeout_rule must freeze block-level sync discipline')

    required_program_snippets = [
        'Authority Freeze',
        'Fact Contract Schema',
        'Narrow Fact-Family Cutover',
        'Continuity / State Normalization',
        'Post-Owner Semantic Constriction',
        'Boundary Constriction',
        'Pack / Runtime Separation Completion',
        'Legacy Mesh Drain',
        'Operational Entrypoint Dedupe',
        'Replay + Full Human Semantic Audit',
        'no canon/state/report updates after micro-fixes inside an unfinished block',
    ]
    for snippet in required_program_snippets:
        if snippet not in program:
            errors.append(f'ACTIVE_PROGRAM missing whole-system program snippet: {snippet}')

    required_canon_snippets = [
        'Single Semantic Owner + Strict Binding Boundary + Canonical Continuity State + First-Class Fact Plane + Adapter-only Legacy Mesh',
        'Current practical truth: `r35f`',
        'complete `Authority Freeze` and `Fact Contract Schema` for whole-system closure before any replay or behavioral acceptance',
        'Do not update `STATE.md`, `docs/ACTIVE_*`, packet, or reports after micro-fixes inside an unfinished block.',
    ]
    for snippet in required_canon_snippets:
        if snippet not in canon:
            errors.append(f'ACTIVE_CANON missing whole-system closure snippet: {snippet}')

    required_master_snippets = [
        'Wave 0. Program Reset And Freeze',
        'Wave 1. Foundation Freeze',
        'Lane A. Fact Plane',
        'Lane B. Continuity Collapse',
        'Lane C. Semantic Owner Constriction',
        'Lane D. Legacy Mesh Drain',
        'Do not relabel canary closure as whole-system closure.',
    ]
    for snippet in required_master_snippets:
        if snippet not in master_tp:
            errors.append(f'master TP missing execution-plan snippet: {snippet}')

    required_block_snippets = [
        'No runtime behavior changes.',
        'No replay or human audit.',
        'No micro-fix-based `STATE.md` or canon updates before a full block completes.',
        'block-closeout reporting discipline',
    ]
    for snippet in required_block_snippets:
        if snippet not in block_tp:
            errors.append(f'active reset TP missing discipline snippet: {snippet}')

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f'whole_system_program_guard: FAIL: {error}', file=sys.stderr)
        return 1
    print('whole_system_program_guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
