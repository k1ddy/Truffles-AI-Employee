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


def _py_files(root: Path, rel_roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel_root in rel_roots:
        base = root / rel_root
        if not base.exists():
            continue
        files.extend(sorted(base.rglob("*.py")))
    return files


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent is None:
            return None
        return f"{parent}.{node.attr}"
    return None


def _tracked_function_names(path: Path, patterns: list[str]) -> set[str]:
    compiled = [re.compile(item) for item in patterns]
    names: set[str] = set()
    for node in ast.walk(_load_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(pattern.match(node.name) for pattern in compiled):
                names.add(node.name)
    return names


def _snapshot_diff(label: str, observed: set[str], expected: set[str], file_path: str) -> list[str]:
    violations: list[str] = []
    extras = sorted(observed - expected)
    missing = sorted(expected - observed)
    if extras:
        violations.append(f"{file_path}: {label} grew without waiver -> {', '.join(extras)}")
    if missing:
        violations.append(f"{file_path}: {label} drifted below snapshot -> {', '.join(missing)}")
    return violations


def _callsite_files(root: Path, search_roots: list[str], call_name: str) -> set[str]:
    observed: set[str] = set()
    for path in _py_files(root, search_roots):
        tree = _load_tree(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node.func) == call_name:
                observed.add(path.relative_to(root).as_posix())
                break
    return observed


def _callsites_missing_keywords(
    root: Path,
    search_roots: list[str],
    call_name: str,
    required_keywords: list[str],
) -> list[str]:
    violations: list[str] = []
    required = set(required_keywords)
    for path in _py_files(root, search_roots):
        tree = _load_tree(path)
        function_stack: list[str] = []

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            def visit_Call(self, node: ast.Call) -> None:
                if _call_name(node.func) == call_name:
                    observed = {item.arg for item in node.keywords if item.arg}
                    missing = sorted(required - observed)
                    if missing:
                        owner = function_stack[-1] if function_stack else "<module>"
                        violations.append(
                            f"{path.relative_to(root).as_posix()}:{owner}: {call_name} missing required keywords -> {', '.join(missing)}"
                        )
                self.generic_visit(node)

        Visitor().visit(tree)
    return violations


def evaluate(root: Path, config: dict) -> list[str]:
    violations: list[str] = []

    for item in config.get("hotspots") or []:
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

    for item in config.get("repo_callsite_contracts") or []:
        if not isinstance(item, dict):
            continue
        call_name = item.get("call_name")
        search_roots = item.get("search_roots") or []
        allowlist = set(item.get("exact_allowlist") or [])
        if not isinstance(call_name, str):
            continue
        observed = _callsite_files(root, list(search_roots), call_name)
        violations.extend(
            _snapshot_diff(f"repo callsite set for {call_name}", observed, allowlist, "repo")
        )

    for item in config.get("keyword_call_contracts") or []:
        if not isinstance(item, dict):
            continue
        call_name = item.get("call_name")
        search_roots = item.get("search_roots") or []
        required_keywords = item.get("required_keywords") or []
        allowlist = set(item.get("exact_allowlist") or [])
        if not isinstance(call_name, str):
            continue
        observed = _callsite_files(root, list(search_roots), call_name)
        violations.extend(
            _snapshot_diff(f"keyword-guarded callsite set for {call_name}", observed, allowlist, "repo")
        )
        violations.extend(
            _callsites_missing_keywords(root, list(search_roots), call_name, list(required_keywords))
        )

    for item in config.get("forbidden_text_contracts") or []:
        if not isinstance(item, dict):
            continue
        rel_path = item.get("path")
        patterns = item.get("patterns") or []
        if not isinstance(rel_path, str):
            continue
        text_path = root / rel_path
        if not text_path.exists():
            violations.append(f"{rel_path}: forbidden-text path is missing")
            continue
        text = text_path.read_text(encoding="utf-8")
        for pattern in patterns:
            if isinstance(pattern, str) and pattern in text:
                violations.append(f"{rel_path}: forbidden text present -> {pattern}")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/FACT_PLANE_GUARD.yaml")
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_config(root / args.config)
    violations = evaluate(root, config)
    if violations:
        for item in violations:
            print(f"fact_plane_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("fact_plane_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
