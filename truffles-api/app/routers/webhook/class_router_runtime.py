"""Shared class-router/controller runtime helpers for active webhook paths."""

from __future__ import annotations

import os
from typing import Any

from app.services.intent_service import DomainIntent

from .runtime_primitives import INFO_INTENTS
from .trace import _router_observability_meta

CONTROLLER_CONFIDENCE_THRESHOLD = float(
    os.getenv("CONTROLLER_CONFIDENCE_THRESHOLD", "0.3") or 0.3
)
CONSULT_INTERRUPT_INTENTS = {"booking", "pricing", "duration", "location", "hours"}

_CONTROLLER_FALLBACK_IGNORE_VALUES = {"none", "skipped", "ok", "low_confidence"}
_CONTROLLER_FALLBACK_REASON_MAP = {
    "timeout": "timeout",
    "invalid_json": "invalid_json",
    "budget_exceeded": "budget_exceeded",
    "budget_reserved": "budget_reserved",
    "no_api_key": "no_api_key",
    "prompt_missing": "prompt_missing",
    "empty_message": "empty_message",
    "empty_response": "empty_response",
    "invalid_class": "invalid_class",
    "unsupported_temperature": "unsupported_temperature",
}
_CONTROLLER_FALLBACK_ERROR_VALUES = {"controller_failed", "error"}


def _normalize_class_name(class_name: str) -> str:
    normalized = class_name.strip()
    if normalized.casefold() in {"info", "info_bundle"}:
        return "info_bundle"
    return normalized


def _build_controller_meta_output(
    *, error: str, retry: bool = False, elapsed_ms: float = 0.0
) -> dict[str, Any]:
    return {
        "class": None,
        "goal": None,
        "intents": [],
        "slots": {},
        "followups": [],
        "safety_flags": [],
        "confidence": 0.0,
        "reason": "",
        "carryover": {},
        "controller_llm_ms": round(elapsed_ms, 2),
        "controller_error": error,
        "controller_retry": bool(retry),
    }


def _ensure_controller_output_meta(
    controller_output: dict[str, Any], *, error: str | None
) -> dict[str, Any]:
    if not isinstance(controller_output.get("controller_llm_ms"), (int, float)):
        controller_output["controller_llm_ms"] = 0.0
    if not isinstance(controller_output.get("controller_error"), str) or not controller_output.get(
        "controller_error"
    ):
        controller_output["controller_error"] = error or "none"
    if not isinstance(controller_output.get("controller_retry"), bool):
        controller_output["controller_retry"] = False
    if "controller_goal" in controller_output and not controller_output.get("goal"):
        controller_output["goal"] = controller_output.get("controller_goal")
    return controller_output


def _normalize_controller_fallback_reason(*, error: str | None) -> str | None:
    if not error:
        return None
    normalized = error.strip().casefold()
    if not normalized or normalized in _CONTROLLER_FALLBACK_IGNORE_VALUES:
        return None
    mapped = _CONTROLLER_FALLBACK_REASON_MAP.get(normalized)
    if mapped:
        return mapped
    if normalized in _CONTROLLER_FALLBACK_ERROR_VALUES:
        return "error"
    return "error"


def _resolve_controller_signal_class(
    *, intent_decomp_set: set[str], booking_signal: bool
) -> str | None:
    if booking_signal:
        return "booking"
    if "consult" in intent_decomp_set:
        return "consult"
    if "booking" in intent_decomp_set:
        return "booking"
    if intent_decomp_set & INFO_INTENTS:
        return "info_bundle"
    if "greeting" in intent_decomp_set:
        return "greeting"
    if "out_of_domain" in intent_decomp_set:
        return "out_of_domain"
    return None


def _build_class_controller_result(
    *,
    info_intents: set[str],
    info_meta: dict[str, Any] | None,
    booking_signal: bool,
    class_carryover: dict[str, Any] | None,
    domain_intent: DomainIntent,
    domain_meta: dict[str, Any] | None,
    explicit_service_signal: bool,
) -> dict[str, Any]:
    anchors_out_hits = int(domain_meta.get("out_hits") or 0) if isinstance(domain_meta, dict) else 0
    anchors_in_hits = int(domain_meta.get("strict_in_hits") or 0) if isinstance(domain_meta, dict) else 0
    in_signals: list[str] = []
    out_signals: list[str] = []
    classes: list[str] = []

    if info_intents:
        in_signals.append("info_intents")
        classes.append("info_bundle")
    if isinstance(info_meta, dict):
        raw_anchor_intents = info_meta.get("anchor_intents")
        if isinstance(raw_anchor_intents, list):
            for item in raw_anchor_intents:
                if isinstance(item, str) and item.strip():
                    in_signals.append(f"info_anchor_{item.strip().casefold()}")
        info_signals = info_meta.get("info_signals")
        if isinstance(info_signals, dict) and info_signals.get("guest"):
            in_signals.append("info_guest")
            classes.append("info_bundle")
    if booking_signal:
        in_signals.append("booking_signal")
        classes.append("booking")
    if explicit_service_signal:
        in_signals.append("explicit_service")
    if anchors_in_hits > 0:
        in_signals.append("anchor_in")
    if anchors_out_hits > 0:
        out_signals.append("anchor_out")

    carryover_class = None
    carryover_info_sections: list[str] = []
    carryover_intents: list[str] = []
    if isinstance(class_carryover, dict):
        carryover_class = class_carryover.get("class")
        if isinstance(carryover_class, str) and carryover_class.strip():
            carryover_class = _normalize_class_name(carryover_class)
            in_signals.append("carryover")
            classes.append(carryover_class)
        raw_sections = class_carryover.get("info_sections")
        if isinstance(raw_sections, list):
            carryover_info_sections = [item for item in raw_sections if isinstance(item, str)]
        raw_intents = class_carryover.get("intents")
        if isinstance(raw_intents, list):
            carryover_intents = [item for item in raw_intents if isinstance(item, str)]

    if domain_intent == DomainIntent.OUT_OF_DOMAIN and not out_signals:
        out_signals.append("domain_out")

    out_of_domain_signal = bool(out_signals and not in_signals)
    if out_of_domain_signal:
        classes.append("out_of_domain")
    classes = list(dict.fromkeys(classes))
    in_signals = list(dict.fromkeys(in_signals))
    out_signals = list(dict.fromkeys(out_signals))
    carryover_intents = list(dict.fromkeys(carryover_intents))
    carryover_info_sections = list(dict.fromkeys(carryover_info_sections))
    return {
        "classes": classes,
        "intents": sorted(info_intents),
        "in_signals": in_signals,
        "out_signals": out_signals,
        "anchors_in_hits": anchors_in_hits,
        "anchors_out_hits": anchors_out_hits,
        "out_of_domain_signal": out_of_domain_signal,
        "carryover_class": carryover_class,
        "carryover_info_sections": carryover_info_sections,
        "carryover_intents": carryover_intents,
    }


def build_observer_class_router_result(
    *,
    class_name: str | None,
    goal: str | None,
    info_intents: set[str] | list[str] | tuple[str, ...] | None = None,
    booking_signal: bool = False,
    carryover_class: str | None = None,
    carryover_intents: list[str] | tuple[str, ...] | None = None,
    carryover_info_sections: list[str] | tuple[str, ...] | None = None,
    in_signals: list[str] | tuple[str, ...] | None = None,
    out_signals: list[str] | tuple[str, ...] | None = None,
    out_of_domain_signal: bool = False,
) -> dict[str, Any]:
    normalized_class = (
        _normalize_class_name(class_name)
        if isinstance(class_name, str) and class_name.strip()
        else None
    )
    normalized_carryover_class = (
        _normalize_class_name(carryover_class)
        if isinstance(carryover_class, str) and carryover_class.strip()
        else None
    )
    classes: list[str] = []
    if normalized_class:
        classes.append(normalized_class)
    if normalized_carryover_class and normalized_carryover_class not in classes:
        classes.append(normalized_carryover_class)
    normalized_intents = sorted(
        {
            item.strip().casefold()
            for item in (info_intents or [])
            if isinstance(item, str) and item.strip()
        }
    )
    normalized_in_signals = list(
        dict.fromkeys(
            item.strip()
            for item in (in_signals or [])
            if isinstance(item, str) and item.strip()
        )
    )
    normalized_out_signals = list(
        dict.fromkeys(
            item.strip()
            for item in (out_signals or [])
            if isinstance(item, str) and item.strip()
        )
    )
    if booking_signal and "booking_signal" not in normalized_in_signals:
        normalized_in_signals.append("booking_signal")
    normalized_carryover_intents = list(
        dict.fromkeys(
            item.strip().casefold()
            for item in (carryover_intents or [])
            if isinstance(item, str) and item.strip()
        )
    )
    normalized_carryover_sections = list(
        dict.fromkeys(
            item.strip().casefold()
            for item in (carryover_info_sections or [])
            if isinstance(item, str) and item.strip()
        )
    )
    controller_meta = {
        "used": False,
        "attempted": False,
        "fallback": False,
        "confidence": None,
        "reason": None,
        "fallback_reason": None,
        "error": "observer_only",
        "output": None,
        "signal_class": None,
        "signal_match": False,
        "used_reason": "observer_only",
        "sla": None,
        "goal": goal.strip() if isinstance(goal, str) and goal.strip() else None,
        "low_confidence": False,
        "observer_only": True,
    }
    return {
        "classes": classes,
        "intents": normalized_intents,
        "in_signals": normalized_in_signals,
        "out_signals": normalized_out_signals,
        "anchors_in_hits": 0,
        "anchors_out_hits": 0,
        "out_of_domain_signal": bool(out_of_domain_signal),
        "carryover_class": normalized_carryover_class,
        "carryover_info_sections": normalized_carryover_sections,
        "carryover_intents": normalized_carryover_intents,
        "controller": controller_meta,
        "controller_fallback_reason": None,
        "router": dict(controller_meta),
        "router_fallback_reason": None,
        "observer_only": True,
    }


def _resolve_class_router_result(
    *,
    info_intents: set[str],
    info_meta: dict[str, Any] | None,
    booking_signal: bool,
    class_carryover: dict[str, Any] | None,
    domain_intent: DomainIntent,
    domain_meta: dict[str, Any] | None,
    router_state: dict[str, Any] | None,
    explicit_service_signal: bool,
) -> dict[str, Any]:
    result = _build_class_controller_result(
        info_intents=info_intents,
        info_meta=info_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        explicit_service_signal=explicit_service_signal,
    )

    controller_output = router_state.get("output") if isinstance(router_state, dict) else None
    controller_used = router_state.get("used") if isinstance(router_state, dict) else False
    controller_error = router_state.get("error") if isinstance(router_state, dict) else None
    controller_fallback = router_state.get("fallback_reason") if isinstance(router_state, dict) else None
    controller_attempted = bool(router_state.get("attempted")) if isinstance(router_state, dict) else False
    controller_fallback_flag = bool(router_state.get("fallback")) if isinstance(router_state, dict) else False
    controller_confidence = router_state.get("confidence") if isinstance(router_state, dict) else None
    controller_sla = router_state.get("sla") if isinstance(router_state, dict) else None
    controller_signal_class = router_state.get("signal_class") if isinstance(router_state, dict) else None
    controller_signal_match = router_state.get("signal_match") if isinstance(router_state, dict) else None
    controller_used_reason = router_state.get("used_reason") if isinstance(router_state, dict) else None

    controller_class = None
    controller_reason = None
    controller_goal = None
    if isinstance(controller_output, dict):
        raw_class = controller_output.get("class")
        if isinstance(raw_class, str):
            controller_class = _normalize_class_name(raw_class)
        raw_reason = controller_output.get("reason")
        if isinstance(raw_reason, str):
            controller_reason = raw_reason
        raw_goal = controller_output.get("goal")
        if isinstance(raw_goal, str):
            controller_goal = raw_goal.strip()

    controller_confidence_value = controller_confidence
    controller_low_confidence = bool(
        controller_used
        and isinstance(controller_confidence_value, (int, float))
        and controller_confidence_value < CONTROLLER_CONFIDENCE_THRESHOLD
    )

    controller_fallback_reason = None
    controller_error_normalized = controller_error if isinstance(controller_error, str) else None
    controller_error_normalized = controller_error_normalized.strip() if controller_error_normalized else None
    if controller_error_normalized:
        controller_fallback_reason = _normalize_controller_fallback_reason(error=controller_error_normalized)

    if controller_used and controller_class and controller_low_confidence:
        controller_used_reason = "low_confidence"
        controller_used = True
        controller_fallback_reason = None
        controller_fallback_flag = False
    elif not controller_used and isinstance(controller_fallback, str):
        normalized_fallback = _normalize_controller_fallback_reason(error=controller_fallback)
        if normalized_fallback:
            controller_fallback_reason = controller_fallback_reason or normalized_fallback

    result["controller"] = {
        "used": bool(controller_used),
        "attempted": controller_attempted,
        "fallback": controller_fallback_flag,
        "confidence": controller_confidence,
        "reason": controller_reason,
        "fallback_reason": controller_fallback_reason if not controller_used else None,
        "error": controller_error,
        "output": controller_output,
        "signal_class": controller_signal_class,
        "signal_match": controller_signal_match,
        "used_reason": controller_used_reason,
        "sla": controller_sla,
        "goal": controller_goal,
        "low_confidence": controller_low_confidence,
    }
    result["controller_fallback_reason"] = controller_fallback_reason
    result["router"] = result["controller"]
    result["router_fallback_reason"] = controller_fallback_reason
    return result


def _controller_meta_updates_from_class_router(class_router_result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(class_router_result, dict):
        return {}
    controller_meta = class_router_result.get("controller")
    if not isinstance(controller_meta, dict):
        return {}
    return {
        "controller_used": bool(controller_meta.get("used")),
        "controller_attempted": bool(controller_meta.get("attempted")),
        "controller_fallback": bool(controller_meta.get("fallback")),
        "controller_low_confidence": bool(controller_meta.get("low_confidence")),
        "controller_used_reason": controller_meta.get("used_reason"),
        "controller_confidence": controller_meta.get("confidence"),
        "controller_error": controller_meta.get("error"),
        "controller_goal": controller_meta.get("goal"),
        "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
    }


def _router_observability_updates_from_class_router(
    class_router_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(class_router_result, dict):
        return {}
    controller_meta = class_router_result.get("controller")
    if not isinstance(controller_meta, dict):
        return {}
    attempted = bool(controller_meta.get("attempted"))
    reason = "none" if attempted else "not_run"
    return _router_observability_meta(eligible=attempted, reason=reason)


__all__ = [
    "CONSULT_INTERRUPT_INTENTS",
    "CONTROLLER_CONFIDENCE_THRESHOLD",
    "DomainIntent",
    "_build_controller_meta_output",
    "build_observer_class_router_result",
    "_controller_meta_updates_from_class_router",
    "_ensure_controller_output_meta",
    "_normalize_class_name",
    "_normalize_controller_fallback_reason",
    "_resolve_class_router_result",
    "_resolve_controller_signal_class",
    "_router_observability_updates_from_class_router",
]
