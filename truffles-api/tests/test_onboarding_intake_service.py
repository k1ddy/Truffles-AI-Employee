from types import SimpleNamespace

from app.routers import console as console_router
from app.services.onboarding_intake_service import (
    build_intake_field_states,
    build_intake_pack_quality_summary,
    build_intake_payload,
    build_intake_question_queue,
    evaluate_intake_payload,
)


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

    business = payload.get("client_pack", {}).get("business", {})
    location = payload.get("client_pack", {}).get("location", {})
    operations = payload.get("client_pack", {}).get("operations", {})
    communication = payload.get("client_pack", {}).get("communication", {})
    catalog = payload.get("client_pack", {}).get("catalog", {})
    assert business.get("name") == "Demo Salon"
    assert location.get("city") == "Алматы"
    assert location.get("address", {}).get("full") == "Абая 10"
    assert operations.get("hours", {}).get("open") == "09:00"
    assert operations.get("hours", {}).get("close") == "21:00"
    assert set(communication.get("languages", [])) == {"ru", "kk"}
    assert "Маникюр" in (catalog.get("summary") or "")

    services = payload.get("client_pack", {}).get("services_catalog", {}).get("services", [])
    assert len(services) >= 2
    assert any(service.get("name") == "Маникюр" for service in services)


def test_build_intake_payload_parses_neutral_business_aliases():
    payload = build_intake_payload(
        client_data_json=None,
        client_data_text="""
        Business name: Demo Clinic
        Location city: Astana
        Location address: Abay 10
        Working hours: mon 09:00-18:00
        Communication languages: ru, kk
        """,
    )

    business = payload.get("client_pack", {}).get("business", {})
    location = payload.get("client_pack", {}).get("location", {})
    operations = payload.get("client_pack", {}).get("operations", {})
    communication = payload.get("client_pack", {}).get("communication", {})
    assert business.get("name") == "Demo Clinic"
    assert location.get("city") == "Astana"
    assert location.get("address", {}).get("full") == "Abay 10"
    assert operations.get("hours", {}).get("open") == "09:00"
    assert operations.get("hours", {}).get("close") == "18:00"
    assert set(communication.get("languages", [])) == {"ru", "kk"}


def test_build_intake_payload_keeps_salon_compatibility_aliases():
    payload = build_intake_payload(
        client_data_json={
            "client_pack": {
                "business": {"name": "Demo Beauty"},
                "location": {"city": "Almaty", "address": {"full": "Abay 10"}},
                "operations": {"hours": {"days": ["mon"], "open": "09:00", "close": "18:00"}},
                "catalog": {"summary": "Hair and nails"},
                "communication": {"languages": ["ru", "kk"]},
            }
        },
        client_data_text=None,
    )

    salon = payload.get("client_pack", {}).get("salon", {})
    assert salon.get("name") == "Demo Beauty"
    assert salon.get("city") == "Almaty"
    assert salon.get("address", {}).get("full") == "Abay 10"


def test_build_intake_payload_ignores_markdown_noise_blocks():
    payload = build_intake_payload(
        client_data_json=None,
        client_data_text="""
        ## Demo package
        Название: Demo Salon
        Город: Алматы
        Адрес: Абая 10
        График: Пн-Вс 09:00-21:00
        Языки: ru, kk
        - Маникюр 12000 тг 60 мин

        ```json
        {
          "city": "Шымкент",
          "name": "Noise"
        }
        ```

        | field | value |
        | --- | --- |
        | city | Astana |
        """,
    )

    business = payload.get("client_pack", {}).get("business", {})
    location = payload.get("client_pack", {}).get("location", {})
    operations = payload.get("client_pack", {}).get("operations", {})
    services = payload.get("client_pack", {}).get("services_catalog", {}).get("services", [])

    assert business.get("name") == "Demo Salon"
    assert location.get("city") == "Алматы"
    assert location.get("address", {}).get("full") == "Абая 10"
    assert operations.get("hours", {}).get("open") == "09:00"
    assert operations.get("hours", {}).get("close") == "21:00"
    assert len(services) == 1
    assert services[0].get("name") == "Маникюр"
    assert services[0].get("price") == 12000
    assert services[0].get("duration_minutes") == 60


def test_evaluate_intake_payload_returns_missing_questions():
    payload = {"client_pack": {"salon": {"name": "Demo Salon"}}}
    missing, questions = evaluate_intake_payload(payload)

    assert "client_pack.location.city" in missing
    assert any("город" in question.casefold() for question in questions)


def test_evaluate_intake_payload_skips_booking_for_non_booking_domain():
    payload = {
        "client_pack": {
            "business": {"name": "Demo Legal"},
            "location": {"city": "Almaty", "address": {"full": "Main street, 1"}},
            "operations": {"hours": {"days": ["mon"], "open": "09:00", "close": "18:00"}},
            "catalog": {"summary": "Legal consultations"},
            "communication": {"languages": ["ru", "kk"]},
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


def test_build_intake_field_states_marks_confirmed_assumed_unknown():
    client_data_json = {
        "client_pack": {
            "business": {"name": "Demo Legal"},
            "communication": {"languages": ["ru", "kk"]},
            "catalog": {"summary": "Legal consultations"},
        }
    }
    payload = build_intake_payload(
        client_data_json=client_data_json,
        client_data_text=None,
    )

    states = build_intake_field_states(
        payload,
        domain_slug="legal",
        client_data_json=client_data_json,
    )
    by_field = {item.field: item for item in states}

    assert by_field["client_pack.business.name"].status == "confirmed"
    assert by_field["client_pack.communication.languages"].status == "confirmed"
    assert by_field["client_pack.location.city"].status == "unknown"
    assert by_field["client_pack.policy.hard_law"].status == "unknown"


def test_build_intake_question_queue_prioritizes_blockers():
    missing_fields = [
        "client_pack.business.name",
        "client_pack.policy.hard_law",
        "client_pack.location.city",
    ]

    queue = build_intake_question_queue(missing_fields)

    assert [item.field for item in queue] == [
        "client_pack.policy.hard_law",
        "client_pack.location.city",
        "client_pack.business.name",
    ]
    assert queue[0].priority == "critical"
    assert queue[0].blocking_go_live is True
    assert queue[1].priority == "high"
    assert queue[2].priority == "medium"


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


def _build_complete_beauty_payload() -> dict:
    return {
        "client_pack": {
            "business": {"name": "Demo Salon"},
            "location": {"city": "Almaty", "address": {"full": "Abay 10"}},
            "operations": {"hours": {"days": ["mon", "tue"], "open": "09:00", "close": "21:00"}},
            "catalog": {"summary": "Nails and lashes"},
            "communication": {"languages": ["ru", "kk"]},
            "services_catalog": {
                "services": [{"name": "Маникюр", "price": 12000, "duration_minutes": 60}]
            },
            "service_duration_estimates": [{"service": "Маникюр", "duration_minutes": 60}],
            "booking": {
                "collect_fields": ["service", "time", "name", "phone"],
                "bot_can_confirm": True,
            },
            "guest_policy": {"allowed": "yes"},
            "safety": {"medical_note": "consult specialist"},
            "pricing": {"price_from_reason": "depends on scope"},
            "quality": {"expectations_photo": "reference required"},
            "price_list": [{"category": "Nails", "items": [{"name": "Маникюр", "price": 12000}]}],
            "policy": {
                "hard_law": {"intent": "hard_law", "keywords": ["law"]},
                "payment_info": {"intent": "payment", "keywords": ["pay"]},
                "reschedule": {"intent": "reschedule", "keywords": ["move"]},
                "cancel": {"intent": "cancel", "keywords": ["cancel"]},
                "medical": {"intent": "medical", "keywords": ["medical"]},
                "legal": {"intent": "legal", "keywords": ["legal"]},
                "complaint": {"intent": "complaint", "keywords": ["complaint"]},
                "discounts": {"intent": "discounts", "keywords": ["discount"]},
                "guard_topics": {"refund": ["refund", "возврат"]},
            },
        },
        "domain_pack": {
            "version": "1.0.0",
            "ood_anchors": {
                "in_domain": ["маникюр", "педикюр"],
                "out_of_domain": ["кредит"],
                "strict_in": ["салон"],
            },
        },
    }


def _baseline_from_quality(summary) -> dict:
    return {
        "compile": {
            "status": summary.compile.status,
            "infra_valid": summary.compile.infra_valid,
            "policy_bundle_present": summary.compile.policy_bundle_present,
            "signal_graph_present": summary.compile.signal_graph_present,
        },
        "quality_matrix": {
            "status": summary.quality_matrix.status,
            "infra_valid": summary.quality_matrix.infra_valid,
            "semantic_valid": summary.quality_matrix.semantic_valid,
            "missing_fields_count": summary.quality_matrix.missing_fields_count,
            "critical_missing_fields_count": summary.quality_matrix.critical_missing_fields_count,
            "dimensions": [
                {"id": item.id, "status": item.status}
                for item in summary.quality_matrix.dimensions
            ],
        },
    }


def test_build_intake_pack_quality_summary_passes_for_complete_payload():
    payload = _build_complete_beauty_payload()

    summary = build_intake_pack_quality_summary(
        payload,
        domain_slug="beauty",
        require_booking=True,
    )

    assert summary.compile.status == "pass"
    assert summary.compile.policy_bundle_present is True
    assert summary.compile.signal_graph_present is True
    assert summary.quality_matrix.status == "pass"
    assert summary.quality_matrix.semantic_valid is True
    assert summary.quality_matrix.missing_fields_count == 0
    assert summary.quality_matrix.critical_missing_fields_count == 0
    assert summary.quality_matrix.regressions == []


def test_build_intake_pack_quality_summary_fails_when_policy_schema_is_invalid():
    payload = _build_complete_beauty_payload()
    payload["client_pack"]["policy"]["hard_law"] = "invalid"

    summary = build_intake_pack_quality_summary(
        payload,
        domain_slug="beauty",
        require_booking=True,
    )

    assert summary.compile.status == "fail"
    assert summary.compile.infra_valid is True
    assert summary.quality_matrix.status == "fail"
    assert any(item.id == "pack_compile" and item.status == "fail" for item in summary.quality_matrix.dimensions)


def test_build_intake_pack_quality_summary_marks_regression_vs_baseline():
    baseline_payload = _build_complete_beauty_payload()
    baseline_summary = build_intake_pack_quality_summary(
        baseline_payload,
        domain_slug="beauty",
        require_booking=True,
    )
    current_payload = _build_complete_beauty_payload()
    current_payload["client_pack"]["booking"].pop("collect_fields")

    summary = build_intake_pack_quality_summary(
        current_payload,
        domain_slug="beauty",
        require_booking=True,
        baseline_summary=_baseline_from_quality(baseline_summary),
    )

    assert summary.quality_matrix.status == "fail"
    assert "missing_fields_count" in summary.quality_matrix.regressions
    assert "dimension:intake_required_fields" in summary.quality_matrix.regressions
