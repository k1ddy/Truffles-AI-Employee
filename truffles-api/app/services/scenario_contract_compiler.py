from __future__ import annotations

from typing import Any, Mapping

from app.services.expected_reply_contract import (
    EXPECTED_REPLY_TIME,
    normalize_expected_reply_type,
)
from app.services.interaction_owner_matrix_service import get_interaction_owner_row


_ACTIVE_TIME_SPECIALIST_FOLLOWUP_ROW_ID = "M31"


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    return cleaned or None


def _normalize_expect_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if not key:
            continue
        if isinstance(raw_value, (str, int, float, bool)) or raw_value is None:
            normalized[key] = raw_value
            continue
        if isinstance(raw_value, list):
            cleaned = [
                item
                for item in raw_value
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
            if cleaned:
                normalized[key] = cleaned
    return normalized


def _normalize_expect_contains_mapping(value: Any) -> dict[str, list[Any]]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, list[Any]] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            continue
        key = raw_key.strip()
        if not key:
            continue
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        cleaned = [
            item
            for item in values
            if isinstance(item, (str, int, float, bool)) or item is None
        ]
        if cleaned:
            normalized[key] = cleaned
    return normalized


def _normalize_expect_trace_contains(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        mapping = _normalize_expect_mapping(item)
        if mapping:
            normalized.append(mapping)
    return normalized


def _matrix_expected_reply_axes(row_id: str) -> dict[str, str]:
    row = get_interaction_owner_row(row_id)
    if not isinstance(row, Mapping):
        return {}
    semantic_axes = row.get("semantic_axes")
    if not isinstance(semantic_axes, Mapping):
        return {}
    return {
        "expected_reply_type": normalize_expected_reply_type(
            semantic_axes.get("expected_reply_type")
        )
        or EXPECTED_REPLY_TIME,
        "pending_question_target": _normalize_token(
            semantic_axes.get("pending_question_target")
        )
        or "specialist",
        "active_question_relation": _normalize_token(
            semantic_axes.get("active_question_relation")
        )
        or "referent_followup",
    }


def should_compile_active_time_specialist_followup_expectations(
    expectations: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(expectations, Mapping):
        return False
    if normalize_expected_reply_type(expectations.get("reply_type")) != EXPECTED_REPLY_TIME:
        return False
    meta_any = _normalize_expect_contains_mapping(expectations.get("meta_any"))
    trace_contains = _normalize_expect_trace_contains(expectations.get("trace_contains"))

    target_values = {
        _normalize_token(item)
        for item in meta_any.get("pending_question_target", [])
        if _normalize_token(item)
    }
    relation_values = {
        _normalize_token(item)
        for item in meta_any.get("active_question_relation", [])
        if _normalize_token(item)
    }

    for entry in trace_contains:
        stage = _normalize_token(entry.get("stage"))
        if stage != "pending_question_interaction":
            continue
        target = _normalize_token(entry.get("pending_question_target"))
        relation = _normalize_token(entry.get("active_question_relation"))
        if target:
            target_values.add(target)
        if relation:
            relation_values.add(relation)

    return "specialist" in target_values and "referent_followup" in relation_values


def compile_active_time_specialist_followup_expectations(
    expectations: Mapping[str, Any] | None,
) -> dict[str, Any]:
    compiled = dict(expectations or {})
    if not should_compile_active_time_specialist_followup_expectations(compiled):
        return compiled

    semantic_axes = _matrix_expected_reply_axes(_ACTIVE_TIME_SPECIALIST_FOLLOWUP_ROW_ID)
    expected_reply_type = semantic_axes["expected_reply_type"]

    compiled["reply_type"] = expected_reply_type
    compiled["expected_reply"] = True
    compiled["info_sections"] = []

    meta = _normalize_expect_mapping(compiled.get("meta"))
    if meta.get("expected_reply_type") is not None:
        meta["expected_reply_type"] = expected_reply_type
    if meta:
        compiled["meta"] = meta

    meta_any = _normalize_expect_contains_mapping(compiled.get("meta_any"))
    for stale_key in (
        "pending_question_act",
        "pending_question_interaction",
        "pending_question_owner",
        "booking_interrupt_info",
        "intent",
        "source",
    ):
        meta_any.pop(stale_key, None)
    meta_any["pending_question_target"] = [semantic_axes["pending_question_target"]]
    meta_any["active_question_relation"] = [semantic_axes["active_question_relation"]]
    meta_any["expected_reply_type"] = [expected_reply_type]
    compiled["meta_any"] = meta_any

    trace_contains: list[dict[str, Any]] = []
    for entry in _normalize_expect_trace_contains(compiled.get("trace_contains")):
        if _normalize_token(entry.get("stage")) == "pending_question_interaction":
            continue
        normalized_entry = dict(entry)
        if _normalize_token(normalized_entry.get("stage")) == "question_contract":
            normalized_entry["expected_reply_type"] = expected_reply_type
        trace_contains.append(normalized_entry)

    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": expected_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    compiled["trace_contains"] = trace_contains

    return compiled


__all__ = [
    "compile_active_time_specialist_followup_expectations",
    "should_compile_active_time_specialist_followup_expectations",
]
