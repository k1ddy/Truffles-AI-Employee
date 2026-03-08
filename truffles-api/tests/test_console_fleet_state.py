from app.services.console_errors import ConsoleAPIError
from app.services.console_fleet_state import (
    is_client_active_status,
    normalize_fleet_payment_status,
    parse_fleet_lifecycle_param,
    parse_fleet_payment_param,
    parse_fleet_service_param,
    resolve_fleet_commercial_state,
    resolve_fleet_lifecycle_state,
    resolve_fleet_next_action,
    resolve_fleet_service_state,
)


def test_parse_fleet_filters_accept_none_and_all() -> None:
    assert parse_fleet_lifecycle_param(None) is None
    assert parse_fleet_lifecycle_param("all") is None
    assert parse_fleet_lifecycle_param("ACTIVE") == "active"

    assert parse_fleet_payment_param(None) is None
    assert parse_fleet_payment_param("all") is None
    assert parse_fleet_payment_param("Confirmed") == "confirmed"

    assert parse_fleet_service_param(None) is None
    assert parse_fleet_service_param("all") is None
    assert parse_fleet_service_param("DEGRADED") == "degraded"


def test_parse_fleet_filters_raise_console_error_on_invalid_value() -> None:
    try:
        parse_fleet_lifecycle_param("bad")
    except ConsoleAPIError as exc:
        assert exc.status_code == 400
        assert exc.code == "INVALID_PARAM"
        assert exc.message == "Invalid fleet_lifecycle"
    else:
        raise AssertionError("Expected ConsoleAPIError")

    try:
        parse_fleet_payment_param("bad")
    except ConsoleAPIError as exc:
        assert exc.status_code == 400
        assert exc.code == "INVALID_PARAM"
        assert exc.message == "Invalid payment_status"
    else:
        raise AssertionError("Expected ConsoleAPIError")

    try:
        parse_fleet_service_param("bad")
    except ConsoleAPIError as exc:
        assert exc.status_code == 400
        assert exc.code == "INVALID_PARAM"
        assert exc.message == "Invalid service_state"
    else:
        raise AssertionError("Expected ConsoleAPIError")


def test_normalize_fleet_payment_status_and_commercial_state() -> None:
    assert normalize_fleet_payment_status("confirmed") == "confirmed"
    assert normalize_fleet_payment_status("PENDING") == "pending"
    assert normalize_fleet_payment_status("x") == "unknown"

    assert resolve_fleet_commercial_state("confirmed") == "payment_confirmed"
    assert resolve_fleet_commercial_state("pending") == "payment_pending"
    assert resolve_fleet_commercial_state("rejected") == "payment_rejected"
    assert resolve_fleet_commercial_state("unknown") == "contract_missing"


def test_resolve_fleet_service_state() -> None:
    assert resolve_fleet_service_state(
        client_active=False,
        active_branches=1,
        degraded_branches=0,
        go_live_ready_branches=1,
    ) == "attention"
    assert resolve_fleet_service_state(
        client_active=True,
        active_branches=1,
        degraded_branches=1,
        go_live_ready_branches=1,
    ) == "degraded"
    assert resolve_fleet_service_state(
        client_active=True,
        active_branches=2,
        degraded_branches=0,
        go_live_ready_branches=1,
    ) == "attention"
    assert resolve_fleet_service_state(
        client_active=True,
        active_branches=2,
        degraded_branches=0,
        go_live_ready_branches=2,
    ) == "ok"


def test_resolve_fleet_lifecycle_state_respects_override() -> None:
    lifecycle = resolve_fleet_lifecycle_state(
        client_status="active",
        client_config={"lifecycle_state": "paused"},
        company_billing_info={"lifecycle_state": "active"},
        payment_status="confirmed",
        active_branches=3,
        go_live_ready_branches=3,
    )

    assert lifecycle == "active"

    lifecycle = resolve_fleet_lifecycle_state(
        client_status="active",
        client_config={"service_lifecycle_state": "go_live_ready"},
        company_billing_info=None,
        payment_status="confirmed",
        active_branches=3,
        go_live_ready_branches=3,
    )

    assert lifecycle == "go_live_ready"


def test_resolve_fleet_lifecycle_state_fallback_path() -> None:
    assert resolve_fleet_lifecycle_state(
        client_status="deleted",
        client_config=None,
        company_billing_info=None,
        payment_status="confirmed",
        active_branches=1,
        go_live_ready_branches=1,
    ) == "archived"
    assert resolve_fleet_lifecycle_state(
        client_status="active",
        client_config=None,
        company_billing_info=None,
        payment_status="rejected",
        active_branches=1,
        go_live_ready_branches=1,
    ) == "paused"
    assert resolve_fleet_lifecycle_state(
        client_status="active",
        client_config=None,
        company_billing_info=None,
        payment_status="pending",
        active_branches=0,
        go_live_ready_branches=0,
    ) == "contracting"
    assert resolve_fleet_lifecycle_state(
        client_status="active",
        client_config=None,
        company_billing_info=None,
        payment_status="confirmed",
        active_branches=0,
        go_live_ready_branches=0,
    ) == "onboarding"
    assert resolve_fleet_lifecycle_state(
        client_status="active",
        client_config=None,
        company_billing_info=None,
        payment_status="pending",
        active_branches=2,
        go_live_ready_branches=2,
    ) == "go_live_ready"
    assert resolve_fleet_lifecycle_state(
        client_status="active",
        client_config=None,
        company_billing_info=None,
        payment_status="confirmed",
        active_branches=2,
        go_live_ready_branches=2,
    ) == "active"


def test_resolve_fleet_next_action() -> None:
    assert resolve_fleet_next_action(
        lifecycle_state="lead",
        service_state="ok",
        payment_status="pending",
    ) == "qualify_and_collect_contract"
    assert resolve_fleet_next_action(
        lifecycle_state="go_live_ready",
        service_state="ok",
        payment_status="pending",
    ) == "confirm_payment_and_approve_go_live"
    assert resolve_fleet_next_action(
        lifecycle_state="go_live_ready",
        service_state="ok",
        payment_status="confirmed",
    ) == "approve_go_live"
    assert resolve_fleet_next_action(
        lifecycle_state="active",
        service_state="degraded",
        payment_status="confirmed",
    ) == "run_integration_recovery"
    assert resolve_fleet_next_action(
        lifecycle_state="active",
        service_state="attention",
        payment_status="confirmed",
    ) == "resolve_attention_items"
    assert resolve_fleet_next_action(
        lifecycle_state="active",
        service_state="ok",
        payment_status="confirmed",
    ) == "monitor_sla_and_quality"


def test_is_client_active_status() -> None:
    assert is_client_active_status("active") is True
    assert is_client_active_status(" ACTIVE ") is True
    assert is_client_active_status("deleted") is False
