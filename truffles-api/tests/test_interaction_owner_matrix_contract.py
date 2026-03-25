from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker, RefResolver


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_schema(relative_path: str) -> Draft202012Validator:
    schema_path = _repo_root() / relative_path
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(base_uri=schema_path.resolve().as_uri(), referrer=schema)
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _load_yaml(relative_path: str) -> dict:
    path = _repo_root() / relative_path
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_interaction_owner_matrix_yaml_matches_schema() -> None:
    payload = _load_yaml("truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml")
    _load_schema("contracts/policy/interaction_owner_matrix.v1.jsonschema").validate(payload)


def test_interaction_owner_matrix_freezes_current_remaining_rows() -> None:
    payload = _load_yaml("truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml")
    rows = payload["rows"]
    assert len(rows) == 41

    row_ids = [row["row_id"] for row in rows]
    assert len(set(row_ids)) == len(row_ids)

    assert payload["admission_rules"]["one_child_tp_per_row"] is True
    assert payload["admission_rules"]["child_tp_must_name_matrix_row"] is True

    open_rows = [row for row in rows if row["status"]["state"] == "open"]
    assert [row["row_id"] for row in open_rows] == []

    m19 = next(row for row in rows if row["row_id"] == "M19")
    assert m19["status"]["state"] == "closed_bounded"
    assert m19["status"]["child_tp_refs"] == ["P1.6o70", "P1.6o91"]
    assert m19["status"]["surfaced_by_runs"] == ["r96", "r116"]
    assert m19["semantic_axes"]["pending_question_target"] == "specialist"
    assert m19["semantic_axes"]["active_question_relation"] == "referent_followup"
    assert m19["semantic_axes"]["expected_reply_type"] == "time"
    assert "branch-catalog" in m19["allowed_degrade_raw"]

    m21 = next(row for row in rows if row["row_id"] == "M21")
    assert m21["status"]["state"] == "closed_bounded"
    assert m21["status"]["child_tp_refs"] == ["P1.6o72", "P1.6o116"]
    assert m21["status"]["surfaced_by_runs"] == ["r102", "r128"]
    assert m21["active_slot"] == "name"
    assert m21["semantic_axes"]["expected_reply_type"] == "name"
    assert m21["semantic_axes"]["pending_question_target"] == "time"
    assert m21["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m21["semantic_axes"]["subject_kind"] == "booking"
    assert m21["semantic_axes"]["capability"] == "live_availability"
    assert m21["semantic_axes"]["temporal_scope"] == "specific_time"
    assert m21["semantic_axes"]["resolution_mode"] == "referent_followup"
    assert m21["execution_owner"] == "active-name deictic time-availability follow-up owner"
    assert "stale `service_choice`" in m21["forbidden_compression_raw"]
    assert "P1.6o116" in m21["status"]["raw"]
    assert "P1.6o117" in m21["status"]["raw"]

    m27 = next(row for row in rows if row["row_id"] == "M27")
    assert m27["status"]["state"] == "closed_bounded"
    assert m27["status"]["child_tp_refs"] == ["P1.6o78", "P1.6o83", "P1.6o84"]
    assert m27["status"]["surfaced_by_runs"] == ["r112"]
    assert m27["semantic_axes"]["expected_reply_type"] == "time"
    assert m27["runtime_match"]["tool_action"] == "info"
    assert m27["runtime_match"]["expected_reply_reason"] == "booking_confirm_reject"
    assert m27["runtime_match"]["require_grounded_referents"] == ["service"]
    assert m27["runtime_effects"]["bypass_service_clarify"] is True
    assert m27["runtime_effects"]["carryover_grounded_referents"] == ["service"]
    assert m27["runtime_effects"]["preserve_expected_reply_type"] == "time"

    m28 = next(row for row in rows if row["row_id"] == "M28")
    assert m28["status"]["state"] == "closed_bounded"
    assert m28["status"]["child_tp_refs"] == ["P1.6o85"]
    assert m28["status"]["surfaced_by_runs"] == ["r113"]
    assert m28["active_slot"] == "time"
    assert m28["semantic_axes"]["expected_reply_type"] == "name"
    assert m28["execution_owner"] == "slot-compare explicit-time fill scenario-governance owner"

    m29 = next(row for row in rows if row["row_id"] == "M29")
    assert m29["status"]["state"] == "closed_bounded"
    assert m29["status"]["child_tp_refs"] == ["P1.6o87"]
    assert m29["status"]["surfaced_by_runs"] == ["r114"]
    assert m29["active_slot"] == "time"
    assert m29["semantic_axes"]["pending_question_target"] == "time"
    assert m29["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m29["semantic_axes"]["expected_reply_type"] == "time"
    assert m29["execution_owner"] == "booking-tag requested-slot scenario-governance owner"

    m30 = next(row for row in rows if row["row_id"] == "M30")
    assert m30["status"]["state"] == "closed_bounded"
    assert m30["status"]["child_tp_refs"] == ["P1.6o89"]
    assert m30["status"]["surfaced_by_runs"] == ["r115"]
    assert m30["active_slot"] == "time"
    assert m30["semantic_axes"]["pending_question_target"] == "time"
    assert m30["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m30["semantic_axes"]["expected_reply_type"] == "time"
    assert m30["execution_owner"] == "slot-constraint generic-slot-question scenario-governance owner"
    assert "reopened existing" in m30["status"]["raw"]

    m31 = next(row for row in rows if row["row_id"] == "M31")
    assert m31["status"]["state"] == "closed_bounded"
    assert m31["status"]["child_tp_refs"] == ["P1.6o93"]
    assert m31["status"]["surfaced_by_runs"] == ["r117"]
    assert m31["active_slot"] == "time"
    assert m31["semantic_axes"]["expected_reply_type"] == "time"
    assert m31["semantic_axes"]["pending_question_target"] == "specialist"
    assert m31["semantic_axes"]["active_question_relation"] == "referent_followup"
    assert m31["semantic_axes"]["resolution_mode"] == "referent_followup"
    assert m31["semantic_axes"]["next_question"] == "name"
    assert m31["execution_owner"] == "policy-core generic specialist-choice follow-up owner"
    assert "booking_info_contract/master" in m31["forbidden_compression_raw"]
    assert "r118" in m31["status"]["raw"]

    m32 = next(row for row in rows if row["row_id"] == "M32")
    assert m32["status"]["state"] == "closed_bounded"
    assert m32["status"]["child_tp_refs"] == ["P1.6o95"]
    assert m32["status"]["surfaced_by_runs"] == ["r118"]
    assert m32["active_slot"] == "name"
    assert m32["semantic_axes"]["expected_reply_type"] == "name"
    assert m32["semantic_axes"]["pending_question_target"] == "time"
    assert m32["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m32["semantic_axes"]["capability"] == "bookability"
    assert m32["semantic_axes"]["temporal_scope"] == "specific_time"
    assert m32["semantic_axes"]["resolution_mode"] == "referent_followup"
    assert m32["semantic_axes"]["next_question"] == "name"
    assert m32["execution_owner"] == "active-name deictic-day requested-slot follow-up owner"
    assert "question_contract:policy_core_degraded_collect" in m32["forbidden_compression_raw"]
    assert "r119" in m32["status"]["raw"]

    m33 = next(row for row in rows if row["row_id"] == "M33")
    assert m33["status"]["state"] == "closed_bounded"
    assert m33["status"]["child_tp_refs"] == ["P1.6o97"]
    assert m33["status"]["surfaced_by_runs"] == ["r119"]
    assert m33["active_slot"] == "name"
    assert m33["semantic_axes"]["expected_reply_type"] == "name"
    assert m33["semantic_axes"]["pending_question_target"] == "time"
    assert m33["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m33["semantic_axes"]["subject_kind"] == "service"
    assert m33["semantic_axes"]["capability"] == "pricing"
    assert m33["semantic_axes"]["resolution_mode"] == "direct"
    assert m33["semantic_axes"]["next_question"] == "name"
    assert m33["semantic_axes"]["open_questions"] == ["name"]
    assert m33["execution_owner"] == "active-name service-info interrupt owner"
    assert m33["runtime_match"]["tool_action"] == "catalog.service_query"
    assert m33["runtime_match"]["expected_reply_reason"] == "booking_time_availability_followup"
    assert m33["runtime_match"]["require_grounded_referents"] == ["service"]
    assert m33["runtime_effects"]["preserve_expected_reply_type"] == "name"
    assert m33["runtime_effects"]["reason_code"] == "owner_matrix_m33"
    assert "P1.6o98" in m33["status"]["raw"]

    m34 = next(row for row in rows if row["row_id"] == "M34")
    assert m34["status"]["state"] == "closed_bounded"
    assert m34["status"]["child_tp_refs"] == ["P1.6o99"]
    assert m34["status"]["surfaced_by_runs"] == ["r120"]
    assert m34["active_slot"] == "name"
    assert m34["semantic_axes"]["expected_reply_type"] == "name"
    assert m34["semantic_axes"]["pending_question_target"] == "specialist"
    assert m34["semantic_axes"]["active_question_relation"] == "referent_followup"
    assert m34["semantic_axes"]["subject_kind"] == "specialist"
    assert m34["semantic_axes"]["capability"] == "bookability"
    assert m34["semantic_axes"]["resolution_mode"] == "referent_followup"
    assert m34["semantic_axes"]["next_question"] == "name"
    assert m34["execution_owner"] == "active-name timeout specialist-choice follow-up owner"
    assert "policy_core_timeout_specialist_followup" in m34["allowed_degrade_raw"]
    assert "service_choice" in m34["forbidden_compression_raw"]
    assert "P1.6o100" in m34["status"]["raw"]

    m35 = next(row for row in rows if row["row_id"] == "M35")
    assert m35["status"]["state"] == "closed_bounded"
    assert m35["status"]["child_tp_refs"] == ["P1.6o101"]
    assert m35["status"]["surfaced_by_runs"] == ["r121"]
    assert m35["active_slot"] == "time"
    assert m35["semantic_axes"]["expected_reply_type"] == "time"
    assert m35["semantic_axes"]["pending_question_target"] == "time"
    assert m35["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m35["semantic_axes"]["subject_kind"] == "booking"
    assert m35["semantic_axes"]["capability"] == "live_availability"
    assert m35["semantic_axes"]["resolution_mode"] == "referent_followup"
    assert m35["semantic_axes"]["next_question"] == "datetime"
    assert m35["execution_owner"] == "slot-compare generic-slot-question scenario-governance owner"
    assert "ask_about_requested_slot(time)" in m35["allowed_degrade_raw"]
    assert "slot_compare(time)" in m35["forbidden_compression_raw"]
    assert "P1.6o102" in m35["status"]["raw"]

    m36 = next(row for row in rows if row["row_id"] == "M36")
    assert m36["status"]["state"] == "closed_bounded"
    assert m36["status"]["child_tp_refs"] == ["P1.6o103"]
    assert m36["status"]["surfaced_by_runs"] == ["r122"]
    assert m36["active_slot"] == "time"
    assert m36["semantic_axes"]["expected_reply_type"] == "name"
    assert m36["execution_owner"] == "grounded partial-date daypart fill scenario-governance owner"
    assert "time -> name" in m36["allowed_degrade_raw"]
    assert "mixed_fill_plus_question" in m36["forbidden_compression_raw"]
    assert "P1.6o104" in m36["status"]["raw"]

    m37 = next(row for row in rows if row["row_id"] == "M37")
    assert m37["status"]["state"] == "closed_bounded"
    assert m37["status"]["child_tp_refs"] == ["P1.6o105"]
    assert m37["status"]["surfaced_by_runs"] == ["r123"]
    assert m37["active_slot"] == "time"
    assert m37["semantic_axes"]["expected_reply_type"] == "time"
    assert m37["semantic_axes"]["subject_kind"] == "booking"
    assert m37["execution_owner"] == "timeout active-booking slot-fill follow-up owner"
    assert "slot-fill helpers" in m37["allowed_degrade_raw"]
    assert "pack_fact_fallback" in m37["forbidden_compression_raw"]
    assert "p1.6o106-l2-dev-20260312-a1-r1" in m37["status"]["raw"]
    assert "M38" in m37["status"]["raw"]

    m38 = next(row for row in rows if row["row_id"] == "M38")
    assert m38["status"]["state"] == "closed_bounded"
    assert m38["status"]["child_tp_refs"] == ["P1.6o107"]
    assert m38["status"]["surfaced_by_runs"] == ["r124"]
    assert m38["active_slot"] == "time"
    assert m38["semantic_axes"]["expected_reply_type"] == "time"
    assert m38["semantic_axes"]["pending_question_target"] == "specialist"
    assert m38["semantic_axes"]["active_question_relation"] == "specialist_availability_interrupt"
    assert m38["semantic_axes"]["subject_kind"] == "specialist"
    assert m38["execution_owner"] == "active-time timeout generic specialist-choice follow-up owner"
    assert "timeout specialist-target interrupt reply" in m38["allowed_degrade_raw"]
    assert "policy_core_timeout_degrade_booking_limit" in m38["forbidden_compression_raw"]
    assert "P1.6o107" in m38["status"]["raw"]
    assert "p1.6o108-l2-dev-20260312-a1-r1" in m38["status"]["raw"]
    assert "M39" in m38["status"]["raw"]

    m39 = next(row for row in rows if row["row_id"] == "M39")
    assert m39["status"]["state"] == "closed_bounded"
    assert m39["status"]["child_tp_refs"] == ["P1.6o109"]
    assert m39["status"]["surfaced_by_runs"] == ["r125"]
    assert m39["active_slot"] == "time"
    assert m39["semantic_axes"]["expected_reply_type"] == "time"
    assert m39["semantic_axes"]["subject_kind"] == "service"
    assert m39["semantic_axes"]["capability"] == "other"
    assert m39["semantic_axes"]["resolution_mode"] == "clarify_missing_subject"
    assert m39["execution_owner"] == "active-time services-overview interrupt owner"
    assert "catalog.service_query" in m39["allowed_degrade_raw"]
    assert "service_choice" in m39["forbidden_compression_raw"]
    assert "P1.6o109" in m39["status"]["raw"]
    assert "p1.6o110-l2-dev-20260312-a1-r1" in m39["status"]["raw"]
    assert "M40" in m39["status"]["raw"]

    m40 = next(row for row in rows if row["row_id"] == "M40")
    assert m40["status"]["state"] == "closed_bounded"
    assert m40["status"]["child_tp_refs"] == ["P1.6o111"]
    assert m40["status"]["surfaced_by_runs"] == ["r126"]
    assert m40["active_slot"] == "time"
    assert m40["semantic_axes"]["expected_reply_type"] == "name"
    assert m40["semantic_axes"]["pending_question_target"] == "time"
    assert m40["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m40["semantic_axes"]["subject_kind"] == "booking"
    assert m40["semantic_axes"]["temporal_scope"] == "specific_day"
    assert m40["execution_owner"] == "active-time partial-date fill degraded-collect scenario-governance owner"
    assert "time -> name" in m40["allowed_degrade_raw"]
    assert "policy_core_degraded_collect" in m40["forbidden_compression_raw"]
    assert "P1.6o111" in m40["status"]["raw"]
    assert "P1.6o112" in m40["status"]["raw"]

    m41 = next(row for row in rows if row["row_id"] == "M41")
    assert m41["status"]["state"] == "closed_bounded"
    assert m41["status"]["child_tp_refs"] == ["P1.6o114"]
    assert m41["status"]["surfaced_by_runs"] == ["r127"]
    assert m41["active_slot"] == "time"
    assert m41["semantic_axes"]["expected_reply_type"] == "time"
    assert m41["semantic_axes"]["pending_question_target"] == "time"
    assert m41["semantic_axes"]["active_question_relation"] == "ask_about_requested_slot"
    assert m41["semantic_axes"]["subject_kind"] == "booking"
    assert m41["semantic_axes"]["resolution_mode"] == "clarify_missing_time"
    assert m41["semantic_axes"]["next_question"] == "datetime"
    assert m41["execution_owner"] == "active-time time-preference timeout guidance owner"
    assert "booking_slot_guidance" in m41["allowed_degrade_raw"]
    assert "truth_gate service_duration" in m41["forbidden_compression_raw"]
    assert "P1.6o114" in m41["status"]["raw"]
    assert "P1.6o115" in m41["status"]["raw"]

    m7 = next(row for row in rows if row["row_id"] == "M7")
    assert "booking_info_contract/master" in m7["forbidden_compression_raw"]
