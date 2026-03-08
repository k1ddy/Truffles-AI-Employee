from datetime import datetime
from typing import Any, Callable, Optional
from uuid import UUID

from app.models import Branch, ClientSettings
from app.schemas.console import (
    ConsoleAdminControlTowerActionCenterResponse,
    ConsoleAdminControlTowerActionCenterSummary,
    ConsoleAdminControlTowerActionItem,
    ConsoleAdminControlTowerDriftBoardResponse,
    ConsoleAdminControlTowerDriftSummary,
    ConsoleAdminControlTowerMigrationProgramResponse,
    ConsoleAdminControlTowerMigrationProgramSummary,
    ConsoleAdminControlTowerMigrationSignal,
    ConsoleAdminControlTowerMigrationWave,
    ConsoleAdminControlTowerReadinessBoardResponse,
    ConsoleAdminControlTowerReadinessItem,
    ConsoleAdminControlTowerReadinessSummary,
    ConsoleBranchIntegrationStatus,
    ConsoleIncidentListResponse,
    ConsoleProviderLifecycleItem,
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


def build_admin_control_tower_drift_board_response(
    *,
    db: Any,
    active_clients: list[Any],
    companies_by_id: dict[UUID, Any],
    stale_after_minutes: int,
    only_problematic_mode: bool,
    limit: int,
    now: datetime,
    normalize_optional_domain_slug_token: Callable[[Any], Optional[str]],
    load_latest_branch_inbound_observations_for_clients: Callable[..., dict[UUID, tuple[Optional[datetime], Optional[str]]]],
    build_provider_binding_lifecycle_map: Callable[..., dict[UUID, Any]],
    build_branch_integration_status: Callable[..., ConsoleBranchIntegrationStatus],
    build_provider_ops_queue: Callable[..., list[Any]],
    resolve_provider_ops_decision: Callable[[ConsoleBranchIntegrationStatus], Optional[Any]],
    build_provider_lifecycle_item: Callable[..., ConsoleProviderLifecycleItem],
) -> ConsoleAdminControlTowerDriftBoardResponse:
    empty_summary = ConsoleAdminControlTowerDriftSummary(
        total_branches=0,
        ok_branches=0,
        warn_branches=0,
        error_branches=0,
        degraded_branches=0,
        queue_p0=0,
        queue_p1=0,
        queue_p2=0,
    )
    if not active_clients:
        return ConsoleAdminControlTowerDriftBoardResponse(
            generated_at=now.isoformat(),
            stale_after_minutes=stale_after_minutes,
            limit=limit,
            only_problematic=only_problematic_mode,
            summary=empty_summary,
            top_issues=[],
            items=[],
            provider_ops_queue=[],
        )

    client_ids = [client.id for client in active_clients]
    client_slug_map = {client.id: client.name for client in active_clients}
    client_company_map = {
        client.id: client.company_id
        for client in active_clients
        if getattr(client, "company_id", None)
    }
    client_domain_map: dict[UUID, str] = {}
    for client in active_clients:
        config = getattr(client, "config", None)
        if not isinstance(config, dict):
            continue
        domain_key = normalize_optional_domain_slug_token(
            config.get("domain_slug") or config.get("domain")
        )
        if domain_key:
            client_domain_map[client.id] = domain_key

    branches = (
        db.query(Branch)
        .filter(
            Branch.client_id.in_(client_ids),
            Branch.is_active.is_(True),
        )
        .order_by(Branch.created_at.desc(), Branch.id.desc())
        .all()
    )
    if not branches:
        return ConsoleAdminControlTowerDriftBoardResponse(
            generated_at=now.isoformat(),
            stale_after_minutes=stale_after_minutes,
            limit=limit,
            only_problematic=only_problematic_mode,
            summary=empty_summary,
            top_issues=[],
            items=[],
            provider_ops_queue=[],
        )

    branch_by_id = {branch.id: branch for branch in branches}
    branch_client_ids = sorted({branch.client_id for branch in branches})
    token_rows = (
        db.query(
            ClientSettings.client_id,
            ClientSettings.telegram_bot_token,
        )
        .filter(ClientSettings.client_id.in_(branch_client_ids))
        .all()
    )
    telegram_token_map: dict[UUID, bool] = {}
    for row_client_id, token in token_rows:
        telegram_token_map[row_client_id] = bool((token or "").strip())

    inbound_observations = load_latest_branch_inbound_observations_for_clients(
        db,
        client_ids=branch_client_ids,
    )
    provider_binding_by_branch = build_provider_binding_lifecycle_map(
        db,
        client_ids=branch_client_ids,
        branches=branches,
        now=now,
    )

    all_status_items: list[ConsoleBranchIntegrationStatus] = []
    for branch in branches:
        client_slug = client_slug_map.get(branch.client_id)
        if not client_slug:
            continue
        observed = inbound_observations.get(branch.id)
        last_inbound_at: Optional[datetime] = observed[0] if observed else None
        last_inbound_instance_id: Optional[str] = observed[1] if observed else None
        all_status_items.append(
            build_branch_integration_status(
                client_id=branch.client_id,
                client_slug=client_slug,
                branch=branch,
                has_telegram_bot_token=telegram_token_map.get(branch.client_id, False),
                stale_after_minutes=stale_after_minutes,
                last_inbound_at=last_inbound_at,
                last_inbound_instance_id=last_inbound_instance_id,
                now=now,
                provider_binding=provider_binding_by_branch.get(branch.id),
            )
        )

    provider_ops_queue = build_provider_ops_queue(
        all_status_items,
        generated_at=now,
    )
    queue_counter = {"p0": 0, "p1": 0, "p2": 0}
    for queue_item in provider_ops_queue:
        queue_counter[queue_item.priority] = queue_counter.get(queue_item.priority, 0) + 1

    summary = ConsoleAdminControlTowerDriftSummary(
        total_branches=len(all_status_items),
        ok_branches=sum(1 for item in all_status_items if item.status == "ok"),
        warn_branches=sum(1 for item in all_status_items if item.status == "warn"),
        error_branches=sum(1 for item in all_status_items if item.status == "error"),
        degraded_branches=sum(1 for item in all_status_items if item.integration_state == "degraded"),
        queue_p0=queue_counter.get("p0", 0),
        queue_p1=queue_counter.get("p1", 0),
        queue_p2=queue_counter.get("p2", 0),
    )

    scoped_items: list[ConsoleBranchIntegrationStatus] = []
    for status_item in all_status_items:
        decision = resolve_provider_ops_decision(status_item)
        if only_problematic_mode and status_item.status == "ok" and not decision:
            continue
        scoped_items.append(status_item)

    severity_rank = {"error": 2, "warn": 1, "ok": 0}
    scoped_items.sort(
        key=lambda item: (
            -severity_rank.get(item.status, 0),
            -int(item.integration_state == "degraded"),
            -len(item.drift_issues),
            item.client_slug,
            item.branch_name,
        )
    )

    issue_counter: dict[str, int] = {}
    for status_item in scoped_items:
        for issue in status_item.drift_issues:
            normalized = (issue or "").strip()
            if not normalized:
                continue
            issue_counter[normalized] = issue_counter.get(normalized, 0) + 1
        if status_item.integration_state == "degraded":
            issue_counter["integration_degraded"] = issue_counter.get("integration_degraded", 0) + 1

    lifecycle_items: list[ConsoleProviderLifecycleItem] = []
    for status_item in scoped_items[:limit]:
        branch = branch_by_id.get(status_item.branch_id)
        if not branch:
            continue
        company_id = client_company_map.get(status_item.client_id)
        company = companies_by_id.get(company_id) if company_id else None
        company_name = getattr(company, "name", None)
        lifecycle_items.append(
            build_provider_lifecycle_item(
                db=db,
                status=status_item,
                branch=branch,
                company_id=company_id,
                company_name=company_name,
                domain_key=client_domain_map.get(status_item.client_id),
                generated_at=now,
                now=now,
            )
        )

    return ConsoleAdminControlTowerDriftBoardResponse(
        generated_at=now.isoformat(),
        stale_after_minutes=stale_after_minutes,
        limit=limit,
        only_problematic=only_problematic_mode,
        summary=summary,
        top_issues=build_control_tower_issue_counts(issue_counter, limit=10),
        items=lifecycle_items,
        provider_ops_queue=provider_ops_queue[:limit],
    )


def build_admin_control_tower_readiness_board_response(
    *,
    db: Any,
    active_clients: list[Any],
    companies_by_id: dict[UUID, Any],
    include_ready_mode: bool,
    limit: int,
    now: datetime,
    build_onboarding_status: Callable[[Any, Any], Any],
    build_onboarding_scorecard: Callable[[Any, Any], Any],
    resolve_readiness_hard_gate_blockers: Callable[..., list[str]],
    normalize_branch_go_live_state: Callable[[Any], str],
    hard_gate_codes: set[str],
) -> ConsoleAdminControlTowerReadinessBoardResponse:
    empty_summary = ConsoleAdminControlTowerReadinessSummary(
        total_branches=0,
        ready_branches=0,
        blocked_branches=0,
        hard_gate_failed_branches=0,
        go_live_draft_branches=0,
        go_live_approved_branches=0,
        go_live_rejected_branches=0,
        degraded_branches=0,
    )
    if not active_clients:
        return ConsoleAdminControlTowerReadinessBoardResponse(
            generated_at=now.isoformat(),
            limit=limit,
            include_ready=include_ready_mode,
            summary=empty_summary,
            top_blockers=[],
            items=[],
        )

    client_ids = [client.id for client in active_clients]
    client_slug_map = {client.id: client.name for client in active_clients}
    client_company_map = {
        client.id: client.company_id
        for client in active_clients
        if getattr(client, "company_id", None)
    }
    branches = (
        db.query(Branch)
        .filter(
            Branch.client_id.in_(client_ids),
            Branch.is_active.is_(True),
        )
        .order_by(Branch.created_at.desc(), Branch.id.desc())
        .all()
    )

    summary = ConsoleAdminControlTowerReadinessSummary(
        total_branches=0,
        ready_branches=0,
        blocked_branches=0,
        hard_gate_failed_branches=0,
        go_live_draft_branches=0,
        go_live_approved_branches=0,
        go_live_rejected_branches=0,
        degraded_branches=0,
    )
    issue_counter: dict[str, int] = {}
    items: list[ConsoleAdminControlTowerReadinessItem] = []
    allowed_steps = {
        "branch_draft",
        "integrations",
        "team",
        "telegram",
        "knowledge",
        "booking",
        "go_no_go",
    }

    for branch in branches:
        client_slug = client_slug_map.get(branch.client_id)
        if not client_slug:
            continue
        summary.total_branches += 1

        onboarding_status = build_onboarding_status(db, branch)
        scorecard = build_onboarding_scorecard(db, branch)
        missing = list(getattr(scorecard, "missing", []) or [])
        readiness_kernel = getattr(scorecard, "readiness_kernel", None)
        readiness_status = (
            getattr(readiness_kernel, "status", None)
            if readiness_kernel is not None
            else None
        )
        if readiness_status not in {"pass", "warn", "fail"}:
            readiness_status = "pass" if getattr(scorecard, "ready", False) else "fail"
        hard_gate_blockers = resolve_readiness_hard_gate_blockers(
            readiness_kernel,
            hard_gate_codes=hard_gate_codes,
        )
        hard_gate_status = "fail" if hard_gate_blockers else "pass"

        if getattr(scorecard, "ready", False):
            summary.ready_branches += 1
        blocked = (not getattr(scorecard, "ready", False)) or bool(hard_gate_blockers)
        if blocked:
            summary.blocked_branches += 1
        if hard_gate_status == "fail":
            summary.hard_gate_failed_branches += 1

        go_live_state = normalize_branch_go_live_state(getattr(branch, "go_live_state", None))
        if go_live_state == "approved":
            summary.go_live_approved_branches += 1
        elif go_live_state == "rejected":
            summary.go_live_rejected_branches += 1
        else:
            summary.go_live_draft_branches += 1

        integration_state = (getattr(branch, "integration_state", None) or "ok").strip().lower()
        if integration_state not in {"ok", "degraded"}:
            integration_state = "ok"
        if integration_state == "degraded":
            summary.degraded_branches += 1

        if not include_ready_mode and not blocked:
            continue

        current_step = (
            getattr(getattr(onboarding_status, "current_step", None), "value", None)
            or "branch_draft"
        )
        if current_step not in allowed_steps:
            current_step = "branch_draft"

        company_id = client_company_map.get(branch.client_id)
        company = companies_by_id.get(company_id) if company_id else None
        company_name = getattr(company, "name", None)
        item = ConsoleAdminControlTowerReadinessItem(
            company_id=company_id,
            company_name=company_name,
            client_id=branch.client_id,
            client_slug=client_slug,
            branch_id=branch.id,
            branch_slug=branch.slug,
            branch_name=branch.name,
            current_step=current_step,
            scorecard_status="pass" if getattr(scorecard, "ready", False) else "fail",
            readiness_status=readiness_status,
            hard_gate_status=hard_gate_status,
            ready=bool(getattr(scorecard, "ready", False)),
            go_live_state=go_live_state,
            integration_state=integration_state,
            missing=missing,
            hard_gate_blockers=hard_gate_blockers,
        )
        items.append(item)

        for code in missing + hard_gate_blockers:
            normalized = (code or "").strip()
            if not normalized:
                continue
            issue_counter[normalized] = issue_counter.get(normalized, 0) + 1

    readiness_rank = {"fail": 2, "warn": 1, "pass": 0}
    items.sort(
        key=lambda item: (
            -int(not item.ready),
            -int(item.hard_gate_status == "fail"),
            -readiness_rank.get(item.readiness_status, 0),
            -len(item.hard_gate_blockers),
            -len(item.missing),
            item.client_slug,
            item.branch_name,
        )
    )
    return ConsoleAdminControlTowerReadinessBoardResponse(
        generated_at=now.isoformat(),
        limit=limit,
        include_ready=include_ready_mode,
        summary=summary,
        top_blockers=build_control_tower_issue_counts(issue_counter, limit=10),
        items=items[:limit],
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
