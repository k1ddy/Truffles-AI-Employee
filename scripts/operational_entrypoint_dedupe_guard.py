#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = 'docs/OPERATIONAL_ENTRYPOINT_DEDUPE_GUARD.yaml'


def repo_root() -> Path:
    return ROOT


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit(f'ERROR: invalid YAML mapping: {path}')
    return data


def load_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


def call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def imported_modules(path: Path) -> set[str]:
    tree = load_tree(path)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and isinstance(node.module, str):
            modules.add(node.module)
    return modules


def imported_names(path: Path) -> set[str]:
    tree = load_tree(path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def defined_functions(path: Path) -> set[str]:
    tree = load_tree(path)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def module_exports(path: Path) -> set[str]:
    tree = load_tree(path)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if not isinstance(node.value, (ast.List, ast.Tuple)):
                    return set()
                exports: set[str] = set()
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        exports.add(item.value)
                return exports
    return set()


def called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            name = call_name(item.func)
            if name:
                names.add(name)
    return names


def function_calls(path: Path, function_name: str) -> set[str]:
    tree = load_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return called_names(node)
    return set()


def repo_callsite_paths(root: Path, search_roots: list[str], call_names: list[str]) -> set[str]:
    tracked = set(call_names)
    observed: set[str] = set()
    for rel in search_roots:
        base = root / rel
        if not base.exists():
            continue
        for path in sorted(base.rglob('*.py')):
            tree = load_tree(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and call_name(node.func) in tracked:
                    observed.add(str(path.relative_to(root)))
                    break
    return observed


def snapshot_diff(label: str, observed: set[str], expected: set[str], path: str) -> list[str]:
    errors: list[str] = []
    extras = sorted(observed - expected)
    missing = sorted(expected - observed)
    if extras:
        errors.append(f'{path}: {label} grew without waiver -> {", ".join(extras)}')
    if missing:
        errors.append(f'{path}: {label} drifted below snapshot -> {", ".join(missing)}')
    return errors


def evaluate(root: Path, config: dict) -> list[str]:
    errors: list[str] = []

    for hotspot in config.get('hotspots') or []:
        path = root / hotspot['path']
        if not path.exists():
            errors.append(f"{hotspot['path']}: hotspot path is missing")
            continue

        modules = imported_modules(path)
        names = imported_names(path)
        defs = defined_functions(path)
        exports = module_exports(path)
        file_calls = called_names(load_tree(path))

        for module in hotspot.get('forbidden_import_modules') or []:
            if module in modules:
                errors.append(f"{hotspot['path']}: forbidden import module still present -> {module}")
        for name in hotspot.get('required_import_names') or []:
            if name not in names:
                errors.append(f"{hotspot['path']}: missing required import name -> {name}")
        for name in hotspot.get('forbidden_import_names') or []:
            if name in names:
                errors.append(f"{hotspot['path']}: forbidden import name still present -> {name}")
        for name in hotspot.get('required_function_defs') or []:
            if name not in defs:
                errors.append(f"{hotspot['path']}: missing required function definition -> {name}")
        for name in hotspot.get('required_exports') or []:
            if name not in exports:
                errors.append(f"{hotspot['path']}: missing required export -> {name}")
        for name in hotspot.get('forbidden_exports') or []:
            if name in exports:
                errors.append(f"{hotspot['path']}: forbidden export still present -> {name}")
        for name in hotspot.get('forbidden_call_names') or []:
            if name in file_calls:
                errors.append(f"{hotspot['path']}: forbidden file-level call still present -> {name}")

    for contract in config.get('function_call_contracts') or []:
        path = root / contract['path']
        if not path.exists():
            errors.append(f"{contract['path']}: function contract path is missing")
            continue
        observed = function_calls(path, contract['function_name'])
        if not observed:
            errors.append(f"{contract['path']}: function missing or empty -> {contract['function_name']}")
            continue
        for name in contract.get('required_calls') or []:
            if name not in observed:
                errors.append(f"{contract['path']}:{contract['function_name']}: missing required call -> {name}")
        for name in contract.get('forbidden_calls') or []:
            if name in observed:
                errors.append(f"{contract['path']}:{contract['function_name']}: forbidden call still present -> {name}")

    for contract in config.get('repo_callsite_contracts') or []:
        observed = repo_callsite_paths(root, contract.get('search_roots') or [], contract.get('call_names') or [])
        expected = set(contract.get('exact_allowlist') or [])
        label = 'repo callsite set for ' + ', '.join(contract.get('call_names') or [])
        errors.extend(snapshot_diff(label, observed, expected, '<repo>'))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=DEFAULT_CONFIG)
    args = parser.parse_args()

    root = repo_root()
    config = load_config(root / args.config)
    errors = evaluate(root, config)
    if errors:
        for error in errors:
            print(f'ERROR: {error}')
        return 1
    print('Operational entrypoint dedupe guard: OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
