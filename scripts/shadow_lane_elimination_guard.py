#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "docs/SHADOW_LANE_ELIMINATION_GUARD.yaml"


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


def _load_config(root: Path = ROOT, rel: str = DEFAULT_CONFIG) -> dict[str, Any]:
    return _load_yaml(root / rel)


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
    repo_root = search_root.parent if search_root.name == "truffles-api" else search_root.parents[1]
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


def evaluate_removed_shadow_lanes(root: Path = ROOT, config: dict[str, Any] | None = None) -> list[str]:
    config = config or _load_config(root)
    errors: list[str] = []
    app_root = root / "truffles-api" / "app"
    repo_tree_root = root / "truffles-api"
    active_contract = config.get("removed_runtime_shadows") or {}
    decision_contract = config.get("router_shadow_contract") or {}
    legacy_path = str(decision_contract.get("legacy_path") or "truffles-api/app/routers/webhook/_legacy.py")

    for module_name, contract in active_contract.items():
        runtime_path = root / contract["runtime_path"]
        support_path = root / contract["support_path"]
        if runtime_path.exists():
            errors.append(f"{contract['runtime_path']} must be removed from runtime code")
        if not support_path.exists():
            errors.append(f"{contract['support_path']} must exist as the test-only shadow support replacement")

        expected_support_importers = sorted(contract.get("support_test_importers") or [])
        support_module = _module_name_from_path(support_path, root=root)
        support_importers = sorted(
            set(
                _collect_importers(
                    search_root=root / "truffles-api" / "tests",
                    target_module=support_module,
                )
                + _collect_importers(
                    search_root=root / "truffles-api" / "tests",
                    target_module=support_module.rsplit(".", 1)[0],
                    target_member=support_module.rsplit(".", 1)[-1],
                )
            )
        )
        if sorted(support_importers) != expected_support_importers:
            errors.append(
                f"{contract['support_path']} test importers drifted -> {sorted(support_importers)!r} != {expected_support_importers!r}"
            )

        direct_importers = _collect_importers(search_root=repo_tree_root, target_module=module_name)
        member_importers = _collect_importers(
            search_root=repo_tree_root,
            target_module="app" if module_name == "app.webhook" else "app.services",
            target_member=module_name.rsplit(".", 1)[-1],
        )
        all_importers = sorted(set(direct_importers + member_importers))
        if all_importers:
            errors.append(f"removed runtime shadow module {module_name} still has repo importers -> {all_importers!r}")

    decision_importers = sorted(
        set(
            _collect_importers(search_root=app_root, target_module="app.routers.webhook.decision")
            + _collect_importers(
                search_root=app_root,
                target_module="app.routers.webhook",
                target_member="decision",
            )
        )
    )
    expected_decision_importers = sorted(decision_contract.get("decision_importers") or [legacy_path])
    if decision_importers != expected_decision_importers:
        errors.append(
            f"decision.py must remain shadow-only through _legacy.py while shadow lanes are eliminated -> {decision_importers!r}"
        )

    legacy_importers = sorted(
        set(
            _collect_importers(search_root=app_root, target_module="app.routers.webhook._legacy")
            + _collect_importers(
                search_root=app_root,
                target_module="app.routers.webhook",
                target_member="_legacy",
            )
        )
    )
    expected_legacy_importers = sorted(decision_contract.get("legacy_bus_importers") or [])
    if legacy_importers != expected_legacy_importers:
        errors.append(f"_legacy.py must remain outside live app runtime -> {legacy_importers!r}")

    return errors


def collect_registry_errors(root: Path = ROOT, config: dict[str, Any] | None = None) -> list[str]:
    config = config or _load_config(root)
    errors: list[str] = []
    dead_surface_registry = _load_json(root / "docs" / "system_forensics" / "dead_surface_registry.json")
    legacy_caller_surface = _load_json(root / "docs" / "system_forensics" / "legacy_caller_surface.json")
    authority_registry = _load_json(root / "docs" / "system_forensics" / "authority_registry.json")
    registry_contract = config.get("registry_contract") or {}
    expected_status = registry_contract.get("required_status") or "machine_readable_shadow_lane_elimination_base"
    next_phase = registry_contract.get("next_phase_required") or "operational_entrypoint_dedupe"

    if dead_surface_registry.get("status") != expected_status:
        errors.append(f"dead_surface_registry status must be {expected_status}")
    if legacy_caller_surface.get("status") != expected_status:
        errors.append(f"legacy_caller_surface status must be {expected_status}")
    if authority_registry.get("status") != expected_status:
        errors.append(f"authority_registry status must be {expected_status}")

    for module_name, contract in (config.get("removed_runtime_shadows") or {}).items():
        runtime_path = contract["runtime_path"]
        support_path = contract["support_path"]
        removed_entry = _dead_surface_entry(dead_surface_registry, runtime_path)
        support_entry = _dead_surface_entry(dead_surface_registry, support_path)

        if removed_entry.get("path_exists_expected") is not False:
            errors.append(f"{runtime_path} must be marked removed in dead_surface_registry")
        if removed_entry.get("authority_mode") != "removed":
            errors.append(f"{runtime_path} must have removed authority_mode in dead_surface_registry")
        if removed_entry.get("static_app_importers") != [] or removed_entry.get("test_only_importers") != []:
            errors.append(f"{runtime_path} must have no remaining importers in dead_surface_registry")

        if support_entry.get("classification") != "shadow_only_test_residue":
            errors.append(f"{support_path} must be classified as shadow_only_test_residue")
        if support_entry.get("authority_mode") != "shadow_only_test_support":
            errors.append(f"{support_path} must be marked shadow_only_test_support")
        if support_entry.get("static_app_importers") != []:
            errors.append(f"{support_path} must have no app importers")

    legacy_entries = {
        item.get("module_path"): item
        for item in legacy_caller_surface.get("entries", [])
        if isinstance(item, dict)
    }
    for removed_runtime_path in [item["runtime_path"] for item in (config.get("removed_runtime_shadows") or {}).values()]:
        if removed_runtime_path in legacy_entries:
            errors.append(f"{removed_runtime_path} must be removed from legacy_caller_surface entries once the runtime file is deleted")

    freeze_policy = legacy_caller_surface.get("freeze_policy") or {}
    frozen_modules = set(freeze_policy.get("frozen_adapter_only_modules") or [])
    shadow_candidates = set(freeze_policy.get("shadow_or_wrapper_candidates") or [])
    for removed_runtime_path in [item["runtime_path"] for item in (config.get("removed_runtime_shadows") or {}).values()]:
        if removed_runtime_path in frozen_modules:
            errors.append(f"{removed_runtime_path} must be removed from legacy_caller_surface.freeze_policy.frozen_adapter_only_modules")
        if removed_runtime_path in shadow_candidates:
            errors.append(f"{removed_runtime_path} must be removed from legacy_caller_surface.freeze_policy.shadow_or_wrapper_candidates")

    entries = {item["mechanism_id"]: item for item in authority_registry.get("entries", [])}
    for key in [
        "semantic_turn_meaning",
        "post_owner_semantic_reconstruction",
        "continuity_state",
        "boundary_and_degrade",
        "fact_scope",
        "legacy_behavior_authority",
    ]:
        entry = entries.get(key)
        if not isinstance(entry, dict):
            errors.append(f"authority_registry missing mechanism {key}")
            continue
        if entry.get("next_phase_required") != next_phase:
            errors.append(f"{key} must advance next_phase_required to {next_phase}")

    return errors


def collect_errors(root: Path = ROOT, config: dict[str, Any] | None = None) -> list[str]:
    config = config or _load_config(root)
    truth = _load_yaml(root / "docs" / "SOURCE_OF_TRUTH.yaml")
    active_block_tp = config.get("active_block_tp")
    active_block = config.get("active_block")
    next_move = config.get("next_move")

    if truth.get("active_block_tp") != active_block_tp:
        return []

    errors = evaluate_removed_shadow_lanes(root, config)
    errors.extend(collect_registry_errors(root, config))

    if truth.get("current_non_negotiable_next_move") != next_move:
        errors.append("current_non_negotiable_next_move must advance to operational entrypoint dedupe after Shadow Lane Elimination")
    program = truth.get("program") or {}
    if program.get("current_block") != active_block:
        errors.append("program.current_block must point to Consultant Core Shadow Lane Elimination")
    required_checks = set(program.get("required_checks") or [])
    for check in config.get("required_checks") or []:
        if check not in required_checks:
            errors.append(f"program.required_checks missing shadow-lane-elimination check: {check}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = _load_config(ROOT, args.config)
    errors = collect_errors(ROOT, config)
    if errors:
        for error in errors:
            print(f"shadow_lane_elimination_guard: FAIL: {error}", file=sys.stderr)
        return 1
    print("shadow_lane_elimination_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
