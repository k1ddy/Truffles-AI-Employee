from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.routers.webhook import decision as decision_router
from app.schemas.webhook import WebhookRequest
from app.services.policy_validation_boundary_service import (
    build_policy_validation_booking_recovery,
)


_PENDING_BOOKING_REACTIVATION_REPLY_BY_SLOT = {
    "service": decision_router.EXPECTED_REPLY_SERVICE,
    "datetime": decision_router.EXPECTED_REPLY_TIME,
    "name": decision_router.EXPECTED_REPLY_NAME,
    "phone": decision_router.EXPECTED_REPLY_PHONE,
}


def _build_booking_prompt_slot_values(
    booking_state: dict[str, object] | None,
) -> dict[str, str]:
    if not isinstance(booking_state, dict):
        return {}
    normalized: dict[str, str] = {}
    for slot_key in ("service", "datetime", "name", "phone"):
        value = booking_state.get(slot_key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            normalized[slot_key] = cleaned
    return normalized


def resolve_initial_booking_timeout_collect_candidate(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    now: datetime,
) -> dict[str, object] | None:
    if not isinstance(message_text, str) or not message_text.strip():
        return None
    if not decision_router._is_booking_request(
        message_text,
        client_slug=payload.client_slug,
    ):
        return None

    parsed_booking_state = decision_router._update_booking_from_messages(
        {
            "active": True,
            "started_at": now.isoformat(),
        },
        [message_text],
        client_slug=payload.client_slug,
    )
    collect_slot = decision_router._first_missing_booking_slot(
        parsed_booking_state,
        client_slug=payload.client_slug,
    )
    if collect_slot not in {"datetime", "name"}:
        return None

    service_value = parsed_booking_state.get("service")
    normalized_service = (
        service_value.strip()
        if isinstance(service_value, str) and service_value.strip()
        else None
    )
    if normalized_service is None:
        return None

    slot_values: dict[str, str] = {
        "service": normalized_service,
    }
    if collect_slot == "name":
        datetime_value = parsed_booking_state.get("datetime")
        normalized_datetime = (
            datetime_value.strip()
            if isinstance(datetime_value, str) and datetime_value.strip()
            else None
        )
        if normalized_datetime is None:
            return None
        slot_values["datetime"] = normalized_datetime

    return {
        "collect_slot": collect_slot,
        "reason": "booking_prompt",
        "slot_values": slot_values,
        "seed_booking_state": dict(parsed_booking_state),
    }


def _build_pending_booking_reactivation_seed(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    booking_state: dict[str, object] | None,
    context: dict[str, object],
    now: datetime,
) -> tuple[dict[str, object], str | None] | None:
    boundary_payload = decision_router._derive_pending_booking_resume_boundary_payload(
        context,
        now=now,
    )
    boundary_booking_state = (
        boundary_payload.get("booking_state")
        if isinstance(boundary_payload, dict)
        else None
    )
    boundary_resume_slot = (
        boundary_payload.get("resume_slot")
        if isinstance(boundary_payload, dict)
        else None
    )
    seed_booking_state: dict[str, object] = {}
    for source in (boundary_booking_state, booking_state):
        if not isinstance(source, dict):
            continue
        if source.get("active") is True:
            seed_booking_state["active"] = True
        for key, value in _build_booking_prompt_slot_values(source).items():
            seed_booking_state.setdefault(key, value)
        started_at = source.get("started_at")
        if (
            "started_at" not in seed_booking_state
            and isinstance(started_at, str)
            and started_at.strip()
        ):
            seed_booking_state["started_at"] = started_at.strip()
        last_question = source.get("last_question")
        if (
            "last_question" not in seed_booking_state
            and isinstance(last_question, str)
            and last_question.strip()
        ):
            seed_booking_state["last_question"] = last_question.strip()

    has_booking_memory = bool(_build_booking_prompt_slot_values(seed_booking_state))
    has_resume_boundary = isinstance(boundary_payload, dict)
    if not (
        has_resume_boundary
        or has_booking_memory
        or decision_router._is_booking_request(
            message_text,
            client_slug=payload.client_slug,
        )
    ):
        return None

    if seed_booking_state.get("active") is not True:
        seed_booking_state["active"] = True
        seed_booking_state.setdefault("started_at", now.isoformat())

    if (
        isinstance(boundary_resume_slot, str)
        and boundary_resume_slot.strip() in decision_router.BOOKING_SLOT_ORDER
    ):
        resume_slot = boundary_resume_slot.strip()
    else:
        resume_slot = decision_router._first_missing_booking_slot(
            seed_booking_state,
            client_slug=payload.client_slug,
        )
    if resume_slot not in _PENDING_BOOKING_REACTIVATION_REPLY_BY_SLOT:
        return None
    return seed_booking_state, _PENDING_BOOKING_REACTIVATION_REPLY_BY_SLOT[resume_slot]


def resolve_llm_booking_prompt_candidate(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    reply_slot: str | None,
    current_goal: str | None,
    booking_state: dict[str, object] | None,
    context: dict[str, object],
    now: datetime,
    allow_initial_slot_progression: bool = False,
    allow_timeout_recovery: bool = False,
    route_llm_policy_core_fn: Callable[..., dict[str, Any]],
    initial_booking_policy_core_max_tokens: int | None = None,
) -> dict[str, object] | None:
    if not isinstance(message_text, str) or not message_text.strip():
        return None

    def _normalize_token(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned.casefold() if cleaned else None

    context_manager = decision_router._get_context_manager(context)
    semantic_booking_state = dict(booking_state) if isinstance(booking_state, dict) else {}
    fresh_initial_booking_entry = (
        allow_initial_slot_progression
        and allow_timeout_recovery
        and reply_slot is None
        and current_goal is None
        and not _build_booking_prompt_slot_values(semantic_booking_state)
    )
    if not semantic_booking_state.get("service"):
        service_hint = None
        if fresh_initial_booking_entry:
            service_hint = decision_router._extract_service_hint(
                message_text,
                payload.client_slug,
            )
        if not (isinstance(service_hint, str) and service_hint.strip()):
            service_hint = decision_router._get_recent_service_hint(context, now)
        if isinstance(service_hint, str) and service_hint.strip():
            semantic_booking_state["service"] = service_hint.strip()
        elif isinstance(context_manager, dict):
            raw_message_count = context_manager.get("message_count")
            try:
                message_count = max(int(raw_message_count), 0)
            except (TypeError, ValueError):
                message_count = 0
            carryover = decision_router._get_service_carryover(
                context_manager,
                message_count=message_count,
            )
            if isinstance(carryover, dict):
                service_query = carryover.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    semantic_booking_state["service"] = service_query.strip()

    policy_slot_state = _build_booking_prompt_slot_values(semantic_booking_state)
    policy_memory_summary = None
    compact_summary = context_manager.get("compact_summary") if isinstance(context_manager, dict) else None
    if isinstance(compact_summary, dict):
        summary_text = compact_summary.get("text")
        if isinstance(summary_text, str) and summary_text.strip():
            policy_memory_summary = summary_text.strip()

    policy_memory_profile = None
    active_slots = decision_router._collect_policy_active_slots(
        primary_slot_state=policy_slot_state,
        fallback_slot_state=None,
        client_slug=payload.client_slug,
    )
    if reply_slot in {
        decision_router.EXPECTED_REPLY_SERVICE,
        decision_router.EXPECTED_REPLY_TIME,
        decision_router.EXPECTED_REPLY_NAME,
    } or active_slots:
        policy_memory_profile = {}
        if reply_slot in {
            decision_router.EXPECTED_REPLY_SERVICE,
            decision_router.EXPECTED_REPLY_TIME,
            decision_router.EXPECTED_REPLY_NAME,
        }:
            policy_memory_profile["expected_reply_type"] = reply_slot
        if active_slots:
            policy_memory_profile["active_slots"] = active_slots

    consult_refs, _ = decision_router._collect_plan_consult_refs(payload.client_slug)
    policy_info_refs = [] if fresh_initial_booking_entry else sorted(decision_router.INFO_INTENTS)
    # Fresh initial booking entry already owns the collect contract; keep the
    # policy-core envelope booking-only instead of exposing broader consult refs.
    policy_consult_refs = [] if fresh_initial_booking_entry else consult_refs
    policy_core_kwargs = {
        "expected_reply_type": reply_slot,
        "current_goal": current_goal,
        "slot_state": policy_slot_state,
        "info_refs": policy_info_refs,
        "consult_refs": policy_consult_refs,
        "memory_summary": policy_memory_summary,
        "memory_profile": policy_memory_profile,
        "client_slug": payload.client_slug,
        "max_tokens_override": (
            initial_booking_policy_core_max_tokens if fresh_initial_booking_entry else None
        ),
    }
    policy_result = route_llm_policy_core_fn(
        message_text,
        **policy_core_kwargs,
    )
    policy_payload = policy_result.get("payload") if isinstance(policy_result, dict) else None
    policy_error = _normalize_token(
        policy_result.get("error") if isinstance(policy_result, dict) else None
    )
    def _build_policy_collect_candidate() -> dict[str, object] | None:
        if not isinstance(policy_payload, dict):
            return None

        policy_action = _normalize_token(policy_payload.get("action"))
        policy_tool_action = _normalize_token(policy_payload.get("tool_action"))
        policy_intent = _normalize_token(policy_payload.get("intent"))
        policy_goal = _normalize_token(policy_payload.get("goal"))
        policy_tool_args = policy_payload.get("tool_args")
        normalized_tool_args = dict(policy_tool_args) if isinstance(policy_tool_args, dict) else {}
        raw_appointment_id = normalized_tool_args.get("appointment_id")
        normalized_appointment_id = (
            raw_appointment_id.strip()
            if isinstance(raw_appointment_id, str) and raw_appointment_id.strip()
            else None
        )
        is_collect_candidate = (
            policy_action == "collect"
            and policy_tool_action == "collect"
            and policy_intent == "booking"
            and policy_goal in {None, "booking"}
        )
        is_verification_recovery_candidate = (
            policy_action == "fact"
            and policy_tool_action == "calendar.get_booking"
            and policy_intent in {"booking", "check_booking"}
            and policy_goal in {None, "booking"}
            and normalized_appointment_id is None
        )
        if not (is_collect_candidate or is_verification_recovery_candidate):
            return None

        if policy_payload.get("needs_manager") is True:
            return None
        if decision_router._normalize_plan_refs(policy_payload.get("pack_refs")):
            return None
        risk_signals = policy_payload.get("risk_signals")
        if decision_router._normalize_plan_refs(risk_signals):
            return None

        normalized_slot_state = decision_router._normalize_plan_slot_state(policy_payload.get("slots"))
        validated_slot_values: dict[str, str] = {}
        for slot_key, value in normalized_slot_state.items():
            validated_value = decision_router._validate_plan_slot_value(
                slot_key,
                value,
                client_slug=payload.client_slug,
            )
            if validated_value:
                validated_slot_values[slot_key] = validated_value

        collect_slot = _normalize_token(policy_payload.get("next_question"))
        open_questions = [
            item
            for item in decision_router._normalize_plan_questions(policy_payload.get("open_questions"))
            if item in decision_router.BOOKING_SLOT_ORDER
        ]
        if collect_slot not in decision_router.BOOKING_SLOT_ORDER:
            collect_slot = decision_router._select_plan_collect_slot(
                open_questions=open_questions,
                pack_refs=[],
                tool_action=policy_tool_action,
                goal=policy_goal,
            )
        if collect_slot not in {"service", "datetime", "name", "phone"}:
            return None
        if set(open_questions) != {collect_slot}:
            return None

        capability = _normalize_token(policy_payload.get("capability"))
        resolution_mode = _normalize_token(policy_payload.get("resolution_mode"))
        subject_kind = _normalize_token(policy_payload.get("subject_kind"))
        active_relation = _normalize_token(policy_payload.get("active_question_relation"))
        pending_target = _normalize_token(policy_payload.get("pending_question_target"))
        pending_act = _normalize_token(policy_payload.get("pending_question_act"))
        temporal_scope = _normalize_token(policy_payload.get("temporal_scope"))
        raw_tool_args = policy_payload.get("tool_args")
        if raw_tool_args is not None and not isinstance(raw_tool_args, dict):
            return None
        policy_tool_args = dict(raw_tool_args) if isinstance(raw_tool_args, dict) else {}
        decision_router._normalize_specialist_tool_args(policy_tool_args)
        unsupported_tool_args = {
            key for key in policy_tool_args if key not in {"specialist_name", "specialist_id"}
        }
        if unsupported_tool_args:
            return None
        raw_entity_refs = policy_payload.get("entity_refs")
        if raw_entity_refs is not None and not isinstance(raw_entity_refs, (list, tuple)):
            return None
        specialist_name, specialist_id = decision_router._extract_semantic_specialist_preference(
            tool_args=policy_tool_args,
            entity_refs=raw_entity_refs,
        )
        clear_service_hint = bool(specialist_name or specialist_id)
        if decision_router._should_preserve_specialist_availability_followup_owner(
            policy_goal=policy_goal,
            policy_collect_slot=collect_slot,
            policy_pending_question_target=pending_target,
            policy_subject_kind=subject_kind,
            policy_capability=capability,
            policy_temporal_scope=temporal_scope,
            policy_active_question_relation=active_relation,
        ):
            return None
        if decision_router._should_preserve_service_choice_specialist_availability_followup_owner(
            policy_goal=policy_goal,
            policy_collect_slot=collect_slot,
            policy_resolution_mode=resolution_mode,
            policy_pending_question_act=pending_act,
            policy_pending_question_target=pending_target,
            policy_subject_kind=subject_kind,
            policy_capability=capability,
            policy_temporal_scope=temporal_scope,
            policy_active_question_relation=active_relation,
            expected_reply_type=reply_slot,
        ):
            return None
        if decision_router._should_preserve_active_name_time_availability_followup_owner(
            policy_goal=policy_goal,
            policy_collect_slot=collect_slot,
            policy_resolution_mode=resolution_mode,
            policy_pending_question_act=pending_act,
            policy_pending_question_target=pending_target,
            policy_subject_kind=subject_kind,
            policy_capability=capability,
            policy_temporal_scope=temporal_scope,
            policy_active_question_relation=active_relation,
            expected_reply_type=reply_slot,
        ):
            return None
        if decision_router._should_preserve_specialist_followup_owner(
            policy_goal=policy_goal,
            policy_collect_slot=collect_slot,
            policy_pending_question_target=pending_target,
            policy_subject_kind=subject_kind,
            policy_capability=capability,
            policy_resolution_mode=resolution_mode,
            policy_active_question_relation=active_relation,
            specialist_name=specialist_name,
            specialist_id=specialist_id,
            expected_reply_type=reply_slot,
        ):
            return None

        earliest_missing_before = decision_router._first_missing_booking_slot(
            semantic_booking_state,
            client_slug=payload.client_slug,
        )
        merged_slot_state = decision_router._merge_booking_plan_slots(
            booking_state=semantic_booking_state,
            plan_slots=validated_slot_values,
        )
        if decision_router._plan_has_complete_booking_slots(
            merged_slot_state,
            client_slug=payload.client_slug,
        ):
            return None
        earliest_missing_after = decision_router._first_missing_booking_slot(
            merged_slot_state,
            client_slug=payload.client_slug,
        )
        slot_order = tuple(decision_router.BOOKING_SLOT_ORDER)
        try:
            earliest_missing_before_index = slot_order.index(earliest_missing_before)
            earliest_missing_after_index = slot_order.index(earliest_missing_after)
        except ValueError:
            earliest_missing_before_index = None
            earliest_missing_after_index = None
        allow_progressed_collect_slot = bool(
            allow_initial_slot_progression
            and earliest_missing_before_index is not None
            and earliest_missing_after_index is not None
            and earliest_missing_after_index == earliest_missing_before_index + 1
            and collect_slot == earliest_missing_after
        )
        if collect_slot != earliest_missing_after or (
            collect_slot != earliest_missing_before and not allow_progressed_collect_slot
        ):
            return None

        recovery = build_policy_validation_booking_recovery(
            booking_state=semantic_booking_state,
            collect_slot=collect_slot,
            now=now,
            expected_reply_for_booking_question=decision_router._expected_reply_for_booking_question,
            policy_slot_state_validated=validated_slot_values,
        )
        if recovery is None:
            return None
        recovered_booking_state, _ = recovery
        return {
            "collect_slot": collect_slot,
            "reason": _normalize_token(policy_payload.get("reason")) or "booking_prompt",
            "slot_values": validated_slot_values,
            "merged_slot_values": _build_booking_prompt_slot_values(recovered_booking_state),
            "specialist_name": specialist_name,
            "specialist_id": specialist_id,
            "active_question_relation": active_relation or "referent_followup",
            "pending_question_act": pending_act,
            "clear_service_hint": clear_service_hint,
        }

    if not (isinstance(policy_result, dict) and policy_result.get("ok") and isinstance(policy_payload, dict)):
        if allow_timeout_recovery and policy_error in {"timeout", "deadline_exceeded"}:
            timeout_recovery_candidate = resolve_initial_booking_timeout_collect_candidate(
                payload=payload,
                message_text=message_text,
                now=now,
            )
            if timeout_recovery_candidate is not None:
                timeout_recovery_candidate["policy_core_mode"] = "degraded_fallback"
                timeout_recovery_candidate["policy_core_degrade_reason"] = (
                    f"policy_error:{policy_error}"
                )
                timeout_recovery_candidate["policy_core_guard_recovery"] = (
                    "initial_booking_parser"
                )
                return timeout_recovery_candidate
        if allow_timeout_recovery and policy_error == "invalid_schema":
            invalid_schema_candidate = _build_policy_collect_candidate()
            if invalid_schema_candidate is not None:
                invalid_schema_candidate["policy_core_mode"] = "degraded_fallback"
                invalid_schema_candidate["policy_core_degrade_reason"] = (
                    f"policy_error:{policy_error}"
                )
                invalid_schema_candidate["policy_core_guard_recovery"] = (
                    "invalid_schema_collect_contract"
                )
                return invalid_schema_candidate
        return None

    return _build_policy_collect_candidate()


def resolve_pending_booking_reactivation_candidate(
    *,
    payload: WebhookRequest,
    message_text: str | None,
    booking_state: dict[str, object] | None,
    context: dict[str, object],
    now: datetime,
    route_llm_policy_core_fn: Callable[..., dict[str, Any]],
    initial_booking_policy_core_max_tokens: int | None = None,
) -> dict[str, object] | None:
    reactivation_seed = _build_pending_booking_reactivation_seed(
        payload=payload,
        message_text=message_text,
        booking_state=booking_state,
        context=context,
        now=now,
    )
    if reactivation_seed is None:
        return None
    seed_booking_state, reply_slot = reactivation_seed
    return resolve_llm_booking_prompt_candidate(
        payload=payload,
        message_text=message_text,
        reply_slot=reply_slot,
        current_goal="booking",
        booking_state=seed_booking_state,
        context=context,
        now=now,
        allow_initial_slot_progression=True,
        allow_timeout_recovery=True,
        route_llm_policy_core_fn=route_llm_policy_core_fn,
        initial_booking_policy_core_max_tokens=initial_booking_policy_core_max_tokens,
    )
