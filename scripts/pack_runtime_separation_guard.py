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


def _call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _snapshot_diff(label: str, observed: set[str], expected: set[str], file_path: str) -> list[str]:
    violations: list[str] = []
    extras = sorted(observed - expected)
    missing = sorted(expected - observed)
    if extras:
        violations.append(f"{file_path}: {label} grew without waiver -> {', '.join(extras)}")
    if missing:
        violations.append(f"{file_path}: {label} drifted below snapshot -> {', '.join(missing)}")
    return violations


def _python_files(root: Path, search_roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in search_roots:
        base = root / rel
        if base.exists():
            files.extend(sorted(base.rglob("*.py")))
    return files


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    tree = _load_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and isinstance(node.module, str):
            modules.add(node.module)
    return modules


def _imported_names(path: Path) -> set[str]:
    names: set[str] = set()
    tree = _load_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _defined_functions(path: Path) -> set[str]:
    tree = _load_tree(path)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _called_names(path: Path) -> set[str]:
    names: set[str] = set()
    tree = _load_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name:
                names.add(name)
    return names


def _tracked_function_names(path: Path, patterns: list[str]) -> set[str]:
    compiled = [re.compile(item) for item in patterns]
    names: set[str] = set()
    tree = _load_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            pattern.match(node.name) for pattern in compiled
        ):
            names.add(node.name)
    return names


def _repo_callsite_paths(root: Path, search_roots: list[str], call_names: list[str]) -> set[str]:
    observed: set[str] = set()
    tracked = set(call_names)
    for path in _python_files(root, search_roots):
        tree = _load_tree(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node.func) in tracked:
                observed.add(str(path.relative_to(root)))
                break
    return observed


def evaluate(root: Path, config: dict) -> list[str]:
    violations: list[str] = []
    for hotspot in config.get("hotspots") or []:
        if not isinstance(hotspot, dict) or hotspot.get("active_waiver"):
            continue
        rel_path = hotspot.get("path")
        if not isinstance(rel_path, str) or not rel_path.strip():
            continue
        file_path = root / rel_path
        if not file_path.exists():
            violations.append(f"{rel_path}: hotspot path is missing")
            continue

        imported_modules = _imported_modules(file_path)
        for module in hotspot.get("forbidden_import_modules") or []:
            if module in imported_modules:
                violations.append(f"{rel_path}: forbidden import module still present -> {module}")

        imported_names = _imported_names(file_path)
        for name in hotspot.get("forbidden_import_names") or []:
            if name in imported_names:
                violations.append(f"{rel_path}: forbidden import name still present -> {name}")

        defined_functions = _defined_functions(file_path)
        for name in hotspot.get("forbidden_function_defs") or []:
            if name in defined_functions:
                violations.append(f"{rel_path}: forbidden function definition still present -> {name}")

        called_names = _called_names(file_path)
        for name in hotspot.get("forbidden_call_names") or []:
            if name in called_names:
                violations.append(f"{rel_path}: forbidden call name still present -> {name}")

        tracked = hotspot.get("tracked_function_names")
        if isinstance(tracked, dict):
            observed = _tracked_function_names(file_path, tracked.get("name_patterns") or [])
            expected = set(tracked.get("exact_allowlist") or [])
            violations.extend(_snapshot_diff("tracked function set", observed, expected, rel_path))

    for contract in config.get("repo_callsite_contracts") or []:
        if not isinstance(contract, dict):
            continue
        observed = _repo_callsite_paths(
            root,
            list(contract.get("search_roots") or []),
            list(contract.get("call_names") or []),
        )
        expected = set(contract.get("exact_allowlist") or [])
        label = "repo callsite set for " + ", ".join(contract.get("call_names") or [])
        violations.extend(_snapshot_diff(label, observed, expected, "<repo>"))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="docs/PACK_RUNTIME_SEPARATION_GUARD.yaml",
        help="Path to guard config relative to repo root",
    )
    args = parser.parse_args()

    root = repo_root()
    config = load_config(root / args.config)
    violations = evaluate(root, config)
    if violations:
        for item in violations:
            print(f"ERROR: {item}")
        return 1
    print("Pack/runtime separation guard: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
