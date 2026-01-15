import asyncio
import base64
import hashlib
import mimetypes
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import (
    get_logger,
    get_trace_id,
    record_escalation_count,
    record_inbound_count,
    record_policy_count,
)
from app.models import Branch, Client, ClientSettings, Conversation, Handover, Message, User
from app.routers.webhook.booking import (
    BOOKING_SLOT_ORDER,
    _apply_booking_slot,
    _apply_expected_reply_slot,
    _build_booking_summary,
    _clear_service_hint,
    _expected_reply_for_booking_question,
    _get_booking_context,
    _get_recent_service_hint,
    _is_blocked_slot_message,
    _is_booking_related_message,
    _is_booking_time_service_decision,
    _match_expected_reply,
    _next_booking_prompt,
    _resolve_datetime_offline,
    _select_expected_reply_message,
    _select_last_non_booking_message,
    _set_booking_context,
    _set_service_hint,
    _update_booking_from_message,
    _update_booking_from_messages,
    _validate_name_slot,
)
from app.routers.webhook.branch_selection import (
    BRANCH_CONTEXT_KEY,
    BRANCH_SELECTION_KEY,
    MSG_BRANCH_SELECTED,
    _apply_branch_selection,
    _build_branch_prompt,
    _build_branch_selection,
    _coerce_uuid,
    _get_active_branches,
    _get_branch_selection,
    _get_user_branch_preference,
    _handle_branch_selection_gate,
    _is_branch_only_message,
    _match_branch_choice,
    _set_branch_selection,
    _set_user_branch_preference,
)
from app.routers.webhook.context_manager import (
    _apply_consult_return,
    _build_compact_summary_text,
    _build_consult_return_prompt,
    _get_asr_confirmation,
    _get_class_carryover,
    _get_consult_context,
    _get_context_manager,
    _get_conversation_context,
    _get_expected_reply_type,
    _get_low_confidence_retry_count,
    _get_reengage_confirmation,
    _get_service_carryover,
    _increment_context_message_count,
    _is_asr_confirmation_active,
    _is_re_entry_required,
    _is_reengage_confirmation_active,
    _maybe_store_class_carryover,
    _maybe_store_service_carryover,
    _prune_class_carryover,
    _prune_consult_context,
    _prune_service_carryover,
    _record_context_manager_decision,
    _reset_low_confidence_retry,
    _resolve_current_goal,
    _set_asr_confirmation,
    _set_class_carryover,
    _set_consult_context,
    _set_context_manager,
    _set_conversation_context,
    _set_expected_reply_context,
    _set_expected_reply_type,
    _set_handover_confirmation,
    _set_low_confidence_retry_count,
    _set_re_entry_required,
    _set_reengage_confirmation,
    _set_service_carryover,
    _update_compact_summary,
)
from app.routers.webhook.decision import (
    DecisionOutcome,
    DecisionSignals,
    _detect_fast_intent,
    _detect_intent_signals,
    _normalize_message_text,
    _resolve_action,
    build_action_contract,
    build_context_contract,
    build_decision_plan,
    build_fact_contract,
    build_intent_contract,
    build_response_contract,
    is_handover_status_question,
)
from app.routers.webhook.dedup import (
    _buffer_user_message,
    _drain_buffered_messages,
    _get_debounce_redis,
    _handle_debounce_gate,
    _handle_dedup_gate,
    is_duplicate_message_id,
    should_process_debounced_message,
)
from app.routers.webhook.guards import (
    _apply_session_timeout_reset,
    _booking_clarify_guard_reason,
    _format_intent_queue_prompt,
    _format_multi_intent_followup,
    _get_clarify_attempt_state,
    _get_intent_queue,
    _handle_clarify_limit_escalation,
    _handle_opt_out_mute_gate,
    _handle_reengage_and_mute_gate,
    _match_intent_choice_from_text,
    _register_clarify_attempt,
    _select_intent_from_queue,
    _set_clarify_attempt,
    _set_intent_queue,
    _should_escalate_for_clarify,
)
from app.routers.webhook.info import (
    _build_info_intent_reply,
    _count_anchor_hits,
    _detect_info_class_intents,
    _extract_truth_gate_info_intents,
    _is_short_reply,
    _looks_like_info_query,
    _tokenize_for_matching,
)
from app.routers.webhook.media import (
    MediaDecision,
    MediaInfo,
    _build_media_caption,
    _deserialize_media_decision,
    _evaluate_media_decision,
    _extract_media_info,
    _get_media_policy,
    _get_media_rate_settings,
    _get_transcription_settings,
    _is_asr_low_confidence,
    _is_placeholder_text,
    _is_style_reference_request,
    _is_voice_note,
    _maybe_transcribe_voice,
    _send_telegram_media,
    _serialize_media_decision,
    _store_media_locally,
    _update_message_asr_metadata,
    _update_message_media_metadata,
)
from app.routers.webhook.outbox import _handle_enqueue_only_accept, _prepare_skip_persist
from app.routers.webhook.pending import (
    _forward_pending_to_telegram,
    _handle_manager_active_gate,
    _handle_pending_gate,
    _handle_handover_confirmation_gate,
)
from app.routers.webhook.policy import (
    _demo_salon_escalation_gate,
    _demo_salon_price_sidecar,
    _detect_booking_cancel,
    _detect_llm_guard_topics,
    _format_discounts_policy_reply,
    _handle_hard_law_gate,
    _handle_policy_escalation_gate,
    _get_policy_handler,
    _get_policy_pack,
    _get_policy_type,
    _get_routing_policy,
    _has_discount_policy_rules,
    _looks_like_policy_topic,
    _looks_like_promotions_request,
    _resolve_hard_law_sections,
    _should_escalate_to_pending,
    _should_run_booking_flow,
    _should_run_demo_truth_gate,
    _should_run_truth_gate,
)
from app.routers.webhook.response import _apply_quiet_hours_notice, _maybe_append_booking_cta
from app.routers.webhook.router_sla import _update_router_sla
from app.routers.webhook.session_memory import (
    _get_session_memory,
    _is_session_memory_expired,
    _is_session_reset_only_message,
    _normalize_session_memory,
    _parse_session_memory_time,
    _record_session_memory_update,
    _reset_session_memory,
    _session_memory_snapshot,
    _set_session_memory,
    _should_reset_session_memory,
    _update_session_memory_goal,
    _update_session_memory_on_answer,
    _update_session_memory_on_question,
)
from app.routers.webhook.shield import _handle_shield_gate
from app.routers.webhook.trace import (
    _attach_llm_cache_flag,
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.ai_service import (
    ACKNOWLEDGEMENT_RESPONSE,
    BOT_STATUS_RESPONSE,
    GREETING_RESPONSE,
    HIGH_CONFIDENCE_THRESHOLD,
    MID_CONFIDENCE_THRESHOLD,
    OUT_OF_DOMAIN_RESPONSE,
    THANKS_RESPONSE,
    classify_confirmation,
    detect_multi_intent,
    detect_refusal_flags,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
    normalize_for_matching,
    rewrite_for_service_match,
    rewrite_query_for_retrieval,
    transcribe_audio_with_fallback,
)
from app.services.chatflow_service import send_bot_response
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    _detect_promotion_intent,
    _has_duration_signal,
    _has_price_signal,
    _match_service,
    build_consult_reply,
    build_info_combined_reply,
    build_quiet_hours_notice,
    compose_multi_truth_reply,
    format_reply_from_truth,
    get_demo_salon_decision,
    get_demo_salon_price_item,
    get_demo_salon_price_reply,
    get_demo_salon_service_decision,
    get_demo_salon_service_hint,
    load_yaml_truth,
    semantic_question_type,
    semantic_service_match,
)
from app.services.demo_salon_knowledge import (
    _normalize_text as _normalize_service_text,
)
from app.services.escalation_service import get_telegram_credentials, send_telegram_notification
from app.services.intent_service import (
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    classify_intent,
    interpret_expected_reply,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    route_dialogue_controller,
    should_escalate,
)
from app.services.message_service import generate_bot_response, save_message, select_handover_user_message
from app.services.outbox_service import build_inbound_message_id
from app.services.state_machine import ConversationState
from app.services.state_service import escalate_to_pending, manager_resolve, transition_state
from app.services.telegram_service import TelegramService

logger = get_logger("webhook")
_BRANCH_EXPORTS = (
    BRANCH_CONTEXT_KEY,
    BRANCH_SELECTION_KEY,
    MSG_BRANCH_SELECTED,
    _apply_branch_selection,
    _build_branch_prompt,
    _build_branch_selection,
    _coerce_uuid,
    _get_active_branches,
    _get_branch_selection,
    _get_user_branch_preference,
    _is_branch_only_message,
    _match_branch_choice,
    _set_branch_selection,
    _set_user_branch_preference,
)
_DEDUP_EXPORTS = (
    _buffer_user_message,
    _drain_buffered_messages,
    is_duplicate_message_id,
    should_process_debounced_message,
)
ROUTER_SIGNAL_CONFIDENCE_BONUS = 0.1
ROUTER_SIGNAL_CONFIDENCE_FLOOR = 0.2
CONTROLLER_CONFIDENCE_THRESHOLD = float(
    os.getenv("CONTROLLER_CONFIDENCE_THRESHOLD", "0.3") or 0.3
)


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


MEDIA_TYPE_ALIASES = {
    "image": "photo",
    "photo": "photo",
    "jpg": "photo",
    "jpeg": "photo",
    "png": "photo",
    "audio": "audio",
    "voice": "audio",
    "ptt": "audio",
    "document": "document",
    "pdf": "document",
    "doc": "document",
    "docx": "document",
    "xlsx": "document",
    "xls": "document",
    "video": "video",
}
MEDIA_MAX_DEFAULT_MB = {"photo": 8, "audio": 8, "document": 10}
MEDIA_RATE_LIMIT_DEFAULTS = {
    "count": 5,
    "window_seconds": 600,
    "daily_count": 20,
    "bytes_mb": 30,
    "block_seconds": 900,
}
MEDIA_STORAGE_DEFAULT_DIR = os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media")
MEDIA_STORAGE_MAX_BYTES = 25 * 1024 * 1024
AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB = 2.0

STYLE_REFERENCE_PATTERNS = (
    re.compile(r"\bкак на (фото|картин\w+|примере)\b"),
    re.compile(r"\bпо (фото|картин\w+|референс\w*)\b"),
    re.compile(r"\bреференс\w*\b"),
    re.compile(r"\bреф\b"),
    re.compile(r"\bв стиле\b"),
    re.compile(r"\bпохоже на\b"),
)
STYLE_REFERENCE_HINT_TOKENS = ("фото", "картин", "референс", "реф", "пример")


def _find_message_by_message_id(db: Session, client_id: UUID, message_id: str) -> Message | None:
    if not message_id:
        return None
    return (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            Message.message_metadata["message_id"].astext == message_id,
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def _find_message_by_conversation_created_at(
    db: Session,
    conversation_id: UUID,
    created_at: datetime | None,
    *,
    message_text: str | None = None,
    lookback_seconds: int = 120,
) -> Message | None:
    if not conversation_id or not created_at:
        return None
    window_start = created_at - timedelta(seconds=lookback_seconds)
    window_end = created_at + timedelta(seconds=lookback_seconds)
    rows = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == "user",
            Message.created_at >= window_start,
            Message.created_at <= window_end,
        )
        .order_by(Message.created_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return None
    normalized_target = normalize_for_matching(message_text) if message_text else ""
    if normalized_target:
        for msg in rows:
            if normalize_for_matching(msg.content or "") == normalized_target:
                return msg
    return min(
        rows,
        key=lambda msg: abs((msg.created_at - created_at).total_seconds()) if msg.created_at else float("inf"),
    )


def _router_observability_meta(*, eligible: bool, reason: str) -> dict:
    return {
        "router_eligible": bool(eligible),
        "router_skipped_reason": reason,
        "controller_eligible": bool(eligible),
        "controller_skipped_reason": reason,
    }


def _set_router_observability(message: Message | None, *, eligible: bool, reason: str) -> dict:
    updates = _router_observability_meta(eligible=eligible, reason=reason)
    if message:
        _update_message_decision_metadata(message, updates)
    return updates


_DEFAULT_RAG_SCORES = {"bm25_max": 0.0, "vector_max": 0.0, "hybrid_max": 0.0}


def _merge_rag_scores(rag_scores: dict | None) -> dict:
    merged = dict(rag_scores) if isinstance(rag_scores, dict) else {}
    for key, value in _DEFAULT_RAG_SCORES.items():
        if not isinstance(merged.get(key), (int, float)):
            merged[key] = value
    return merged if merged else dict(_DEFAULT_RAG_SCORES)


def _derive_rag_status(
    *,
    rag_scores: dict,
    rag_best_score: float | None,
    rag_attempted: bool,
) -> tuple[bool, str | None]:
    if not rag_attempted:
        return False, "overridden_by_gate"
    best_score = float(rag_best_score or 0.0)
    if best_score >= MID_CONFIDENCE_THRESHOLD:
        return True, None
    vector_count = int(rag_scores.get("vector_count") or 0)
    bm25_count = int(rag_scores.get("bm25_count") or 0)
    if vector_count <= 0 and bm25_count <= 0:
        return False, "empty"
    return False, "low_score"


def _ensure_rag_meta_defaults(message: Message | None) -> None:
    if not message:
        return
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    rag_scores = _merge_rag_scores(decision_meta.get("rag_scores"))
    updates = {"rag_scores": rag_scores}
    if "rag_confident" not in decision_meta:
        updates["rag_confident"] = False
    if "rag_reason" not in decision_meta:
        updates["rag_reason"] = "overridden_by_gate"
    if "router_eligible" not in decision_meta:
        updates["router_eligible"] = False
    if "router_skipped_reason" not in decision_meta:
        updates["router_skipped_reason"] = "not_run"
    _update_message_decision_metadata(message, updates)


def _resolve_backlog_language(message: Message | None) -> str:
    if not message or not isinstance(message.message_metadata, dict):
        return "unknown"
    metadata = message.message_metadata
    for key in ("language", "lang", "locale"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    media_meta = metadata.get("media")
    if isinstance(media_meta, dict):
        transcript_language = media_meta.get("transcript_language")
        if isinstance(transcript_language, str) and transcript_language.strip():
            return transcript_language.strip().lower()
    return "unknown"


def _record_knowledge_backlog(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: UUID,
    message: Message | None,
    user_text: str,
    miss_type: str,
) -> None:
    text_value = (user_text or "").strip()
    if not text_value:
        return
    language = _resolve_backlog_language(message)
    miss_value = (miss_type or "unknown").strip().lower()
    try:
        db.execute(
            text(
                """
                INSERT INTO knowledge_backlog (
                  id,
                  client_id,
                  conversation_id,
                  message_id,
                  user_text,
                  language,
                  miss_type,
                  repeat_count,
                  first_seen_at,
                  last_seen_at
                )
                VALUES (
                  gen_random_uuid(),
                  :client_id,
                  :conversation_id,
                  :message_id,
                  :user_text,
                  :language,
                  :miss_type,
                  1,
                  NOW(),
                  NOW()
                )
                ON CONFLICT (client_id, language, miss_type, user_text)
                DO UPDATE SET
                  repeat_count = knowledge_backlog.repeat_count + 1,
                  last_seen_at = EXCLUDED.last_seen_at,
                  conversation_id = EXCLUDED.conversation_id,
                  message_id = EXCLUDED.message_id
                """
            ),
            {
                "client_id": client_id,
                "conversation_id": conversation_id,
                "message_id": message.id if message else None,
                "user_text": text_value,
                "language": language,
                "miss_type": miss_value,
            },
        )
    except Exception:
        logger.warning(
            "Knowledge backlog upsert failed",
            extra={
                "context": {
                    "client_id": str(client_id),
                    "conversation_id": str(conversation_id),
                    "message_id": str(message.id) if message else None,
                    "miss_type": miss_type,
                }
            },
            exc_info=True,
        )


# Default values (can be overridden in client_settings)
DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
SESSION_TIMEOUT_HOURS = 24
LOW_CONFIDENCE_RETRY_WINDOW_MINUTES = 10
LOW_CONFIDENCE_MAX_RETRIES = 2
HANDOVER_CONFIRM_WINDOW_MINUTES = 15
REENGAGE_CONFIRM_WINDOW_MINUTES = 15
ASR_CONFIRM_WINDOW_MINUTES = 10
SERVICE_HINT_WINDOW_MINUTES = 120
ASR_LOW_CONFIDENCE_MIN_CHARS = 6
ASR_LOW_CONFIDENCE_MIN_WORDS = 3
ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS = 6.0
ASR_LOW_CONFIDENCE_NON_LETTER_RATIO = 0.4
MULTI_INTENT_MIN_CHARS = 350
MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
MSG_LOW_CONFIDENCE = "Хороший вопрос! Уточню у коллег и вернусь с ответом."
MSG_HANDOVER_CONFIRM = "Не уверен, что понял. Подключить менеджера? Ответьте 'да' или 'нет'."
MSG_REENGAGE_CONFIRM = "Вы просили не писать. Хотите снова общаться? Ответьте 'да' или 'нет'."
MSG_REENGAGE_DECLINED = "Хорошо, не буду писать. Если передумаете — напишите снова."
MSG_HANDOVER_DECLINED = (
    "Ок. Напишите, что именно интересует по салону: цена/запись/адрес/мастер/жалоба."
)
MSG_LOW_CONFIDENCE_RETRY = "Уточните, пожалуйста: интересуют услуги/цены или запись/адрес?"
MSG_EXPECTED_SERVICE_OFF_TOPIC = "Я могу помочь по услугам салона. Какая услуга интересует?"
MSG_PENDING_LOW_CONFIDENCE = (
    "Я уже передал менеджеру — он скоро подключится. "
    "Пока ждём, уточните: услуги/цены или запись/адрес."
)
MSG_PENDING_ESCALATION = "Я уже передал менеджеру — он скоро подключится."
MSG_PENDING_STATUS = "Да, я передал. Сейчас менеджер ещё не взял заявку. Как только возьмёт — ответит здесь. Пока ждём, могу помочь: уточните, что нужно?"
MSG_PENDING_WAIT = "Администратор подключится."
MSG_PENDING_SLA_PING = "Напоминаю: менеджер ещё не подключился. Я на связи — напишите, что нужно уточнить."
MSG_PENDING_AUTO_CLOSE = "Закрываю ожидание. Если всё ещё актуально — напишите, я помогу."
MSG_PENDING_ACK = "Хорошо. Напишите, что именно нужно: цена/запись/адрес/мастер."
MSG_AI_ERROR = "Извините, произошла ошибка. Попробуйте позже."
MSG_MEDIA_UNSUPPORTED = (
    "Сейчас принимаем только фото, аудио и документы. Видео не поддерживаются. Опишите вопрос текстом."
)
MSG_MEDIA_TOO_LARGE = "Файл слишком большой. Пришлите, пожалуйста, фото/аудио поменьше или опишите текстом."
MSG_MEDIA_RATE_LIMIT = "Слишком много файлов за короткое время. Давайте продолжим позже или опишите текстом."
MSG_MEDIA_RECEIVED = "Файл получил. Напишите, пожалуйста, что именно нужно: цена/запись/адрес/мастер/жалоба."
MSG_MEDIA_DOC_RECEIVED = "Документ получил. Напишите, пожалуйста, что именно нужно."
MSG_MEDIA_TRANSCRIPT_FAILED = "Не смог разобрать аудио. Напишите, пожалуйста, текстом."
MSG_ASR_CONFIRM = "Я услышал: «{text}». Правильно? (да/нет)"
MSG_ASR_CONFIRM_DECLINED = "Пожалуйста, напишите текстом или перешлите аудио."
MSG_MEDIA_PENDING_NEED_TEXT = (
    "Я уже передал менеджеру. Чтобы ускорить, напишите, что именно нужно: цена/запись/адрес/мастер/жалоба."
)
MSG_MEDIA_STYLE_REFERENCE = (
    "Спасибо за фото/референс. Передал администратору для подтверждения возможности и деталей. "
    "Чтобы ускорить, напишите услугу, дату/время и имя."
)
MSG_STYLE_REFERENCE_NEED_MEDIA = (
    "Можем ориентироваться на фото/референс. Пришлите фото и кратко опишите запрос — "
    "я передам администратору для подтверждения."
)

PENDING_SLA_PING_MINUTES = 15
PENDING_AUTO_CLOSE_HOURS = 4
PENDING_SLA_CONTEXT_KEY = "pending_sla"
PENDING_SLA_PING_SENT_KEY = "ping_sent_at"
PENDING_SLA_AUTO_CLOSE_KEY = "auto_closed_at"
PENDING_RESUME_KEY = "pending_resume"

PENDING_ACK_PHRASES = {
    "ага",
    "актуально",
    "да",
    "давай",
    "жду",
    "можно",
    "ок",
    "ответьте",
}
PENDING_CLOSE_PHRASES = {
    "закрыто",
    "решено",
    "не надо",
    "уже сделал",
    "по телефону",
    "спасибо все",
    "спасибо всё",
}

MSG_BOOKING_ASK_SERVICE = "На какую услугу хотите записаться?"
MSG_BOOKING_ASK_DATETIME = "На какую дату и время вам удобно?"
MSG_BOOKING_ASK_NAME = "Как вас зовут?"
MSG_BOOKING_CANCELLED = "Хорошо, если передумаете — пишите."
MSG_BOOKING_REENGAGE = "Хотите продолжить запись? Если да — напишите услугу."
MSG_BOOKING_CTA = "Хотите записаться?"

SERVICE_HINT_KEY = "last_service_hint"
SERVICE_HINT_AT_KEY = "last_service_hint_at"
RE_ENTRY_REQUIRED_KEY = "re_entry_required"
REENGAGE_CONFIRM_KEY = "reengage_confirmation"
ASR_CONFIRM_KEY = "asr_confirm_pending"
DECISION_TRACE_KEY = "decision_trace"
CONTEXT_MANAGER_KEY = "context_manager"
INTENT_QUEUE_KEY = "intent_queue"
EXPECTED_REPLY_TYPE_KEY = "expected_reply_type"

EXPECTED_REPLY_SERVICE = "service_choice"
EXPECTED_REPLY_TIME = "time"
EXPECTED_REPLY_NAME = "name"
EXPECTED_REPLY_INTENT_CHOICE = "intent_choice"

CLARIFY_MAX_ATTEMPTS = 2
REFUSAL_TTL_MESSAGES = 10
SUMMARY_MESSAGE_THRESHOLD = 12
FACT_GUARD_ENABLED = False
FACT_GUARD_INTENT = "fact_guard"
FACT_GUARD_SKIP_INTENTS = {"service_clarify", "duration_or_price_clarify"}
FACT_GUARD_MAX_ATTEMPTS = 1
MSG_FACT_GUARD_CLARIFY = "Подскажите, пожалуйста, что именно вас интересует?"

ROUTING_MATRIX = {
    ConversationState.BOT_ACTIVE.value: {
        "allow_booking_flow": True,
        "allow_truth_gate_reply": True,
        "allow_handover_create": True,
        "allow_bot_reply": True,
    },
    ConversationState.PENDING.value: {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    },
    ConversationState.MANAGER_ACTIVE.value: {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    },
}


SHIELD_CONTEXT_KEY = "shield"
SHIELD_RECENT_KEY = "recent_messages"
SHIELD_LAST_TEXT_KEY = "last_text"
SHIELD_SPAM_WINDOW_SECONDS = 5.0
SHIELD_SPAM_MAX_MESSAGES = 3
SHIELD_MAX_MESSAGE_LENGTH = 1000
SHIELD_SHORT_MESSAGE_LEN = 12
SHIELD_TOXIC_PATTERNS = [
    re.compile(r"\b(хуй|пизд|пидор|еба|сука|нахуй|убью|иди\s+на\s+хуй|бля[тд])", re.IGNORECASE),
]
SHIELD_MEANINGFUL_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9]{2,}")
HYGIENE_KEYWORDS = [
    "стерилиз",
    "дезраств",
    "дезинф",
    "ультразвук",
    "уз-ванн",
    "сухожар",
    "крафт",
    "однораз",
    "инструмент",
    "обрабатыва",
]


BOOKING_REQUEST_KEYWORDS = [
    "запис",
    "запись",
    "запишите",
    "записаться",
    "бронь",
    "окошк",
    "свободн",
]

SERVICE_KEYWORDS = [
    "маникюр",
    "маник",
    "педикюр",
    "стриж",
    "окраш",
    "мелирован",
    "кератин",
    "ботокс",
    "бров",
    "ресниц",
    "депиляц",
    "шугар",
    "воск",
    "чистк",
    "пилинг",
    "макияж",
    "укладк",
    "прическ",
    "наращив",
    "лак",
]

DATE_KEYWORDS = [
    "сегодня",
    "завтра",
    "послезавтра",
    "понедель",
    "вторник",
    "сред",
    "четверг",
    "пятниц",
    "суббот",
    "воскрес",
    "утром",
    "днем",
    "днём",
    "вечером",
]

TIME_PATTERN = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
TIME_HOUR_PATTERN = re.compile(r"\b(?:в|к)\s*(?:[01]?\d|2[0-3])\b", re.IGNORECASE)
DATE_PATTERN = re.compile(
    r"\b(?:сегодня|завтра|послезавтра|понедель\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскрес\w*|утром|днем|днём|вечером)\b",
    re.IGNORECASE,
)
DATE_NUMERIC_PATTERN = re.compile(r"\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b")
DATE_MONTH_PATTERN = re.compile(
    r"\b\d{1,2}\s*(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*\b",
    re.IGNORECASE,
)
NAME_PATTERN = re.compile(r"\bменя зовут\s+([a-zа-яё-]{2,})", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")
NAME_NOISE_TOKENS = {"меня", "зовут", "это", "я", "имя"}


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip().casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _coerce_batch_messages(message_text: str, batch_messages: list[str] | None) -> list[str]:
    raw_messages = batch_messages if batch_messages else ([message_text] if message_text else [])
    cleaned: list[str] = []
    for msg in raw_messages:
        if not msg:
            continue
        text = msg.strip()
        if text:
            cleaned.append(text)
    if not cleaned and message_text:
        fallback = message_text.strip()
        if fallback:
            cleaned.append(fallback)
    return cleaned


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _matches_guest_policy_lexicon(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    truth = load_yaml_truth()
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("guest_policy_lexicon") if isinstance(domain_pack, dict) else None
    if not isinstance(lexicon, dict):
        return False
    for lang_key in ("ru", "kk"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = normalize_for_matching(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _is_booking_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _contains_any(normalized, BOOKING_REQUEST_KEYWORDS)


def _is_booking_cancel(text: str, *, policy_pack: dict | None) -> bool:
    return _detect_booking_cancel(text, policy_pack=policy_pack)


def _extract_service_hint(text: str, client_slug: str | None) -> str | None:
    if not text or not client_slug:
        return None
    normalized_text = _normalize_text(text)
    booking_like = _is_booking_request(text)
    if not booking_like:
        booking_like = bool(
            TIME_PATTERN.search(text)
            or TIME_HOUR_PATTERN.search(text)
            or DATE_PATTERN.search(text)
            or DATE_NUMERIC_PATTERN.search(text)
            or DATE_MONTH_PATTERN.search(text)
        )
    match = semantic_service_match(text, client_slug)
    if not match or match.action != "match":
        if client_slug == "demo_salon":
            fallback = get_demo_salon_service_hint(text)
            if fallback:
                return fallback
        return None
    canonical_name = match.canonical_name
    if isinstance(canonical_name, str) and canonical_name.strip():
        if booking_like and normalized_text:
            canonical_tokens = _normalize_text(canonical_name).split()
            message_tokens = normalized_text.split()
            if canonical_tokens and message_tokens:
                if not any(token in message_tokens for token in canonical_tokens):
                    return None
        return canonical_name.strip()
    return None


def _extract_datetime(text: str) -> str | None:
    if not text:
        return None
    resolved = _resolve_datetime_offline(text)
    if isinstance(resolved, dict):
        value = resolved.get("value")
        if isinstance(value, str) and value.strip():
            return value
    time_match = TIME_PATTERN.search(text)
    if time_match:
        return time_match.group(0)
    hour_match = TIME_HOUR_PATTERN.search(text)
    if hour_match:
        return hour_match.group(0)
    numeric_date_match = DATE_NUMERIC_PATTERN.search(text)
    if numeric_date_match:
        return numeric_date_match.group(0)
    month_date_match = DATE_MONTH_PATTERN.search(text)
    if month_date_match:
        return month_date_match.group(0)
    date_match = DATE_PATTERN.search(text)
    if date_match:
        return date_match.group(0)
    return None


BOOKING_INFO_QUESTION_TYPES = {"pricing", "hours", "duration"}
INFO_INTENTS = {"pricing", "hours", "duration", "location"}
CONSULT_INTERRUPT_INTENTS = {"booking", "pricing", "duration", "location", "hours"}
INFO_INTENT_PRIORITY_SERVICE = ("pricing", "duration", "location", "hours")
INFO_INTENT_PRIORITY_GENERIC = ("location", "hours", "pricing", "duration")
BOOKING_TIME_SERVICE_INTENTS = {
    "service_match",
    "service_not_found",
    "price_query",
    "price_manicure",
    "service_duration",
    "service_clarify",
    "duration_or_price_clarify",
}
BOOKING_CTA_SERVICE_INTENTS = BOOKING_TIME_SERVICE_INTENTS - {
    "service_not_found",
    "service_clarify",
    "duration_or_price_clarify",
}
CLASS_CARRYOVER_KEY = "class_carryover"
CLASS_CARRYOVER_TTL_MESSAGES = 4
CLASS_CARRYOVER_CLASSES = {"info_bundle"}
SERVICE_CARRYOVER_KEY = "service_carryover"
SERVICE_CARRYOVER_TTL_MESSAGES = 4
CONSULT_CONTEXT_KEY = "consult_context"
CONSULT_CONTEXT_TTL_MESSAGES = 6
SERVICE_CARRYOVER_INTENTS = {"pricing", "duration"}
SERVICE_CARRYOVER_SKIP_INTENTS = {
    "service_clarify",
    "duration_or_price_clarify",
    "service_not_found",
}
SESSION_MEMORY_KEY = "session_memory"
SESSION_MEMORY_TTL_HOURS = 24
SESSION_MEMORY_SHORT_TOKENS = 4
SESSION_MEMORY_RESET_PHRASES = (
    "новый вопрос",
    "другая тема",
    "начнем сначала",
    "начнём сначала",
    "начнем заново",
    "начнём заново",
    "давай сначала",
)


def _normalize_class_name(class_name: str) -> str:
    normalized = class_name.strip()
    if normalized.casefold() in {"info", "info_bundle"}:
        return "info_bundle"
    return normalized


def _evaluate_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None,
    message_text: str | None,
) -> tuple[bool, dict | None]:
    if not messages:
        return False, None
    if any(_is_booking_request(message) for message in messages):
        return True, None
    has_service = any(_extract_service_hint(message, client_slug) for message in messages)
    has_datetime = any(_extract_datetime(message) for message in messages)
    booking_signal = has_service and has_datetime
    if booking_signal and message_text:
        segments = [segment.strip() for segment in re.split(r"[?!\.,;]+", message_text) if segment.strip()]
        if not segments:
            segments = [message_text.strip()]
        for segment in segments:
            question_type = semantic_question_type(segment, include_kinds=BOOKING_INFO_QUESTION_TYPES)
            if question_type and question_type.kind in BOOKING_INFO_QUESTION_TYPES:
                return (
                    False,
                    {
                        "booking_blocked_reason": "info_question",
                        "question_type": question_type.kind,
                        "question_type_score": question_type.score,
                    },
                )
    return booking_signal, None


def _has_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None = None,
    message_text: str | None = None,
) -> bool:
    booking_signal, _ = _evaluate_booking_signal(
        messages,
        client_slug=client_slug,
        message_text=message_text,
    )
    return booking_signal


INFO_ANCHOR_GROUPS: dict[str, list[tuple[str, ...]]] = {
    "pricing": [
        ("цен",),
        ("стоим",),
        ("скольк", "стоит"),
        ("поч",),
    ],
    "duration": [
        ("длит",),
        ("длител",),
        ("скольк", "врем"),
        ("врем", "заним"),
        ("минут",),
        ("час",),
    ],
    "hours": [
        ("график",),
        ("режим", "работ"),
        ("каког", "врем"),
        ("работ", "скольк"),
        ("работ", "когда"),
        ("работ", "до"),
        ("откры",),
        ("закры",),
    ],
    "location": [
        ("адрес",),
        ("где", "наход"),
        ("где", "вы"),
        ("локац",),
        ("перекр",),
        ("угол",),
        ("ориентир",),
        ("как", "доех"),
        ("как", "добрат"),
        ("как", "найт"),
        ("куда", "ехать"),
        ("улиц",),
    ],
}

QUESTION_WORD_PREFIXES = ("скольк", "где", "когда", "како")


def _looks_like_time_only_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    if _is_booking_request(message_text):
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    if any(keyword in normalized for keyword in SERVICE_KEYWORDS):
        return False
    if TIME_PATTERN.search(message_text):
        return True
    return bool(DATE_PATTERN.search(normalized))


def _looks_like_hours_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    if _contains_any(normalized, ["по времени", "по часам", "по час"]):
        return True
    return _contains_any(
        normalized,
        [
            "график",
            "до скольк",
            "во скольк",
            "время работы",
            "часы",
            "часов",
            "работае",
            "открыт",
            "когда откры",
            "открывает",
        ],
    )


def _looks_like_carryover_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    followup_phrases = [
        "по времени",
        "по цене",
        "по стоимости",
        "по длитель",
        "по адресу",
        "по месту",
        "по час",
        "по график",
    ]
    if _contains_any(normalized, followup_phrases):
        return True
    if len(tokens) <= SESSION_MEMORY_SHORT_TOKENS:
        pricing_groups = INFO_ANCHOR_GROUPS.get("pricing", [])
        if pricing_groups and _count_anchor_hits(tokens, pricing_groups) > 0:
            return True
    if tokens[0] in {"и", "а", "еще", "ещё"} and _contains_any(
        normalized,
        [
            "сколько",
            "когда",
            "где",
            "до скольк",
            "во скольк",
            "цена",
            "стоим",
            "длител",
            "время",
            "час",
        ],
    ):
        return True
    return False


def _build_controller_meta_output(*, error: str, retry: bool = False, elapsed_ms: float = 0.0) -> dict:
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


def _ensure_controller_output_meta(controller_output: dict, *, error: str | None) -> dict:
    if not isinstance(controller_output.get("controller_llm_ms"), (int, float)):
        controller_output["controller_llm_ms"] = 0.0
    if not isinstance(controller_output.get("controller_error"), str) or not controller_output.get("controller_error"):
        controller_output["controller_error"] = error or "none"
    if not isinstance(controller_output.get("controller_retry"), bool):
        controller_output["controller_retry"] = False
    if "controller_goal" in controller_output and not controller_output.get("goal"):
        controller_output["goal"] = controller_output.get("controller_goal")
    return controller_output


CONTROLLER_FALLBACK_IGNORE_VALUES = {"none", "skipped", "ok", "low_confidence"}
CONTROLLER_FALLBACK_REASON_MAP = {
    "timeout": "timeout",
    "invalid_json": "invalid_json",
    "budget_exceeded": "budget_exceeded",
    "no_api_key": "no_api_key",
    "prompt_missing": "prompt_missing",
    "empty_message": "empty_message",
    "empty_response": "empty_response",
    "invalid_class": "invalid_class",
    "unsupported_temperature": "unsupported_temperature",
}
CONTROLLER_FALLBACK_ERROR_VALUES = {"controller_failed", "error"}
CONTROLLER_FALLBACK_REASONS = set(CONTROLLER_FALLBACK_REASON_MAP.values()) | {"error"}


def _normalize_controller_fallback_reason(*, error: str | None) -> str | None:
    if not error:
        return None
    normalized = error.strip().casefold()
    if not normalized or normalized in CONTROLLER_FALLBACK_IGNORE_VALUES:
        return None
    mapped = CONTROLLER_FALLBACK_REASON_MAP.get(normalized)
    if mapped:
        return mapped
    if normalized in CONTROLLER_FALLBACK_ERROR_VALUES:
        return "error"
    return "error"


def _resolve_controller_signal_class(*, intent_decomp_set: set[str], booking_signal: bool) -> str | None:
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
    class_carryover: dict | None,
    domain_intent: DomainIntent,
    domain_meta: dict | None,
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
            classes.append("guest_policy")
    if booking_signal:
        in_signals.append("booking_signal")
        classes.append("booking")
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


def _resolve_class_router_result(
    *,
    info_intents: set[str],
    info_meta: dict[str, Any] | None,
    booking_signal: bool,
    class_carryover: dict | None,
    domain_intent: DomainIntent,
    domain_meta: dict | None,
    router_state: dict | None,
) -> dict[str, Any]:
    result = _build_class_controller_result(
        info_intents=info_intents,
        info_meta=info_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
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
    controller_intents: list[str] = []
    controller_goal = None
    if isinstance(controller_output, dict):
        raw_class = controller_output.get("class")
        if isinstance(raw_class, str):
            controller_class = _normalize_class_name(raw_class)
        raw_reason = controller_output.get("reason")
        if isinstance(raw_reason, str):
            controller_reason = raw_reason
        raw_intents = controller_output.get("intents")
        if isinstance(raw_intents, list):
            controller_intents = [item for item in raw_intents if isinstance(item, str)]
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

    if controller_used and controller_class and not controller_low_confidence:
        result["classes"] = [controller_class]
        info_controller_intents = [intent for intent in controller_intents if intent in INFO_INTENTS]
        if controller_class == "info_bundle":
            if info_controller_intents:
                result["intents"] = sorted(info_controller_intents)
        else:
            result["intents"] = sorted(info_controller_intents)
        controller_fallback_reason = None
    elif controller_used and controller_class and controller_low_confidence:
        # Low confidence: keep deterministic class_router result, but track low confidence explicitly.
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
    # Backward-compat for downstream callers still keyed on router
    result["router"] = result["controller"]
    result["router_fallback_reason"] = controller_fallback_reason
    return result


def _controller_meta_updates_from_class_router(class_router_result: dict | None) -> dict[str, Any]:
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


def _router_observability_updates_from_class_router(class_router_result: dict | None) -> dict[str, Any]:
    if not isinstance(class_router_result, dict):
        return {}
    controller_meta = class_router_result.get("controller")
    if not isinstance(controller_meta, dict):
        return {}
    attempted = bool(controller_meta.get("attempted"))
    reason = "none" if attempted else "not_run"
    return _router_observability_meta(eligible=attempted, reason=reason)


def _is_refusal_flag_active(refusal_flags: dict | None, field: str) -> bool:
    if not isinstance(refusal_flags, dict):
        return False
    payload = refusal_flags.get(field)
    if isinstance(payload, dict):
        return payload.get("value") is True
    if isinstance(payload, bool):
        return payload
    return False


def _detect_name_provided(message_text: str, *, client_slug: str | None) -> bool:
    if not message_text:
        return False
    if classify_confirmation(message_text) in {"yes", "no"}:
        return False
    return bool(_validate_name_slot(message_text, allow_freeform=True, client_slug=client_slug))


def _detect_phone_provided(message_text: str) -> bool:
    if not message_text:
        return False
    match = PHONE_PATTERN.search(message_text)
    if not match:
        return False
    digits = re.sub(r"\D", "", match.group(0))
    return len(digits) >= 10


def _update_refusal_flags(
    manager: dict,
    *,
    message_text: str,
    now: datetime,
    client_slug: str | None,
) -> tuple[dict, dict, list[dict]]:
    detected = detect_refusal_flags(message_text)
    name_initiative = _detect_name_provided(message_text, client_slug=client_slug)
    phone_initiative = _detect_phone_provided(message_text)
    existing = manager.get("refusal_flags")
    existing_flags = dict(existing) if isinstance(existing, dict) else {}
    updated_flags: dict = {}
    events: list[dict] = []

    for field in ("name", "phone"):
        data = existing_flags.get(field)
        payload = dict(data) if isinstance(data, dict) else {}
        explicit_refusal = bool(detected.get(field))
        if explicit_refusal:
            updated_flags[field] = {
                "value": True,
                "source": "explicit_refusal",
                "last_set_at": now.isoformat(),
                "ttl_remaining": REFUSAL_TTL_MESSAGES,
            }
            events.append({"type": "set", "field": field, "source": "explicit_refusal"})
            continue
        if field == "name" and name_initiative:
            if payload.get("value") is True:
                events.append({"type": "cleared", "field": field, "source": "explicit_initiative"})
            continue
        if field == "phone" and phone_initiative:
            if payload.get("value") is True:
                events.append({"type": "cleared", "field": field, "source": "explicit_initiative"})
            continue
        if payload.get("value") is True:
            ttl = payload.get("ttl_remaining")
            if isinstance(ttl, int):
                ttl = max(0, ttl - 1)
                if ttl <= 0:
                    events.append({"type": "cleared", "field": field, "source": "ttl_expired"})
                    continue
                payload["ttl_remaining"] = ttl
            updated_flags[field] = payload

    manager["refusal_flags"] = updated_flags
    return manager, updated_flags, events


def _combine_sidecar(primary: str, sidecar: str | None) -> str:
    if not sidecar:
        return primary
    return f"{sidecar}\n\n{primary}"


def _ensure_question_mark(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}?"


def _append_followup(primary: str, followup: str | None) -> str:
    if not followup:
        return primary
    return f"{primary}\n\n{followup}"


MULTI_INTENT_LABELS = {
    "booking": "записи",
    "pricing": "цене",
    "duration": "длительности",
    "location": "адресу",
    "hours": "времени",
    "other": "другому вопросу",
}


_POLICY_HANDLERS = {
    "demo_salon": {
        "policy_type": "demo_salon",
        "escalation_gate": _demo_salon_escalation_gate,
        "service_matcher": get_demo_salon_service_decision,
        "truth_gate": get_demo_salon_decision,
        "price_item": get_demo_salon_price_item,
        "price_sidecar": _demo_salon_price_sidecar,
    }
}


def _is_hygiene_context_text(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    return any(keyword in normalized for keyword in HYGIENE_KEYWORDS)


def find_active_conversation_by_channel_ref(db: Session, client_id, remote_jid: str) -> Conversation | None:
    """Reuse conversation if there is an active handover for this remote_jid."""
    handover = (
        db.query(Handover)
        .filter(
            Handover.client_id == client_id,
            Handover.channel_ref == remote_jid,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    if handover:
        return db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()
    return None


def get_mute_settings(db: Session, client_id) -> tuple[int, int]:
    """Get mute durations from client_settings or use defaults."""
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings:
        mute_first = settings.mute_duration_first_minutes or DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = settings.mute_duration_second_hours or DEFAULT_MUTE_DURATION_SECOND_HOURS
    else:
        mute_first = DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = DEFAULT_MUTE_DURATION_SECOND_HOURS

    return mute_first, mute_second


def get_active_handover(db: Session, conversation_id) -> Handover | None:
    """Get latest pending/active handover for conversation."""
    return (
        db.query(Handover)
        .filter(
            Handover.conversation_id == conversation_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )


def _reuse_active_handover(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message: str,
    source: str,
    intent: str | None = None,
) -> tuple[Handover | None, bool, bool]:
    handover = get_active_handover(db, conversation.id)
    if not handover:
        return None, False, False

    if conversation.state == ConversationState.BOT_ACTIVE.value:
        target_state = ConversationState.MANAGER_ACTIVE if handover.status == "active" else ConversationState.PENDING
        transition_result = transition_state(
            conversation,
            target_state,
            allow_same=True,
            enforce=False,
            handover=handover,
        )
        if transition_result["invalid_transition"]:
            _record_decision_trace(
                conversation,
                {
                    "stage": "state_transition",
                    "decision": "invalid",
                    "meta": {
                        "from": transition_result["from_state"],
                        "to": transition_result["to_state"],
                        "violations": transition_result["violations"],
                    },
                },
            )
        conversation.escalated_at = conversation.escalated_at or datetime.now(timezone.utc)

    telegram_sent = send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message=message,
    )
    _record_decision_trace(
        conversation,
        {
            "stage": "escalation",
            "decision": "reuse_handover",
            "state": conversation.state,
            "intent": intent,
            "source": source,
            "handover_id": str(handover.id),
            "telegram_sent": telegram_sent,
        },
    )
    return handover, True, telegram_sent


def should_offer_low_confidence_retry(conversation: Conversation, now: datetime) -> bool:
    """One clarifying question before creating a handover on low confidence."""
    offered_at = conversation.retry_offered_at
    if not offered_at:
        return True

    if offered_at.tzinfo is None:
        offered_at = offered_at.replace(tzinfo=timezone.utc)

    return (now - offered_at) > timedelta(minutes=LOW_CONFIDENCE_RETRY_WINDOW_MINUTES)


async def _process_outbox_rows(
    db: Session,
    rows: list[dict],
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, int]:
    from app.routers.webhook import outbox as outbox_helpers

    return await outbox_helpers._process_outbox_rows(
        db,
        rows,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )


async def _handle_webhook_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    enforce_secret: bool,
    enqueue_only: bool = False,
    skip_persist: bool = False,
    conversation_id: UUID | None = None,
    batch_messages: list[str] | None = None,
    outbox_ids: list[str] | None = None,
    outbox_created_at: datetime | None = None,
) -> WebhookResponse:
    """Shared webhook processing for inbound ChatFlow payloads."""
    logger.info(f"Webhook received: client_slug={payload.client_slug}")

    def _resolve_trace_conversation(
        *,
        trace_client: Client | None,
        trace_conversation_id: UUID | None,
        trace_message_id: str | None,
        trace_remote_jid: str | None,
    ) -> Conversation | None:
        if trace_conversation_id:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == trace_conversation_id)
                .first()
            )
            if conversation:
                return conversation
        if trace_client and trace_message_id:
            saved_message = _find_message_by_message_id(db, trace_client.id, trace_message_id)
            if saved_message:
                return (
                    db.query(Conversation)
                    .filter(Conversation.id == saved_message.conversation_id)
                    .first()
                )
        if trace_client and trace_remote_jid:
            user = (
                db.query(User)
                .filter(User.client_id == trace_client.id, User.remote_jid == trace_remote_jid)
                .first()
            )
            if user:
                return (
                    db.query(Conversation)
                    .filter(
                        Conversation.client_id == trace_client.id,
                        Conversation.user_id == user.id,
                        Conversation.status == "active",
                    )
                    .first()
                )
        return None

    def _record_early_trace(
        trace_conversation: Conversation | None,
        *,
        stage: str,
        decision: str,
        reason: str,
        meta: dict[str, Any] | None = None,
    ) -> bool:
        if not trace_conversation:
            return False
        trace_payload = {"stage": stage, "decision": decision, "reason": reason}
        if meta:
            trace_payload.update(meta)
        _record_decision_trace(trace_conversation, trace_payload)
        return True

    from . import http as http_helpers

    preflight_response, preflight_payload = http_helpers._run_preflight(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=enforce_secret,
        conversation_id=conversation_id,
        resolve_trace_conversation=_resolve_trace_conversation,
        record_early_trace=_record_early_trace,
    )
    if preflight_response:
        return preflight_response

    client = preflight_payload["client"]
    settings = preflight_payload["settings"]
    body = preflight_payload["body"]
    metadata = preflight_payload["metadata"]
    message_id = preflight_payload["message_id"]
    remote_jid = preflight_payload["remote_jid"]
    message_text = preflight_payload["message_text"]
    message_type = preflight_payload["message_type"]
    has_media = preflight_payload["has_media"]
    is_media_without_text = preflight_payload["is_media_without_text"]
    media_info = preflight_payload["media_info"]

    if not skip_persist:
        record_inbound_count(payload.client_slug)

    batch_messages_provided = batch_messages is not None
    batch_messages = _coerce_batch_messages(message_text, batch_messages)
    batch_non_booking_message = _select_last_non_booking_message(
        batch_messages,
        client_slug=payload.client_slug,
    )

    timing_context: dict = {"client_slug": payload.client_slug, "remote_jid": remote_jid}
    trace_id = get_trace_id()
    if trace_id:
        timing_context["trace_id"] = trace_id
    if client and isinstance(client.config, dict):
        timing_context["client_config"] = client.config
    if outbox_ids:
        timing_context["outbox_ids"] = list(outbox_ids)
        timing_context["outbox_id"] = outbox_ids[0] if len(outbox_ids) == 1 else outbox_ids[0]

    outbound_idempotency_key = message_id or build_inbound_message_id(
        message_id,
        remote_jid,
        metadata.timestamp if metadata else None,
        message_text,
    )

    media_policy = _get_media_policy(client) if media_info else None
    media_decision: MediaDecision | None = None
    saved_message: Message | None = None
    media_redis_client = None
    count_rate_limit = not skip_persist
    if media_info:
        redis_url, socket_timeout_seconds = _get_media_rate_settings()
        media_redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)

    def _log_timing(stage: str, elapsed_ms: float, extra: dict | None = None) -> None:
        context = dict(timing_context)
        if extra:
            context.update(extra)
        context["stage"] = stage
        context["elapsed_ms"] = round(elapsed_ms, 2)
        logger.info("Timing", extra={"context": context})

    def _record_escalation_metric(trigger: str) -> None:
        record_escalation_count(payload.client_slug, trigger)

    def _record_llm_budget_trace() -> None:
        events = timing_context.get("llm_budget_events") if isinstance(timing_context, dict) else None
        if not isinstance(events, list) or not events:
            return
        for event in events:
            if not isinstance(event, dict):
                continue
            allowed = bool(event.get("allowed", True))
            active = bool(event.get("active"))
            if not active and allowed:
                continue
            scope = event.get("scope") or "unknown"
            trace_payload = {
                "stage": "budget_gate",
                "decision": "allow" if allowed else "deny",
                "llm_scope": scope,
            }
            reason = event.get("reason")
            if isinstance(reason, str) and reason:
                trace_payload["reason"] = reason
            limit = event.get("limit")
            count = event.get("count")
            if isinstance(limit, int):
                trace_payload["budget_limit"] = limit
            if isinstance(count, int):
                trace_payload["budget_count"] = count
            if not allowed:
                trace_payload["llm_degradation_reason"] = "budget_exceeded"
            _record_decision_trace(conversation, trace_payload)
        timing_context["llm_budget_events"] = []

    def _record_llm_degradation() -> None:
        reason = timing_context.get("llm_degradation_reason") if isinstance(timing_context, dict) else None
        if not isinstance(reason, str) or not reason:
            return
        if saved_message:
            metadata = (
                saved_message.message_metadata
                if isinstance(saved_message.message_metadata, dict)
                else {}
            )
            decision_meta = metadata.get("decision_meta") if isinstance(metadata, dict) else None
            existing_reason = decision_meta.get("llm_degradation_reason") if isinstance(decision_meta, dict) else None
            if not existing_reason:
                _update_message_decision_metadata(
                    saved_message, {"llm_degradation_reason": reason}
                )
        if reason != "budget_exceeded":
            _record_decision_trace(
                conversation,
                {
                    "stage": "llm_degradation",
                    "decision": "fallback",
                    "llm_degradation_reason": reason,
                },
            )
        timing_context["llm_degradation_reason"] = None

    def _send_response(text: str) -> bool:
        send_start = time.monotonic()
        sent = send_bot_response(
            db,
            client.id,
            remote_jid,
            text,
            idempotency_key=outbound_idempotency_key,
            raise_on_fail=skip_persist,
        )
        _log_timing("send_ms", (time.monotonic() - send_start) * 1000, {"send_ok": sent})
        return sent

    def _ensure_rag_rewrite() -> None:
        if timing_context.get("rag_rewrite_logged"):
            return
        rag_rewrite_meta = rewrite_query_for_retrieval(
            message_text,
            client_slug=payload.client_slug,
            client_config=client.config if client else None,
            timing_context=timing_context,
        )
        _record_llm_budget_trace()
        if not isinstance(rag_rewrite_meta, dict):
            return
        timing_context["rag_rewrite"] = rag_rewrite_meta
        timing_context["rag_rewrite_logged"] = True
        rewrite_used = rag_rewrite_meta.get("rewrite_used") is True
        rewrite_text = rag_rewrite_meta.get("rewrite_text") if rewrite_used else ""
        _record_decision_trace(
            conversation,
            {
                "stage": "rewrite",
                "decision": "used" if rewrite_used else "skipped",
                "rewrite_used": rewrite_used,
                "rewrite_text": rewrite_text,
                "reason": rag_rewrite_meta.get("reason"),
            },
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {"rewrite_used": rewrite_used, "rewrite_text": rewrite_text},
            )

    def _record_rag_meta() -> None:
        _record_llm_budget_trace()
        _record_llm_degradation()
        rag_trace = timing_context.get("rag_trace") if isinstance(timing_context, dict) else None
        if isinstance(rag_trace, list) and rag_trace:
            for entry in rag_trace:
                if isinstance(entry, dict):
                    _record_decision_trace(conversation, entry)
            timing_context["rag_trace"] = []
        rag_scores = timing_context.get("rag_scores") if isinstance(timing_context, dict) else None
        rag_scores = _merge_rag_scores(rag_scores if isinstance(rag_scores, dict) else None)
        if saved_message:
            rag_confident, rag_reason = _derive_rag_status(
                rag_scores=rag_scores,
                rag_best_score=timing_context.get("rag_best_score") if isinstance(timing_context, dict) else None,
                rag_attempted=bool(timing_context.get("rag_attempted")) if isinstance(timing_context, dict) else False,
            )
            _update_message_decision_metadata(
                saved_message,
                {
                    "rag_scores": rag_scores,
                    "rag_confident": rag_confident,
                    "rag_reason": rag_reason,
                },
            )

    if skip_persist:
        (
            skip_response,
            conversation,
            user,
            saved_message,
            media_decision,
        ) = await _prepare_skip_persist(
            db=db,
            client=client,
            conversation_id=conversation_id,
            message_id=message_id,
            remote_jid=remote_jid,
            message_text=message_text,
            media_info=media_info,
            media_policy=media_policy,
            media_redis_client=media_redis_client,
            count_rate_limit=count_rate_limit,
            outbox_created_at=outbox_created_at,
            timing_context=timing_context,
            resolve_trace_conversation=_resolve_trace_conversation,
            record_early_trace=_record_early_trace,
        )
        if skip_response:
            return skip_response
    else:
        dedupe_response, message_id = await _handle_dedup_gate(
            db=db,
            client=client,
            message_id=message_id,
            remote_jid=remote_jid,
            metadata=metadata,
            message_text=message_text,
            conversation_id=conversation_id,
            resolve_trace_conversation=_resolve_trace_conversation,
            record_early_trace=_record_early_trace,
        )
        if dedupe_response:
            return dedupe_response

        # 1. Get or create user
        user = get_or_create_user(db, client.id, remote_jid)

        # 2. Find existing conversation by handover.channel_ref or create new
        conversation = find_active_conversation_by_channel_ref(db, client.id, remote_jid)
        if not conversation:
            conversation = get_or_create_conversation(db, client.id, user.id, "whatsapp")
        timing_context["conversation_id"] = str(conversation.id)

        if media_info and media_decision is None and media_policy:
            media_decision = await _evaluate_media_decision(
                media=media_info,
                client_id=client.id,
                remote_jid=remote_jid,
                policy=media_policy,
                redis_client=media_redis_client,
                count_rate_limit=count_rate_limit,
            )

        # 3. Save user message (keep message_id for dedup)
        message_metadata = metadata.model_dump(exclude_none=True) if metadata else {}
        if message_id:
            message_metadata["message_id"] = message_id
        if message_type:
            message_metadata["message_type"] = message_type
        if has_media:
            message_metadata["has_media"] = True
        if media_info:
            media_meta = {
                "type": media_info.media_type,
                "raw_type": media_info.raw_type,
                "mime": media_info.mime,
                "size_bytes": media_info.size_bytes,
                "url": media_info.url,
                "file_name": media_info.file_name,
                "caption": media_info.caption,
                "ptt": media_info.is_ptt,
            }
            if media_decision:
                media_meta["decision"] = _serialize_media_decision(media_decision)
            message_metadata["media"] = media_meta
        saved_message = save_message(
            db,
            conversation.id,
            client.id,
            role="user",
            content=message_text,
            message_metadata=message_metadata,
        )
        _ensure_rag_meta_defaults(saved_message)
        if trace_id and saved_message:
            _update_message_decision_metadata(saved_message, {"trace_id": trace_id})

        if enqueue_only:
            return await _handle_enqueue_only_accept(
                db=db,
                client=client,
                conversation=conversation,
                payload=payload,
                remote_jid=remote_jid,
                message_id=message_id,
                message_text=message_text,
                metadata=metadata,
                saved_message=saved_message,
                media_info=media_info,
                media_policy=media_policy,
                media_decision=media_decision,
            )

    routing = _get_routing_policy(conversation.state)
    context_contract, context_error = build_context_contract(conversation, payload, settings)
    _record_decision_trace(
        conversation,
        {
            "stage": "contract",
            "decision": "context",
            "contract_ok": context_error is None,
            "contract_error": context_error,
            "contract": context_contract,
        },
    )
    decision_plan = build_decision_plan(
        state=conversation.state,
        routing=routing,
        client_slug=payload.client_slug,
    )
    plan_id = decision_plan.plan_id
    for stage in decision_plan.stages:
        _record_decision_trace(
            conversation,
            {
                "stage": "decision_graph",
                "decision": stage,
                "plan_id": plan_id,
            },
        )

    transcript = None
    asr_meta = None
    if media_info and media_policy and _is_placeholder_text(message_text):
        stored_path = None
        if saved_message and isinstance(saved_message.message_metadata, dict):
            stored_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")
        transcript, transcript_status, asr_meta = await _maybe_transcribe_voice(
            media=media_info,
            policy=media_policy,
            media_decision=media_decision,
            storage_path=stored_path,
            saved_message=saved_message,
        )
        if saved_message and asr_meta:
            _update_message_asr_metadata(saved_message, asr_meta)
        if transcript:
            message_text = transcript
            if saved_message:
                saved_message.content = transcript
                _, _, model, language, _, _, _, _ = _get_transcription_settings()
                transcript_model = model
                if asr_meta and asr_meta.get("asr_model"):
                    transcript_model = asr_meta.get("asr_model")
                updates = {
                    "transcript": transcript,
                    "transcript_model": transcript_model,
                    "transcript_provider": asr_meta.get("asr_provider") if asr_meta else None,
                    "transcribed_at": datetime.now(timezone.utc).isoformat(),
                }
                if language:
                    updates["transcript_language"] = language
                _update_message_media_metadata(saved_message, updates)
        elif transcript_status not in {"disabled", "not_voice", "not_allowed", "too_large", "missing_audio"}:
            logger.warning(
                "Voice transcription skipped",
                extra={"context": {"status": transcript_status, "conversation_id": str(conversation.id)}},
            )

    asr_low_confidence = False
    if transcript and media_info and _is_voice_note(media_info):
        asr_low_confidence = _is_asr_low_confidence(transcript, media_info.duration_seconds)

    # 4. Update last_message_at (keep previous for session timeout check)
    now = datetime.now(timezone.utc)
    policy_type = _get_policy_type(client)
    policy_pack = _get_policy_pack(client)
    policy_pack_missing = not isinstance(policy_pack, dict)
    policy_source = "policy_pack" if not policy_pack_missing else "policy_gate"
    policy_handler = _get_policy_handler(client)
    hard_law_sections = set(_resolve_hard_law_sections(policy_pack))
    quiet_hours_notice: str | None = None
    if conversation.state == ConversationState.BOT_ACTIVE.value and policy_type == "demo_salon":
        quiet_hours_notice = build_quiet_hours_notice(now_utc=now)

    def _finalize_bot_response(text: str, *, allow_quiet_hours: bool = True) -> str:
        if not text:
            return text
        if not allow_quiet_hours:
            return text
        if not quiet_hours_notice:
            return text
        if conversation.state != ConversationState.BOT_ACTIVE.value:
            return text
        return _apply_quiet_hours_notice(text, quiet_hours_notice)

    def _extract_fact_payload(decision_meta: dict[str, Any]) -> dict[str, Any] | None:
        fact_keys = (
            "fact_source",
            "fact_intents",
            "info_sections",
            "info_combined",
            "question_type",
            "question_type_score",
            "service_query",
            "service_query_source",
            "service_query_score",
            "price_item",
            "duration_item",
            "info_signals",
            "anchor_intents",
            "anchor_hits",
            "anchor_boost",
        )
        facts = {key: decision_meta.get(key) for key in fact_keys if key in decision_meta}
        return facts or None

    def _maybe_apply_fact_guard(
        *,
        decision_meta: dict[str, Any] | None,
        intent: str | None,
        source: str,
        allow_handover: bool,
    ) -> WebhookResponse | None:
        if not FACT_GUARD_ENABLED:
            return None
        if not isinstance(decision_meta, dict):
            return None
        if intent in FACT_GUARD_SKIP_INTENTS:
            return None
        fact_source = decision_meta.get("fact_source")
        if not isinstance(fact_source, str) or not fact_source:
            return None
        fact_payload = {
            "info_sections": decision_meta.get("info_sections"),
            "service_query": decision_meta.get("service_query"),
            "price_item": decision_meta.get("price_item"),
            "duration_item": decision_meta.get("duration_item"),
        }
        has_facts = any(
            (
                isinstance(value, str) and value.strip()
            )
            or (
                isinstance(value, list) and value
            )
            or (
                isinstance(value, dict) and value
            )
            for value in fact_payload.values()
        )
        if has_facts:
            return None
        context = _get_conversation_context(conversation)
        context_manager = _get_context_manager(context)
        clarify_count, _ = _get_clarify_attempt_state(context_manager, FACT_GUARD_INTENT)
        if clarify_count >= FACT_GUARD_MAX_ATTEMPTS:
            _record_context_manager_decision(
                conversation,
                saved_message,
                decision="clarify_limit",
                updates={
                    "clarify_attempt": {"intent": FACT_GUARD_INTENT, "count": clarify_count},
                    "clarify_reason": "fact_guard",
                    "clarify_limit": True,
                },
            )
            return _handle_clarify_limit_escalation(
                db=db,
                conversation=conversation,
                user=user,
                message_text=message_text,
                saved_message=saved_message,
                source="fact_guard",
                allow_handover=allow_handover,
                send_response=_send_response,
                finalize_response=_finalize_bot_response,
            )
        _register_clarify_attempt(
            conversation=conversation,
            saved_message=saved_message,
            intent=FACT_GUARD_INTENT,
            now=now,
            reason="fact_guard",
        )
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "fact_guard",
                "decision": "clarify",
                "state": conversation.state,
                "fact_source": fact_source,
                "source": source,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="reply",
            intent="fact_guard",
            source="fact_guard",
            fast_intent=False,
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "clarify_reason": "fact_guard",
                    "fact_guard": True,
                },
            )
        bot_response, sent = _send_and_save(MSG_FACT_GUARD_CLARIFY)
        result_message = "Fact guard clarify sent" if sent else "Fact guard clarify failed"
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    def _record_contract_traces(*, action_type: str | None = None) -> None:
        decision_meta: dict[str, Any] = {}
        if saved_message and isinstance(saved_message.message_metadata, dict):
            raw_meta = saved_message.message_metadata.get("decision_meta")
            if isinstance(raw_meta, dict):
                decision_meta = raw_meta

        action_value = action_type
        if not action_value:
            meta_action = decision_meta.get("action")
            if isinstance(meta_action, str) and meta_action:
                action_value = meta_action
        if not action_value:
            action_value = "reply"

        fact_source = decision_meta.get("fact_source")
        source = decision_meta.get("source")
        if isinstance(fact_source, str) and fact_source:
            sources = [fact_source]
        elif isinstance(source, str) and source:
            sources = [source]
        else:
            sources = None
        policy_gate = decision_meta.get("policy_gate")
        policy_flags = [policy_gate] if isinstance(policy_gate, str) and policy_gate else None
        facts = _extract_fact_payload(decision_meta)

        fact_payload = {
            "info_sections": decision_meta.get("info_sections"),
            "service_query": decision_meta.get("service_query"),
            "price_item": decision_meta.get("price_item"),
            "duration_item": decision_meta.get("duration_item"),
        }
        has_fact_payload = any(
            (
                isinstance(value, str) and value.strip()
            )
            or (
                isinstance(value, list) and value
            )
            or (
                isinstance(value, dict) and value
            )
            for value in fact_payload.values()
        )
        if facts or (isinstance(fact_source, str) and fact_source):
            _record_decision_trace(
                conversation,
                {
                    "stage": "fact_resolver",
                    "decision": "resolved" if has_fact_payload else "missing",
                    "fact_source": fact_source if isinstance(fact_source, str) else None,
                    "facts": facts,
                },
            )

        fact_contract, fact_error = build_fact_contract(
            facts=facts,
            sources=sources,
            policy_flags=policy_flags,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "contract",
                "decision": "fact",
                "contract_ok": fact_error is None,
                "contract_error": fact_error,
                "contract": fact_contract,
            },
        )

        action_contract, action_error = build_action_contract(
            action_type=action_value,
            required_next_slots=None,
            escalation_reason=None,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "contract",
                "decision": "action",
                "contract_ok": action_error is None,
                "contract_error": action_error,
                "contract": action_contract,
            },
        )

        response_contract, response_error = build_response_contract(
            tone=None,
            must_include=None,
            must_not_include=None,
            language=None,
        )
        _record_decision_trace(
            conversation,
            {
                "stage": "contract",
                "decision": "response",
                "contract_ok": response_error is None,
                "contract_error": response_error,
                "contract": response_contract,
            },
        )

    def _send_and_save(text: str, *, allow_quiet_hours: bool = True) -> tuple[str, bool]:
        final_text = _finalize_bot_response(text, allow_quiet_hours=allow_quiet_hours)
        _record_contract_traces()
        save_message(db, conversation.id, client.id, role="assistant", content=final_text)
        sent = _send_response(final_text)
        return final_text, sent
    previous_last_message_at = conversation.last_message_at
    conversation.last_message_at = now
    context = _get_conversation_context(conversation)
    context_manager = _get_context_manager(context)
    session_memory = _get_session_memory(context)
    session_memory, memory_contract_error = _normalize_session_memory(session_memory)
    if memory_contract_error:
        memory_snapshot = _session_memory_snapshot(session_memory)
        memory_snapshot["memory_keys"] = sorted(
            key for key in session_memory.keys() if isinstance(key, str)
        )
        context = _set_session_memory(context, None)
        _set_conversation_context(conversation, context)
        _record_decision_trace(
            conversation,
            {
                "stage": "session_memory",
                "decision": "contract_error",
                "reason": memory_contract_error,
                **memory_snapshot,
            },
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {"session_memory_contract_error": memory_contract_error},
            )
        session_memory = {}
    else:
        context = _set_session_memory(context, session_memory or None)
        _set_conversation_context(conversation, context)
    session_memory_reset_reason = None
    if session_memory and _is_session_memory_expired(session_memory, now):
        session_memory_reset_reason = "expired"
    elif _should_reset_session_memory(message_text):
        session_memory_reset_reason = "explicit_reset"
    elif session_memory and conversation.state in [
        ConversationState.PENDING.value,
        ConversationState.MANAGER_ACTIVE.value,
    ]:
        session_memory_reset_reason = "handover"
    if session_memory_reset_reason:
        reset_snapshot = _session_memory_snapshot(session_memory)
        reset_snapshot["memory_keys"] = sorted(
            key for key in session_memory.keys() if isinstance(key, str)
        )
        context, context_manager, _reset_snapshot = _reset_session_memory(
            context=context,
            context_manager=context_manager,
            reason=session_memory_reset_reason,
            now=now,
        )
        re_entry_required = session_memory_reset_reason in {"expired", "handover"}
        if re_entry_required:
            context = _set_re_entry_required(
                context,
                reason=session_memory_reset_reason,
                now=now,
            )
        _set_conversation_context(conversation, context)
        _record_decision_trace(
            conversation,
            {
                "stage": "session_memory",
                "decision": "reset",
                "reason": session_memory_reset_reason,
                **reset_snapshot,
            },
        )
        if re_entry_required:
            _record_decision_trace(
                conversation,
                {
                    "stage": "re_entry",
                    "decision": "required",
                    "reason": session_memory_reset_reason,
                },
            )
        if saved_message:
            _update_message_decision_metadata(
                saved_message, {"session_memory_reset": session_memory_reset_reason}
            )
        session_memory = {}
        if session_memory_reset_reason == "explicit_reset" and _is_session_reset_only_message(message_text):
            bot_response = "Ок, давайте новую тему. Чем могу помочь?"
            _record_message_decision_meta(
                saved_message,
                action="smalltalk",
                intent="reset",
                source="session_memory",
                fast_intent=False,
            )
            _record_decision_trace(
                conversation,
                {
                    "stage": "session_memory",
                    "decision": "reset_ack",
                    "reason": session_memory_reset_reason,
                },
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Session reset ack sent" if sent else "Session reset ack failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )
    message_count = _increment_context_message_count(context_manager)
    context_manager, refusal_flags, refusal_events = _update_refusal_flags(
        context_manager,
        message_text=message_text,
        now=now,
        client_slug=payload.client_slug,
    )
    context_manager, class_carryover_event = _prune_class_carryover(
        context_manager,
        message_count=message_count,
    )
    context_manager, carryover_event = _prune_service_carryover(
        context_manager,
        message_count=message_count,
    )
    context_manager, consult_context_event = _prune_consult_context(
        context_manager,
        message_count=message_count,
    )
    context = _set_context_manager(context, context_manager)
    _set_conversation_context(conversation, context)
    if refusal_events:
        _record_context_manager_decision(
            conversation,
            saved_message,
            decision="refusal_flags",
            updates={"refusal_flags": refusal_flags, "refusal_events": refusal_events},
        )
    if class_carryover_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "class_carryover",
                "decision": "expired",
                **class_carryover_event,
            },
        )
    if carryover_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "service_carryover",
                "decision": "expired",
                **carryover_event,
            },
        )
    if consult_context_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "consult_context",
                "decision": "expired",
                **consult_context_event,
            },
        )
    if message_count == SUMMARY_MESSAGE_THRESHOLD:
        _update_compact_summary(
            conversation=conversation,
            saved_message=saved_message,
            reason="message_threshold",
            now=now,
        )
        context = _get_conversation_context(conversation)
    current_goal = context_manager.get("current_goal") if isinstance(context_manager, dict) else None
    consult_context = _get_consult_context(context_manager, message_count=message_count)
    consult_return_prompt = None
    consult_return_reason = None
    consult_return_pending = False
    class_carryover = _get_class_carryover(context_manager, message_count=message_count)

    expected_reply_type = _get_expected_reply_type(context)
    intent_queue = _get_intent_queue(context)
    session_memory = _get_session_memory(context)
    re_entry_required = _is_re_entry_required(context)
    memory_expected_reply_type = None
    if (
        not expected_reply_type
        and session_memory
        and not re_entry_required
        and not _is_session_memory_expired(session_memory, now)
    ):
        memory_active_goal = session_memory.get("active_goal")
        last_question_type = session_memory.get("last_question_type")
        if isinstance(last_question_type, str):
            last_question_type = last_question_type.strip()
        if (
            (not memory_active_goal or not current_goal or memory_active_goal == current_goal)
            and last_question_type in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}
            and _is_short_reply(message_text)
            and not _looks_like_info_query(message_text)
            and not _looks_like_policy_topic(
                message_text,
                policy_type=policy_type,
                policy_pack=policy_pack,
            )
        ):
            expected_reply_type = last_question_type
            memory_expected_reply_type = last_question_type
            _record_decision_trace(
                conversation,
                {
                    "stage": "session_memory",
                    "decision": "expected_reply_fallback",
                    "expected_reply_type": last_question_type,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message, {"session_memory_expected_reply": last_question_type}
                )
    expected_reply_matched: bool | None = None
    expected_reply_shortcircuit = False
    expected_reply_blocked_by_info = False
    expected_reply_text = (
        _select_expected_reply_message(
            batch_messages,
            expected_reply_type=expected_reply_type,
            client_slug=payload.client_slug,
        )
        or message_text
    )
    if expected_reply_type in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}:
        if message_text:
            normalized_message = _normalize_service_text(message_text)
            expected_reply_blocked_by_info = (
                _looks_like_info_query(message_text)
                or _has_price_signal(normalized_message, message_text)
                or _has_duration_signal(normalized_message, message_text)
            )
        expected_reply_text = expected_reply_text or ""
        answer_result = None
        answer_confidence = 0.0
        answer_slot = ""
        answer_value = ""
        answer_error = "blocked_by_info"
        if expected_reply_blocked_by_info:
            answer_meta = {
                "answer_interpreter_used": False,
                "answer_confidence": 0.0,
                "answer_slot": "",
                "answer_value": "",
                "answer_error": "blocked_by_info",
            }
            matched = False
            value = None
        else:
            answer_error = "invalid_result"
            prompt_hint = None
            booking_context = _get_booking_context(context)
            last_question = booking_context.get("last_question")
            if expected_reply_type == EXPECTED_REPLY_SERVICE:
                prompt_hint = (
                    MSG_BOOKING_ASK_SERVICE
                    if last_question == "service"
                    else MSG_EXPECTED_SERVICE_OFF_TOPIC
                )
            elif expected_reply_type == EXPECTED_REPLY_TIME:
                prompt_hint = MSG_BOOKING_ASK_DATETIME
            elif expected_reply_type == EXPECTED_REPLY_NAME:
                prompt_hint = MSG_BOOKING_ASK_NAME

            question_context = {
                "prompt_hint": prompt_hint,
                "booking": booking_context,
                "current_goal": current_goal,
                "service_carryover": _get_service_carryover(
                    context_manager, message_count=message_count
                ),
            }
            answer_result = interpret_expected_reply(
                expected_reply_text,
                expected_reply_type=expected_reply_type,
                carryover=class_carryover,
                question_context=question_context,
                client_slug=payload.client_slug,
            )
            answer_payload = answer_result.get("payload") if isinstance(answer_result, dict) else None
            if isinstance(answer_result, dict):
                answer_error = answer_result.get("error") or "none"
            if isinstance(answer_payload, dict):
                answer_slot = answer_payload.get("slot") or ""
                answer_value = answer_payload.get("value") or ""
                try:
                    answer_confidence = float(answer_payload.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    answer_confidence = 0.0
                answer_confidence = max(0.0, min(answer_confidence, 1.0))
            answer_meta = {
                "answer_interpreter_used": True,
                "answer_confidence": answer_confidence,
                "answer_slot": answer_slot,
                "answer_value": answer_value,
                "answer_error": answer_error,
            }

        answer_confidence_floor = 0.65
        answer_value_ok = isinstance(answer_value, str) and answer_value.strip()
        answer_slot_ok = isinstance(answer_slot, str) and answer_slot.strip()
        answer_result_ok = isinstance(answer_result, dict) and answer_result.get("ok") is True
        answer_valid = answer_result_ok and answer_slot_ok and answer_value_ok
        answer_confidence_ok = (
            answer_result_ok and answer_value_ok and answer_confidence >= answer_confidence_floor
        )
        answer_used = answer_confidence_ok or answer_valid
        answer_value_validated = True
        deterministic_matched, deterministic_value = _match_expected_reply(
            expected_reply_type=expected_reply_type,
            message_text=expected_reply_text,
            client_slug=payload.client_slug,
        )
        if deterministic_matched:
            if answer_used and isinstance(answer_value, str) and isinstance(deterministic_value, str):
                if answer_value != deterministic_value:
                    answer_error = "deterministic_override"
                    answer_confidence = 0.0
                    answer_value = deterministic_value
            matched = True
            value = deterministic_value
        else:
            if answer_used:
                answer_used = False
                answer_value_validated = False
                answer_confidence = 0.0
                answer_error = "deterministic_miss"
                answer_slot = ""
                answer_value = ""
            matched = False
            value = None
        answer_meta.update(
            {
                "answer_confidence": answer_confidence,
                "answer_slot": answer_slot,
                "answer_value": answer_value,
                "answer_error": answer_error,
            }
        )
        expected_reply_matched = matched
        if matched:
            expected_reply_shortcircuit = True
        if matched and isinstance(value, str) and expected_reply_type == EXPECTED_REPLY_SERVICE:
            context = _set_service_hint(context, value, now)
            _set_conversation_context(conversation, context)
            _maybe_store_service_carryover(
                conversation=conversation,
                service_meta={
                    "service_query": value,
                    "service_query_source": "expected_reply",
                    "service_query_score": 1.0,
                },
                intent=None,
                message_count=message_count,
                reason="expected_reply",
            )
            context = _get_conversation_context(conversation)
        if matched and isinstance(value, str):
            context = _apply_expected_reply_slot(
                context,
                expected_reply_type=expected_reply_type,
                value=value,
            )
            _set_conversation_context(conversation, context)
        if matched:
            next_expected = EXPECTED_REPLY_INTENT_CHOICE if intent_queue else None
            context = _set_expected_reply_type(context, next_expected)
            _set_conversation_context(conversation, context)
        if matched and isinstance(value, str) and isinstance(expected_reply_type, str):
            context = _get_conversation_context(conversation)
            context, memory = _update_session_memory_on_answer(
                context,
                expected_reply_type=expected_reply_type,
                value=value,
                now=now,
            )
            _set_conversation_context(conversation, context)
            _record_session_memory_update(
                conversation,
                saved_message,
                memory=memory,
                reason="answer_matched",
            )
        if expected_reply_shortcircuit:
            context_manager = _get_context_manager(context)
            if context_manager.get("current_goal") != "booking":
                context_manager["current_goal"] = "booking"
                context = _set_context_manager(context, context_manager)
                _set_conversation_context(conversation, context)
                _record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="current_goal",
                    updates={"current_goal": "booking"},
                )
                context, memory = _update_session_memory_goal(
                    context, active_goal="booking", now=now
                )
                _set_conversation_context(conversation, context)
                _record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=memory,
                    reason="active_goal",
                )
            current_goal = "booking"
        trace_payload = {
            "stage": "question_contract",
            "decision": "matched" if matched else "missed",
            "expected_reply_type": expected_reply_type,
            "value": value,
        }
        if expected_reply_shortcircuit:
            trace_payload["expected_reply_shortcircuit"] = True
        if expected_reply_blocked_by_info:
            trace_payload["expected_reply_blocked_by_info"] = True
            trace_payload.update(
                _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="expected_reply_deferred",
                )
            )
        trace_payload.update(answer_meta)
        if not answer_value_validated:
            trace_payload["expected_reply_value_validated"] = False
        _record_decision_trace(conversation, trace_payload)
        if saved_message:
            updates = {
                "expected_reply_type": expected_reply_type,
                "expected_reply_matched": matched,
                "expected_reply_value": value,
            }
            if expected_reply_shortcircuit:
                updates["expected_reply_shortcircuit"] = True
            if expected_reply_blocked_by_info:
                updates["expected_reply_blocked_by_info"] = True
            updates.update(answer_meta)
            if not answer_value_validated:
                updates["expected_reply_value_validated"] = False
            _update_message_decision_metadata(saved_message, updates)
        context = _get_conversation_context(conversation)
        expected_reply_type = _get_expected_reply_type(context)
        intent_queue = _get_intent_queue(context)

    # 4.5 Branch routing (instance_id -> branch, or ask user)
    branch_response = _handle_branch_selection_gate(
        db=db,
        client_id=client.id,
        settings=settings,
        conversation=conversation,
        user=user,
        metadata=metadata,
        message_text=message_text,
        now=now,
        send_and_save=_send_and_save,
    )
    if branch_response:
        return branch_response

    if conversation.branch_id:
        timing_context["branch_id"] = str(conversation.branch_id)
        if "knowledge_tag" not in timing_context:
            branch = (
                db.query(Branch).filter(Branch.id == conversation.branch_id).first()
            )
            if branch and branch.knowledge_tag:
                timing_context["knowledge_tag"] = branch.knowledge_tag

    # 4.9 Behavioral shield (pre-LAW/policy).
    shield_response = _handle_shield_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        metadata=metadata,
        now=now,
        saved_message=saved_message,
        send_and_save=_send_and_save,
        record_escalation_metric=_record_escalation_metric,
        skip_persist=skip_persist,
    )
    if shield_response:
        return shield_response

    # 5. Check session timeout - reset mute if no messages for 24h+
    bot_response = None
    sent = False
    result_message = None
    intent = None

    _apply_session_timeout_reset(
        conversation=conversation,
        previous_last_message_at=previous_last_message_at,
        now=now,
    )

    _forward_pending_to_telegram(
        db=db,
        client_id=client.id,
        conversation=conversation,
        metadata=metadata,
        message_text=message_text,
        has_media=has_media,
        media_info=media_info,
        media_decision=media_decision,
        media_policy=media_policy,
        saved_message=saved_message,
        transcript=transcript,
    )

    manager_active_response = _handle_manager_active_gate(
        db=db,
        conversation=conversation,
        saved_message=saved_message,
    )
    if manager_active_response:
        return manager_active_response

    # 8.1 Detect signals early for re-engage and mute decisions.
    reengage_response, batch_messages, reengage_override = _handle_reengage_and_mute_gate(
        db=db,
        client_id=client.id,
        client_slug=payload.client_slug,
        conversation=conversation,
        message_text=message_text,
        batch_messages=batch_messages,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        now=now,
        send_and_save=_send_and_save,
    )
    if reengage_response:
        return reengage_response

    # 9.01 ASR low-confidence confirmation (bot-active only).
    context = _get_conversation_context(conversation)
    asr_confirmation = _get_asr_confirmation(context)
    if not routing.get("allow_bot_reply"):
        if asr_confirmation:
            context = _set_asr_confirmation(context, None)
            _set_conversation_context(conversation, context)
    else:
        if asr_confirmation:
            if not _is_asr_confirmation_active(asr_confirmation, now):
                context = _set_asr_confirmation(context, None)
                _set_conversation_context(conversation, context)
                asr_confirmation = None
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    confirmed_text = (asr_confirmation.get("transcript") or "").strip()
                    context = _set_asr_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    if confirmed_text:
                        message_text = confirmed_text
                        if not batch_messages_provided:
                            batch_messages = _coerce_batch_messages(message_text, None)
                    else:
                        bot_response = MSG_ASR_CONFIRM_DECLINED
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "media",
                                "decision": "asr_confirm_missing_transcript",
                                "reason": "empty_transcript",
                                "state": conversation.state,
                            },
                        )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "ASR confirm missing transcript" if sent else "ASR confirm response failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                elif decision == "no":
                    context = _set_asr_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    bot_response = MSG_ASR_CONFIRM_DECLINED
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "media",
                            "decision": "asr_confirm_declined",
                            "reason": "user_declined",
                            "state": conversation.state,
                        },
                    )
                    bot_response, sent = _send_and_save(bot_response)
                    result_message = "ASR confirm declined" if sent else "ASR confirm decline failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )
                else:
                    context = _set_asr_confirmation(context, None)
                    _set_conversation_context(conversation, context)

        if asr_low_confidence and transcript:
            attempt = int(asr_confirmation.get("attempt", 0)) + 1 if asr_confirmation else 1
            confirmation_payload = {
                "asked_at": now.isoformat(),
                "transcript": transcript.strip(),
                "attempt": attempt,
            }
            context = _set_asr_confirmation(context, confirmation_payload)
            _set_conversation_context(conversation, context)
            bot_response = MSG_ASR_CONFIRM.format(text=confirmation_payload["transcript"])
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {"asr_confirm_requested": True, "asr_low_confidence": True},
                )
            _record_decision_trace(
                conversation,
                {
                    "stage": "media",
                    "decision": "asr_confirm_requested",
                    "reason": "low_confidence",
                    "state": conversation.state,
                    "attempt": attempt,
                },
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = "ASR confirmation requested" if sent else "ASR confirmation send failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    pending_response = _handle_pending_gate(
        db=db,
        conversation=conversation,
        message_text=message_text,
        saved_message=saved_message,
        now=now,
        send_and_save=_send_and_save,
    )
    if pending_response:
        return pending_response

    if has_media:
        if not media_info:
            bot_response = MSG_MEDIA_UNSUPPORTED
            if is_media_without_text:
                router_media_meta = _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="media_only",
                )
                trace_payload = {
                    "stage": "media",
                    "decision": "unsupported",
                    "state": conversation.state,
                }
                trace_payload.update(router_media_meta)
                _record_decision_trace(conversation, trace_payload)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Media unsupported response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        if media_decision is None and media_policy:
            media_decision = await _evaluate_media_decision(
                media=media_info,
                client_id=client.id,
                remote_jid=remote_jid,
                policy=media_policy,
                redis_client=media_redis_client,
                count_rate_limit=count_rate_limit,
            )

        if media_decision and not media_decision.allowed:
            bot_response = media_decision.response or MSG_MEDIA_UNSUPPORTED
            if is_media_without_text:
                router_media_meta = _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="media_only",
                )
                trace_payload = {
                    "stage": "media",
                    "decision": "rejected",
                    "state": conversation.state,
                }
                trace_payload.update(router_media_meta)
                _record_decision_trace(conversation, trace_payload)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Media rejected response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        storage_path = None
        if saved_message and isinstance(saved_message.message_metadata, dict):
            storage_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")

        if media_policy and media_policy.get("store_media") and not storage_path:
            storage_result = await _store_media_locally(
                media=media_info,
                policy=media_policy,
                client_slug=client.name,
                conversation_id=conversation.id,
                message_id=message_id,
            )
            if storage_result.get("stored"):
                storage_path = storage_result.get("path")
            if saved_message:
                update_payload = {
                    "storage_path": storage_result.get("path"),
                    "stored": bool(storage_result.get("stored")),
                    "storage_error": storage_result.get("error"),
                    "size_bytes": storage_result.get("size_bytes") or media_info.size_bytes,
                    "sha256": storage_result.get("sha256"),
                }
                _update_message_media_metadata(saved_message, update_payload)

        media_response = None
        media_escalated = False
        media_text_placeholder = _is_placeholder_text(message_text)
        asr_failed = bool(asr_meta and asr_meta.get("asr_failed"))
        style_request = _is_style_reference_request(
            message_text,
            has_media=media_info.media_type == "photo",
        )

        if conversation.state == ConversationState.BOT_ACTIVE.value:
            if media_text_placeholder and _is_voice_note(media_info) and asr_failed:
                media_response = MSG_MEDIA_TRANSCRIPT_FAILED
            elif style_request and media_info.media_type == "photo":
                handover_text = message_text.strip()
                if media_text_placeholder:
                    handover_text = "Клиент отправил фото/референс."
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=handover_text,
                    source="media_style",
                    intent="style_reference",
                )
                if reused:
                    result_message = (
                        f"Style reference reuse, telegram={'sent' if telegram_sent else 'failed'}"
                    )
                    media_escalated = True
                    media_response = MSG_MEDIA_STYLE_REFERENCE
                else:
                    _record_escalation_metric("media")
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=handover_text,
                        trigger_type="media",
                        trigger_value="style_reference",
                    )
                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=handover_text,
                        )
                        result_message = (
                            f"Style reference escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        )
                        media_escalated = True
                        media_response = MSG_MEDIA_STYLE_REFERENCE
                    else:
                        bot_response = MSG_AI_ERROR
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "Style reference escalation failed" if sent else "Media escalation response failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
            elif style_request:
                media_response = MSG_STYLE_REFERENCE_NEED_MEDIA
            elif media_text_placeholder:
                if media_info.media_type == "document":
                    media_response = MSG_MEDIA_DOC_RECEIVED
                else:
                    media_response = MSG_MEDIA_RECEIVED

        elif conversation.state == ConversationState.PENDING.value:
            if media_text_placeholder and _is_voice_note(media_info) and asr_failed:
                media_response = MSG_MEDIA_TRANSCRIPT_FAILED
            elif style_request:
                media_response = MSG_STYLE_REFERENCE_NEED_MEDIA
            elif media_text_placeholder:
                media_response = MSG_MEDIA_PENDING_NEED_TEXT

        if (
            (conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value] or media_escalated)
            and conversation.telegram_topic_id
            and not (metadata and metadata.forwarded_to_telegram)
            and (media_policy or {}).get("forward_to_telegram")
        ):
            bot_token, chat_id = get_telegram_credentials(db, client.id)
            if bot_token and chat_id:
                telegram = TelegramService(bot_token)
                caption = _build_media_caption(message_text, media_info)
                forward_result = _send_telegram_media(
                    telegram=telegram,
                    chat_id=chat_id,
                    topic_id=conversation.telegram_topic_id,
                    media=media_info,
                    caption=caption,
                    stored_path=storage_path,
                )
                if forward_result.get("ok"):
                    if metadata:
                        metadata.forwarded_to_telegram = True
                    if saved_message:
                        _update_message_media_metadata(saved_message, {"forwarded_to_telegram": True})
                else:
                    logger.warning(
                        "Media forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") or forward_result.get("error"),
                            }
                        },
                    )

        if media_response is not None and conversation.state != ConversationState.MANAGER_ACTIVE.value:
            bot_response = media_response
            if is_media_without_text:
                router_media_meta = _set_router_observability(
                    saved_message,
                    eligible=False,
                    reason="media_only",
                )
                trace_payload = {
                    "stage": "media",
                    "decision": "media_only",
                    "state": conversation.state,
                }
                trace_payload.update(router_media_meta)
                _record_decision_trace(conversation, trace_payload)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Media response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    # 9.0 Debounce bursty inputs: only the latest message triggers bot logic.
    (
        debounce_response,
        message_text,
        batch_messages,
        append_user_message,
        now,
    ) = await _handle_debounce_gate(
        db=db,
        client=client,
        conversation=conversation,
        message_text=message_text,
        message_id=message_id,
        remote_jid=remote_jid,
        batch_messages=batch_messages,
        batch_messages_provided=batch_messages_provided,
        payload_client_slug=payload.client_slug,
        now=now,
    )
    if debounce_response:
        return debounce_response

    # 9.02 Pending handover confirmation before other flows.
    handover_response = _handle_handover_confirmation_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        now=now,
        send_and_save=_send_and_save,
        record_escalation_metric=_record_escalation_metric,
    )
    if handover_response:
        return handover_response

    batch_messages = _coerce_batch_messages(message_text, batch_messages)
    booking_messages = batch_messages
    booking_context = None
    booking = None
    booking_active = False
    opt_out_in_batch = any(is_opt_out_message(msg) for msg in booking_messages)
    if reengage_override:
        opt_out_in_batch = False
    bypass_domain_flows = opt_out_in_batch
    if routing["allow_booking_flow"]:
        booking_context = _get_conversation_context(conversation)
        booking = _get_booking_context(booking_context)
        booking_active = bool(booking.get("active"))
        if opt_out_in_batch and booking_active:
            booking_context = _set_booking_context(booking_context, {"active": False})
            booking_context = _clear_service_hint(booking_context)
            _set_conversation_context(conversation, booking_context)
            booking_active = False
    booking_block_meta = None
    if not bypass_domain_flows:
        booking_signal, booking_block_meta = _evaluate_booking_signal(
            booking_messages,
            client_slug=payload.client_slug,
            message_text=message_text,
        )
    else:
        booking_signal = False

    # 6.95 Hard-LAW pre-LLM gate (policy-pack driven).
    hard_law_response = _handle_hard_law_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        policy_pack=policy_pack,
        bypass_domain_flows=bypass_domain_flows,
        routing=routing,
        policy_type=policy_type,
        policy_source=policy_source,
        policy_pack_missing=policy_pack_missing,
        client_slug=payload.client_slug,
        send_and_save=_send_and_save,
        record_policy_count=record_policy_count,
        record_escalation_metric=_record_escalation_metric,
        log_timing=_log_timing,
    )
    if hard_law_response:
        return hard_law_response
    intent_decomp_payload = None
    intent_decomp_intents: list[str] = []
    intent_decomp_primary = None
    intent_decomp_secondary: list[str] = []
    intent_decomp_service_query = None
    intent_decomp_multi = False
    intent_decomp_used = False
    consult_intent = False
    consult_topic = None
    consult_question = None
    intent_queue_choice = None
    intent_queue_followup = None
    intent_queue_intents: list[str] = []
    pending_intent_queue: list[str] | None = None
    pending_expected_reply_type: str | None = None
    intent_queue_expected_next: str | None = None
    intent_queue_event: dict | None = None
    if routing["allow_bot_reply"] and not bypass_domain_flows and message_text:
        intent_decomp_payload = detect_multi_intent(message_text, client_slug=payload.client_slug)
        if isinstance(intent_decomp_payload, dict):
            intent_decomp_used = True
            raw_intents = intent_decomp_payload.get("intents")
            if isinstance(raw_intents, list):
                intent_decomp_intents = [
                    item.strip().casefold()
                    for item in raw_intents
                    if isinstance(item, str) and item.strip()
                ]
            primary = intent_decomp_payload.get("primary_intent")
            if isinstance(primary, str):
                intent_decomp_primary = primary.strip().casefold()
            secondary = intent_decomp_payload.get("secondary_intents") or []
            if isinstance(secondary, list):
                intent_decomp_secondary = [
                    item.strip().casefold()
                    for item in secondary
                    if isinstance(item, str) and item.strip()
                ]
            if not intent_decomp_intents:
                if intent_decomp_primary:
                    intent_decomp_intents.append(intent_decomp_primary)
                for item in intent_decomp_secondary:
                    if item not in intent_decomp_intents:
                        intent_decomp_intents.append(item)
            intent_decomp_multi = bool(intent_decomp_payload.get("multi_intent") is True)
            service_query = intent_decomp_payload.get("service_query")
            if isinstance(service_query, str):
                service_query = service_query.strip()
                if service_query:
                    intent_decomp_service_query = service_query
            consult_intent = intent_decomp_payload.get("consult_intent") is True
            consult_topic = intent_decomp_payload.get("consult_topic")
            if isinstance(consult_topic, str):
                consult_topic = consult_topic.strip() or None
            else:
                consult_topic = None
            consult_question = intent_decomp_payload.get("consult_question")
            if isinstance(consult_question, str):
                consult_question = consult_question.strip() or None
            else:
                consult_question = None
            service_query_source = "intent_decomp"
            service_query_score = 1.0 if intent_decomp_service_query else 0.0
            consult_meta = {}
            if consult_intent:
                consult_meta["consult_intent"] = True
            if consult_topic:
                consult_meta["consult_topic"] = consult_topic
            if consult_question:
                consult_meta["consult_question"] = consult_question
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "intent_decomp_used": True,
                        "intents": intent_decomp_intents,
                        "service_query": intent_decomp_service_query,
                        "service_query_source": service_query_source,
                        "service_query_score": service_query_score,
                        **consult_meta,
                    },
                )
            _record_decision_trace(
                conversation,
                {
                    "stage": "intent_decomposition",
                    "intents": intent_decomp_intents,
                    "primary_intent": intent_decomp_primary,
                    "secondary_intents": intent_decomp_secondary,
                    "multi_intent": intent_decomp_multi,
                    "service_query": intent_decomp_service_query,
                    "service_query_source": service_query_source,
                    "service_query_score": service_query_score,
                    **consult_meta,
                },
            )

    if expected_reply_type == EXPECTED_REPLY_INTENT_CHOICE and intent_queue and message_text:
        intent_queue_choice = _select_intent_from_queue(
            intent_queue,
            intent_decomp_intents if intent_decomp_used else [],
            message_text=message_text,
        )
        if intent_queue_choice:
            if intent_queue_choice == "booking":
                pending_intent_queue = []
                pending_expected_reply_type = None
                intent_queue_expected_next = "booking"
            else:
                pending_intent_queue = [
                    intent for intent in intent_queue if intent != intent_queue_choice
                ]
                pending_expected_reply_type = (
                    EXPECTED_REPLY_INTENT_CHOICE if pending_intent_queue else None
                )
                intent_queue_expected_next = pending_expected_reply_type
            intent_queue_event = {
                "decision": "dequeue",
                "chosen_intent": intent_queue_choice,
                "remaining_queue": pending_intent_queue,
                "expected_reply_matched": True,
                "expected_reply_choice": intent_queue_choice,
                "expected_reply_next": intent_queue_expected_next,
            }
            if intent_decomp_used:
                reordered_intents = [intent_queue_choice] + [
                    intent for intent in intent_decomp_intents if intent != intent_queue_choice
                ]
                intent_decomp_intents = reordered_intents
                intent_decomp_primary = intent_queue_choice
                intent_decomp_secondary = [
                    intent for intent in reordered_intents if intent != intent_decomp_primary
                ]
                intent_decomp_multi = len(reordered_intents) > 1
                if isinstance(intent_decomp_payload, dict):
                    intent_decomp_payload = {
                        **intent_decomp_payload,
                        "primary_intent": intent_decomp_primary,
                        "secondary_intents": intent_decomp_secondary,
                        "intents": intent_decomp_intents,
                        "multi_intent": intent_decomp_multi,
                    }
        else:
            intent_queue_event = {
                "decision": "no_match",
                "expected_reply_type": expected_reply_type,
                "intent_queue": intent_queue,
                "intents": intent_decomp_intents,
                "expected_reply_matched": False,
            }

    intent_decomp_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent} if intent_decomp_used else set()
    info_class_intents: set[str] = set()
    info_class_meta: dict[str, Any] = {}
    if message_text:
        info_class_intents, info_class_meta = _detect_info_class_intents(
            message_text,
            intent_decomp_set=intent_decomp_set,
        )
        if payload.client_slug == "demo_salon" and _matches_guest_policy_lexicon(message_text):
            if not isinstance(info_class_meta, dict):
                info_class_meta = {}
            info_signals = info_class_meta.get("info_signals")
            if not isinstance(info_signals, dict):
                info_signals = {}
            info_signals["guest"] = True
            info_class_meta["info_signals"] = info_signals
    info_signals = (
        info_class_meta.get("info_signals")
        if isinstance(info_class_meta, dict)
        else None
    )
    basic_info_message = bool(
        {"location", "hours"} & info_class_intents
        or (
            isinstance(info_signals, dict)
            and (info_signals.get("parking") or info_signals.get("guest"))
        )
    )
    carryover_followup = _looks_like_carryover_followup(message_text)
    allow_service_carryover = bool(carryover_followup and not basic_info_message)
    preserve_info_carryover = bool(
        not os.environ.get("OPENAI_API_KEY")
        and isinstance(class_carryover, dict)
        and class_carryover.get("class") == "info_bundle"
        and class_carryover.get("info_sections")
    )
    if not allow_service_carryover:
        existing_service_carryover = _get_service_carryover(
            context_manager, message_count=message_count
        )
        if (basic_info_message or class_carryover or existing_service_carryover) and not preserve_info_carryover:
            carryover_reason = "basic_info_lock" if basic_info_message else "no_followup"
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "carryover_ignored": True,
                        "carryover_ignored_reason": carryover_reason,
                    },
                )
            _record_decision_trace(
                conversation,
                {
                    "stage": "carryover_guard",
                    "decision": "ignored",
                    "reason": carryover_reason,
                },
            )
        if not preserve_info_carryover:
            class_carryover = None
    consult_interrupt_intents = (
        intent_decomp_set & CONSULT_INTERRUPT_INTENTS if intent_decomp_used else set()
    )
    if (
        current_goal == "consult"
        and consult_context
        and not consult_intent
        and (consult_interrupt_intents or booking_signal)
    ):
        consult_return_pending = True
        consult_return_reason = (
            "intent_interrupt" if consult_interrupt_intents else "booking_signal"
        )
        consult_return_prompt = _build_consult_return_prompt(consult_context)
    if intent_decomp_used:
        new_goal = _resolve_current_goal(intent_decomp_set, consult_intent)
        if not expected_reply_shortcircuit and not (
            current_goal == "consult" and consult_return_pending
        ):
            if new_goal and new_goal != current_goal:
                context = _get_conversation_context(conversation)
                context_manager = _get_context_manager(context)
                context_manager["current_goal"] = new_goal
                context = _set_context_manager(context, context_manager)
                _set_conversation_context(conversation, context)
                _record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="current_goal",
                    updates={"current_goal": new_goal},
                )
                context, memory = _update_session_memory_goal(
                    context, active_goal=new_goal, now=now
                )
                _set_conversation_context(conversation, context)
                _record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=memory,
                    reason="active_goal",
                )
                _update_compact_summary(
                    conversation=conversation,
                    saved_message=saved_message,
                    reason="intent_change",
                    now=now,
                )
                context = _get_conversation_context(conversation)
                current_goal = new_goal
    if booking_context is not None:
        booking_context = _get_conversation_context(conversation)
        booking = _get_booking_context(booking_context)
        booking_active = bool(booking.get("active"))

    if (
        intent_decomp_used
        and not consult_intent
        and not intent_decomp_service_query
        and intent_decomp_set & SERVICE_CARRYOVER_INTENTS
        and allow_service_carryover
    ):
        skip_service_carryover = False
        if isinstance(class_carryover, dict) and _looks_like_hours_followup(message_text):
            raw_sections = class_carryover.get("info_sections")
            if isinstance(raw_sections, list):
                for section in raw_sections:
                    if isinstance(section, str) and section.strip().casefold() == "hours":
                        skip_service_carryover = True
                        break
        if not skip_service_carryover:
            context = _get_conversation_context(conversation)
            context_manager = _get_context_manager(context)
            carryover = _get_service_carryover(context_manager, message_count=message_count)
            if carryover and isinstance(intent_decomp_payload, dict):
                intent_decomp_payload = dict(intent_decomp_payload)
                intent_decomp_payload["service_query"] = carryover["service_query"]
                intent_decomp_payload["service_query_source"] = "context"
                carryover_score = carryover.get("service_query_score")
                if isinstance(carryover_score, (int, float)):
                    intent_decomp_payload["service_query_score"] = carryover_score
                intent_decomp_service_query = carryover["service_query"]
                service_query_score = (
                    float(carryover_score)
                    if isinstance(carryover_score, (int, float))
                    else 1.0
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "service_query": carryover["service_query"],
                            "service_query_source": "context",
                            "service_query_score": service_query_score,
                            "service_query_ttl": carryover.get("ttl"),
                            "service_query_ttl_remaining": carryover.get("remaining"),
                        },
                    )
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "service_carryover",
                        "decision": "used",
                        "service_query": carryover["service_query"],
                        "service_query_source": "context",
                        "service_query_score": service_query_score,
                        "ttl": carryover.get("ttl"),
                        "ttl_remaining": carryover.get("remaining"),
                    },
                )
    intent_decomp_has_booking = "booking" in intent_decomp_set
    intent_decomp_info = intent_decomp_set & BOOKING_INFO_QUESTION_TYPES
    if expected_reply_shortcircuit:
        booking_signal = True
        booking_block_meta = None
    elif intent_decomp_has_booking:
        booking_signal = True
        if booking_block_meta and booking_block_meta.get("booking_blocked_reason") == "info_question":
            booking_block_meta = None
    else:
        if booking_signal and not booking_block_meta:
            if intent_decomp_info:
                booking_block_meta = {
                    "booking_blocked_reason": "info_question",
                    "question_intents": sorted(intent_decomp_info),
                }
            elif intent_decomp_used and intent_decomp_set and intent_decomp_set != {"other"}:
                booking_block_meta = {
                    "booking_blocked_reason": "intent_decomp_no_booking",
                }
            elif not intent_decomp_used:
                booking_block_meta = {
                    "booking_blocked_reason": "intent_decomp_missing",
                }
        if booking_block_meta:
            booking_signal = False

    booking_wants_flow = (
        _should_run_booking_flow(
            routing,
            booking_active=booking_active,
            booking_signal=booking_signal,
        )
        if not bypass_domain_flows
        else False
    )
    if booking_block_meta:
        _record_decision_trace(
            conversation,
            {
                "stage": "booking_gate",
                "decision": "booking_blocked",
                **booking_block_meta,
            },
        )
        if saved_message:
            existing_meta = (
                saved_message.message_metadata.get("decision_meta")
                if isinstance(saved_message.message_metadata, dict)
                else None
            )
            if not isinstance(existing_meta, dict) or "booking_blocked_reason" not in existing_meta:
                _update_message_decision_metadata(saved_message, booking_block_meta)
        if booking_active:
            context = booking_context if isinstance(booking_context, dict) else _get_conversation_context(conversation)
            booking_state = booking if isinstance(booking, dict) else _get_booking_context(context)
            booking_state = dict(booking_state)
            booking_state["active"] = False
            booking_state["last_question"] = None
            booking_state["service"] = None
            booking_state["datetime"] = None
            context = _set_booking_context(context, booking_state)
            _set_conversation_context(conversation, context)
            booking_active = False
            booking = booking_state
        booking_signal = False
        booking_wants_flow = False
    booking_blocked = bool(booking_block_meta)

    multi_intent_primary = None
    multi_intent_secondary: list[str] = []
    multi_intent_followup = None
    multi_intent_booking_followup = None
    multi_intent_other_followup = None

    opt_out_response = _handle_opt_out_mute_gate(
        db=db,
        client_id=client.id,
        conversation=conversation,
        saved_message=saved_message,
        opt_out_in_batch=opt_out_in_batch,
        booking_signal=booking_signal,
        now=now,
        send_and_save=_send_and_save,
    )
    if opt_out_response:
        return opt_out_response

    # 9.03 Policy escalation gate (policy-pack keywords + intent fallback).
    policy_response = _handle_policy_escalation_gate(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        policy_pack=policy_pack,
        hard_law_sections=hard_law_sections,
        bypass_domain_flows=bypass_domain_flows,
        routing=routing,
        policy_type=policy_type,
        policy_source=policy_source,
        policy_pack_missing=policy_pack_missing,
        booking_wants_flow=booking_wants_flow,
        intent_hints=intent_decomp_intents if policy_pack else None,
        consult_intent=consult_intent,
        current_goal=current_goal,
        multi_intent_other_followup=multi_intent_other_followup,
        client_slug=payload.client_slug,
        send_and_save=_send_and_save,
        record_policy_count=record_policy_count,
        record_escalation_metric=_record_escalation_metric,
        log_timing=_log_timing,
    )
    if policy_response:
        return policy_response

    controller_signal_class = _resolve_controller_signal_class(
        intent_decomp_set=intent_decomp_set,
        booking_signal=booking_signal,
    )
    controller_state: dict[str, Any] | None = {
        "used": False,
        "confidence": 0.0,
        "output": _build_controller_meta_output(error="skipped"),
        "error": "skipped",
        "fallback_reason": "skipped",
        "signal_class": controller_signal_class,
        "signal_match": False,
        "used_reason": None,
        "attempted": False,
        "sla": None,
    }
    controller_should_attempt = bool(
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and not booking_wants_flow
        and not expected_reply_shortcircuit
        and os.environ.get("OPENAI_API_KEY")
    )
    if controller_should_attempt:
        controller_state["attempted"] = True
        controller_state["error"] = None
        controller_state["fallback_reason"] = "skipped"
        controller_result = route_dialogue_controller(
            message_text,
            carryover=class_carryover,
            expected_reply_type=expected_reply_type,
            client_slug=payload.client_slug,
            client_config=client.config if client else None,
            timing_context=timing_context,
        )
        if isinstance(controller_result, dict) and controller_result.get("ok") is True:
            controller_output = controller_result.get("payload")
            if isinstance(controller_output, dict):
                controller_state["output"] = _ensure_controller_output_meta(controller_output, error=None)
                confidence = controller_output.get("confidence")
                if isinstance(confidence, (int, float)):
                    controller_state["confidence"] = float(confidence)
            controller_class = controller_output.get("class")
            normalized_class = (
                _normalize_class_name(controller_class)
                if isinstance(controller_class, str) and controller_class.strip()
                else None
            )
            signal_match = bool(controller_signal_class and normalized_class == controller_signal_class)
            controller_state["signal_match"] = signal_match
            if normalized_class:
                controller_state["used"] = True
                controller_state["used_reason"] = "controller"
                controller_state["fallback_reason"] = None
            else:
                controller_state["used"] = False
                controller_state["fallback_reason"] = _normalize_controller_fallback_reason(
                    error="invalid_class"
                )
        else:
            controller_state["error"] = (
                controller_result.get("error")
                if isinstance(controller_result, dict)
                else "controller_failed"
            )
            controller_state["fallback_reason"] = _normalize_controller_fallback_reason(
                error=controller_state["error"]
            )
            controller_state["confidence"] = 0.0
            controller_output = controller_result.get("payload") if isinstance(controller_result, dict) else None
            if isinstance(controller_output, dict):
                controller_state["output"] = _ensure_controller_output_meta(
                    controller_output, error=controller_state["error"]
                )
            else:
                controller_state["output"] = _build_controller_meta_output(error=controller_state["error"])

    _record_llm_budget_trace()
    if isinstance(controller_state, dict):
        controller_output = controller_state.get("output")
        if isinstance(controller_output, dict):
            controller_output = _ensure_controller_output_meta(
                controller_output, error=controller_state.get("error")
            )
            controller_state["output"] = controller_output
            controller_error_value = controller_output.get("controller_error")
        else:
            controller_state["output"] = _build_controller_meta_output(
                error=str(controller_state.get("error") or "controller_failed")
            )
            controller_error_value = controller_state["output"].get("controller_error")
        controller_timeout = isinstance(controller_error_value, str) and controller_error_value == "timeout"
        controller_fallback_reason = controller_state.get("fallback_reason")
        if (
            isinstance(controller_fallback_reason, str)
            and controller_fallback_reason.strip().casefold() == "low_confidence"
        ):
            controller_state["fallback_reason"] = None
            controller_fallback_reason = None
        controller_fallback = controller_fallback_reason not in (None, "skipped")
        controller_state["timeout"] = controller_timeout
        controller_state["fallback"] = controller_fallback
        controller_state["sla"] = _update_router_sla(  # reuse SLA tracker
            attempted=bool(controller_state.get("attempted")),
            fallback=bool(controller_fallback),
            timeout=bool(controller_timeout),
        )
    router_state = controller_state

    early_domain_intent = DomainIntent.UNKNOWN
    early_domain_meta: dict = {}
    early_out_of_domain = False
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not bypass_domain_flows
        and message_text
    ):
        early_info_intents, early_info_meta = _detect_info_class_intents(
            message_text,
            intent_decomp_set=set(),
        )
        if not (
            is_greeting_message(message_text)
            or is_thanks_message(message_text)
            or is_acknowledgement_message(message_text)
            or is_low_signal_message(message_text)
            or is_bot_status_question(message_text)
            or is_human_request_message(message_text)
            or is_opt_out_message(message_text)
        ):
            early_domain_intent, _, _, early_domain_meta = classify_domain_with_scores(
                message_text, client.config if client else None
            )
            out_hits = int(early_domain_meta.get("out_hits") or 0)
            strict_in_hits = int(early_domain_meta.get("strict_in_hits") or 0)
            early_in_signals = bool(strict_in_hits > 0 or booking_signal or early_info_intents)
            early_out_of_domain = bool(out_hits > 0 and not early_in_signals)

    expected_reply_off_topic = (
        expected_reply_type == EXPECTED_REPLY_SERVICE
        and expected_reply_matched is False
        and not expected_reply_blocked_by_info
        and message_text
        and (early_out_of_domain or is_frustration_message(message_text))
    )
    if expected_reply_off_topic:
        bot_response = MSG_EXPECTED_SERVICE_OFF_TOPIC
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "out_of_domain",
                "decision": "expected_reply_off_topic",
                "state": conversation.state,
                "domain_intent": early_domain_intent.value,
                "out_hits": early_domain_meta.get("out_hits"),
                "strict_in_hits": early_domain_meta.get("strict_in_hits"),
                "info_intents": sorted(early_info_intents),
                "expected_reply_type": expected_reply_type,
                "expected_reply_reason": "off_topic",
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="out_of_domain",
            intent="out_of_domain",
            source="domain_router" if early_out_of_domain else "question_contract",
            fast_intent=False,
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "expected_reply_type": expected_reply_type,
                    "expected_reply_matched": False,
                    "expected_reply_reason": "off_topic",
                },
            )
        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        result_message = (
            "Expected reply off-topic response sent"
            if sent
            else "Expected reply off-topic response failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    in_domain_signal = bool(int(early_domain_meta.get("strict_in_hits") or 0) > 0)
    if early_domain_intent == DomainIntent.IN_DOMAIN:
        in_domain_signal = True
    expected_reply_invalid_choice = (
        expected_reply_type == EXPECTED_REPLY_SERVICE
        and expected_reply_matched is False
        and not expected_reply_blocked_by_info
        and message_text
        and not in_domain_signal
    )
    if expected_reply_invalid_choice:
        semantic_match = semantic_service_match(message_text, payload.client_slug)
        if not semantic_match:
            clarify_intent = current_goal or "info"
            context = _get_conversation_context(conversation)
            context_manager = _get_context_manager(context)
            if _should_escalate_for_clarify(context_manager, clarify_intent):
                clarify_count, _ = _get_clarify_attempt_state(context_manager, clarify_intent)
                clarify_reason = "consult_no_service" if clarify_intent == "consult" else "invalid_choice"
                _record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="clarify_limit",
                    updates={
                        "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                        "clarify_reason": clarify_reason,
                        "clarify_limit": True,
                    },
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "expected_reply_type": expected_reply_type,
                            "expected_reply_matched": False,
                            "expected_reply_reason": "invalid_choice",
                        },
                    )
                if clarify_intent == "consult":
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "consult_flow",
                            "decision": "consult_escalate",
                            "reason": "consult_no_service",
                            "state": conversation.state,
                            "expected_reply_type": expected_reply_type,
                        },
                    )
                    return _handle_clarify_limit_escalation(
                        db=db,
                        conversation=conversation,
                        user=user,
                        message_text=message_text,
                        saved_message=saved_message,
                        source="consult",
                        allow_handover=routing.get("allow_handover_create", False),
                        escalation_intent="consult_no_service",
                        send_response=_send_response,
                        finalize_response=_finalize_bot_response,
                    )
                return _handle_clarify_limit_escalation(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message_text=message_text,
                    saved_message=saved_message,
                    source="question_contract",
                    allow_handover=routing.get("allow_handover_create", False),
                    send_response=_send_response,
                    finalize_response=_finalize_bot_response,
                )
            _register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent=clarify_intent,
                now=now,
                reason="invalid_choice",
            )
            context = _get_conversation_context(conversation)
            context = _set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=EXPECTED_REPLY_SERVICE,
                reason="invalid_choice",
                now=now,
            )
            bot_response = MSG_EXPECTED_SERVICE_OFF_TOPIC
            _reset_low_confidence_retry(conversation)
            _record_decision_trace(
                conversation,
                {
                    "stage": "question_contract",
                    "decision": "invalid_choice",
                    "state": conversation.state,
                    "expected_reply_type": expected_reply_type,
                    "expected_reply_reason": "invalid_choice",
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="reply",
                intent="service_clarify",
                source="question_contract",
                fast_intent=False,
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "expected_reply_type": expected_reply_type,
                        "expected_reply_matched": False,
                        "expected_reply_reason": "invalid_choice",
                    },
                )
            bot_response, sent = _send_and_save(bot_response)
            result_message = (
                "Expected reply invalid choice response sent"
                if sent
                else "Expected reply invalid choice response failed"
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if early_out_of_domain:
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "out_of_domain",
                "decision": "early_block",
                "state": conversation.state,
                "domain_intent": early_domain_intent.value,
                "out_hits": early_domain_meta.get("out_hits"),
                "strict_in_hits": early_domain_meta.get("strict_in_hits"),
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="out_of_domain",
            intent="out_of_domain",
            source="domain_router",
            fast_intent=False,
        )
        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        result_message = "Out-of-domain early response sent" if sent else "Out-of-domain early response failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    promotions_router_class = None
    router_used = bool(router_state.get("used")) if isinstance(router_state, dict) else False
    router_output = router_state.get("output") if isinstance(router_state, dict) else None
    if isinstance(router_output, dict):
        raw_class = router_output.get("class")
        if isinstance(raw_class, str):
            promotions_router_class = _normalize_class_name(raw_class)
    discount_signal = _looks_like_promotions_request(
        message_text,
        policy_type=policy_type,
        policy_pack=policy_pack,
    )
    promotions_trigger = False
    if router_used and promotions_router_class in {"promotions", "discounts"}:
        promotions_trigger = True
    if discount_signal:
        promotions_trigger = True

    if (
        promotions_trigger
        and routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
    ):
        class_router_result = _resolve_class_router_result(
            info_intents=info_class_intents,
            info_meta=info_class_meta,
            booking_signal=booking_signal,
            class_carryover=class_carryover,
            domain_intent=DomainIntent.UNKNOWN,
            domain_meta=None,
            router_state=router_state,
        )
        if discount_signal:
            class_router_result = dict(class_router_result)
            classes = list(class_router_result.get("classes") or [])
            if "promotions" not in classes and "discounts" not in classes:
                classes.insert(0, "promotions")
            class_router_result["classes"] = classes
            in_signals = list(class_router_result.get("in_signals") or [])
            if "promotions_signal" not in in_signals:
                in_signals.append("promotions_signal")
            class_router_result["in_signals"] = in_signals

        promotion_intent = None
        if policy_type == "demo_salon":
            promotion_intent = _detect_promotion_intent(_normalize_text(message_text))
        promo_reply = None
        if promotion_intent == "promotion_birthday":
            promo_reply = format_reply_from_truth(
                "promotions",
                {"promotion_intent": promotion_intent},
            )
        if promo_reply:
            decision = DemoSalonDecision(
                action="reply",
                response=promo_reply,
                intent="promotions",
            )
        else:
            discounts_available = _has_discount_policy_rules(
                policy_pack=policy_pack,
                policy_type=policy_type,
            )
            discounts_reply = (
                _format_discounts_policy_reply(
                    policy_pack=policy_pack,
                    policy_type=policy_type,
                )
                if discounts_available
                else None
            )
            if discounts_reply:
                decision = DemoSalonDecision(
                    action="reply",
                    response=discounts_reply,
                    intent="discounts",
                )
            else:
                decision = DemoSalonDecision(
                    action="escalate",
                    response=MSG_ESCALATED,
                    intent="discounts",
                )

        bot_response = decision.response or MSG_ESCALATED
        followup_intents: list[str] = []
        if booking_signal or "booking" in intent_decomp_set:
            followup_intents.append("booking")
        for intent_name in ("location", "hours"):
            if intent_name in info_class_intents and intent_name not in followup_intents:
                followup_intents.append(intent_name)
        followup_prompt = None
        queue_set = False
        if followup_intents:
            if expected_reply_type is None and pending_intent_queue is None and not intent_queue_event:
                context = _get_conversation_context(conversation)
                context = _set_intent_queue(context, followup_intents)
                context = _set_expected_reply_type(context, EXPECTED_REPLY_INTENT_CHOICE)
                _set_conversation_context(conversation, context)
                followup_prompt = _format_intent_queue_prompt(followup_intents)
                queue_set = True
            else:
                followup_prompt = _format_multi_intent_followup("discounts", followup_intents)
        if followup_prompt:
            bot_response = _combine_sidecar(bot_response, followup_prompt)

        _reset_low_confidence_retry(conversation)
        record_policy_count(payload.client_slug, "discounts")

        result_message = "Policy discounts reply sent"
        if decision.action == "escalate":
            _, reused, telegram_sent = _reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source=policy_source,
                intent=decision.intent,
            )
            if reused:
                result_message = f"Policy discounts reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == ConversationState.BOT_ACTIVE.value and routing.get("allow_handover_create", False):
                _record_escalation_metric("intent")
                result = escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=decision.intent or "discounts",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Policy discounts escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Policy discounts escalation failed: {result.error}"
            else:
                result_message = "Policy discounts escalation skipped (already pending)"

        router_gate_meta = _set_router_observability(
            saved_message,
            eligible=False,
            reason="policy_gate",
        )
        trace_payload = {
            "stage": "policy_gate",
            "decision": decision.action,
            "intent": decision.intent,
            "state": conversation.state,
            "policy_type": policy_type,
            "policy_gate": "discounts",
            "source": policy_source,
            "class_router": class_router_result,
        }
        discounts_policy = policy_pack.get("discounts") if isinstance(policy_pack, dict) else None
        risk_level = discounts_policy.get("risk_level") if isinstance(discounts_policy, dict) else None
        if isinstance(risk_level, str) and risk_level:
            trace_payload["risk_level"] = risk_level
        trace_payload.update(router_gate_meta)
        if followup_intents:
            trace_payload["followup_intents"] = followup_intents
        _record_decision_trace(conversation, trace_payload)
        _record_message_decision_meta(
            saved_message,
            action=decision.action,
            intent=decision.intent,
            source=policy_source,
            fast_intent=False,
        )
        if saved_message:
            meta_updates = {
                "class_router": class_router_result,
                "policy_gate": "discounts",
                "source": policy_source,
            }
            if policy_pack_missing:
                meta_updates["policy_pack_missing"] = True
            if isinstance(risk_level, str) and risk_level:
                meta_updates["risk_level"] = risk_level
            if queue_set:
                meta_updates["intent_queue"] = followup_intents
                meta_updates["expected_reply_type"] = EXPECTED_REPLY_INTENT_CHOICE
            meta_updates.update(_controller_meta_updates_from_class_router(class_router_result))
            _update_message_decision_metadata(saved_message, meta_updates)

        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if intent_queue_event:
        _record_decision_trace(
            conversation,
            {
                "stage": "intent_queue",
                **intent_queue_event,
            },
        )
        if intent_queue_event.get("decision") == "no_match" and intent_queue:
            intent_queue_intents = intent_queue
            intent_queue_followup = _format_intent_queue_prompt(intent_queue)
        if saved_message:
            updates = {"intent_queue_choice": intent_queue_choice}
            if intent_queue_event.get("decision") == "dequeue":
                updates["intent_queue_remaining"] = pending_intent_queue or []
                updates["expected_reply_matched"] = True
                updates["expected_reply_choice"] = intent_queue_choice
                updates["expected_reply_next"] = intent_queue_expected_next
            else:
                updates["intent_queue_missed"] = True
                updates["expected_reply_matched"] = False
            _update_message_decision_metadata(saved_message, updates)

    if (
        intent_queue_choice
        and expected_reply_type == EXPECTED_REPLY_INTENT_CHOICE
        and intent_queue_choice in INFO_INTENTS
        and routing["allow_bot_reply"]
        and not bypass_domain_flows
    ):
        info_service_query = intent_decomp_service_query
        if not info_service_query and intent_queue_choice in {"pricing", "duration"}:
            info_service_query = _extract_service_hint(message_text, payload.client_slug)
        if (
            not info_service_query
            and intent_queue_choice in {"pricing", "duration"}
            and allow_service_carryover
        ):
            carryover = _get_service_carryover(context_manager, message_count=message_count)
            if carryover:
                info_service_query = carryover.get("service_query")

        info_reply, info_meta = _build_info_intent_reply(
            intent_queue_choice,
            service_query=info_service_query,
            client_slug=payload.client_slug,
            message_text=message_text,
        )
        info_reply = info_reply.strip() if isinstance(info_reply, str) else None
        if info_reply:
            guard_response = _maybe_apply_fact_guard(
                decision_meta=info_meta if isinstance(info_meta, dict) else None,
                intent=intent_queue_choice,
                source="intent_queue",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return guard_response
            remaining_queue = (
                pending_intent_queue
                if pending_intent_queue is not None
                else [intent for intent in intent_queue if intent != intent_queue_choice]
            )
            expected_next = EXPECTED_REPLY_INTENT_CHOICE if remaining_queue else None
            context = _get_conversation_context(conversation)
            context = _set_intent_queue(context, remaining_queue or None)
            context = _set_expected_reply_type(context, expected_next)
            _set_conversation_context(conversation, context)
            followup = _format_intent_queue_prompt(remaining_queue)
            bot_response = info_reply
            if followup:
                bot_response = f"{bot_response}\n\n{followup}"
            bot_response = _maybe_append_booking_cta(
                bot_response,
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=bool(followup),
            )
            if consult_return_pending:
                bot_response = _apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "intent_queue_info",
                )
            _reset_low_confidence_retry(conversation)
            trace_payload = {
                "stage": "intent_queue",
                "decision": "info_reply",
                "state": conversation.state,
                "chosen_intent": intent_queue_choice,
                "remaining_queue": remaining_queue,
                "expected_reply_next": expected_next,
            }
            if isinstance(info_meta, dict) and info_meta:
                trace_payload.update(info_meta)
            _record_decision_trace(conversation, trace_payload)
            _record_message_decision_meta(
                saved_message,
                action="reply",
                intent=intent_queue_choice,
                source="intent_queue",
                fast_intent=False,
            )
            if saved_message and isinstance(info_meta, dict) and info_meta:
                _update_message_decision_metadata(saved_message, info_meta)
            _maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=[intent_queue_choice],
                info_meta=info_meta,
                message_count=message_count,
                reason="intent_queue",
            )
            _maybe_store_service_carryover(
                conversation=conversation,
                service_meta=info_meta if isinstance(info_meta, dict) else None,
                intent=intent_queue_choice,
                message_count=message_count,
                reason="intent_queue_choice",
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = (
                "Intent queue info reply sent" if sent else "Intent queue info reply failed"
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if (
        intent_queue_choice == "booking"
        and expected_reply_type == EXPECTED_REPLY_INTENT_CHOICE
        and routing["allow_booking_flow"]
        and not bypass_domain_flows
    ):
        context = _get_conversation_context(conversation)
        context = _set_intent_queue(context, None)
        context_manager = _get_context_manager(context)
        booking_state = _get_booking_context(context)
        booking_state = dict(booking_state)
        if not booking_state.get("active"):
            booking_state["active"] = True
            booking_state["started_at"] = now.isoformat()
        booking_state = _update_booking_from_messages(
            booking_state,
            booking_messages,
            client_slug=payload.client_slug,
        )
        if not booking_state.get("service"):
            service_hint = _get_recent_service_hint(context, now)
            if service_hint:
                booking_state["service"] = service_hint
                context = _clear_service_hint(context)
        if not booking_state.get("service") and allow_service_carryover:
            carryover = _get_service_carryover(context_manager, message_count=message_count)
            if carryover:
                booking_state["service"] = carryover.get("service_query")
        refusal_flags = context_manager.get("refusal_flags") if isinstance(context_manager, dict) else None
        booking_state, prompt = _next_booking_prompt(booking_state, refusal_flags=refusal_flags)
        context = _set_booking_context(context, booking_state)
        _set_conversation_context(conversation, context)
        booking_expected = _expected_reply_for_booking_question(booking_state.get("last_question"))
        if prompt and booking_expected:
            context = _set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=booking_expected,
                reason="booking_prompt",
                now=now,
            )
        _record_decision_trace(
            conversation,
            {
                "stage": "booking",
                "decision": "prompt",
                "state": conversation.state,
                "missing_slot": booking_state.get("last_question"),
                "source": "intent_queue",
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="booking_prompt",
            intent="booking",
            source="intent_queue",
            fast_intent=False,
        )
        bot_response = prompt or MSG_BOOKING_ASK_DATETIME
        if consult_return_pending:
            bot_response = _apply_consult_return(
                conversation=conversation,
                saved_message=saved_message,
                bot_response=bot_response,
                consult_return_prompt=consult_return_prompt,
                consult_context=consult_context,
                reason=consult_return_reason or "intent_queue_booking",
            )
        _reset_low_confidence_retry(conversation)
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Intent queue booking prompt sent" if sent else "Intent queue booking prompt failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if (
        intent_decomp_used
        and expected_reply_type is None
        and not intent_queue_event
        and pending_intent_queue is None
        and routing["allow_bot_reply"]
        and routing["allow_truth_gate_reply"]
        and not bypass_domain_flows
        and message_text
        and policy_type == "demo_salon"
    ):
        combined_intents: list[str] = []
        seen_intents: set[str] = set()
        for intent_name in intent_decomp_intents:
            normalized = intent_name.strip().casefold()
            if not normalized or normalized in seen_intents:
                continue
            combined_intents.append(normalized)
            seen_intents.add(normalized)

        truth_gate_intents: list[str] = []
        if "booking" in intent_decomp_set:
            truth_gate_intents = _extract_truth_gate_info_intents(
                message_text,
                policy_handler=policy_handler,
                policy_type=policy_type,
                client_slug=payload.client_slug,
                intent_decomp=intent_decomp_payload,
            )
        for intent_name in truth_gate_intents:
            if intent_name not in seen_intents:
                combined_intents.append(intent_name)
                seen_intents.add(intent_name)

        combined_set = set(combined_intents)
        info_intents = [intent for intent in combined_intents if intent in INFO_INTENTS]
        info_intent_set = set(info_intents)
        should_defer_booking = (
            "booking" in combined_set
            and info_intent_set
            and (len(info_intent_set) >= 2 or len(combined_set) >= 3)
        )
        if should_defer_booking:
            info_service_query = intent_decomp_service_query
            if not info_service_query and {"pricing", "duration"} & info_intent_set:
                info_service_query = _extract_service_hint(message_text, payload.client_slug)
            priority = (
                INFO_INTENT_PRIORITY_SERVICE
                if info_service_query
                else INFO_INTENT_PRIORITY_GENERIC
            )
            answer_intents: list[str] = []
            for intent_name in priority:
                if intent_name in info_intent_set and intent_name not in answer_intents:
                    answer_intents.append(intent_name)
                if len(answer_intents) >= 2:
                    break
            if not answer_intents:
                answer_intents = info_intents[:2]

            replies: list[str] = []
            seen_replies: set[str] = set()
            answered_intents: list[str] = []
            info_meta: dict = {}
            service_meta: dict | None = None
            for intent_name in answer_intents:
                reply, meta = _build_info_intent_reply(
                    intent_name,
                    service_query=info_service_query,
                    client_slug=payload.client_slug,
                    message_text=message_text,
                )
                if isinstance(reply, str):
                    reply = reply.strip()
                    if reply and reply not in seen_replies:
                        replies.append(reply)
                        seen_replies.add(reply)
                        answered_intents.append(intent_name)
                if isinstance(meta, dict) and meta:
                    info_meta.update(meta)
                    service_meta = dict(info_meta)
            if replies:
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=info_meta if info_meta else None,
                    intent="multi_intent_info",
                    source="intent_queue",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                answered_set = set(answered_intents)
                remaining_queue = [
                    intent for intent in combined_intents if intent not in answered_set
                ]
                context = _get_conversation_context(conversation)
                expected_next = EXPECTED_REPLY_INTENT_CHOICE if remaining_queue else None
                context = _set_intent_queue(context, remaining_queue or None)
                context = _set_expected_reply_type(context, expected_next)
                _set_conversation_context(conversation, context)
                followup = _format_intent_queue_prompt(remaining_queue)
                bot_response = "\n\n".join(replies)
                if followup:
                    bot_response = f"{bot_response}\n\n{followup}"
                _reset_low_confidence_retry(conversation)
                trace_payload = {
                    "stage": "intent_queue",
                    "decision": "defer_booking",
                    "state": conversation.state,
                    "combined_intents": combined_intents,
                    "info_intents": answered_intents,
                    "intent_queue": remaining_queue,
                    "expected_reply_type": expected_next,
                }
                trace_payload.update(info_meta)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent="multi_intent_info",
                    source="intent_queue",
                    fast_intent=False,
                )
                if saved_message:
                    updates = {
                        "combined_intents": combined_intents,
                        "info_intents_answered": answered_intents,
                        "intent_queue_reason": "defer_booking",
                        "booking_deferred": True,
                    }
                    if remaining_queue:
                        updates["intent_queue"] = remaining_queue
                        updates["expected_reply_type"] = expected_next
                    if info_meta:
                        updates.update(info_meta)
                    _update_message_decision_metadata(saved_message, updates)
                _maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=answered_intents,
                    info_meta=info_meta,
                    message_count=message_count,
                    reason="intent_queue",
                )
                if service_meta:
                    _maybe_store_service_carryover(
                        conversation=conversation,
                        service_meta=service_meta,
                        intent="multi_intent_info",
                        message_count=message_count,
                        reason="intent_queue",
                    )
                if consult_return_pending:
                    bot_response = _apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "intent_queue_defer",
                    )
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Intent queue info reply sent" if sent else "Intent queue info reply failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

    if pending_intent_queue is not None:
        context = _get_conversation_context(conversation)
        context = _set_intent_queue(context, pending_intent_queue)
        context = _set_expected_reply_type(context, pending_expected_reply_type)
        _set_conversation_context(conversation, context)
        intent_queue_intents = pending_intent_queue
        if pending_intent_queue:
            intent_queue_followup = _format_intent_queue_prompt(pending_intent_queue)
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "intent_queue": pending_intent_queue,
                    "expected_reply_type": pending_expected_reply_type,
                },
            )
    elif intent_decomp_used and len(intent_decomp_intents) >= 3 and expected_reply_type != EXPECTED_REPLY_INTENT_CHOICE:
        queue = [intent for intent in intent_decomp_intents if intent != intent_decomp_primary]
        if queue:
            context = _get_conversation_context(conversation)
            context = _set_intent_queue(context, queue)
            context = _set_expected_reply_type(context, EXPECTED_REPLY_INTENT_CHOICE)
            _set_conversation_context(conversation, context)
            intent_queue_intents = queue
            intent_queue_followup = _format_intent_queue_prompt(queue)
            _record_decision_trace(
                conversation,
                {
                    "stage": "intent_queue",
                    "decision": "set",
                    "primary_intent": intent_decomp_primary,
                    "intent_queue": queue,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "intent_queue": queue,
                        "expected_reply_type": EXPECTED_REPLY_INTENT_CHOICE,
                    },
                )

    consult_decision = None
    consult_meta: dict[str, Any] = {}
    consult_signal = False
    consult_flow_decision = None
    consult_short_circuit = False
    consult_short_circuit_reason = None
    consult_short_circuit_service = None
    if routing["allow_bot_reply"] and not bypass_domain_flows and message_text:
        consult_blocked = bool(booking_wants_flow or booking_active or booking_signal)
        if consult_intent:
            consult_blocked = False
        elif intent_decomp_set & {"booking", "pricing", "duration", "location", "hours"}:
            consult_blocked = True
        consult_candidate = None
        if not consult_blocked:
            consult_candidate = build_consult_reply(
                message_text,
                client_slug=payload.client_slug,
                intent_decomp=intent_decomp_payload,
                conversation_id=str(conversation.id),
            )
        if consult_candidate and not consult_intent and isinstance(intent_decomp_payload, dict):
            consult_intent = True
            intent_decomp_payload = dict(intent_decomp_payload)
            intent_decomp_payload["consult_intent"] = True
            candidate_meta = consult_candidate.meta if isinstance(consult_candidate.meta, dict) else {}
            candidate_topic = candidate_meta.get("consult_topic")
            candidate_question = candidate_meta.get("consult_question")
            if candidate_topic and not consult_topic:
                consult_topic = candidate_topic
                intent_decomp_payload["consult_topic"] = candidate_topic
            if candidate_question and not consult_question:
                consult_question = candidate_question
                intent_decomp_payload["consult_question"] = candidate_question
        consult_intent_signal = bool(consult_intent or consult_candidate)
        normalized_message = normalize_for_matching(message_text) if message_text else ""
        explicit_info_signal = bool(
            booking_signal
            or _has_price_signal(normalized_message, message_text)
            or _has_duration_signal(normalized_message, message_text)
            or (_looks_like_info_query(message_text) and not consult_intent_signal)
        )
        explicit_info_intent = bool(
            explicit_info_signal
            or (
                intent_decomp_set & {"booking", "pricing", "duration", "location", "hours"}
                and not consult_intent_signal
            )
            or (info_class_intents & {"location", "hours"} and not consult_intent_signal)
        )
        consult_candidate_meta = (
            consult_candidate.meta
            if consult_candidate and isinstance(consult_candidate.meta, dict)
            else None
        )
        if consult_intent_signal:
            consult_short_circuit_service = intent_decomp_service_query
            if not consult_short_circuit_service and payload.client_slug == "demo_salon":
                consult_short_circuit_service = get_demo_salon_service_hint(message_text)
                if consult_short_circuit_service:
                    consult_short_circuit_reason = "service_hint"
            if consult_short_circuit_service and explicit_info_intent:
                consult_short_circuit = True
                if not consult_short_circuit_reason:
                    consult_short_circuit_reason = "explicit_info"
                consult_flow_trace = {
                    "stage": "consult_flow",
                    "decision": "short_circuit",
                    "state": conversation.state,
                    "reason": consult_short_circuit_reason,
                }
                consult_flow_trace["explicit_info"] = True
                consult_flow_trace["service_query"] = consult_short_circuit_service
                if consult_topic:
                    consult_flow_trace["consult_topic"] = consult_topic
                if consult_question:
                    consult_flow_trace["consult_question"] = consult_question
                if consult_candidate_meta:
                    consult_playbook_id = consult_candidate_meta.get("consult_playbook_id")
                    if consult_playbook_id:
                        consult_flow_trace["consult_playbook_id"] = consult_playbook_id
                    consult_variant_id = consult_candidate_meta.get("consult_variant_id")
                    if consult_variant_id:
                        consult_flow_trace["consult_variant_id"] = consult_variant_id
                _record_decision_trace(conversation, consult_flow_trace)
        consult_decision = None if consult_short_circuit else consult_candidate
        if consult_decision:
            consult_meta = consult_decision.meta if isinstance(consult_decision.meta, dict) else {}
            consult_meta = dict(consult_meta)
            consult_signal = True
        if consult_intent and not consult_short_circuit:
            consult_signal = True
            consult_meta["consult_intent"] = True
            if consult_topic:
                consult_meta["consult_topic"] = consult_topic
            if consult_question:
                consult_meta["consult_question"] = consult_question
    if consult_signal:
        context = _get_conversation_context(conversation)
        context_manager = _get_context_manager(context)
        if consult_decision:
            consult_flow_decision = (
                "consult_escalate" if consult_decision.action == "escalate" else "consult_reply"
            )
        elif _should_escalate_for_clarify(context_manager, "consult"):
            clarify_count, _ = _get_clarify_attempt_state(context_manager, "consult")
            _record_context_manager_decision(
                conversation,
                saved_message,
                decision="clarify_limit",
                updates={
                    "clarify_attempt": {"intent": "consult", "count": clarify_count},
                    "clarify_reason": "consult_no_service",
                    "clarify_limit": True,
                },
            )
            consult_meta["clarify_limit"] = True
            consult_meta["clarify_reason"] = "consult_no_service"
            consult_meta["clarify_attempt"] = {"intent": "consult", "count": clarify_count}
            consult_decision = DemoSalonDecision(
                action="escalate",
                response=MSG_ESCALATED,
                intent="consult_no_service",
                meta=consult_meta,
            )
            consult_flow_decision = "consult_escalate"
        else:
            clarify_count = _register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent="consult",
                now=now,
                reason="consult",
            )
            context = _get_conversation_context(conversation)
            context = _set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=EXPECTED_REPLY_SERVICE,
                reason="consult_clarify",
                now=now,
            )
            consult_meta["consult_questions"] = [MSG_EXPECTED_SERVICE_OFF_TOPIC]
            consult_meta["clarify_attempt"] = {"intent": "consult", "count": clarify_count}
            consult_meta["clarify_reason"] = "consult"
            consult_meta["expected_reply_type"] = EXPECTED_REPLY_SERVICE
            consult_decision = DemoSalonDecision(
                action="reply",
                response=MSG_EXPECTED_SERVICE_OFF_TOPIC,
                intent="consult_reply",
                meta=consult_meta,
            )
            consult_flow_decision = "consult_clarify"

    if consult_decision:
        if consult_flow_decision:
            consult_flow_trace = {
                "stage": "consult_flow",
                "decision": consult_flow_decision,
                "state": conversation.state,
            }
            if consult_flow_decision == "consult_clarify":
                consult_flow_trace["expected_reply_type"] = EXPECTED_REPLY_SERVICE
                consult_flow_trace["reason"] = "consult_clarify"
            elif consult_flow_decision == "consult_escalate":
                consult_flow_trace["reason"] = "consult_no_service"
            else:
                consult_flow_trace["reason"] = "consult_pack"
            consult_playbook_id = consult_meta.get("consult_playbook_id")
            if consult_playbook_id:
                consult_flow_trace["consult_playbook_id"] = consult_playbook_id
            consult_variant_id = consult_meta.get("consult_variant_id")
            if consult_variant_id:
                consult_flow_trace["consult_variant_id"] = consult_variant_id
            _record_decision_trace(conversation, consult_flow_trace)
        if consult_decision.action == "reply":
            context = _get_conversation_context(conversation)
            context_manager = _get_context_manager(context)
            context_manager["current_goal"] = "consult"
            context_manager = _set_consult_context(
                context_manager,
                consult_meta=consult_meta,
                message_count=message_count,
            )
            context = _set_context_manager(context, context_manager)
            _set_conversation_context(conversation, context)
            context, memory = _update_session_memory_goal(
                context, active_goal="consult", now=now
            )
            _set_conversation_context(conversation, context)
            _record_session_memory_update(
                conversation,
                saved_message,
                memory=memory,
                reason="active_goal",
            )
            consult_trace = {
                "stage": "consult_context",
                "decision": "set",
                "current_goal": "consult",
                "ttl": CONSULT_CONTEXT_TTL_MESSAGES,
            }
            consult_topic = consult_meta.get("consult_topic")
            if consult_topic:
                consult_trace["consult_topic"] = consult_topic
            _record_decision_trace(conversation, consult_trace)
            if saved_message:
                _update_message_decision_metadata(saved_message, {"current_goal": "consult"})
        consult_trace = {
            "stage": "consult",
            "decision": consult_decision.action,
            "intent": consult_decision.intent,
            "state": conversation.state,
        }
        consult_trace.update(consult_meta)
        _record_decision_trace(conversation, consult_trace)
        _record_message_decision_meta(
            saved_message,
            action=consult_decision.action,
            intent=consult_decision.intent,
            source="consult",
            fast_intent=False,
        )
        if saved_message and consult_meta:
            _update_message_decision_metadata(saved_message, consult_meta)

        if consult_decision.action == "escalate":
            bot_response = consult_decision.response or MSG_ESCALATED
            _reset_low_confidence_retry(conversation)

            result_message = "Consult escalation"
            _, reused, telegram_sent = _reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="consult",
                intent=consult_decision.intent,
            )
            if reused:
                result_message = f"Consult reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == ConversationState.BOT_ACTIVE.value and routing["allow_handover_create"]:
                _record_escalation_metric("intent")
                result = escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=consult_decision.intent or "consult",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Consult escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Consult escalation failed: {result.error}"
            else:
                result_message = "Consult escalation skipped (already pending)"

            bot_response, sent = _send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        bot_response = consult_decision.response
        bot_response = _combine_sidecar(bot_response, intent_queue_followup)
        _reset_low_confidence_retry(conversation)
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Consult reply sent" if sent else "Consult reply send failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    multi_intent_primary = None
    multi_intent_secondary: list[str] = []
    multi_intent_followup = None
    if intent_queue_followup:
        if isinstance(intent_decomp_primary, str):
            multi_intent_primary = intent_decomp_primary
        if intent_queue_intents:
            multi_intent_secondary = list(intent_queue_intents)
        multi_intent_followup = intent_queue_followup
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "multi_intent": True,
                    "primary_intent": multi_intent_primary,
                    "secondary_count": len(multi_intent_secondary),
                    "intent_queue": intent_queue_intents,
                },
            )
    elif (
        routing["allow_bot_reply"]
        and not bypass_domain_flows
        and message_text
        and len(message_text) >= MULTI_INTENT_MIN_CHARS
        and not booking_active
    ):
        multi_intent_payload = intent_decomp_payload
        if not multi_intent_payload:
            multi_intent_payload = detect_multi_intent(message_text, client_slug=payload.client_slug)
        if isinstance(multi_intent_payload, dict) and multi_intent_payload.get("multi_intent") is True:
            primary = multi_intent_payload.get("primary_intent")
            secondary = multi_intent_payload.get("secondary_intents") or []
            if isinstance(primary, str):
                multi_intent_primary = primary
            if isinstance(secondary, list):
                multi_intent_secondary = [item for item in secondary if isinstance(item, str)]
            if multi_intent_primary:
                multi_intent_followup = _format_multi_intent_followup(
                    multi_intent_primary, multi_intent_secondary
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "multi_intent": True,
                            "primary_intent": multi_intent_primary,
                            "secondary_count": len(multi_intent_secondary),
                        },
                    )
                if booking_blocked:
                    booking_signal = False
                    booking_wants_flow = False

    multi_intent_booking_followup = None
    multi_intent_other_followup = None
    if multi_intent_followup:
        if multi_intent_primary == "booking":
            multi_intent_booking_followup = multi_intent_followup
        else:
            multi_intent_other_followup = multi_intent_followup

    booking_interrupt_text = batch_non_booking_message or message_text
    booking_time_service_candidate = (
        expected_reply_type == EXPECTED_REPLY_TIME
        and expected_reply_matched is False
        and message_text
    )
    if (
        routing["allow_booking_flow"]
        and not bypass_domain_flows
        and booking_wants_flow
        and not consult_intent
        and (
            intent_decomp_used
            or booking_time_service_candidate
            or batch_non_booking_message
            or expected_reply_shortcircuit
        )
    ):
        booking_info_intents = (
            sorted(intent_decomp_set & INFO_INTENTS) if intent_decomp_used else []
        )
        if expected_reply_shortcircuit and booking_interrupt_text:
            anchor_intents, _ = _detect_info_class_intents(
                booking_interrupt_text,
                intent_decomp_set=set(),
            )
            booking_info_intents = sorted(anchor_intents)
        if (
            not booking_info_intents
            and booking_time_service_candidate
            and info_class_intents
        ):
            booking_info_intents = sorted(info_class_intents)
        allow_booking_interrupt_info = bool(
            booking_info_intents
            or booking_time_service_candidate
            or (batch_non_booking_message and not expected_reply_shortcircuit)
        )
        if allow_booking_interrupt_info and policy_handler and routing["allow_truth_gate_reply"]:
            info_decision = None
            info_source = None
            if booking_info_intents:
                if "hours" in booking_info_intents and {"pricing", "duration"} & set(booking_info_intents):
                    multi_result = compose_multi_truth_reply(
                        booking_interrupt_text,
                        payload.client_slug,
                        intent_decomp=intent_decomp_payload,
                        return_meta=True,
                    )
                    if multi_result:
                        multi_reply, multi_meta = multi_result
                        info_decision = DemoSalonDecision(
                            action="reply",
                            response=multi_reply,
                            intent="multi_truth",
                            meta=multi_meta if isinstance(multi_meta, dict) else None,
                        )
                        info_source = "multi_truth"
                if not info_decision:
                    service_matcher = policy_handler.get("service_matcher")
                    if service_matcher:
                        info_decision = service_matcher(
                            booking_interrupt_text,
                            client_slug=payload.client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if info_decision:
                            info_source = "service_matcher"
                if not info_decision:
                    truth_gate = policy_handler.get("truth_gate")
                    if truth_gate:
                        if policy_type == "demo_salon":
                            info_decision = truth_gate(
                                booking_interrupt_text,
                                client_slug=payload.client_slug,
                                intent_decomp=intent_decomp_payload,
                            )
                        else:
                            info_decision = truth_gate(booking_interrupt_text)
                        if info_decision:
                            info_source = "truth_gate"
            if not info_decision and batch_non_booking_message and not booking_info_intents:
                service_matcher = policy_handler.get("service_matcher")
                if service_matcher:
                    info_decision = service_matcher(
                        booking_interrupt_text,
                        client_slug=payload.client_slug,
                        intent_decomp=intent_decomp_payload,
                    )
                    if info_decision:
                        info_source = "service_matcher"
                if not info_decision:
                    truth_gate = policy_handler.get("truth_gate")
                    if truth_gate:
                        if policy_type == "demo_salon":
                            info_decision = truth_gate(
                                booking_interrupt_text,
                                client_slug=payload.client_slug,
                                intent_decomp=intent_decomp_payload,
                            )
                        else:
                            info_decision = truth_gate(booking_interrupt_text)
                        if info_decision:
                            info_source = "truth_gate"
            if not info_decision and booking_time_service_candidate:
                service_matcher = policy_handler.get("service_matcher")
                if service_matcher:
                    candidate = service_matcher(
                        booking_interrupt_text,
                        client_slug=payload.client_slug,
                        intent_decomp=intent_decomp_payload,
                    )
                    if _is_booking_time_service_decision(candidate):
                        info_decision = candidate
                        info_source = "service_matcher"
                if not info_decision:
                    truth_gate = policy_handler.get("truth_gate")
                    if truth_gate:
                        if policy_type == "demo_salon":
                            candidate = truth_gate(
                                booking_interrupt_text,
                                client_slug=payload.client_slug,
                                intent_decomp=intent_decomp_payload,
                            )
                        else:
                            candidate = truth_gate(booking_interrupt_text)
                        if _is_booking_time_service_decision(candidate):
                            info_decision = candidate
                            info_source = "truth_gate"

            if info_decision and info_decision.action == "reply":
                info_meta = info_decision.meta if isinstance(info_decision.meta, dict) else {}
                info_meta = dict(info_meta)
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=info_meta,
                    intent=info_decision.intent,
                    source=info_source or "booking_interrupt",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                booking_time_service_interrupt = bool(
                    booking_time_service_candidate and _is_booking_time_service_decision(info_decision)
                )
                booking_interrupt_info = bool(
                    info_decision
                    and info_decision.action == "reply"
                    and not booking_time_service_interrupt
                )

                context = booking_context if isinstance(booking_context, dict) else _get_conversation_context(conversation)
                booking_state = booking if isinstance(booking, dict) else _get_booking_context(context)
                booking_active = bool(booking_state.get("active"))
                if not booking_active:
                    booking_state = dict(booking_state)
                    booking_state["active"] = True
                    booking_state["started_at"] = now.isoformat()
                booking_state = _update_booking_from_messages(
                    booking_state,
                    booking_messages,
                    client_slug=payload.client_slug,
                )
                if booking_time_service_interrupt:
                    service_query = info_meta.get("service_query")
                    if isinstance(service_query, str) and service_query.strip():
                        booking_state["service"] = service_query.strip()
                if not booking_state.get("service"):
                    service_hint = _get_recent_service_hint(context, now)
                    if service_hint:
                        booking_state["service"] = service_hint
                        context = _clear_service_hint(context)
                context_manager = _get_context_manager(context)
                refusal_flags = context_manager.get("refusal_flags")
                booking_state, prompt = _next_booking_prompt(booking_state, refusal_flags=refusal_flags)
                context = _set_booking_context(context, booking_state)
                _set_conversation_context(conversation, context)
                booking_expected = _expected_reply_for_booking_question(booking_state.get("last_question"))
                booking_prompt_repeat = bool(
                    booking_expected
                    and expected_reply_type == booking_expected
                    and expected_reply_matched is False
                )
                if prompt and booking_expected:
                    context = _set_expected_reply_context(
                        conversation=conversation,
                        saved_message=saved_message,
                        context=context,
                        expected_reply_type=booking_expected,
                        reason="booking_prompt",
                        now=now,
                    )

                if (
                    info_decision.intent in {"service_clarify", "duration_or_price_clarify"}
                    and not booking_time_service_interrupt
                ):
                    if booking_interrupt_info:
                        prompt = None
                    else:
                        clarify_intent = current_goal or "info"
                        context_manager = _get_context_manager(context)
                        if _should_escalate_for_clarify(context_manager, clarify_intent):
                            clarify_count, _ = _get_clarify_attempt_state(context_manager, clarify_intent)
                            _record_context_manager_decision(
                                conversation,
                                saved_message,
                                decision="clarify_limit",
                                updates={
                                    "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                                    "clarify_reason": "service_clarify",
                                    "clarify_limit": True,
                                },
                            )
                            return _handle_clarify_limit_escalation(
                                db=db,
                                conversation=conversation,
                                user=user,
                                message_text=message_text,
                                saved_message=saved_message,
                                source=info_source or "booking_interrupt",
                                allow_handover=routing.get("allow_handover_create", False),
                                send_response=_send_response,
                                finalize_response=_finalize_bot_response,
                            )
                        _register_clarify_attempt(
                            conversation=conversation,
                            saved_message=saved_message,
                            intent=clarify_intent,
                            now=now,
                            reason="service_clarify",
                        )
                        context = _set_expected_reply_context(
                            conversation=conversation,
                            saved_message=saved_message,
                            context=context,
                            expected_reply_type=EXPECTED_REPLY_SERVICE,
                            reason="service_clarify",
                            now=now,
                        )
                        prompt = None

                if prompt and not booking_time_service_interrupt and not booking_interrupt_info and booking_prompt_repeat:
                    context_manager = _get_context_manager(context)
                    clarify_guard_reason = _booking_clarify_guard_reason(
                        booking_interrupt_info=booking_interrupt_info,
                        basic_info_message=basic_info_message,
                        session_memory_reset_reason=session_memory_reset_reason,
                        memory_expected_reply_type=memory_expected_reply_type,
                    )
                    if clarify_guard_reason:
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "clarify_guard": True,
                                    "clarify_guard_reason": clarify_guard_reason,
                                },
                            )
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "clarify_guard",
                                "decision": "skip",
                                "intent": "booking",
                                "reason": clarify_guard_reason,
                            },
                        )
                    elif _should_escalate_for_clarify(context_manager, "booking"):
                        clarify_count, _ = _get_clarify_attempt_state(context_manager, "booking")
                        _record_context_manager_decision(
                            conversation,
                            saved_message,
                            decision="clarify_limit",
                            updates={
                                "clarify_attempt": {"intent": "booking", "count": clarify_count},
                                "clarify_reason": "booking_prompt",
                                "clarify_limit": True,
                            },
                        )
                        return _handle_clarify_limit_escalation(
                            db=db,
                            conversation=conversation,
                            user=user,
                            message_text=message_text,
                            saved_message=saved_message,
                            source="booking",
                            allow_handover=routing.get("allow_handover_create", False),
                            send_response=_send_response,
                            finalize_response=_finalize_bot_response,
                        )
                    elif clarify_guard_reason is None:
                        _register_clarify_attempt(
                            conversation=conversation,
                            saved_message=saved_message,
                            intent="booking",
                            now=now,
                            reason="booking_prompt",
                        )

                trace_payload = {
                    "stage": "booking_interrupt",
                    "decision": "info_reply",
                    "state": conversation.state,
                    "info_intents": booking_info_intents,
                    "booking_prompt": prompt,
                }
                if booking_interrupt_info:
                    trace_payload["booking_interrupt_info"] = True
                _record_decision_trace(conversation, trace_payload)

                if info_source == "service_matcher":
                    matcher_trace = {
                        "stage": "service_matcher",
                        "decision": info_decision.intent,
                        "state": conversation.state,
                    }
                    matcher_trace.update(info_meta)
                    _record_decision_trace(conversation, matcher_trace)
                elif info_source == "truth_gate":
                    gate_trace = {
                        "stage": "truth_gate",
                        "decision": info_decision.action,
                        "intent": info_decision.intent,
                        "state": conversation.state,
                        "booking_wants_flow": booking_wants_flow,
                        "policy_type": policy_type,
                    }
                    gate_trace.update(info_meta)
                    _record_decision_trace(conversation, gate_trace)
                elif info_source == "multi_truth":
                    multi_trace = {
                        "stage": "multi_truth",
                        "decision": "reply",
                        "intent": "multi_truth",
                        "state": conversation.state,
                        "intents": booking_info_intents,
                    }
                    multi_trace.update(info_meta)
                    _record_decision_trace(conversation, multi_trace)

                _record_message_decision_meta(
                    saved_message,
                    action=info_decision.action,
                    intent=info_decision.intent,
                    source=info_source or "booking_interrupt",
                    fast_intent=False,
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            **info_meta,
                            "booking_info_interrupt": True,
                            "booking_info_intents": booking_info_intents,
                            "booking_interrupt_info": bool(booking_interrupt_info),
                        },
                    )
                _maybe_store_service_carryover(
                    conversation=conversation,
                    service_meta=info_meta,
                    intent=info_decision.intent,
                    message_count=message_count,
                    reason="booking_interrupt",
                )
                _maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=booking_info_intents,
                    info_meta=info_meta,
                    message_count=message_count,
                    reason="booking_interrupt",
                )

                bot_response = _combine_sidecar(prompt or "", info_decision.response or "")
                bot_response = bot_response.strip()
                if consult_return_pending:
                    bot_response = _apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "booking_interrupt",
                    )
                _reset_low_confidence_retry(conversation)
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Booking info interrupt sent" if sent else "Booking info interrupt failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

    policy_price_sidecar = None
    if not bypass_domain_flows and policy_handler and routing["allow_truth_gate_reply"] and booking_wants_flow:
        price_sidecar = policy_handler.get("price_sidecar")
        if price_sidecar:
            policy_price_sidecar, price_item = price_sidecar(booking_messages)
            if price_item:
                booking_context = (
                    booking_context if isinstance(booking_context, dict) else _get_conversation_context(conversation)
                )
                booking_context = _set_service_hint(booking_context, price_item, now)
                _set_conversation_context(conversation, booking_context)

    # 9.05 Booking flow: collect slots before intent/LLM.
    booking_t0 = None
    booking_logged = False
    if routing["allow_booking_flow"] and not bypass_domain_flows:
        booking_t0 = time.monotonic()
        context = booking_context if isinstance(booking_context, dict) else _get_conversation_context(conversation)
        booking_state = booking if isinstance(booking, dict) else _get_booking_context(context)
        booking_active = bool(booking_state.get("active"))

        if booking_active and _is_booking_cancel(message_text, policy_pack=policy_pack):
            booking_state = {"active": False}
            context = _set_booking_context(context, booking_state)
            _set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "cancelled",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="booking_cancelled",
                intent="booking",
                source="booking",
                fast_intent=False,
            )
            bot_response = _combine_sidecar(MSG_BOOKING_CANCELLED, multi_intent_booking_followup)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Booking cancelled" if sent else "Booking cancel response failed"
            _log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            db.commit()
            return WebhookResponse(
                success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
            )

        booking_related = any(
            _is_booking_related_message(msg, payload.client_slug) for msg in booking_messages
        )
        if booking_active and not booking_signal and not booking_related:
            booking_state = {"active": False}
            context = _set_booking_context(context, booking_state)
            _set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "paused",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="booking_paused",
                intent="booking",
                source="booking",
                fast_intent=False,
            )
            bot_response = _combine_sidecar(MSG_BOOKING_REENGAGE, multi_intent_booking_followup)
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Booking paused" if sent else "Booking pause response failed"
            _log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            db.commit()
            return WebhookResponse(
                success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
            )

        if booking_active or booking_signal:
            if not booking_active:
                booking_state = dict(booking_state)
                booking_state["active"] = True
                booking_state["started_at"] = now.isoformat()

            booking_state = _update_booking_from_messages(
                booking_state,
                booking_messages,
                client_slug=payload.client_slug,
            )
            context_manager = _get_context_manager(context)
            if not booking_state.get("service"):
                service_hint = _get_recent_service_hint(context, now)
                if service_hint:
                    booking_state["service"] = service_hint
                    context = _clear_service_hint(context)
                else:
                    carryover = _get_service_carryover(
                        context_manager, message_count=message_count
                    )
                    service_query = (
                        carryover.get("service_query")
                        if isinstance(carryover, dict)
                        else None
                    )
                    if isinstance(service_query, str) and service_query.strip():
                        booking_state["service"] = service_query.strip()
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "service_carryover",
                                "decision": "used",
                                "service_query": service_query.strip(),
                                "service_query_source": carryover.get("service_query_source")
                                if isinstance(carryover, dict)
                                else None,
                                "service_query_score": carryover.get("service_query_score")
                                if isinstance(carryover, dict)
                                else None,
                                "reason": "booking_flow",
                            },
                        )
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "service_query": service_query.strip(),
                                    "service_query_source": "context",
                                    "service_query_score": carryover.get("service_query_score")
                                    if isinstance(carryover, dict)
                                    else None,
                                },
                            )
            refusal_flags = context_manager.get("refusal_flags")
            booking_state, prompt = _next_booking_prompt(booking_state, refusal_flags=refusal_flags)
            context = _set_booking_context(context, booking_state)
            _set_conversation_context(conversation, context)
            booking_expected = _expected_reply_for_booking_question(booking_state.get("last_question"))
            booking_prompt_repeat = bool(
                booking_expected
                and expected_reply_type == booking_expected
                and expected_reply_matched is False
            )
            if prompt and booking_expected:
                context = _set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    expected_reply_type=booking_expected,
                    reason="booking_prompt",
                    now=now,
                )

            if prompt:
                context_manager = _get_context_manager(context)
                if booking_prompt_repeat:
                    clarify_guard_reason = _booking_clarify_guard_reason(
                        booking_interrupt_info=False,
                        basic_info_message=basic_info_message,
                        session_memory_reset_reason=session_memory_reset_reason,
                        memory_expected_reply_type=memory_expected_reply_type,
                    )
                    if clarify_guard_reason:
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "clarify_guard": True,
                                    "clarify_guard_reason": clarify_guard_reason,
                                },
                            )
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "clarify_guard",
                                "decision": "skip",
                                "intent": "booking",
                                "reason": clarify_guard_reason,
                            },
                        )
                    elif _should_escalate_for_clarify(context_manager, "booking"):
                        clarify_count, _ = _get_clarify_attempt_state(context_manager, "booking")
                        _record_context_manager_decision(
                            conversation,
                            saved_message,
                            decision="clarify_limit",
                            updates={
                                "clarify_attempt": {"intent": "booking", "count": clarify_count},
                                "clarify_reason": "booking_prompt",
                                "clarify_limit": True,
                            },
                        )
                        return _handle_clarify_limit_escalation(
                            db=db,
                            conversation=conversation,
                            user=user,
                            message_text=message_text,
                            saved_message=saved_message,
                            source="booking",
                            allow_handover=routing.get("allow_handover_create", False),
                            send_response=_send_response,
                            finalize_response=_finalize_bot_response,
                        )
                    elif clarify_guard_reason is None:
                            _register_clarify_attempt(
                                conversation=conversation,
                                saved_message=saved_message,
                                intent="booking",
                                now=now,
                                reason="booking_prompt",
                            )
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "booking",
                        "decision": "prompt",
                        "state": conversation.state,
                        "missing_slot": booking_state.get("last_question"),
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="booking_prompt",
                    intent="booking",
                    source="booking",
                    fast_intent=False,
                )
                bot_response = _combine_sidecar(prompt, policy_price_sidecar)
                bot_response = _combine_sidecar(bot_response, multi_intent_booking_followup)
                if consult_return_pending:
                    bot_response = _apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "booking_prompt",
                    )
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Booking slot requested" if sent else "Booking slot response failed"
                _log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
                booking_logged = True
                db.commit()
                return WebhookResponse(
                    success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
                )

            context_manager = _get_context_manager(context)
            refusal_flags = context_manager.get("refusal_flags")
            booking_summary = _build_booking_summary(booking_state, refusal_flags=refusal_flags)
            if routing["allow_handover_create"]:
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=booking_summary,
                    source="booking",
                    intent="booking",
                )
                if reused:
                    bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                    result_message = f"Booking reuse, telegram={'sent' if telegram_sent else 'failed'}"
                    trace_decision = "reuse_handover"
                else:
                    _record_escalation_metric("intent")
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=booking_summary,
                        trigger_type="intent",
                        trigger_value="booking",
                    )

                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=booking_summary,
                        )
                        bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                        result_message = f"Booking escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        trace_decision = "escalated"
                    else:
                        if result.error_code == "no_telegram":
                            bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                            result_message = "Booking captured without telegram"
                            trace_decision = "captured_pending"
                        else:
                            bot_response = MSG_AI_ERROR
                            result_message = f"Booking escalation failed: {result.error}"
                            trace_decision = "escalation_failed"
            else:
                bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                result_message = "Booking captured while pending"
                trace_decision = "captured_pending"

            bot_response = _combine_sidecar(bot_response, multi_intent_booking_followup)
            context = _set_booking_context(context, {"active": False})
            _set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": trace_decision,
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action=f"booking_{trace_decision}",
                intent="booking",
                source="booking",
                fast_intent=False,
            )
            bot_response, sent = _send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            _log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            db.commit()
            return WebhookResponse(
                success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
            )
    if booking_t0 is not None and not booking_logged:
        _log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)

    llm_primary_result = None
    llm_primary_failed = False
    llm_primary_reason = None
    skip_llm_primary = False
    force_truth_gate = False

    # 9.06 Fast intent (smalltalk) before LLM to avoid extra calls.
    fast_decision = None
    if routing["allow_bot_reply"]:
        fast_decision = _detect_fast_intent(
            message_text,
            policy_type=policy_type,
            booking_wants_flow=booking_wants_flow,
            bypass_domain_flows=bypass_domain_flows,
        )

    if fast_decision:
        bot_response = fast_decision.response
        _reset_low_confidence_retry(conversation)

        result_message = "Fast intent reply sent"
        if fast_decision.action == "smalltalk":
            result_message = "Fast intent smalltalk sent"

        _record_decision_trace(
            conversation,
            {
                "stage": "fast_intent",
                "decision": fast_decision.action,
                "intent": fast_decision.intent,
                "state": conversation.state,
                "booking_wants_flow": booking_wants_flow,
                "policy_type": policy_type,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action=fast_decision.action,
            intent=fast_decision.intent,
            source="fast_intent",
            fast_intent=True,
        )
        bot_response, sent = _send_and_save(bot_response)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if (
        routing["allow_bot_reply"]
        and not booking_wants_flow
        and not bypass_domain_flows
        and policy_handler
    ):
        if intent_decomp_used and message_text:
            intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
            if "booking" not in intent_set and "hours" in intent_set and "pricing" in intent_set:
                multi_result = compose_multi_truth_reply(
                    message_text,
                    payload.client_slug,
                    intent_decomp=intent_decomp_payload,
                    return_meta=True,
                )
                if multi_result:
                    multi_reply, multi_meta = multi_result
                    guard_response = _maybe_apply_fact_guard(
                        decision_meta=multi_meta if isinstance(multi_meta, dict) else None,
                        intent="multi_truth",
                        source="multi_truth",
                        allow_handover=routing.get("allow_handover_create", False),
                    )
                    if guard_response:
                        db.commit()
                        return guard_response
                    bot_response = multi_reply
                    bot_response = _maybe_append_booking_cta(
                        bot_response,
                        conversation_state=conversation.state,
                        allow_booking_flow=routing["allow_booking_flow"],
                    )
                    _reset_low_confidence_retry(conversation)

                    result_message = "Multi-truth reply sent"
                    trace_payload = {
                        "stage": "multi_truth",
                        "decision": "reply",
                        "intent": "multi_truth",
                        "state": conversation.state,
                        "intents": sorted(intent_set),
                    }
                    if isinstance(multi_meta, dict):
                        trace_payload.update(multi_meta)
                    _record_decision_trace(conversation, trace_payload)
                    _record_message_decision_meta(
                        saved_message,
                        action="reply",
                        intent="multi_truth",
                        source="multi_truth",
                        fast_intent=False,
                    )
                    if saved_message and isinstance(multi_meta, dict):
                        _update_message_decision_metadata(saved_message, multi_meta)
                    _maybe_store_class_carryover(
                        conversation=conversation,
                        class_name="info_bundle",
                        intents=["multi_truth"],
                        info_meta=multi_meta if isinstance(multi_meta, dict) else None,
                        message_count=message_count,
                        reason="multi_truth",
                    )
                    _maybe_store_service_carryover(
                        conversation=conversation,
                        service_meta=multi_meta if isinstance(multi_meta, dict) else None,
                        intent="multi_truth",
                        message_count=message_count,
                        reason="multi_truth",
                    )
                    bot_response, sent = _send_and_save(bot_response)
                    if not sent:
                        result_message = f"{result_message}; response_send=failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

        class_router_result = _resolve_class_router_result(
            info_intents=info_class_intents,
            info_meta=info_class_meta,
            booking_signal=booking_signal,
            class_carryover=class_carryover,
            domain_intent=DomainIntent.UNKNOWN,
            domain_meta=None,
            router_state=router_state,
        )
        info_class = "info_bundle" in (class_router_result.get("classes") or [])
        guest_policy_class = "guest_policy" in (class_router_result.get("classes") or [])
        base_info_intents: set[str] = set(class_router_result.get("intents") or [])
        info_class_intents_for_reply: set[str] = set(base_info_intents)
        for item in class_router_result.get("carryover_intents") or []:
            if isinstance(item, str) and item.strip():
                info_class_intents_for_reply.add(item.strip().casefold())
        skip_info_class_for_service = False
        if (
            info_class
            and message_text
            and payload.client_slug == "demo_salon"
            and not info_class_intents
        ):
            normalized = normalize_for_matching(message_text)
            service_hint = get_demo_salon_service_hint(message_text)
            if service_hint:
                if _contains_any(
                    normalized,
                    [
                        "парков",
                        "гост",
                        "ребен",
                        "ребён",
                        "дет",
                        "коляс",
                        "ожидан",
                        "подруг",
                    ],
                ):
                    service_hint = None
                else:
                    presence_keywords = [
                        "делаете",
                        "делает",
                        "делают",
                        "есть",
                        "есть ли",
                        "оказываете",
                        "предоставляете",
                    ]
                    presence_hint = _contains_any(normalized, presence_keywords) or (
                        "?" in message_text and len(normalized.split()) <= 4
                    )
                    if presence_hint and not (
                        _has_price_signal(normalized, message_text)
                        or _has_duration_signal(normalized, message_text)
                    ):
                        skip_info_class_for_service = True
        router_service_query = None
        alias_service_query = None
        intent_decomp_explicit_query = None
        carryover_has_hours = False
        if info_class and info_class_intents_for_reply and not skip_info_class_for_service:
            carryover_sections = class_router_result.get("carryover_info_sections")
            if isinstance(carryover_sections, list):
                for section in carryover_sections:
                    if isinstance(section, str) and section.strip().casefold() == "hours":
                        carryover_has_hours = True
                        break
            router_state = class_router_result.get("router") if isinstance(class_router_result, dict) else None
            router_output = router_state.get("output") if isinstance(router_state, dict) else None
            if isinstance(router_output, dict):
                slots = router_output.get("slots")
                if isinstance(slots, dict):
                    candidate = slots.get("service_query")
                    if isinstance(candidate, str) and candidate.strip():
                        router_service_query = candidate.strip()
            if message_text and payload.client_slug:
                normalized_for_alias = _normalize_service_text(message_text)
                if normalized_for_alias:
                    alias_match = _match_service(normalized_for_alias)
                    if isinstance(alias_match, dict):
                        alias_name = alias_match.get("name")
                        if isinstance(alias_name, str) and alias_name.strip():
                            alias_service_query = alias_name.strip()
            intent_decomp_source = None
            if isinstance(intent_decomp_payload, dict):
                source = intent_decomp_payload.get("service_query_source")
                if isinstance(source, str):
                    intent_decomp_source = source
            intent_decomp_explicit_query = (
                intent_decomp_service_query if intent_decomp_source != "context" else None
            )
        controller_low_confidence = False
        controller_state = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
        if isinstance(controller_state, dict):
            controller_low_confidence = bool(controller_state.get("low_confidence"))
        explicit_service_signal = bool(
            intent_decomp_explicit_query or router_service_query or alias_service_query
        )
        service_carryover_meta = _get_service_carryover(
            context_manager, message_count=message_count
        )
        carryover_service_query = None
        if isinstance(service_carryover_meta, dict):
            carryover_service_query = service_carryover_meta.get("service_query")
        guest_policy_lock = guest_policy_class
        info_bundle_lock = info_class and not (
            explicit_service_signal or intent_decomp_explicit_query or router_service_query
        )
        info_semantic_lock = guest_policy_lock or info_bundle_lock or controller_low_confidence
        info_semantic_meta: dict[str, Any] = {}
        if info_semantic_lock:
            if guest_policy_lock:
                info_class_intents_for_reply.discard("pricing")
                info_class_intents_for_reply.discard("duration")
            else:
                if "pricing" not in base_info_intents:
                    info_class_intents_for_reply.discard("pricing")
                if "duration" not in base_info_intents:
                    info_class_intents_for_reply.discard("duration")
            if guest_policy_lock:
                skip_reason = "guest_policy_lock"
            elif info_bundle_lock:
                skip_reason = "info_bundle_lock"
            else:
                skip_reason = "controller_low_confidence"
            info_semantic_meta = {
                "info_semantic_match_skipped": True,
                "info_semantic_match_skip_reason": skip_reason,
            }
            if guest_policy_lock:
                info_semantic_meta.update(
                    {
                        "question_type": None,
                        "service_query": None,
                        "service_query_source": None,
                        "service_query_score": 0.0,
                    }
                )
            carryover_service_query = None
        force_hours_followup = (
            carryover_has_hours
            and _looks_like_hours_followup(message_text)
            and not explicit_service_signal
        )
        info_service_query = None
        if not info_semantic_lock:
            if alias_service_query:
                info_service_query = alias_service_query
            elif router_service_query:
                info_service_query = router_service_query
            elif intent_decomp_explicit_query:
                info_service_query = intent_decomp_explicit_query
            if (
                not force_hours_followup
                and not info_service_query
                and {"pricing", "duration"} & info_class_intents_for_reply
                and not info_semantic_lock
            ):
                info_service_query = _extract_service_hint(message_text, payload.client_slug)
            if (
                not force_hours_followup
                and not info_service_query
                and {"pricing", "duration"} & info_class_intents_for_reply
                and not info_semantic_lock
                and allow_service_carryover
            ):
                if carryover_service_query:
                    info_service_query = carryover_service_query
            if force_hours_followup:
                info_class_intents_for_reply.discard("duration")
                info_class_intents_for_reply.add("hours")

            priority = (
                INFO_INTENT_PRIORITY_SERVICE
                if info_service_query
                else INFO_INTENT_PRIORITY_GENERIC
            )
            answer_intents: list[str] = []
            for intent_name in priority:
                if intent_name in info_class_intents_for_reply and intent_name not in answer_intents:
                    answer_intents.append(intent_name)
                if len(answer_intents) >= 2:
                    break
            if not answer_intents:
                answer_intents = list(sorted(info_class_intents_for_reply))[:2]

            info_signals = (
                info_class_meta.get("info_signals")
                if isinstance(info_class_meta, dict)
                else None
            )
            include_parking = (
                bool(info_signals.get("parking")) if isinstance(info_signals, dict) else False
            )
            include_guest = (
                bool(info_signals.get("guest")) if isinstance(info_signals, dict) else False
            )
            include_base_bundle = False
            if isinstance(info_signals, dict):
                include_base_bundle = any(
                    bool(info_signals.get(key))
                    for key in ("parking", "guest", "location", "hours")
                )
            if not include_base_bundle:
                include_base_bundle = bool(
                    {"hours", "location"} & info_class_intents_for_reply
                )
            base_bundle_reply: str | None = None
            base_bundle_meta: dict[str, Any] = {}
            if include_base_bundle:
                base_bundle_reply, base_bundle_meta = build_info_combined_reply(
                    include_parking=include_parking,
                    include_guest=include_guest,
                )

            replies: list[str] = []
            info_meta_combined: dict[str, Any] = {}
            if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                info_meta_combined.update(base_bundle_meta)
            if info_semantic_meta:
                info_meta_combined.update(info_semantic_meta)
            if isinstance(base_bundle_reply, str):
                base_bundle_reply = base_bundle_reply.strip()
                if base_bundle_reply:
                    replies.append(base_bundle_reply)
            extra_intents = [
                intent_name
                for intent_name in answer_intents
                if intent_name not in {"hours", "location"}
            ]
            for intent_name in extra_intents:
                reply, meta = _build_info_intent_reply(
                    intent_name,
                    service_query=info_service_query,
                    client_slug=payload.client_slug,
                    message_text=message_text,
                    include_info_bundle=False,
                )
                if isinstance(reply, str):
                    reply = reply.strip()
                    if reply:
                        replies.append(reply)
                if isinstance(meta, dict) and meta:
                    info_meta_combined.update(meta)
            if force_hours_followup:
                info_meta_combined["question_type"] = "hours"
            if replies:
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=info_meta_combined if info_meta_combined else None,
                    intent="info_bundle",
                    source="class_router",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                bot_response = "\n\n".join(replies)
                bot_response = _maybe_append_booking_cta(
                    bot_response,
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=False,
                )
                bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
                _reset_low_confidence_retry(conversation)
                trace_payload = {
                    "stage": "info_class",
                    "decision": "reply",
                    "state": conversation.state,
                    "intents": answer_intents,
                    "class_router": class_router_result,
                }
                trace_payload.update(info_meta_combined)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent="info_bundle",
                    source="class_router",
                    fast_intent=False,
                )
                if saved_message:
                    meta_updates = {"class_router": class_router_result}
                    if info_meta_combined:
                        meta_updates.update(info_meta_combined)
                    meta_updates.update(_controller_meta_updates_from_class_router(class_router_result))
                    meta_updates.update(_router_observability_updates_from_class_router(class_router_result))
                    _update_message_decision_metadata(saved_message, meta_updates)
                _maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=answer_intents,
                    info_meta=info_meta_combined,
                    message_count=message_count,
                    reason="class_router",
                )
                _maybe_store_service_carryover(
                    conversation=conversation,
                    service_meta=info_meta_combined,
                    intent="info_bundle",
                    message_count=message_count,
                    reason="class_router",
                )
                if consult_return_pending:
                    bot_response = _apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "info_class",
                )
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Info class reply sent" if sent else "Info class reply failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

        if guest_policy_class and routing["allow_bot_reply"]:
            include_parking = bool(info_signals.get("parking")) if isinstance(info_signals, dict) else False
            base_bundle_reply, base_bundle_meta = build_info_combined_reply(
                include_parking=include_parking,
                include_guest=True,
            )
            if base_bundle_meta:
                info_class_intents_for_reply.add("guest_policy")
            if isinstance(base_bundle_reply, str) and base_bundle_reply.strip():
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=base_bundle_meta if isinstance(base_bundle_meta, dict) else None,
                    intent="guest_policy",
                    source="class_router",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                bot_response = base_bundle_reply.strip()
                bot_response = _maybe_append_booking_cta(
                    bot_response,
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=bool(multi_intent_other_followup),
                )
                bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
                _reset_low_confidence_retry(conversation)
                trace_payload = {
                    "stage": "info_class",
                    "decision": "reply",
                    "state": conversation.state,
                    "intents": sorted(info_class_intents_for_reply or {"guest_policy"}),
                    "class_router": class_router_result,
                }
                if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                    trace_payload.update(base_bundle_meta)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent="info_bundle",
                    source="class_router",
                    fast_intent=False,
                )
                if saved_message:
                    meta_updates = {"class_router": class_router_result}
                    if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                        meta_updates.update(base_bundle_meta)
                    meta_updates.update(_controller_meta_updates_from_class_router(class_router_result))
                    meta_updates.update(_router_observability_updates_from_class_router(class_router_result))
                    _update_message_decision_metadata(saved_message, meta_updates)
                _maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=sorted(info_class_intents_for_reply or {"guest_policy"}),
                    info_meta=base_bundle_meta if isinstance(base_bundle_meta, dict) else {},
                    message_count=message_count,
                    reason="guest_policy_lock",
                )
                _maybe_store_service_carryover(
                    conversation=conversation,
                    service_meta=base_bundle_meta if isinstance(base_bundle_meta, dict) else None,
                    intent="info_bundle",
                    message_count=message_count,
                    reason="guest_policy_lock",
                )
                if consult_return_pending:
                    bot_response = _apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "info_class",
                    )
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Guest policy reply sent" if sent else "Guest policy reply failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

        if message_text:
            normalized_message = normalize_for_matching(message_text)
            force_truth_gate = bool(
                info_class_intents & {"pricing", "duration"}
                or _has_price_signal(normalized_message, message_text)
                or _has_duration_signal(normalized_message, message_text)
            )
        service_matcher = policy_handler.get("service_matcher")
        service_decision = None
        if service_matcher and not force_truth_gate:
            service_decision = service_matcher(
                message_text,
                client_slug=payload.client_slug,
                intent_decomp=intent_decomp_payload,
            )
        if service_decision:
            if service_decision.action == "reply":
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=service_decision.meta if isinstance(service_decision.meta, dict) else None,
                    intent=service_decision.intent,
                    source="service_matcher",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
            bot_response = service_decision.response
            bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
            if (
                service_decision.action == "reply"
                and service_decision.intent in BOOKING_CTA_SERVICE_INTENTS
            ):
                bot_response = _maybe_append_booking_cta(
                    bot_response,
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=bool(multi_intent_other_followup),
                )
            if consult_return_pending:
                bot_response = _apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "service_matcher",
                )
            _reset_low_confidence_retry(conversation)

            result_message = "Service matcher reply sent"
            clarify_reason = None
            if service_decision.intent == "service_clarify":
                clarify_intent = current_goal or "info"
                context = _get_conversation_context(conversation)
                context_manager = _get_context_manager(context)
                if _should_escalate_for_clarify(context_manager, clarify_intent):
                    clarify_count, _ = _get_clarify_attempt_state(context_manager, clarify_intent)
                    _record_context_manager_decision(
                        conversation,
                        saved_message,
                        decision="clarify_limit",
                        updates={
                            "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                            "clarify_reason": "service_clarify",
                            "clarify_limit": True,
                        },
                    )
                    return _handle_clarify_limit_escalation(
                        db=db,
                        conversation=conversation,
                        user=user,
                        message_text=message_text,
                        saved_message=saved_message,
                        source="service_matcher",
                        allow_handover=routing.get("allow_handover_create", False),
                        send_response=_send_response,
                        finalize_response=_finalize_bot_response,
                    )
                _register_clarify_attempt(
                    conversation=conversation,
                    saved_message=saved_message,
                    intent=clarify_intent,
                    now=now,
                    reason="service_clarify",
                )
                service_meta = getattr(service_decision, "meta", None)
                service_query = None
                service_source = None
                if isinstance(service_meta, dict):
                    service_query = service_meta.get("service_query")
                    service_source = service_meta.get("service_query_source")
                if not service_query and service_source in (None, "", "none"):
                    clarify_reason = "missing_service_query"
                elif not service_query and intent_decomp_used:
                    decomp_query = (
                        intent_decomp_payload.get("service_query")
                        if isinstance(intent_decomp_payload, dict)
                        else None
                    )
                    if not decomp_query:
                        intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
                        if "pricing" in intent_set or "duration" in intent_set:
                            clarify_reason = "missing_service_query"
                if service_decision.action != "escalate":
                    context = _get_conversation_context(conversation)
                    context = _set_expected_reply_context(
                        conversation=conversation,
                        saved_message=saved_message,
                        context=context,
                        expected_reply_type=EXPECTED_REPLY_SERVICE,
                        reason="service_clarify",
                        now=now,
                    )
            trace_payload = {
                "stage": "service_matcher",
                "decision": service_decision.intent,
                "state": conversation.state,
            }
            if isinstance(getattr(service_decision, "meta", None), dict):
                trace_payload.update(service_decision.meta)
            _record_decision_trace(conversation, trace_payload)
            _record_message_decision_meta(
                saved_message,
                action=service_decision.action,
                intent=service_decision.intent,
                source="service_matcher",
                fast_intent=False,
            )
            if saved_message and isinstance(getattr(service_decision, "meta", None), dict):
                _update_message_decision_metadata(saved_message, service_decision.meta)
            if saved_message and clarify_reason:
                _update_message_decision_metadata(saved_message, {"clarify_reason": clarify_reason})
            _maybe_store_service_carryover(
                conversation=conversation,
                service_meta=service_decision.meta if isinstance(service_decision.meta, dict) else None,
                intent=service_decision.intent,
                message_count=message_count,
                reason="service_matcher",
            )
            bot_response, sent = _send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if force_truth_gate:
        skip_llm_primary = True
        llm_primary_failed = True
        llm_primary_reason = "forced_truth_gate"

    if routing["allow_bot_reply"] and not skip_llm_primary:
        _ensure_rag_rewrite()
        llm_primary_result = generate_bot_response(
            db,
            conversation,
            message_text,
            payload.client_slug,
            append_user_message=append_user_message,
            pending_hint=conversation.state == ConversationState.PENDING.value,
            timing_context=timing_context,
        )
        _record_rag_meta()
        if not llm_primary_result.ok:
            llm_primary_failed = True
            llm_primary_reason = "ai_error"
        else:
            response_text, confidence = llm_primary_result.value
            if confidence == "bot_inactive":
                llm_primary_failed = True
                llm_primary_reason = "bot_inactive"
            elif response_text and confidence != "low_confidence":
                blocked_topics = _detect_llm_guard_topics(
                    response_text,
                    policy_type=policy_type,
                    policy_pack=policy_pack,
                )
                if blocked_topics:
                    bot_response = MSG_ESCALATED
                    _reset_low_confidence_retry(conversation)

                    result_message = "LLM guard escalation"
                    _, reused, telegram_sent = _reuse_active_handover(
                        db=db,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                        source="llm_guard",
                        intent="llm_guard",
                    )
                    if reused:
                        result_message = f"LLM guard reuse, telegram={'sent' if telegram_sent else 'failed'}"
                    elif conversation.state == ConversationState.BOT_ACTIVE.value and routing["allow_handover_create"]:
                        _record_escalation_metric("intent")
                        result = escalate_to_pending(
                            db=db,
                            conversation=conversation,
                            user_message=message_text,
                            trigger_type="intent",
                            trigger_value="llm_guard",
                        )
                        if result.ok:
                            handover = result.value
                            telegram_sent = send_telegram_notification(
                                db=db,
                                handover=handover,
                                conversation=conversation,
                                user=user,
                                message=message_text,
                            )
                            result_message = f"LLM guard escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        else:
                            result_message = f"LLM guard escalation failed: {result.error}"
                    else:
                        result_message = "LLM guard escalation skipped (already pending)"

                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "llm_guard",
                            "decision": "blocked_topics",
                            "state": conversation.state,
                            "blocked_topics": blocked_topics,
                        },
                    )
                    if saved_message:
                        llm_used = bool(timing_context.get("llm_used")) if timing_context else False
                        llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
                        llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
                        _update_message_decision_metadata(
                            saved_message,
                            {
                                "action": "escalate",
                                "intent": "llm_guard",
                                "source": "llm_guard",
                                "fast_intent": False,
                                "llm_primary_used": False,
                                "llm_used": llm_used,
                                "llm_timeout": llm_timeout,
                                "llm_cache_hit": llm_cache_hit,
                            },
                        )
                    bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
                    if not sent:
                        result_message = f"{result_message}; response_send=failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

                bot_response = response_text
                bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
                _reset_low_confidence_retry(conversation)
                trace = _attach_llm_cache_flag(
                    {
                        "stage": "ai_response",
                        "decision": "bot_reply",
                        "state": conversation.state,
                        "confidence": confidence,
                        "llm_primary_used": True,
                    },
                    timing_context,
                )
                _record_decision_trace(conversation, trace)
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Message sent" if sent else "Failed to send"
                if saved_message:
                    llm_used = bool(timing_context.get("llm_used")) if timing_context else False
                    llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
                    llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "action": "ai_response",
                            "intent": intent.value if intent else None,
                            "source": "llm" if llm_used else "rule",
                            "fast_intent": False,
                            "llm_primary_used": True,
                            "llm_used": llm_used,
                            "llm_timeout": llm_timeout,
                            "llm_cache_hit": llm_cache_hit,
                        },
                    )
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

            else:
                llm_primary_failed = True
                llm_primary_reason = "low_confidence" if confidence == "low_confidence" else "no_response"

    if llm_primary_failed and not bypass_domain_flows and policy_handler and _should_run_truth_gate(
        routing, booking_wants_flow
    ):
        policy_t0 = time.monotonic()
        truth_gate = policy_handler.get("truth_gate")
        decision = None
        if truth_gate:
            if policy_type == "demo_salon":
                decision = truth_gate(
                    message_text,
                    client_slug=payload.client_slug,
                    intent_decomp=intent_decomp_payload,
                )
            else:
                decision = truth_gate(message_text)
        if decision:
            if decision.intent == "price_query":
                price_item_fn = policy_handler.get("price_item")
                price_item = price_item_fn(message_text) if price_item_fn else None
                if not price_item and price_item_fn and isinstance(getattr(decision, "meta", None), dict):
                    service_query = decision.meta.get("service_query")
                    if isinstance(service_query, str) and service_query.strip():
                        price_item = price_item_fn(service_query)
                if price_item:
                    context = _get_conversation_context(conversation)
                    context = _set_service_hint(context, price_item, now)
                    _set_conversation_context(conversation, context)
                elif not (
                    isinstance(getattr(decision, "meta", None), dict)
                    and decision.meta.get("service_query")
                ):
                    decision = DemoSalonDecision(
                        action="escalate",
                        response=MSG_ESCALATED,
                        intent="price_query",
                    )
            if decision.intent == "service_clarify" and decision.action != "escalate":
                clarify_intent = current_goal or "info"
                context = _get_conversation_context(conversation)
                context_manager = _get_context_manager(context)
                if _should_escalate_for_clarify(context_manager, clarify_intent):
                    clarify_count, _ = _get_clarify_attempt_state(context_manager, clarify_intent)
                    _record_context_manager_decision(
                        conversation,
                        saved_message,
                        decision="clarify_limit",
                        updates={
                            "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                            "clarify_reason": "service_clarify",
                            "clarify_limit": True,
                        },
                    )
                    decision = DemoSalonDecision(
                        action="escalate",
                        response=MSG_ESCALATED,
                        intent="clarify_limit",
                        meta={"clarify_limit": True},
                    )
                else:
                    _register_clarify_attempt(
                        conversation=conversation,
                        saved_message=saved_message,
                        intent=clarify_intent,
                        now=now,
                        reason="service_clarify",
                    )
            if decision.action != "escalate" and decision.intent in {
                "service_clarify",
                "duration_or_price_clarify",
            }:
                context = _get_conversation_context(conversation)
                context = _set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    expected_reply_type=EXPECTED_REPLY_SERVICE,
                    reason=decision.intent,
                    now=now,
                )
            if decision.action == "reply":
                guard_response = _maybe_apply_fact_guard(
                    decision_meta=decision.meta if isinstance(decision.meta, dict) else None,
                    intent=decision.intent,
                    source="truth_gate",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
            bot_response = decision.response
            if consult_return_pending:
                bot_response = _apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "truth_gate",
                )
            _reset_low_confidence_retry(conversation)

            result_message = "Truth gate fallback reply sent"
            if decision.action == "escalate":
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=message_text,
                    source="truth_gate",
                    intent=decision.intent,
                )
                if reused:
                    result_message = f"Truth gate reuse, telegram={'sent' if telegram_sent else 'failed'}"
                elif conversation.state == ConversationState.BOT_ACTIVE.value:
                    _record_escalation_metric("intent")
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=message_text,
                        trigger_type="intent",
                        trigger_value=decision.intent or "policy",
                    )
                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=message_text,
                        )
                        result_message = f"Truth gate escalation, telegram={'sent' if telegram_sent else 'failed'}"
                    else:
                        result_message = f"Truth gate escalation failed: {result.error}"
                else:
                    result_message = "Truth gate escalation skipped (already pending)"

            trace_payload = {
                "stage": "truth_gate",
                "decision": decision.action,
                "intent": decision.intent,
                "state": conversation.state,
                "booking_wants_flow": booking_wants_flow,
                "policy_type": policy_type,
                "llm_fallback_reason": llm_primary_reason,
            }
            if decision.intent == "multi_truth":
                trace_payload["multi_truth"] = True
            if isinstance(getattr(decision, "meta", None), dict):
                trace_payload.update(decision.meta)
            _record_decision_trace(conversation, trace_payload)
            _record_message_decision_meta(
                saved_message,
                action=decision.action,
                intent=decision.intent,
                source="truth_gate",
                fast_intent=False,
            )
            if saved_message and isinstance(getattr(decision, "meta", None), dict):
                _update_message_decision_metadata(saved_message, decision.meta)
            if saved_message and decision.intent == "service_clarify":
                clarify_reason = None
                service_meta = getattr(decision, "meta", None)
                service_query = None
                service_source = None
                if isinstance(service_meta, dict):
                    service_query = service_meta.get("service_query")
                    service_source = service_meta.get("service_query_source")
                if not service_query and service_source in (None, "", "none"):
                    clarify_reason = "missing_service_query"
                elif not service_query and intent_decomp_used:
                    decomp_query = (
                        intent_decomp_payload.get("service_query")
                        if isinstance(intent_decomp_payload, dict)
                        else None
                    )
                    if not decomp_query:
                        intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
                        if "pricing" in intent_set or "duration" in intent_set:
                            clarify_reason = "missing_service_query"
                if clarify_reason:
                    _update_message_decision_metadata(saved_message, {"clarify_reason": clarify_reason})
            decision_meta = decision.meta if isinstance(getattr(decision, "meta", None), dict) else {}
            info_carryover_intents: list[str] = []
            if decision.intent in INFO_INTENTS:
                info_carryover_intents.append(decision.intent)
            if decision.intent in {"parking", "guest_policy"}:
                info_carryover_intents.append(decision.intent)
            if info_carryover_intents or decision_meta.get("info_sections"):
                _maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=info_carryover_intents,
                    info_meta=decision_meta,
                    message_count=message_count,
                    reason="truth_gate",
                )
            _maybe_store_service_carryover(
                conversation=conversation,
                service_meta=decision.meta if isinstance(decision.meta, dict) else None,
                intent=decision.intent,
                message_count=message_count,
                reason="truth_gate",
            )
            bot_response, sent = _send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            _log_timing(
                "policy_gate_ms",
                (time.monotonic() - policy_t0) * 1000,
                {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "truth_fallback"},
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )
        _log_timing(
            "policy_gate_ms",
            (time.monotonic() - policy_t0) * 1000,
            {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "truth_fallback"},
        )

    # 10. Classify intent (expensive). Protect against accidental escalations on short/noisy messages.
    intent_t0 = time.monotonic()
    decision_text = _normalize_message_text(message_text)
    signals = _detect_intent_signals(decision_text)
    intent = signals.intent
    is_greeting = signals.is_greeting
    is_thanks = signals.is_thanks
    is_ack = signals.is_ack
    is_low_signal = signals.is_low_signal
    is_status_question = signals.is_status_question
    intent_contract, intent_error = build_intent_contract(signals, intent_decomp_payload)
    _record_decision_trace(
        conversation,
        {
            "stage": "contract",
            "decision": "intent",
            "contract_ok": intent_error is None,
            "contract_error": intent_error,
            "contract": intent_contract,
        },
    )

    domain_intent = DomainIntent.UNKNOWN
    domain_in_score = 0.0
    domain_out_score = 0.0
    domain_meta: dict = {}
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not (is_greeting or is_thanks or is_ack or is_low_signal)
        and not is_status_question
    ):
        domain_intent, domain_in_score, domain_out_score, domain_meta = classify_domain_with_scores(
            message_text, client.config if client else None
        )
        log_scores = _is_env_enabled(os.environ.get("DOMAIN_ROUTER_LOG_SCORES"), default=False)
        if log_scores and (domain_intent != DomainIntent.UNKNOWN or max(domain_in_score, domain_out_score) >= 0.45):
            logger.info(
                "Domain scores",
                extra={
                    "context": {
                        "client_slug": payload.client_slug,
                        "remote_jid": remote_jid,
                        "intent": intent.value,
                        "domain_intent": domain_intent.value,
                        "in_score": round(domain_in_score, 4),
                        "out_score": round(domain_out_score, 4),
                        "in_threshold": domain_meta.get("in_threshold"),
                        "out_threshold": domain_meta.get("out_threshold"),
                        "margin": domain_meta.get("margin"),
                        "out_hits": domain_meta.get("out_hits"),
                        "strict_in_hits": domain_meta.get("strict_in_hits"),
                        "matched_in": domain_meta.get("matched_in"),
                        "matched_out": domain_meta.get("matched_out"),
                        "matched_strict_in": domain_meta.get("matched_strict_in"),
                        "anchors_in": domain_meta.get("anchors_in"),
                        "anchors_out": domain_meta.get("anchors_out"),
                        "strict_in_anchors": domain_meta.get("strict_in_anchors"),
                        "message_len": len(message_text),
                        "message_preview": message_text[:80],
                    }
                },
            )

    domain_out_hits = int(domain_meta.get("out_hits") or 0)
    domain_strict_in_hits = int(domain_meta.get("strict_in_hits") or 0)
    class_router_result = _resolve_class_router_result(
        info_intents=info_class_intents,
        info_meta=info_class_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        router_state=router_state,
    )
    out_of_domain_signal = class_router_result["out_of_domain_signal"]
    _log_timing(
        "intent_ms",
        (time.monotonic() - intent_t0) * 1000,
        {
            "intent": intent.value,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
            "class_router": class_router_result,
        },
    )

    rag_confident = False

    router_meta = _set_router_observability(
        saved_message,
        eligible=not expected_reply_shortcircuit,
        reason="expected_reply_shortcircuit" if expected_reply_shortcircuit else "none",
    )
    controller_meta = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_used = bool(controller_meta.get("used")) if isinstance(controller_meta, dict) else False
    controller_attempted = bool(controller_meta.get("attempted")) if isinstance(controller_meta, dict) else False
    controller_fallback = bool(controller_meta.get("fallback")) if isinstance(controller_meta, dict) else False
    controller_low_confidence = (
        bool(controller_meta.get("low_confidence")) if isinstance(controller_meta, dict) else False
    )
    controller_used_reason = (
        controller_meta.get("used_reason") if isinstance(controller_meta, dict) else None
    )
    controller_confidence = (
        controller_meta.get("confidence") if isinstance(controller_meta, dict) else None
    )
    controller_error = controller_meta.get("error") if isinstance(controller_meta, dict) else None
    controller_goal = controller_meta.get("goal") if isinstance(controller_meta, dict) else None
    trace_payload = {
        "stage": "class_router",
        "classes": class_router_result.get("classes"),
        "intents": class_router_result.get("intents"),
        "carryover_intents": class_router_result.get("carryover_intents"),
        "in_signals": class_router_result.get("in_signals"),
        "out_signals": class_router_result.get("out_signals"),
        "anchors_in_hits": class_router_result.get("anchors_in_hits"),
        "anchors_out_hits": class_router_result.get("anchors_out_hits"),
        "out_of_domain_signal": out_of_domain_signal,
        "carryover_class": class_router_result.get("carryover_class"),
        "carryover_info_sections": class_router_result.get("carryover_info_sections"),
        "router_fallback_reason": class_router_result.get("router_fallback_reason"),
        "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
        "router": class_router_result.get("router"),
        "controller": controller_meta,
        "controller_used": controller_used,
        "controller_attempted": controller_attempted,
        "controller_fallback": controller_fallback,
        "controller_low_confidence": controller_low_confidence,
        "controller_used_reason": controller_used_reason,
        "controller_confidence": controller_confidence,
        "controller_error": controller_error,
        "controller_goal": controller_goal,
    }
    trace_payload.update(router_meta)
    _record_decision_trace(conversation, trace_payload)
    if saved_message:
        _update_message_decision_metadata(
            saved_message,
            {
                "class_router": class_router_result,
                "carryover_class": class_router_result.get("carryover_class"),
                "router_fallback_reason": class_router_result.get("router_fallback_reason"),
                "controller_used": controller_used,
                "controller_attempted": controller_attempted,
                "controller_fallback": controller_fallback,
                "controller_low_confidence": controller_low_confidence,
                "controller_used_reason": controller_used_reason,
                "controller_confidence": controller_confidence,
                "controller_error": controller_error,
                "controller_goal": controller_goal,
                "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
            },
        )

    _record_decision_trace(
        conversation,
        {
            "stage": "intent",
            "decision": intent.value,
            "state": conversation.state,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "rag_confident": rag_confident,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
            "info_intents": sorted(info_class_intents),
        },
    )

    controller_meta = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_error = controller_meta.get("error") if isinstance(controller_meta, dict) else None
    offline_controller = (not os.environ.get("OPENAI_API_KEY")) or controller_error == "no_api_key"
    info_intents_for_reply: set[str] = set(class_router_result.get("intents") or [])
    for item in class_router_result.get("carryover_intents") or []:
        if isinstance(item, str) and item.strip():
            info_intents_for_reply.add(item.strip().casefold())
    carryover_sections = (
        [item for item in class_router_result.get("carryover_info_sections") or [] if isinstance(item, str)]
        if isinstance(class_router_result, dict)
        else []
    )
    for section in carryover_sections:
        normalized_section = section.strip().casefold()
        if normalized_section in {"location", "hours"}:
            info_intents_for_reply.add(normalized_section)
    info_signals = info_class_meta.get("info_signals") if isinstance(info_class_meta, dict) else None
    base_info_requested = bool(
        {"location", "hours"} & info_intents_for_reply
        or (
            isinstance(info_signals, dict)
            and (info_signals.get("parking") or info_signals.get("guest"))
        )
        or any(
            isinstance(section, str) and section.strip().casefold() in {"location", "hours", "parking", "guest_policy"}
            for section in carryover_sections
        )
    )
    if (
        offline_controller
        and routing["allow_bot_reply"]
        and not booking_wants_flow
        and not bypass_domain_flows
        and policy_handler
        and base_info_requested
        and "info_bundle" in (class_router_result.get("classes") or [])
    ):
        carryover_sections_normalized = {section.strip().casefold() for section in carryover_sections}
        include_parking = (
            bool(info_signals.get("parking")) if isinstance(info_signals, dict) else False
        ) or "parking" in carryover_sections_normalized
        include_guest = (
            bool(info_signals.get("guest")) if isinstance(info_signals, dict) else False
        ) or "guest_policy" in carryover_sections_normalized
        base_bundle_reply, base_bundle_meta = build_info_combined_reply(
            include_parking=include_parking,
            include_guest=include_guest,
        )
        if isinstance(base_bundle_reply, str) and base_bundle_reply.strip():
            info_meta_combined: dict[str, Any] = {}
            if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                info_meta_combined.update(base_bundle_meta)
            guard_response = _maybe_apply_fact_guard(
                decision_meta=info_meta_combined if info_meta_combined else None,
                intent="info_bundle",
                source="class_router",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return guard_response
            bot_response = base_bundle_reply.strip()
            bot_response = _maybe_append_booking_cta(
                bot_response,
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=False,
            )
            bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
            _reset_low_confidence_retry(conversation)
            trace_payload = {
                "stage": "info_class",
                "decision": "reply",
                "state": conversation.state,
                "intents": sorted(info_intents_for_reply),
                "class_router": class_router_result,
            }
            if info_meta_combined:
                trace_payload.update(info_meta_combined)
            _record_decision_trace(conversation, trace_payload)
            _record_message_decision_meta(
                saved_message,
                action="reply",
                intent="info_bundle",
                source="class_router",
                fast_intent=False,
            )
            if saved_message:
                meta_updates = {"class_router": class_router_result}
                if info_meta_combined:
                    meta_updates.update(info_meta_combined)
                meta_updates.update(_controller_meta_updates_from_class_router(class_router_result))
                meta_updates.update(_router_observability_updates_from_class_router(class_router_result))
                _update_message_decision_metadata(saved_message, meta_updates)
            _maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=sorted(info_intents_for_reply),
                info_meta=info_meta_combined,
                message_count=message_count,
                reason="class_router_offline",
            )
            _maybe_store_service_carryover(
                conversation=conversation,
                service_meta=info_meta_combined,
                intent="info_bundle",
                message_count=message_count,
                reason="class_router_offline",
            )
            if consult_return_pending:
                bot_response = _apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "info_class",
                )
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Info class reply sent" if sent else "Info class reply failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    # 10.1 Self-healing moved to health_service.check_and_heal_conversations()
    # Call POST /admin/heal periodically to fix broken states

    is_pending_status_question = (
        conversation.state == ConversationState.PENDING.value and is_handover_status_question(message_text)
    )
    style_reference = not has_media and _is_style_reference_request(message_text, has_media=False)
    decision = _resolve_action(
        routing=routing,
        state=conversation.state,
        signals=signals,
        is_pending_status_question=is_pending_status_question,
        style_reference=style_reference,
        out_of_domain_signal=out_of_domain_signal,
        rag_confident=rag_confident,
    )

    if decision.action == "smalltalk":
        bot_response = GREETING_RESPONSE if intent == Intent.GREETING else THANKS_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "smalltalk",
                "decision": intent.value,
                "state": conversation.state,
            },
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Greeting response sent" if sent else "Greeting response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "pending_status":
        bot_response = MSG_PENDING_STATUS
        _record_decision_trace(
            conversation,
            {
                "stage": "pending_status",
                "decision": "status_reply",
                "state": conversation.state,
            },
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Pending status response sent" if sent else "Pending status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "bot_status":
        bot_response = BOT_STATUS_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "bot_status",
                "decision": "status_reply",
                "state": conversation.state,
            },
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Bot status response sent" if sent else "Bot status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "style_reference":
        bot_response = MSG_STYLE_REFERENCE_NEED_MEDIA
        _record_decision_trace(
            conversation,
            {
                "stage": "style_reference",
                "decision": "need_media",
                "state": conversation.state,
            },
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Style reference prompt sent" if sent else "Style reference prompt failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    if decision.action == "out_of_domain":
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        _record_decision_trace(
            conversation,
            {
                "stage": "out_of_domain",
                "decision": "fallback",
                "state": conversation.state,
                "rag_confident": rag_confident,
            },
        )
        _record_knowledge_backlog(
            db,
            client_id=client.id,
            conversation_id=conversation.id,
            message=saved_message,
            user_text=message_text,
            miss_type="out_of_domain",
        )
        bot_response, sent = _send_and_save(bot_response, allow_quiet_hours=False)
        result_message = "Out-of-domain response sent" if sent else "Out-of-domain response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 10. Handle based on intent and state
    if decision.action == "escalate":
        handover_message = message_text
        if intent == Intent.HUMAN_REQUEST:
            handover_message = select_handover_user_message(db, conversation.id, message_text)

        _, reused, telegram_sent = _reuse_active_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=handover_message,
            source="intent_escalation",
            intent=intent.value,
        )

        if reused:
            bot_response = MSG_ESCALATED
            bot_response, sent = _send_and_save(bot_response)
            result_message = (
                f"Escalation reused ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
            )
        else:
            # Escalate using state_service (atomic transition)
            _record_escalation_metric("intent")
            result = escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=handover_message,
                trigger_type="intent",
                trigger_value=intent.value,
            )

            if result.ok:
                handover = result.value
                # Send notification to Telegram
                telegram_sent = send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=handover_message,
                )
                bot_response = MSG_ESCALATED
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "escalation",
                        "decision": "created",
                        "state": conversation.state,
                        "intent": intent.value,
                        "telegram_sent": telegram_sent,
                    },
                )
                bot_response, sent = _send_and_save(bot_response)
                result_message = f"Escalated ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
            else:
                logger.error(f"Escalation failed: {result.error}")
                # Fallback: respond normally
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "escalation",
                        "decision": "failed",
                        "state": conversation.state,
                        "intent": intent.value,
                        "error": result.error_code,
                    },
                )
                _ensure_rag_rewrite()
                gen_result = generate_bot_response(
                    db,
                    conversation,
                    message_text,
                    payload.client_slug,
                    append_user_message=append_user_message,
                    pending_hint=conversation.state == ConversationState.PENDING.value,
                    timing_context=timing_context,
                )
                _record_rag_meta()
                if gen_result.ok and gen_result.value[0]:
                    bot_response = gen_result.value[0]
                    bot_response, sent = _send_and_save(bot_response)
                result_message = f"Escalation failed ({result.error_code}), responded normally"

    elif decision.action == "pending_escalation":
        bot_response = MSG_PENDING_ESCALATION if intent == Intent.FRUSTRATION else MSG_PENDING_STATUS
        _record_decision_trace(
            conversation,
            {
                "stage": "escalation",
                "decision": "skipped_pending",
                "state": conversation.state,
                "intent": intent.value,
            },
        )
        bot_response, sent = _send_and_save(bot_response)
        result_message = "Escalation skipped (pending), status response sent" if sent else "Pending status response failed"

    elif decision.action == "rejection":
        # Client rejects help
        if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
            handover = get_active_handover(db, conversation.id)
            if handover:
                manager_resolve(db, conversation, handover, manager_id="system", manager_name="system")
            bot_response = MSG_MUTED_TEMP
            _record_decision_trace(
                conversation,
                {
                    "stage": "rejection",
                    "decision": "cancel_handover",
                    "state": conversation.state,
                },
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = "Request cancelled, bot reactivated"
        else:
            mute_first, mute_second = get_mute_settings(db, client.id)
            if conversation.no_count == 0:
                # First rejection: mute (default 30 min)
                conversation.bot_muted_until = now + timedelta(minutes=mute_first)
                conversation.no_count = 1
                bot_response = MSG_MUTED_TEMP
                trace_decision = "muted_first"
            else:
                # Second rejection: mute (default 24 hours)
                conversation.bot_muted_until = now + timedelta(hours=mute_second)
                conversation.no_count += 1
                bot_response = MSG_MUTED_LONG
                trace_decision = "muted_second"

            _record_decision_trace(
                conversation,
                {
                    "stage": "rejection",
                    "decision": trace_decision,
                    "state": conversation.state,
                    "no_count": conversation.no_count,
                },
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = f"Muted (rejection #{conversation.no_count})"

    elif decision.action == "ai_response":
        # Bot responds: normal mode OR pending (bot helps while waiting)
        llm_primary_used = False
        gen_result = llm_primary_result
        if gen_result is None:
            _ensure_rag_rewrite()
            gen_result = generate_bot_response(
                db,
                conversation,
                message_text,
                payload.client_slug,
                append_user_message=append_user_message,
                pending_hint=conversation.state == ConversationState.PENDING.value,
                timing_context=timing_context,
            )
            _record_rag_meta()

        if not gen_result.ok:
            # AI error — fallback response
            bot_response = MSG_AI_ERROR
            _record_decision_trace(
                conversation,
                {
                    "stage": "ai_response",
                    "decision": "ai_error",
                    "state": conversation.state,
                    "error": gen_result.error,
                },
            )
            bot_response, sent = _send_and_save(bot_response)
            result_message = f"AI error: {gen_result.error}"
        else:
            response_text, confidence = gen_result.value

            if confidence == "low_confidence":
                miss_type = (
                    "llm_timeout"
                    if timing_context and timing_context.get("llm_timeout")
                    else "low_confidence"
                )
                _record_knowledge_backlog(
                    db,
                    client_id=client.id,
                    conversation_id=conversation.id,
                    message=saved_message,
                    user_text=message_text,
                    miss_type=miss_type,
                )
                semantic_result = None
                rewrite_query = None
                info_intent_hint = False
                if isinstance(intent_decomp_payload, dict):
                    raw_intents = intent_decomp_payload.get("intents")
                    if isinstance(raw_intents, list):
                        normalized_intents = {
                            item.strip().casefold()
                            for item in raw_intents
                            if isinstance(item, str) and item.strip()
                        }
                        info_intent_hint = bool(normalized_intents & {"hours", "pricing", "duration"})
                if info_intent_hint:
                    llm_primary_failed = True
                    llm_primary_reason = "low_confidence"
                else:
                    router_meta = None
                    router_output = None
                    router_output_class = None
                    if isinstance(class_router_result, dict):
                        router_meta = class_router_result.get("router")
                        if isinstance(router_meta, dict):
                            router_output = router_meta.get("output")
                            if isinstance(router_output, dict):
                                router_output_class = router_output.get("class")
                    if (
                        router_output_class == "out_of_domain"
                        and not (class_router_result.get("in_signals") or [])
                        and not expected_reply_shortcircuit
                    ):
                        bot_response = OUT_OF_DOMAIN_RESPONSE
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "out_of_domain",
                                "decision": "router_low_confidence",
                                "state": conversation.state,
                            },
                        )
                        _record_message_decision_meta(
                            saved_message,
                            action="out_of_domain",
                            intent="out_of_domain",
                            source="router_low_confidence",
                            fast_intent=False,
                        )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "Router OOD reply sent" if sent else "Router OOD reply send failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                    if out_of_domain_signal and not expected_reply_shortcircuit:
                        bot_response = OUT_OF_DOMAIN_RESPONSE
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "out_of_domain",
                                "decision": "domain_anchor",
                                "state": conversation.state,
                            },
                        )
                        _record_message_decision_meta(
                            saved_message,
                            action="out_of_domain",
                            intent="out_of_domain",
                            source="domain_anchor",
                            fast_intent=False,
                        )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "Domain anchor OOD reply sent"
                            if sent
                            else "Domain anchor OOD reply send failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                    if _looks_like_time_only_request(message_text):
                        bot_response = MSG_EXPECTED_SERVICE_OFF_TOPIC
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "time_only_guard",
                                "decision": "service_clarify",
                                "state": conversation.state,
                            },
                        )
                        _record_message_decision_meta(
                            saved_message,
                            action="reply",
                            intent="service_clarify",
                            source="time_only_guard",
                            fast_intent=False,
                        )
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message, {"time_only_guard": True}
                            )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "Time-only guard reply sent" if sent else "Time-only guard send failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                    if not out_of_domain_signal:
                        explicit_service_hint = None
                        if message_text and payload.client_slug:
                            explicit_service_hint = _extract_service_hint(
                                message_text, payload.client_slug
                            )
                        intent_decomp_explicit_query = None
                        if isinstance(intent_decomp_payload, dict):
                            raw_source = intent_decomp_payload.get("service_query_source")
                            raw_query = intent_decomp_payload.get("service_query")
                            if (
                                isinstance(raw_query, str)
                                and raw_query.strip()
                                and raw_source != "context"
                            ):
                                intent_decomp_explicit_query = raw_query.strip()
                        controller_service_query = None
                        for state_key in ("router", "controller"):
                            state = (
                                class_router_result.get(state_key)
                                if isinstance(class_router_result, dict)
                                else None
                            )
                            if not isinstance(state, dict):
                                continue
                            output = state.get("output")
                            if not isinstance(output, dict):
                                continue
                            slots = output.get("slots")
                            if not isinstance(slots, dict):
                                continue
                            candidate = slots.get("service_query")
                            if isinstance(candidate, str) and candidate.strip():
                                controller_service_query = candidate.strip()
                                break
                        in_signals = class_router_result.get("in_signals") or []
                        anchors_in_hits = int(class_router_result.get("anchors_in_hits") or 0)
                        service_semantic_allowed = bool(
                            explicit_service_hint
                            or intent_decomp_explicit_query
                            or controller_service_query
                            or booking_signal
                            or info_intent_hint
                            or in_signals
                            or anchors_in_hits > 0
                        )
                        if not service_semantic_allowed:
                            bot_response = OUT_OF_DOMAIN_RESPONSE
                            _record_decision_trace(
                                conversation,
                                {
                                    "stage": "out_of_domain",
                                    "decision": "service_semantic_guard",
                                    "state": conversation.state,
                                },
                            )
                            _record_message_decision_meta(
                                saved_message,
                                action="out_of_domain",
                                intent="out_of_domain",
                                source="service_semantic_guard",
                                fast_intent=False,
                            )
                            if saved_message:
                                _update_message_decision_metadata(
                                    saved_message,
                                    {
                                        "service_semantic_match_skipped": True,
                                        "service_semantic_match_skip_reason": "low_signal",
                                    },
                                )
                            bot_response, sent = _send_and_save(bot_response)
                            result_message = (
                                "Service semantic guard reply sent"
                                if sent
                                else "Service semantic guard reply send failed"
                            )
                            db.commit()
                            return WebhookResponse(
                                success=True,
                                message=result_message,
                                conversation_id=conversation.id,
                                bot_response=bot_response,
                            )
                        semantic_result = semantic_service_match(message_text, payload.client_slug)
                        if not semantic_result:
                            rewrite_query = rewrite_for_service_match(
                                message_text,
                                payload.client_slug,
                                client_config=client.config if client else None,
                                timing_context=timing_context,
                            )
                            _record_llm_budget_trace()
                            if rewrite_query:
                                semantic_result = semantic_service_match(rewrite_query, payload.client_slug)
                    if semantic_result:
                        rewrite_used = bool(rewrite_query)
                        bot_response = semantic_result.response
                        _reset_low_confidence_retry(conversation)
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "service_semantic_matcher",
                                "decision": semantic_result.action,
                                "state": conversation.state,
                                "score": semantic_result.score,
                                "canonical_name": semantic_result.canonical_name,
                                "suggestions": semantic_result.suggestions or [],
                                "rewrite_used": rewrite_used,
                                "rewrite_query": rewrite_query,
                            },
                        )
                        if saved_message:
                            llm_used = bool(timing_context.get("llm_used")) if timing_context else False
                            llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
                            llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "action": semantic_result.action,
                                    "intent": "service_semantic",
                                    "source": "service_semantic_matcher",
                                    "service_semantic_score": semantic_result.score,
                                    "service_semantic_rewrite_used": rewrite_used,
                                    "service_semantic_rewrite_query": rewrite_query,
                                    "fast_intent": False,
                                    "llm_primary_used": False,
                                    "llm_used": llm_used,
                                    "llm_timeout": llm_timeout,
                                    "llm_cache_hit": llm_cache_hit,
                                },
                            )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = (
                            "Service semantic matcher reply sent" if sent else "Service semantic matcher send failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        )
                    if conversation.state == ConversationState.PENDING.value:
                        # Already escalated: respond but don't re-escalate
                        bot_response = MSG_PENDING_LOW_CONFIDENCE
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "ai_response",
                                "decision": "low_confidence_pending",
                                "state": conversation.state,
                            },
                        )
                        bot_response, sent = _send_and_save(bot_response)
                        result_message = "Low confidence while pending, responded without re-escalation"
                    else:
                        # Low RAG confidence — ask clarifying question before escalation (up to a limit).
                        context = _get_conversation_context(conversation)
                        retry_count = _get_low_confidence_retry_count(context)
                        if should_offer_low_confidence_retry(conversation, now):
                            retry_count = 0

                        if retry_count < LOW_CONFIDENCE_MAX_RETRIES:
                            clarify_intent = current_goal or "info"
                            context_manager = _get_context_manager(context)
                            if _should_escalate_for_clarify(context_manager, clarify_intent):
                                clarify_count, _ = _get_clarify_attempt_state(context_manager, clarify_intent)
                                _record_context_manager_decision(
                                    conversation,
                                    saved_message,
                                    decision="clarify_limit",
                                    updates={
                                        "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                                        "clarify_reason": "low_confidence_retry",
                                        "clarify_limit": True,
                                    },
                                )
                                return _handle_clarify_limit_escalation(
                                    db=db,
                                    conversation=conversation,
                                    user=user,
                                    message_text=message_text,
                                    saved_message=saved_message,
                                    source="ai_response",
                                    allow_handover=routing.get("allow_handover_create", False),
                                    send_response=_send_response,
                                    finalize_response=_finalize_bot_response,
                                )
                            _register_clarify_attempt(
                                conversation=conversation,
                                saved_message=saved_message,
                                intent=clarify_intent,
                                now=now,
                                reason="low_confidence_retry",
                            )
                            bot_response = MSG_LOW_CONFIDENCE_RETRY
                            conversation.retry_offered_at = now
                            context = _set_low_confidence_retry_count(context, retry_count + 1)
                            _set_conversation_context(conversation, context)
                            _record_decision_trace(
                                conversation,
                                {
                                    "stage": "ai_response",
                                    "decision": "low_confidence_retry",
                                    "state": conversation.state,
                                    "retry_count": retry_count + 1,
                                },
                            )
                            bot_response, sent = _send_and_save(bot_response)
                            result_message = "Low confidence: asked clarification before escalation"
                        else:
                            confirmation = {
                                "status": "pending",
                                "asked_at": now.isoformat(),
                                "trigger_type": "low_confidence",
                                "trigger_value": "low_confidence",
                                "user_message": message_text,
                            }
                            context = _set_handover_confirmation(context, confirmation)
                            _set_conversation_context(conversation, context)

                            bot_response = MSG_HANDOVER_CONFIRM
                            _record_decision_trace(
                                conversation,
                                {
                                    "stage": "ai_response",
                                    "decision": "low_confidence_handover_confirm",
                                    "state": conversation.state,
                                    "retry_count": retry_count,
                                },
                            )
                            bot_response, sent = _send_and_save(bot_response)
                            result_message = (
                                "Low confidence: asked for handover confirmation"
                                if sent
                                else "Low confidence: handover confirmation send failed"
                            )

            elif confidence == "bot_inactive":
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "ai_response",
                        "decision": "bot_inactive",
                        "state": conversation.state,
                    },
                )
                result_message = f"Bot not active (state: {conversation.state})"

            elif response_text:
                bot_response = response_text
                logger.debug(f"bot_response: {bot_response[:100] if bot_response else 'None/Empty'}...")
                _reset_low_confidence_retry(conversation)
                llm_primary_used = True
                trace = _attach_llm_cache_flag(
                    {
                        "stage": "ai_response",
                        "decision": "bot_reply",
                        "state": conversation.state,
                        "confidence": confidence,
                    },
                    timing_context,
                )
                _record_decision_trace(conversation, trace)
                bot_response, sent = _send_and_save(bot_response)
                result_message = "Message sent" if sent else "Failed to send"
            else:
                _record_knowledge_backlog(
                    db,
                    client_id=client.id,
                    conversation_id=conversation.id,
                    message=saved_message,
                    user_text=message_text,
                    miss_type="clarify",
                )
                explicit_service_hint = None
                if message_text and payload.client_slug:
                    explicit_service_hint = _extract_service_hint(
                        message_text, payload.client_slug
                    )
                intent_decomp_explicit_query = None
                info_intent_hint = False
                if isinstance(intent_decomp_payload, dict):
                    raw_source = intent_decomp_payload.get("service_query_source")
                    raw_query = intent_decomp_payload.get("service_query")
                    if (
                        isinstance(raw_query, str)
                        and raw_query.strip()
                        and raw_source != "context"
                    ):
                        intent_decomp_explicit_query = raw_query.strip()
                    raw_intents = intent_decomp_payload.get("intents")
                    if isinstance(raw_intents, list):
                        normalized_intents = {
                            item.strip().casefold()
                            for item in raw_intents
                            if isinstance(item, str) and item.strip()
                        }
                        info_intent_hint = bool(
                            normalized_intents & {"hours", "pricing", "duration", "location"}
                        )
                has_domain_signal = bool(
                    explicit_service_hint
                    or intent_decomp_explicit_query
                    or booking_signal
                    or info_class_intents
                    or info_intent_hint
                    or int(class_router_result.get("anchors_in_hits") or 0) > 0
                )
                if not has_domain_signal and not expected_reply_shortcircuit:
                    bot_response = OUT_OF_DOMAIN_RESPONSE
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "out_of_domain",
                            "decision": "no_response_guard",
                            "state": conversation.state,
                        },
                    )
                    _record_message_decision_meta(
                        saved_message,
                        action="out_of_domain",
                        intent="out_of_domain",
                        source="no_response_guard",
                        fast_intent=False,
                    )
                    bot_response, sent = _send_and_save(bot_response)
                    result_message = (
                        "No-response OOD reply sent"
                        if sent
                        else "No-response OOD reply send failed"
                    )
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )
                context = _get_conversation_context(conversation)
                retry_count = _get_low_confidence_retry_count(context)
                if should_offer_low_confidence_retry(conversation, now):
                    retry_count = 0

                if retry_count < LOW_CONFIDENCE_MAX_RETRIES:
                    bot_response = MSG_LOW_CONFIDENCE_RETRY
                    conversation.retry_offered_at = now
                    context = _set_low_confidence_retry_count(context, retry_count + 1)
                    _set_conversation_context(conversation, context)
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "ai_response",
                            "decision": "no_response_retry",
                            "state": conversation.state,
                            "retry_count": retry_count + 1,
                        },
                    )
                    bot_response, sent = _send_and_save(bot_response)
                    result_message = "No response: asked clarification"
                else:
                    confirmation = {
                        "status": "pending",
                        "asked_at": now.isoformat(),
                        "trigger_type": "low_confidence",
                        "trigger_value": "low_confidence",
                        "user_message": message_text,
                    }
                    context = _set_handover_confirmation(context, confirmation)
                    _set_conversation_context(conversation, context)

                    bot_response = MSG_HANDOVER_CONFIRM
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "ai_response",
                            "decision": "no_response_handover_confirm",
                            "state": conversation.state,
                            "retry_count": retry_count,
                        },
                    )
                    bot_response, sent = _send_and_save(bot_response)
                    result_message = (
                        "No response: asked for handover confirmation"
                        if sent
                        else "No response: handover confirmation send failed"
                    )
        if saved_message:
            llm_used = bool(timing_context.get("llm_used")) if timing_context else False
            llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
            llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
            _update_message_decision_metadata(
                saved_message,
                {
                    "action": "ai_response",
                    "intent": intent.value if intent else None,
                    "source": "llm" if llm_used else "rule",
                    "fast_intent": False,
                    "llm_primary_used": llm_primary_used,
                    "llm_used": llm_used,
                    "llm_timeout": llm_timeout,
                    "llm_cache_hit": llm_cache_hit,
                },
            )
    else:
        _record_decision_trace(
            conversation,
            {
                "stage": "routing",
                "decision": "unknown_state",
                "state": conversation.state,
            },
        )
        result_message = f"Unknown state: {conversation.state}"

    db.commit()

    return WebhookResponse(
        success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
    )
