from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_config(repo: Path) -> dict:
    config = {
        "version": "test",
        "hotspots": [
            {
                "path": "truffles-api/app/core/boundary_hotspot.py",
                "active_waiver": None,
                "tracked_function_names": {
                    "name_patterns": [r"^build_.*$", r"^validate$"],
                    "exact_allowlist": ["build_override", "validate"],
                },
                "tracked_literal_members": [
                    {
                        "symbol": "ALLOWED_FIELDS",
                        "exact_allowlist": ["outcome", "pending_question_contract"],
                    }
                ],
            },
            {
                "path": "truffles-api/app/core/runtime_hotspot.py",
                "active_waiver": None,
                "tracked_call_parent_functions": [
                    {
                        "call_names": ["build_degrade_override"],
                        "exact_allowlist": ["plan_turn"],
                    }
                ],
            },
            {
                "path": "truffles-api/app/core/realizer_hotspot.py",
                "active_waiver": None,
                "tracked_override_meta_get_keys": {
                    "exact_allowlist": [],
                },
            },
        ],
        "repo_callsite_contracts": [
            {
                "search_roots": ["truffles-api/app"],
                "call_names": ["build_degrade_override"],
                "exact_allowlist": ["truffles-api/app/core/runtime_hotspot.py"],
            },
            {
                "search_roots": ["truffles-api/app"],
                "call_names": ["_resolve_pending_resume_boundary_activation"],
                "exact_allowlist": [],
            },
        ],
    }
    path = repo / "docs" / "BOUNDARY_DEGRADE_GUARD.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def write_hotspots(
    repo: Path,
    *,
    extra_meta_key: str | None = None,
    extra_callsite: bool = False,
    extra_boundary_restore_callsite: bool = False,
) -> None:
    boundary_path = repo / "truffles-api" / "app" / "core" / "boundary_hotspot.py"
    boundary_path.parent.mkdir(parents=True, exist_ok=True)
    boundary_path.write_text(
        "ALLOWED_FIELDS = ('outcome', 'pending_question_contract')\n\n"
        "def build_override():\n    return None\n\n"
        "def validate():\n    return None\n",
        encoding="utf-8",
    )

    runtime_path = repo / "truffles-api" / "app" / "core" / "runtime_hotspot.py"
    runtime_path.write_text(
        "def plan_turn(boundary):\n    return boundary.build_degrade_override()\n",
        encoding="utf-8",
    )

    meta_lines: list[str] = []
    if extra_meta_key:
        meta_lines.append(f"override.meta.get('{extra_meta_key}')")
    realizer_path = repo / "truffles-api" / "app" / "core" / "realizer_hotspot.py"
    realizer_path.write_text(
        "def realize(override):\n"
        + "".join(f"    {line}\n" for line in meta_lines)
        + "    return None\n",
        encoding="utf-8",
    )

    if extra_callsite:
        extra_path = repo / "truffles-api" / "app" / "core" / "extra_hotspot.py"
        extra_path.write_text(
            "def drift(boundary):\n    return boundary.build_degrade_override()\n",
            encoding="utf-8",
        )
    if extra_boundary_restore_callsite:
        restore_path = repo / "truffles-api" / "app" / "core" / "restore_hotspot.py"
        restore_path.write_text(
            "def drift():\n    return _resolve_pending_resume_boundary_activation()\n",
            encoding="utf-8",
        )


def test_boundary_degrade_guard_allows_exact_snapshot(tmp_path: Path) -> None:
    module = load_module("boundary_degrade_guard", SCRIPTS / "boundary_degrade_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(repo)

    assert module.evaluate(repo, config) == []


def test_boundary_degrade_guard_blocks_new_override_meta_key_and_callsite(tmp_path: Path) -> None:
    module = load_module("boundary_degrade_guard", SCRIPTS / "boundary_degrade_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(
        repo,
        extra_meta_key="expected_reply_type",
        extra_callsite=True,
        extra_boundary_restore_callsite=True,
    )

    violations = module.evaluate(repo, config)
    assert violations
    assert any("override.meta key read set grew without waiver" in item for item in violations)
    assert any("repo callsite set for build_degrade_override grew without waiver" in item for item in violations)
    assert any(
        "repo callsite set for _resolve_pending_resume_boundary_activation grew without waiver" in item
        for item in violations
    )


def test_boundary_degrade_guard_allows_snapshot_shrink_for_stricter_boundary(tmp_path: Path) -> None:
    module = load_module("boundary_degrade_guard", SCRIPTS / "boundary_degrade_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(repo)

    runtime_path = repo / "truffles-api" / "app" / "core" / "runtime_hotspot.py"
    runtime_path.write_text("def plan_turn(boundary):\n    return None\n", encoding="utf-8")

    assert module.evaluate(repo, config) == []


def test_repo_boundary_degrade_snapshot_matches_current_repo() -> None:
    module = load_module("boundary_degrade_guard", SCRIPTS / "boundary_degrade_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "BOUNDARY_DEGRADE_GUARD.yaml").read_text(encoding="utf-8"))

    hotspots = {item["path"]: item for item in config["hotspots"]}
    assert set(hotspots) == {
        "truffles-api/app/core/boundary_validator.py",
        "truffles-api/app/core/consultant_runtime.py",
        "truffles-api/app/core/response_realizer.py",
        "truffles-api/app/core/turn_executor.py",
    }
    assert module.evaluate(ROOT, config) == []
