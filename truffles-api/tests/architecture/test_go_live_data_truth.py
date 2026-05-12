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


def _base_config() -> dict:
    return {
        "version": "test",
        "contract_name": "go_live_data_readiness",
        "target": {"client_slug": "demo_salon", "branch_slug": "main", "vertical": "beauty"},
        "repo_contract": {
            "required_file_tokens": [
                {
                    "path": "TECH.md",
                    "tokens": ["docs/GO_LIVE_DATA_READINESS.yaml", "scripts/go_live_data_truth.py"],
                }
            ]
        },
        "required_target_checks": {
            "branch_active": True,
            "branch_go_live_state": "approved",
            "active_knowledge_status": "published",
            "minimum_data_contract_version": "minimum_data_contract.v2",
            "minimum_data_contract_ready": True,
            "knowledge_safe_mode": False,
            "operational_service_integrity": True,
        },
        "report_only_checks": {
            "integration_state": True,
            "knowledge_sync_status": True,
            "fleet_active_branch_residuals": True,
            "published_candidate_residuals": True,
        },
        "residual_policy": {"do_not_hide_fleet_missing_branches": True},
    }


def _ready_version(sync_status: str = "pending") -> dict:
    return {
        "id": "033ba3b8-a19a-4887-8587-aa761243f29c",
        "status": "published",
        "sync_status": sync_status,
        "minimum_data_contract": {
            "version": "minimum_data_contract.v2",
            "ready": True,
            "missing_fields": [],
        },
    }


_DEFAULT_ACTIVE_VERSION = object()


def _target(active_version: dict | None | object = _DEFAULT_ACTIVE_VERSION) -> dict:
    return {
        "client_found": True,
        "branch_found": True,
        "client_slug": "demo_salon",
        "branch_slug": "main",
        "branch_active": True,
        "go_live_state": "approved",
        "integration_state": "degraded",
        "integration_reason": "no_recent_inbound",
        "knowledge_safe_mode": False,
        "active_version": _ready_version() if active_version is _DEFAULT_ACTIVE_VERSION else active_version,
        "operational_data_integrity": {
            "services_on_branch": 3,
            "active_services_on_branch": 3,
            "specialists_on_branch": 2,
            "active_specialists_on_branch": 2,
            "specialist_service_links": 3,
            "cross_client_specialist_service_links": 0,
            "cross_branch_specialist_service_links": 0,
            "service_rows_with_foreign_branch": 0,
        },
    }


def _snapshot(target: dict | None = None, fleet_branches: list[dict] | None = None) -> dict:
    return {
        "target": target if target is not None else _target(),
        "fleet": {"active_branches": fleet_branches if fleet_branches is not None else [_target()]},
        "repo_contract_errors": [],
    }


def _write_repo(tmp_path: Path, *, config: dict, tech_text: str | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    (repo / "TECH.md").write_text(
        tech_text or "docs/GO_LIVE_DATA_READINESS.yaml\nscripts/go_live_data_truth.py\n",
        encoding="utf-8",
    )
    (repo / "docs" / "GO_LIVE_DATA_READINESS.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    (repo / "scripts" / "go_live_data_truth.py").write_text("# placeholder\n", encoding="utf-8")
    return repo


def test_validate_repo_contract_matches_current_repo() -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")
    config = module.load_config(ROOT / "docs" / "GO_LIVE_DATA_READINESS.yaml")

    assert module.validate_repo_contract(ROOT, config) == []


def test_validate_repo_contract_flags_missing_tokens(tmp_path: Path) -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")
    repo = _write_repo(tmp_path, config=_base_config(), tech_text="missing token\n")
    config = module.load_config(repo / "docs" / "GO_LIVE_DATA_READINESS.yaml")

    violations = module.validate_repo_contract(repo, config)

    assert any("TECH.md missing required go-live data token" in item for item in violations)


def test_evaluate_snapshot_accepts_ready_target_while_reporting_non_data_residuals() -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")

    payload = module.evaluate_snapshot(_snapshot(), _base_config())

    assert payload["valid"] is True
    assert payload["target_verdict"]["data_ready"] is True
    assert any("integration_state is report-only" in item for item in payload["warnings"])
    assert any("sync_status is report-only" in item for item in payload["warnings"])


def test_evaluate_snapshot_flags_missing_active_knowledge_as_target_failure() -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")
    target = _target(active_version=None)

    payload = module.evaluate_snapshot(_snapshot(target=target), _base_config())

    assert payload["valid"] is False
    assert any("target active knowledge version missing" in item for item in payload["errors"])


def test_evaluate_snapshot_flags_operational_service_integrity_failure() -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")
    target = _target()
    target["operational_data_integrity"] = {
        "services_on_branch": 0,
        "active_services_on_branch": 0,
        "specialists_on_branch": 2,
        "active_specialists_on_branch": 2,
        "specialist_service_links": 3,
        "cross_client_specialist_service_links": 1,
        "cross_branch_specialist_service_links": 2,
        "service_rows_with_foreign_branch": 4,
    }

    payload = module.evaluate_snapshot(_snapshot(target=target), _base_config())

    assert payload["valid"] is False
    assert payload["target_verdict"]["operational_service_integrity_ready"] is False
    assert "target branch service catalog empty" in payload["errors"]
    assert "target specialist-service client mismatch -> count=1" in payload["errors"]
    assert "target specialist-service branch mismatch -> count=2" in payload["errors"]
    assert "target service rows point to foreign client branch -> count=4" in payload["errors"]


def test_evaluate_snapshot_keeps_fleet_residuals_visible_without_blocking_target() -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")
    fleet = [
        _target(),
        {
            "client_slug": "clinic_pack",
            "branch_slug": "main",
            "branch_id": "c6fbe329-ac55-4b34-983f-0bf1cd1a398e",
            "knowledge_tag": "clinic_pack",
            "active_version": None,
            "latest_published_candidate": {
                "id": "5cde6cee-2193-4c08-95f7-9605d50b620f",
                "status": "published",
                "minimum_data_contract": {
                    "version": "minimum_data_contract.v2",
                    "ready": True,
                    "missing_fields": [],
                },
            },
        },
        {
            "client_slug": "generic",
            "branch_slug": "main",
            "branch_id": "e6862577-449e-4c54-9deb-7d9aee782076",
            "knowledge_tag": "generic",
            "active_version": None,
            "latest_published_candidate": {
                "id": "dab6c495-a8f4-4e27-885c-f0c0117700f3",
                "status": "published",
                "minimum_data_contract": {
                    "version": "minimum_data_contract.v2",
                    "ready": False,
                    "missing_fields": ["client_pack.guest_policy"],
                },
            },
        },
    ]

    payload = module.evaluate_snapshot(_snapshot(fleet_branches=fleet), _base_config())

    assert payload["valid"] is True
    assert len(payload["fleet_residuals"]) == 2
    assert len(payload["published_candidate_residuals"]) == 1
    assert any("fleet active branch data residuals remain" in item for item in payload["warnings"])


def test_evaluate_snapshot_fails_if_fleet_report_is_missing() -> None:
    module = load_module("go_live_data_truth", SCRIPTS / "go_live_data_truth.py")
    snapshot = {"target": _target(), "repo_contract_errors": []}

    payload = module.evaluate_snapshot(snapshot, _base_config())

    assert payload["valid"] is False
    assert any("fleet active branch residuals were not reported" in item for item in payload["errors"])
