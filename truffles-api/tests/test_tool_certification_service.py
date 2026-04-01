from types import SimpleNamespace
from unittest.mock import Mock

from app.services import tool_certification_service
from app.services.tool_registry_snapshot_service import list_declared_tool_actions


def _entry(
    *,
    certification_status: str = "certified",
    health_status: str = "healthy",
    registry_status: str = "active",
    allowed_scopes: tuple[str, ...] = ("client", "branch"),
    source: str = "tool_registry",
):
    return SimpleNamespace(
        certification_status=certification_status,
        health_status=health_status,
        registry_status=registry_status,
        allowed_scopes=allowed_scopes,
        source=source,
    )


def test_resolve_tool_certification_decision_blocks_uncertified(monkeypatch):
    monkeypatch.setattr(
        tool_certification_service,
        "_load_effective_registry",
        lambda _db: {"calendar.list_slots": _entry(certification_status="uncertified")},
    )

    decision = tool_certification_service.resolve_tool_certification_decision(
        Mock(),
        tool_action="calendar.list_slots",
        scope="client",
    )

    assert decision.allowed is False
    assert decision.reason == "certification:uncertified"


def test_resolve_tool_certification_decision_blocks_health_down(monkeypatch):
    monkeypatch.setattr(
        tool_certification_service,
        "_load_effective_registry",
        lambda _db: {"catalog.location": _entry(health_status="down")},
    )

    decision = tool_certification_service.resolve_tool_certification_decision(
        Mock(),
        tool_action="catalog.location",
        scope="client",
    )

    assert decision.allowed is False
    assert decision.reason == "health:down"


def test_resolve_tool_certification_decision_blocks_scope_mismatch(monkeypatch):
    monkeypatch.setattr(
        tool_certification_service,
        "_load_effective_registry",
        lambda _db: {"catalog.portfolio": _entry(allowed_scopes=("client",))},
    )

    decision = tool_certification_service.resolve_tool_certification_decision(
        Mock(),
        tool_action="catalog.portfolio",
        scope="branch",
    )

    assert decision.allowed is False
    assert decision.reason == "scope:branch"


def test_validate_tool_allow_tokens_for_scope_blocks_wildcard_with_uncertified(monkeypatch):
    monkeypatch.setattr(
        tool_certification_service,
        "_load_effective_registry",
        lambda _db: {
            "catalog.location": _entry(),
            "catalog.portfolio": _entry(certification_status="uncertified"),
        },
    )

    ok, error = tool_certification_service.validate_tool_allow_tokens_for_scope(
        Mock(),
        allow_tokens=["catalog.*"],
        scope="client",
    )

    assert ok is False
    assert "catalog.portfolio" in str(error)
    assert "certification:uncertified" in str(error)


def test_validate_tool_allow_tokens_for_scope_rejects_unknown_token(monkeypatch):
    monkeypatch.setattr(
        tool_certification_service,
        "_load_effective_registry",
        lambda _db: {"catalog.location": _entry()},
    )

    ok, error = tool_certification_service.validate_tool_allow_tokens_for_scope(
        Mock(),
        allow_tokens=["calendar.*"],
        scope="client",
    )

    assert ok is False
    assert "does not match known tool actions" in str(error)


def test_validate_tool_allow_tokens_for_scope_allows_certified_tools(monkeypatch):
    monkeypatch.setattr(
        tool_certification_service,
        "_load_effective_registry",
        lambda _db: {
            "calendar.list_slots": _entry(),
            "calendar.book_slot": _entry(),
        },
    )

    ok, error = tool_certification_service.validate_tool_allow_tokens_for_scope(
        Mock(),
        allow_tokens=["calendar.*"],
        scope="branch",
    )

    assert ok is True
    assert error is None


def test_default_tool_registry_matches_snapshot_actions() -> None:
    registry = tool_certification_service._build_default_registry()

    assert sorted(registry.keys()) == sorted(list_declared_tool_actions())
