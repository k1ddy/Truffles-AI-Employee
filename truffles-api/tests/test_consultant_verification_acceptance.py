from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / "ops" / "consultant_verification_acceptance.py"
_SPEC = importlib.util.spec_from_file_location("consultant_verification_acceptance", _MODULE_PATH)
_acceptance = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_acceptance)


def _raw_snapshot(
    *,
    workspace_enabled: bool = True,
    team_tools_enabled: bool = False,
    can_verify_now: bool = True,
    blocker_codes: list[str] | None = None,
    available_source_modes: list[str] | None = None,
    session_status: str = "go",
    session_failure_code: str | None = None,
    assistant_turn_id: str | None = "turn-1",
    context_error_code: str | None = None,
    probe_error_code: str | None = None,
) -> dict:
    return {
        "probe_error_code": probe_error_code,
        "context": {
            "client_slug": "demo_salon",
            "branch_slug": "main",
            "error_code": context_error_code,
            "error_message": None,
            "agent_id": "agent-1",
            "agent_role": "owner",
        },
        "overview": {
            "workspace_enabled": workspace_enabled,
            "team_tools_enabled": team_tools_enabled,
            "can_verify_now": can_verify_now,
            "branch_selection_required": False,
            "available_source_modes": available_source_modes if available_source_modes is not None else ["live"],
            "blocker_codes": blocker_codes or [],
        },
        "session_probe": {
            "status": session_status,
            "failure_code": session_failure_code,
            "assistant_turn_id": assistant_turn_id,
        },
    }


def test_build_acceptance_snapshot_go_when_preview_is_ready_and_team_tools_are_off():
    snapshot = _acceptance.build_acceptance_snapshot(
        raw_snapshot=_raw_snapshot(team_tools_enabled=False),
        client_slug="demo_salon",
        branch_slug="main",
    )

    assert snapshot["decision"] == "go"
    assert snapshot["reasons"] == []
    assert snapshot["invariants"]["team_tools_enabled"] is False
    assert snapshot["invariants"]["team_tools_not_required_for_preview"] is True
    assert snapshot["invariants"]["session_probe_passed"] is True


def test_build_acceptance_snapshot_blocks_when_preview_source_is_missing():
    snapshot = _acceptance.build_acceptance_snapshot(
        raw_snapshot=_raw_snapshot(
            can_verify_now=False,
            blocker_codes=["preview_source_missing"],
            available_source_modes=[],
            session_status="skipped",
            session_failure_code="overview_blocked",
            assistant_turn_id=None,
        ),
        client_slug="demo_salon",
        branch_slug="main",
    )

    assert snapshot["decision"] == "no_go"
    assert snapshot["reasons"] == ["overview:preview_source_missing"]
    assert snapshot["invariants"]["preview_source_available"] is False


def test_build_acceptance_snapshot_blocks_when_session_probe_fails_after_ready_overview():
    snapshot = _acceptance.build_acceptance_snapshot(
        raw_snapshot=_raw_snapshot(
            session_status="failed",
            session_failure_code="create_failed",
            assistant_turn_id=None,
        ),
        client_slug="demo_salon",
        branch_slug="main",
    )

    assert snapshot["decision"] == "no_go"
    assert "session:create_failed" in snapshot["reasons"]
    assert snapshot["invariants"]["can_verify_now"] is True


def test_build_acceptance_snapshot_surfaces_context_probe_errors():
    snapshot = _acceptance.build_acceptance_snapshot(
        raw_snapshot=_raw_snapshot(
            context_error_code="owner_or_admin_missing",
            probe_error_code="runtime_probe_failed",
            can_verify_now=False,
            available_source_modes=[],
            assistant_turn_id=None,
            session_status="failed",
            session_failure_code="runtime_probe_failed",
        ),
        client_slug="demo_salon",
        branch_slug="main",
    )

    assert snapshot["decision"] == "no_go"
    assert "context:owner_or_admin_missing" in snapshot["reasons"]
    assert "probe:runtime_probe_failed" in snapshot["reasons"]


def test_resolve_effective_source_mode_uses_overview_default_for_auto():
    assert (
        _acceptance.resolve_effective_source_mode(
            {"default_source_mode": "draft"},
            requested_source_mode="auto",
        )
        == "draft"
    )
    assert (
        _acceptance.resolve_effective_source_mode(
            {"default_source_mode": None},
            requested_source_mode="auto",
        )
        is None
    )
    assert (
        _acceptance.resolve_effective_source_mode(
            {"default_source_mode": "draft"},
            requested_source_mode="live",
        )
        == "live"
    )


def test_response_roles_include_consultant_turns():
    assert "consultant" in _acceptance._RESPONSE_ROLES
