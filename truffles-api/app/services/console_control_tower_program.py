from datetime import datetime
from uuid import UUID

from app.schemas.console import (
    ConsoleAdminControlTowerActionCenterResponse,
    ConsoleAdminControlTowerActionCenterSummary,
    ConsoleAdminControlTowerActionItem,
    ConsoleAdminControlTowerDriftBoardResponse,
    ConsoleAdminControlTowerMigrationProgramResponse,
    ConsoleAdminControlTowerMigrationProgramSummary,
    ConsoleAdminControlTowerMigrationSignal,
    ConsoleAdminControlTowerMigrationWave,
    ConsoleAdminControlTowerReadinessBoardResponse,
    ConsoleIncidentListResponse,
)
from app.services.console_control_tower_utils import (
    build_control_tower_issue_counts,
    build_migration_promotion_actions,
    build_migration_signals,
    build_migration_wave,
    control_tower_incident_priority,
    control_tower_provider_action_label,
    dedupe_non_empty,
    merge_control_tower_issue_counts,
)


def build_admin_control_tower_action_center_response(
    *,
    incidents: ConsoleIncidentListResponse,
    drift_board: ConsoleAdminControlTowerDriftBoardResponse,
    readiness_board: ConsoleAdminControlTowerReadinessBoardResponse,
    client_ids: list[UUID],
    stale_after_minutes: int,
    include_p2_mode: bool,
    limit: int,
    now: datetime,
) -> ConsoleAdminControlTowerActionCenterResponse:
    reason_counter: dict[str, int] = {}
    collected: list[ConsoleAdminControlTowerActionItem] = []

    for incident in incidents.items:
        priority = control_tower_incident_priority(incident.severity)
        reasons = dedupe_non_empty([incident.reason_code])
        for reason in reasons:
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
        for action in incident.actions:
            collected.append(
                ConsoleAdminControlTowerActionItem(
                    id=f"incident:{incident.id}:{action.id}",
                    priority=priority,
                    source="incident",
                    kind="ops_job" if action.job_type else "navigate",
                    title=action.title,
                    description=action.description,
                    reasons=reasons,
                    href=action.href,
                    incident_id=incident.id,
                    client_id=incident.client_id,
                    client_slug=incident.client_slug,
                    branch_id=incident.branch_id,
                    job_type=action.job_type,
                    mode=action.mode,
                    params=action.params if isinstance(action.params, dict) else None,
                    requires_confirmation=bool(action.requires_confirmation),
                    evidence_links=dedupe_non_empty(
                        ["/admin/incidents", action.href or "", "/admin/control-tower/overview"]
                    ),
                )
            )

    for queue_item in drift_board.provider_ops_queue:
        reasons = dedupe_non_empty(list(queue_item.reasons or []))
        for reason in reasons:
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
        collected.append(
            ConsoleAdminControlTowerActionItem(
                id=f"provider:{queue_item.branch_id}:{queue_item.recommended_action}",
                priority=queue_item.priority,
                source="provider_ops",
                kind="provider_action",
                title=control_tower_provider_action_label(queue_item.recommended_action),
                description=(
                    f"{queue_item.client_slug}/{queue_item.branch_name}: "
                    f"priority={queue_item.priority}, reasons={', '.join(reasons) or 'n/a'}"
                ),
                reasons=reasons,
                href="/integrations",
                client_id=queue_item.client_id,
                client_slug=queue_item.client_slug,
                branch_id=queue_item.branch_id,
                branch_slug=queue_item.branch_slug,
                branch_name=queue_item.branch_name,
                provider_action=queue_item.recommended_action,
                params={
                    "branch_id": str(queue_item.branch_id),
                    "action": queue_item.recommended_action,
                    "mode": "execute",
                    "requires_confirmation": bool(queue_item.requires_confirmation),
                },
                requires_confirmation=bool(queue_item.requires_confirmation),
                evidence_links=[
                    "/admin/control-tower/drift-board",
                    f"/admin/integrations/{queue_item.branch_id}/reconcile",
                ],
            )
        )

    for readiness_item in readiness_board.items:
        reasons = dedupe_non_empty(
            list(readiness_item.hard_gate_blockers or []) + list(readiness_item.missing or [])
        )
        if not reasons:
            reasons = ["readiness_blocked"]
        for reason in reasons:
            reason_counter[reason] = reason_counter.get(reason, 0) + 1
        collected.append(
            ConsoleAdminControlTowerActionItem(
                id=f"readiness:{readiness_item.branch_id}",
                priority="p0" if readiness_item.hard_gate_status == "fail" else "p1",
                source="readiness",
                kind="navigate",
                title=f"Закрыть go-live blockers: {readiness_item.client_slug}/{readiness_item.branch_name}",
                description=(
                    "Проверьте hard-gate и недостающие onboarding шаги перед продвижением филиала."
                ),
                reasons=reasons,
                href="/tenants",
                client_id=readiness_item.client_id,
                client_slug=readiness_item.client_slug,
                branch_id=readiness_item.branch_id,
                branch_slug=readiness_item.branch_slug,
                branch_name=readiness_item.branch_name,
                evidence_links=["/admin/control-tower/readiness-board", "/tenants"],
            )
        )

    scoped_items: list[ConsoleAdminControlTowerActionItem] = []
    for item in collected:
        if item.client_id and item.client_id not in client_ids:
            continue
        if not include_p2_mode and item.priority == "p2":
            continue
        scoped_items.append(item)

    priority_rank = {"p0": 0, "p1": 1, "p2": 2}
    source_rank = {"incident": 0, "provider_ops": 1, "readiness": 2}
    scoped_items.sort(
        key=lambda item: (
            priority_rank.get(item.priority, 99),
            source_rank.get(item.source, 99),
            item.client_slug or "",
            item.branch_name or "",
            item.title,
        )
    )

    summary = ConsoleAdminControlTowerActionCenterSummary(
        total_actions=len(scoped_items),
        p0_actions=sum(1 for item in scoped_items if item.priority == "p0"),
        p1_actions=sum(1 for item in scoped_items if item.priority == "p1"),
        p2_actions=sum(1 for item in scoped_items if item.priority == "p2"),
        incident_actions=sum(1 for item in scoped_items if item.source == "incident"),
        provider_ops_actions=sum(1 for item in scoped_items if item.source == "provider_ops"),
        readiness_actions=sum(1 for item in scoped_items if item.source == "readiness"),
    )

    return ConsoleAdminControlTowerActionCenterResponse(
        generated_at=now.isoformat(),
        stale_after_minutes=stale_after_minutes,
        limit=limit,
        include_p2=include_p2_mode,
        summary=summary,
        top_reasons=build_control_tower_issue_counts(reason_counter, limit=10),
        items=scoped_items[:limit],
    )


def build_admin_control_tower_migration_program_response(
    *,
    active_clients_total: int,
    readiness_board: ConsoleAdminControlTowerReadinessBoardResponse,
    drift_board: ConsoleAdminControlTowerDriftBoardResponse,
    action_center: ConsoleAdminControlTowerActionCenterResponse,
    stale_after_minutes: int,
    include_p2_mode: bool,
    limit: int,
    now: datetime,
) -> ConsoleAdminControlTowerMigrationProgramResponse:
    if active_clients_total <= 0:
        empty_waves = [
            ConsoleAdminControlTowerMigrationWave(
                wave=wave,
                gate="hold",
                reason="no_active_clients",
                candidate_clients_total=0,
                candidate_branches_total=0,
                blockers_total=0,
                rollback_triggers=["no_active_clients"],
                top_blockers=[],
            )
            for wave in ("canary", "cohort", "fleet")
        ]
        return ConsoleAdminControlTowerMigrationProgramResponse(
            generated_at=now.isoformat(),
            stale_after_minutes=stale_after_minutes,
            limit=limit,
            include_p2=include_p2_mode,
            summary=ConsoleAdminControlTowerMigrationProgramSummary(
                active_clients_total=0,
                total_branches=0,
                ready_branches=0,
                blocked_branches=0,
                p0_actions=0,
                p1_actions=0,
                p2_actions=0,
                waves_go=0,
                waves_hold=3,
            ),
            waves=empty_waves,
            signals=[
                ConsoleAdminControlTowerMigrationSignal(
                    code="active_clients",
                    status="fail",
                    value=0,
                    threshold=1,
                    note="no active clients in scope",
                )
            ],
            promotion_actions=[],
        )

    merged_top_blockers = build_control_tower_issue_counts(
        merge_control_tower_issue_counts(
            readiness_board.top_blockers,
            drift_board.top_issues,
            action_center.top_reasons,
        ),
        limit=5,
    )
    total_branches = readiness_board.summary.total_branches
    ready_branches = readiness_board.summary.ready_branches
    blocked_branches = readiness_board.summary.blocked_branches
    p0_actions = action_center.summary.p0_actions
    p1_actions = action_center.summary.p1_actions
    p2_actions = action_center.summary.p2_actions
    hard_blockers_total = (
        readiness_board.summary.hard_gate_failed_branches
        + drift_board.summary.queue_p0
        + p0_actions
    )
    soft_blockers_total = drift_board.summary.queue_p1 + p1_actions

    canary_wave = build_migration_wave(
        wave="canary",
        candidate_clients_total=1 if ready_branches > 0 else 0,
        candidate_branches_total=min(ready_branches, 3),
        hard_blockers_total=hard_blockers_total,
        soft_blockers_total=soft_blockers_total,
        blocked_branches_total=blocked_branches,
        soft_blocker_budget=2,
        top_blockers=merged_top_blockers,
    )
    cohort_wave = build_migration_wave(
        wave="cohort",
        candidate_clients_total=min(active_clients_total, 5) if ready_branches > 0 else 0,
        candidate_branches_total=min(ready_branches, 25),
        hard_blockers_total=hard_blockers_total,
        soft_blockers_total=soft_blockers_total,
        blocked_branches_total=blocked_branches,
        soft_blocker_budget=5,
        top_blockers=merged_top_blockers,
    )
    fleet_wave = build_migration_wave(
        wave="fleet",
        candidate_clients_total=active_clients_total if ready_branches > 0 else 0,
        candidate_branches_total=ready_branches,
        hard_blockers_total=hard_blockers_total,
        soft_blockers_total=soft_blockers_total + (p2_actions if include_p2_mode else 0),
        blocked_branches_total=blocked_branches,
        soft_blocker_budget=0,
        top_blockers=merged_top_blockers,
    )
    waves = [canary_wave, cohort_wave, fleet_wave]
    signals = build_migration_signals(
        ready_branches=ready_branches,
        blocked_branches=blocked_branches,
        hard_blockers_total=hard_blockers_total,
        soft_blockers_total=soft_blockers_total,
    )
    promotion_actions = build_migration_promotion_actions(
        action_center=action_center,
        waves=waves,
        limit=limit,
    )

    return ConsoleAdminControlTowerMigrationProgramResponse(
        generated_at=now.isoformat(),
        stale_after_minutes=stale_after_minutes,
        limit=limit,
        include_p2=include_p2_mode,
        summary=ConsoleAdminControlTowerMigrationProgramSummary(
            active_clients_total=active_clients_total,
            total_branches=total_branches,
            ready_branches=ready_branches,
            blocked_branches=blocked_branches,
            p0_actions=p0_actions,
            p1_actions=p1_actions,
            p2_actions=p2_actions,
            waves_go=sum(1 for wave in waves if wave.gate == "go"),
            waves_hold=sum(1 for wave in waves if wave.gate == "hold"),
        ),
        waves=waves,
        signals=signals,
        promotion_actions=promotion_actions,
    )
