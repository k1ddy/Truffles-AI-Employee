from datetime import datetime, timezone

from app.schemas.console import (
    ConsoleAdminControlTowerActionCenterResponse,
    ConsoleAdminControlTowerActionCenterSummary,
    ConsoleAdminControlTowerActionItem,
    ConsoleAdminControlTowerMigrationProgramResponse,
    ConsoleAdminControlTowerMigrationProgramSummary,
    ConsoleAdminControlTowerMigrationWave,
    ConsoleAdminControlTowerPromotionAction,
)
from app.services.console_control_tower_utils import (
    build_admin_control_tower_migration_wave_detail,
    build_control_tower_issue_counts,
    build_migration_promotion_actions,
    build_migration_signals,
    build_migration_wave,
    dedupe_non_empty,
)


def test_dedupe_non_empty_keeps_order_and_filters_empty() -> None:
    values = ["a", " ", "b", "a", "", "b", "c"]

    assert dedupe_non_empty(values) == ["a", "b", "c"]


def test_build_control_tower_issue_counts_sorts_by_count_then_code() -> None:
    counts = build_control_tower_issue_counts(
        {
            "beta": 2,
            "alpha": 3,
            "gamma": 2,
        },
        limit=3,
    )

    assert [item.code for item in counts] == ["alpha", "beta", "gamma"]
    assert [item.count for item in counts] == [3, 2, 2]


def test_build_migration_wave_sets_hold_reasons_and_rollbacks() -> None:
    wave = build_migration_wave(
        wave="fleet",
        candidate_clients_total=2,
        candidate_branches_total=5,
        hard_blockers_total=1,
        soft_blockers_total=2,
        blocked_branches_total=3,
        soft_blocker_budget=0,
        top_blockers=[],
    )

    assert wave.gate == "hold"
    assert "hard_blockers_present" in wave.reason
    assert "blocked_branches_remaining" in wave.reason
    assert "incident_p0_open" in wave.rollback_triggers
    assert "blocked_branches_remaining" in wave.rollback_triggers


def test_build_migration_signals_assigns_soft_warn_when_under_threshold() -> None:
    signals = build_migration_signals(
        ready_branches=2,
        blocked_branches=1,
        hard_blockers_total=0,
        soft_blockers_total=2,
    )

    signal_by_code = {signal.code: signal for signal in signals}
    assert signal_by_code["ready_branches"].status == "pass"
    assert signal_by_code["hard_blockers"].status == "pass"
    assert signal_by_code["soft_blockers"].status == "warn"
    assert signal_by_code["blocked_branches"].status == "fail"


def test_build_migration_promotion_actions_and_wave_detail_filters() -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    action_center = ConsoleAdminControlTowerActionCenterResponse(
        generated_at=now_iso,
        stale_after_minutes=60,
        limit=10,
        include_p2=True,
        summary=ConsoleAdminControlTowerActionCenterSummary(
            total_actions=3,
            p0_actions=1,
            p1_actions=1,
            p2_actions=1,
            incident_actions=1,
            provider_ops_actions=1,
            readiness_actions=1,
        ),
        top_reasons=[],
        items=[
            ConsoleAdminControlTowerActionItem(
                id="incident-p0",
                priority="p0",
                source="incident",
                kind="navigate",
                title="Open incident",
                description="Investigate",
            ),
            ConsoleAdminControlTowerActionItem(
                id="drift-p1",
                priority="p1",
                source="provider_ops",
                kind="navigate",
                title="Open integrations",
                description="Fix provider drift",
            ),
            ConsoleAdminControlTowerActionItem(
                id="readiness-p2",
                priority="p2",
                source="readiness",
                kind="navigate",
                title="Open tenants",
                description="Review blockers",
            ),
        ],
    )
    waves = [
        ConsoleAdminControlTowerMigrationWave(
            wave="canary",
            gate="go",
            reason="wave_ready_for_promotion",
            candidate_clients_total=1,
            candidate_branches_total=1,
            blockers_total=0,
        ),
        ConsoleAdminControlTowerMigrationWave(
            wave="cohort",
            gate="hold",
            reason="soft_blocker_budget_exceeded",
            candidate_clients_total=2,
            candidate_branches_total=4,
            blockers_total=2,
        ),
        ConsoleAdminControlTowerMigrationWave(
            wave="fleet",
            gate="hold",
            reason="blocked_branches_remaining",
            candidate_clients_total=2,
            candidate_branches_total=4,
            blockers_total=3,
        ),
    ]
    promotion_actions = build_migration_promotion_actions(
        action_center=action_center,
        waves=waves,
        limit=3,
    )

    assert [item.wave for item in promotion_actions] == ["canary", "cohort", "fleet"]
    assert promotion_actions[0].gate == "go"
    assert promotion_actions[1].gate == "hold"

    migration_program = ConsoleAdminControlTowerMigrationProgramResponse(
        generated_at=now_iso,
        stale_after_minutes=60,
        limit=10,
        include_p2=True,
        summary=ConsoleAdminControlTowerMigrationProgramSummary(
            active_clients_total=2,
            total_branches=6,
            ready_branches=4,
            blocked_branches=2,
            p0_actions=1,
            p1_actions=1,
            p2_actions=1,
            waves_go=1,
            waves_hold=2,
        ),
        waves=waves,
        signals=[],
        promotion_actions=promotion_actions,
    )

    detail = build_admin_control_tower_migration_wave_detail(
        migration_program=migration_program,
        wave="cohort",
        limit=1,
    )

    assert detail.wave == "cohort"
    assert detail.decision == "hold"
    assert detail.promotion_actions_total == 1
    assert len(detail.promotion_actions) == 1
    assert detail.promotion_actions[0].id == "drift-p1"


