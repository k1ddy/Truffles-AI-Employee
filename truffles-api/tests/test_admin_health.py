from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import app.services.health_service as health_service
from app.services.health_service import build_knowledge_activation_health_snapshot, build_minimum_data_status
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

    def fake_get_active_knowledge_version(_db, branch_id):
        if branch_id == branch_ready.id:
            return published_ready
        if branch_id == branch_missing.id:
            return None
        return None

    monkeypatch.setattr(health_service, "get_active_knowledge_version", fake_get_active_knowledge_version)

    status = build_minimum_data_status(db)

    assert status["version"] == MINIMUM_DATA_CONTRACT_VERSION
    assert status["branches_total"] == 2
    assert status["ready_count"] == 1
    assert status["missing_count"] == 1
    assert status["missing"][0]["branch_id"] == str(branch_missing.id)
    assert "knowledge_published" in status["missing"][0]["missing_fields"]


def test_build_knowledge_activation_health_snapshot_marks_stale_running_critical(monkeypatch):
    now = datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc)
    jobs = [
        SimpleNamespace(
            state="queued",
            queued_at=now - timedelta(minutes=30),
            created_at=now - timedelta(minutes=30),
            heartbeat_at=None,
            started_at=None,
            finished_at=None,
            updated_at=now - timedelta(minutes=30),
        ),
        SimpleNamespace(
            state="running",
            queued_at=now - timedelta(minutes=12),
            created_at=now - timedelta(minutes=12),
            started_at=now - timedelta(minutes=10),
            heartbeat_at=now - timedelta(minutes=3),
            finished_at=None,
            updated_at=now - timedelta(minutes=3),
        ),
        SimpleNamespace(
            state="failed",
            queued_at=now - timedelta(hours=2),
            created_at=now - timedelta(hours=2),
            started_at=now - timedelta(hours=2),
            heartbeat_at=now - timedelta(hours=2),
            finished_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1),
        ),
        SimpleNamespace(
            state="running",
            queued_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=1),
            started_at=now - timedelta(hours=1),
            heartbeat_at=now - timedelta(hours=1),
            finished_at=None,
            updated_at=now - timedelta(hours=1),
        ),
    ]

    monkeypatch.setattr(health_service, "list_latest_knowledge_activation_jobs", lambda *args, **kwargs: jobs)

    snapshot = build_knowledge_activation_health_snapshot(MagicMock(), now=now)

    assert snapshot["status"] == "critical"
    assert snapshot["counts"] == {
        "queued": 1,
        "running": 1,
        "ready": 0,
        "failed": 1,
        "stuck": 1,
    }
    assert snapshot["failed_24h"] == 2
    assert snapshot["stale_running"] == 1
    assert snapshot["oldest_queued_age_seconds"] == 1800
    assert snapshot["oldest_running_heartbeat_age_seconds"] == 180


def test_build_knowledge_activation_health_snapshot_returns_empty_for_empty_branch_scope():
    snapshot = build_knowledge_activation_health_snapshot(
        MagicMock(),
        branch_ids=[],
    )

    assert snapshot["status"] == "healthy"
    assert snapshot["counts"]["queued"] == 0
    assert snapshot["failed_24h"] == 0
