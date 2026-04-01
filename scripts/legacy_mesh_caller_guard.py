#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Iterable

import yaml


LAW_RULES = {
    "mounted_ingress_surfaces": lambda entry: entry.get("classification") in {
        "mounted_live_composition_root",
        "mounted_live_package_surface",
        "mounted_live_ingress_router",
    },
    "behavior_owning_surfaces": lambda entry: str(entry.get("authority_mode", "")).startswith("behavior_owning_legacy_"),
    "observer_only_surfaces": lambda entry: entry.get("authority_mode") == "adapter_only_observer",
    "shadow_only_surfaces": lambda entry: str(entry.get("authority_mode", "")).startswith("shadow_only_"),
    "unmounted_surfaces": lambda entry: entry.get("classification") in {
        "unmounted_lazy_compatibility_surface",
        "lazy_export_only_unmounted_legacy_helper",
        "unmounted_legacy_helper_surface",
        "unmounted_legacy_wrapper",
    },
    "removed_surfaces": lambda entry: entry.get("authority_mode") == "removed",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid JSON object: {path}")
    return data


def _module_name_from_path(rel_path: str) -> str | None:
    path = Path(rel_path)
    if path.suffix != ".py":
        return None
    if path.parts[:2] == ("truffles-api", "app") or path.parts[:2] == ("truffles-api", "tests"):
        rel = path.relative_to("truffles-api").with_suffix("")
        return ".".join(rel.parts)
    return None


def _resolve_module(current_module: str, module: str | None, level: int) -> str:
    if level == 0:
        return module or ""
    parts = current_module.split(".")[:-1]
    base = parts[: len(parts) - level + 1]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _tracked_member_map(entries: Iterable[dict]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    module_map: dict[str, str] = {}
    member_map: dict[str, dict[str, str]] = {}
    for entry in entries:
        rel_path = entry.get("surface_path")
        if not isinstance(rel_path, str):
            continue
        module_name = _module_name_from_path(rel_path)
        if not module_name:
            continue
        module_map[module_name] = rel_path
        parts = module_name.split(".")
        if len(parts) < 2:
            continue
        parent = ".".join(parts[:-1])
        member_map.setdefault(parent, {})[parts[-1]] = rel_path
    return module_map, member_map


def _scan_importers(root: Path, entries: list[dict]) -> dict[str, dict[str, list[str]]]:
    module_map, member_map = _tracked_member_map(entries)
    results = {
        entry["surface_path"]: {"static_app_importers": [], "test_only_importers": []}
        for entry in entries
        if isinstance(entry.get("surface_path"), str)
    }
    for base in [root / "truffles-api" / "app", root / "truffles-api" / "tests"]:
        bucket = "static_app_importers" if base.name == "app" else "test_only_importers"
        for path in base.rglob("*.py"):
            current_module = ".".join(path.relative_to(root / "truffles-api").with_suffix("").parts)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            matched: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        rel_path = module_map.get(alias.name)
                        if rel_path:
                            matched.add(rel_path)
                elif isinstance(node, ast.ImportFrom):
                    resolved = _resolve_module(current_module, node.module, node.level)
                    rel_path = module_map.get(resolved)
                    if rel_path:
                        matched.add(rel_path)
                    members = member_map.get(resolved, {})
                    for alias in node.names:
                        rel_path = members.get(alias.name)
                        if rel_path:
                            matched.add(rel_path)
            for rel_path in matched:
                if str(path.relative_to(root)) == rel_path:
                    continue
                results.setdefault(rel_path, {"static_app_importers": [], "test_only_importers": []})
                results[rel_path][bucket].append(str(path.relative_to(root)))
    for buckets in results.values():
        for key in ["static_app_importers", "test_only_importers"]:
            buckets[key] = sorted(set(buckets[key]))
    return results


def evaluate(root: Path, registry: dict) -> list[str]:
    entries = registry.get("entries")
    if not isinstance(entries, list):
        return ["dead_surface_registry.entries must be a list"]
    actual = _scan_importers(root, entries)
    violations: list[str] = []
    caller_proof_law = registry.get("caller_proof_law")
    if not isinstance(caller_proof_law, dict):
        violations.append("dead_surface_registry.caller_proof_law must be a mapping")
        caller_proof_law = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        surface_path = entry.get("surface_path")
        if not isinstance(surface_path, str):
            continue
        expected = actual.get(surface_path, {"static_app_importers": [], "test_only_importers": []})
        for key in ["static_app_importers", "test_only_importers"]:
            declared = entry.get(key)
            if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
                violations.append(f"{surface_path}: {key} missing or invalid")
                continue
            declared_sorted = sorted(set(declared))
            if declared_sorted != expected[key]:
                violations.append(
                    f"{surface_path}: {key} drift -> declared={declared_sorted} actual={expected[key]}"
                )
    for law_key, predicate in LAW_RULES.items():
        declared = caller_proof_law.get(law_key)
        if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
            violations.append(f"caller_proof_law.{law_key} missing or invalid")
            continue
        expected = sorted(
            entry["surface_path"]
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("surface_path"), str) and predicate(entry)
        )
        declared_sorted = sorted(set(declared))
        if declared_sorted != expected:
            violations.append(
                f"caller_proof_law.{law_key} drift -> declared={declared_sorted} actual={expected}"
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/SOURCE_OF_TRUTH.yaml")
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    truth = load_yaml(root / args.config)
    registry_rel = truth.get("dead_surface_registry")
    if not isinstance(registry_rel, str):
        raise SystemExit("ERROR: SOURCE_OF_TRUTH.dead_surface_registry must be a path")
    registry = load_json(root / registry_rel)
    violations = evaluate(root, registry)
    if violations:
        for item in violations:
            print(f"legacy_mesh_caller_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("legacy_mesh_caller_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
