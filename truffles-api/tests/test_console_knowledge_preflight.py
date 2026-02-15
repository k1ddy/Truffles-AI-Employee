from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import console_knowledge_preflight as preflight


class _QueryStub:
    def __init__(self, events):
        self._events = events

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._events


class _DBStub:
    def __init__(self, events):
        self._events = events

    def query(self, _model):
        return _QueryStub(self._events)


def _event(payload: dict):
    return SimpleNamespace(created_at=datetime.now(timezone.utc), payload=payload)


def test_build_knowledge_draft_hash_is_trim_stable() -> None:
    left = preflight.build_knowledge_draft_hash("  hello world  ")
    right = preflight.build_knowledge_draft_hash("hello world")

    assert left == right
    assert len(left) == 16


def test_build_knowledge_validate_payload_contains_hash_and_counts() -> None:
    payload = preflight.build_knowledge_validate_payload(
        valid=True,
        errors=[],
        warnings=["w1"],
        draft_hash="abc123",
    )

    assert payload["valid"] is True
    assert payload["errors_count"] == 0
    assert payload["warnings_count"] == 1
    assert payload["draft_hash"] == "abc123"


def test_has_recent_knowledge_preflight_true_for_matching_valid_event() -> None:
    draft_hash = preflight.build_knowledge_draft_hash("draft")
    db = _DBStub(
        [
            _event({"draft_hash": draft_hash, "valid": True, "errors": [], "warnings": []}),
        ]
    )

    result = preflight.has_recent_knowledge_preflight(
        db=db,
        client_id=uuid4(),
        branch_id=uuid4(),
        draft_hash=draft_hash,
    )

    assert result is True


def test_has_recent_knowledge_preflight_false_for_hash_mismatch() -> None:
    db = _DBStub(
        [
            _event({"draft_hash": "other_hash", "valid": True, "errors": [], "warnings": []}),
        ]
    )

    result = preflight.has_recent_knowledge_preflight(
        db=db,
        client_id=uuid4(),
        branch_id=uuid4(),
        draft_hash="target_hash",
    )

    assert result is False


def test_has_recent_knowledge_preflight_false_when_errors_present() -> None:
    draft_hash = preflight.build_knowledge_draft_hash("draft")
    db = _DBStub(
        [
            _event({"draft_hash": draft_hash, "valid": True, "errors": ["e1"], "warnings": []}),
        ]
    )

    result = preflight.has_recent_knowledge_preflight(
        db=db,
        client_id=uuid4(),
        branch_id=uuid4(),
        draft_hash=draft_hash,
    )

    assert result is False
