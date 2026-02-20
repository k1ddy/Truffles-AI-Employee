from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services.reference_branch_selection import (
    ReferenceBranchSignal,
    has_recent_inbound,
    select_reference_branch_ids,
)


def _signal(
    *,
    client_id,
    is_active=True,
    has_instance_id=False,
    has_phone=False,
    has_recent=False,
    go_live_allowed=False,
    onboarding_go_no_go=False,
    integration_ok=True,
    slug="branch",
):
    return ReferenceBranchSignal(
        branch_id=uuid4(),
        client_id=client_id,
        is_active=is_active,
        slug=slug,
        created_at=datetime.now(timezone.utc),
        has_instance_id=has_instance_id,
        has_phone=has_phone,
        has_recent_inbound=has_recent,
        go_live_allowed=go_live_allowed,
        onboarding_go_no_go=onboarding_go_no_go,
        integration_ok=integration_ok,
    )


def test_has_recent_inbound_window():
    now = datetime.now(timezone.utc)
    assert has_recent_inbound(now - timedelta(days=5), now=now, window_days=30) is True
    assert has_recent_inbound(now - timedelta(days=40), now=now, window_days=30) is False


def test_select_reference_branch_ids_uses_all_active_live_signal_branches():
    client_id = uuid4()
    live_by_go_live = _signal(client_id=client_id, go_live_allowed=True, slug="main")
    live_by_traffic = _signal(client_id=client_id, has_recent=True, slug="live")
    test_branch = _signal(client_id=client_id, is_active=True, slug="test")
    inactive_branch = _signal(client_id=client_id, is_active=False, go_live_allowed=True, slug="old")

    decisions = select_reference_branch_ids(
        [live_by_go_live, live_by_traffic, test_branch, inactive_branch]
    )

    decision = decisions[client_id]
    assert decision.reason == "active_live_signals"
    assert set(decision.branch_ids) == {live_by_go_live.branch_id, live_by_traffic.branch_id}
    assert test_branch.branch_id not in decision.branch_ids
    assert inactive_branch.branch_id not in decision.branch_ids


def test_select_reference_branch_ids_fallback_to_best_active_candidate():
    client_id = uuid4()
    weak = _signal(client_id=client_id, has_instance_id=False, has_phone=False, integration_ok=False)
    strong = _signal(client_id=client_id, has_instance_id=True, has_phone=False, onboarding_go_no_go=True)

    decisions = select_reference_branch_ids([weak, strong])
    decision = decisions[client_id]

    assert decision.reason == "active_fallback_best_candidate"
    assert decision.branch_ids == (strong.branch_id,)


def test_select_reference_branch_ids_no_active_branches():
    client_id = uuid4()
    inactive = _signal(client_id=client_id, is_active=False, go_live_allowed=True)

    decisions = select_reference_branch_ids([inactive])
    decision = decisions[client_id]

    assert decision.reason == "no_active_branches"
    assert decision.branch_ids == ()
