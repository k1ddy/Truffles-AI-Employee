from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "knowledge_activation_release_guard.py"
_SPEC = importlib.util.spec_from_file_location("knowledge_activation_release_guard", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_guard)


def test_build_release_guard_snapshot_passes_with_warning_admin_health(monkeypatch):
    monkeypatch.setattr(
        _guard,
        "_json_request",
        lambda url, **kwargs: {
            "http://127.0.0.1:8015/health": (200, {"status": "ok", "knowledge_activation_enabled": True}, None),
            "http://127.0.0.1:8015/knowledge-activation/process": (200, {"claimed": 0, "processed": 0}, None),
            "http://127.0.0.1:8000/admin/health/check": (
                200,
                {
                    "checks": {
                        "knowledge_activation": {
                            "status": "warning",
                            "counts": {"queued": 1, "running": 0, "ready": 1, "failed": 0, "stuck": 0},
                        }
                    }
                },
                None,
            ),
        }[url],
    )
    monkeypatch.setattr(
        _guard,
        "_text_request",
        lambda url, **kwargs: (
            200,
            "\n".join(
                [
                    "health_check_knowledge_activation_status 1",
                    'knowledge_activation_jobs_total{state="queued"} 1',
                    "knowledge_activation_failed_24h_total 0",
                    "knowledge_activation_stale_running_total 0",
                    "knowledge_activation_oldest_queued_age_seconds 10",
                    "knowledge_activation_oldest_running_heartbeat_age_seconds 0",
                ]
            ),
            None,
        ),
    )

    snapshot = _guard.build_release_guard_snapshot(
        service_health_url="http://127.0.0.1:8015/health",
        process_url="http://127.0.0.1:8015/knowledge-activation/process",
        admin_health_url="http://127.0.0.1:8000/admin/health/check",
        metrics_url="http://127.0.0.1:8000/metrics",
        service_token=None,
        timeout_seconds=1.0,
        max_activation_status="warning",
    )

    assert snapshot["decision"] == "go"
    assert snapshot["reasons"] == []
    assert snapshot["admin_health"]["knowledge_activation"]["status"] == "warning"
    assert snapshot["metrics"]["snapshot"]["missing"] == []


def test_build_release_guard_snapshot_fails_on_critical_admin_health(monkeypatch):
    monkeypatch.setattr(
        _guard,
        "_json_request",
        lambda url, **kwargs: {
            "http://127.0.0.1:8015/health": (200, {"status": "ok", "knowledge_activation_enabled": True}, None),
            "http://127.0.0.1:8015/knowledge-activation/process": (200, {"claimed": 0, "processed": 0}, None),
            "http://127.0.0.1:8000/admin/health/check": (
                200,
                {"checks": {"knowledge_activation": {"status": "critical"}}},
                None,
            ),
        }[url],
    )
    monkeypatch.setattr(
        _guard,
        "_text_request",
        lambda url, **kwargs: (200, "health_check_knowledge_activation_status 0\n", None),
    )

    snapshot = _guard.build_release_guard_snapshot(
        service_health_url="http://127.0.0.1:8015/health",
        process_url="http://127.0.0.1:8015/knowledge-activation/process",
        admin_health_url="http://127.0.0.1:8000/admin/health/check",
        metrics_url="http://127.0.0.1:8000/metrics",
        service_token=None,
        timeout_seconds=1.0,
        max_activation_status="warning",
    )

    assert snapshot["decision"] == "no_go"
    assert "activation_health_critical" in snapshot["reasons"]
    assert "activation_metrics_missing" in snapshot["reasons"]


def test_main_writes_output_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        _guard,
        "build_release_guard_snapshot",
        lambda **kwargs: {
            "captured_at": "2026-03-15T13:00:00+00:00",
            "decision": "go",
            "reasons": [],
        },
    )
    output_path = tmp_path / "guard.json"

    exit_code = _guard.main(["--output", str(output_path), "--pretty"])

    assert exit_code == 0
    payload = json.loads(output_path.read_text())
    assert payload["decision"] == "go"
