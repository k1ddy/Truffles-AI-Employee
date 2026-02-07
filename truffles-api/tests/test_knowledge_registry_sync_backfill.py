from types import SimpleNamespace
from uuid import uuid4

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
