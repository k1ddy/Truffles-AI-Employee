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
                "path": "truffles-api/app/core/fact_plane.py",
                "active_waiver": None,
                "tracked_function_names": {
                    "name_patterns": [r"^build_from_.*$"],
                    "exact_allowlist": [
                        "build_from_policy_decision",
                        "build_from_request",
                        "build_from_runtime_payload",
                    ],
                },
            }
        ],
        "repo_callsite_contracts": [
            {
                "search_roots": ["truffles-api/app"],
                "call_name": "FactRequestV1.build_from_policy_decision",
                "exact_allowlist": ["truffles-api/app/core/turn_executor.py"],
            },
            {
                "search_roots": ["truffles-api/app"],
                "call_name": "FactPlanV1.build_from_request",
                "exact_allowlist": ["truffles-api/app/core/turn_executor.py"],
            },
            {
                "search_roots": ["truffles-api/app"],
                "call_name": "FactResultV1.build_from_runtime_payload",
                "exact_allowlist": ["truffles-api/app/core/turn_executor.py"],
            },
            {
                "search_roots": ["truffles-api/app"],
                "call_name": "build_fact_contract_meta",
                "exact_allowlist": ["truffles-api/app/core/turn_executor.py"],
            },
        ],
        "keyword_call_contracts": [
            {
                "search_roots": ["truffles-api/app/core"],
                "call_name": "execute_tool_action",
                "required_keywords": ["allowed_fact_refs"],
                "exact_allowlist": ["truffles-api/app/core/turn_executor.py"],
            }
        ],
        "forbidden_text_contracts": [
            {
                "path": "truffles-api/app/core/turn_executor.py",
                "patterns": ["info_sections.append("],
            }
        ],
    }
    path = repo / "docs" / "FACT_PLANE_GUARD.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config


def write_files(repo: Path, *, missing_keyword: bool = False, extra_callsite: bool = False, forbidden_text: bool = False) -> None:
    fact_plane = repo / "truffles-api" / "app" / "core" / "fact_plane.py"
    fact_plane.parent.mkdir(parents=True, exist_ok=True)
    fact_plane.write_text(
        "class FactRequestV1:\n"
        "    @classmethod\n"
        "    def build_from_policy_decision(cls, decision):\n"
        "        return None\n\n"
        "class FactPlanV1:\n"
        "    @classmethod\n"
        "    def build_from_request(cls, request, *, decision):\n"
        "        return None\n\n"
        "class FactResultV1:\n"
        "    @classmethod\n"
        "    def build_from_runtime_payload(cls, plan, **kwargs):\n"
        "        return None\n\n"
        "def build_fact_contract_meta(meta, *, fact_request, fact_plan, fact_result):\n"
        "    return meta\n",
        encoding="utf-8",
    )

    keyword = "allowed_fact_refs=[]" if not missing_keyword else "tool_args={}"
    turn_executor_lines = [
        "from app.core.fact_plane import FactPlanV1, FactRequestV1, FactResultV1, build_fact_contract_meta",
        "from app.services.tool_registry_service import execute_tool_action",
        "",
        "def execute():",
        "    fact_request = FactRequestV1.build_from_policy_decision(None)",
        "    fact_plan = FactPlanV1.build_from_request(fact_request, decision=None)",
        "    fact_result = FactResultV1.build_from_runtime_payload(fact_plan, resolution_source='tool', response_text=None, meta=None)",
        "    build_fact_contract_meta({}, fact_request=fact_request, fact_plan=fact_plan, fact_result=fact_result)",
        f"    execute_tool_action(None, tool_action='catalog.service_query', tool_args={{}}, {keyword})",
        "    return None",
    ]
    if forbidden_text:
        turn_executor_lines.append("info_sections.append('pricing')")
    turn_executor = repo / "truffles-api" / "app" / "core" / "turn_executor.py"
    turn_executor.write_text("\n".join(turn_executor_lines) + "\n", encoding="utf-8")

    if extra_callsite:
        extra = repo / "truffles-api" / "app" / "core" / "extra_fact.py"
        extra.write_text(
            "from app.core.fact_plane import FactRequestV1\n\n"
            "def drift():\n"
            "    return FactRequestV1.build_from_policy_decision(None)\n",
            encoding="utf-8",
        )


def test_fact_plane_guard_allows_exact_snapshot(tmp_path: Path) -> None:
    module = load_module("fact_plane_guard", SCRIPTS / "fact_plane_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_files(repo)

    assert module.evaluate(repo, config) == []


def test_fact_plane_guard_blocks_missing_keyword_extra_callsite_and_forbidden_text(tmp_path: Path) -> None:
    module = load_module("fact_plane_guard", SCRIPTS / "fact_plane_guard.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = write_config(repo)
    write_files(repo, missing_keyword=True, extra_callsite=True, forbidden_text=True)

    violations = module.evaluate(repo, config)
    assert violations
    assert any("repo callsite set for FactRequestV1.build_from_policy_decision grew without waiver" in item for item in violations)
    assert any("execute_tool_action missing required keywords" in item for item in violations)
    assert any("forbidden text present -> info_sections.append(" in item for item in violations)


def test_repo_fact_plane_guard_snapshot_matches_current_repo() -> None:
    module = load_module("fact_plane_guard", SCRIPTS / "fact_plane_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "FACT_PLANE_GUARD.yaml").read_text(encoding="utf-8"))

    assert {item["call_name"] for item in config["repo_callsite_contracts"]} == {
        "FactRequestV1.build_from_policy_decision",
        "FactPlanV1.build_from_request",
        "FactResultV1.build_from_runtime_payload",
        "build_fact_contract_meta",
    }
    assert module.evaluate(ROOT, config) == []
