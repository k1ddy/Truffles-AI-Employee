#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"ERROR: cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_top_level_consistency(root: Path, truth: dict, legacy: dict) -> list[str]:
    errors: list[str] = []
    for key in ["active_dec", "active_master_tp", "active_block_tp", "active_canon", "legacy_sunset"]:
        rel = truth.get(key)
        if not isinstance(rel, str) or not rel.strip():
            errors.append(f"SOURCE_OF_TRUTH missing path key: {key}")
            continue
        if not (root / rel).exists():
            errors.append(f"SOURCE_OF_TRUTH references missing path for {key}: {rel}")
    forbidden = truth.get("forbidden_semantic_files") or []
    sunset_paths = [item.get("path") for item in legacy.get("sunset_files", []) if isinstance(item, dict)]
    if sorted(forbidden) != sorted(sunset_paths):
        errors.append("forbidden_semantic_files must match LEGACY_SUNSET sunset_files")
    proof_only = sorted(truth.get("proof_only", {}).get("files") or [])
    if proof_only != sorted(legacy.get("proof_only_files") or []):
        errors.append("proof_only files mismatch between SOURCE_OF_TRUTH and LEGACY_SUNSET")
    program = truth.get("program") or {}
    allowed = set(program.get("allowed_touch") or [])
    forbidden_touch = set(program.get("forbidden_touch") or [])
    overlap = sorted(allowed.intersection(forbidden_touch))
    if overlap:
        errors.append(f"allowed_touch overlaps forbidden_touch: {', '.join(overlap)}")
    if not set(forbidden).issubset(forbidden_touch):
        errors.append("program.forbidden_touch must include all forbidden_semantic_files")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--head-ref", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or repo_root())
    truth = load_yaml(root / "docs" / "SOURCE_OF_TRUTH.yaml")
    legacy = load_yaml(root / "docs" / "LEGACY_SUNSET.yaml")
    errors = validate_top_level_consistency(root, truth, legacy)
    if errors:
        for error in errors:
            print(f"arch_guard: FAIL: {error}", file=sys.stderr)
        return 1

    build_packet = root / "scripts" / "build_agent_packet.py"
    subprocess.run([sys.executable, str(build_packet), "--check"], cwd=root, check=True)

    for script_name in [
        "legacy_freeze_guard.py",
        "continuity_writer_guard.py",
        "proof_path_guard.py",
        "semantic_bridge_growth_guard.py",
    ]:
        script = root / "scripts" / script_name
        cmd = [sys.executable, str(script)]
        if args.base_ref:
            cmd.extend(["--base-ref", args.base_ref])
        if args.head_ref:
            cmd.extend(["--head-ref", args.head_ref])
        subprocess.run(cmd, cwd=root, check=True)

    print("arch_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
