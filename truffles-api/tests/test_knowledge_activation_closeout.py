from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / "ops" / "knowledge_activation_closeout.py"
_SPEC = importlib.util.spec_from_file_location("knowledge_activation_closeout", _MODULE_PATH)
_closeout = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_closeout)


def _guard(decision: str = "go", reasons: list[str] | None = None) -> dict:
    return {
        "decision": decision,
        "reasons": reasons or [],
    }


def _tenant(
    *,
    owner_surface_enabled: bool = True,
    active_version_id: str | None = "v1",
    latest_published_id: str | None = "v1",
    latest_draft_id: str | None = None,
    latest_job_state: str | None = None,
) -> dict:
    config = {"consultant_verification_enabled": owner_surface_enabled}
    payload: dict[str, object] = {
        "client_id": "client-1",
        "branch_id": "branch-1",
        "client_config": config,
        "branch_slug": "branch-a",
        "active_version": (
            {
                "id": active_version_id,
                "status": "published",
                "published_at": "2026-03-15T10:00:00+00:00",
                "sync_status": "ready",
                "sync_error": None,
            }
            if active_version_id
            else None
        ),
        "latest_published": (
            {
                "id": latest_published_id,
                "status": "published",
                "published_at": "2026-03-15T10:05:00+00:00",
                "created_at": "2026-03-15T10:05:00+00:00",
                "sync_status": "pending",
                "sync_error": None,
            }
            if latest_published_id
            else None
        ),
        "latest_draft": (
            {
                "id": latest_draft_id,
                "status": "draft",
                "created_at": "2026-03-15T10:06:00+00:00",
            }
            if latest_draft_id
            else None
        ),
        "latest_job": (
            {
                "id": "job-1",
                "version_id": latest_published_id,
                "state": latest_job_state,
                "current_stage": latest_job_state,
                "attempt_count": 1,
                "queued_at": "2026-03-15T10:05:00+00:00",
                "started_at": None,
                "heartbeat_at": None,
                "finished_at": None,
                "error_code": None,
                "last_error": None,
            }
            if latest_job_state
            else None
        ),
        "job_stats_24h": {"queued": 0, "running": 0, "ready": 1, "failed": 0, "stuck": 0},
    }
    return payload


def test_build_closeout_snapshot_go_when_guard_and_tenant_are_ready():
    snapshot = _closeout.build_closeout_snapshot(
        guard_snapshot=_guard(),
        tenant_snapshot=_tenant(latest_job_state="ready"),
        client_slug="demo_salon",
        branch_slug="branch-a",
    )

    assert snapshot["decision"] == "go"
    assert snapshot["reasons"] == []
    assert snapshot["tenant"]["can_verify_now"] is True
    assert snapshot["tenant"]["live_activation_status"] == "ready"
    assert snapshot["invariants"]["tenant_activation_ready"] is True



def test_build_closeout_snapshot_blocks_when_activation_pending_but_preview_stays_available():
    snapshot = _closeout.build_closeout_snapshot(
        guard_snapshot=_guard(),
        tenant_snapshot=_tenant(active_version_id="v1", latest_published_id="v2", latest_job_state="running"),
        client_slug="demo_salon",
        branch_slug="branch-a",
    )

    assert snapshot["decision"] == "no_go"
    assert "tenant:activation_pending" in snapshot["reasons"]
    assert snapshot["tenant"]["can_verify_now"] is True
    assert snapshot["invariants"]["preview_not_blocked_by_activation"] is True
    assert snapshot["invariants"]["live_pointer_separated_from_pending_candidate"] is True



def test_build_closeout_snapshot_blocks_when_release_guard_fails():
    snapshot = _closeout.build_closeout_snapshot(
        guard_snapshot=_guard(decision="no_go", reasons=["service_health_unavailable"]),
        tenant_snapshot=_tenant(latest_job_state="ready"),
        client_slug="demo_salon",
        branch_slug="branch-a",
    )

    assert snapshot["decision"] == "no_go"
    assert "release_guard:service_health_unavailable" in snapshot["reasons"]


def test_build_closeout_snapshot_keeps_rollout_disabled_as_evidence_not_blocker():
    snapshot = _closeout.build_closeout_snapshot(
        guard_snapshot=_guard(),
        tenant_snapshot=_tenant(owner_surface_enabled=False, latest_job_state="ready"),
        client_slug="demo_salon",
        branch_slug="branch-a",
    )

    assert snapshot["decision"] == "go"
    assert snapshot["reasons"] == []
    assert snapshot["tenant"]["owner_surface_enabled"] is False
    assert snapshot["tenant"]["release_preview_ready"] is True
    assert snapshot["tenant"]["can_verify_now"] is False
    assert snapshot["invariants"]["owner_surface_enabled"] is False
