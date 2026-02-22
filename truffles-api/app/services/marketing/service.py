from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    ConversationHumanLock,
    MarketingCampaign,
    MarketingCampaignDelivery,
    MarketingCampaignRecipient,
    MarketingConsent,
    MarketingDeliveryEvent,
    MarketingSuppression,
    Message,
    OutboxMessage,
    User,
)
from app.models.appointment import Appointment
from app.services.health_service import build_outbox_health_snapshot
from app.services.provider_error_policy import classify_provider_error

MARKETING_SEGMENT_REACTIVATION_30_120 = "reactivation_30_120"
MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D = "no_show_recovery_14d"
MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D = "engaged_no_booking_7d"
MARKETING_SEGMENT_CODES = {
    MARKETING_SEGMENT_REACTIVATION_30_120,
    MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D,
    MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D,
}

MARKETING_STATUS_DRAFT = "draft"
MARKETING_STATUS_IN_REVIEW = "in_review"
MARKETING_STATUS_APPROVED = "approved"
MARKETING_STATUS_SCHEDULED = "scheduled"
MARKETING_STATUS_RUNNING = "running"
MARKETING_STATUS_PAUSED = "paused"
MARKETING_STATUS_COMPLETED = "completed"
MARKETING_STATUS_CANCELLED = "cancelled"
MARKETING_STATUS_FAILED = "failed"
MARKETING_STATUS_CANONICAL_VALUES = {
    MARKETING_STATUS_DRAFT,
    MARKETING_STATUS_IN_REVIEW,
    MARKETING_STATUS_APPROVED,
    MARKETING_STATUS_SCHEDULED,
    MARKETING_STATUS_RUNNING,
    MARKETING_STATUS_PAUSED,
    MARKETING_STATUS_COMPLETED,
    MARKETING_STATUS_CANCELLED,
    MARKETING_STATUS_FAILED,
}
MARKETING_STATUS_VALUES = {
    *MARKETING_STATUS_CANONICAL_VALUES,
    # Backward-compat statuses from Wave 3.
    "ready",
    "executed",
}
MARKETING_LEGACY_STATUS_MAP = {
    "ready": MARKETING_STATUS_APPROVED,
    "executed": MARKETING_STATUS_COMPLETED,
}

MARKETING_FREQUENCY_CAP_DAYS = 7
MARKETING_PERMANENT_FAILURE_LOOKBACK_DAYS = 90
MARKETING_TEMPLATE_GATE_ENABLED_ENV = "MARKETING_TEMPLATE_GATE_ENABLED"
MARKETING_TEMPLATE_APPROVED_STATES = {"approved", "active", "ready"}
MARKETING_PREVIEW_ENGAGEMENT_LOOKBACK_DAYS = 7
MARKETING_BILLING_BLOCK_LOOKBACK_HOURS = 24
MARKETING_BILLING_BLOCK_SAMPLE_LIMIT = 500
_SERVICE_PRICING_INTENT_SIGNALS = {
    "pricing",
    "price_query",
    "catalog.service_query",
    "service_match",
    "services_overview",
    "service_duration",
    "service_clarify",
}

_CANCELLED_APPOINTMENT_STATUSES = {"CANCELLED", "CANCELED", "cancelled", "canceled"}
_NO_SHOW_APPOINTMENT_STATUSES = {"NO_SHOW", "no_show"}
_TRANSITIONS: dict[str, set[str]] = {
    MARKETING_STATUS_DRAFT: {MARKETING_STATUS_IN_REVIEW, MARKETING_STATUS_CANCELLED},
    "ready": {MARKETING_STATUS_IN_REVIEW, MARKETING_STATUS_APPROVED, MARKETING_STATUS_CANCELLED},
    MARKETING_STATUS_IN_REVIEW: {MARKETING_STATUS_DRAFT, MARKETING_STATUS_APPROVED, MARKETING_STATUS_CANCELLED},
    MARKETING_STATUS_APPROVED: {
        MARKETING_STATUS_SCHEDULED,
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_PAUSED,
        MARKETING_STATUS_CANCELLED,
    },
    MARKETING_STATUS_SCHEDULED: {MARKETING_STATUS_RUNNING, MARKETING_STATUS_PAUSED, MARKETING_STATUS_CANCELLED},
    MARKETING_STATUS_RUNNING: {
        MARKETING_STATUS_COMPLETED,
        MARKETING_STATUS_PAUSED,
        MARKETING_STATUS_FAILED,
        MARKETING_STATUS_CANCELLED,
    },
    "executed": {
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_PAUSED,
        MARKETING_STATUS_COMPLETED,
        MARKETING_STATUS_FAILED,
        MARKETING_STATUS_CANCELLED,
    },
    MARKETING_STATUS_PAUSED: {
        MARKETING_STATUS_APPROVED,
        MARKETING_STATUS_SCHEDULED,
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_CANCELLED,
    },
}

_SEGMENT_DEFAULTS_REACTIVATION = {
    "min_days_since_last_visit": 30,
    "max_days_since_last_visit": 120,
    "require_no_future_booking": True,
}
_SEGMENT_DEFAULTS_NO_SHOW = {
    "no_show_window_days": 14,
    "min_no_show_count": 1,
    "require_no_future_booking": True,
}
_SEGMENT_DEFAULTS_ENGAGED = {
    "engagement_window_days": 7,
    "require_no_future_booking": True,
}

MARKETING_SEGMENT_PARAM_DEFAULTS: dict[str, dict[str, Any]] = {
    MARKETING_SEGMENT_REACTIVATION_30_120: dict(_SEGMENT_DEFAULTS_REACTIVATION),
    MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D: dict(_SEGMENT_DEFAULTS_NO_SHOW),
    MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D: dict(_SEGMENT_DEFAULTS_ENGAGED),
}


def _to_int(value: Any, default_value: int) -> int:
    if value is None:
        return default_value
    if isinstance(value, bool):
        return default_value
    try:
        return int(value)
    except Exception:
        return default_value


def _to_bool(value: Any, default_value: bool) -> bool:
    if value is None:
        return default_value
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default_value


def _resolve_segment_params_container(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def normalize_marketing_segment_params(
    segment_code: str,
    raw_params: Any,
    *,
    strict: bool = True,
) -> dict[str, Any]:
    if segment_code not in MARKETING_SEGMENT_CODES:
        raise ValueError("unsupported_segment")

    raw_map = _resolve_segment_params_container(raw_params)
    defaults = MARKETING_SEGMENT_PARAM_DEFAULTS.get(segment_code, {})

    if segment_code == MARKETING_SEGMENT_REACTIVATION_30_120:
        allowed_keys = {"min_days_since_last_visit", "max_days_since_last_visit", "require_no_future_booking"}
        if strict:
            unknown_keys = sorted(set(raw_map.keys()) - allowed_keys)
            if unknown_keys:
                raise ValueError("invalid_segment_params_keys")
        min_days = _to_int(raw_map.get("min_days_since_last_visit"), int(defaults["min_days_since_last_visit"]))
        max_days = _to_int(raw_map.get("max_days_since_last_visit"), int(defaults["max_days_since_last_visit"]))
        require_no_future = _to_bool(raw_map.get("require_no_future_booking"), bool(defaults["require_no_future_booking"]))
        if min_days < 1 or min_days > 3650:
            raise ValueError("invalid_min_days_since_last_visit")
        if max_days < 1 or max_days > 3650:
            raise ValueError("invalid_max_days_since_last_visit")
        if min_days > max_days:
            raise ValueError("invalid_reactivation_window")
        return {
            "min_days_since_last_visit": min_days,
            "max_days_since_last_visit": max_days,
            "require_no_future_booking": require_no_future,
        }

    if segment_code == MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D:
        allowed_keys = {"no_show_window_days", "min_no_show_count", "require_no_future_booking"}
        if strict:
            unknown_keys = sorted(set(raw_map.keys()) - allowed_keys)
            if unknown_keys:
                raise ValueError("invalid_segment_params_keys")
        no_show_window_days = _to_int(raw_map.get("no_show_window_days"), int(defaults["no_show_window_days"]))
        min_no_show_count = _to_int(raw_map.get("min_no_show_count"), int(defaults["min_no_show_count"]))
        require_no_future = _to_bool(raw_map.get("require_no_future_booking"), bool(defaults["require_no_future_booking"]))
        if no_show_window_days < 1 or no_show_window_days > 365:
            raise ValueError("invalid_no_show_window_days")
        if min_no_show_count < 1 or min_no_show_count > 10:
            raise ValueError("invalid_min_no_show_count")
        return {
            "no_show_window_days": no_show_window_days,
            "min_no_show_count": min_no_show_count,
            "require_no_future_booking": require_no_future,
        }

    if segment_code == MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D:
        allowed_keys = {"engagement_window_days", "require_no_future_booking"}
        if strict:
            unknown_keys = sorted(set(raw_map.keys()) - allowed_keys)
            if unknown_keys:
                raise ValueError("invalid_segment_params_keys")
        engagement_window_days = _to_int(raw_map.get("engagement_window_days"), int(defaults["engagement_window_days"]))
        require_no_future = _to_bool(raw_map.get("require_no_future_booking"), bool(defaults["require_no_future_booking"]))
        if engagement_window_days < 1 or engagement_window_days > 90:
            raise ValueError("invalid_engagement_window_days")
        return {
            "engagement_window_days": engagement_window_days,
            "require_no_future_booking": require_no_future,
        }

    return dict(defaults)


def build_marketing_segment_summary(segment_code: str, segment_params: Any) -> str:
    params = normalize_marketing_segment_params(segment_code, segment_params, strict=False)
    if segment_code == MARKETING_SEGMENT_REACTIVATION_30_120:
        return (
            "Клиенты без будущей записи, у которых последний визит был "
            f"{params['min_days_since_last_visit']}-{params['max_days_since_last_visit']} дней назад."
        )
    if segment_code == MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D:
        return (
            "Клиенты с no-show за последние "
            f"{params['no_show_window_days']} дней (минимум {params['min_no_show_count']}), без будущей записи."
        )
    if segment_code == MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D:
        return (
            "Клиенты с интересом к услугам/ценам за последние "
            f"{params['engagement_window_days']} дней, без будущей записи."
        )
    return "Сегмент аудитории"


def resolve_campaign_segment_params(
    campaign: MarketingCampaign,
    *,
    segment_code: str,
    override_params: Any = None,
    strict: bool = False,
) -> dict[str, Any]:
    if override_params is not None:
        return normalize_marketing_segment_params(segment_code, override_params, strict=strict)
    audience_filter = campaign.audience_filter if isinstance(campaign.audience_filter, dict) else {}
    raw_segment_params = audience_filter.get("segment_params")
    return normalize_marketing_segment_params(segment_code, raw_segment_params, strict=strict)


def get_marketing_segment_catalog() -> list[dict[str, Any]]:
    return [
        {
            "code": MARKETING_SEGMENT_REACTIVATION_30_120,
            "label": "Возврат клиентов",
            "short_label": "Возврат",
            "description": "Вернуть клиентов, которые давно не были и пока не записались снова.",
            "defaults": dict(_SEGMENT_DEFAULTS_REACTIVATION),
            "summary": build_marketing_segment_summary(
                MARKETING_SEGMENT_REACTIVATION_30_120,
                _SEGMENT_DEFAULTS_REACTIVATION,
            ),
            "editable_fields": [
                {
                    "key": "min_days_since_last_visit",
                    "label": "От, дней после визита",
                    "type": "int",
                    "min": 1,
                    "max": 3650,
                    "step": 1,
                },
                {
                    "key": "max_days_since_last_visit",
                    "label": "До, дней после визита",
                    "type": "int",
                    "min": 1,
                    "max": 3650,
                    "step": 1,
                },
                {
                    "key": "require_no_future_booking",
                    "label": "Только без будущей записи",
                    "type": "bool",
                },
            ],
        },
        {
            "code": MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D,
            "label": "После no-show",
            "short_label": "No-show",
            "description": "Догнать клиентов, которые не пришли, и вернуть их в расписание.",
            "defaults": dict(_SEGMENT_DEFAULTS_NO_SHOW),
            "summary": build_marketing_segment_summary(
                MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D,
                _SEGMENT_DEFAULTS_NO_SHOW,
            ),
            "editable_fields": [
                {
                    "key": "no_show_window_days",
                    "label": "Период поиска no-show, дней",
                    "type": "int",
                    "min": 1,
                    "max": 365,
                    "step": 1,
                },
                {
                    "key": "min_no_show_count",
                    "label": "Минимум no-show за период",
                    "type": "int",
                    "min": 1,
                    "max": 10,
                    "step": 1,
                },
                {
                    "key": "require_no_future_booking",
                    "label": "Только без будущей записи",
                    "type": "bool",
                },
            ],
        },
        {
            "code": MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D,
            "label": "Интерес без записи",
            "short_label": "Интерес",
            "description": "Клиенты, которые задавали вопросы по услугам/ценам, но не записались.",
            "defaults": dict(_SEGMENT_DEFAULTS_ENGAGED),
            "summary": build_marketing_segment_summary(
                MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D,
                _SEGMENT_DEFAULTS_ENGAGED,
            ),
            "editable_fields": [
                {
                    "key": "engagement_window_days",
                    "label": "Период интереса, дней",
                    "type": "int",
                    "min": 1,
                    "max": 90,
                    "step": 1,
                },
                {
                    "key": "require_no_future_booking",
                    "label": "Только без будущей записи",
                    "type": "bool",
                },
            ],
        },
    ]


def describe_marketing_reason_code(reason_code: str) -> str:
    value = (reason_code or "").strip()
    if not value:
        return ""
    if value.startswith("segment="):
        segment = value.split("=", 1)[1].strip()
        return {
            MARKETING_SEGMENT_REACTIVATION_30_120: "Подходит под сегмент возврата клиентов.",
            MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D: "Подходит под сегмент после no-show.",
            MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D: "Подходит под сегмент интереса без записи.",
        }.get(segment, "Подходит под выбранный сегмент.")
    if value.startswith("last_visit_days="):
        return f"Последний визит: {value.split('=', 1)[1].strip()} дней назад."
    if value.startswith("no_show_count=") or value.startswith("no_show_window_count="):
        return f"Количество no-show за период: {value.split('=', 1)[1].strip()}."
    if value.startswith("engagement_days="):
        return f"Последний интерес к услугам/ценам: {value.split('=', 1)[1].strip()} дней назад."
    if value.startswith("engagement_signal="):
        signal = value.split("=", 1)[1].strip()
        return f"Обнаружен сигнал интереса ({signal})."
    if value == "no_future_booking=true":
        return "Нет будущей записи."
    return value.replace("_", " ")


def describe_marketing_suppression_reason(reason_code: str) -> str:
    value = (reason_code or "").strip()
    if not value:
        return ""
    if value == "consent:opt_out":
        return "Клиент запретил маркетинговые сообщения (opt-out)."
    if value.startswith("suppression:"):
        reason = value.split(":", 1)[1].strip().replace("_", " ")
        return f"Контакт в списке исключений: {reason}."
    if value == "state:human_lock_active":
        return "Диалог на ручной обработке менеджером."
    if value.startswith("frequency_cap:"):
        period = value.split(":", 1)[1].strip()
        return f"Ограничение частоты рассылки: не чаще 1 раза за {period}."
    if value == "provider:permanent_failure_history":
        return "Ранее были постоянные ошибки доставки по контакту."
    return value.replace("_", " ")


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def normalize_marketing_status(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized in MARKETING_STATUS_CANONICAL_VALUES:
        return normalized
    return MARKETING_LEGACY_STATUS_MAP.get(normalized, MARKETING_STATUS_DRAFT)


def resolve_marketing_campaign_status(campaign: MarketingCampaign) -> str:
    status_v2 = getattr(campaign, "status_v2", None)
    if isinstance(status_v2, str) and status_v2 in MARKETING_STATUS_CANONICAL_VALUES:
        return status_v2
    return normalize_marketing_status(getattr(campaign, "status", None))


def _set_campaign_status(campaign: MarketingCampaign, status: str) -> None:
    canonical = normalize_marketing_status(status)
    campaign.status = canonical
    campaign.status_v2 = canonical


def check_marketing_transition(current_status: str, target_status: str) -> bool:
    if current_status == target_status:
        return True
    allowed = _TRANSITIONS.get(current_status)
    if not allowed:
        return False
    return target_status in allowed


def _normalize_jid(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _is_cancelled_appointment_status(value: Optional[str]) -> bool:
    return (value or "").strip() in _CANCELLED_APPOINTMENT_STATUSES


def _days_since(when: Optional[datetime], *, now: datetime) -> Optional[int]:
    if not when:
        return None
    delta = now - when
    return max(int(delta.total_seconds() // 86400), 0)


def _metadata_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return [normalized] if normalized else []
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            if isinstance(item, str):
                normalized = item.strip().lower()
                if normalized:
                    values.append(normalized)
        return values
    return []


def _message_has_service_or_pricing_signal(*, intent: Optional[str], metadata: Any) -> tuple[bool, Optional[str]]:
    normalized_intent = (intent or "").strip().lower()
    if normalized_intent in _SERVICE_PRICING_INTENT_SIGNALS:
        return True, f"intent:{normalized_intent}"
    if normalized_intent.startswith("pricing") or normalized_intent.startswith("service_"):
        return True, f"intent:{normalized_intent}"

    if not isinstance(metadata, dict):
        return False, None

    service_query = metadata.get("service_query")
    if isinstance(service_query, str) and service_query.strip():
        return True, "meta:service_query"

    info_sections = _metadata_string_list(metadata.get("info_sections"))
    if any(value == "pricing" or value.startswith("service") for value in info_sections):
        return True, "meta:info_sections"

    booking_info_intents = _metadata_string_list(metadata.get("booking_info_intents"))
    if any(value == "pricing" or value.startswith("service") for value in booking_info_intents):
        return True, "meta:booking_info_intents"

    intents = _metadata_string_list(metadata.get("intents"))
    if any(value == "pricing" or value.startswith("service") for value in intents):
        return True, "meta:intents"

    secondary_intents = _metadata_string_list(metadata.get("secondary_intents"))
    if any(value == "pricing" or value.startswith("service") for value in secondary_intents):
        return True, "meta:secondary_intents"

    return False, None


def _load_recent_service_pricing_engagement(
    db: Session,
    *,
    client_id: UUID,
    conversation_ids: set[UUID],
    now: datetime,
    lookback_days: int,
) -> dict[UUID, dict[str, Any]]:
    if not conversation_ids:
        return {}

    cutoff = now - timedelta(days=max(lookback_days, 1))
    rows = (
        db.query(
            Message.conversation_id,
            Message.created_at,
            Message.intent,
            Message.message_metadata,
        )
        .filter(
            Message.client_id == client_id,
            Message.role == "user",
            Message.conversation_id.in_(conversation_ids),
            Message.created_at >= cutoff,
        )
        .order_by(Message.created_at.desc())
        .all()
    )

    by_conversation: dict[UUID, dict[str, Any]] = {}
    for row in rows:
        conversation_id = row.conversation_id
        if conversation_id in by_conversation:
            continue
        has_signal, signal_source = _message_has_service_or_pricing_signal(
            intent=row.intent,
            metadata=row.message_metadata,
        )
        if not has_signal:
            continue
        by_conversation[conversation_id] = {
            "engaged": True,
            "last_engaged_at": row.created_at,
            "signal": signal_source or "unknown",
        }
    return by_conversation


def _load_candidate_conversations(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
) -> list[dict[str, Any]]:
    rows = (
        db.query(
            Conversation.id.label("conversation_id"),
            Conversation.user_id.label("user_id"),
            Conversation.last_message_at.label("last_message_at"),
            User.remote_jid.label("recipient_jid"),
        )
        .join(User, User.id == Conversation.user_id)
        .filter(
            Conversation.client_id == client_id,
            Conversation.branch_id == branch_id,
            Conversation.channel == "whatsapp",
            User.remote_jid.isnot(None),
            func.length(func.trim(User.remote_jid)) > 0,
        )
        .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
        .all()
    )
    by_jid: dict[str, dict[str, Any]] = {}
    for row in rows:
        normalized_jid = _normalize_jid(row.recipient_jid)
        if not normalized_jid or normalized_jid in by_jid:
            continue
        by_jid[normalized_jid] = {
            "recipient_jid": row.recipient_jid,
            "user_id": row.user_id,
            "conversation_id": row.conversation_id,
            "last_message_at": row.last_message_at,
        }
    return list(by_jid.values())


def _load_appointment_stats(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    user_ids: set[UUID],
    now: datetime,
    no_show_window_days: int = 14,
) -> dict[UUID, dict[str, Any]]:
    if not user_ids:
        return {}

    stats: dict[UUID, dict[str, Any]] = {
        user_id: {"last_visit_at": None, "future_count": 0, "no_show_window_count": 0}
        for user_id in user_ids
    }
    base_query = db.query(Appointment).filter(
        Appointment.client_id == client_id,
        Appointment.branch_id == branch_id,
        Appointment.user_id.in_(user_ids),
    )

    past_rows = (
        db.query(
            Appointment.user_id,
            func.max(Appointment.start_at).label("last_visit_at"),
        )
        .filter(
            Appointment.client_id == client_id,
            Appointment.branch_id == branch_id,
            Appointment.user_id.in_(user_ids),
            Appointment.start_at <= now,
            ~Appointment.status.in_(_CANCELLED_APPOINTMENT_STATUSES),
        )
        .group_by(Appointment.user_id)
        .all()
    )
    for row in past_rows:
        if row.user_id in stats:
            stats[row.user_id]["last_visit_at"] = row.last_visit_at

    future_rows = (
        db.query(
            Appointment.user_id,
            func.count(Appointment.id).label("future_count"),
        )
        .filter(
            Appointment.client_id == client_id,
            Appointment.branch_id == branch_id,
            Appointment.user_id.in_(user_ids),
            Appointment.start_at > now,
            ~Appointment.status.in_(_CANCELLED_APPOINTMENT_STATUSES),
        )
        .group_by(Appointment.user_id)
        .all()
    )
    for row in future_rows:
        if row.user_id in stats:
            stats[row.user_id]["future_count"] = int(row.future_count or 0)

    no_show_cutoff = now - timedelta(days=max(int(no_show_window_days), 1))
    no_show_rows = (
        db.query(
            Appointment.user_id,
            func.count(Appointment.id).label("no_show_count"),
        )
        .filter(
            Appointment.client_id == client_id,
            Appointment.branch_id == branch_id,
            Appointment.user_id.in_(user_ids),
            Appointment.start_at >= no_show_cutoff,
            Appointment.status.in_(_NO_SHOW_APPOINTMENT_STATUSES),
        )
        .group_by(Appointment.user_id)
        .all()
    )
    for row in no_show_rows:
        if row.user_id in stats:
            stats[row.user_id]["no_show_window_count"] = int(row.no_show_count or 0)

    return stats


def _matches_segment(
    *,
    segment_code: str,
    segment_params: dict[str, Any],
    stats: dict[str, Any],
    engagement: Optional[dict[str, Any]],
    now: datetime,
) -> tuple[bool, list[str]]:
    last_visit_at = stats.get("last_visit_at")
    future_count = int(stats.get("future_count") or 0)
    no_show_window_count = int(stats.get("no_show_window_count") or 0)
    days_since_last_visit = _days_since(last_visit_at, now=now)
    reason_codes: list[str] = []

    if segment_code == MARKETING_SEGMENT_REACTIVATION_30_120:
        min_days_since_last_visit = int(segment_params.get("min_days_since_last_visit") or 30)
        max_days_since_last_visit = int(segment_params.get("max_days_since_last_visit") or 120)
        require_no_future_booking = bool(segment_params.get("require_no_future_booking", True))
        if days_since_last_visit is None:
            return False, []
        if days_since_last_visit < min_days_since_last_visit or days_since_last_visit > max_days_since_last_visit:
            return False, []
        if require_no_future_booking and future_count > 0:
            return False, []
        reason_codes.extend(
            [
                "segment=reactivation_30_120",
                f"last_visit_days={days_since_last_visit}",
                f"window_days={min_days_since_last_visit}-{max_days_since_last_visit}",
            ]
        )
        if require_no_future_booking:
            reason_codes.append("no_future_booking=true")
        return True, reason_codes

    if segment_code == MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D:
        min_no_show_count = int(segment_params.get("min_no_show_count") or 1)
        no_show_window_days = int(segment_params.get("no_show_window_days") or 14)
        require_no_future_booking = bool(segment_params.get("require_no_future_booking", True))
        if no_show_window_count < min_no_show_count:
            return False, []
        if require_no_future_booking and future_count > 0:
            return False, []
        reason_codes.extend(
            [
                "segment=no_show_recovery_14d",
                f"no_show_window_count={no_show_window_count}",
                f"no_show_window_days={no_show_window_days}",
                f"min_no_show_count={min_no_show_count}",
            ]
        )
        if require_no_future_booking:
            reason_codes.append("no_future_booking=true")
        return True, reason_codes

    if segment_code == MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D:
        engagement_window_days = int(segment_params.get("engagement_window_days") or MARKETING_PREVIEW_ENGAGEMENT_LOOKBACK_DAYS)
        require_no_future_booking = bool(segment_params.get("require_no_future_booking", True))
        if not engagement or not bool(engagement.get("engaged")):
            return False, []
        if require_no_future_booking and future_count > 0:
            return False, []
        last_engaged_at = engagement.get("last_engaged_at")
        days_since_message = _days_since(last_engaged_at, now=now)
        if days_since_message is None or days_since_message > engagement_window_days:
            return False, []
        signal = str(engagement.get("signal") or "unknown")
        reason_codes.extend(
            [
                "segment=engaged_no_booking_7d",
                f"engagement_signal={signal}",
                f"engagement_window_days={engagement_window_days}",
            ]
        )
        if require_no_future_booking:
            reason_codes.append("no_future_booking=true")
        if days_since_message is not None:
            reason_codes.append(f"engagement_days={days_since_message}")
        return True, reason_codes

    return False, []


def _load_latest_consent_map(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
) -> dict[str, str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return {}
    rows = (
        db.query(MarketingConsent)
        .filter(
            MarketingConsent.client_id == client_id,
            MarketingConsent.active.is_(True),
            MarketingConsent.recipient_jid.in_(normalized),
        )
        .order_by(MarketingConsent.changed_at.desc(), MarketingConsent.id.desc())
        .all()
    )
    resolved: dict[str, str] = {}
    for row in rows:
        jid = _normalize_jid(row.recipient_jid)
        if jid and jid not in resolved:
            resolved[jid] = (row.status or "").strip()
    return resolved


def _load_active_suppressions(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> dict[str, list[str]]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return {}
    rows = (
        db.query(MarketingSuppression)
        .filter(
            MarketingSuppression.client_id == client_id,
            MarketingSuppression.active.is_(True),
            MarketingSuppression.recipient_jid.in_(normalized),
            or_(MarketingSuppression.expires_at.is_(None), MarketingSuppression.expires_at > now),
        )
        .all()
    )
    mapped: dict[str, list[str]] = {}
    for row in rows:
        jid = _normalize_jid(row.recipient_jid)
        if not jid:
            continue
        mapped.setdefault(jid, []).append(f"suppression:{row.reason}")
    return mapped


def _load_active_human_locks(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> set[str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return set()
    rows = (
        db.query(ConversationHumanLock.remote_jid)
        .filter(
            ConversationHumanLock.client_id == client_id,
            ConversationHumanLock.remote_jid.in_(normalized),
            ConversationHumanLock.lock_until > now,
        )
        .all()
    )
    return {_normalize_jid(row[0]) for row in rows if row and row[0]}


def _load_recent_marketing_touch_jids(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> set[str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return set()
    cutoff = now - timedelta(days=MARKETING_FREQUENCY_CAP_DAYS)
    rows = (
        db.query(User.remote_jid)
        .join(Conversation, Conversation.user_id == User.id)
        .join(OutboxMessage, OutboxMessage.conversation_id == Conversation.id)
        .filter(
            Conversation.client_id == client_id,
            OutboxMessage.client_id == client_id,
            OutboxMessage.created_at >= cutoff,
            OutboxMessage.meta["source"].astext == "marketing_campaign",
            User.remote_jid.in_(normalized),
        )
        .all()
    )
    return {_normalize_jid(row[0]) for row in rows if row and row[0]}


def _load_permanent_failure_jids(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> set[str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return set()
    cutoff = now - timedelta(days=MARKETING_PERMANENT_FAILURE_LOOKBACK_DAYS)
    rows = (
        db.query(User.remote_jid, OutboxMessage.last_error)
        .join(Conversation, Conversation.user_id == User.id)
        .join(OutboxMessage, OutboxMessage.conversation_id == Conversation.id)
        .filter(
            Conversation.client_id == client_id,
            OutboxMessage.client_id == client_id,
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= cutoff,
            User.remote_jid.in_(normalized),
        )
        .all()
    )
    permanent: set[str] = set()
    for jid, last_error in rows:
        normalized_jid = _normalize_jid(jid)
        if not normalized_jid:
            continue
        classification = classify_provider_error(last_error)
        if not classification.retryable:
            permanent.add(normalized_jid)
    return permanent


def _count_recent_provider_billing_blocked_failures(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    now: datetime,
) -> int:
    cutoff = now - timedelta(hours=MARKETING_BILLING_BLOCK_LOOKBACK_HOURS)
    rows = (
        db.query(OutboxMessage.last_error)
        .join(Conversation, Conversation.id == OutboxMessage.conversation_id)
        .filter(
            OutboxMessage.client_id == client_id,
            Conversation.client_id == client_id,
            Conversation.branch_id == branch_id,
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= cutoff,
            OutboxMessage.last_error.isnot(None),
        )
        .order_by(OutboxMessage.created_at.desc())
        .limit(MARKETING_BILLING_BLOCK_SAMPLE_LIMIT)
        .all()
    )
    count = 0
    for row in rows:
        error_text = row[0] if isinstance(row, tuple) else getattr(row, "last_error", None)
        if classify_provider_error(error_text).kind == "billing_blocked":
            count += 1
    return count


def _resolve_suppression_reasons(
    *,
    consent_status: Optional[str],
    explicit_suppressions: list[str],
    human_lock: bool,
    frequency_cap_hit: bool,
    permanent_failure: bool,
) -> list[str]:
    reasons: list[str] = []
    if (consent_status or "").strip() == "opt_out":
        reasons.append("consent:opt_out")
    reasons.extend(explicit_suppressions)
    if human_lock:
        reasons.append("state:human_lock_active")
    if frequency_cap_hit:
        reasons.append(f"frequency_cap:{MARKETING_FREQUENCY_CAP_DAYS}d")
    if permanent_failure:
        reasons.append("provider:permanent_failure_history")
    return reasons


def _resolve_effective_delivery_status(delivery_status: Optional[str], outbox_status: Optional[str]) -> str:
    normalized_delivery = (delivery_status or "").strip().lower()
    if normalized_delivery == "replied":
        return "replied"
    normalized_outbox = (outbox_status or "").strip().upper()
    if normalized_outbox == "SENT":
        return "sent"
    if normalized_outbox == "FAILED":
        return "failed"
    if normalized_delivery in {"queued", "sent", "failed", "replied"}:
        return normalized_delivery
    return "queued"


def derive_marketing_terminal_status(
    *,
    queued_count: int,
    failed_count: int,
    total_count: int,
) -> Optional[str]:
    if total_count <= 0 or queued_count > 0:
        return None
    if failed_count > 0:
        return MARKETING_STATUS_FAILED
    return MARKETING_STATUS_COMPLETED


def _campaign_template_state(campaign: MarketingCampaign) -> Optional[str]:
    for source in (campaign.audience_filter, campaign.preflight_snapshot):
        if not isinstance(source, dict):
            continue
        value = source.get("template_state")
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def refresh_marketing_campaign_lifecycle(
    db: Session,
    *,
    campaign: MarketingCampaign,
    now: Optional[datetime] = None,
) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    rows = (
        db.query(
            MarketingCampaignDelivery.status.label("delivery_status"),
            OutboxMessage.status.label("outbox_status"),
        )
        .outerjoin(OutboxMessage, OutboxMessage.id == MarketingCampaignDelivery.outbox_id)
        .filter(MarketingCampaignDelivery.campaign_id == campaign.id)
        .all()
    )

    counts = {"queued": 0, "sent": 0, "failed": 0, "replied": 0}
    for row in rows:
        status_value = _resolve_effective_delivery_status(
            getattr(row, "delivery_status", None),
            getattr(row, "outbox_status", None),
        )
        counts[status_value] += 1

    terminal_status = derive_marketing_terminal_status(
        queued_count=counts["queued"],
        failed_count=counts["failed"],
        total_count=sum(counts.values()),
    )
    current_status = resolve_marketing_campaign_status(campaign)
    if terminal_status and current_status not in {
        MARKETING_STATUS_COMPLETED,
        MARKETING_STATUS_FAILED,
        MARKETING_STATUS_CANCELLED,
    }:
        _set_campaign_status(campaign, terminal_status)
        campaign.run_completed_at = now
        campaign.updated_at = now
        db.add(campaign)
        db.flush()
    elif counts["queued"] > 0 and current_status not in {
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_COMPLETED,
        MARKETING_STATUS_FAILED,
        MARKETING_STATUS_CANCELLED,
    }:
        _set_campaign_status(campaign, MARKETING_STATUS_RUNNING)
        campaign.updated_at = now
        db.add(campaign)
        db.flush()
    return counts


def materialize_marketing_campaign_audience(
    db: Session,
    *,
    campaign: MarketingCampaign,
    segment_code: str,
    sample_limit: int,
    now: Optional[datetime] = None,
    segment_params: Any = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if segment_code not in MARKETING_SEGMENT_CODES:
        raise ValueError("unsupported_segment")
    effective_segment_params = resolve_campaign_segment_params(
        campaign,
        segment_code=segment_code,
        override_params=segment_params,
        strict=False,
    )
    segment_summary = build_marketing_segment_summary(segment_code, effective_segment_params)

    candidates = _load_candidate_conversations(
        db,
        client_id=campaign.client_id,
        branch_id=campaign.branch_id,
    )
    user_ids = {candidate["user_id"] for candidate in candidates if candidate.get("user_id")}
    no_show_window_days = int(effective_segment_params.get("no_show_window_days") or 14)
    stats_by_user = _load_appointment_stats(
        db,
        client_id=campaign.client_id,
        branch_id=campaign.branch_id,
        user_ids=user_ids,
        now=now,
        no_show_window_days=no_show_window_days,
    )
    conversation_ids = {candidate["conversation_id"] for candidate in candidates if candidate.get("conversation_id")}
    engagement_window_days = int(
        effective_segment_params.get("engagement_window_days") or MARKETING_PREVIEW_ENGAGEMENT_LOOKBACK_DAYS
    )
    engagement_by_conversation = _load_recent_service_pricing_engagement(
        db,
        client_id=campaign.client_id,
        conversation_ids=conversation_ids,
        now=now,
        lookback_days=engagement_window_days,
    )

    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        user_id = candidate.get("user_id")
        stats = stats_by_user.get(user_id, {"last_visit_at": None, "future_count": 0, "no_show_window_count": 0})
        engagement = engagement_by_conversation.get(candidate.get("conversation_id"))
        matches, reason_codes = _matches_segment(
            segment_code=segment_code,
            segment_params=effective_segment_params,
            stats=stats,
            engagement=engagement,
            now=now,
        )
        if not matches:
            continue
        selected.append(
            {
                **candidate,
                "reason_codes": reason_codes,
            }
        )

    recipient_jids = [item["recipient_jid"] for item in selected]
    consent_by_jid = _load_latest_consent_map(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
    )
    suppressions_by_jid = _load_active_suppressions(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )
    human_lock_jids = _load_active_human_locks(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )
    frequency_cap_jids = _load_recent_marketing_touch_jids(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )
    permanent_failure_jids = _load_permanent_failure_jids(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )

    db.query(MarketingCampaignRecipient).filter(MarketingCampaignRecipient.campaign_id == campaign.id).delete()

    suppressed_count = 0
    suppression_reason_counts: dict[str, int] = {}
    for item in selected:
        normalized_jid = _normalize_jid(item["recipient_jid"])
        suppression_reasons = _resolve_suppression_reasons(
            consent_status=consent_by_jid.get(normalized_jid),
            explicit_suppressions=suppressions_by_jid.get(normalized_jid, []),
            human_lock=normalized_jid in human_lock_jids,
            frequency_cap_hit=normalized_jid in frequency_cap_jids,
            permanent_failure=normalized_jid in permanent_failure_jids,
        )
        suppressed = len(suppression_reasons) > 0
        if suppressed:
            suppressed_count += 1
            for reason in set(suppression_reasons):
                suppression_reason_counts[reason] = suppression_reason_counts.get(reason, 0) + 1
        db.add(
            MarketingCampaignRecipient(
                campaign_id=campaign.id,
                client_id=campaign.client_id,
                branch_id=campaign.branch_id,
                user_id=item.get("user_id"),
                conversation_id=item.get("conversation_id"),
                recipient_jid=item["recipient_jid"],
                segment_code=segment_code,
                reason_codes=item["reason_codes"],
                suppressed=suppressed,
                suppression_reasons=suppression_reasons,
                created_at=now,
                updated_at=now,
            )
        )

    candidate_count = len(candidates)
    matched_count = len(selected)
    segment_excluded_count = max(candidate_count - matched_count, 0)
    preview_stats = {
        "candidate_count": candidate_count,
        "matched_count": matched_count,
        "segment_excluded_count": segment_excluded_count,
        "eligible_count": max(matched_count - suppressed_count, 0),
        "suppressed_count": suppressed_count,
        "suppression_reason_counts": suppression_reason_counts,
    }
    campaign.segment_code = segment_code
    campaign.preview_total = len(selected)
    campaign.last_preview_at = now
    campaign.preflight_valid = False
    campaign.preflight_snapshot = {
        "generated_at": now.isoformat(),
        "reason": "preview_refresh_required_before_execute",
        "eligible_count": preview_stats["eligible_count"],
        "suppressed_count": suppressed_count,
        "preview_stats": preview_stats,
    }
    audience_filter = campaign.audience_filter if isinstance(campaign.audience_filter, dict) else {}
    campaign.audience_filter = {
        **audience_filter,
        "segment_params": effective_segment_params,
        "segment_summary": segment_summary,
        "preview_stats": preview_stats,
    }
    campaign.updated_at = now
    db.add(campaign)
    db.flush()

    preview_rows = (
        db.query(MarketingCampaignRecipient)
        .filter(MarketingCampaignRecipient.campaign_id == campaign.id)
        .order_by(MarketingCampaignRecipient.suppressed.asc(), MarketingCampaignRecipient.created_at.desc())
        .limit(max(sample_limit, 1))
        .all()
    )

    return {
        "estimated_recipients": len(selected),
        "candidate_count": candidate_count,
        "matched_count": matched_count,
        "segment_excluded_count": segment_excluded_count,
        "eligible_count": max(len(selected) - suppressed_count, 0),
        "suppressed_count": suppressed_count,
        "suppression_reason_counts": suppression_reason_counts,
        "segment_params": effective_segment_params,
        "segment_summary": segment_summary,
        "sample_conversation_ids": [
            row.conversation_id
            for row in preview_rows
            if row.conversation_id
        ],
        "sample_recipient_jids": [
            row.recipient_jid
            for row in preview_rows
            if row.recipient_jid
        ],
    }


def fetch_marketing_audience_preview(
    db: Session,
    *,
    campaign_id: UUID,
    include_suppressed: bool,
    limit: int,
) -> list[MarketingCampaignRecipient]:
    query = db.query(MarketingCampaignRecipient).filter(MarketingCampaignRecipient.campaign_id == campaign_id)
    if not include_suppressed:
        query = query.filter(MarketingCampaignRecipient.suppressed.is_(False))
    return (
        query.order_by(
            MarketingCampaignRecipient.suppressed.asc(),
            MarketingCampaignRecipient.updated_at.desc(),
            MarketingCampaignRecipient.id.desc(),
        )
        .limit(max(limit, 1))
        .all()
    )


def build_marketing_campaign_preflight(
    db: Session,
    *,
    campaign: MarketingCampaign,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    previous_snapshot = campaign.preflight_snapshot if isinstance(campaign.preflight_snapshot, dict) else {}
    audience_filter = campaign.audience_filter if isinstance(campaign.audience_filter, dict) else {}
    segment_params = audience_filter.get("segment_params")
    segment_summary = audience_filter.get("segment_summary")
    preview_stats = (
        previous_snapshot.get("preview_stats")
        if isinstance(previous_snapshot.get("preview_stats"), dict)
        else audience_filter.get("preview_stats")
    )
    campaign_status = resolve_marketing_campaign_status(campaign)
    total_count = (
        db.query(func.count(MarketingCampaignRecipient.id))
        .filter(MarketingCampaignRecipient.campaign_id == campaign.id)
        .scalar()
        or 0
    )
    suppressed_count = (
        db.query(func.count(MarketingCampaignRecipient.id))
        .filter(
            MarketingCampaignRecipient.campaign_id == campaign.id,
            MarketingCampaignRecipient.suppressed.is_(True),
        )
        .scalar()
        or 0
    )
    eligible_count = max(int(total_count) - int(suppressed_count), 0)

    outbox_snapshot = build_outbox_health_snapshot(db, now=now)
    provider_billing_blocked_count = _count_recent_provider_billing_blocked_failures(
        db,
        client_id=campaign.client_id,
        branch_id=campaign.branch_id,
        now=now,
    )
    provider_billing_blocked = provider_billing_blocked_count > 0
    runtime_blocked = outbox_snapshot.get("status") == "critical"
    approval_ok = campaign_status in {MARKETING_STATUS_APPROVED, MARKETING_STATUS_SCHEDULED}
    preview_ok = int(total_count) > 0
    eligible_ok = eligible_count > 0
    template_gate_enabled = _env_flag(MARKETING_TEMPLATE_GATE_ENABLED_ENV, default=False)
    template_state = _campaign_template_state(campaign)
    template_ok = True
    if template_gate_enabled:
        template_ok = template_state in MARKETING_TEMPLATE_APPROVED_STATES

    blocked_reasons: list[str] = []
    if runtime_blocked:
        blocked_reasons.append("runtime_health_critical")
    if provider_billing_blocked:
        blocked_reasons.append("provider_billing_blocked")
    if not approval_ok:
        blocked_reasons.append("campaign_not_approved")
    if not preview_ok:
        blocked_reasons.append("audience_snapshot_missing")
    if not eligible_ok:
        blocked_reasons.append("eligible_recipients_empty")
    if not template_ok:
        blocked_reasons.append("template_not_approved")

    preflight_valid = len(blocked_reasons) == 0
    snapshot = {
        "generated_at": now.isoformat(),
        "campaign_id": str(campaign.id),
        "outbox_health": outbox_snapshot,
        "audience_total": int(total_count),
        "suppressed_count": int(suppressed_count),
        "eligible_count": int(eligible_count),
        "approval_ok": approval_ok,
        "preview_ok": preview_ok,
        "runtime_blocked": runtime_blocked,
        "provider_billing_blocked": provider_billing_blocked,
        "provider_billing_blocked_count": provider_billing_blocked_count,
        "template_gate_enabled": template_gate_enabled,
        "template_state": template_state,
        "template_ok": template_ok,
        "blocked_reasons": blocked_reasons,
        "preflight_valid": preflight_valid,
    }
    if isinstance(segment_params, dict):
        snapshot["segment_params"] = resolve_campaign_segment_params(
            campaign,
            segment_code=campaign.segment_code or MARKETING_SEGMENT_REACTIVATION_30_120,
            override_params=segment_params,
            strict=False,
        )
    if isinstance(segment_summary, str) and segment_summary.strip():
        snapshot["segment_summary"] = segment_summary.strip()
    if isinstance(preview_stats, dict):
        snapshot["preview_stats"] = preview_stats
    campaign.preflight_snapshot = snapshot
    campaign.preflight_valid = preflight_valid
    campaign.updated_at = now
    db.add(campaign)
    db.flush()
    return snapshot


def mark_campaign_under_review(campaign: MarketingCampaign, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_IN_REVIEW):
        raise ValueError("invalid_transition_to_in_review")
    _set_campaign_status(campaign, MARKETING_STATUS_IN_REVIEW)
    campaign.requested_review_at = now
    campaign.updated_at = now


def mark_campaign_approved(campaign: MarketingCampaign, *, approved_by: UUID, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_APPROVED):
        raise ValueError("invalid_transition_to_approved")
    _set_campaign_status(campaign, MARKETING_STATUS_APPROVED)
    campaign.approved_by = approved_by
    campaign.approved_at = now
    campaign.updated_at = now


def mark_campaign_paused(campaign: MarketingCampaign, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_PAUSED):
        raise ValueError("invalid_transition_to_paused")
    _set_campaign_status(campaign, MARKETING_STATUS_PAUSED)
    campaign.updated_at = now


def mark_campaign_resume(campaign: MarketingCampaign, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_APPROVED):
        raise ValueError("invalid_transition_to_approved")
    _set_campaign_status(campaign, MARKETING_STATUS_APPROVED)
    campaign.updated_at = now


def run_marketing_campaign_execute(
    db: Session,
    *,
    campaign: MarketingCampaign,
    message_text: str,
    max_recipients: Optional[int],
    now: Optional[datetime] = None,
) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    preflight = build_marketing_campaign_preflight(db, campaign=campaign, now=now)
    if not preflight.get("preflight_valid"):
        raise ValueError("preflight_failed")

    recipients_query = db.query(MarketingCampaignRecipient).filter(
        MarketingCampaignRecipient.campaign_id == campaign.id,
        MarketingCampaignRecipient.suppressed.is_(False),
    )
    recipients_query = recipients_query.order_by(
        MarketingCampaignRecipient.updated_at.desc(),
        MarketingCampaignRecipient.id.desc(),
    )
    if max_recipients is not None:
        recipients_query = recipients_query.limit(max_recipients)
    recipients = recipients_query.all()

    existing_jids = {
        _normalize_jid(row.recipient_jid)
        for row in db.query(MarketingCampaignDelivery.recipient_jid)
        .filter(
            MarketingCampaignDelivery.campaign_id == campaign.id,
            MarketingCampaignDelivery.recipient_jid.isnot(None),
        )
        .all()
        if row and row.recipient_jid
    }

    queued_count = 0
    skipped_count = 0
    for recipient in recipients:
        normalized_jid = _normalize_jid(recipient.recipient_jid)
        if not normalized_jid or normalized_jid in existing_jids:
            skipped_count += 1
            continue

        synthetic_inbound_id = f"marketing:{campaign.id}:{normalized_jid}"
        outbox_item = OutboxMessage(
            client_id=campaign.client_id,
            conversation_id=recipient.conversation_id,
            branch_id=campaign.branch_id,
            inbound_message_id=synthetic_inbound_id,
            payload_json={"text": message_text},
            meta={
                "source": "marketing_campaign",
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "segment_code": campaign.segment_code,
                "audience_mode": campaign.audience_mode,
            },
            status="PENDING",
            attempts=0,
            next_attempt_at=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        db.add(outbox_item)
        db.flush()

        delivery = MarketingCampaignDelivery(
            campaign_id=campaign.id,
            client_id=campaign.client_id,
            branch_id=campaign.branch_id,
            conversation_id=recipient.conversation_id,
            user_id=recipient.user_id,
            recipient_jid=recipient.recipient_jid,
            status="queued",
            outbox_id=outbox_item.id,
            error_reason=None,
            created_at=now,
            updated_at=now,
        )
        db.add(delivery)
        db.flush()

        db.add(
            MarketingDeliveryEvent(
                campaign_id=campaign.id,
                delivery_id=delivery.id,
                outbox_id=outbox_item.id,
                client_id=campaign.client_id,
                branch_id=campaign.branch_id,
                recipient_jid=recipient.recipient_jid,
                event_type="queued",
                payload={"reason": "campaign_execute"},
                created_at=now,
            )
        )
        queued_count += 1
        existing_jids.add(normalized_jid)

    if queued_count > 0:
        _set_campaign_status(campaign, MARKETING_STATUS_RUNNING)
        campaign.executed_at = now
        campaign.run_started_at = campaign.run_started_at or now
        campaign.run_completed_at = None
    campaign.updated_at = now
    db.add(campaign)
    db.flush()
    if queued_count <= 0:
        refresh_marketing_campaign_lifecycle(db, campaign=campaign, now=now)
    return {
        "queued_count": queued_count,
        "skipped_count": skipped_count,
    }


def retry_failed_marketing_deliveries(
    db: Session,
    *,
    campaign: MarketingCampaign,
    limit: int,
    now: Optional[datetime] = None,
) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    failed_query = (
        db.query(MarketingCampaignDelivery, OutboxMessage)
        .join(OutboxMessage, OutboxMessage.id == MarketingCampaignDelivery.outbox_id)
        .filter(
            MarketingCampaignDelivery.campaign_id == campaign.id,
            OutboxMessage.status == "FAILED",
        )
    )
    total_failed = int(failed_query.count() or 0)
    rows = (
        failed_query.order_by(
            OutboxMessage.updated_at.desc().nullslast(),
            OutboxMessage.id.desc(),
        )
        .limit(max(limit, 1))
        .all()
    )

    retried_count = 0
    skipped_permanent = 0
    for delivery, outbox_row in rows:
        classification = classify_provider_error(outbox_row.last_error)
        if not classification.retryable:
            skipped_permanent += 1
            db.add(
                MarketingDeliveryEvent(
                    campaign_id=campaign.id,
                    delivery_id=delivery.id,
                    outbox_id=outbox_row.id,
                    client_id=campaign.client_id,
                    branch_id=campaign.branch_id,
                    recipient_jid=delivery.recipient_jid,
                    event_type="retry_skipped_permanent",
                    payload={
                        "provider_kind": classification.kind,
                        "reason_code": classification.incident_reason_code,
                    },
                    created_at=now,
                )
            )
            continue

        outbox_row.status = "PENDING"
        outbox_row.next_attempt_at = None
        outbox_row.last_error = None
        outbox_row.updated_at = now
        delivery.status = "queued"
        delivery.error_reason = None
        delivery.updated_at = now
        retried_count += 1
        db.add(
            MarketingDeliveryEvent(
                campaign_id=campaign.id,
                delivery_id=delivery.id,
                outbox_id=outbox_row.id,
                client_id=campaign.client_id,
                branch_id=campaign.branch_id,
                recipient_jid=delivery.recipient_jid,
                event_type="retry_queued",
                payload={"reason": "retry_failed"},
                created_at=now,
            )
        )

    skipped_count = max(total_failed - retried_count, 0)
    campaign.updated_at = now
    db.add(campaign)
    db.flush()
    refresh_marketing_campaign_lifecycle(db, campaign=campaign, now=now)
    return {
        "retried_count": retried_count,
        "skipped_count": skipped_count,
        "skipped_permanent": skipped_permanent,
    }
