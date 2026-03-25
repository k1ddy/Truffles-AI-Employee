from app.routers.webhook import outbox as outbox_router


def test_classify_transport_degradation_billing_blocked_marker() -> None:
    meta = outbox_router._classify_transport_degradation(
        "Outbound delivery failed: [CHATFLOW_BILLING_BLOCKED] ChatFlow billing blocked: plan renewal required"
    )

    assert meta == {
        "delivery_state": "transport_degraded",
        "delivery_error_code": "CHATFLOW_BILLING_BLOCKED",
        "delivery_error_class": "provider_billing_blocked",
        "delivery_error_kind": "billing_blocked",
    }


def test_classify_transport_degradation_unknown_error() -> None:
    assert outbox_router._classify_transport_degradation("Outbound delivery failed: temporary timeout") is None
