from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.console import (
    ConsoleAdminControlTowerActionCenterResponse,
    ConsoleAdminControlTowerActionCenterSummary,
    ConsoleAdminControlTowerDriftBoardResponse,
    ConsoleAdminControlTowerDriftSummary,
    ConsoleAdminControlTowerIssueCount,
    ConsoleAdminControlTowerReadinessBoardResponse,
    ConsoleAdminControlTowerReadinessItem,
    ConsoleAdminControlTowerReadinessSummary,
    ConsoleIncidentAction,
    ConsoleIncidentItem,
    ConsoleIncidentListResponse,
    ConsoleIncidentSummary,
    ConsoleProviderOpsQueueItem,
)
from app.services.console_control_tower_program import (
    build_admin_control_tower_action_center_response,
    build_admin_control_tower_migration_program_response,
)


def _build_incidents(client_id) -> ConsoleIncidentListResponse:
    return ConsoleIncidentListResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        scope="fleet",
        summary=ConsoleIncidentSummary(total=1, critical=1, warn=0, info=0),
        items=[
            ConsoleIncidentItem(
                id="inc-1",
                scope="fleet",
                severity="critical",
                title="Provider outage",
                summary="Provider unavailable",
                reason_code="provider_unavailable",
                reason_label="Provider unavailable",
                source="outbox",
                detected_at=datetime.now(timezone.utc).isoformat(),
                client_id=client_id,
                client_slug="demo_salon",
                branch_id=uuid4(),
                actions=[
                    ConsoleIncidentAction(
                        id="action-1",
                        title="Run outbox process",
                        description="Retry failed messages",
                        href="/ops",
                        job_type="outbox_process",
                        mode="dry_run",
                    )
                ],
            )
        ],
    )


def _build_readiness_board(client_id, branch_id) -> ConsoleAdminControlTowerReadinessBoardResponse:
    return ConsoleAdminControlTowerReadinessBoardResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        limit=20,
        include_ready=False,
        summary=ConsoleAdminControlTowerReadinessSummary(
            total_branches=1,
            ready_branches=0,
            blocked_branches=1,
            hard_gate_failed_branches=1,
            go_live_draft_branches=1,
            go_live_approved_branches=0,
            go_live_rejected_branches=0,
            degraded_branches=0,
        ),
        top_blockers=[ConsoleAdminControlTowerIssueCount(code="readiness_blocked", count=1)],
        items=[
            ConsoleAdminControlTowerReadinessItem(
                client_id=client_id,
                client_slug="demo_salon",
                branch_id=branch_id,
                branch_slug="almaty-center",
                branch_name="Almaty Center",
                current_step="go_no_go",
                scorecard_status="fail",
                readiness_status="fail",
                hard_gate_status="fail",
                ready=False,
                go_live_state="pending",
                integration_state="ok",
                missing=["reference_pack"],
                hard_gate_blockers=["payment_confirmed"],
            )
        ],
    )


def _build_drift_board(client_id, branch_id) -> ConsoleAdminControlTowerDriftBoardResponse:
    return ConsoleAdminControlTowerDriftBoardResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        stale_after_minutes=60,
        limit=20,
        only_problematic=True,
        summary=ConsoleAdminControlTowerDriftSummary(
            total_branches=1,
            ok_branches=0,
            warn_branches=1,
            error_branches=0,
            degraded_branches=1,
            queue_p0=0,
            queue_p1=1,
            queue_p2=0,
        ),
        top_issues=[ConsoleAdminControlTowerIssueCount(code="provider_binding_rebind_required", count=1)],
        items=[],
        provider_ops_queue=[
            ConsoleProviderOpsQueueItem(
                client_id=client_id,
                client_slug="demo_salon",
                branch_id=branch_id,
                branch_slug="almaty-center",
                branch_name="Almaty Center",
                priority="p1",
                recommended_action="provider_start_rebind",
                reasons=["provider_binding_rebind_required"],
                requires_confirmation=False,
            )
        ],
    )


def test_build_admin_control_tower_action_center_response_composes_and_sorts() -> None:
    client_id = uuid4()
    branch_id = uuid4()
    now = datetime.now(timezone.utc)

    response = build_admin_control_tower_action_center_response(
        incidents=_build_incidents(client_id),
        drift_board=_build_drift_board(client_id, branch_id),
        readiness_board=_build_readiness_board(client_id, branch_id),
        client_ids=[client_id],
        stale_after_minutes=60,
        include_p2_mode=False,
        limit=20,
        now=now,
    )

    assert response.summary.total_actions == 3
    assert response.summary.p0_actions == 2
    assert response.summary.p1_actions == 1
    assert response.summary.p2_actions == 0
    assert response.items[0].source == "incident"
    assert response.items[1].source == "readiness"
    assert response.items[2].source == "provider_ops"
    assert any(item.code == "provider_unavailable" for item in response.top_reasons)


def test_build_admin_control_tower_migration_program_response_uses_board_signals() -> None:
    client_id = uuid4()
    branch_id = uuid4()
    now = datetime.now(timezone.utc)

    action_center = build_admin_control_tower_action_center_response(
        incidents=_build_incidents(client_id),
        drift_board=_build_drift_board(client_id, branch_id),
        readiness_board=_build_readiness_board(client_id, branch_id),
        client_ids=[client_id],
        stale_after_minutes=60,
        include_p2_mode=False,
        limit=20,
        now=now,
    )

    program = build_admin_control_tower_migration_program_response(
        active_clients_total=2,
        readiness_board=_build_readiness_board(client_id, branch_id),
        drift_board=_build_drift_board(client_id, branch_id),
        action_center=action_center,
        stale_after_minutes=60,
        include_p2_mode=False,
        limit=20,
        now=now,
    )

    assert program.summary.active_clients_total == 2
    assert program.summary.p0_actions == action_center.summary.p0_actions
    assert len(program.waves) == 3
    assert any(wave.gate == "hold" for wave in program.waves)
    assert any(signal.code == "hard_blockers" and signal.status == "fail" for signal in program.signals)
    assert len(program.promotion_actions) > 0


def test_build_admin_control_tower_migration_program_response_handles_empty_clients() -> None:
    now = datetime.now(timezone.utc)
    client_id = uuid4()
    branch_id = uuid4()

    program = build_admin_control_tower_migration_program_response(
        active_clients_total=0,
        readiness_board=_build_readiness_board(client_id, branch_id),
        drift_board=_build_drift_board(client_id, branch_id),
        action_center=ConsoleAdminControlTowerActionCenterResponse(
            generated_at=now.isoformat(),
            stale_after_minutes=60,
            limit=20,
            include_p2=False,
            summary=ConsoleAdminControlTowerActionCenterSummary(
                total_actions=0,
                p0_actions=0,
                p1_actions=0,
                p2_actions=0,
                incident_actions=0,
                provider_ops_actions=0,
                readiness_actions=0,
            ),
            top_reasons=[],
            items=[],
        ),
        stale_after_minutes=60,
        include_p2_mode=False,
        limit=20,
        now=now,
    )

    assert program.summary.active_clients_total == 0
    assert len(program.waves) == 3
    assert all(wave.gate == "hold" for wave in program.waves)
