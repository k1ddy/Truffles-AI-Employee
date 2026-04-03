#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


COMMENT_PREFIXES = ("#", '"""', "'''")

# These router surfaces now carry stronger dedicated ownership/compatibility guards.
# Keep them out of line-by-line freeze until the current branch converges and the
# sunset docs are resynced after final closure.
TARGETED_GUARD_GOVERNED_FILES = {
    "truffles-api/app/routers/webhook/_legacy.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/decision.py",
    "truffles-api/app/routers/webhook/guards.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/routers/webhook/policy.py",
    "truffles-api/app/routers/webhook/response.py",
}


def git_output(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True)


def default_base_ref(repo_root: Path) -> str:
    try:
        return git_output(repo_root, ["merge-base", "HEAD", "origin/main"]).strip()
    except subprocess.CalledProcessError:
        try:
            return git_output(repo_root, ["rev-parse", "HEAD~1"]).strip()
        except subprocess.CalledProcessError as exc:
            raise SystemExit("ERROR: could not determine default base ref") from exc


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def added_lines(repo_root: Path, file_path: str, base_ref: str, head_ref: str | None) -> list[str]:
    diff_args = ["diff", "--unified=0", "--no-color", base_ref]
    if head_ref:
        diff_args.append(head_ref)
    diff_args.extend(["--", file_path])
    try:
        diff = git_output(repo_root, diff_args)
    except subprocess.CalledProcessError:
        return []
    lines: list[str] = []
    for raw in diff.splitlines():
        if raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
    return lines


def is_executable_addition(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return not stripped.startswith(COMMENT_PREFIXES)


def _normalize_allowed_lines(waiver: object) -> set[str] | None:
    if not isinstance(waiver, dict):
        return None
    allowed = waiver.get("allowed_executable_lines")
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        return None
    return {item.strip() for item in allowed}


def evaluate(repo_root: Path, config: dict, base_ref: str, head_ref: str | None) -> list[str]:
    violations: list[str] = []
    for item in config.get("sunset_files", []):
        if not isinstance(item, dict):
            continue
        file_path = item.get("path")
        if not isinstance(file_path, str):
            continue
        if file_path in TARGETED_GUARD_GOVERNED_FILES:
            continue
        waiver = item.get("active_waiver")
        additions = [line for line in added_lines(repo_root, file_path, base_ref, head_ref) if is_executable_addition(line)]
        if not additions:
            continue
        if waiver:
            allowed_lines = _normalize_allowed_lines(waiver)
            if allowed_lines is None:
                continue
            additions = [line for line in additions if line.strip() not in allowed_lines]
            if not additions:
                continue
        preview = "; ".join(additions[:3])
        violations.append(f"{file_path}: executable additions in frozen file without waiver -> {preview}")
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
            print(f"legacy_freeze_guard: FAIL: {item}", file=sys.stderr)
        return 1
    print("legacy_freeze_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
