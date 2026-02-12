from types import SimpleNamespace

from app.routers import console as console_router
from app.services.onboarding_intake_service import build_intake_payload, evaluate_intake_payload


def test_build_intake_payload_parses_text_into_pack_fields():
    payload = build_intake_payload(
        client_data_json=None,
        client_data_text="""
        Название: Demo Salon
        Город: Алматы
        Адрес: Абая 10
        График: Пн-Вс 09:00-21:00
        Языки: ru, kk
        - Маникюр 12000 тг 60 мин
        - Педикюр 18000 тг 90 мин
        """,
    )

    salon = payload.get("client_pack", {}).get("salon", {})
    assert salon.get("name") == "Demo Salon"
    assert salon.get("city") == "Алматы"
    assert salon.get("address", {}).get("full") == "Абая 10"
    assert salon.get("hours", {}).get("open") == "09:00"
    assert salon.get("hours", {}).get("close") == "21:00"
    assert set(salon.get("communication", {}).get("languages", [])) == {"ru", "kk"}

    services = payload.get("client_pack", {}).get("services_catalog", {}).get("services", [])
    assert len(services) >= 2
    assert any(service.get("name") == "Маникюр" for service in services)


def test_evaluate_intake_payload_returns_missing_questions():
    payload = {"client_pack": {"salon": {"name": "Demo Salon"}}}
    missing, questions = evaluate_intake_payload(payload)

    assert "client_pack.salon.city" in missing
    assert any("город" in question.casefold() for question in questions)


def test_evaluate_intake_payload_skips_booking_for_non_booking_domain():
    payload = {
        "client_pack": {
            "salon": {
                "name": "Demo Legal",
                "city": "Almaty",
                "address": {"full": "Main street, 1"},
                "hours": {"days": ["mon"], "open": "09:00", "close": "18:00"},
                "services_summary": "Legal consultations",
                "communication": {"languages": ["ru", "kk"]},
            },
            "services_catalog": {"services": [{"name": "Consultation"}]},
            "guest_policy": {"allowed_guests": "no"},
            "safety": {"medical_note": "n/a"},
            "pricing": {"price_from_reason": "depends on case"},
            "quality": {"expectations_photo": "n/a"},
            "price_list": [{"category": "Legal", "items": [{"name": "Consultation", "price": 10000}]}],
            "policy": {
                "hard_law": {"intents": ["refund"]},
                "payment_info": {"intent": "payment", "keywords": ["pay"]},
                "reschedule": {"intent": "reschedule", "keywords": ["reschedule"]},
                "cancel": {"intent": "cancel_request", "keywords": ["cancel"]},
                "medical": {"intent": "medical", "keywords": ["medical"]},
                "legal": {"intent": "legal", "keywords": ["legal"]},
                "complaint": {"intent": "complaint", "keywords": ["complaint"]},
                "discounts": {"intent": "discounts", "keywords": ["discount"]},
                "guard_topics": {"refund": ["refund"]},
            },
        }
    }

    missing, questions = evaluate_intake_payload(payload, domain_slug="legal")

    assert "client_pack.booking.collect_fields" not in missing
    assert "client_pack.booking.bot_can_confirm" not in missing
    assert "client_pack.service_duration_estimates" not in missing
    assert all("записи" not in question.casefold() for question in questions)


def test_build_capabilities_from_purchased_services_maps_flags():
    result = console_router._build_capabilities_from_purchased_services(
        purchased_services=[
            "whatsapp",
            "booking_confirm",
            "knowledge_upload",
            "provider_google_calendar",
        ],
        purchased_payload=None,
        domain_slug="beauty",
    )

    assert result.domain_slug == "beauty"
    assert result.channels.whatsapp is True
    assert result.features.booking_mode == "confirm_slots"
    assert result.features.knowledge_upload is True
    assert result.providers.calendar_provider == "google_calendar"


def test_webhook_secret_derived_from_instance_is_deterministic(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET_PEPPER", "test-pepper")
    first = console_router._derive_webhook_secret_from_instance("instance-123")
    second = console_router._derive_webhook_secret_from_instance("instance-123")
    third = console_router._derive_webhook_secret_from_instance("instance-456")

    assert first == second
    assert first != third
    assert first.startswith("whs_v1_")


def test_ensure_webhook_secret_updates_branch_record(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET_PEPPER", "test-pepper")
    client = SimpleNamespace(name="demo_salon")
    branch = SimpleNamespace(webhook_secret=None)

    secret, webhook_url, changed = console_router._ensure_client_webhook_secret_from_instance(
        db=SimpleNamespace(),
        client=client,
        branch=branch,
        instance_id="instance-123",
    )

    assert changed is True
    assert branch.webhook_secret == secret
    assert webhook_url.endswith(f"webhook_secret={secret}")
