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
        "contract_name": "provider_integration_readiness",
        "target": {"client_slug": "demo_salon", "branch_slug": "main", "vertical": "beauty"},
        "repo_contract": {
            "required_file_tokens": [
                {
                    "path": "TECH.md",
                    "tokens": ["docs/PROVIDER_INTEGRATION_READINESS.yaml", "scripts/provider_integration_truth.py"],
                }
            ]
        },
        "required_target_checks": {
            "client_status": "active",
            "branch_active": True,
            "branch_go_live_state": "approved",
            "instance_id_present": True,
            "webhook_secret_present": True,
            "public_base_url_present": True,
            "provider_gateway_inbound_enabled": True,
            "integration_state": "ok",
            "no_recent_inbound_hard_degrade_disabled": True,
            "canonical_webhook_probe_ok": True,
        },
        "warning_observations": {"no_recent_inbound": True},
        "residual_policy": {"do_not_hide_external_canary_gap": True},
    }


def _ready_snapshot(*, integration_state: str = "ok", integration_reason: str | None = None) -> dict:
    return {
        "target": {
            "client_found": True,
            "branch_found": True,
            "client_slug": "demo_salon",
            "client_status": "active",
            "branch_slug": "main",
            "branch_active": True,
            "go_live_state": "approved",
            "instance_id_present": True,
            "webhook_secret_present": True,
            "integration_state": integration_state,
            "integration_reason": integration_reason,
            "latest_inbound_at": "2026-04-17T14:53:28+00:00",
            "latest_inbound_age_minutes": 3000.0,
            "latest_inbound_origin": {"source": "consultant_runtime", "origin_source": "focused_family_proof"},
        },
        "env": {
            "public_base_url": "https://api.truffles.kz",
            "provider_gateway_inbound_enabled": True,
            "provider_gateway_outbound_enabled": False,
            "integration_watchdog_stale_minutes": 120,
            "no_recent_inbound_hard_degrade_enabled": False,
        },
        "route_probes": {
            "canonical_webhook_probe": {
                "ok": True,
                "http_status": 200,
                "payload": {"ok": True, "client_slug": "demo_salon"},
            }
        },
        "repo_contract_errors": [],
    }


def _write_repo(tmp_path: Path, *, config: dict, tech_text: str | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    (repo / "TECH.md").write_text(
        tech_text or "docs/PROVIDER_INTEGRATION_READINESS.yaml\nscripts/provider_integration_truth.py\n",
        encoding="utf-8",
    )
    (repo / "docs" / "PROVIDER_INTEGRATION_READINESS.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    (repo / "scripts" / "provider_integration_truth.py").write_text("# placeholder\n", encoding="utf-8")
    return repo


def test_validate_repo_contract_matches_current_repo() -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")
    config = module.load_config(ROOT / "docs" / "PROVIDER_INTEGRATION_READINESS.yaml")

    assert module.validate_repo_contract(ROOT, config) == []


def test_validate_repo_contract_flags_missing_tokens(tmp_path: Path) -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")
    repo = _write_repo(tmp_path, config=_base_config(), tech_text="missing token\n")
    config = module.load_config(repo / "docs" / "PROVIDER_INTEGRATION_READINESS.yaml")

    violations = module.validate_repo_contract(repo, config)

    assert any("TECH.md missing required provider integration token" in item for item in violations)


def test_evaluate_snapshot_accepts_ready_config_with_stale_inbound_warning() -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")

    payload = module.evaluate_snapshot(_ready_snapshot(), _base_config())

    assert payload["valid"] is True
    assert payload["target_verdict"]["provider_integration_ready"] is True
    assert any("latest inbound is stale" in item for item in payload["warnings"])
    assert any("external provider canary is not proven" in item for item in payload["warnings"])


def test_evaluate_snapshot_blocks_owner_reported_commercial_channel_unavailable() -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")
    config = _base_config()
    config["current_owner_truth"] = {
        "chatflow_whatsapp_status": "commercially_unavailable",
        "reason": "unpaid_or_not_enabled",
        "does_not_block": "internal_console_calendar_booking_proof",
    }

    payload = module.evaluate_snapshot(_ready_snapshot(), config)

    assert payload["valid"] is False
    assert payload["target_verdict"]["config_route_ready"] is True
    assert payload["target_verdict"]["external_channel_ready"] is False
    assert payload["target_verdict"]["internal_booking_blocked_by_provider"] is False
    assert any("CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE" in item for item in payload["errors"])
    assert any("internal_console_calendar_booking_proof" in item for item in payload["warnings"])


def test_evaluate_snapshot_blocks_stale_inbound_hard_degrade_mode() -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")
    snapshot = _ready_snapshot()
    snapshot["env"]["no_recent_inbound_hard_degrade_enabled"] = True

    payload = module.evaluate_snapshot(snapshot, _base_config())

    assert payload["valid"] is False
    assert any("NO_RECENT_INBOUND_DEGRADES" in item for item in payload["errors"])


def test_evaluate_snapshot_blocks_degraded_branch_state() -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")

    payload = module.evaluate_snapshot(
        _ready_snapshot(integration_state="degraded", integration_reason="no_recent_inbound"),
        _base_config(),
    )

    assert payload["valid"] is False
    assert any("target integration_state mismatch" in item for item in payload["errors"])


def test_evaluate_snapshot_blocks_failed_route_probe() -> None:
    module = load_module("provider_integration_truth", SCRIPTS / "provider_integration_truth.py")
    snapshot = _ready_snapshot()
    snapshot["route_probes"]["canonical_webhook_probe"] = {"ok": False, "error": "connection refused"}

    payload = module.evaluate_snapshot(snapshot, _base_config())

    assert payload["valid"] is False
    assert any("canonical webhook probe failed" in item for item in payload["errors"])
