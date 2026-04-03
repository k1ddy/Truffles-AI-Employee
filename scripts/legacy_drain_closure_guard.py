#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid JSON object: {path}")
    return data


def _bootstrap_python_path(root: Path) -> None:
    truffles_api = root / "truffles-api"
    candidate = str(truffles_api)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


def _top_level_import_modules(tree: ast.AST, *, package_module: str) -> list[str]:
    modules: list[str] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                base = package_module.split(".")
                base = base[: len(base) - node.level]
                if module:
                    base.extend(module.split("."))
                module = ".".join(base)
            modules.append(module)
    return modules


def _module_name_from_path(rel_path: str) -> str | None:
    path = Path(rel_path)
    if path.suffix != ".py":
        return None
    if path.parts[:2] == ("truffles-api", "app"):
        return ".".join(path.relative_to("truffles-api").with_suffix("").parts)
    return None


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
        current_module = _module_name_from_path(str(path.relative_to(repo_root)))
        if current_module is None:
            continue
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


def _iter_import_modules(tree: ast.AST) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                modules.append(module)
    return modules


def _validate_package_root(root: Path, config: dict[str, Any], violations: list[str]) -> None:
    init_path = root / str(config["package_root"])
    source = init_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(init_path))
    package_module = _module_name_from_path(str(config["package_root"]))
    assert package_module is not None
    top_level_modules = set(_top_level_import_modules(tree, package_module=package_module))
    allowed_modules = set(config.get("package_root_allowed_eager_import_modules") or [])
    for module in config.get("package_root_forbidden_eager_import_modules", []):
        if module in top_level_modules:
            violations.append(f"{config['package_root']}: forbidden eager legacy import remains -> {module}")
    unexpected_modules = sorted(top_level_modules - allowed_modules)
    missing_allowed_modules = sorted(allowed_modules - top_level_modules)
    if unexpected_modules:
        violations.append(
            f"{config['package_root']}: package-root adapter seam gained unexpected eager imports -> {unexpected_modules!r}"
        )
    if missing_allowed_modules:
        violations.append(
            f"{config['package_root']}: package-root adapter seam lost required eager imports -> {missing_allowed_modules!r}"
        )
    if "def __getattr__(name: str):" not in source:
        violations.append(f"{config['package_root']}: missing __getattr__ lazy compatibility export gate")
    if "import_module(" not in source:
        violations.append(f"{config['package_root']}: missing import_module-based lazy export path")
    for name in config.get("required_lazy_exports", []):
        if f'"{name}"' not in source and f"'{name}'" not in source:
            violations.append(f"{config['package_root']}: lazy export missing -> {name}")
    if config.get("package_root_final_fate") != "adapter_only":
        violations.append("docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml package_root_final_fate must remain adapter_only")


def _validate_core_import_seam(root: Path, config: dict[str, Any], violations: list[str]) -> None:
    allowed_core_imports = {
        rel: set(modules)
        for rel, modules in (config.get("allowed_core_legacy_imports") or {}).items()
    }
    core_root = root / "truffles-api" / "app" / "core"
    for path in core_root.rglob("*.py"):
        rel = str(path.relative_to(root))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_modules = {
            module
            for module in _iter_import_modules(tree)
            if module == "app.routers.webhook" or module.startswith("app.routers.webhook.")
        }
        allowed = allowed_core_imports.get(rel, set())
        unexpected = sorted(imported_modules - allowed)
        if unexpected:
            violations.append(f"{rel}: unexpected legacy webhook imports -> {unexpected}")
        if rel not in allowed_core_imports and imported_modules:
            violations.append(f"{rel}: legacy webhook import not permitted in core -> {sorted(imported_modules)}")

    runtime_path = root / str(config["consultant_runtime_path"])
    tree = ast.parse(runtime_path.read_text(encoding="utf-8"), filename=str(runtime_path))
    session_imports: list[str] | None = None
    http_aliases: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "app.routers.webhook.session_memory":
            session_imports = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module == "app.routers.webhook":
            for alias in node.names:
                if alias.name == "http":
                    http_aliases.add(alias.asname or alias.name)
    expected_session_imports = list(config.get("expected_session_memory_imports") or [])
    if session_imports != expected_session_imports:
        violations.append(
            f"{config['consultant_runtime_path']}: session_memory import seam drift -> expected {expected_session_imports!r}, got {session_imports!r}"
        )
    if http_aliases != {"http_helpers"}:
        violations.append(
            f"{config['consultant_runtime_path']}: webhook.http import seam drift -> expected alias 'http_helpers', got {sorted(http_aliases)!r}"
        )

    observed_http_calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "http_helpers":
            observed_http_calls.add(func.attr)
    expected_http_calls = set(config.get("expected_http_helper_calls") or [])
    if observed_http_calls != expected_http_calls:
        violations.append(
            f"{config['consultant_runtime_path']}: http helper call seam drift -> expected {sorted(expected_http_calls)!r}, got {sorted(observed_http_calls)!r}"
        )


def _validate_adapter_surfaces(root: Path, config: dict[str, Any], violations: list[str]) -> None:
    forbidden_tokens = [str(token) for token in (config.get("forbidden_touched_tokens_in_adapter_surfaces") or [])]
    for rel in config.get("adapter_only_surfaces", []):
        text = (root / rel).read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{rel}: adapter-only surface still contains touched-envelope token -> {token}")


def _validate_surface_fates(root: Path, config: dict[str, Any], violations: list[str]) -> None:
    allowed_fates = set(config.get("final_fate_set") or [])
    app_root = root / "truffles-api" / "app"
    runtime_roots = ("truffles-api/app/core/", "truffles-api/app/main.py")
    for spec_name, spec in (config.get("surface_fates") or {}).items():
        if not isinstance(spec, dict):
            violations.append(f"surface_fates.{spec_name} must be a mapping")
            continue
        surface_path = str(spec.get("surface_path") or "")
        final_fate = str(spec.get("final_fate") or "")
        if final_fate not in allowed_fates:
            violations.append(f"{surface_path}: final_fate must belong to {sorted(allowed_fates)!r}")
            continue
        module_name = _module_name_from_path(surface_path)
        if module_name is None:
            violations.append(f"{surface_path}: unsupported surface path for import proof")
            continue
        member_name = Path(surface_path).stem
        direct_importers = _collect_importers(search_root=app_root, target_module=module_name)
        via_package_importers = _collect_importers(
            search_root=app_root,
            target_module="app.routers.webhook",
            target_member=member_name,
        )
        app_importers = sorted(set(direct_importers + via_package_importers))
        expected_app_importers = list(spec.get("expected_app_importers") or [])
        if app_importers != expected_app_importers:
            violations.append(
                f"{surface_path}: app importers drift -> expected {expected_app_importers!r}, got {app_importers!r}"
            )
        runtime_importers = [
            rel for rel in app_importers if rel == runtime_roots[1] or rel.startswith(runtime_roots[0])
        ]
        expected_runtime_importers = list(spec.get("expected_runtime_importers") or [])
        if runtime_importers != expected_runtime_importers:
            violations.append(
                f"{surface_path}: runtime importers drift -> expected {expected_runtime_importers!r}, got {runtime_importers!r}"
            )
        if final_fate == "unreachable" and runtime_importers:
            violations.append(f"{surface_path}: unreachable surface regained runtime importers -> {runtime_importers!r}")
        if final_fate == "adapter_only" and not expected_runtime_importers:
            violations.append(f"{surface_path}: adapter_only fate must name its runtime importer seam explicitly")


def _validate_registry(config: dict[str, Any], registry: dict[str, Any], violations: list[str]) -> None:
    if registry.get("active_block") != config.get("active_block"):
        violations.append(
            f"dead_surface_registry active_block drift -> expected {config.get('active_block')!r}, got {registry.get('active_block')!r}"
        )
    if registry.get("status") != config.get("expected_registry_status"):
        violations.append(
            f"dead_surface_registry status drift -> expected {config.get('expected_registry_status')!r}, got {registry.get('status')!r}"
        )
    caller_proof_law = registry.get("caller_proof_law") if isinstance(registry.get("caller_proof_law"), dict) else {}
    expected_map = {
        "behavior_owning_surfaces": "adapter_only_surfaces",
        "adapter_only_for_touched_envelope": "adapter_only_surfaces",
        "startup_load_drained_from_package_root": "startup_load_drained_from_package_root",
        "unreachable_for_touched_envelope": "unreachable_surfaces_for_touched_envelope",
    }
    for key, config_key in expected_map.items():
        expected = list(config.get(config_key) or [])
        declared = caller_proof_law.get(key)
        if declared != expected:
            violations.append(f"dead_surface_registry caller_proof_law.{key} drift -> expected {expected!r}, got {declared!r}")

    entries = {
        item.get("surface_path"): item
        for item in registry.get("entries", [])
        if isinstance(item, dict) and isinstance(item.get("surface_path"), str)
    }
    for rel in config.get("adapter_only_surfaces", []):
        entry = entries.get(rel) or {}
        if entry.get("family_envelope_status") != "adapter_only_for_touched_envelope":
            violations.append(f"{rel}: registry family_envelope_status must be adapter_only_for_touched_envelope")
    for rel in config.get("unreachable_surfaces_for_touched_envelope", []):
        entry = entries.get(rel) or {}
        if entry.get("family_envelope_status") != "unreachable_for_touched_envelope":
            violations.append(f"{rel}: registry family_envelope_status must be unreachable_for_touched_envelope")
    for rel in config.get("startup_load_drained_from_package_root", []):
        entry = entries.get(rel) or {}
        if entry.get("startup_load_mode") != "lazy_export_only":
            violations.append(f"{rel}: registry startup_load_mode must be lazy_export_only")
        if entry.get("live_runtime_callers") != []:
            violations.append(f"{rel}: registry live_runtime_callers must be [] after startup drain")


def _validate_lazy_exports_runtime(root: Path, config: dict[str, Any], violations: list[str]) -> None:
    _bootstrap_python_path(root)
    webhook = importlib.import_module("app.routers.webhook")
    for name in config.get("required_lazy_exports", []):
        try:
            value = getattr(webhook, name)
        except Exception as exc:  # pragma: no cover - guard failure path
            violations.append(f"app.routers.webhook lazy export failed for {name}: {exc}")
            continue
        if value is None:
            violations.append(f"app.routers.webhook lazy export resolved to None -> {name}")


def evaluate(root: Path, config: dict[str, Any], registry: dict[str, Any] | None = None) -> list[str]:
    violations: list[str] = []
    resolved_registry = registry or load_json(root / str(config["registry_path"]))
    _validate_package_root(root, config, violations)
    _validate_core_import_seam(root, config, violations)
    _validate_adapter_surfaces(root, config, violations)
    _validate_surface_fates(root, config, violations)
    _validate_registry(config, resolved_registry, violations)
    _validate_lazy_exports_runtime(root, config, violations)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--config", default="docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml")
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    config = load_yaml(root / args.config)
    registry = load_json(root / str(config["registry_path"]))
    violations = evaluate(root, config, registry)
    if violations:
        for item in violations:
            print(f"legacy_drain_closure_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("legacy_drain_closure_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
