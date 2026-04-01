#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

import yaml


def git_output(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True)


def default_base_ref(repo_root: Path) -> str:
    try:
        return git_output(repo_root, ["merge-base", "HEAD", "origin/main"]).strip()
    except subprocess.CalledProcessError:
        return git_output(repo_root, ["rev-parse", "HEAD~1"]).strip()


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def changed_python_files(repo_root: Path, base_ref: str, head_ref: str | None) -> list[str]:
    diff_args = ["diff", "--name-only", base_ref]
    if head_ref:
        diff_args.append(head_ref)
    diff_args.append("--")
    output = git_output(repo_root, diff_args)
    return [line.strip() for line in output.splitlines() if line.strip().endswith(".py")]


def diff_added_lines(repo_root: Path, file_path: str, base_ref: str, head_ref: str | None) -> tuple[set[int], list[str]]:
    diff_args = ["diff", "--unified=0", "--no-color", base_ref]
    if head_ref:
        diff_args.append(head_ref)
    diff_args.extend(["--", file_path])
    diff = git_output(repo_root, diff_args)
    added_numbers: set[int] = set()
    added_text: list[str] = []
    current_line = None
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            # @@ -a,b +c,d @@
            marker = raw.split("+", 1)[1].split(" ", 1)[0]
            start = marker.split(",", 1)[0]
            current_line = int(start)
            continue
        if raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            if current_line is not None:
                added_numbers.add(current_line)
                current_line += 1
            added_text.append(raw[1:])
            continue
        if raw.startswith("-"):
            continue
        if current_line is not None:
            current_line += 1
    return added_numbers, added_text


def iter_import_names(tree: ast.AST) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                items.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = f"{module}.{alias.name}" if module else alias.name
                items.append((node.lineno, name))
    return items


def node_touches_added_lines(node: ast.AST, added_numbers: set[int]) -> bool:
    lineno = getattr(node, "lineno", None)
    if lineno is None:
        return False
    end_lineno = getattr(node, "end_lineno", lineno)
    return any(line in added_numbers for line in range(lineno, end_lineno + 1))


def expr_contains_proof_path(node: ast.AST, path_suffixes: tuple[str, ...]) -> bool:
    saw_suffix = False
    saw_path_context = False
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if any(child.value.endswith(suffix) for suffix in path_suffixes):
                saw_suffix = True
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "Path":
            saw_path_context = True
        elif isinstance(child, ast.BinOp) and isinstance(child.op, ast.Div):
            saw_path_context = True
        elif isinstance(child, ast.Attribute) and child.attr in {"resolve", "parents", "parent"}:
            saw_path_context = True
    return saw_suffix and saw_path_context


def is_ast_parse_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "ast"
        and func.attr == "parse"
    )


def is_exec_compile_call(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "exec" or not node.args:
        return False
    inner = node.args[0]
    return isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "compile"


def evaluate(repo_root: Path, config: dict, base_ref: str, head_ref: str | None) -> list[str]:
    proof_guard = config.get("proof_guard") or {}
    proof_only_files = set(config.get("proof_only_files") or [])
    runtime_forbidden = tuple(proof_guard.get("forbidden_runtime_imports") or [])
    test_forbidden = tuple(proof_guard.get("forbidden_test_imports") or [])
    semantic_tokens = tuple(proof_guard.get("semantic_contract_tokens") or [])
    test_path_suffixes = tuple(proof_guard.get("forbidden_test_path_suffixes") or [])
    violations: list[str] = []

    for file_path in changed_python_files(repo_root, base_ref, head_ref):
        added_numbers, added_text = diff_added_lines(repo_root, file_path, base_ref, head_ref)
        absolute = repo_root / file_path
        if not absolute.exists():
            continue
        if file_path in proof_only_files:
            for line in added_text:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if any(token in line for token in semantic_tokens):
                    violations.append(f"{file_path}: proof-only file gained semantic-authority token -> {stripped}")
            continue

        source = absolute.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(absolute))
        imports = iter_import_names(tree)
        if file_path.startswith("truffles-api/app/"):
            for lineno, name in imports:
                if lineno in added_numbers and any(name == item or name.startswith(f"{item}.") for item in runtime_forbidden):
                    violations.append(f"{file_path}:{lineno}: runtime import from proof-only module -> {name}")
        if file_path.startswith("truffles-api/tests/"):
            for lineno, name in imports:
                if lineno in added_numbers and any(name == item or name.startswith(f"{item}.") for item in test_forbidden):
                    violations.append(f"{file_path}:{lineno}: test import from proof-only module -> {name}")
            proof_path_vars: set[str] = set()
            proof_path_reads: list[str] = []
            exec_or_parse_calls: list[str] = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and node_touches_added_lines(node, added_numbers):
                    if expr_contains_proof_path(node.value, test_path_suffixes):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                proof_path_vars.add(target.id)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node_touches_added_lines(node, added_numbers):
                    continue
                if isinstance(node.func, ast.Attribute) and node.func.attr == "read_text":
                    receiver = node.func.value
                    if (
                        isinstance(receiver, ast.Name)
                        and receiver.id in proof_path_vars
                        or expr_contains_proof_path(receiver, test_path_suffixes)
                    ):
                        proof_path_reads.append(ast.get_source_segment(source, node) or "read_text(...)")
                        continue
                if is_ast_parse_call(node):
                    exec_or_parse_calls.append(ast.get_source_segment(source, node) or "ast.parse(...)")
                    continue
                if is_exec_compile_call(node):
                    exec_or_parse_calls.append(ast.get_source_segment(source, node) or "exec(compile(...))")

            if proof_path_reads and exec_or_parse_calls:
                violations.append(
                    f"{file_path}: test AST/exec load from proof-only path -> "
                    f"{proof_path_reads[0]} | {exec_or_parse_calls[0]}"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/LEGACY_SUNSET.yaml")
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--head-ref", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root or Path(__file__).resolve().parents[1])
    config = load_config(repo_root / args.config)
    base_ref = args.base_ref or default_base_ref(repo_root)
    violations = evaluate(repo_root, config, base_ref, args.head_ref)
    if violations:
        for item in violations:
            print(f"proof_path_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("proof_path_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
