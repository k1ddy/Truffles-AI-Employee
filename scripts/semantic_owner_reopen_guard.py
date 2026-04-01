#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise SystemExit(f"ERROR: function not found: {name}")


def _return_policy_decision_call(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Call | None:
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "PolicyDecision":
                return call
    return None


def _keyword_node(call: ast.Call, key: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == key:
            return keyword.value
    return None


def _dict_literal_keys(node: ast.AST | None) -> set[str]:
    if not isinstance(node, ast.Dict):
        return set()
    keys: set[str] = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
    return keys


def _assigned_dict_keys(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    variable_name: str,
) -> set[str]:
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == variable_name for target in node.targets):
            continue
        return _dict_literal_keys(node.value)
    return set()


def collect_errors(root: Path = ROOT) -> list[str]:
    config = _load_config(root / "docs" / "SEMANTIC_OWNER_REOPEN_GUARD.yaml")
    errors: list[str] = []

    planner_path = root / config["planner_file"]
    planner_tree = _parse_module(planner_path)
    for builder_name in config.get("planner_builders") or []:
        func = _find_function(planner_tree, builder_name)
        call = _return_policy_decision_call(func)
        if call is None:
            errors.append(f"{planner_path.relative_to(root)}:{builder_name} must return PolicyDecision")
            continue
        source_node = _keyword_node(call, "source")
        if not (
            isinstance(source_node, ast.Constant)
            and source_node.value == "planner_control"
        ):
            errors.append(f"{planner_path.relative_to(root)}:{builder_name} must set source='planner_control'")
        intent_node = _keyword_node(call, "intent")
        if not (
            isinstance(intent_node, ast.Name)
            and intent_node.id == "_SYSTEM_CONTROL_INTENT"
        ):
            errors.append(f"{planner_path.relative_to(root)}:{builder_name} must set intent=_SYSTEM_CONTROL_INTENT")
        meta_keys = _dict_literal_keys(_keyword_node(call, "meta"))
        for required_key in ("control_label", "synthetic_policy_decision"):
            if required_key not in meta_keys:
                errors.append(f"{planner_path.relative_to(root)}:{builder_name} meta missing {required_key}")

    runtime_path = root / config["runtime_file"]
    runtime_tree = _parse_module(runtime_path)
    runtime_func = _find_function(runtime_tree, config["runtime_control_function"])
    decision_meta_keys = _assigned_dict_keys(runtime_func, "decision_meta")
    for required_key in config.get("runtime_control_decision_meta_keys_required") or []:
        if required_key not in decision_meta_keys:
            errors.append(f"{runtime_path.relative_to(root)}:{config['runtime_control_function']} decision_meta missing {required_key}")
    for forbidden_key in config.get("runtime_control_decision_meta_keys_forbidden") or []:
        if forbidden_key in decision_meta_keys:
            errors.append(f"{runtime_path.relative_to(root)}:{config['runtime_control_function']} decision_meta still writes {forbidden_key}")

    for marker in config.get("required_text_markers") or []:
        rel_path = marker["path"]
        text = (root / rel_path).read_text(encoding="utf-8")
        pattern = str(marker["pattern"]).replace("\\n", "\n")
        if pattern not in text:
            errors.append(f"{rel_path} missing marker: {marker['pattern']}")

    return errors


def main() -> int:
    errors = collect_errors(ROOT)
    if errors:
        for error in errors:
            print(f"semantic_owner_reopen_guard: FAIL: {error}", file=sys.stderr)
        return 1
    print("semantic_owner_reopen_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
