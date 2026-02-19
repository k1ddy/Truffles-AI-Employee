from pathlib import Path

import yaml


def _load_console_contract() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "contracts" / "console_api" / "openapi.v1.yaml"
    return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}


def _find_path(paths: dict, path: str) -> dict | None:
    legacy = path
    prefixed = f"/console/v1{path}"
    if legacy in paths:
        return paths.get(legacy)
    if prefixed in paths:
        return paths.get(prefixed)
    return None


def _has_string_type(schema: dict) -> bool:
    if schema.get("type") == "string":
        return True
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return False
    return any(isinstance(item, dict) and item.get("type") == "string" for item in any_of)


def test_calendar_paths_are_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}

    expected_methods = {
        "/calendar/specialists": {"get", "post"},
        "/calendar/specialists/{specialist_id}": {"patch"},
        "/calendar/specialists/{specialist_id}/enable": {"post"},
        "/calendar/specialists/{specialist_id}/disable": {"post"},
        "/calendar/slots": {"get"},
        "/calendar/bookings": {"get", "post"},
        "/calendar/bookings/{booking_id}/cancel": {"post"},
        "/calendar/bookings/{booking_id}/status": {"post"},
        "/calendar/bookings/{booking_id}/no-show-followup": {"post"},
        "/calendar/google/connect": {"get"},
        "/calendar/google/callback": {"get"},
        "/calendar/google/status": {"get"},
    }

    for path, required_ops in expected_methods.items():
        path_item = _find_path(paths, path)
        assert path_item is not None, f"missing path in console contract: {path}"
        available_ops = {key for key in (path_item or {}).keys() if isinstance(key, str)}
        for method in required_ops:
            assert method in available_ops, f"missing operation {method.upper()} {path}"


def test_calendar_schemas_are_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    required_schema_aliases = [
        ("SpecialistServicePayload",),
        ("SpecialistCreate",),
        ("SpecialistUpdate",),
        ("SpecialistResponse",),
        ("SpecialistsResponse",),
        ("SlotResponse",),
        ("SlotsResponse",),
        ("BookingCreate",),
        ("BookingStatusUpdateRequest",),
        ("BookingNoShowFollowUpRequest",),
        ("BookingResponse",),
        ("BookingActionResponse",),
        ("BookingsListResponse",),
    ]
    for aliases in required_schema_aliases:
        assert any(name in schemas for name in aliases), (
            f"missing schema in console contract: one of {aliases}"
        )


def test_booking_status_update_contract_uses_simple_terminal_statuses() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    booking_status_schema = schemas.get("BookingStatusUpdateRequest") or {}
    status_schema = (booking_status_schema.get("properties") or {}).get("status") or {}
    status_enum = status_schema.get("enum")
    if isinstance(status_enum, list):
        assert status_enum == ["COMPLETED", "NO_SHOW"]
    else:
        assert status_schema.get("type") == "string"


def test_booking_response_contract_exposes_no_show_followup_flag() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    booking_response = schemas.get("BookingResponse") or {}
    properties = booking_response.get("properties") or {}

    assert "no_show_followup_done" in properties
    assert (properties.get("no_show_followup_done") or {}).get("type") == "boolean"

    assert "no_show_followup_result" in properties
    assert _has_string_type(properties.get("no_show_followup_result") or {})
    assert "no_show_followup_closed_at" in properties
    assert _has_string_type(properties.get("no_show_followup_closed_at") or {})
    assert "no_show_followup_closed_by" in properties
    assert _has_string_type(properties.get("no_show_followup_closed_by") or {})
    assert "no_show_followup_rebooked_appointment_id" in properties
    assert _has_string_type(properties.get("no_show_followup_rebooked_appointment_id") or {})


def test_no_show_followup_request_contract_exposes_result_and_rebook_link() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    followup_schema = schemas.get("BookingNoShowFollowUpRequest") or {}
    properties = followup_schema.get("properties") or {}

    assert (properties.get("result") or {}).get("enum") == ["contacted", "rebooked"]
    assert _has_string_type(properties.get("rebooked_appointment_id") or {})
