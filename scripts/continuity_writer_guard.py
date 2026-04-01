#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

import yaml


GUARDED_HELPER_CALLS = {
    "_capture_pending_resume_context",
    "_restore_pending_resume_context",
    "_restore_pending_resume_payload",
    "_set_pending_resume",
}

CONTEXT_CONTAINER_NAMES = {
    "context",
    "context_manager",
    "working_context",
    "restored_context",
    "normalized_context",
    "updated_context",
    "snapshot_context",
    "pending_resume",
    "session_memory",
    "canonical_state",
}


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


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid JSON object: {path}")
    return data


def resolve_guard_config(repo_root: Path, config: dict) -> dict:
    if isinstance(config.get("continuity_guard"), dict):
        return config

    legacy_rel = config.get("legacy_sunset")
    inventory_rel = config.get("compatibility_carrier_inventory")
    if not isinstance(legacy_rel, str) or not isinstance(inventory_rel, str):
        return config

    legacy = load_config(repo_root / legacy_rel)
    inventory = load_json(repo_root / inventory_rel)
    freeze_guard = inventory.get("freeze_guard") if isinstance(inventory.get("freeze_guard"), dict) else {}
    legacy_guard = legacy.get("continuity_guard") if isinstance(legacy.get("continuity_guard"), dict) else {}

    continuity_guard = {
        "allowed_writer_paths": freeze_guard.get("allowed_new_writer_paths")
        or legacy_guard.get("allowed_writer_paths")
        or [],
        "guarded_tokens": freeze_guard.get("guarded_context_tokens")
        or legacy_guard.get("guarded_tokens")
        or [],
    }
    return {
        "sunset_files": legacy.get("sunset_files") or [],
        "continuity_guard": continuity_guard,
    }


def changed_python_files(repo_root: Path, base_ref: str, head_ref: str | None) -> list[str]:
    diff_args = ["diff", "--name-only", base_ref]
    if head_ref:
        diff_args.append(head_ref)
    diff_args.append("--")
    output = git_output(repo_root, diff_args)
    return [line.strip() for line in output.splitlines() if line.strip().endswith(".py")]


def added_line_numbers(repo_root: Path, file_path: str, base_ref: str, head_ref: str | None) -> set[int]:
    diff_args = ["diff", "--unified=0", "--no-color", base_ref]
    if head_ref:
        diff_args.append(head_ref)
    diff_args.extend(["--", file_path])
    diff = git_output(repo_root, diff_args)
    added: set[int] = set()
    current_new_line = None
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            header = raw.split("@@", 2)[1].strip()
            plus_chunk = next(
                (part for part in header.split() if part.startswith("+")),
                None,
            )
            if not plus_chunk:
                current_new_line = None
                continue
            start_text = plus_chunk[1:].split(",", 1)[0]
            current_new_line = int(start_text)
            continue
        if current_new_line is None:
            continue
        if raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            added.add(current_new_line)
            current_new_line += 1
            continue
        if raw.startswith("-"):
            continue
        current_new_line += 1
    return added


def _active_waiver_for_file(config: dict, file_path: str) -> object:
    for item in config.get("sunset_files", []):
        if isinstance(item, dict) and item.get("path") == file_path:
            return item.get("active_waiver")
    return None


def _waiver_allows_line(waiver: object, stripped_line: str) -> bool:
    if not waiver:
        return False
    if not isinstance(waiver, dict):
        return True
    allowed = waiver.get("allowed_executable_lines")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        return True
    return stripped_line in {item.strip() for item in allowed}


def _load_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _node_touches_added_lines(node: ast.AST, added_lines: set[int]) -> bool:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)
    if not isinstance(start, int):
        return False
    if not isinstance(end, int):
        end = start
    return any(line in added_lines for line in range(start, end + 1))


def _source_segment(source: str, node: ast.AST) -> str:
    return (ast.get_source_segment(source, node) or "").strip()


def _call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _subscript_key(node: ast.Subscript) -> str | None:
    slice_node = node.slice
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return slice_node.value
    return None


def _name_like(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_context_container(node: ast.AST | None) -> bool:
    name = _name_like(node)
    return isinstance(name, str) and name in CONTEXT_CONTAINER_NAMES


def _is_guarded_context_subscript(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and _is_context_container(node.value)
        and _subscript_key(node) is not None
    )


def _guarded_target(node: ast.AST, guarded_tokens: set[str]) -> bool:
    if isinstance(node, ast.Subscript):
        key = _subscript_key(node)
        return (
            key in guarded_tokens
            and _is_context_container(node.value)
        )
    return False


def _collect_assigned_names(target: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(target, ast.Name):
        names.add(target.id)
        return names
    if isinstance(target, (ast.Tuple, ast.List)):
        for item in target.elts:
            names.update(_collect_assigned_names(item))
    return names


def _value_uses_guarded_helper(value: ast.AST, helper_bound_names: set[str]) -> bool:
    if isinstance(value, ast.Name):
        return value.id in helper_bound_names
    if isinstance(value, ast.Call):
        return _call_name(value.func) in GUARDED_HELPER_CALLS
    return any(_value_uses_guarded_helper(child, helper_bound_names) for child in ast.iter_child_nodes(value))


def _assignment_violations(
    *,
    node: ast.AST,
    source: str,
    helper_bound_names: set[str],
    guarded_tokens: set[str],
) -> list[str]:
    violations: list[str] = []
    target_nodes: list[ast.AST] = []
    value: ast.AST | None = None
    if isinstance(node, ast.Assign):
        target_nodes = list(node.targets)
        value = node.value
    elif isinstance(node, ast.AnnAssign):
        target_nodes = [node.target]
        value = node.value
    elif isinstance(node, ast.AugAssign):
        target_nodes = [node.target]
        value = node.value
    if value is None:
        return violations
    for target in target_nodes:
        if _guarded_target(target, guarded_tokens):
            violations.append(_source_segment(source, node))
            continue
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "context"
            and _value_uses_guarded_helper(value, helper_bound_names)
        ):
            violations.append(_source_segment(source, node))
    return [item for item in violations if item]


def _call_violations(
    *,
    node: ast.Call,
    source: str,
    guarded_tokens: set[str],
) -> list[str]:
    func_name = _call_name(node.func)
    if func_name not in {"update", "setdefault", "pop"}:
        return []
    receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
    if not _is_context_container(receiver):
        return []
    if func_name == "pop" and node.args:
        key = node.args[0]
        if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in guarded_tokens:
            return [_source_segment(source, node)]
        return []
    if func_name == "setdefault" and node.args:
        key = node.args[0]
        if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value in guarded_tokens:
            return [_source_segment(source, node)]
        return []
    if func_name == "update":
        dict_args = [arg for arg in node.args if isinstance(arg, ast.Dict)]
        dict_args.extend(
            keyword.value
            for keyword in node.keywords
            if isinstance(keyword.value, ast.Dict)
        )
        for dict_node in dict_args:
            for key_node in dict_node.keys:
                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                    if key_node.value in guarded_tokens:
                        return [_source_segment(source, node)]
    return []


def _file_violations(
    *,
    path: Path,
    added_lines: set[int],
    guarded_tokens: set[str],
    waiver: object,
) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    helper_bound_names: set[str] = set()
    violations: list[str] = []
    for node in ast.walk(tree):
        if not _node_touches_added_lines(node, added_lines):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(getattr(node, "value", None), ast.Call):
            call_name = _call_name(node.value.func)
            if call_name in GUARDED_HELPER_CALLS:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    helper_bound_names.update(_collect_assigned_names(target))
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for item in _assignment_violations(
                node=node,
                source=source,
                helper_bound_names=helper_bound_names,
                guarded_tokens=guarded_tokens,
            ):
                if not _waiver_allows_line(waiver, item):
                    violations.append(item)
        if isinstance(node, ast.Call):
            for item in _call_violations(
                node=node,
                source=source,
                guarded_tokens=guarded_tokens,
            ):
                if not _waiver_allows_line(waiver, item):
                    violations.append(item)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in violations:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def evaluate(repo_root: Path, config: dict, base_ref: str, head_ref: str | None) -> list[str]:
    continuity = config.get("continuity_guard") or {}
    allowed = set(continuity.get("allowed_writer_paths") or [])
    guarded_tokens = set(continuity.get("guarded_tokens") or [])
    violations: list[str] = []
    for file_path in changed_python_files(repo_root, base_ref, head_ref):
        if not file_path.startswith("truffles-api/app/"):
            continue
        if file_path in allowed:
            continue
        added_lines = added_line_numbers(repo_root, file_path, base_ref, head_ref)
        if not added_lines:
            continue
        waiver = _active_waiver_for_file(config, file_path)
        file_violations = _file_violations(
            path=repo_root / file_path,
            added_lines=added_lines,
            guarded_tokens=guarded_tokens,
            waiver=waiver,
        )
        for item in file_violations:
            violations.append(f"{file_path}: continuity token added outside allowed writers -> {item}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/SOURCE_OF_TRUTH.yaml")
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--head-ref", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root or Path(__file__).resolve().parents[1])
    config = resolve_guard_config(repo_root, load_config(repo_root / args.config))
    base_ref = args.base_ref or default_base_ref(repo_root)
    violations = evaluate(repo_root, config, base_ref, args.head_ref)
    if violations:
        for item in violations:
            print(f"continuity_writer_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("continuity_writer_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
