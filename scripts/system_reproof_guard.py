#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "docs/SYSTEM_REPROOF_GUARD.yaml"


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def load_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def defined_functions(path: Path) -> set[str]:
    tree = load_tree(path)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def function_node(path: Path, function_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    tree = load_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    return None


def function_calls(path: Path, function_name: str) -> set[str]:
    node = function_node(path, function_name)
    if node is None:
        return set()
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            name = call_name(item.func)
            if name:
                names.add(name)
    return names


def function_source(path: Path, function_name: str) -> str:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    node = function_node(path, function_name)
    if node is None:
        return ""
    end_lineno = getattr(node, "end_lineno", None)
    if end_lineno is None:
        return ""
    return "\n".join(lines[node.lineno - 1 : end_lineno])


def evaluate(root: Path, config: dict) -> list[str]:
    errors: list[str] = []

    for hotspot in config.get("hotspots") or []:
        path = root / hotspot["path"]
        if not path.exists():
            errors.append(f"{hotspot['path']}: hotspot path is missing")
            continue
        defs = defined_functions(path)
        for name in hotspot.get("required_function_defs") or []:
            if name not in defs:
                errors.append(f"{hotspot['path']}: missing required function definition -> {name}")

    for contract in config.get("function_call_contracts") or []:
        path = root / contract["path"]
        if not path.exists():
            errors.append(f"{contract['path']}: function contract path is missing")
            continue
        observed = function_calls(path, contract["function_name"])
        if not observed:
            errors.append(f"{contract['path']}: function missing or empty -> {contract['function_name']}")
            continue
        for name in contract.get("required_calls") or []:
            if name not in observed:
                errors.append(f"{contract['path']}:{contract['function_name']}: missing required call -> {name}")
        for name in contract.get("forbidden_calls") or []:
            if name in observed:
                errors.append(f"{contract['path']}:{contract['function_name']}: forbidden call still present -> {name}")

    for contract in config.get("function_source_contracts") or []:
        path = root / contract["path"]
        if not path.exists():
            errors.append(f"{contract['path']}: source contract path is missing")
            continue
        source = function_source(path, contract["function_name"])
        if not source:
            errors.append(f"{contract['path']}: function missing or empty -> {contract['function_name']}")
            continue
        for snippet in contract.get("required_substrings") or []:
            if snippet not in source:
                errors.append(f"{contract['path']}:{contract['function_name']}: missing required source snippet -> {snippet}")
        for snippet in contract.get("forbidden_substrings") or []:
            if snippet in source:
                errors.append(f"{contract['path']}:{contract['function_name']}: forbidden source snippet still present -> {snippet}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = load_config(ROOT / args.config)
    errors = evaluate(ROOT, config)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("System reproof guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
