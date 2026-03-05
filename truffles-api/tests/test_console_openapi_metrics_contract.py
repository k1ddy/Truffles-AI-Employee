from pathlib import Path

import yaml


def _load_console_contract() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "contracts" / "console_api" / "openapi.v1.yaml"
    return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}


def test_metrics_daily_contract_exposes_realtime_reliability_fields() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    metrics_schema = schemas.get("ConsoleMetricsDailyResponse") or {}
    properties = metrics_schema.get("properties") or {}

    assert "queue_lag_seconds" in properties
    assert "queue_lag_status" in properties
    assert "stale_view_rate" in properties
    assert "stale_view_status" in properties
    assert "case_action_apply_latency_seconds" in properties
    assert "case_action_apply_latency_status" in properties
