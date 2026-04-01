from __future__ import annotations

from app.services import tool_registry_snapshot_service


def test_build_tool_registry_snapshot_is_versioned() -> None:
    snapshot = tool_registry_snapshot_service.build_tool_registry_snapshot()

    assert snapshot.schema_version == "tool_registry_snapshot.v1"
    assert snapshot.registry_version == "v1"
    assert "calendar.book_slot" in snapshot.entries
    assert "catalog.service_query" in snapshot.entries


def test_tool_registry_snapshot_exposes_binding_affordances() -> None:
    calendar_book = tool_registry_snapshot_service.resolve_tool_registry_entry("calendar.book_slot")
    catalog_location = tool_registry_snapshot_service.resolve_tool_registry_entry("catalog.location")

    assert calendar_book is not None
    assert calendar_book.accepts_service_query is True
    assert calendar_book.accepts_specialist_id is True
    assert calendar_book.accepts_customer_name is True
    assert calendar_book.accepts_customer_phone is True

    assert catalog_location is not None
    assert catalog_location.accepts_service_query is False


def test_tool_registry_snapshot_maps_policy_info_refs() -> None:
    assert tool_registry_snapshot_service.resolve_policy_info_tool_action("pricing") == "catalog.service_query"
    assert tool_registry_snapshot_service.resolve_policy_info_tool_action("hours") == "catalog.location"
    assert tool_registry_snapshot_service.resolve_policy_info_tool_action("missing") is None


def test_tool_registry_snapshot_exposes_ordered_policy_info_tool_candidates() -> None:
    assert tool_registry_snapshot_service.list_policy_info_tool_actions() == (
        "catalog.service_query",
        "catalog.location",
    )
