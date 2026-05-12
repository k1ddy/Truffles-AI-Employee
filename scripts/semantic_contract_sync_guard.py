#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROMPT_PATH = Path("prompts/llm_policy_core.md")
COMPACT_PROMPT_PATH = Path("prompts/llm_policy_core_compact.md")
PROMPT_SERVICE_PATH = Path("truffles-api/app/services/policy_prompt_snapshot_service.py")
VOCAB_SERVICE_PATH = Path("truffles-api/app/services/policy_vocabulary_snapshot_service.py")
MARKER = "{{GENERATED_MIXED_FIRST_TURN_FACT_CONTRACT_BLOCK}}"

SEMANTIC_FIELD_TO_CATEGORY = {
    "intent": "intents",
    "action": "actions",
    "expected_reply_type": "expected_reply_types",
    "next_question": "next_questions",
    "open_questions": "next_questions",
    "subject_kind": "subject_kinds",
    "capability": "capabilities",
    "resolution_mode": "resolution_modes",
    "pending_question_act": "pending_question_acts",
    "pending_question_target": "pending_question_targets",
    "active_question_relation": "active_question_relations",
}

REQUIRED_SOURCE_SNIPPETS = {
    PROMPT_SERVICE_PATH: (
        "prompt_text = _inject_policy_core_generated_contract_blocks(prompt_text, compact=False)",
        "prompt_text = _inject_policy_core_generated_contract_blocks(prompt_text, compact=True)",
        MARKER,
    ),
    VOCAB_SERVICE_PATH: (
        "_validate_generated_contract_vocabulary_sync(snapshot)",
        "policy_core_generated_contract_semantic_tokens()",
    ),
}


def _load_text(root: Path, relative_path: Path) -> str:
    path = root / relative_path
    if not path.exists():
        raise SystemExit(f"semantic_contract_sync_guard: FAIL: missing required file {relative_path}")
    return path.read_text(encoding="utf-8")


def _import_contract_modules(root: Path):
    app_root = root / "truffles-api"
    if not app_root.exists():
        raise SystemExit("semantic_contract_sync_guard: FAIL: missing truffles-api root")
    sys.path.insert(0, str(app_root))
    try:
        from app.services.policy_prompt_snapshot_service import (  # type: ignore
            _POLICY_CORE_COMPACT_PROMPT_PATH,
            _POLICY_CORE_PROMPT_PATH,
            _POLICY_CORE_GENERATED_CONTRACT_BLOCK_MARKER,
            PolicyCoreGeneratedValueRefV1,
            iter_policy_core_generated_contract_blocks,
            load_policy_core_compact_prompt_snapshot,
            load_policy_core_prompt_snapshot,
            policy_core_generated_contract_semantic_tokens,
        )
        from app.services.policy_vocabulary_snapshot_service import (  # type: ignore
            build_policy_core_vocabulary_snapshot,
        )
    finally:
        sys.path.pop(0)
    return {
        "PROMPT_PATH": _POLICY_CORE_PROMPT_PATH,
        "COMPACT_PROMPT_PATH": _POLICY_CORE_COMPACT_PROMPT_PATH,
        "MARKER": _POLICY_CORE_GENERATED_CONTRACT_BLOCK_MARKER,
        "ValueRef": PolicyCoreGeneratedValueRefV1,
        "iter_blocks": iter_policy_core_generated_contract_blocks,
        "load_full": load_policy_core_prompt_snapshot,
        "load_compact": load_policy_core_compact_prompt_snapshot,
        "semantic_tokens": policy_core_generated_contract_semantic_tokens,
        "build_vocab": build_policy_core_vocabulary_snapshot,
    }


def _iter_static_semantic_literals(template_value: Any, *, field_name: str) -> list[str]:
    if template_value is None:
        return []
    if isinstance(template_value, str):
        stripped = template_value.strip()
        return [stripped] if stripped else []
    if isinstance(template_value, (list, tuple)):
        values: list[str] = []
        for item in template_value:
            values.extend(_iter_static_semantic_literals(item, field_name=field_name))
        return values
    if isinstance(template_value, dict):
        values: list[str] = []
        for key, value in template_value.items():
            nested_field = key if key in SEMANTIC_FIELD_TO_CATEGORY else field_name
            values.extend(_iter_static_semantic_literals(value, field_name=nested_field))
        return values
    return []


def _collect_boundary_template_literals(blocks: tuple[Any, ...], value_ref_type: type[Any]) -> dict[str, set[str]]:
    observed: dict[str, set[str]] = defaultdict(set)
    for block in blocks:
        for template in getattr(block, "boundary_payload_templates", ()):
            payload = getattr(template, "payload", None)
            if not isinstance(payload, dict):
                continue
            for field_name, category in SEMANTIC_FIELD_TO_CATEGORY.items():
                value = payload.get(field_name)
                if isinstance(value, value_ref_type):
                    continue
                for literal in _iter_static_semantic_literals(value, field_name=field_name):
                    observed[category].add(literal)
    return observed


def evaluate(root: Path) -> list[str]:
    violations: list[str] = []

    for relative_path, snippets in REQUIRED_SOURCE_SNIPPETS.items():
        text = _load_text(root, relative_path)
        for snippet in snippets:
            if snippet not in text:
                violations.append(
                    f"{relative_path} missing required semantic-contract sync snippet {snippet!r}"
                )

    prompt_source = _load_text(root, PROMPT_PATH)
    marker_count = prompt_source.count(MARKER)
    if marker_count != 1:
        violations.append(
            f"{PROMPT_PATH} must contain generated contract marker exactly once; observed {marker_count}"
        )

    modules = _import_contract_modules(root)
    blocks = tuple(modules["iter_blocks"]())
    if not blocks:
        violations.append("generated contract block registry is empty")
        return violations

    marker = modules["MARKER"]
    if marker != MARKER:
        violations.append("generated contract marker constant drifted from prompt marker")

    block_ids = [block.block_id for block in blocks]
    duplicate_block_ids = sorted(block_id for block_id, count in Counter(block_ids).items() if count > 1)
    if duplicate_block_ids:
        violations.append(f"generated contract block ids must be unique -> {duplicate_block_ids}")

    full_prompt_snapshot = modules["load_full"]()
    compact_prompt_snapshot = modules["load_compact"]()
    full_prompt = full_prompt_snapshot.prompt_text
    compact_prompt = compact_prompt_snapshot.prompt_text
    if marker in full_prompt:
        violations.append("full prompt snapshot still contains generated contract marker")
    if marker in compact_prompt:
        violations.append("compact prompt snapshot still contains generated contract marker")

    for block in blocks:
        full_count = full_prompt.count(block.full_prompt_text)
        compact_count = compact_prompt.count(block.compact_prompt_text)
        if full_count != 1:
            violations.append(
                f"full prompt must contain generated block {block.block_id} exactly once; observed {full_count}"
            )
        if compact_count != 1:
            violations.append(
                f"compact prompt must contain generated block {block.block_id} exactly once; observed {compact_count}"
            )
        if prompt_source.count(block.full_prompt_text):
            violations.append(
                f"{PROMPT_PATH} must not inline rendered full block {block.block_id}; keep marker-based single source"
            )

    full_loader_source = inspect.getsource(modules["load_full"])
    if "_inject_policy_core_generated_contract_blocks(prompt_text, compact=False)" not in full_loader_source:
        violations.append("full prompt loader no longer routes through generated contract injector")
    compact_loader_source = inspect.getsource(modules["load_compact"])
    if "_inject_policy_core_generated_contract_blocks(prompt_text, compact=True)" not in compact_loader_source:
        violations.append("compact prompt loader no longer routes through generated contract injector")
    vocab_builder_source = inspect.getsource(modules["build_vocab"])
    if "_validate_generated_contract_vocabulary_sync(snapshot)" not in vocab_builder_source:
        violations.append("vocabulary builder no longer calls generated contract vocabulary sync")

    snapshot = modules["build_vocab"]()
    declared_tokens = modules["semantic_tokens"]()
    allowlists = {
        "intents": set(snapshot.intents),
        "actions": set(snapshot.actions),
        "expected_reply_types": set(snapshot.expected_reply_types),
        "next_questions": set(snapshot.next_questions),
        "subject_kinds": set(snapshot.subject_kinds),
        "capabilities": set(snapshot.capabilities),
        "temporal_scopes": set(snapshot.temporal_scopes),
        "resolution_modes": set(snapshot.resolution_modes),
        "pending_question_acts": set(snapshot.pending_question_acts),
        "pending_question_targets": set(snapshot.pending_question_targets),
        "active_question_relations": set(snapshot.active_question_relations),
    }
    for category, values in declared_tokens.items():
        missing = sorted(value for value in values if value not in allowlists.get(category, set()))
        if missing:
            violations.append(f"declared generated semantic tokens missing from vocabulary {category}: {missing}")

    boundary_literals = _collect_boundary_template_literals(blocks, modules["ValueRef"])
    for category, values in boundary_literals.items():
        declared = set(declared_tokens.get(category, frozenset()))
        missing = sorted(value for value in values if value not in declared)
        if missing:
            violations.append(
                f"boundary payload literals missing from generated semantic token coverage {category}: {missing}"
            )

    compact_prompt_path = Path(modules["COMPACT_PROMPT_PATH"])
    if compact_prompt_path.exists():
        compact_source = compact_prompt_path.read_text(encoding="utf-8")
        compact_marker_count = compact_source.count(marker)
        if compact_marker_count != 1:
            violations.append(
                f"{compact_prompt_path.relative_to(root)} must contain generated contract marker exactly once; observed {compact_marker_count}"
            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root to scan",
    )
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    violations = evaluate(root)
    if violations:
        for item in violations:
            print(f"semantic_contract_sync_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("semantic_contract_sync_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
