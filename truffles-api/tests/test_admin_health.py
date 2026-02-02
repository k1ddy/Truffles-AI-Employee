from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import app.services.health_service as health_service
from app.services.health_service import build_minimum_data_status
from app.services.knowledge_validation import MINIMUM_DATA_CONTRACT_VERSION


def _ready_payload() -> dict:
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


def test_build_minimum_data_status_reports_missing(monkeypatch):
    branch_ready = SimpleNamespace(id=uuid4(), knowledge_tag="ready", is_active=True)
    branch_missing = SimpleNamespace(id=uuid4(), knowledge_tag="missing", is_active=True)

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [branch_ready, branch_missing]

    published_ready = SimpleNamespace(payload_json=_ready_payload())

    def fake_get_current_published(_db, branch_id):
        if branch_id == branch_ready.id:
            return published_ready
        if branch_id == branch_missing.id:
            return None
        return None

    monkeypatch.setattr(health_service, "get_current_published", fake_get_current_published)

    status = build_minimum_data_status(db)

    assert status["version"] == MINIMUM_DATA_CONTRACT_VERSION
    assert status["branches_total"] == 2
    assert status["ready_count"] == 1
    assert status["missing_count"] == 1
    assert status["missing"][0]["branch_id"] == str(branch_missing.id)
    assert "knowledge_published" in status["missing"][0]["missing_fields"]
