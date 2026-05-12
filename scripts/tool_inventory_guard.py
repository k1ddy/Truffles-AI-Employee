#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


SCRIPT_SUFFIXES = {".py", ".sh", ".json"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _direct_files(directory: Path, *, suffixes: set[str]) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix in suffixes
    )


def _inventory_text(root: Path) -> str:
    parts: list[str] = []
    for relative_path in ("TECH.md", "STRUCTURE.md"):
        path = root / relative_path
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def collect_inventory_errors(root: Path) -> list[str]:
    inventory = _inventory_text(root)
    errors: list[str] = []

    for path in _direct_files(root / "scripts", suffixes=SCRIPT_SUFFIXES):
        token = f"`scripts/{path.name}`"
        if token not in inventory:
            errors.append(f"missing scripts inventory entry: scripts/{path.name}")

    architecture_tests_dir = root / "truffles-api" / "tests" / "architecture"
    for path in _direct_files(architecture_tests_dir, suffixes={".py"}):
        token = f"`truffles-api/tests/architecture/{path.name}`"
        if token not in inventory:
            errors.append(
                "missing architecture-test inventory entry: "
                f"truffles-api/tests/architecture/{path.name}"
            )

    required_process_terms = (
        "Business capability -> architecture layer -> inventory lookup -> decision record -> implementation -> proof -> impacted docs/inventory update",
        "new development tool, script, architecture test, runtime worker, router, provider adapter, or external dependency",
    )
    for term in required_process_terms:
        if term not in inventory:
            errors.append(f"missing operating-model term: {term}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or _repo_root()).resolve()
    errors = collect_inventory_errors(root)
    if errors:
        for error in errors:
            print(f"tool_inventory_guard: FAIL: {error}")
        return 1
    print("tool_inventory_guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
