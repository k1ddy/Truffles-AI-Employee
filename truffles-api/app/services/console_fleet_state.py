from typing import Any, Optional

from app.services.console_errors import ConsoleAPIError

CLIENT_STATUS_ACTIVE = "active"
FLEET_LIFECYCLE_STATES = {
    "lead",
    "contracting",
    "onboarding",
    "go_live_ready",
    "active",
    "paused",
    "archived",
}
FLEET_PAYMENT_STATES = {"pending", "confirmed", "rejected", "unknown"}
FLEET_SERVICE_STATES = {"ok", "degraded", "attention"}
FLEET_COMMERCIAL_STATES = {
    "payment_confirmed",
    "payment_pending",
    "payment_rejected",
    "contract_missing",
}
FLEET_NEXT_ACTION_STATES = {
    "qualify_and_collect_contract",
    "collect_signed_contract_and_payment",
    "complete_onboarding_steps",
    "confirm_payment_and_approve_go_live",
    "approve_go_live",
    "resolve_payment_or_service_blocker",
    "archived_no_action",
    "run_integration_recovery",
    "resolve_attention_items",
    "monitor_sla_and_quality",
}


def parse_fleet_lifecycle_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in FLEET_LIFECYCLE_STATES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid fleet_lifecycle")
    return normalized


def parse_fleet_payment_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in FLEET_PAYMENT_STATES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid payment_status")
    return normalized


def parse_fleet_service_param(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized not in FLEET_SERVICE_STATES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid service_state")
    return normalized


def is_client_active_status(status: Optional[str]) -> bool:
    return (status or "").strip().lower() == CLIENT_STATUS_ACTIVE


def normalize_fleet_payment_status(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"pending", "confirmed", "rejected"}:
        return normalized
    return "unknown"


def resolve_fleet_commercial_state(payment_status: str) -> str:
    if payment_status == "confirmed":
        return "payment_confirmed"
    if payment_status == "pending":
        return "payment_pending"
    if payment_status == "rejected":
        return "payment_rejected"
    return "contract_missing"


def resolve_fleet_service_state(
    *,
    client_active: bool,
    active_branches: int,
    degraded_branches: int,
    go_live_ready_branches: int,
) -> str:
    if not client_active:
        return "attention"
    if active_branches <= 0:
        return "attention"
    if degraded_branches > 0:
        return "degraded"
    if go_live_ready_branches < active_branches:
        return "attention"
    return "ok"


def resolve_fleet_lifecycle_override(
    *,
    client_config: Any,
    company_billing_info: Any,
) -> Optional[str]:
    candidates: list[Optional[str]] = []
    if isinstance(company_billing_info, dict):
        candidates.append(company_billing_info.get("lifecycle_state"))
        candidates.append(company_billing_info.get("service_lifecycle_state"))
    if isinstance(client_config, dict):
        candidates.append(client_config.get("lifecycle_state"))
        candidates.append(client_config.get("service_lifecycle_state"))
    for raw in candidates:
        normalized = (raw or "").strip().lower() if isinstance(raw, str) else ""
        if normalized in FLEET_LIFECYCLE_STATES:
            return normalized
    return None


def resolve_fleet_lifecycle_state(
    *,
    client_status: Optional[str],
    client_config: Any,
    company_billing_info: Any,
    payment_status: str,
    active_branches: int,
    go_live_ready_branches: int,
) -> str:
    override = resolve_fleet_lifecycle_override(
        client_config=client_config,
        company_billing_info=company_billing_info,
    )
    if override:
        return override
    if not is_client_active_status(client_status):
        return "archived"
    if payment_status == "rejected":
        return "paused"
    if active_branches <= 0:
        if payment_status == "confirmed":
            return "onboarding"
        return "contracting"
    if go_live_ready_branches < active_branches:
        return "onboarding"
    if payment_status != "confirmed":
        return "go_live_ready"
    return "active"


def resolve_fleet_next_action(
    *,
    lifecycle_state: str,
    service_state: str,
    payment_status: str,
) -> str:
    if lifecycle_state == "lead":
        return "qualify_and_collect_contract"
    if lifecycle_state == "contracting":
        return "collect_signed_contract_and_payment"
    if lifecycle_state == "onboarding":
        return "complete_onboarding_steps"
    if lifecycle_state == "go_live_ready":
        if payment_status != "confirmed":
            return "confirm_payment_and_approve_go_live"
        return "approve_go_live"
    if lifecycle_state == "paused":
        return "resolve_payment_or_service_blocker"
    if lifecycle_state == "archived":
        return "archived_no_action"
    if service_state == "degraded":
        return "run_integration_recovery"
    if service_state == "attention":
        return "resolve_attention_items"
    return "monitor_sla_and_quality"
