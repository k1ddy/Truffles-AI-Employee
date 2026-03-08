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


def _has_integer_type(schema: dict) -> bool:
    if schema.get("type") == "integer":
        return True
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return False
    return any(isinstance(item, dict) and item.get("type") == "integer" for item in any_of)


def test_calendar_paths_are_present_in_console_openapi_contract() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}

    expected_methods = {
        "/queue-state/current": {"get", "put"},
        "/queue-state/views": {"get", "post"},
        "/queue-state/views/{view_id}": {"get", "patch", "delete"},
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
        ("BookingCaseEffect",),
        ("BookingActionResponse",),
        ("BookingsListResponse",),
        ("ConsoleQueueStateCurrentRequest",),
        ("ConsoleQueueStateCurrentResponse",),
        ("ConsoleSavedView",),
        ("ConsoleSavedViewListResponse",),
        ("ConsoleSavedViewCreateRequest",),
        ("ConsoleSavedViewUpdateRequest",),
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
    assert "conversation_id" in properties
    assert _has_string_type(properties.get("conversation_id") or {})
    assert "case_id" in properties
    assert _has_string_type(properties.get("case_id") or {})
    assert "needs_action" in properties
    assert (properties.get("needs_action") or {}).get("type") == "boolean"
    assert "attention_reason" in properties
    assert _has_string_type(properties.get("attention_reason") or {})


def test_booking_action_response_contract_exposes_case_effects() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    booking_action = schemas.get("BookingActionResponse") or {}
    action_props = booking_action.get("properties") or {}

    assert "case_effects" in action_props
    case_effects_schema = action_props.get("case_effects") or {}
    assert case_effects_schema.get("type") == "array"

    effect_schema = schemas.get("BookingCaseEffect") or {}
    effect_props = effect_schema.get("properties") or {}
    assert "case_id" in effect_props
    assert _has_string_type(effect_props.get("case_id") or {})
    assert "action" in effect_props
    assert _has_string_type(effect_props.get("action") or {})
    assert "message" in effect_props
    assert _has_string_type(effect_props.get("message") or {})


def test_calendar_bookings_list_contract_exposes_conversation_filter() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/calendar/bookings") or {}
    get_op = path_item.get("get") or {}
    params = get_op.get("parameters") or []
    assert any((param or {}).get("name") == "conversation_id" for param in params)
    assert any((param or {}).get("name") == "case_id" for param in params)
    assert any((param or {}).get("name") == "lane" for param in params)
    assert any((param or {}).get("name") == "needs_action" for param in params)
    assert any((param or {}).get("name") == "cursor" for param in params)


def test_queue_state_current_contract_exposes_surface_and_scope_params() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/queue-state/current") or {}
    get_op = path_item.get("get") or {}
    put_op = path_item.get("put") or {}

    get_params = get_op.get("parameters") or []
    assert any((param or {}).get("name") == "surface" for param in get_params)
    assert any((param or {}).get("name") == "case_id" for param in get_params)
    assert any((param or {}).get("name") == "conversation_id" for param in get_params)

    request_body = (put_op.get("requestBody") or {}).get("content", {}).get("application/json", {})
    request_schema = request_body.get("schema") or {}
    schema_ref = request_schema.get("$ref", "")
    assert schema_ref.endswith("/ConsoleQueueStateCurrentRequest")

    success_schema = (
        (((put_op.get("responses") or {}).get("200") or {}).get("content") or {})
        .get("application/json", {})
        .get("schema")
        or {}
    )
    assert (success_schema.get("$ref") or "").endswith("/ConsoleQueueStateCurrentResponse")


def test_queue_state_current_response_contract_exposes_restore_payload() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    queue_state_response = schemas.get("ConsoleQueueStateCurrentResponse") or {}
    properties = queue_state_response.get("properties") or {}

    assert "found" in properties
    assert (properties.get("found") or {}).get("type") == "boolean"
    assert "surface" in properties
    assert _has_string_type(properties.get("surface") or {})
    assert "selected_branch_id" in properties
    assert _has_string_type(properties.get("selected_branch_id") or {})
    assert "case_id" in properties
    assert _has_string_type(properties.get("case_id") or {})
    assert "conversation_id" in properties
    assert _has_string_type(properties.get("conversation_id") or {})
    assert "version" in properties
    assert _has_integer_type(properties.get("version") or {})
    assert "query_state" in properties
    assert (properties.get("query_state") or {}).get("type") == "object"
    assert "updated_at" in properties
    assert _has_string_type(properties.get("updated_at") or {})


def test_queue_state_saved_views_contract_exposes_catalog_payload() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    saved_view_schema = schemas.get("ConsoleSavedView") or {}
    properties = saved_view_schema.get("properties") or {}

    assert "id" in properties
    assert _has_string_type(properties.get("id") or {})
    assert "surface" in properties
    assert _has_string_type(properties.get("surface") or {})
    assert "scope" in properties
    assert _has_string_type(properties.get("scope") or {})
    assert "name" in properties
    assert _has_string_type(properties.get("name") or {})
    assert "version" in properties
    assert _has_integer_type(properties.get("version") or {})
    assert "query_state" in properties
    assert (properties.get("query_state") or {}).get("type") == "object"
    assert "is_default" in properties
    assert (properties.get("is_default") or {}).get("type") == "boolean"
    assert "is_applicable" in properties
    assert (properties.get("is_applicable") or {}).get("type") == "boolean"
    assert "created_by_agent_id" in properties
    assert _has_string_type(properties.get("created_by_agent_id") or {})
    assert "target_branch_id" in properties
    assert _has_string_type(properties.get("target_branch_id") or {})
    assert "target_role" in properties
    assert _has_string_type(properties.get("target_role") or {})


def test_queue_state_saved_view_mutation_contract_exposes_managed_scope_fields() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    create_schema = schemas.get("ConsoleSavedViewCreateRequest") or {}
    create_props = create_schema.get("properties") or {}
    assert "scope" in create_props
    assert _has_string_type(create_props.get("scope") or {})
    assert "target_branch_id" in create_props
    assert _has_string_type(create_props.get("target_branch_id") or {})
    assert "target_role" in create_props
    assert _has_string_type(create_props.get("target_role") or {})

    update_schema = schemas.get("ConsoleSavedViewUpdateRequest") or {}
    update_props = update_schema.get("properties") or {}
    assert "target_branch_id" in update_props
    assert _has_string_type(update_props.get("target_branch_id") or {})
    assert "target_role" in update_props
    assert _has_string_type(update_props.get("target_role") or {})


def test_bookings_list_response_contract_exposes_cursor_and_has_more() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    bookings_list_schema = schemas.get("BookingsListResponse") or {}
    properties = bookings_list_schema.get("properties") or {}

    assert "items" in properties
    assert "cursor" in properties
    assert _has_string_type(properties.get("cursor") or {})
    assert "has_more" in properties
    assert (properties.get("has_more") or {}).get("type") == "boolean"


def test_console_case_contract_exposes_action_sla_fields() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    case_schema = schemas.get("ConsoleCase") or {}
    properties = case_schema.get("properties") or {}

    assert "sla_status" in properties
    assert _has_string_type(properties.get("sla_status") or {})
    assert "sla_action_state" in properties
    assert _has_string_type(properties.get("sla_action_state") or {})
    assert "sla_overdue_minutes" in properties
    assert _has_integer_type(properties.get("sla_overdue_minutes") or {})
    assert "target_response_at" in properties
    assert _has_string_type(properties.get("target_response_at") or {})
    assert "assigned_to_id" in properties
    assert _has_string_type(properties.get("assigned_to_id") or {})
    assert "business_status_code" in properties
    assert _has_string_type(properties.get("business_status_code") or {})
    assert "business_status_label" in properties
    assert _has_string_type(properties.get("business_status_label") or {})
    assert "snoozed_until" in properties
    assert _has_string_type(properties.get("snoozed_until") or {})
    assert "snoozed_reason" in properties
    assert _has_string_type(properties.get("snoozed_reason") or {})
    assert "snoozed_by" in properties
    assert _has_string_type(properties.get("snoozed_by") or {})
    assert "booking_summary" in properties

    booking_summary_schema = schemas.get("ConsoleCaseBookingSummary") or {}
    booking_summary_props = booking_summary_schema.get("properties") or {}
    assert "booking_id" in booking_summary_props
    assert _has_string_type(booking_summary_props.get("booking_id") or {})
    assert "status" in booking_summary_props
    assert _has_string_type(booking_summary_props.get("status") or {})
    assert "start_at" in booking_summary_props
    assert _has_string_type(booking_summary_props.get("start_at") or {})
    assert "operator_summary" in booking_summary_props
    assert _has_string_type(booking_summary_props.get("operator_summary") or {})
    assert "needs_action" in booking_summary_props
    assert (booking_summary_props.get("needs_action") or {}).get("type") == "boolean"


def test_console_case_action_paths_expose_wave6_single_case_actions() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}

    assert _find_path(paths, "/cases/bulk") is not None
    assert "post" in ((_find_path(paths, "/cases/bulk") or {}).keys())
    assert _find_path(paths, "/cases/assignees") is not None
    assert "get" in ((_find_path(paths, "/cases/assignees") or {}).keys())
    assert _find_path(paths, "/cases/{case_id}/assignees") is not None
    assert "get" in ((_find_path(paths, "/cases/{case_id}/assignees") or {}).keys())
    assert _find_path(paths, "/cases/{case_id}/reassign") is not None
    assert "post" in ((_find_path(paths, "/cases/{case_id}/reassign") or {}).keys())
    assert _find_path(paths, "/cases/{case_id}/snooze") is not None
    assert "post" in ((_find_path(paths, "/cases/{case_id}/snooze") or {}).keys())
    assert _find_path(paths, "/cases/{case_id}/reopen") is not None
    assert "post" in ((_find_path(paths, "/cases/{case_id}/reopen") or {}).keys())


def test_console_cases_list_contract_exposes_queue_view_param() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/cases") or {}
    get_op = path_item.get("get") or {}
    params = get_op.get("parameters") or []
    queue_view_param = next(
        ((param or {}) for param in params if (param or {}).get("name") == "queue_view"),
        None,
    )

    assert queue_view_param is not None
    schema = (queue_view_param.get("schema") or {})
    assert _has_string_type(schema)


def test_console_cases_list_contract_exposes_history_params() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/cases") or {}
    get_op = path_item.get("get") or {}
    params = get_op.get("parameters") or []

    assert any((param or {}).get("name") == "resolved_from" for param in params)
    assert any((param or {}).get("name") == "resolved_to" for param in params)


def test_console_case_action_schemas_expose_wave6_requests_and_assignees() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    bulk_request_schema = schemas.get("ConsoleCaseBulkActionRequest") or {}
    bulk_request_props = bulk_request_schema.get("properties") or {}
    assert (bulk_request_props.get("action") or {}).get("enum") == ["reassign", "snooze", "route"]
    assert "case_ids" in bulk_request_props
    assert "agent_id" in bulk_request_props
    assert _has_string_type(bulk_request_props.get("agent_id") or {})
    assert "policy" in bulk_request_props
    assert (bulk_request_props.get("policy") or {}).get("anyOf") == [
        {"const": "least_open_cases"},
        {"type": "null"},
    ]
    assert "minutes" in bulk_request_props
    assert _has_integer_type(bulk_request_props.get("minutes") or {})
    assert "reason" in bulk_request_props
    assert _has_string_type(bulk_request_props.get("reason") or {})

    bulk_result_schema = schemas.get("ConsoleCaseBulkActionResult") or {}
    bulk_result_props = bulk_result_schema.get("properties") or {}
    assert (bulk_result_props.get("status") or {}).get("enum") == ["processed", "skipped", "failed"]
    assert _has_string_type(bulk_result_props.get("code") or {})
    assert "routing" in bulk_result_props

    bulk_response_schema = schemas.get("ConsoleCaseBulkActionResponse") or {}
    bulk_response_props = bulk_response_schema.get("properties") or {}
    assert (bulk_response_props.get("success") or {}).get("type") == "boolean"
    assert _has_integer_type(bulk_response_props.get("processed_count") or {})
    assert _has_integer_type(bulk_response_props.get("skipped_count") or {})
    assert _has_integer_type(bulk_response_props.get("failed_count") or {})

    assignee_schema = schemas.get("ConsoleCaseAssigneeOption") or {}
    assignee_props = assignee_schema.get("properties") or {}
    assert "agent_id" in assignee_props
    assert _has_string_type(assignee_props.get("agent_id") or {})
    assert "agent_name" in assignee_props
    assert _has_string_type(assignee_props.get("agent_name") or {})
    assert "is_current" in assignee_props
    assert (assignee_props.get("is_current") or {}).get("type") == "boolean"
    assert "open_case_count" in assignee_props
    assert _has_integer_type(assignee_props.get("open_case_count") or {})

    assignee_list_schema = schemas.get("ConsoleCaseAssigneeListResponse") or {}
    assignee_list_props = assignee_list_schema.get("properties") or {}
    assert "items" in assignee_list_props
    assert "routing" in assignee_list_props

    routing_schema = schemas.get("ConsoleCaseRoutingDecision") or {}
    routing_props = routing_schema.get("properties") or {}
    assert (routing_props.get("policy") or {}).get("const") == "least_open_cases"
    assert _has_string_type(routing_props.get("recommended_agent_id") or {})
    assert _has_string_type(routing_props.get("recommended_agent_name") or {})
    assert _has_integer_type(routing_props.get("recommended_open_case_count") or {})
    assert (routing_props.get("will_reassign") or {}).get("type") == "boolean"
    assert _has_string_type(routing_props.get("reason_code") or {})
    assert _has_string_type(routing_props.get("reason_summary") or {})

    reassign_schema = schemas.get("ConsoleCaseReassignRequest") or {}
    reassign_props = reassign_schema.get("properties") or {}
    assert _has_string_type(reassign_props.get("agent_id") or {})
    assert (reassign_props.get("mode") or {}).get("enum") == ["manual", "policy"]
    assert (reassign_props.get("policy") or {}).get("anyOf") == [
        {"const": "least_open_cases"},
        {"type": "null"},
    ]

    action_response_schema = schemas.get("ConsoleCaseActionResponse") or {}
    assert "routing" in (action_response_schema.get("properties") or {})

    snooze_schema = schemas.get("ConsoleCaseSnoozeRequest") or {}
    snooze_props = snooze_schema.get("properties") or {}
    assert _has_integer_type(snooze_props.get("minutes") or {})
    assert _has_string_type(snooze_props.get("reason") or {})


def test_console_case_list_contract_exposes_owner_filters() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    path_item = _find_path(paths, "/cases") or {}
    get_op = path_item.get("get") or {}
    params = get_op.get("parameters") or []

    assert any((param or {}).get("name") == "assignee_id" for param in params)
    assert any((param or {}).get("name") == "unassigned" for param in params)


def test_console_macro_contract_exposes_action_macros_and_execute_path() -> None:
    spec = _load_console_contract()
    paths = spec.get("paths") or {}
    schemas = ((spec.get("components") or {}).get("schemas")) or {}

    execute_path = _find_path(paths, "/inbox/macros/{macro_id}/execute") or {}
    assert "post" in execute_path

    macro_schema = schemas.get("ConsoleMacro") or {}
    macro_props = macro_schema.get("properties") or {}
    assert "action" in macro_props

    macro_action_schema = schemas.get("ConsoleMacroAction") or {}
    macro_action_props = macro_action_schema.get("properties") or {}
    assert (macro_action_props.get("type") or {}).get("enum") == [
        "take_case",
        "resolve_case",
        "return_to_bot",
        "reopen_case",
        "snooze_case",
    ]
    assert _has_integer_type(macro_action_props.get("minutes") or {})
    assert _has_string_type(macro_action_props.get("reason") or {})

    macro_create_schema = schemas.get("ConsoleMacroCreateRequest") or {}
    assert "action" in (macro_create_schema.get("properties") or {})

    macro_update_schema = schemas.get("ConsoleMacroUpdateRequest") or {}
    assert "action" in (macro_update_schema.get("properties") or {})

    execute_request_schema = schemas.get("ConsoleMacroExecuteRequest") or {}
    assert _has_string_type(((execute_request_schema.get("properties") or {}).get("case_id") or {}))

    execute_response_schema = schemas.get("ConsoleMacroExecuteResponse") or {}
    execute_response_props = execute_response_schema.get("properties") or {}
    assert (execute_response_props.get("success") or {}).get("type") == "boolean"
    assert "macro" in execute_response_props
    assert "case" in execute_response_props
    assert "sync" in execute_response_props


def test_no_show_followup_request_contract_exposes_result_and_rebook_link() -> None:
    spec = _load_console_contract()
    schemas = ((spec.get("components") or {}).get("schemas")) or {}
    followup_schema = schemas.get("BookingNoShowFollowUpRequest") or {}
    properties = followup_schema.get("properties") or {}

    assert (properties.get("result") or {}).get("enum") == ["contacted", "rebooked"]
    assert _has_string_type(properties.get("rebooked_appointment_id") or {})
