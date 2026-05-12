#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


REASON_CODE = "boundary_semantic_normalization"
INTENT_SERVICE = "truffles-api/app/services/intent_service.py"
TURN_PLANNER = "truffles-api/app/core/turn_planner.py"
CONSULTANT_RUNTIME = "truffles-api/app/core/consultant_runtime.py"
DIAGNOSE = "ops/diagnose.py"

REQUIRED_SNIPPETS = {
    INTENT_SERVICE: (
        '_POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE = "boundary_semantic_normalization"',
        '"reason_code": _POLICY_CORE_BOUNDARY_SEMANTIC_NORMALIZATION_REASON_CODE',
        'result["boundary_normalization_used"] = True',
        'result["boundary_normalization_events"] = events',
        'result["llm_policy_override_reason_code"] = (',
        'result["llm_policy_override_reason_codes"] = reason_codes',
        '_policy_core_sync_boundary_normalization_audit(result)',
        'result["semantic_intent_overrides"] = semantic_override_events',
        'result["semantic_arbiter_audit"] = {',
    ),
    TURN_PLANNER: (
        '("boundary_normalization_used", "boundary_normalization_used")',
        '("boundary_normalization_events", "boundary_normalization_events")',
        '("llm_policy_override_reason_code", "llm_policy_override_reason_code")',
        '("llm_policy_override_reason_codes", "llm_policy_override_reason_codes")',
        '("semantic_intent_overrides", "semantic_intent_overrides")',
        '("semantic_arbiter_audit", "semantic_arbiter_audit")',
    ),
    CONSULTANT_RUNTIME: (
        'decision_meta["boundary_normalization_used"] = bool(',
        'decision_meta["boundary_normalization_events"] = list(',
        'decision_meta["llm_policy_override_reason_code"] = override_reason_code.strip()',
        'decision_meta["llm_policy_override_reason_codes"] = list(',
        'llm_policy_core_meta["semantic_intent_overrides"] = list(',
        '"audit": dict(semantic_arbiter_audit)',
    ),
}

CALL_PARENT_CONTRACTS = {
    "_policy_core_record_boundary_normalization": {
        "path": INTENT_SERVICE,
        "allowlist": {
            "route_llm_policy_core",
            "_policy_core_apply_schema_boundary_normalizations",
        },
    },
    "_policy_core_sync_boundary_normalization_audit": {
        "path": INTENT_SERVICE,
        "allowlist": {"_policy_core_record_boundary_normalization"},
    },
}

TOKEN_PATH_ALLOWLISTS = {
    "boundary_normalization_used": {
        CONSULTANT_RUNTIME,
        INTENT_SERVICE,
        TURN_PLANNER,
    },
    "boundary_normalization_events": {
        CONSULTANT_RUNTIME,
        INTENT_SERVICE,
        TURN_PLANNER,
    },
    "semantic_intent_overrides": {
        CONSULTANT_RUNTIME,
        INTENT_SERVICE,
        TURN_PLANNER,
        DIAGNOSE,
    },
    "semantic_arbiter_audit": {
        CONSULTANT_RUNTIME,
        INTENT_SERVICE,
        TURN_PLANNER,
        "truffles-api/app/routers/webhook/decision.py",
    },
}

SEARCH_ROOTS = ("truffles-api/app", "ops")


def _load_text(root: Path, relative_path: str) -> str:
    path = root / relative_path
    if not path.exists():
        raise SystemExit(f"boundary_rewrite_guard: FAIL: missing required file {relative_path}")
    return path.read_text(encoding="utf-8")


def _load_tree(root: Path, relative_path: str) -> ast.AST:
    path = root / relative_path
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


class _FunctionCallParentVisitor(ast.NodeVisitor):
    def __init__(self, target_name: str) -> None:
        self._target_name = target_name
        self._stack: list[str] = []
        self.parents: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if _call_name(node.func) == self._target_name and self._stack:
            self.parents.add(self._stack[-1])
        self.generic_visit(node)


def _find_call_parents(root: Path, *, relative_path: str, target_name: str) -> set[str]:
    visitor = _FunctionCallParentVisitor(target_name)
    visitor.visit(_load_tree(root, relative_path))
    return visitor.parents


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative_root in SEARCH_ROOTS:
        base = root / relative_root
        if not base.exists():
            continue
        files.extend(sorted(base.rglob("*.py")))
    return files


def _paths_with_token(root: Path, token: str) -> set[str]:
    paths: set[str] = set()
    for path in _iter_python_files(root):
        text = path.read_text(encoding="utf-8")
        if token in text:
            paths.add(str(path.relative_to(root)))
    return paths


def _literal_members(root: Path, *, relative_path: str, symbol_name: str) -> set[str] | None:
    tree = _load_tree(root, relative_path)
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
        if not isinstance(value, (ast.Set, ast.List, ast.Tuple)):
            return None
        members: set[str] = set()
        for item in value.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            members.add(item.value)
        return members
    return None


def evaluate(root: Path) -> list[str]:
    violations: list[str] = []

    for relative_path, snippets in REQUIRED_SNIPPETS.items():
        text = _load_text(root, relative_path)
        for snippet in snippets:
            if snippet not in text:
                violations.append(f"{relative_path} missing required boundary rewrite snippet {snippet!r}")

    for target_name, contract in CALL_PARENT_CONTRACTS.items():
        observed = _find_call_parents(root, relative_path=contract["path"], target_name=target_name)
        extras = sorted(observed - set(contract["allowlist"]))
        if extras:
            violations.append(
                f"{contract['path']}: call parent set for {target_name} grew without waiver -> {', '.join(extras)}"
            )

    for token, allowlist in TOKEN_PATH_ALLOWLISTS.items():
        observed = _paths_with_token(root, token)
        extras = sorted(observed - set(allowlist))
        if extras:
            violations.append(f"token path set for {token} grew without waiver -> {', '.join(extras)}")

    reason_members = _literal_members(root, relative_path=DIAGNOSE, symbol_name="LLM_POLICY_OVERRIDE_REASON_WHITELIST")
    if reason_members is None:
        violations.append(f"{DIAGNOSE}: could not resolve LLM_POLICY_OVERRIDE_REASON_WHITELIST literal members")
    elif REASON_CODE not in reason_members:
        violations.append(f"{DIAGNOSE}: LLM_POLICY_OVERRIDE_REASON_WHITELIST missing {REASON_CODE}")

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
            print(f"boundary_rewrite_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("boundary_rewrite_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
