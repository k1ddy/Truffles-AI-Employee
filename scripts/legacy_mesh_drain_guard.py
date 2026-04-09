#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_BLOCK_TP = "docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md"
ACTIVE_BLOCK = "Consultant Core Legacy Mesh Drain"
NEXT_MOVE = "complete_shadow_lane_elimination_before_operational_entrypoint_dedupe_or_replay"
HELPER_MODULE = "app.routers.webhook.expected_reply_interrupt_runtime"
HELPER_NAME = "_should_block_expected_reply_by_info"
DECISION_PATH = "truffles-api/app/routers/webhook/decision.py"
LEGACY_PATH = "truffles-api/app/routers/webhook/_legacy.py"
LEGACY_COMPAT_IMPORTERS = ["truffles-api/app/routers/webhook/info_compat.py"]
PACKAGE_INIT_PATH = "truffles-api/app/routers/webhook/__init__.py"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: YAML document must be a mapping: {path}")
    return data


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: JSON document must be an object: {path}")
    return data


def _module_name_from_path(path: Path, *, root: Path) -> str:
    return ".".join(path.relative_to(root / "truffles-api").with_suffix("").parts)


def _resolve_import(current_module: str, module: str | None, level: int) -> str:
    if level == 0:
        return module or ""
    parts = current_module.split(".")[:-1]
    base = parts[: len(parts) - level + 1]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _collect_importers(
    *,
    search_root: Path,
    target_module: str,
    target_member: str | None = None,
) -> list[str]:
    importers: list[str] = []
    repo_root = search_root.parents[1]
    for path in sorted(search_root.rglob("*.py")):
        current_module = _module_name_from_path(path, root=repo_root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        matched = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == target_module:
                        matched = True
                        break
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_import(current_module, node.module, node.level)
                if resolved == target_module:
                    if target_member is None:
                        matched = True
                    elif any(alias.name == target_member for alias in node.names):
                        matched = True
            if matched:
                importers.append(str(path.relative_to(repo_root)))
                break
    return importers


def _dead_surface_entry(registry: dict[str, Any], surface_path: str) -> dict[str, Any]:
    for entry in registry.get("entries", []):
        if isinstance(entry, dict) and entry.get("surface_path") == surface_path:
            return entry
    raise AssertionError(f"missing dead_surface_registry entry for {surface_path}")


def collect_topology_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    package_init = root / PACKAGE_INIT_PATH
    init_text = package_init.read_text(encoding="utf-8")
    init_tree = ast.parse(init_text, filename=str(package_init))

    if "app.routers.webhook.decision" in init_text:
        errors.append("__init__.py must not reference app.routers.webhook.decision after legacy mesh drain")
    if f'"{HELPER_NAME}": (' not in init_text and f"'{HELPER_NAME}': (" not in init_text:
        errors.append("__init__.py must keep _should_block_expected_reply_by_info on the lazy export allowlist")
    if HELPER_MODULE not in init_text:
        errors.append("__init__.py must route the package-root info-interrupt helper through expected_reply_interrupt_runtime")

    for node in ast.walk(init_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.routers.webhook.decision":
                    errors.append("__init__.py still imports app.routers.webhook.decision")
        elif isinstance(node, ast.ImportFrom):
            resolved = node.module or ""
            if resolved == "app.routers.webhook.decision":
                errors.append("__init__.py still imports from app.routers.webhook.decision")

    app_root = root / "truffles-api" / "app"
    decision_importers = _collect_importers(search_root=app_root, target_module="app.routers.webhook.decision")
    decision_member_importers = _collect_importers(
        search_root=app_root,
        target_module="app.routers.webhook",
        target_member="decision",
    )
    all_decision_importers = sorted(set(decision_importers + decision_member_importers))
    expected_decision_importers = [LEGACY_PATH]
    if all_decision_importers != expected_decision_importers:
        errors.append(
            f"app runtime decision importers drifted -> expected {expected_decision_importers!r}, got {all_decision_importers!r}"
        )

    legacy_importers = _collect_importers(search_root=app_root, target_module="app.routers.webhook._legacy")
    legacy_member_importers = _collect_importers(
        search_root=app_root,
        target_module="app.routers.webhook",
        target_member="_legacy",
    )
    all_legacy_importers = sorted(set(legacy_importers + legacy_member_importers))
    if all_legacy_importers != LEGACY_COMPAT_IMPORTERS:
        errors.append(
            f"app runtime must not import _legacy.py anymore -> {all_legacy_importers!r}"
        )

    return errors


def collect_registry_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    dead_surface_registry = _load_json(root / "docs" / "system_forensics" / "dead_surface_registry.json")
    decision_entry = _dead_surface_entry(dead_surface_registry, DECISION_PATH)
    legacy_entry = _dead_surface_entry(dead_surface_registry, LEGACY_PATH)
    expected_decision_importers = [LEGACY_PATH]
    if decision_entry.get("static_app_importers") != expected_decision_importers:
        errors.append(
            "dead_surface_registry decision static_app_importers must shrink to ['truffles-api/app/routers/webhook/_legacy.py']"
        )
    if legacy_entry.get("static_app_importers") != LEGACY_COMPAT_IMPORTERS:
        errors.append(
            "dead_surface_registry _legacy static_app_importers must remain aligned with compat-only imports"
        )
    return errors


def collect_errors(root: Path = ROOT) -> list[str]:
    truth = _load_yaml(root / "docs" / "SOURCE_OF_TRUTH.yaml")
    if truth.get("active_block_tp") != ACTIVE_BLOCK_TP:
        return []

    errors = collect_topology_errors(root)
    errors.extend(collect_registry_errors(root))
    if truth.get("current_non_negotiable_next_move") != NEXT_MOVE:
        errors.append("current_non_negotiable_next_move must advance to shadow lane elimination after Legacy Mesh Drain")
    program = truth.get("program") or {}
    if program.get("current_block") != ACTIVE_BLOCK:
        errors.append("program.current_block must point to Consultant Core Legacy Mesh Drain")
    required_checks = set(program.get("required_checks") or [])
    for check in [
        "python3 scripts/recovery_execution_guard.py",
        "python3 scripts/legacy_mesh_drain_guard.py",
        "python3 scripts/arch_guard.py",
        "pytest -q truffles-api/tests/architecture/test_legacy_mesh_drain_guard.py",
    ]:
        if check not in required_checks:
            errors.append(f"program.required_checks missing legacy-mesh-drain check: {check}")
    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(f"legacy_mesh_drain_guard: FAIL: {error}", file=sys.stderr)
        return 1
    print("legacy_mesh_drain_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
