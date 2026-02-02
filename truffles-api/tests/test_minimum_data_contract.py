from app.services.knowledge_validation import evaluate_minimum_data_contract


def _base_payload() -> dict:
    return {
        "client_pack": {
            "salon": {
                "name": "Demo Salon",
                "city": "Almaty",
                "address": {"full": "Main street, 1"},
                "hours": {"days": ["mon"], "open": "09:00", "close": "18:00"},
                "services_summary": "Hair and nails",
                "communication": {"languages": ["ru", "kk"]},
            },
            "services_catalog": {
                "services": [
                    {"name": "Haircut"},
                ]
            },
            "booking": {"collect_fields": ["name", "phone"], "bot_can_confirm": True},
            "price_list": [
                {"category": "Hair", "items": [{"name": "Haircut", "price": 1000}]},
            ],
            "guest_policy": {"allowed_guests": "ok"},
            "service_duration_estimates": {"haircut": "30"},
            "safety": {"medical_note": "Ask admin"},
            "pricing": {"price_from_reason": "Depends on length"},
            "quality": {"expectations_photo": "Bring a reference"},
            "policy": {
                "hard_law": {"intents": ["refund"]},
                "payment_info": {"intent": "payment", "keywords": ["pay"]},
                "reschedule": {"intent": "reschedule", "keywords": ["reschedule"]},
                "cancel": {"intent": "cancel_request", "keywords": ["cancel"]},
                "medical": {"intent": "medical", "keywords": ["medical"]},
                "legal": {"intent": "legal", "keywords": ["legal"]},
                "complaint": {
                    "intent": "complaint",
                    "keywords": ["complaint"],
                    "explicit_keywords": ["complaint"],
                    "consult_override_keywords": ["fear"],
                },
                "discounts": {"intent": "discounts", "keywords": ["discount"]},
                "guard_topics": {"refund": ["refund"]},
            },
        }
    }


def test_minimum_data_contract_ready():
    status = evaluate_minimum_data_contract(_base_payload())
    assert status.ready is True
    assert status.missing_fields == []


def test_minimum_data_contract_missing_duration():
    payload = _base_payload()
    payload["client_pack"].pop("service_duration_estimates")
    status = evaluate_minimum_data_contract(payload)
    assert status.ready is False
    assert "client_pack.service_duration_estimates" in status.missing_fields


def test_minimum_data_contract_missing_language_variant():
    payload = _base_payload()
    payload["client_pack"]["salon"]["communication"]["languages"] = ["ru"]
    status = evaluate_minimum_data_contract(payload)
    assert status.ready is False
    assert "client_pack.salon.communication.languages" in status.missing_fields


def test_minimum_data_contract_missing_guest_policy():
    payload = _base_payload()
    payload["client_pack"].pop("guest_policy")
    status = evaluate_minimum_data_contract(payload)
    assert status.ready is False
    assert "client_pack.guest_policy" in status.missing_fields
