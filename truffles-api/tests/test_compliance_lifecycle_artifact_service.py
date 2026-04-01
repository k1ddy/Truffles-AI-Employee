from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services import compliance_lifecycle_artifact_service as artifact_service


def _run_record():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        scope="client",
        data_class="learned_responses",
        operation="retention_scan",
        run_mode="manual",
        status="completed",
        client_id=uuid4(),
        branch_id=None,
        policy_version_id=None,
        summary_json={"candidate_count": 1, "evidence_record_count": 1},
    )


def _record_item(*, run_id):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        run_id=run_id,
        entity_type="learned_response",
        entity_id=str(uuid4()),
        action="retention_scan",
        result="candidate",
        payload_json={"retention_expires_at": now.isoformat()},
        occurred_at=now,
    )


def test_publish_lifecycle_artifact_creates_record():
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = None
    db.query.return_value = query
    run = _run_record()
    records = [_record_item(run_id=run.id)]

    artifact = artifact_service.publish_lifecycle_artifact(
        db,
        run=run,
        records=records,
        actor_id=uuid4(),
    )

    assert artifact.run_id == run.id
    assert artifact.artifact_type == "compliance_lifecycle_evidence"
    assert len(artifact.artifact_digest) == 64
    assert artifact.records_count == 1
    assert artifact.evidence_record_count == 1
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_publish_lifecycle_artifact_updates_existing_record():
    db = Mock()
    now = datetime.now(timezone.utc)
    existing = SimpleNamespace(
        id=uuid4(),
        run_id=uuid4(),
        scope="client",
        data_class="learned_responses",
        operation="retention_scan",
        run_mode="preview",
        status="running",
        client_id=uuid4(),
        branch_id=None,
        artifact_type="compliance_lifecycle_evidence",
        artifact_digest="b" * 64,
        payload_json={},
        records_count=0,
        evidence_record_count=0,
        published_by=None,
        published_at=now,
        updated_at=now,
    )
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = existing
    db.query.return_value = query
    run = _run_record()
    run.id = existing.run_id
    run.client_id = existing.client_id
    records = [_record_item(run_id=run.id), _record_item(run_id=run.id)]

    artifact = artifact_service.publish_lifecycle_artifact(
        db,
        run=run,
        records=records,
        actor_id=uuid4(),
    )

    assert artifact is existing
    assert len(existing.artifact_digest) == 64
    assert existing.records_count == 2
    assert existing.evidence_record_count == 1
    db.add.assert_not_called()
    db.flush.assert_called_once()


def test_get_lifecycle_artifact_returns_row():
    db = Mock()
    row = SimpleNamespace(id=uuid4())
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = row
    db.query.return_value = query

    artifact = artifact_service.get_lifecycle_artifact(
        db,
        run_id=uuid4(),
        client_id=uuid4(),
        scope="client",
        branch_id=None,
    )

    assert artifact is row
