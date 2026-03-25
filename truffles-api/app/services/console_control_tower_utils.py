from typing import Literal, Optional

from app.schemas.console import (
    ConsoleAdminControlTowerActionCenterResponse,
    ConsoleAdminControlTowerIssueCount,
    ConsoleAdminControlTowerMigrationProgramResponse,
    ConsoleAdminControlTowerMigrationSignal,
    ConsoleAdminControlTowerMigrationWave,
    ConsoleAdminControlTowerMigrationWaveDetailResponse,
    ConsoleAdminControlTowerPromotionAction,
)


def dedupe_non_empty(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = (value or "").strip()
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return deduped


def build_control_tower_issue_counts(
    counter: dict[str, int],
    *,
    limit: int = 10,
) -> list[ConsoleAdminControlTowerIssueCount]:
    if not counter:
        return []
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [
        ConsoleAdminControlTowerIssueCount(code=code, count=count)
        for code, count in ranked[: max(limit, 0)]
    ]


def control_tower_incident_priority(severity: str) -> Literal["p0", "p1", "p2"]:
    if severity == "critical":
        return "p0"
    if severity == "warn":
        return "p1"
    return "p2"


def control_tower_provider_action_label(action: str) -> str:
    labels = {
        "integration_reconcile": "Запустить integration reconcile",
        "provider_start_rebind": "Начать provider rebind",
        "provider_complete_rebind": "Завершить provider rebind",
        "provider_renewal_confirmed": "Подтвердить продление провайдера",
        "provider_webhook_updated": "Обновить webhook/instance",
        "provider_send_reminder": "Отправить напоминание провайдеру",
    }
    return labels.get(action, "Запустить provider action")


def merge_control_tower_issue_counts(
    *groups: list[ConsoleAdminControlTowerIssueCount],
) -> dict[str, int]:
    merged: dict[str, int] = {}
    for group in groups:
        for item in group:
            code = (item.code or "").strip()
            if not code:
                continue
            merged[code] = merged.get(code, 0) + int(item.count or 0)
    return merged


def build_migration_wave(
    *,
    wave: Literal["canary", "cohort", "fleet"],
    candidate_clients_total: int,
    candidate_branches_total: int,
    hard_blockers_total: int,
    soft_blockers_total: int,
    blocked_branches_total: int,
    soft_blocker_budget: int,
    top_blockers: list[ConsoleAdminControlTowerIssueCount],
) -> ConsoleAdminControlTowerMigrationWave:
    gate: Literal["go", "hold"] = "go"
    reasons: list[str] = []
    rollback_triggers: list[str] = []

    if candidate_branches_total <= 0:
        gate = "hold"
        reasons.append("no_ready_candidates")
        rollback_triggers.append("no_ready_candidates")

    if hard_blockers_total > 0:
        gate = "hold"
        reasons.append("hard_blockers_present")
        rollback_triggers.extend(
            [
                "incident_p0_open",
                "readiness_hard_gate_failed",
                "provider_ops_p0_queue",
            ]
        )

    if soft_blockers_total > soft_blocker_budget:
        gate = "hold"
        reasons.append("soft_blocker_budget_exceeded")
        rollback_triggers.append("soft_blocker_burn_rate")

    if wave == "fleet" and blocked_branches_total > 0:
        gate = "hold"
        reasons.append("blocked_branches_remaining")
        rollback_triggers.append("blocked_branches_remaining")

    if gate == "go":
        reason_text = "wave_ready_for_promotion"
    else:
        reason_text = "+".join(dedupe_non_empty(reasons)) or "wave_hold"

    blockers_total = hard_blockers_total + max(0, soft_blockers_total - soft_blocker_budget)
    return ConsoleAdminControlTowerMigrationWave(
        wave=wave,
        gate=gate,
        reason=reason_text,
        candidate_clients_total=max(candidate_clients_total, 0),
        candidate_branches_total=max(candidate_branches_total, 0),
        blockers_total=max(blockers_total, 0),
        rollback_triggers=dedupe_non_empty(rollback_triggers),
        top_blockers=top_blockers,
    )


def resolve_migration_wave_for_priority(
    priority: Literal["p0", "p1", "p2"],
) -> Literal["canary", "cohort", "fleet"]:
    if priority == "p0":
        return "canary"
    if priority == "p1":
        return "cohort"
    return "fleet"


def build_migration_signals(
    *,
    ready_branches: int,
    blocked_branches: int,
    hard_blockers_total: int,
    soft_blockers_total: int,
) -> list[ConsoleAdminControlTowerMigrationSignal]:
    if soft_blockers_total <= 0:
        soft_status: Literal["pass", "warn", "fail"] = "pass"
    elif soft_blockers_total <= 3:
        soft_status = "warn"
    else:
        soft_status = "fail"
    return [
        ConsoleAdminControlTowerMigrationSignal(
            code="ready_branches",
            status="pass" if ready_branches > 0 else "fail",
            value=max(ready_branches, 0),
            threshold=1,
            note="at least one ready branch is required for promotion",
        ),
        ConsoleAdminControlTowerMigrationSignal(
            code="hard_blockers",
            status="pass" if hard_blockers_total == 0 else "fail",
            value=max(hard_blockers_total, 0),
            threshold=0,
            note="p0 incidents + hard-gate failures + p0 action queue",
        ),
        ConsoleAdminControlTowerMigrationSignal(
            code="soft_blockers",
            status=soft_status,
            value=max(soft_blockers_total, 0),
            threshold=3,
            note="p1 drift queue + p1 action queue",
        ),
        ConsoleAdminControlTowerMigrationSignal(
            code="blocked_branches",
            status="pass" if blocked_branches == 0 else "fail",
            value=max(blocked_branches, 0),
            threshold=0,
            note="fleet promotion requires zero blocked branches",
        ),
    ]


def build_migration_promotion_actions(
    *,
    action_center: ConsoleAdminControlTowerActionCenterResponse,
    waves: list[ConsoleAdminControlTowerMigrationWave],
    limit: int,
) -> list[ConsoleAdminControlTowerPromotionAction]:
    wave_by_id = {wave.wave: wave for wave in waves}
    collected: list[ConsoleAdminControlTowerPromotionAction] = []
    for item in action_center.items:
        wave_id = resolve_migration_wave_for_priority(item.priority)
        wave_gate = wave_by_id.get(wave_id).gate if wave_id in wave_by_id else "hold"
        collected.append(
            ConsoleAdminControlTowerPromotionAction(
                id=item.id,
                wave=wave_id,
                gate=wave_gate,
                priority=item.priority,
                source=item.source,
                kind=item.kind,
                title=item.title,
                description=item.description,
                reasons=list(item.reasons or []),
                href=item.href,
                job_type=item.job_type,
                mode=item.mode,
                params=item.params if isinstance(item.params, dict) else None,
                evidence_links=list(item.evidence_links or []),
            )
        )
        if len(collected) >= limit:
            break
    return collected


def build_admin_control_tower_migration_wave_detail(
    *,
    migration_program: ConsoleAdminControlTowerMigrationProgramResponse,
    wave: Literal["canary", "cohort", "fleet"],
    limit: int,
) -> ConsoleAdminControlTowerMigrationWaveDetailResponse:
    selected_wave: Optional[ConsoleAdminControlTowerMigrationWave] = None
    for candidate in migration_program.waves:
        if candidate.wave == wave:
            selected_wave = candidate
            break
    if selected_wave is None:
        selected_wave = ConsoleAdminControlTowerMigrationWave(
            wave=wave,
            gate="hold",
            reason="wave_not_available",
            candidate_clients_total=0,
            candidate_branches_total=0,
            blockers_total=0,
            rollback_triggers=["wave_not_available"],
            top_blockers=[],
        )

    selected_actions = [
        item
        for item in migration_program.promotion_actions
        if item.wave == wave
    ][:limit]
    decision: Literal["promote", "hold"] = "promote" if selected_wave.gate == "go" else "hold"
    reason = selected_wave.reason if selected_wave.reason else ("wave_ready_for_promotion" if decision == "promote" else "wave_hold")
    return ConsoleAdminControlTowerMigrationWaveDetailResponse(
        generated_at=migration_program.generated_at,
        stale_after_minutes=migration_program.stale_after_minutes,
        limit=limit,
        include_p2=migration_program.include_p2,
        wave=wave,
        decision=decision,
        reason=reason,
        summary=migration_program.summary,
        wave_state=selected_wave,
        signals=list(migration_program.signals or []),
        promotion_actions_total=sum(
            1 for item in migration_program.promotion_actions if item.wave == wave
        ),
        promotion_actions=selected_actions,
    )
