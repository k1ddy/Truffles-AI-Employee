from __future__ import annotations

from dataclasses import dataclass, field

from app.services.intent_service import (
    DomainIntent,
    Intent,
    _normalize_text as _normalize_domain_text,
    classify_domain_with_scores,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
)
from app.services.ai_service import (
    classify_confirmation,
    detect_refusal_flags,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
    normalize_for_matching,
)
from app.services.expected_reply_contract import expected_reply_slot_key


@dataclass(frozen=True)
class IntentRoutingPrimitives:
    normalized_text: str
    is_greeting: bool
    is_thanks: bool
    is_ack: bool
    is_low_signal: bool
    is_status_question: bool
    confirmation_decision: str
    refusal_flags: dict[str, bool]
    is_opt_out: bool
    is_frustration: bool
    is_human_request: bool
    lexical_intent: Intent | None = None

    def to_ai_signal_override(self) -> dict[str, object]:
        return {
            "normalized_text": self.normalized_text,
            "is_greeting": self.is_greeting,
            "is_thanks": self.is_thanks,
            "is_ack": self.is_ack,
            "is_low_signal": self.is_low_signal,
            "is_status_question": self.is_status_question,
            "confirmation_decision": self.confirmation_decision,
            "refusal_flags": dict(self.refusal_flags),
        }

    def to_intent_override(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "normalized_text": self.normalized_text,
            "is_opt_out": self.is_opt_out,
            "is_frustration": self.is_frustration,
            "is_human_request": self.is_human_request,
        }
        if self.lexical_intent is not None:
            payload["intent"] = self.lexical_intent.value
        return payload


@dataclass(frozen=True)
class DomainRoutingSnapshot:
    normalized_text: str
    domain_intent: DomainIntent
    in_score: float
    out_score: float
    meta: dict[str, object]

    def to_override(self) -> dict[str, object]:
        return {
            "normalized_text": self.normalized_text,
            "domain_intent": self.domain_intent.value,
            "in_score": self.in_score,
            "out_score": self.out_score,
            "meta": dict(self.meta),
        }


@dataclass(frozen=True)
class ControllerRouteSnapshot:
    normalized_text: str
    controller_class: str
    goal: str
    intents: tuple[str, ...]
    confidence: float
    reason: str

    def to_override(self) -> dict[str, object]:
        return {
            "normalized_text": self.normalized_text,
            "class": self.controller_class,
            "goal": self.goal,
            "intents": list(self.intents),
            "slots": {},
            "followups": [],
            "safety_flags": [],
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PolicyCoreRouteSnapshot:
    normalized_text: str
    intent: str
    action: str
    tool_action: str
    confidence: float
    reason: str
    needs_manager: bool = True
    goal: str = "handoff"
    tool_args: dict[str, object] = field(default_factory=dict)
    pack_refs: tuple[str, ...] = field(default_factory=tuple)
    slots: dict[str, str] = field(default_factory=dict)
    next_question: str | None = None
    open_questions: tuple[str, ...] = field(default_factory=tuple)
    capability: str | None = None
    subject_kind: str | None = None
    temporal_scope: str | None = None
    resolution_mode: str | None = None
    pending_question_act: str | None = None
    pending_question_target: str | None = None
    active_question_relation: str | None = None

    def to_override(self) -> dict[str, object]:
        return {
            "normalized_text": self.normalized_text,
            "intent": self.intent,
            "action": self.action,
            "tool_action": self.tool_action,
            "tool_args": dict(self.tool_args),
            "pack_refs": list(self.pack_refs),
            "slots": dict(self.slots),
            "next_question": self.next_question,
            "open_questions": list(self.open_questions),
            "needs_manager": self.needs_manager,
            "risk_signals": [],
            "confidence": self.confidence,
            "reason": self.reason,
            "goal": self.goal,
            "capability": self.capability,
            "entity_refs": [],
            "subject_kind": self.subject_kind,
            "temporal_scope": self.temporal_scope,
            "resolution_mode": self.resolution_mode,
            "pending_question_act": self.pending_question_act,
            "pending_question_target": self.pending_question_target,
            "active_question_relation": self.active_question_relation,
            "resolver_id": "consultant_core_ingress_override",
            "resolver_version": "2026-03-16",
        }


def detect_intent_routing_primitives(message_text: str | None) -> IntentRoutingPrimitives | None:
    normalized_text = normalize_for_matching(message_text or "")
    if not normalized_text:
        return None

    is_greeting = is_greeting_message(message_text)
    is_thanks = is_thanks_message(message_text)
    is_ack = is_acknowledgement_message(message_text)
    is_low_signal = is_low_signal_message(message_text)
    is_status_question = is_bot_status_question(message_text)
    confirmation_decision = classify_confirmation(message_text or "")
    refusal_flags = detect_refusal_flags(message_text or "")
    is_opt_out = is_opt_out_message(message_text)
    is_frustration = is_frustration_message(message_text)
    is_human_request = is_human_request_message(message_text)

    lexical_intent = None
    if is_opt_out:
        lexical_intent = Intent.REJECTION
    elif is_frustration:
        lexical_intent = Intent.FRUSTRATION
    elif is_human_request:
        lexical_intent = Intent.HUMAN_REQUEST
    elif is_greeting:
        lexical_intent = Intent.GREETING
    elif is_thanks:
        lexical_intent = Intent.THANKS
    elif is_ack or is_low_signal:
        lexical_intent = Intent.OTHER

    return IntentRoutingPrimitives(
        normalized_text=normalized_text,
        is_greeting=is_greeting,
        is_thanks=is_thanks,
        is_ack=is_ack,
        is_low_signal=is_low_signal,
        is_status_question=is_status_question,
        confirmation_decision=confirmation_decision,
        refusal_flags=dict(refusal_flags),
        is_opt_out=is_opt_out,
        is_frustration=is_frustration,
        is_human_request=is_human_request,
        lexical_intent=lexical_intent,
    )


def detect_domain_routing_snapshot(
    message_text: str | None,
    *,
    client_config: dict | None,
) -> DomainRoutingSnapshot | None:
    normalized_text = _normalize_domain_text(message_text or "")
    if not normalized_text:
        return None

    domain_intent, in_score, out_score, meta = classify_domain_with_scores(
        message_text or "",
        client_config,
    )
    return DomainRoutingSnapshot(
        normalized_text=normalized_text,
        domain_intent=domain_intent,
        in_score=float(in_score),
        out_score=float(out_score),
        meta=dict(meta or {}),
    )


def detect_controller_route_snapshot(
    message_text: str | None,
    *,
    primitives: IntentRoutingPrimitives | None = None,
    domain_snapshot: DomainRoutingSnapshot | None = None,
) -> ControllerRouteSnapshot | None:
    normalized_text = normalize_for_matching(message_text or "")
    if not normalized_text:
        return None

    if primitives is None:
        primitives = detect_intent_routing_primitives(message_text)

    if (
        primitives is not None
        and not primitives.is_human_request
        and not primitives.is_opt_out
        and not primitives.is_frustration
        and (primitives.is_greeting or primitives.is_thanks or primitives.is_ack)
    ):
        return ControllerRouteSnapshot(
            normalized_text=normalized_text,
            controller_class="greeting",
            goal="greeting",
            intents=("greeting",),
            confidence=0.95,
            reason="ingress_lexical_greeting",
        )

    if domain_snapshot is None or domain_snapshot.domain_intent != DomainIntent.OUT_OF_DOMAIN:
        return None

    if primitives is not None and (
        primitives.is_greeting
        or primitives.is_thanks
        or primitives.is_ack
        or primitives.is_human_request
        or primitives.is_opt_out
        or primitives.is_frustration
    ):
        return None

    meta = domain_snapshot.meta if isinstance(domain_snapshot.meta, dict) else {}
    out_hits = int(meta.get("out_hits") or 0)
    in_hits = int(meta.get("strict_in_hits") or 0)
    if out_hits <= 0 or in_hits != 0 or domain_snapshot.out_score <= domain_snapshot.in_score:
        return None

    return ControllerRouteSnapshot(
        normalized_text=normalized_text,
        controller_class="out_of_domain",
        goal="out_of_domain",
        intents=("out_of_domain",),
        confidence=min(1.0, max(0.95, float(domain_snapshot.out_score))),
        reason="ingress_domain_router_out_of_domain",
    )


def detect_policy_core_route_snapshot(
    message_text: str | None,
    *,
    primitives: IntentRoutingPrimitives | None = None,
    has_media: bool = False,
    client_slug: str | None = None,
    reply_slot: str | None = None,
    resume_reason: str | None = None,
    has_active_service_referent: bool = False,
    active_service_referent: str | None = None,
    active_booking_time_token: str | None = None,
    active_booking_datetime_value: str | None = None,
    booking_active: bool = False,
) -> PolicyCoreRouteSnapshot | None:
    normalized_text = normalize_for_matching(message_text or "")
    if not normalized_text:
        return None
    resolved_active_service_referent = (
        active_service_referent.strip()
        if isinstance(active_service_referent, str) and active_service_referent.strip()
        else None
    )
    resolved_active_booking_time_token = (
        active_booking_time_token.strip()
        if isinstance(active_booking_time_token, str) and active_booking_time_token.strip()
        else None
    )
    resolved_active_booking_datetime_value = (
        active_booking_datetime_value.strip()
        if isinstance(active_booking_datetime_value, str) and active_booking_datetime_value.strip()
        else None
    )
    if resolved_active_service_referent:
        has_active_service_referent = True
    normalized_reply_slot = reply_slot.strip().casefold() if isinstance(reply_slot, str) and reply_slot.strip() else None
    normalized_reply_slot_key = expected_reply_slot_key(normalized_reply_slot) or normalized_reply_slot
    normalized_resume_reason = (
        resume_reason.strip().casefold()
        if isinstance(resume_reason, str) and resume_reason.strip()
        else None
    )

    if primitives is None:
        primitives = detect_intent_routing_primitives(message_text)
    if primitives is None:
        return None

    if primitives.is_human_request:
        return PolicyCoreRouteSnapshot(
            normalized_text=normalized_text,
            intent="human_request",
            action="handoff",
            tool_action="handoff",
            confidence=0.98,
            reason="ingress_explicit_human_request",
        )

    if primitives.is_opt_out:
        return None

    if primitives.is_frustration:
        return PolicyCoreRouteSnapshot(
            normalized_text=normalized_text,
            intent="frustration",
            action="handoff",
            tool_action="handoff",
            confidence=0.94,
            reason="ingress_explicit_frustration_handoff",
        )

    if not has_media:
        from app.routers.webhook.media import _is_style_reference_request

        if _is_style_reference_request(message_text, has_media=False):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="portfolio",
                action="fact",
                tool_action="catalog.portfolio",
                confidence=0.97,
                reason="style_reference_text",
                needs_manager=False,
                goal="info",
                pack_refs=("portfolio",),
                capability="portfolio",
            )

    if not has_media and not primitives.is_status_question:
        from app.services.info_signal_service import detect_booking_verification_mode

        verification_mode = detect_booking_verification_mode(message_text)
        if verification_mode == "confirm":
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="confirm_booking",
                action="collect",
                tool_action="collect",
                confidence=0.95,
                reason="booking_confirmation_text",
                needs_manager=False,
                goal="booking",
                next_question="datetime",
                open_questions=("datetime",),
                active_question_relation="fill_requested_slot",
            )
        if verification_mode == "check":
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="check_booking",
                action="fact",
                tool_action="calendar.get_booking",
                confidence=0.95,
                reason="booking_verification_text",
                needs_manager=False,
                goal="booking",
            )

    if not has_media:
        from app.services.info_signal_service import looks_like_services_overview_message

        if looks_like_services_overview_message(message_text):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="services_overview",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="services_overview",
                needs_manager=False,
                goal="info",
            )

    if not has_media:
        from app.services.info_signal_service import detect_location_policy_pack_refs

        pack_refs = detect_location_policy_pack_refs(message_text, client_slug=client_slug)
        if pack_refs:
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="fact",
                tool_action="catalog.location",
                confidence=0.95,
                reason="parking_question" if "parking" in pack_refs else "location_question",
                needs_manager=False,
                goal="info",
                pack_refs=pack_refs,
            )

    if not has_media:
        from app.services.info_signal_service import (
            detect_service_choice_specialist_exact_time_followup,
            detect_service_choice_specialist_daypart_followup,
            detect_service_choice_specialist_day_followup_service_query,
            detect_service_choice_specialist_weekday_followup_service_query,
            detect_service_choice_specialist_weekend_followup_service_query,
        )

        exact_time_followup = detect_service_choice_specialist_exact_time_followup(
            message_text,
            client_slug=client_slug,
        )
        daypart_followup = detect_service_choice_specialist_daypart_followup(
            message_text,
            client_slug=client_slug,
        )
        day_service_query = detect_service_choice_specialist_day_followup_service_query(
            message_text,
            client_slug=client_slug,
        )
        weekday_service_query = detect_service_choice_specialist_weekday_followup_service_query(
            message_text,
            client_slug=client_slug,
        )
        weekend_service_query = detect_service_choice_specialist_weekend_followup_service_query(
            message_text,
            client_slug=client_slug,
        )
        if (
            normalized_reply_slot_key == "service"
            and normalized_resume_reason == "booking_prompt"
            and weekday_service_query
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="weekday_followup",
                needs_manager=False,
                goal="info",
                slots={
                    "service": weekday_service_query,
                    "datetime": "",
                    "name": "",
                },
                next_question="datetime",
                open_questions=("datetime",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="weekday",
                resolution_mode="clarify_missing_time",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            normalized_reply_slot_key == "service"
            and normalized_resume_reason == "booking_prompt"
            and weekend_service_query
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="weekend_followup",
                needs_manager=False,
                goal="info",
                slots={
                    "service": weekend_service_query,
                    "datetime": "",
                    "name": "",
                },
                next_question="datetime",
                open_questions=("datetime",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="weekend",
                resolution_mode="clarify_missing_time",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            normalized_reply_slot_key == "service"
            and normalized_resume_reason == "booking_prompt"
            and day_service_query
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="day_followup",
                needs_manager=False,
                goal="info",
                slots={
                    "service": day_service_query,
                    "datetime": "",
                    "name": "",
                },
                next_question="datetime",
                open_questions=("datetime",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="specific_time",
                resolution_mode="clarify_missing_time",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            normalized_reply_slot_key == "service"
            and normalized_resume_reason == "booking_prompt"
            and exact_time_followup
        ):
            exact_time_service_query, exact_time_datetime_token = exact_time_followup
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.94,
                reason="specialist_exact_time_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": exact_time_service_query,
                    "datetime": exact_time_datetime_token,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="specialist_availability_followup",
            )
        if (
            normalized_reply_slot_key == "service"
            and normalized_resume_reason == "booking_prompt"
            and daypart_followup
        ):
            daypart_service_query, daypart_datetime_token = daypart_followup
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="daypart_followup",
                needs_manager=False,
                goal="info",
                slots={
                    "service": daypart_service_query,
                    "datetime": daypart_datetime_token,
                    "name": "",
                },
                next_question="datetime",
                open_questions=("datetime",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="specific_time",
                resolution_mode="clarify_missing_time",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="ask_about_requested_slot",
            )

    suppress_hours_booking_service_followup = False
    if not has_media:
        from app.services.booking_signal_service import (
            extract_time_token,
            has_explicit_date_signal,
            normalize_resolved_datetime_value,
        )
        from app.services.info_signal_service import signal_any_match

        suppress_hours_booking_service_followup = bool(
            booking_active
            and normalized_reply_slot_key == "service"
            and normalized_resume_reason in {"booking_prompt", "booking_interrupt"}
            and not resolved_active_service_referent
            and signal_any_match(
                normalized_text,
                client_slug,
                "booking_request",
                "booking_keywords",
            )
            and (
                has_explicit_date_signal(message_text)
                or extract_time_token(message_text)
                or normalize_resolved_datetime_value(
                    message_text,
                    normalized_text=normalized_text,
                )
            )
        )

    suppress_hours_pending_time_slot_constraint = False
    if (
        not has_media
        and booking_active
        and normalized_reply_slot == "time"
        and isinstance(message_text, str)
        and message_text.strip()
    ):
        from app.routers.webhook import decision as decision_router

        matched_time_slot, matched_time_value, _ = decision_router._match_expected_reply(
            expected_reply_type=decision_router.EXPECTED_REPLY_TIME,
            message_text=message_text,
            client_slug=client_slug,
        )
        suppress_hours_pending_time_slot_constraint = bool(
            matched_time_slot
            and isinstance(matched_time_value, str)
            and matched_time_value.strip()
            and decision_router._is_time_slot_constraint_candidate(
                message_text=message_text,
                candidate_value=matched_time_value.strip(),
                client_slug=client_slug,
            )
        )

    if not has_media:
        from app.services.info_signal_service import looks_like_hours_policy_message

        if (
            not suppress_hours_booking_service_followup
            and not suppress_hours_pending_time_slot_constraint
            and looks_like_hours_policy_message(message_text, client_slug=client_slug)
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="hours",
                action="fact",
                tool_action="info",
                confidence=0.95,
                reason="hours_question",
                needs_manager=False,
                goal="info",
                pack_refs=("hours",),
                capability="hours",
            )

    if not has_media:
        from app.services.info_signal_service import looks_like_promotions_rules_policy_message

        if looks_like_promotions_rules_policy_message(message_text, client_slug=client_slug):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="promotions_rules",
                action="fact",
                tool_action="info",
                confidence=0.95,
                reason="promotions_rules_question",
                needs_manager=False,
                goal="info",
                pack_refs=("promotions",),
                capability="promotions",
            )

    if not has_media:
        from app.services.info_signal_service import looks_like_promotions_policy_message

        if looks_like_promotions_policy_message(message_text, client_slug=client_slug):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="promotions",
                action="fact",
                tool_action="info",
                confidence=0.95,
                reason="promotions_question",
                needs_manager=False,
                goal="info",
                pack_refs=("promotions",),
                capability="promotions",
            )

    if not has_media:
        from app.services.info_signal_service import looks_like_contact_policy_message

        if looks_like_contact_policy_message(message_text, client_slug=client_slug):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="contact",
                action="fact",
                tool_action="info",
                confidence=0.95,
                reason="contact_question",
                needs_manager=False,
                goal="info",
                pack_refs=("contact",),
            )

    if not has_media:
        from app.services.info_signal_service import detect_portfolio_policy_service_query

        matched, service_query = detect_portfolio_policy_service_query(
            message_text,
            client_slug=client_slug,
        )
        if matched:
            tool_args = {"service_query": service_query} if service_query else {}
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="portfolio",
                action="fact",
                tool_action="catalog.portfolio",
                confidence=0.95,
                reason="portfolio_question",
                needs_manager=False,
                goal="info",
                tool_args=tool_args,
                pack_refs=("portfolio",),
                capability="portfolio",
            )

    if not has_media:
        from app.services.info_signal_service import (
            _has_price_signal,
            looks_like_pricing_service_clarify_policy_message,
        )

        if (
            resolved_active_service_referent
            and _has_price_signal(normalized_text, message_text, client_slug=client_slug)
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="pricing_query",
                needs_manager=False,
                goal="booking",
                tool_args={"service_query": resolved_active_service_referent},
                pack_refs=("pricing",),
                capability="pricing",
            )

        if (
            looks_like_pricing_service_clarify_policy_message(
                message_text,
                client_slug=client_slug,
            )
        ):
            if resolved_active_service_referent:
                return PolicyCoreRouteSnapshot(
                    normalized_text=normalized_text,
                    intent="info",
                    action="fact",
                    tool_action="catalog.service_query",
                    confidence=0.95,
                    reason="pricing_query",
                    needs_manager=False,
                    goal="booking",
                    tool_args={"service_query": resolved_active_service_referent},
                    pack_refs=("pricing",),
                    capability="pricing",
                )
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="pricing",
                action="collect",
                tool_action="info",
                confidence=0.94,
                reason="need_service",
                needs_manager=False,
                goal="info",
                pack_refs=("pricing",),
                next_question="service",
                open_questions=("service",),
                capability="pricing",
                subject_kind="service",
                resolution_mode="clarify_missing_subject",
            )

    if not has_media:
        from app.services.info_signal_service import looks_like_bookability_time_collect_policy_message

        if (
            booking_active
            and resolved_active_service_referent
            and looks_like_bookability_time_collect_policy_message(
                message_text,
                client_slug=client_slug,
            )
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="calendar.list_slots",
                confidence=0.94,
                reason="missing_temporal_scope",
                needs_manager=False,
                goal="booking",
                tool_args={"service_query": resolved_active_service_referent},
                slots={"service": resolved_active_service_referent, "datetime": ""},
                next_question="datetime",
                open_questions=("datetime",),
                capability="bookability",
                subject_kind="service",
                temporal_scope="none",
                resolution_mode="clarify_missing_time",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="time",
                active_question_relation="ask_about_requested_slot",
            )

    if not has_media:
        from app.services.info_signal_service import (
            detect_active_name_relative_daypart_availability_followup_datetime_token,
            looks_like_active_name_deictic_day_availability_followup,
            detect_active_name_relative_date_availability_followup_datetime_token,
            detect_active_name_time_availability_followup_time_token,
            looks_like_active_name_deictic_time_availability_followup,
        )

        time_token = detect_active_name_time_availability_followup_time_token(
            message_text,
            client_slug=client_slug,
        )
        relative_daypart_token = (
            detect_active_name_relative_daypart_availability_followup_datetime_token(
                message_text,
                client_slug=client_slug,
            )
        )
        relative_date_token = detect_active_name_relative_date_availability_followup_datetime_token(
            message_text,
            client_slug=client_slug,
        )
        if (
            booking_active
            and resolved_active_service_referent
            and normalized_reply_slot == "name"
            and normalized_resume_reason == "booking_time_availability_followup"
            and time_token
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.94,
                reason="booking_time_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": time_token,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="live_availability",
                subject_kind="booking",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="time",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            booking_active
            and resolved_active_service_referent
            and resolved_active_booking_time_token
            and normalized_reply_slot == "name"
            and normalized_resume_reason in {"booking_prompt", "booking_time_availability_followup"}
            and relative_daypart_token
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="booking_time_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": relative_daypart_token,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="bookability",
                subject_kind="booking",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="time",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            booking_active
            and resolved_active_service_referent
            and resolved_active_booking_time_token
            and normalized_reply_slot == "name"
            and normalized_resume_reason in {"booking_prompt", "booking_time_availability_followup"}
            and relative_date_token
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="booking_time_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": relative_date_token,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="bookability",
                subject_kind="booking",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="time",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            booking_active
            and resolved_active_service_referent
            and resolved_active_booking_time_token
            and normalized_reply_slot == "name"
            and normalized_resume_reason in {"booking_prompt", "booking_time_availability_followup"}
            and looks_like_active_name_deictic_day_availability_followup(
                message_text,
                client_slug=client_slug,
            )
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="booking_time_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": resolved_active_booking_time_token,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="bookability",
                subject_kind="booking",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="time",
                active_question_relation="ask_about_requested_slot",
            )
        if (
            booking_active
            and resolved_active_service_referent
            and resolved_active_booking_time_token
            and normalized_reply_slot == "name"
            and looks_like_active_name_deictic_time_availability_followup(
                message_text,
                client_slug=client_slug,
            )
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="booking_time_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": resolved_active_booking_time_token,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="live_availability",
                subject_kind="booking",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="time",
                active_question_relation="ask_about_requested_slot",
            )

    if not has_media:
        from app.services.info_signal_service import detect_grounded_pricing_service_query

        service_query = detect_grounded_pricing_service_query(
            message_text,
            client_slug=client_slug,
        )
        if service_query:
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="info",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="pricing_query",
                needs_manager=False,
                goal="booking",
                tool_args={"service_query": service_query},
                pack_refs=("pricing",),
                capability="pricing",
            )

    if not has_media:
        from app.services.info_signal_service import (
            _has_duration_signal,
            looks_like_duration_service_clarify_policy_message,
        )

        if (
            resolved_active_service_referent
            and _has_duration_signal(normalized_text, message_text, client_slug=client_slug)
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="duration",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="duration_info",
                needs_manager=False,
                goal="booking",
                tool_args={"service_query": resolved_active_service_referent},
                pack_refs=("duration",),
                capability="duration",
            )

        if (
            looks_like_duration_service_clarify_policy_message(
                message_text,
                client_slug=client_slug,
            )
        ):
            if resolved_active_service_referent:
                return PolicyCoreRouteSnapshot(
                    normalized_text=normalized_text,
                    intent="duration",
                    action="fact",
                    tool_action="catalog.service_query",
                    confidence=0.95,
                    reason="duration_info",
                    needs_manager=False,
                    goal="booking",
                    tool_args={"service_query": resolved_active_service_referent},
                    pack_refs=("duration",),
                    capability="duration",
                )
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="duration",
                action="collect",
                tool_action="info",
                confidence=0.94,
                reason="need_service",
                needs_manager=False,
                goal="info",
                pack_refs=("duration",),
                next_question="service",
                open_questions=("service",),
                capability="duration",
                subject_kind="service",
                resolution_mode="clarify_missing_subject",
            )

    if not has_media:
        from app.services.info_signal_service import detect_grounded_duration_service_query

        service_query = detect_grounded_duration_service_query(
            message_text,
            client_slug=client_slug,
        )
        if service_query:
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="duration",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="duration_info",
                needs_manager=False,
                goal="booking",
                tool_args={"service_query": service_query},
                pack_refs=("duration",),
                capability="duration",
            )

    if not has_media:
        from app.services.info_signal_service import (
            looks_like_specialist_date_range_availability_followup,
            looks_like_grounded_specialist_availability_followup,
        )

        if (
            booking_active
            and resolved_active_service_referent
            and normalized_reply_slot == "time"
            and normalized_resume_reason
            in {"booking_prompt", "booking_specialist_availability_followup"}
            and looks_like_specialist_date_range_availability_followup(
                message_text,
                client_slug=client_slug,
            )
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="booking_specialist_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": "",
                    "name": "",
                },
                next_question="datetime",
                open_questions=("datetime",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="date_range",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="specialist_availability_followup",
            )
        if (
            booking_active
            and resolved_active_service_referent
            and resolved_active_booking_datetime_value
            and normalized_reply_slot == "time"
            and normalized_resume_reason
            in {"booking_prompt", "booking_specialist_availability_followup"}
            and looks_like_grounded_specialist_availability_followup(
                message_text,
                client_slug=client_slug,
            )
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="booking",
                action="collect",
                tool_action="collect",
                confidence=0.93,
                reason="booking_specialist_availability_followup",
                needs_manager=False,
                goal="booking",
                slots={
                    "service": resolved_active_service_referent,
                    "datetime": resolved_active_booking_datetime_value,
                    "name": "",
                },
                next_question="name",
                open_questions=("name",),
                capability="live_availability",
                subject_kind="specialist",
                temporal_scope="specific_time",
                resolution_mode="referent_followup",
                pending_question_act="ask_about_requested_slot",
                pending_question_target="specialist",
                active_question_relation="specialist_availability_followup",
            )

    if not has_media:
        from app.services.info_signal_service import (
            detect_grounded_master_service_query,
        )

        service_query = detect_grounded_master_service_query(
            message_text,
            client_slug=client_slug,
        )
        if service_query:
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="master_query",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="master_question",
                needs_manager=False,
                goal="info",
                tool_args={"service_query": service_query},
                pack_refs=("master",),
            )

    if not has_media:
        from app.services.info_signal_service import looks_like_master_service_clarify_policy_message
        from app.services.pack_runtime_service import resolve_master_intent

        master_resolution = resolve_master_intent(
            message_text=message_text,
            client_slug=client_slug,
            service_query=None,
            intent_decomp=None,
            force_master_intent=False,
        )
        if resolved_active_service_referent and (
            master_resolution.explicit or bool(master_resolution.matched_signals)
        ):
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="master_query",
                action="fact",
                tool_action="catalog.service_query",
                confidence=0.95,
                reason="master_question",
                needs_manager=False,
                goal="info",
                tool_args={"service_query": resolved_active_service_referent},
                pack_refs=("master",),
            )

        if looks_like_master_service_clarify_policy_message(
            message_text,
            client_slug=client_slug,
        ):
            if resolved_active_service_referent:
                return PolicyCoreRouteSnapshot(
                    normalized_text=normalized_text,
                    intent="master_query",
                    action="fact",
                    tool_action="catalog.service_query",
                    confidence=0.95,
                    reason="master_question",
                    needs_manager=False,
                    goal="info",
                    tool_args={"service_query": resolved_active_service_referent},
                    pack_refs=("master",),
                )
            return PolicyCoreRouteSnapshot(
                normalized_text=normalized_text,
                intent="master_query",
                action="collect",
                tool_action="collect",
                confidence=0.94,
                reason="master_service_clarify",
                needs_manager=False,
                goal="info",
                pack_refs=("master",),
                next_question="service",
                open_questions=("service",),
                subject_kind="service",
                resolution_mode="clarify_missing_subject",
            )

    return None
