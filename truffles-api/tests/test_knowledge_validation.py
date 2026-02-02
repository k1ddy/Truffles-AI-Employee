import copy

from app.services.knowledge_validation import (
    build_diff,
    dump_pack_yaml,
    parse_draft_text,
    validate_payload,
)


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
                    {"name": "Haircut", "price_items": ["Haircut"]},
                    {"name": "Manicure", "price_items": ["Manicure"]},
                ]
            },
            "service_duration_estimates": {"haircut_min": "40-60"},
            "booking": {"collect_fields": ["name", "phone"], "bot_can_confirm": True},
            "guest_policy": {"allowed_guests": "yes"},
            "safety": {"medical_note": "Ask admin"},
            "pricing": {"price_from_reason": "Depends on length"},
            "quality": {"expectations_photo": "Bring a photo"},
            "price_list": [
                {"category": "Hair", "items": [{"name": "Haircut", "price": 1000}]},
                {"category": "Nails", "items": [{"name": "Manicure", "price": 2000}]},
            ],
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


def test_parse_draft_text_accepts_yaml():
    payload = _base_payload()
    draft_text = dump_pack_yaml(payload)
    parsed, errors = parse_draft_text(draft_text)
    assert errors == []
    assert parsed == payload


def test_validate_payload_missing_required_field():
    payload = _base_payload()
    payload["client_pack"]["salon"].pop("name")
    errors, warnings = validate_payload(payload)
    assert any("client_pack.salon.name" in err for err in errors)
    assert warnings == []


def test_validate_payload_requires_ru_kk_languages():
    payload = _base_payload()
    payload["client_pack"]["salon"]["communication"]["languages"] = ["ru"]
    errors, warnings = validate_payload(payload)
    assert any("client_pack.salon.communication.languages" in err for err in errors)
    assert warnings == []


def test_validate_payload_warns_on_reduced_services():
    previous = _base_payload()
    payload = copy.deepcopy(previous)
    payload["client_pack"]["services_catalog"]["services"] = [{"name": "Haircut"}]
    errors, warnings = validate_payload(payload, previous_payload=previous)
    assert errors == []
    assert any("services_catalog.services reduced" in warning for warning in warnings)


def test_build_diff_returns_text():
    previous = _base_payload()
    payload = copy.deepcopy(previous)
    payload["client_pack"]["salon"]["city"] = "Astana"
    diff = build_diff(previous, payload)
    assert "Astana" in diff
