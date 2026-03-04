from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.console_errors import ConsoleAPIError
from app.services.console_onboarding_readiness import (
    BRANCH_GO_LIVE_DEFAULT_STATE,
    GO_LIVE_WAIVER_MAX_HOURS,
    GO_LIVE_WAIVER_MIN_HOURS,
    coerce_utc_datetime,
    ensure_branch_go_live_gate,
    is_branch_go_live_allowed,
    is_branch_go_live_waiver_active,
    is_readiness_hard_gate_enforced_for_branch,
    normalize_branch_go_live_state,
    normalize_go_live_waiver_ttl_hours,
    resolve_readiness_hard_gate_blockers,
    serialize_onboarding_readiness_kernel,
)


def _build_readiness_kernel() -> SimpleNamespace:
    return SimpleNamespace(
        status="warn",
        blocker_codes=["provider_binding_rebind_required"],
        next_action_codes=["sync_provider"],
        shadow_hard_gate_blockers=[
            "go_no_go:payment_confirmed",
            "provider_binding_rebind_required",
            "go_no_go:payment_confirmed",
            "noise",
        ],
        auto_questions=[
            SimpleNamespace(
                code="payment_confirmed",
                question="Оплата подтверждена?",
                blocking_go_live=True,
            )
        ],
        dimensions=[
            SimpleNamespace(
                id="delivery_health",
                status="warn",
                blocker_codes=["provider_binding_rebind_required"],
                next_action_codes=["sync_provider"],
            )
        ],
    )


def test_resolve_readiness_hard_gate_blockers_filters_and_dedupes() -> None:
    readiness_kernel = _build_readiness_kernel()

    blockers = resolve_readiness_hard_gate_blockers(
        readiness_kernel,
        hard_gate_codes={"provider_binding_rebind_required"},
    )

    assert blockers == [
        "go_no_go:payment_confirmed",
        "provider_binding_rebind_required",
    ]


def test_is_readiness_hard_gate_enforced_for_branch_supports_flag_and_canary() -> None:
    branch = SimpleNamespace(id=str(uuid4()).upper())

    assert is_readiness_hard_gate_enforced_for_branch(
        branch,
        hard_gate_enabled=True,
        canary_branch_ids=set(),
    )
    assert is_readiness_hard_gate_enforced_for_branch(
        branch,
        hard_gate_enabled=False,
        canary_branch_ids={str(branch.id).strip().lower()},
    )
    assert not is_readiness_hard_gate_enforced_for_branch(
        SimpleNamespace(id=None),
        hard_gate_enabled=False,
        canary_branch_ids=set(),
    )


def test_serialize_onboarding_readiness_kernel_returns_none_for_empty_input() -> None:
    assert (
        serialize_onboarding_readiness_kernel(
            None,
            hard_gate_enforced=True,
            hard_gate_codes={"provider_binding_rebind_required"},
        )
        is None
    )


def test_serialize_onboarding_readiness_kernel_builds_shadow_hard_gate() -> None:
    readiness_kernel = _build_readiness_kernel()

    payload = serialize_onboarding_readiness_kernel(
        readiness_kernel,
        hard_gate_enforced=True,
        hard_gate_codes={"provider_binding_rebind_required"},
    )

    assert payload is not None
    assert payload.status == "warn"
    assert payload.shadow_hard_gate.enforced is True
    assert payload.shadow_hard_gate.status == "fail"
    assert payload.shadow_hard_gate.blocker_codes == [
        "go_no_go:payment_confirmed",
        "provider_binding_rebind_required",
    ]
    assert payload.auto_questions[0].code == "payment_confirmed"
    assert payload.dimensions[0].id == "delivery_health"


def test_normalize_branch_go_live_state_returns_default_for_unknown_value() -> None:
    assert normalize_branch_go_live_state("approved") == "approved"
    assert normalize_branch_go_live_state("  rejected  ") == "rejected"
    assert normalize_branch_go_live_state("unknown") == BRANCH_GO_LIVE_DEFAULT_STATE


def test_normalize_go_live_waiver_ttl_hours_enforces_bounds() -> None:
    assert normalize_go_live_waiver_ttl_hours(GO_LIVE_WAIVER_MIN_HOURS) == GO_LIVE_WAIVER_MIN_HOURS
    assert normalize_go_live_waiver_ttl_hours(GO_LIVE_WAIVER_MAX_HOURS) == GO_LIVE_WAIVER_MAX_HOURS
    with pytest.raises(ConsoleAPIError):
        normalize_go_live_waiver_ttl_hours(GO_LIVE_WAIVER_MIN_HOURS - 1)
    with pytest.raises(ConsoleAPIError):
        normalize_go_live_waiver_ttl_hours(GO_LIVE_WAIVER_MAX_HOURS + 1)


def test_coerce_utc_datetime_adds_tz_for_naive_values() -> None:
    naive_value = datetime(2026, 3, 4, 12, 0, 0)
    aware_value = datetime(2026, 3, 4, 12, 0, 0, tzinfo=timezone.utc)
    assert coerce_utc_datetime(None) is None
    assert coerce_utc_datetime(naive_value) == aware_value
    assert coerce_utc_datetime(aware_value) == aware_value


def test_is_branch_go_live_waiver_active_and_allowed() -> None:
    now = datetime.now(timezone.utc)
    pending_without_waiver = SimpleNamespace(
        go_live_state="pending",
        go_live_waiver_until=None,
    )
    approved_branch = SimpleNamespace(
        go_live_state="approved",
        go_live_waiver_until=None,
    )
    waived_branch = SimpleNamespace(
        go_live_state="pending",
        go_live_waiver_until=now + timedelta(hours=2),
    )

    assert not is_branch_go_live_waiver_active(pending_without_waiver, now=now)
    assert is_branch_go_live_waiver_active(waived_branch, now=now)
    assert not is_branch_go_live_allowed(pending_without_waiver, now=now)
    assert is_branch_go_live_allowed(approved_branch, now=now)
    assert is_branch_go_live_allowed(waived_branch, now=now)


def test_ensure_branch_go_live_gate_raises_with_details_when_blocked() -> None:
    branch = SimpleNamespace(
        go_live_state="pending",
        go_live_waiver_until=None,
        go_live_reason="awaiting_checklist",
    )

    with pytest.raises(ConsoleAPIError) as exc:
        ensure_branch_go_live_gate(branch, operation="branch_activate")

    assert exc.value.status_code == 409
    assert exc.value.code == "GO_LIVE_GATE_REQUIRED"
    assert exc.value.details is not None
    assert exc.value.details["operation"] == "branch_activate"
