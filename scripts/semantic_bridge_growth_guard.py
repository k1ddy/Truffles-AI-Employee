#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def _load_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _tracked_function_names(path: Path, patterns: list[str]) -> set[str]:
    compiled = [re.compile(item) for item in patterns]
    names: set[str] = set()
    for node in ast.walk(_load_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(pattern.match(node.name) for pattern in compiled):
                names.add(node.name)
    return names


def _tracked_policy_snapshot_reasons(path: Path) -> set[str]:
    reasons: set[str] = set()
    for node in ast.walk(_load_tree(path)):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "PolicyCoreRouteSnapshot":
            continue
        for keyword in node.keywords:
            if keyword.arg != "reason":
                continue
            value = keyword.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                reasons.add(value.value)
    return reasons


def _snapshot_diff(label: str, observed: set[str], expected: set[str], file_path: str) -> list[str]:
    violations: list[str] = []
    extras = sorted(observed - expected)
    if extras:
        violations.append(
            f"{file_path}: {label} grew without waiver -> {', '.join(extras)}"
        )
    return violations


def evaluate(root: Path, config: dict) -> list[str]:
    violations: list[str] = []
    hotspots = config.get("hotspots") or []
    for item in hotspots:
        if not isinstance(item, dict):
            continue
        if item.get("active_waiver"):
            continue
        rel_path = item.get("path")
        if not isinstance(rel_path, str) or not rel_path.strip():
            continue
        file_path = root / rel_path
        if not file_path.exists():
            violations.append(f"{rel_path}: hotspot path is missing")
            continue

        tracked_functions = item.get("tracked_function_names")
        if isinstance(tracked_functions, dict):
            patterns = tracked_functions.get("name_patterns") or []
            allowlist = set(tracked_functions.get("exact_allowlist") or [])
            observed = _tracked_function_names(file_path, list(patterns))
            violations.extend(
                _snapshot_diff("tracked function set", observed, allowlist, rel_path)
            )

        tracked_reasons = item.get("tracked_policy_snapshot_reasons")
        if isinstance(tracked_reasons, dict):
            allowlist = set(tracked_reasons.get("exact_allowlist") or [])
            observed = _tracked_policy_snapshot_reasons(file_path)
            violations.extend(
                _snapshot_diff("PolicyCoreRouteSnapshot reason set", observed, allowlist, rel_path)
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/SEMANTIC_BRIDGE_GUARD.yaml")
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_config(root / args.config)
    violations = evaluate(root, config)
    if violations:
        for item in violations:
            print(f"semantic_bridge_growth_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("semantic_bridge_growth_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
