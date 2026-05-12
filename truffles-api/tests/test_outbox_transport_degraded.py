from app.services import outbox_runtime_service as outbox_runtime


def test_classify_transport_degradation_billing_blocked_marker() -> None:
    meta = outbox_runtime._classify_transport_degradation(
        "Outbound delivery failed: [CHATFLOW_BILLING_BLOCKED] ChatFlow billing blocked: plan renewal required"
    )

    assert meta == {
        "delivery_state": "transport_degraded",
        "delivery_error_code": "CHATFLOW_BILLING_BLOCKED",
        "delivery_error_class": "provider_billing_blocked",
        "delivery_error_kind": "billing_blocked",
    }


def test_classify_transport_degradation_unknown_error() -> None:
    assert outbox_runtime._classify_transport_degradation("Outbound delivery failed: temporary timeout") is None


def test_classify_transport_degradation_transport_guard() -> None:
    meta = outbox_runtime._classify_transport_degradation(
        "ChatFlow delivery failed: [CHATFLOW_ERROR] Outbound blocked by transport mode guard"
    )

    assert meta == {
        "delivery_state": "transport_degraded",
        "delivery_error_code": "CHATFLOW_ERROR",
        "delivery_error_class": "provider_transport_guard",
        "delivery_error_kind": "transport_guard",
    }


def test_extract_decision_trace_id_from_nested_contracts() -> None:
    assert (
        outbox_runtime._extract_decision_trace_id(
            {"decision_trace": {"trace_id": "trace-from-decision"}}
        )
        == "trace-from-decision"
    )
    assert (
        outbox_runtime._extract_decision_trace_id(
            {"runtime_trace_contract": {"trace_id": "trace-from-contract"}}
        )
        == "trace-from-contract"
    )
