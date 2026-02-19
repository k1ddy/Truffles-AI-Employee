from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services import outbox_service


class _MappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


def test_claim_pending_outbox_batches_passes_include_without_conversation_param():
    db = Mock()
    db.execute.return_value = _MappingsResult([{"id": "row-1"}])

    rows = outbox_service.claim_pending_outbox_batches(
        db,
        limit=5,
        idle_seconds=12,
        max_wait_seconds=20,
        include_without_conversation=False,
    )

    assert rows == [{"id": "row-1"}]
    assert db.execute.call_count == 1
    params = db.execute.call_args.args[1]
    assert params["limit"] == 5
    assert params["idle_seconds"] == 12
    assert params["max_wait_seconds"] == 20
    assert params["include_without_conversation"] is False
    db.commit.assert_called_once()


def test_archive_pending_outbox_marks_rows_failed_and_commits():
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        conversation_id=None,
        branch_id=None,
        status="PENDING",
        last_error=None,
        attempts=2,
        next_attempt_at=now,
        updated_at=now,
        created_at=now,
    )

    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = [row]

    db = Mock()
    db.query.return_value = query

    result = outbox_service.archive_pending_outbox(
        db,
        client_id=row.client_id,
        older_than_seconds=3600,
        limit=10,
        reason="archived_pending:older_than_24h",
        only_without_conversation=True,
    )

    assert result == {"matched": 1, "archived": 1}
    assert row.status == "FAILED"
    assert row.last_error == "archived_pending:older_than_24h"
    assert row.next_attempt_at is None
    db.commit.assert_called_once()

