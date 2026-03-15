from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services import knowledge_registry_service as service


def test_sync_published_branch_docs_runs_primary_sync_and_backfill(monkeypatch):
    branch = SimpleNamespace(id=uuid4(), client_id=uuid4(), knowledge_tag="branch-tag")
    version = SimpleNamespace(id=uuid4(), payload_json={"client_pack": {"salon": {"name": "A"}}})
    captured = {}

    def _sync_primary(payload_json, *, client_slug, branch_id, knowledge_tag, version_id):
        captured["primary"] = {
            "payload_json": payload_json,
            "client_slug": client_slug,
            "branch_id": branch_id,
            "knowledge_tag": knowledge_tag,
            "version_id": version_id,
        }
        return 7, 3

    def _backfill(db, *, client_slug, client_id, exclude_branch_id):
        captured["backfill"] = {
            "client_slug": client_slug,
            "client_id": client_id,
            "exclude_branch_id": exclude_branch_id,
        }
        return 2, 1

    monkeypatch.setattr(service, "sync_qdrant_from_pack", _sync_primary)
    monkeypatch.setattr(service, "backfill_client_published_branches", _backfill)

    stats = service.sync_published_branch_docs(
        db=SimpleNamespace(),
        client_slug="demo_salon",
        branch=branch,
        version=version,
        backfill_other_branches=True,
    )

    assert stats == {
        "docs_synced": 7,
        "services_synced": 3,
        "backfill_synced": 2,
        "backfill_skipped": 1,
    }
    assert captured["primary"]["client_slug"] == "demo_salon"
    assert captured["primary"]["branch_id"] == branch.id
    assert captured["primary"]["knowledge_tag"] == "branch-tag"
    assert captured["primary"]["version_id"] == version.id
    assert captured["backfill"]["client_id"] == branch.client_id
    assert captured["backfill"]["exclude_branch_id"] == branch.id


def test_backfill_client_published_branches_syncs_only_branches_with_published_pack(monkeypatch):
    client_id = uuid4()
    first_branch = SimpleNamespace(id=uuid4(), knowledge_tag="branch-a")
    second_branch = SimpleNamespace(id=uuid4(), knowledge_tag="branch-b")
    first_version = SimpleNamespace(id=uuid4(), payload_json={"client_pack": {"salon": {"name": "A"}}})
    captured_calls = []

    monkeypatch.setattr(
        service,
        "_list_client_backfill_branches",
        lambda db, *, client_id, exclude_branch_id: [first_branch, second_branch],
    )
    monkeypatch.setattr(
        service,
        "get_current_published",
        lambda db, *, branch_id: first_version if branch_id == first_branch.id else None,
    )

    def _sync(payload_json, *, client_slug, branch_id, knowledge_tag, version_id):
        captured_calls.append(
            {
                "payload_json": payload_json,
                "client_slug": client_slug,
                "branch_id": branch_id,
                "knowledge_tag": knowledge_tag,
                "version_id": version_id,
            }
        )
        return 3, 1

    monkeypatch.setattr(service, "sync_qdrant_from_pack", _sync)

    synced, skipped = service.backfill_client_published_branches(
        db=SimpleNamespace(),
        client_slug="demo_salon",
        client_id=client_id,
        exclude_branch_id=None,
    )

    assert synced == 1
    assert skipped == 1
    assert len(captured_calls) == 1
    assert captured_calls[0]["client_slug"] == "demo_salon"
    assert captured_calls[0]["branch_id"] == first_branch.id
    assert captured_calls[0]["knowledge_tag"] == "branch-a"
    assert captured_calls[0]["version_id"] == first_version.id


def test_publish_version_blocks_lossy_structured_rewrite_before_compile(monkeypatch):
    branch = SimpleNamespace(id=uuid4(), client_id=uuid4())
    current = SimpleNamespace(
        payload_json={
            "client_pack": {
                "guest_policy": {"allow_new_clients": True},
                "policy": {"payment_info": {"methods": ["card"]}},
            }
        },
        status="published",
    )

    monkeypatch.setattr(service, "get_current_published", lambda *_args, **_kwargs: current)
    monkeypatch.setattr(
        service,
        "compile_pack_payload",
        lambda *_args, **_kwargs: pytest.fail("compiler should not run for lossy structured rewrite"),
    )

    with pytest.raises(service.PackCompilerError) as exc_info:
        service.publish_version(
            SimpleNamespace(add=lambda *_args, **_kwargs: None),
            branch=branch,
            payload_json={
                "client_pack": {
                    "guest_policy": "",
                    "policy": {"payment_info": "Оплата наличными"},
                }
            },
            actor_id=uuid4(),
            source_version_id=None,
        )

    assert exc_info.value.errors == [
        "Lossy structured field rewrite blocked: client_pack.guest_policy",
        "Lossy structured field rewrite blocked: client_pack.policy.payment_info",
    ]


def test_process_knowledge_sync_event_runs_branch_only_sync_and_marks_ready(monkeypatch):
    client = SimpleNamespace(id=uuid4(), name="demo_salon", config={})
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        knowledge_tag="branch-a",
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="old",
        knowledge_safe_mode_at=None,
    )
    version = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        branch_id=branch.id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
        sync_status="pending",
        sync_error=None,
        sync_completed_at=None,
    )
    job = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        branch_id=branch.id,
        version_id=version.id,
        state="queued",
        current_stage="queued",
        queued_at=datetime.now(timezone.utc),
        started_at=None,
        heartbeat_at=None,
        finished_at=None,
        last_error=None,
        error_code=None,
        attempt_count=1,
        updated_at=None,
    )
    db = Mock()

    class _Query:
        def __init__(self, row):
            self._row = row

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self._row

    db.query.side_effect = lambda model: _Query(
        {
            service.Client: client,
            service.Branch: branch,
            service.KnowledgeVersion: version,
            service.KnowledgeActivationJob: job,
        }[model]
    )
    captured: dict[str, object] = {}

    def _sync(*_args, **kwargs):
        captured["backfill_other_branches"] = kwargs["backfill_other_branches"]
        return {"docs_synced": 2, "services_synced": 1, "backfill_synced": 0, "backfill_skipped": 0}

    monkeypatch.setattr(service, "sync_published_branch_docs", _sync)
    monkeypatch.setattr(service, "extract_compiled_artifacts", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(service, "record_audit_event", lambda *_args, **_kwargs: None)

    ok, error = service.process_knowledge_sync_event(
        db,
        payload_json={
            "payload": {
                "client_id": str(client.id),
                "branch_id": str(branch.id),
                "version_id": str(version.id),
                "job_id": str(job.id),
                "source": "knowledge_publish",
                "actor_id": str(uuid4()),
                "actor_name": "Owner",
            }
        },
    )

    assert ok is True
    assert error is None
    assert captured["backfill_other_branches"] is False
    assert version.sync_status == service.KNOWLEDGE_SYNC_STATUS_READY
    assert version.sync_error is None
    assert isinstance(version.sync_completed_at, datetime)
    assert job.state == service.KNOWLEDGE_ACTIVATION_STATE_READY
    assert job.current_stage == service.KNOWLEDGE_ACTIVATION_STAGE_READY
    assert isinstance(job.heartbeat_at, datetime)
    assert branch.active_knowledge_version_id == version.id
    assert branch.knowledge_safe_mode is False
    assert branch.knowledge_safe_mode_reason is None
    db.commit.assert_called_once()


def test_process_knowledge_sync_event_marks_failed_without_switching_live_on_sync_error(monkeypatch):
    client = SimpleNamespace(id=uuid4(), name="demo_salon", config={})
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        knowledge_tag="branch-a",
        knowledge_safe_mode=False,
        knowledge_safe_mode_reason=None,
        knowledge_safe_mode_at=None,
    )
    version = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        branch_id=branch.id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
        sync_status="pending",
        sync_error=None,
        sync_completed_at=None,
    )
    job = SimpleNamespace(
        id=uuid4(),
        client_id=client.id,
        branch_id=branch.id,
        version_id=version.id,
        state="queued",
        current_stage="queued",
        queued_at=datetime.now(timezone.utc),
        started_at=None,
        heartbeat_at=None,
        finished_at=None,
        last_error=None,
        error_code=None,
        attempt_count=1,
        updated_at=None,
    )
    db = Mock()

    class _Query:
        def __init__(self, row):
            self._row = row

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self._row

    db.query.side_effect = lambda model: _Query(
        {
            service.Client: client,
            service.Branch: branch,
            service.KnowledgeVersion: version,
            service.KnowledgeActivationJob: job,
        }[model]
    )

    monkeypatch.setattr(
        service,
        "sync_published_branch_docs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("timed out")),
    )
    monkeypatch.setattr(service, "record_audit_event", lambda *_args, **_kwargs: None)

    ok, error = service.process_knowledge_sync_event(
        db,
        payload_json={
            "payload": {
                "client_id": str(client.id),
                "branch_id": str(branch.id),
                "version_id": str(version.id),
                "job_id": str(job.id),
                "source": "knowledge_sync_retry",
            }
        },
    )

    assert ok is False
    assert error == "timed out"
    assert version.sync_status == service.KNOWLEDGE_SYNC_STATUS_FAILED
    assert version.sync_error == "timed out"
    assert isinstance(version.sync_completed_at, datetime)
    assert job.state == service.KNOWLEDGE_ACTIVATION_STATE_FAILED
    assert job.current_stage == service.KNOWLEDGE_ACTIVATION_STAGE_FAILED
    assert job.last_error == "timed out"
    assert branch.knowledge_safe_mode is False
    assert branch.knowledge_safe_mode_reason is None
    assert getattr(branch, "active_knowledge_version_id", None) is None
    db.rollback.assert_called_once()
    db.commit.assert_called_once()


def test_claim_queued_knowledge_activation_jobs_marks_running_stage():
    job = service.KnowledgeActivationJob(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        version_id=uuid4(),
        state=service.KNOWLEDGE_ACTIVATION_STATE_QUEUED,
        current_stage=service.KNOWLEDGE_ACTIVATION_STAGE_QUEUED,
        attempt_count=1,
        queued_at=datetime.now(timezone.utc),
    )
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.with_for_update.return_value = query
    query.limit.return_value = query
    query.all.return_value = [job]
    db.query.return_value = query

    claimed = service.claim_queued_knowledge_activation_jobs(db, limit=5)

    assert [item.id for item in claimed] == [job.id]
    assert job.state == service.KNOWLEDGE_ACTIVATION_STATE_RUNNING
    assert job.current_stage == service.KNOWLEDGE_ACTIVATION_STAGE_SYNCING_BRANCH_DOCS
    assert isinstance(job.started_at, datetime)
    assert isinstance(job.heartbeat_at, datetime)
    db.commit.assert_called_once()


def test_mark_stale_knowledge_activation_jobs_stuck_marks_version_failed(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    version_id = uuid4()
    job = service.KnowledgeActivationJob(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        version_id=version_id,
        state=service.KNOWLEDGE_ACTIVATION_STATE_RUNNING,
        current_stage=service.KNOWLEDGE_ACTIVATION_STAGE_APPLYING_CLIENT_CONFIG,
        attempt_count=1,
        queued_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        heartbeat_at=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
    )
    version = service.KnowledgeVersion(
        id=version_id,
        branch_id=branch_id,
        client_id=client_id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
    )
    audit_calls: list[dict] = []

    class _JobsQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return [job]

    class _VersionQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return version

    db = Mock()
    db.query.side_effect = lambda model: _JobsQuery() if model is service.KnowledgeActivationJob else _VersionQuery()
    monkeypatch.setattr(
        service,
        "record_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    results = service.mark_stale_knowledge_activation_jobs_stuck(
        db,
        now=datetime(2026, 3, 15, 9, 30, tzinfo=timezone.utc),
        stuck_after_seconds=60,
    )

    assert results == {"scanned": 1, "stuck": 1}
    assert job.state == service.KNOWLEDGE_ACTIVATION_STATE_STUCK
    assert job.current_stage == service.KNOWLEDGE_ACTIVATION_STAGE_FAILED
    assert job.error_code == service.KNOWLEDGE_ACTIVATION_STUCK_ERROR_CODE
    assert version.sync_status == service.KNOWLEDGE_SYNC_STATUS_FAILED
    assert version.sync_error == service.KNOWLEDGE_ACTIVATION_STUCK_MESSAGE
    assert audit_calls[0]["event_type"] == "knowledge_activation_stuck"
    db.commit.assert_called_once()
