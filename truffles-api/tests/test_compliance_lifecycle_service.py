from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services import compliance_lifecycle_service


class _FakeQuery:
    def __init__(self, items):
        self._items = items

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self._items = self._items[:value]
        return self

    def all(self):
        return list(self._items)


def test_create_lifecycle_run_sets_running_status():
    db = Mock()
    run = compliance_lifecycle_service.create_lifecycle_run(
        db,
        scope="client",
        data_class="learned_responses",
        operation="retention_scan",
        client_id=uuid4(),
        branch_id=None,
        company_id=uuid4(),
        domain_key=None,
        policy_version_id=None,
        policy_scope=None,
        policy_schema_version=None,
        policy_snapshot={"destruction_mode": "archive"},
        actor_id=uuid4(),
        run_mode="preview",
    )

    assert run.status == "running"
    assert run.operation == "retention_scan"
    assert run.data_class == "learned_responses"
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_execute_lifecycle_preview_creates_candidate_records(monkeypatch):
    now = datetime.now(timezone.utc)
    due_items = [
        SimpleNamespace(
            id=uuid4(),
            retention_expires_at=now,
            consent_status="granted",
            anonymization_mode="redact",
            created_at=now,
        ),
        SimpleNamespace(
            id=uuid4(),
            retention_expires_at=now,
            consent_status="granted",
            anonymization_mode="redact",
            created_at=now,
        ),
    ]
    captured = []

    monkeypatch.setattr(
        compliance_lifecycle_service,
        "_due_learned_responses_query",
        lambda *args, **kwargs: _FakeQuery(due_items),
    )
    monkeypatch.setattr(
        compliance_lifecycle_service,
        "append_lifecycle_record",
        lambda *args, **kwargs: captured.append(kwargs),
    )

    run = SimpleNamespace(
        id=uuid4(),
        data_class="learned_responses",
        operation="destruction_preview",
        run_mode="preview",
        client_id=uuid4(),
        branch_id=None,
        policy_snapshot_json={"destruction_mode": "anonymize"},
        scope="client",
    )

    summary = compliance_lifecycle_service.execute_lifecycle_preview(
        Mock(),
        run=run,
        max_items=10,
    )

    assert summary["candidate_count"] == 2
    assert summary["applied_count"] == 0
    assert summary["skipped_count"] == 0
    assert summary["error_count"] == 0
    assert summary["apply_actions"] is False
    assert summary["evidence_record_count"] == 2
    assert len(summary["evidence_digest"]) == 64
    assert summary["execution_action"] == "destruction_preview"
    assert summary["run_mode"] == "preview"
    assert len(captured) == 2
    assert captured[0]["result"] == "candidate"
    assert captured[0]["payload"]["planned_destruction_mode"] == "anonymize"
    assert captured[0]["payload"]["execution_action"] == "destruction_preview"


def test_execute_lifecycle_preview_manual_mode_sets_execution_action(monkeypatch):
    now = datetime.now(timezone.utc)
    due_items = [
        SimpleNamespace(
            id=uuid4(),
            retention_expires_at=now,
            consent_status="granted",
            anonymization_mode="redact",
            created_at=now,
            question_text="Q",
            response_text="A",
            source_name="Manager",
            source_channel="wa",
            redaction_summary=None,
            is_active=True,
            status="approved",
            updated_at=now,
        ),
    ]
    captured = []

    monkeypatch.setattr(
        compliance_lifecycle_service,
        "_due_learned_responses_query",
        lambda *args, **kwargs: _FakeQuery(due_items),
    )
    monkeypatch.setattr(
        compliance_lifecycle_service,
        "append_lifecycle_record",
        lambda *args, **kwargs: captured.append(kwargs),
    )

    run = SimpleNamespace(
        id=uuid4(),
        data_class="learned_responses",
        operation="destruction_preview",
        run_mode="manual",
        client_id=uuid4(),
        branch_id=None,
        policy_snapshot_json={"destruction_mode": "anonymize"},
        scope="client",
    )

    summary = compliance_lifecycle_service.execute_lifecycle_preview(
        Mock(),
        run=run,
        max_items=10,
        apply_actions=True,
    )

    assert summary["candidate_count"] == 1
    assert summary["applied_count"] == 1
    assert summary["skipped_count"] == 0
    assert summary["error_count"] == 0
    assert summary["apply_actions"] is True
    assert summary["evidence_record_count"] == 1
    assert len(summary["evidence_digest"]) == 64
    assert summary["execution_action"] == "anonymize_record"
    assert captured[0]["payload"]["execution_action"] == "anonymize_record"
    assert captured[0]["payload"]["applied"] is True
    assert captured[0]["payload"]["action_status"] == "anonymized"
    assert due_items[0].question_text == "[anonymized]"
    assert due_items[0].response_text == "[anonymized]"
    assert due_items[0].is_active is False


def test_execute_lifecycle_preview_rejects_unsupported_data_class():
    run = SimpleNamespace(
        id=uuid4(),
        data_class="messages",
        operation="retention_scan",
        client_id=uuid4(),
        branch_id=None,
        policy_snapshot_json={},
        scope="client",
    )

    with pytest.raises(ValueError, match="unsupported data_class"):
        compliance_lifecycle_service.execute_lifecycle_preview(
            Mock(),
            run=run,
            max_items=5,
        )


def test_finalize_lifecycle_run_updates_status_and_summary():
    run = SimpleNamespace(
        status="running",
        summary_json={},
        error_message=None,
        finished_at=None,
        updated_at=None,
    )

    compliance_lifecycle_service.finalize_lifecycle_run(
        Mock(),
        run=run,
        status="completed",
        summary={"candidate_count": 3},
        error_message=None,
    )

    assert run.status == "completed"
    assert run.summary_json["candidate_count"] == 3
