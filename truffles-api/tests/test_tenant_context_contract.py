from app.services.tenant_context_contract import validate_tenant_context_contract


def test_tenant_context_contract_accepts_valid_payload():
    payload = {
        "client_id": "11111111-1111-4111-8111-111111111111",
        "client_slug": "demo_salon",
        "source": "webhook",
    }
    validated, error = validate_tenant_context_contract(payload)

    assert error is None
    assert validated == payload


def test_tenant_context_contract_rejects_invalid_source():
    payload = {
        "client_id": "11111111-1111-4111-8111-111111111111",
        "client_slug": "demo_salon",
        "source": "provider_gateway",
    }
    validated, error = validate_tenant_context_contract(payload)

    assert validated is None
    assert error is not None
    assert "source" in error


def test_tenant_context_contract_allows_missing_client_id_for_webhook_stage():
    payload = {
        "client_slug": "demo_salon",
        "source": "webhook",
    }
    validated, error = validate_tenant_context_contract(payload, require_client_id=False)

    assert error is None
    assert validated == payload
