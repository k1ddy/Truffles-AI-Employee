from app.services.provider_error_policy import (
    classify_provider_error,
    incident_reason_from_provider_error,
    is_permanent_provider_error,
)


def test_classify_provider_error_billing_by_code():
    classified = classify_provider_error(
        "[CHATFLOW_BILLING_BLOCKED] ChatFlow billing blocked: plan renewal required"
    )

    assert classified.kind == "billing_blocked"
    assert classified.incident_reason_code == "provider_billing_blocked"
    assert classified.retryable is False


def test_classify_provider_error_unavailable_by_marker():
    classified = classify_provider_error("provider timeout while sending message")

    assert classified.kind == "unavailable"
    assert classified.incident_reason_code == "provider_unavailable"
    assert classified.retryable is True


def test_classify_provider_error_transport_guard_is_non_retryable():
    classified = classify_provider_error(
        "[CHATFLOW_ERROR] Outbound blocked by transport mode guard"
    )

    assert classified.kind == "transport_guard"
    assert classified.incident_reason_code == "provider_transport_guard"
    assert classified.retryable is False


def test_incident_reason_from_provider_error_falls_back_to_unknown():
    code, label = incident_reason_from_provider_error("unexpected provider issue")

    assert code == "unknown"
    assert "диагностика" in label.lower()


def test_classify_provider_error_invalid_recipient_marker():
    classified = classify_provider_error("recipient not found for this WhatsApp number")

    assert classified.kind == "invalid_recipient"
    assert classified.incident_reason_code == "provider_invalid_recipient"
    assert classified.retryable is False


def test_is_permanent_provider_error_only_for_non_retryable_rules():
    assert is_permanent_provider_error("[CHATFLOW_BILLING_BLOCKED] plan renewal required") is True
    assert is_permanent_provider_error("Outbound blocked by transport mode guard") is True
    assert is_permanent_provider_error("recipient not found for this WhatsApp number") is True
    assert is_permanent_provider_error("provider timeout") is False
