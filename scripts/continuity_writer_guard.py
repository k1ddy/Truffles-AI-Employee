#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


WRITE_MARKERS = (
    "=",
    ".update(",
    "setdefault(",
    ".pop(",
    '\":',
    "':",
)


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


def added_lines(repo_root: Path, file_path: str, base_ref: str, head_ref: str | None) -> list[str]:
    diff_args = ["diff", "--unified=0", "--no-color", base_ref]
    if head_ref:
        diff_args.append(head_ref)
    diff_args.extend(["--", file_path])
    diff = git_output(repo_root, diff_args)
    lines: list[str] = []
    for raw in diff.splitlines():
        if raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
    return lines


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


def evaluate(repo_root: Path, config: dict, base_ref: str, head_ref: str | None) -> list[str]:
    continuity = config.get("continuity_guard") or {}
    allowed = set(continuity.get("allowed_writer_paths") or [])
    guarded_tokens = list(continuity.get("guarded_tokens") or [])
    violations: list[str] = []
    for file_path in changed_python_files(repo_root, base_ref, head_ref):
        if not file_path.startswith("truffles-api/app/"):
            continue
        if file_path in allowed:
            continue
        waiver = _active_waiver_for_file(config, file_path)
        for line in added_lines(repo_root, file_path, base_ref, head_ref):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if _waiver_allows_line(waiver, stripped):
                continue
            if not any(token in line for token in guarded_tokens):
                continue
            if not any(marker in line for marker in WRITE_MARKERS):
                continue
            violations.append(f"{file_path}: continuity token added outside allowed writers -> {stripped}")
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
            print(f"continuity_writer_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("continuity_writer_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
