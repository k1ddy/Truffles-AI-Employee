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
    if extras:
        violations.append(f"{file_path}: {label} grew without waiver -> {', '.join(extras)}")
    return violations


def _tracked_function_names(path: Path, patterns: list[str]) -> set[str]:
    compiled = [re.compile(item) for item in patterns]
    names: set[str] = set()
    for node in ast.walk(_load_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            pattern.match(node.name) for pattern in compiled
        ):
            names.add(node.name)
    return names


def _string_collection_from_ast(node: ast.AST) -> list[str] | None:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for item in node.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            values.append(item.value)
        return values
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "frozenset":
        if len(node.args) != 1:
            return None
        return _string_collection_from_ast(node.args[0])
    return None


def _tracked_literal_members(path: Path, symbol_name: str) -> set[str] | None:
    tree = _load_tree(path)
    for node in tree.body:
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == symbol_name for target in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == symbol_name:
                value = node.value
        if value is None:
            continue
        members = _string_collection_from_ast(value)
        if members is None:
            return None
        return set(members)
    return None


class _FunctionCallParentVisitor(ast.NodeVisitor):
    def __init__(self, call_names: set[str]) -> None:
        self._call_names = call_names
        self._stack: list[str] = []
        self.matched: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pragma: no cover - exercised via evaluate
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # pragma: no cover - exercised via evaluate
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if _call_name(node.func) in self._call_names and self._stack:
            self.matched.add(self._stack[-1])
        self.generic_visit(node)


def _tracked_call_parent_functions(path: Path, call_names: list[str]) -> set[str]:
    visitor = _FunctionCallParentVisitor(set(call_names))
    visitor.visit(_load_tree(path))
    return visitor.matched


class _OverrideMetaKeyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.keys: set[str] = set()

    @staticmethod
    def _is_override_meta(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "meta"
            and isinstance(node.value, ast.Name)
            and node.value.id == "override"
        )

    @staticmethod
    def _constant_string(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and self._is_override_meta(node.func.value)
            and node.args
        ):
            key = self._constant_string(node.args[0])
            if key:
                self.keys.add(key)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._is_override_meta(node.value):
            key = self._constant_string(node.slice)
            if key:
                self.keys.add(key)
        self.generic_visit(node)


def _tracked_override_meta_get_keys(path: Path) -> set[str]:
    visitor = _OverrideMetaKeyVisitor()
    visitor.visit(_load_tree(path))
    return visitor.keys


def _python_files(root: Path, search_roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in search_roots:
        base = root / rel
        if not base.exists():
            continue
        files.extend(sorted(base.rglob("*.py")))
    return files


class _RepoCallsiteVisitor(ast.NodeVisitor):
    def __init__(self, call_names: set[str]) -> None:
        self._call_names = call_names
        self.matched = False

    def visit_Call(self, node: ast.Call) -> None:
        if _call_name(node.func) in self._call_names:
            self.matched = True
        if not self.matched:
            self.generic_visit(node)


def _repo_callsite_paths(root: Path, search_roots: list[str], call_names: list[str]) -> set[str]:
    observed: set[str] = set()
    for path in _python_files(root, search_roots):
        visitor = _RepoCallsiteVisitor(set(call_names))
        visitor.visit(_load_tree(path))
        if visitor.matched:
            observed.add(str(path.relative_to(root)))
    return observed


def evaluate(root: Path, config: dict) -> list[str]:
    violations: list[str] = []
    hotspots = config.get("hotspots") or []
    for item in hotspots:
        if not isinstance(item, dict) or item.get("active_waiver"):
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
            violations.extend(_snapshot_diff("tracked function set", observed, allowlist, rel_path))

        tracked_literals = item.get("tracked_literal_members") or []
        for literal_contract in tracked_literals:
            if not isinstance(literal_contract, dict):
                continue
            symbol_name = literal_contract.get("symbol")
            if not isinstance(symbol_name, str) or not symbol_name.strip():
                continue
            observed = _tracked_literal_members(file_path, symbol_name)
            if observed is None:
                violations.append(f"{rel_path}: literal member snapshot missing or non-literal for {symbol_name}")
                continue
            allowlist = set(literal_contract.get("exact_allowlist") or [])
            violations.extend(
                _snapshot_diff(f"{symbol_name} literal member set", observed, allowlist, rel_path)
            )

        tracked_call_parent_functions = item.get("tracked_call_parent_functions") or []
        for contract in tracked_call_parent_functions:
            if not isinstance(contract, dict):
                continue
            call_names = contract.get("call_names") or []
            allowlist = set(contract.get("exact_allowlist") or [])
            observed = _tracked_call_parent_functions(file_path, list(call_names))
            label = f"call parent set for {', '.join(call_names)}"
            violations.extend(_snapshot_diff(label, observed, allowlist, rel_path))

        tracked_override_meta_keys = item.get("tracked_override_meta_get_keys")
        if isinstance(tracked_override_meta_keys, dict):
            allowlist = set(tracked_override_meta_keys.get("exact_allowlist") or [])
            observed = _tracked_override_meta_get_keys(file_path)
            violations.extend(_snapshot_diff("override.meta key read set", observed, allowlist, rel_path))

    for contract in config.get("repo_callsite_contracts") or []:
        if not isinstance(contract, dict) or contract.get("active_waiver"):
            continue
        search_roots = contract.get("search_roots") or []
        call_names = contract.get("call_names") or []
        allowlist = set(contract.get("exact_allowlist") or [])
        observed = _repo_callsite_paths(root, list(search_roots), list(call_names))
        label = f"repo callsite set for {', '.join(call_names)}"
        violations.extend(_snapshot_diff(label, observed, allowlist, '<repo>'))

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/BOUNDARY_DEGRADE_GUARD.yaml")
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_config(root / args.config)
    violations = evaluate(root, config)
    if violations:
        for item in violations:
            print(f"boundary_degrade_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("boundary_degrade_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
