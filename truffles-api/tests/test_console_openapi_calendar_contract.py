from pathlib import Path

import yaml


def _load_console_contract() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    contract_path = repo_root / "contracts" / "console_api" / "openapi.v1.yaml"
    return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}


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
        assert path in paths, f"missing path in console contract: {path}"
        available_ops = {key for key in (paths.get(path) or {}).keys() if isinstance(key, str)}
        for method in required_ops:
            assert method in available_ops, f"missing operation {method.upper()} {path}"


def test_calendar_schemas_are_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    required_schemas = {
        "SpecialistServicePayload",
        "SpecialistCreate",
        "SpecialistUpdate",
        "SpecialistResponse",
        "SpecialistsResponse",
        "SlotResponse",
        "SlotsResponse",
        "BookingCreate",
        "BookingStatusUpdateRequest",
        "BookingNoShowFollowUpRequest",
        "BookingResponse",
        "BookingActionResponse",
        "BookingsListResponse",
        "GoogleStatusResponse",
    }

    for schema_name in required_schemas:
        assert schema_name in schemas, f"missing schema in console contract: {schema_name}"


def test_booking_status_update_contract_uses_simple_terminal_statuses() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    booking_status_schema = schemas.get("BookingStatusUpdateRequest") or {}
    status_schema = (booking_status_schema.get("properties") or {}).get("status") or {}

    assert status_schema.get("enum") == ["COMPLETED", "NO_SHOW"]
