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
                "path": "truffles-api/app/services/pack_runtime_service.py",
                "active_waiver": None,
                "forbidden_import_modules": ["app.services.pack_runtime_neutral_adapter"],
                "forbidden_function_defs": ["get_pack_adapter"],
                "tracked_function_names": {
                    "name_patterns": [r"^build_runtime_service_.*$", r"^get_pack_.*$"],
                    "exact_allowlist": [
                        "build_runtime_service_duration_reply",
                        "build_runtime_service_not_found_reply",
                        "build_runtime_service_presence_reply_for_name",
                        "build_runtime_service_truth_reply",
                        "get_pack_decision",
                        "get_pack_price_item",
                        "get_pack_price_reply",
                        "get_pack_runtime",
                        "get_pack_service_decision",
                        "get_pack_service_hint",
                    ],
                },
            },
            {
                "path": "truffles-api/app/services/tool_registry_service.py",
                "active_waiver": None,
                "forbidden_import_names": [
                    "_detect_promotion_intent",
                    "_has_duration_signal",
                    "_has_parking_signal",
                    "_has_price_signal",
                    "_match_service",
                    "_normalize_text",
                    "build_info_combined_reply",
                    "build_runtime_service_duration_reply",
                    "build_runtime_service_not_found_reply",
                    "build_runtime_service_presence_reply_for_name",
                    "build_runtime_service_truth_reply",
                    "format_reply_from_truth",
                    "get_pack_adapter",
                    "get_pack_price_item",
                    "get_pack_price_reply",
                    "get_system_lexicon_list",
                    "load_yaml_truth",
                ],
                "forbidden_call_names": [
                    "get_pack_adapter",
                    "_call_pack_adapter",
                    "_find_best_price_item",
                ],
            },
            {
                "path": "truffles-api/app/core/turn_executor.py",
                "active_waiver": None,
                "forbidden_import_names": [
                    "build_master_reply_from_pack",
                    "format_reply_from_truth",
                    "get_pack_decision",
                    "resolve_master_intent",
                ],
            },
        ],
        "repo_callsite_contracts": [
            {
                "search_roots": ["truffles-api/app"],
                "call_names": ["get_pack_adapter", "_call_pack_adapter"],
                "exact_allowlist": [],
            }
        ],
    }
    path = repo / "docs" / "PACK_RUNTIME_SEPARATION_GUARD.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def write_hotspots(repo: Path, *, drift: bool = False) -> None:
    service_path = repo / "truffles-api" / "app" / "services" / "pack_runtime_service.py"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    extra = (
        "\nfrom app.services.pack_runtime_neutral_adapter import format_reply_from_truth\n"
        if drift
        else "\n"
    )
    forbidden_def = "\ndef get_pack_adapter():\n    return None\n" if drift else "\n"
    service_path.write_text(
        "def build_runtime_service_duration_reply():\n    return None\n\n"
        "def build_runtime_service_not_found_reply():\n    return None\n\n"
        "def build_runtime_service_presence_reply_for_name():\n    return None\n\n"
        "def build_runtime_service_truth_reply():\n    return None\n\n"
        "def get_pack_decision():\n    return None\n\n"
        "def get_pack_price_item():\n    return None\n\n"
        "def get_pack_price_reply():\n    return None\n\n"
        "def get_pack_runtime():\n    return None\n\n"
        "def get_pack_service_decision():\n    return None\n\n"
        "def get_pack_service_hint():\n    return None\n"
        + extra
        + forbidden_def,
        encoding="utf-8",
    )

    tool_registry_path = repo / "truffles-api" / "app" / "services" / "tool_registry_service.py"
    tool_registry_path.parent.mkdir(parents=True, exist_ok=True)
    tool_registry_path.write_text(
        (
            "from app.services.pack_runtime_service import get_pack_runtime\n\n"
            "def execute():\n"
            "    return get_pack_runtime('demo_salon')\n"
        )
        if not drift
        else (
            "from app.services.pack_runtime_service import get_pack_adapter\n\n"
            "def execute():\n"
            "    return _call_pack_adapter()\n"
        ),
        encoding="utf-8",
    )

    turn_executor_path = repo / "truffles-api" / "app" / "core" / "turn_executor.py"
    turn_executor_path.parent.mkdir(parents=True, exist_ok=True)
    turn_executor_path.write_text(
        (
            "from app.services.pack_runtime_service import get_pack_runtime\n\n"
            "def execute():\n"
            "    return get_pack_runtime('demo_salon')\n"
        )
        if not drift
        else (
            "from app.services.pack_runtime_service import get_pack_decision\n\n"
            "def execute():\n"
            "    return get_pack_decision('ok')\n"
        ),
        encoding="utf-8",
    )


def test_pack_runtime_separation_guard_allows_exact_snapshot(tmp_path: Path) -> None:
    module = load_module("pack_runtime_separation_guard", SCRIPTS / "pack_runtime_separation_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(repo)

    assert module.evaluate(repo, config) == []


def test_pack_runtime_separation_guard_blocks_adapter_drift(tmp_path: Path) -> None:
    module = load_module("pack_runtime_separation_guard", SCRIPTS / "pack_runtime_separation_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_hotspots(repo, drift=True)

    violations = module.evaluate(repo, config)
    assert violations
    assert any("forbidden import module still present" in item for item in violations)
    assert any("forbidden import name still present" in item for item in violations)
    assert any("forbidden function definition still present" in item for item in violations)
    assert any("repo callsite set for get_pack_adapter, _call_pack_adapter grew without waiver" in item for item in violations)


def test_repo_pack_runtime_separation_snapshot_matches_current_repo() -> None:
    module = load_module("pack_runtime_separation_guard", SCRIPTS / "pack_runtime_separation_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "PACK_RUNTIME_SEPARATION_GUARD.yaml").read_text(encoding="utf-8"))

    hotspots = {item["path"]: item for item in config["hotspots"]}
    assert set(hotspots) == {
        "truffles-api/app/core/turn_executor.py",
        "truffles-api/app/services/pack_runtime_service.py",
        "truffles-api/app/services/tool_registry_service.py",
    }
    assert module.evaluate(ROOT, config) == []
