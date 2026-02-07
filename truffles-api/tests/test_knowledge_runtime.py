from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services import knowledge_runtime
from app.services.demo_salon_knowledge import load_yaml_truth
from app.services.knowledge_runtime import RuntimeTruth, set_runtime_truth


def test_build_runtime_truth_missing_branch():
    runtime_truth = knowledge_runtime.build_runtime_truth(
        db=Mock(),
        client_slug="demo_salon",
        client_id=uuid4(),
        branch_id=None,
        allow_fallback=False,
    )
    assert runtime_truth.source == "missing_branch"
    assert runtime_truth.truth == {}


def test_build_runtime_truth_uses_published_pack(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    payload = {
        "compiled_artifacts": {
            "effective_pack": {"salon": {"name": "Test"}},
            "hash": "hash-1",
        }
    }
    version = SimpleNamespace(payload_json=payload, client_id=client_id, id=uuid4())

    expected_branch_id = branch_id

    def _fake_get_current_published(_db, branch_id):
        assert branch_id == expected_branch_id
        return version

    monkeypatch.setattr(knowledge_runtime, "get_current_published", _fake_get_current_published)

    runtime_truth = knowledge_runtime.build_runtime_truth(
        db=Mock(),
        client_slug="demo_salon",
        client_id=client_id,
        branch_id=branch_id,
        allow_fallback=False,
    )
    assert runtime_truth.source == "knowledge_versions"
    assert runtime_truth.truth == {"salon": {"name": "Test"}}
    assert runtime_truth.compiled_hash == "hash-1"
    assert runtime_truth.version_id == str(version.id)


def test_load_yaml_truth_uses_runtime_truth():
    runtime_truth = RuntimeTruth(
        truth={"salon": {"name": "FromDB"}},
        client_slug="demo_salon",
        branch_id=uuid4(),
        source="knowledge_versions",
        allow_fallback=False,
    )
    set_runtime_truth(runtime_truth)
    try:
        truth = load_yaml_truth("demo_salon")
        assert truth.get("salon", {}).get("name") == "FromDB"
    finally:
        set_runtime_truth(None)


def test_load_yaml_truth_uses_runtime_truth_for_generic_slug():
    runtime_truth = RuntimeTruth(
        truth={"salon": {"name": "GenericFromDB"}},
        client_slug="generic",
        branch_id=uuid4(),
        source="knowledge_versions",
        allow_fallback=False,
    )
    set_runtime_truth(runtime_truth)
    try:
        truth = load_yaml_truth("generic")
        assert truth.get("salon", {}).get("name") == "GenericFromDB"
    finally:
        set_runtime_truth(None)


def test_load_yaml_truth_blocks_slug_mismatch_without_fallback():
    runtime_truth = RuntimeTruth(
        truth={"salon": {"name": "TenantScoped"}},
        client_slug="generic",
        branch_id=uuid4(),
        source="knowledge_versions",
        allow_fallback=False,
    )
    set_runtime_truth(runtime_truth)
    try:
        truth = load_yaml_truth("demo_salon")
        assert truth == {}
    finally:
        set_runtime_truth(None)
