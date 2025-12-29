import asyncio
import base64
import hashlib
import mimetypes
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from app.database import get_db
from app.logging_config import get_logger
from app.models import Branch, Client, ClientSettings, Conversation, Handover, Message, User
from app.schemas.webhook import WebhookBody, WebhookRequest, WebhookResponse
from app.services.ai_service import (
    ACKNOWLEDGEMENT_RESPONSE,
    BOT_STATUS_RESPONSE,
    GREETING_RESPONSE,
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
    transcribe_audio_with_fallback,
)
from app.services.alert_service import alert_warning
from app.services.chatflow_service import send_bot_response, verify_signed_media_path
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    build_consult_reply,
    compose_multi_truth_reply,
    get_demo_salon_decision,
    get_demo_salon_price_item,
    get_demo_salon_price_reply,
    get_demo_salon_service_decision,
    semantic_question_type,
    semantic_service_match,
)
from app.services.escalation_service import get_telegram_credentials, send_telegram_notification
from app.services.intent_service import (
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    classify_intent,
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
    is_rejection,
    should_escalate,
)
from app.services.message_service import generate_bot_response, save_message, select_handover_user_message
from app.services.outbox_service import build_inbound_message_id, enqueue_outbox_message, mark_outbox_status
from app.services.state_machine import ConversationState
from app.services.state_service import escalate_to_pending, manager_resolve
from app.services.telegram_service import TelegramService

logger = get_logger("webhook")

router = APIRouter()

# Optional Redis-based debounce for bursty WhatsApp messages.
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover
    redis_async = None


_debounce_redis_client = None
_debounce_redis_url = None


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _get_debounce_settings() -> tuple[bool, float, int, str, float]:
    enabled = _is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    inactivity_seconds = float(os.environ.get("DEBOUNCE_INACTIVITY_SECONDS", "1.5"))
    ttl_seconds = int(float(os.environ.get("DEBOUNCE_TTL_SECONDS", "30")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEBOUNCE_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds


def _get_message_buffer_settings() -> tuple[bool, int]:
    enabled = _is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    max_messages = int(float(os.environ.get("DEBOUNCE_MAX_BUFFER_MESSAGES", "8")))
    return enabled, max_messages


def _get_outbox_window_merge_seconds() -> float:
    raw = os.environ.get("OUTBOX_WINDOW_MERGE_SECONDS", "2.5")
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, seconds)


def _coerce_outbox_created_at(value: datetime | None) -> datetime:
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _split_outbox_batches(batch_sorted: list[dict], window_seconds: float) -> list[list[dict]]:
    if not batch_sorted:
        return []
    if window_seconds <= 0:
        return [batch_sorted]
    groups: list[list[dict]] = []
    current: list[dict] = []
    last_created: datetime | None = None
    for row in batch_sorted:
        created_at = _coerce_outbox_created_at(row.get("created_at"))
        if not current:
            current.append(row)
            last_created = created_at
            continue
        if last_created and (created_at - last_created).total_seconds() <= window_seconds:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
        last_created = created_at
    if current:
        groups.append(current)
    return groups


def _get_dedup_settings() -> tuple[int, str, float]:
    ttl_seconds = int(float(os.environ.get("DEDUP_TTL_SECONDS", "86400")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEDUP_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return ttl_seconds, redis_url, socket_timeout_seconds


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


@router.get("/media/{media_path:path}")
async def serve_media(media_path: str, expires: int, sig: str):
    """Serve locally stored media via signed URLs."""
    normalized_path = (media_path or "").strip().lstrip("/")
    if not normalized_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing media path")
    if not verify_signed_media_path(normalized_path, expires, sig):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired signature")

    base_dir = Path(MEDIA_STORAGE_DEFAULT_DIR).resolve()
    target_path = (base_dir / normalized_path).resolve()
    if base_dir not in target_path.parents and target_path != base_dir:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path")
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    return FileResponse(target_path)


class MediaInfo:
    def __init__(
        self,
        *,
        raw_type: str,
        media_type: str,
        mime: str | None,
        size_bytes: int | None,
        duration_seconds: float | None,
        url: str | None,
        file_name: str | None,
        caption: str | None,
        base64_data: str | None,
        is_ptt: bool,
    ) -> None:
        self.raw_type = raw_type
        self.media_type = media_type
        self.mime = mime
        self.size_bytes = size_bytes
        self.duration_seconds = duration_seconds
        self.url = url
        self.file_name = file_name
        self.caption = caption
        self.base64_data = base64_data
        self.is_ptt = is_ptt


class MediaDecision:
    def __init__(
        self,
        *,
        allowed: bool,
        reason: str | None = None,
        response: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.allowed = allowed
        self.reason = reason
        self.response = response
        self.retry_after = retry_after


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _coerce_int(value: object, default: int, *, min_value: int | None = None) -> int:
    if value is None:
        result = default
    else:
        try:
            result = int(float(value))
        except (TypeError, ValueError):
            result = default
    if min_value is not None and result < min_value:
        return min_value
    return result


def _get_media_policy(client: Client | None) -> dict:
    overrides = {}
    if client and isinstance(client.config, dict):
        overrides = client.config.get("media") if isinstance(client.config.get("media"), dict) else {}

    max_size_cfg = overrides.get("max_size_mb") if isinstance(overrides.get("max_size_mb"), dict) else {}
    rate_cfg = overrides.get("rate_limit") if isinstance(overrides.get("rate_limit"), dict) else {}

    max_sizes_mb = {
        "photo": _coerce_int(
            overrides.get("max_photo_mb", max_size_cfg.get("photo")),
            MEDIA_MAX_DEFAULT_MB["photo"],
            min_value=1,
        ),
        "audio": _coerce_int(
            overrides.get("max_audio_mb", max_size_cfg.get("audio")),
            MEDIA_MAX_DEFAULT_MB["audio"],
            min_value=1,
        ),
        "document": _coerce_int(
            overrides.get("max_document_mb", max_size_cfg.get("document")),
            MEDIA_MAX_DEFAULT_MB["document"],
            min_value=1,
        ),
    }

    rate_limit = {
        "count": _coerce_int(rate_cfg.get("count"), MEDIA_RATE_LIMIT_DEFAULTS["count"], min_value=1),
        "window_seconds": _coerce_int(
            rate_cfg.get("window_seconds"), MEDIA_RATE_LIMIT_DEFAULTS["window_seconds"], min_value=30
        ),
        "daily_count": _coerce_int(rate_cfg.get("daily_count"), MEDIA_RATE_LIMIT_DEFAULTS["daily_count"], min_value=1),
        "bytes_mb": _coerce_int(rate_cfg.get("bytes_mb"), MEDIA_RATE_LIMIT_DEFAULTS["bytes_mb"], min_value=1),
        "block_seconds": _coerce_int(
            rate_cfg.get("block_seconds"), MEDIA_RATE_LIMIT_DEFAULTS["block_seconds"], min_value=60
        ),
    }

    storage_dir = overrides.get("storage_dir") or MEDIA_STORAGE_DEFAULT_DIR
    allowed_hosts = overrides.get("allowed_hosts")
    if isinstance(allowed_hosts, str):
        allowed_hosts = [host.strip() for host in allowed_hosts.split(",") if host.strip()]
    if not isinstance(allowed_hosts, list) or not allowed_hosts:
        allowed_hosts = ["app.chatflow.kz"]

    return {
        "enabled": _coerce_bool(overrides.get("enabled"), True),
        "allow_photo": _coerce_bool(overrides.get("allow_photo"), True),
        "allow_audio": _coerce_bool(overrides.get("allow_audio"), True),
        "allow_document": _coerce_bool(overrides.get("allow_document"), True),
        "forward_to_telegram": _coerce_bool(overrides.get("forward_to_telegram"), True),
        "store_media": _coerce_bool(overrides.get("store_media"), True),
        "max_size_mb": max_sizes_mb,
        "rate_limit": rate_limit,
        "storage_dir": storage_dir,
        "allowed_hosts": allowed_hosts,
    }


def _normalize_media_type(raw_type: str | None, mime: str | None) -> str:
    raw = (raw_type or "").strip().lower()
    if raw in MEDIA_TYPE_ALIASES:
        return MEDIA_TYPE_ALIASES[raw]
    if mime:
        if mime.startswith("image/"):
            return "photo"
        if mime.startswith("audio/"):
            return "audio"
        if mime in {"application/pdf", "application/msword"} or mime.startswith(
            "application/vnd"
        ):
            return "document"
        if mime.startswith("video/"):
            return "video"
    return "unknown"


def _extract_media_info(body: WebhookBody) -> MediaInfo | None:
    media = body.mediaData if isinstance(body.mediaData, dict) else None
    if not media:
        return None
    raw_type = (body.messageType or media.get("type") or "").strip().lower()
    mime = media.get("mimetype") or media.get("mime") or media.get("type")
    url = media.get("url")
    file_name = media.get("fileName") or media.get("filename")
    caption = media.get("caption")
    base64_data = media.get("base64")
    is_ptt = bool(media.get("ptt"))
    duration_seconds = None
    duration_value = (
        media.get("seconds")
        or media.get("duration")
        or media.get("duration_seconds")
        or media.get("length")
    )
    if duration_value is not None:
        try:
            duration_seconds = float(duration_value)
            if duration_seconds <= 0:
                duration_seconds = None
        except (TypeError, ValueError):
            duration_seconds = None
    size_bytes = None
    size_value = media.get("size")
    if size_value is not None:
        try:
            size_bytes = int(size_value)
        except (TypeError, ValueError):
            size_bytes = None
    if size_bytes is None and isinstance(base64_data, str) and base64_data:
        try:
            size_bytes = (len(base64_data) * 3) // 4
        except Exception:
            size_bytes = None

    media_type = _normalize_media_type(raw_type, mime if isinstance(mime, str) else None)
    return MediaInfo(
        raw_type=raw_type,
        media_type=media_type,
        mime=mime if isinstance(mime, str) else None,
        size_bytes=size_bytes,
        duration_seconds=duration_seconds,
        url=url if isinstance(url, str) else None,
        file_name=file_name if isinstance(file_name, str) else None,
        caption=caption if isinstance(caption, str) else None,
        base64_data=base64_data if isinstance(base64_data, str) else None,
        is_ptt=is_ptt,
    )


_media_rate_warned = False
_media_rate_cache: dict[str, dict[str, float | int]] = {}


def _get_media_rate_settings() -> tuple[str, float]:
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("MEDIA_RATE_SOCKET_TIMEOUT_SECONDS", "0.5"))
    return redis_url, socket_timeout_seconds


def _get_transcription_settings() -> tuple[bool, int, str, str | None, str, str | None, float, int]:
    enabled = _is_env_enabled(os.environ.get("AUDIO_TRANSCRIPTION_ENABLED"), default=False)
    raw_max_mb = os.environ.get("AUDIO_TRANSCRIPTION_MAX_MB", str(AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB))
    try:
        max_mb = float(raw_max_mb)
    except (TypeError, ValueError):
        max_mb = AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB
    max_bytes = max(0, int(max_mb * 1024 * 1024))
    model = os.environ.get("AUDIO_TRANSCRIPTION_MODEL", "whisper-1")
    language = os.environ.get("AUDIO_TRANSCRIPTION_LANGUAGE")
    primary_provider = os.environ.get("ASR_PRIMARY_PROVIDER", "elevenlabs")
    fallback_provider = os.environ.get("ASR_FALLBACK_PROVIDER")
    raw_timeout = os.environ.get("ASR_TIMEOUT_SECONDS", "6")
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError):
        timeout_seconds = 6.0
    if timeout_seconds <= 0:
        timeout_seconds = 6.0
    min_chars = _coerce_int(os.environ.get("ASR_MIN_CHARS"), 12, min_value=0)
    return enabled, max_bytes, model, language, primary_provider, fallback_provider, timeout_seconds, min_chars


def _is_placeholder_text(text: str | None) -> bool:
    if not text:
        return True
    cleaned = text.strip()
    return not cleaned or bool(re.fullmatch(r"\[.+\]", cleaned))


def _is_voice_note(media: MediaInfo | None) -> bool:
    if not media:
        return False
    return media.media_type == "audio" and bool(media.is_ptt)


def _count_words(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"[\w'-]+", text, flags=re.UNICODE))


def _non_letter_ratio(text: str) -> float:
    if not text:
        return 0.0
    letters = sum(1 for char in text if char.isalpha())
    non_letters = sum(1 for char in text if not char.isalpha() and not char.isspace())
    total = letters + non_letters
    if total == 0:
        return 0.0
    return non_letters / total


def _is_asr_low_confidence(text: str, duration_seconds: float | None) -> bool:
    cleaned = (text or "").strip()
    compact = re.sub(r"\s+", "", cleaned)
    if len(compact) < ASR_LOW_CONFIDENCE_MIN_CHARS:
        return True
    words = _count_words(cleaned)
    if (
        duration_seconds is not None
        and duration_seconds > ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS
        and words < ASR_LOW_CONFIDENCE_MIN_WORDS
    ):
        return True
    if _non_letter_ratio(cleaned) >= ASR_LOW_CONFIDENCE_NON_LETTER_RATIO:
        return True
    return False


def _is_style_reference_request(text: str | None, *, has_media: bool) -> bool:
    normalized = normalize_for_matching(text or "")
    if not normalized:
        return False
    if not has_media and not any(token in normalized for token in ["фото", "картин", "референс", "реф", "пример"]):
        return False
    return any(pattern.search(normalized) for pattern in STYLE_REFERENCE_PATTERNS)


def _read_media_bytes_from_storage(storage_path: str | None, max_bytes: int) -> tuple[bytes | None, str | None]:
    if not storage_path:
        return None, "missing_path"
    path = Path(storage_path)
    if not path.exists():
        return None, "missing_file"
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, f"stat_failed:{exc}"
    if max_bytes and size > max_bytes:
        return None, "too_large"
    try:
        return path.read_bytes(), None
    except OSError as exc:
        return None, f"read_failed:{exc}"


async def _download_media_bytes(media: MediaInfo, policy: dict, max_bytes: int) -> tuple[bytes | None, str | None]:
    if not media.url:
        return None, "missing_url"
    allowed_hosts = policy.get("allowed_hosts") if isinstance(policy.get("allowed_hosts"), list) else ["app.chatflow.kz"]
    if not _is_allowed_media_url(media.url, allowed_hosts):
        return None, "blocked_host"

    size_bytes = 0
    data = bytearray()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("GET", media.url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                    size_bytes += len(chunk)
                    if max_bytes and size_bytes > max_bytes:
                        return None, "too_large"
                    data.extend(chunk)
    except Exception as exc:
        return None, f"download_failed:{exc}"

    return bytes(data), None


def _guess_transcript_filename(media: MediaInfo) -> str:
    ext = _guess_extension(media.mime, media.file_name)
    return f"voice{ext}"


async def _maybe_transcribe_voice(
    *,
    media: MediaInfo,
    policy: dict,
    media_decision: MediaDecision | None,
    storage_path: str | None,
    saved_message: Message | None,
) -> tuple[str | None, str | None, dict | None]:
    enabled, max_bytes, model, language, primary_provider, fallback_provider, timeout_seconds, min_chars = (
        _get_transcription_settings()
    )
    if not _is_voice_note(media):
        return None, "not_voice", None

    asr_meta = {
        "asr_used": False,
        "asr_provider": primary_provider,
        "asr_fallback_used": False,
        "asr_failed": False,
        "asr_text_len": 0,
    }

    if not enabled or not max_bytes:
        return None, "disabled", asr_meta
    if media_decision and not media_decision.allowed:
        return None, "not_allowed", asr_meta
    if media.size_bytes and max_bytes and media.size_bytes > max_bytes:
        return None, "too_large", asr_meta

    if saved_message and isinstance(saved_message.message_metadata, dict):
        media_meta = saved_message.message_metadata.get("media") or {}
        existing = media_meta.get("transcript")
        if isinstance(existing, str) and existing.strip():
            asr_meta["asr_used"] = True
            asr_meta["asr_text_len"] = len(existing.strip())
            asr_meta["asr_provider"] = media_meta.get("transcript_provider") or media_meta.get("transcript_model")
            return existing.strip(), "cached", asr_meta

    audio_bytes = None
    source_error = None
    if storage_path:
        audio_bytes, source_error = _read_media_bytes_from_storage(storage_path, max_bytes)
    if not audio_bytes:
        if media.base64_data:
            try:
                estimated = (len(media.base64_data) * 3) // 4
            except Exception:
                estimated = 0
            if max_bytes and estimated > max_bytes:
                return None, "too_large", asr_meta
            try:
                decoded = base64.b64decode(media.base64_data, validate=False)
            except Exception as exc:
                return None, f"base64_decode_failed:{exc}", asr_meta
            if max_bytes and len(decoded) > max_bytes:
                return None, "too_large", asr_meta
            audio_bytes = decoded
        else:
            audio_bytes, source_error = await _download_media_bytes(media, policy, max_bytes)

    if not audio_bytes:
        asr_meta["asr_failed"] = True
        return None, source_error or "missing_audio", asr_meta

    transcript, asr_meta, status = transcribe_audio_with_fallback(
        audio_bytes,
        filename=_guess_transcript_filename(media),
        mime_type=media.mime,
        model=model,
        language=language,
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
        timeout_seconds=timeout_seconds,
        min_chars=min_chars,
    )
    if not transcript:
        return None, status, asr_meta
    return transcript.strip(), status, asr_meta


def _purge_media_rate_cache(now_ts: float) -> None:
    if len(_media_rate_cache) < 5000:
        return
    expired = [key for key, item in _media_rate_cache.items() if item.get("expires_at", 0) <= now_ts]
    for key in expired:
        _media_rate_cache.pop(key, None)


def _check_media_rate_limit_fallback(
    *,
    key_base: str,
    size_bytes: int,
    rate_limit: dict,
) -> MediaDecision:
    now_ts = time.time()
    _purge_media_rate_cache(now_ts)

    block_key = f"{key_base}:block"
    block_until = _media_rate_cache.get(block_key, {}).get("expires_at", 0)
    if block_until and block_until > now_ts:
        retry_after = int(block_until - now_ts)
        return MediaDecision(allowed=False, reason="rate_limited", response=MSG_MEDIA_RATE_LIMIT, retry_after=retry_after)

    window_key = f"{key_base}:window"
    window = _media_rate_cache.get(window_key)
    if not window or window.get("expires_at", 0) <= now_ts:
        window = {"count": 0, "bytes": 0, "expires_at": now_ts + rate_limit["window_seconds"]}
    window["count"] = int(window.get("count", 0)) + 1
    window["bytes"] = int(window.get("bytes", 0)) + size_bytes
    _media_rate_cache[window_key] = window

    day_key = f"{key_base}:day"
    day = _media_rate_cache.get(day_key)
    if not day or day.get("expires_at", 0) <= now_ts:
        day = {"count": 0, "expires_at": now_ts + 86400}
    day["count"] = int(day.get("count", 0)) + 1
    _media_rate_cache[day_key] = day

    if window["count"] > rate_limit["count"]:
        _media_rate_cache[block_key] = {"expires_at": now_ts + rate_limit["block_seconds"]}
        return MediaDecision(allowed=False, reason="rate_limited", response=MSG_MEDIA_RATE_LIMIT, retry_after=rate_limit["block_seconds"])

    if window["bytes"] > rate_limit["bytes_mb"] * 1024 * 1024:
        _media_rate_cache[block_key] = {"expires_at": now_ts + rate_limit["block_seconds"]}
        return MediaDecision(allowed=False, reason="rate_limited", response=MSG_MEDIA_RATE_LIMIT, retry_after=rate_limit["block_seconds"])

    if day["count"] > rate_limit["daily_count"]:
        _media_rate_cache[block_key] = {"expires_at": now_ts + rate_limit["block_seconds"]}
        return MediaDecision(allowed=False, reason="rate_limited", response=MSG_MEDIA_RATE_LIMIT, retry_after=rate_limit["block_seconds"])

    return MediaDecision(allowed=True)


async def _check_media_rate_limit(
    *,
    redis_client,
    key_base: str,
    size_bytes: int,
    rate_limit: dict,
) -> MediaDecision:
    global _media_rate_warned
    if not redis_client:
        if not _media_rate_warned:
            alert_warning("Media rate limiter disabled (redis unavailable)", {"key": key_base})
            _media_rate_warned = True
        return _check_media_rate_limit_fallback(
            key_base=key_base,
            size_bytes=size_bytes,
            rate_limit=rate_limit,
        )

    block_key = f"{key_base}:block"
    try:
        blocked = await redis_client.get(block_key)
    except Exception as exc:
        logger.warning("Media rate limit redis check failed", extra={"context": {"error": str(exc)}})
        return _check_media_rate_limit_fallback(
            key_base=key_base,
            size_bytes=size_bytes,
            rate_limit=rate_limit,
        )

    if blocked:
        return MediaDecision(allowed=False, reason="rate_limited", response=MSG_MEDIA_RATE_LIMIT)

    count_key = f"{key_base}:count"
    bytes_key = f"{key_base}:bytes"
    day_key = f"{key_base}:day"

    try:
        count = await redis_client.incr(count_key)
        if count == 1:
            await redis_client.expire(count_key, rate_limit["window_seconds"])
        total_bytes = await redis_client.incrby(bytes_key, size_bytes)
        if total_bytes == size_bytes:
            await redis_client.expire(bytes_key, rate_limit["window_seconds"])
        daily = await redis_client.incr(day_key)
        if daily == 1:
            await redis_client.expire(day_key, 86400)
    except Exception as exc:
        logger.warning("Media rate limit redis update failed", extra={"context": {"error": str(exc)}})
        return _check_media_rate_limit_fallback(
            key_base=key_base,
            size_bytes=size_bytes,
            rate_limit=rate_limit,
        )

    over_limit = (
        count > rate_limit["count"]
        or total_bytes > rate_limit["bytes_mb"] * 1024 * 1024
        or daily > rate_limit["daily_count"]
    )
    if over_limit:
        try:
            await redis_client.setex(block_key, rate_limit["block_seconds"], "1")
        except Exception as exc:
            logger.warning("Media rate limit redis block failed", extra={"context": {"error": str(exc)}})
        return MediaDecision(allowed=False, reason="rate_limited", response=MSG_MEDIA_RATE_LIMIT, retry_after=rate_limit["block_seconds"])

    return MediaDecision(allowed=True)


async def _evaluate_media_decision(
    *,
    media: MediaInfo,
    client_id: UUID,
    remote_jid: str,
    policy: dict,
    redis_client,
    count_rate_limit: bool = True,
) -> MediaDecision:
    if not policy.get("enabled"):
        return MediaDecision(allowed=False, reason="disabled", response=MSG_MEDIA_UNSUPPORTED)

    allowed = {
        "photo": policy.get("allow_photo", True),
        "audio": policy.get("allow_audio", True),
        "document": policy.get("allow_document", True),
    }

    if media.media_type not in allowed or not allowed.get(media.media_type, False):
        return MediaDecision(allowed=False, reason="unsupported_type", response=MSG_MEDIA_UNSUPPORTED)

    max_mb = policy.get("max_size_mb", MEDIA_MAX_DEFAULT_MB).get(media.media_type, 8)
    max_bytes = max_mb * 1024 * 1024
    size_bytes = media.size_bytes
    if size_bytes is not None and size_bytes > max_bytes:
        return MediaDecision(allowed=False, reason="too_large", response=MSG_MEDIA_TOO_LARGE)

    if not count_rate_limit:
        return MediaDecision(allowed=True)

    size_for_limit = size_bytes or 0
    decision = await _check_media_rate_limit(
        redis_client=redis_client,
        key_base=f"media:{client_id}:{remote_jid}",
        size_bytes=size_for_limit,
        rate_limit=policy.get("rate_limit", MEDIA_RATE_LIMIT_DEFAULTS),
    )
    if not decision.allowed:
        return decision

    return MediaDecision(allowed=True)


def _guess_extension(mime: str | None, file_name: str | None) -> str:
    if file_name:
        suffix = Path(file_name).suffix
        if suffix:
            return suffix
    if mime:
        ext = mimetypes.guess_extension(mime.split(";")[0].strip())
        if ext:
            return ext
    return ""


def _is_allowed_media_url(url: str, allowed_hosts: list[str]) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    return host in allowed_hosts


def _safe_media_id(value: str | None) -> str:
    if not value:
        return uuid4().hex
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", value)
    return cleaned or uuid4().hex


async def _store_media_locally(
    *,
    media: MediaInfo,
    policy: dict,
    client_slug: str,
    conversation_id: UUID,
    message_id: str | None,
) -> dict:
    if not policy.get("store_media", True):
        return {"stored": False, "error": "store_disabled"}

    storage_dir = Path(str(policy.get("storage_dir") or MEDIA_STORAGE_DEFAULT_DIR))
    target_dir = storage_dir / client_slug / str(conversation_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    ext = _guess_extension(media.mime, media.file_name)
    file_id = _safe_media_id(message_id)
    target_path = target_dir / f"{file_id}{ext}"

    max_mb = policy.get("max_size_mb", MEDIA_MAX_DEFAULT_MB).get(media.media_type, 8)
    max_bytes = min(max_mb * 1024 * 1024, MEDIA_STORAGE_MAX_BYTES)

    if media.base64_data:
        estimated = (len(media.base64_data) * 3) // 4
        if estimated > max_bytes:
            return {"stored": False, "error": "too_large"}
        try:
            decoded = base64.b64decode(media.base64_data, validate=False)
        except Exception as exc:
            return {"stored": False, "error": f"base64_decode_failed:{exc}"}
        if len(decoded) > max_bytes:
            return {"stored": False, "error": "too_large"}
        digest = hashlib.sha256(decoded).hexdigest()
        target_path.write_bytes(decoded)
        return {"stored": True, "path": str(target_path), "size_bytes": len(decoded), "sha256": digest}

    if not media.url:
        return {"stored": False, "error": "missing_url"}
    allowed_hosts = policy.get("allowed_hosts") if isinstance(policy.get("allowed_hosts"), list) else ["app.chatflow.kz"]
    if not _is_allowed_media_url(media.url, allowed_hosts):
        return {"stored": False, "error": "blocked_host"}

    digest = hashlib.sha256()
    size_bytes = 0
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("GET", media.url) as response:
                response.raise_for_status()
                with target_path.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        if not chunk:
                            continue
                        size_bytes += len(chunk)
                        if size_bytes > max_bytes:
                            handle.close()
                            if target_path.exists():
                                target_path.unlink()
                            return {"stored": False, "error": "too_large"}
                        digest.update(chunk)
                        handle.write(chunk)
    except Exception as exc:
        if target_path.exists():
            target_path.unlink()
        return {"stored": False, "error": f"download_failed:{exc}"}

    return {
        "stored": True,
        "path": str(target_path),
        "size_bytes": size_bytes,
        "sha256": digest.hexdigest(),
    }


def _build_media_caption(message_text: str | None, media: MediaInfo) -> str | None:
    if media.caption and media.caption.strip():
        return media.caption.strip()
    if message_text:
        text = message_text.strip()
        if text and not re.fullmatch(r"\[.+\]", text):
            return text
    return None


def _select_media_source(media: MediaInfo, stored_path: str | None) -> str | None:
    if stored_path and Path(stored_path).exists():
        return stored_path
    if media.url:
        return media.url
    return None


def _send_telegram_media(
    *,
    telegram: TelegramService,
    chat_id: str,
    topic_id: int,
    media: MediaInfo,
    caption: str | None,
    stored_path: str | None,
) -> dict:
    source = _select_media_source(media, stored_path)
    if not source:
        return {"ok": False, "error": "missing_media_source"}

    if media.media_type == "photo":
        return telegram.send_photo(
            chat_id=chat_id,
            photo=source,
            caption=caption,
            message_thread_id=topic_id,
        )
    if media.media_type == "audio":
        if media.is_ptt and media.mime and ("ogg" in media.mime or "opus" in media.mime):
            return telegram.send_voice(
                chat_id=chat_id,
                voice=source,
                caption=caption,
                message_thread_id=topic_id,
            )
        return telegram.send_audio(
            chat_id=chat_id,
            audio=source,
            caption=caption,
            message_thread_id=topic_id,
        )
    if media.media_type == "document":
        return telegram.send_document(
            chat_id=chat_id,
            document=source,
            caption=caption,
            message_thread_id=topic_id,
        )
    return {"ok": False, "error": f"unsupported_media_type:{media.media_type}"}


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


def _update_message_media_metadata(message: Message, updates: dict) -> None:
    metadata = dict(message.message_metadata or {})
    media_meta = dict(metadata.get("media") or {})
    media_meta.update(updates)
    metadata["media"] = media_meta
    message.message_metadata = metadata


def _update_message_asr_metadata(message: Message, updates: dict) -> None:
    metadata = dict(message.message_metadata or {})
    asr_meta = dict(metadata.get("asr") or {})
    asr_meta.update(updates)
    metadata["asr"] = asr_meta
    message.message_metadata = metadata


def _update_message_decision_metadata(message: Message, updates: dict) -> None:
    metadata = dict(message.message_metadata or {})
    decision_meta = dict(metadata.get("decision_meta") or {})
    decision_meta.update(updates)
    metadata["decision_meta"] = decision_meta
    message.message_metadata = metadata


def _record_message_decision_meta(
    message: Message | None,
    *,
    action: str | None,
    intent: str | None,
    source: str,
    fast_intent: bool,
) -> None:
    if not message:
        return
    _update_message_decision_metadata(
        message,
        {
            "action": action,
            "intent": intent,
            "source": source,
            "fast_intent": fast_intent,
            "llm_primary_used": False,
            "llm_used": False,
            "llm_timeout": False,
            "llm_cache_hit": False,
        },
    )


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


def _serialize_media_decision(decision: MediaDecision) -> dict:
    return {
        "allowed": bool(decision.allowed),
        "reason": decision.reason,
        "retry_after": decision.retry_after,
    }


def _media_response_for_reason(reason: str | None) -> str | None:
    if reason == "too_large":
        return MSG_MEDIA_TOO_LARGE
    if reason == "rate_limited":
        return MSG_MEDIA_RATE_LIMIT
    if reason in {"unsupported_type", "disabled"}:
        return MSG_MEDIA_UNSUPPORTED
    return None


def _deserialize_media_decision(data: dict | None) -> MediaDecision | None:
    if not isinstance(data, dict):
        return None
    if "allowed" not in data:
        return None
    reason = data.get("reason")
    return MediaDecision(
        allowed=bool(data.get("allowed")),
        reason=reason if isinstance(reason, str) else None,
        response=_media_response_for_reason(reason if isinstance(reason, str) else None),
        retry_after=data.get("retry_after") if isinstance(data.get("retry_after"), int) else None,
    )


def _coerce_remote_jid(value) -> str | None:
    if not value or isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if "@" in text:
        return text
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"


def _normalize_chatflow_payload(payload: dict, client_slug: str | None) -> tuple[dict, str]:
    body = payload.get("body")
    if not isinstance(body, dict):
        body = payload

    body = dict(body)
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    candidate = payload
    remote_jid = metadata.get("remoteJid")
    if not remote_jid:
        for key in ("remoteJid", "remote_jid", "jid", "from", "chatId", "session_id", "user_id", "phone"):
            remote_jid = candidate.get(key)
            if remote_jid:
                break
    remote_jid = _coerce_remote_jid(remote_jid)
    if remote_jid:
        metadata.setdefault("remoteJid", remote_jid)

    message_id = metadata.get("messageId")
    if not message_id:
        for key in ("messageId", "message_id", "id"):
            message_id = candidate.get(key)
            if message_id:
                break

    msg_obj = candidate.get("message") if isinstance(candidate.get("message"), dict) else None
    if not message_id and msg_obj:
        message_id = msg_obj.get("id") or msg_obj.get("messageId")
    if message_id:
        metadata.setdefault("messageId", message_id)

    timestamp = metadata.get("timestamp")
    if not timestamp:
        for key in ("timestamp", "t", "time"):
            timestamp = candidate.get(key)
            if timestamp:
                break
    if timestamp:
        metadata.setdefault("timestamp", timestamp)

    sender = metadata.get("sender")
    if not sender:
        for key in ("sender", "pushName", "name"):
            sender = candidate.get(key)
            if sender:
                break
    if sender:
        metadata.setdefault("sender", sender)

    instance_id = metadata.get("instanceId") or metadata.get("instance_id")
    if not instance_id:
        for key in ("instanceId", "instance_id", "instance", "whatsapp_instance_id"):
            instance_id = candidate.get(key)
            if instance_id:
                break
    if not instance_id:
        node_data = candidate.get("nodeData") or body.get("nodeData")
        if isinstance(node_data, dict):
            for key in ("instanceId", "instance_id", "instance", "whatsapp_instance_id"):
                instance_id = node_data.get(key)
                if instance_id:
                    break
    if instance_id:
        metadata.setdefault("instanceId", instance_id)

    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        message = None
        for key in ("text", "body", "message_text", "content"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                message = value
                break
        if not message and msg_obj:
            for key in ("text", "body", "message", "content"):
                value = msg_obj.get(key)
                if isinstance(value, str) and value.strip():
                    message = value
                    break
    if message:
        body["message"] = message

    body["metadata"] = metadata
    slug = client_slug or payload.get("client_slug") or "truffles"
    return body, slug


async def _parse_webhook_request(
    request: Request,
    *,
    client_slug: str | None = None,
) -> WebhookRequest | WebhookResponse:
    try:
        payload = await request.json()
    except ClientDisconnect:
        logger.info("Webhook client disconnected during read", extra={"context": {"client_slug": client_slug}})
        return WebhookResponse(success=True, message="Client disconnected")
    except Exception as exc:
        try:
            raw = await request.body()
        except ClientDisconnect:
            logger.info("Webhook client disconnected during body read", extra={"context": {"client_slug": client_slug}})
            return WebhookResponse(success=True, message="Client disconnected")
        if not raw or not raw.strip():
            logger.info("Webhook probe with empty body", extra={"context": {"client_slug": client_slug}})
            return WebhookResponse(success=True, message="Empty payload")

        logger.warning(
            "Webhook payload is not valid JSON",
            extra={
                "context": {
                    "error": str(exc),
                    "body_preview": raw[:200].decode("utf-8", "ignore"),
                }
            },
        )
        return WebhookResponse(success=False, message="Invalid JSON payload")

    if not isinstance(payload, dict):
        return WebhookResponse(success=False, message="Invalid payload format")

    body, slug = _normalize_chatflow_payload(payload, client_slug)

    query_instance_id = (
        request.query_params.get("instanceId")
        or request.query_params.get("instance_id")
        or request.query_params.get("instance")
    )
    if query_instance_id:
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
        metadata.setdefault("instanceId", query_instance_id)
        body["metadata"] = metadata

    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    if not metadata.get("remoteJid") or not body.get("message"):
        logger.info(
            "Webhook payload missing expected fields",
            extra={
                "context": {
                    "client_slug": slug,
                    "payload_keys": list(payload.keys())[:20],
                    "body_keys": list(body.keys())[:20],
                    "metadata_keys": list(metadata.keys())[:20],
                    "has_message": bool(body.get("message")),
                }
            },
        )

    try:
        return WebhookRequest(body=body, client_slug=slug)
    except Exception as exc:
        logger.warning("Webhook payload validation failed", extra={"context": {"error": str(exc)}})
        return WebhookResponse(success=False, message="Invalid webhook payload")


def _get_debounce_redis(redis_url: str, socket_timeout_seconds: float):
    global _debounce_redis_client, _debounce_redis_url

    if redis_async is None:
        return None

    if _debounce_redis_client is None or _debounce_redis_url != redis_url:
        _debounce_redis_url = redis_url
        _debounce_redis_client = redis_async.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=socket_timeout_seconds,
            socket_timeout=socket_timeout_seconds,
        )

    return _debounce_redis_client


async def should_process_debounced_message(
    *,
    client_id: str,
    remote_jid: str,
    message_id: str | None,
    sleep_func=asyncio.sleep,
    redis_client=None,
) -> bool:
    """
    Debounce bursty user messages: only the latest message in a short window triggers AI/escalation.

    Strategy: store a per-user token in Redis and check after a short pause whether it's still the last one.
    If Redis is unavailable, falls back to current behavior (process immediately).
    """
    enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds = _get_debounce_settings()
    if not enabled:
        return True

    token = message_id or uuid4().hex
    key = f"truffles:debounce:{client_id}:{remote_jid}"

    redis_client = redis_client or _get_debounce_redis(redis_url, socket_timeout_seconds)
    if not redis_client:
        return True

    try:
        await redis_client.set(key, token, ex=ttl_seconds)
        await sleep_func(inactivity_seconds)
        last_token = await redis_client.get(key)
        return last_token == token
    except Exception as e:
        logger.warning(f"Debounce unavailable, proceeding without it: {e}")
        return True


async def _buffer_user_message(
    *,
    redis_client,
    client_id: str,
    remote_jid: str,
    message_text: str,
    ttl_seconds: int,
    max_messages: int,
) -> None:
    if not redis_client:
        return

    key = f"truffles:buffer:{client_id}:{remote_jid}"
    try:
        await redis_client.rpush(key, message_text)
        await redis_client.ltrim(key, -max_messages, -1)
        await redis_client.expire(key, ttl_seconds)
    except Exception as e:
        logger.warning(f"Message buffer unavailable: {e}")


async def _drain_buffered_messages(*, redis_client, client_id: str, remote_jid: str) -> list[str]:
    if not redis_client:
        return []

    key = f"truffles:buffer:{client_id}:{remote_jid}"
    try:
        messages = await redis_client.lrange(key, 0, -1)
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Message buffer drain failed: {e}")
        return []

    cleaned: list[str] = []
    for msg in messages or []:
        if not msg:
            continue
        text = msg.strip()
        if text:
            cleaned.append(text)
    return cleaned


async def is_duplicate_message_id(
    *,
    db: Session,
    client_id,
    message_id: str | None,
    redis_client=None,
) -> bool:
    if not message_id:
        return False

    ttl_seconds, redis_url, socket_timeout_seconds = _get_dedup_settings()
    key = f"truffles:dedup:{client_id}:{message_id}"

    redis_client = redis_client or _get_debounce_redis(redis_url, socket_timeout_seconds)
    if redis_client:
        try:
            was_set = await redis_client.set(key, "1", ex=ttl_seconds, nx=True)
            if not was_set:
                return True
        except Exception as e:
            logger.warning(f"Dedup redis unavailable, falling back to DB: {e}")

    # Persistent dedup in DB (message_dedup) to survive restarts/retries.
    try:
        result = db.execute(
            text(
                """
                INSERT INTO message_dedup (client_id, message_id)
                VALUES (:client_id, :message_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"client_id": client_id, "message_id": message_id},
        )
        db.commit()
        if result.rowcount == 0:
            logger.info(
                "Duplicate message_id (DB)",
                extra={"context": {"client_id": str(client_id), "message_id": message_id}},
            )
            return True
    except Exception as e:
        logger.warning(
            "DB dedup check failed, falling back to messages table",
            extra={"context": {"client_id": str(client_id), "message_id": message_id, "error": str(e)}},
        )

    duplicate = (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            Message.message_metadata["message_id"].astext == message_id,
        )
        .first()
    )
    if duplicate:
        logger.info(
            "Duplicate message_id (messages table)",
            extra={"context": {"client_id": str(client_id), "message_id": message_id}},
        )
    return duplicate is not None

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
MSG_PENDING_LOW_CONFIDENCE = (
    "Я уже передал менеджеру — он скоро подключится. "
    "Пока ждём, уточните: услуги/цены или запись/адрес."
)
MSG_PENDING_ESCALATION = "Я уже передал менеджеру — он скоро подключится."
MSG_PENDING_STATUS = "Да, я передал. Сейчас менеджер ещё не взял заявку. Как только возьмёт — ответит здесь. Пока ждём, могу помочь: уточните, что нужно?"
MSG_PENDING_WAIT = "Администратор подключится."
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

LLM_GUARD_TOPICS = {
    "payment": [
        "оплат",
        "предоплат",
        "kaspi",
        "каспи",
        "перевод",
        "карт",
        "карта",
        "qr",
        "счет",
        "счёт",
        "реквизит",
        "iban",
        "swift",
        "терминал",
        "эквайр",
        "касса",
        "налич",
        "безнал",
    ],
    "medical": [
        "беремен",
        "аллерг",
        "противопоказ",
        "медицин",
        "кормл",
        "лактац",
        "ожог",
        "жжет",
        "жжёт",
        "болит",
        "больно",
        "кров",
        "воспал",
        "сып",
        "реакц",
        "анестез",
        "обезбол",
        "дермат",
    ],
    "complaint": [
        "жалоб",
        "претенз",
        "разочар",
        "недовол",
        "плохо",
        "ужас",
        "кошмар",
        "хам",
        "грубо",
        "брак",
        "отпал",
        "слезл",
        "сломал",
        "испор",
    ],
    "discount": [
        "скидк",
        "скидоч",
        "скидос",
        "дешевл",
        "подешевл",
        "купон",
        "акци",
        "промо",
        "промокод",
        "торг",
        "уступ",
    ],
    "refund": [
        "возврат",
        "верну",
        "вернем",
        "вернём",
        "refund",
    ],
}

MSG_BOOKING_ASK_SERVICE = "На какую услугу хотите записаться?"
MSG_BOOKING_ASK_DATETIME = "На какую дату и время вам удобно?"
MSG_BOOKING_ASK_NAME = "Как вас зовут?"
MSG_BOOKING_CANCELLED = "Хорошо, если передумаете — пишите."
MSG_BOOKING_REENGAGE = "Хотите продолжить запись? Если да — напишите услугу."

SERVICE_HINT_KEY = "last_service_hint"
SERVICE_HINT_AT_KEY = "last_service_hint_at"
REENGAGE_CONFIRM_KEY = "reengage_confirmation"
ASR_CONFIRM_KEY = "asr_confirm_pending"
DECISION_TRACE_KEY = "decision_trace"
CONTEXT_MANAGER_KEY = "context_manager"

CLARIFY_MAX_ATTEMPTS = 2
REFUSAL_TTL_MESSAGES = 10
SUMMARY_MESSAGE_THRESHOLD = 12

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


def _get_routing_policy(state: str) -> dict[str, bool]:
    policy = ROUTING_MATRIX.get(state)
    if policy:
        return dict(policy)
    return {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    }


def _should_run_booking_flow(
    policy: dict[str, bool],
    *,
    booking_active: bool,
    booking_signal: bool,
) -> bool:
    return bool(policy.get("allow_booking_flow")) and (booking_active or booking_signal)


def _should_run_truth_gate(policy: dict[str, bool], booking_wants_flow: bool) -> bool:
    return bool(policy.get("allow_truth_gate_reply")) and not booking_wants_flow


def _should_run_demo_truth_gate(policy: dict[str, bool], booking_wants_flow: bool) -> bool:
    return _should_run_truth_gate(policy, booking_wants_flow)


def _should_escalate_to_pending(policy: dict[str, bool], intent: Intent) -> bool:
    return bool(policy.get("allow_handover_create")) and should_escalate(intent)


@dataclass(frozen=True)
class DecisionSignals:
    intent: Intent
    is_greeting: bool
    is_thanks: bool
    is_ack: bool
    is_low_signal: bool
    is_status_question: bool


@dataclass(frozen=True)
class DecisionOutcome:
    action: str


def _normalize_message_text(message_text: str | None) -> str:
    return (message_text or "").strip()


def _detect_fast_intent(
    message_text: str,
    *,
    policy_type: str | None,
    booking_wants_flow: bool,
    bypass_domain_flows: bool,
) -> DemoSalonDecision | None:
    if not message_text or booking_wants_flow or bypass_domain_flows:
        return None

    if is_greeting_message(message_text):
        return DemoSalonDecision(action="smalltalk", response=GREETING_RESPONSE, intent="greeting")
    if is_thanks_message(message_text):
        return DemoSalonDecision(action="smalltalk", response=THANKS_RESPONSE, intent="thanks")
    if is_acknowledgement_message(message_text):
        return DemoSalonDecision(action="smalltalk", response=ACKNOWLEDGEMENT_RESPONSE, intent="ack")
    return None


def _detect_intent_signals(message_text: str) -> DecisionSignals:
    is_greeting = is_greeting_message(message_text)
    is_thanks = is_thanks_message(message_text)
    is_ack = is_acknowledgement_message(message_text)
    is_low_signal = is_low_signal_message(message_text)
    is_status_question = is_bot_status_question(message_text)

    if is_greeting:
        intent = Intent.GREETING
        logger.info("Intent shortcut: greeting")
    elif is_thanks:
        intent = Intent.THANKS
        logger.info("Intent shortcut: thanks")
    elif is_ack or is_low_signal:
        intent = Intent.OTHER
        logger.info("Intent shortcut: acknowledgement/low-signal -> other")
    else:
        intent = classify_intent(message_text)
        logger.info(f"Intent classified: {intent.value}")

    return DecisionSignals(
        intent=intent,
        is_greeting=is_greeting,
        is_thanks=is_thanks,
        is_ack=is_ack,
        is_low_signal=is_low_signal,
        is_status_question=is_status_question,
    )


def _resolve_action(
    *,
    routing: dict[str, bool],
    state: str,
    signals: DecisionSignals,
    is_pending_status_question: bool,
    style_reference: bool,
    out_of_domain_signal: bool,
    rag_confident: bool,
) -> DecisionOutcome:
    if routing["allow_bot_reply"] and (signals.is_greeting or signals.is_thanks):
        return DecisionOutcome("smalltalk")
    if routing["allow_bot_reply"] and state == ConversationState.PENDING.value and is_pending_status_question:
        return DecisionOutcome("pending_status")
    if routing["allow_bot_reply"] and signals.is_status_question:
        return DecisionOutcome("bot_status")
    if routing["allow_bot_reply"] and out_of_domain_signal and not rag_confident:
        return DecisionOutcome("out_of_domain")
    if routing["allow_bot_reply"] and style_reference:
        return DecisionOutcome("style_reference")
    if _should_escalate_to_pending(routing, signals.intent):
        return DecisionOutcome("escalate")
    if should_escalate(signals.intent) and not routing["allow_handover_create"]:
        return DecisionOutcome("pending_escalation")
    if is_rejection(signals.intent):
        return DecisionOutcome("rejection")
    if routing["allow_bot_reply"]:
        return DecisionOutcome("ai_response")
    return DecisionOutcome("unknown_state")


def is_handover_status_question(text: str) -> bool:
    """Detect 'did you forward / when manager replies' questions in pending state."""
    if not text:
        return False

    normalized = text.strip().casefold()
    keywords = [
        "передал",
        "передали",
        "передано",
        "заявк",
        "менеджер",
        "админ",
        "администратор",
        "когда ответ",
        "когда ответит",
        "не отвеч",
        "не отвечает",
        "почему не отвеч",
        "почему молч",
        "молч",
        "тишин",
        "сколько ждать",
        "ждать",
        "ответит",
        "взял",
        "взяли",
        "беру",
    ]
    return any(k in normalized for k in keywords)


BOOKING_REQUEST_KEYWORDS = [
    "запис",
    "запись",
    "запишите",
    "записаться",
    "бронь",
    "окошк",
    "свободн",
]

BOOKING_CANCEL_KEYWORDS = [
    "не надо запис",
    "не хочу запис",
    "передумал",
    "передумала",
    "не буду запис",
    "отмена записи",
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
DATE_PATTERN = re.compile(
    r"\b(?:сегодня|завтра|послезавтра|понедель\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскрес\w*|утром|днем|днём|вечером)\b",
    re.IGNORECASE,
)
NAME_PATTERN = re.compile(r"\bменя зовут\s+([a-zа-яё-]{2,})", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-\(\)]{8,}\d")


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip().casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _detect_llm_guard_topics(response_text: str) -> list[str]:
    normalized = _normalize_text(response_text)
    if not normalized:
        return []
    hits: list[str] = []
    for topic, keywords in LLM_GUARD_TOPICS.items():
        if any(keyword in normalized for keyword in keywords):
            hits.append(topic)
    return hits


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


def _is_booking_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _contains_any(normalized, BOOKING_REQUEST_KEYWORDS)


def _is_booking_cancel(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _contains_any(normalized, BOOKING_CANCEL_KEYWORDS)


def _extract_service_hint(text: str, client_slug: str | None) -> str | None:
    if not text or not client_slug:
        return None
    match = semantic_service_match(text, client_slug)
    if not match or match.action != "match":
        return None
    canonical_name = match.canonical_name
    if isinstance(canonical_name, str) and canonical_name.strip():
        return canonical_name.strip()
    return None


def _extract_datetime(text: str) -> str | None:
    if not text:
        return None
    time_match = TIME_PATTERN.search(text)
    if time_match:
        return time_match.group(0)
    date_match = DATE_PATTERN.search(text)
    if date_match:
        return date_match.group(0)
    return None


BOOKING_INFO_QUESTION_TYPES = {"pricing", "hours", "duration"}
INFO_INTENTS = {"pricing", "hours", "duration", "location"}


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


def _get_conversation_context(conversation: Conversation) -> dict:
    context = conversation.context or {}
    if isinstance(context, dict):
        return dict(context)
    return {}


def _set_conversation_context(conversation: Conversation, context: dict) -> None:
    conversation.context = context


def _record_decision_trace(conversation: Conversation, trace: dict) -> None:
    context = _get_conversation_context(conversation)
    payload = dict(trace)
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    existing = context.get(DECISION_TRACE_KEY)
    if isinstance(existing, list):
        trace_list = [item for item in existing if isinstance(item, dict)]
    elif isinstance(existing, dict):
        trace_list = [existing]
    else:
        trace_list = []
    trace_list.append(payload)
    if len(trace_list) > 12:
        trace_list = trace_list[-12:]
    context[DECISION_TRACE_KEY] = trace_list
    _set_conversation_context(conversation, context)


def _get_context_manager(context: dict) -> dict:
    manager = context.get(CONTEXT_MANAGER_KEY) if isinstance(context, dict) else None
    if isinstance(manager, dict):
        return dict(manager)
    return {}


def _set_context_manager(context: dict, manager: dict) -> dict:
    context = dict(context)
    context[CONTEXT_MANAGER_KEY] = manager
    return context


def _increment_context_message_count(manager: dict) -> int:
    value = manager.get("message_count", 0)
    try:
        count = max(0, int(value))
    except (TypeError, ValueError):
        count = 0
    count += 1
    manager["message_count"] = count
    return count


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


def _resolve_current_goal(intent_set: set[str], consult_intent: bool) -> str | None:
    if consult_intent:
        return "consult"
    if "booking" in intent_set:
        return "booking"
    if intent_set & INFO_INTENTS:
        return "info"
    return None


def _get_clarify_attempt_state(manager: dict, intent: str) -> tuple[int, str | None]:
    attempts = manager.get("clarify_attempts")
    if not isinstance(attempts, dict):
        return 0, None
    payload = attempts.get(intent)
    if not isinstance(payload, dict):
        return 0, None
    value = payload.get("count", 0)
    try:
        count = max(0, int(value))
    except (TypeError, ValueError):
        count = 0
    last_at = payload.get("last_at")
    return count, last_at if isinstance(last_at, str) else None


def _set_clarify_attempt(manager: dict, intent: str, count: int, now: datetime) -> dict:
    attempts = manager.get("clarify_attempts")
    attempts_map = dict(attempts) if isinstance(attempts, dict) else {}
    attempts_map[intent] = {"count": max(0, int(count)), "last_at": now.isoformat()}
    manager["clarify_attempts"] = attempts_map
    return manager


def _should_escalate_for_clarify(manager: dict, intent: str) -> bool:
    count, _ = _get_clarify_attempt_state(manager, intent)
    return count >= CLARIFY_MAX_ATTEMPTS


def _register_clarify_attempt(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    intent: str,
    now: datetime,
    reason: str,
) -> int:
    context = _get_conversation_context(conversation)
    manager = _get_context_manager(context)
    count, _ = _get_clarify_attempt_state(manager, intent)
    count += 1
    manager = _set_clarify_attempt(manager, intent, count, now)
    context = _set_context_manager(context, manager)
    _set_conversation_context(conversation, context)
    attempt_payload = {"intent": intent, "count": count, "last_at": now.isoformat()}
    _record_context_manager_decision(
        conversation,
        saved_message,
        decision="clarify_attempt",
        updates={"clarify_attempt": attempt_payload, "clarify_reason": reason},
    )
    if count >= CLARIFY_MAX_ATTEMPTS:
        _update_compact_summary(
            conversation=conversation,
            saved_message=saved_message,
            reason="clarify_limit",
            now=now,
        )
    return count


def _build_compact_summary_text(
    *,
    booking: dict,
    refusal_flags: dict,
    language: str | None,
) -> str:
    parts: list[str] = []
    service = booking.get("service")
    if isinstance(service, str) and service.strip():
        parts.append(f"Услуга: {service.strip()}")
    datetime_pref = booking.get("datetime")
    if isinstance(datetime_pref, str) and datetime_pref.strip():
        parts.append(f"Время: {datetime_pref.strip()}")
    name = booking.get("name")
    if isinstance(name, str) and name.strip():
        parts.append(f"Имя: {name.strip()}")
    if not name and _is_refusal_flag_active(refusal_flags, "name"):
        parts.append("Имя: отказ")
    if _is_refusal_flag_active(refusal_flags, "phone"):
        parts.append("Телефон: отказ")
    if isinstance(language, str) and language and language != "unknown":
        parts.append(f"Язык: {language}")
    return "; ".join(parts).strip()


def _update_compact_summary(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    reason: str,
    now: datetime,
) -> None:
    context = _get_conversation_context(conversation)
    manager = _get_context_manager(context)
    refusal_flags = manager.get("refusal_flags")
    refusal_flags = dict(refusal_flags) if isinstance(refusal_flags, dict) else {}
    booking = _get_booking_context(context)
    language = _resolve_backlog_language(saved_message) if saved_message else "unknown"
    summary_text = _build_compact_summary_text(
        booking=booking,
        refusal_flags=refusal_flags,
        language=language,
    )
    manager["compact_summary"] = {
        "text": summary_text,
        "updated_at": now.isoformat(),
        "reason": reason,
    }
    context = _set_context_manager(context, manager)
    _set_conversation_context(conversation, context)
    if saved_message:
        _update_message_decision_metadata(saved_message, {"summary_updated": reason})
    _record_decision_trace(
        conversation,
        {
            "stage": "context_manager",
            "decision": "summary_updated",
            "reason": reason,
            "summary_text": summary_text,
        },
    )


def _record_context_manager_decision(
    conversation: Conversation,
    saved_message: Message | None,
    *,
    decision: str,
    updates: dict,
) -> None:
    if saved_message and updates:
        _update_message_decision_metadata(saved_message, updates)
    trace = {"stage": "context_manager", "decision": decision}
    trace.update(updates)
    _record_decision_trace(conversation, trace)


def _handle_clarify_limit_escalation(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str,
    saved_message: Message | None,
    source: str,
    allow_handover: bool,
    send_response,
) -> WebhookResponse:
    bot_response = MSG_ESCALATED
    _reset_low_confidence_retry(conversation)
    result_message = f"{source} clarify limit escalation"

    _, reused, telegram_sent = _reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=message_text,
        source=source,
        intent="clarify_limit",
    )
    if reused:
        result_message = f"{source} clarify limit reuse, telegram={'sent' if telegram_sent else 'failed'}"
    elif conversation.state == ConversationState.BOT_ACTIVE.value and allow_handover:
        result = escalate_to_pending(
            db=db,
            conversation=conversation,
            user_message=message_text,
            trigger_type="intent",
            trigger_value="clarify_limit",
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
            result_message = f"{source} clarify limit escalation, telegram={'sent' if telegram_sent else 'failed'}"
        else:
            result_message = f"{source} clarify limit escalation failed: {result.error}"
    else:
        result_message = f"{source} clarify limit escalation skipped (already pending)"

    _record_decision_trace(
        conversation,
        {
            "stage": source,
            "decision": "clarify_limit",
            "intent": "clarify_limit",
            "state": conversation.state,
        },
    )
    _record_message_decision_meta(
        saved_message,
        action="escalate",
        intent="clarify_limit",
        source=source,
        fast_intent=False,
    )
    if saved_message:
        _update_message_decision_metadata(saved_message, {"clarify_limit": True})
    save_message(db, conversation.id, conversation.client_id, role="assistant", content=bot_response)
    sent = send_response(bot_response)
    if not sent:
        result_message = f"{result_message}; response_send=failed"
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


def _attach_llm_cache_flag(trace: dict, timing_context: dict | None) -> dict:
    if timing_context and "llm_cache_hit" in timing_context:
        trace["llm_cache_hit"] = timing_context["llm_cache_hit"]
    return trace


def _get_low_confidence_retry_count(context: dict) -> int:
    value = context.get("low_confidence_retry_count", 0) if isinstance(context, dict) else 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _set_low_confidence_retry_count(context: dict, count: int) -> dict:
    context = dict(context)
    context["low_confidence_retry_count"] = max(0, int(count))
    return context


def _reset_low_confidence_retry(conversation: Conversation) -> None:
    context = _get_conversation_context(conversation)
    if context.get("low_confidence_retry_count"):
        context = _set_low_confidence_retry_count(context, 0)
        _set_conversation_context(conversation, context)
    conversation.retry_offered_at = None


def _get_handover_confirmation(context: dict) -> dict | None:
    confirmation = context.get("handover_confirmation") if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_handover_confirmation(context: dict, confirmation: dict | None) -> dict:
    context = dict(context)
    if confirmation:
        context["handover_confirmation"] = confirmation
    else:
        context.pop("handover_confirmation", None)
    return context


def _is_handover_confirmation_active(confirmation: dict, now: datetime) -> bool:
    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=HANDOVER_CONFIRM_WINDOW_MINUTES)


def _get_reengage_confirmation(context: dict) -> dict | None:
    confirmation = context.get(REENGAGE_CONFIRM_KEY) if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_reengage_confirmation(context: dict, confirmation: dict | None) -> dict:
    context = dict(context)
    if confirmation:
        context[REENGAGE_CONFIRM_KEY] = confirmation
    else:
        context.pop(REENGAGE_CONFIRM_KEY, None)
    return context


def _is_reengage_confirmation_active(confirmation: dict, now: datetime) -> bool:
    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=REENGAGE_CONFIRM_WINDOW_MINUTES)


def _get_asr_confirmation(context: dict) -> dict | None:
    confirmation = context.get(ASR_CONFIRM_KEY) if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_asr_confirmation(context: dict, confirmation: dict | None) -> dict:
    context = dict(context)
    if confirmation:
        context[ASR_CONFIRM_KEY] = confirmation
    else:
        context.pop(ASR_CONFIRM_KEY, None)
    return context


def _is_asr_confirmation_active(confirmation: dict, now: datetime) -> bool:
    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=ASR_CONFIRM_WINDOW_MINUTES)


def _get_booking_context(context: dict) -> dict:
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        return dict(booking)
    return {}


def _set_booking_context(context: dict, booking: dict) -> dict:
    context = dict(context)
    context["booking"] = booking
    return context


def _set_service_hint(context: dict, service: str, now: datetime) -> dict:
    context = dict(context)
    context[SERVICE_HINT_KEY] = service
    context[SERVICE_HINT_AT_KEY] = now.isoformat()
    return context


def _clear_service_hint(context: dict) -> dict:
    context = dict(context)
    context.pop(SERVICE_HINT_KEY, None)
    context.pop(SERVICE_HINT_AT_KEY, None)
    return context


def _get_recent_service_hint(context: dict, now: datetime) -> str | None:
    if not isinstance(context, dict):
        return None
    value = context.get(SERVICE_HINT_KEY)
    if not value:
        return None
    timestamp_raw = context.get(SERVICE_HINT_AT_KEY)
    if not timestamp_raw:
        return None
    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except (TypeError, ValueError):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if (now - timestamp) > timedelta(minutes=SERVICE_HINT_WINDOW_MINUTES):
        return None
    return str(value).strip() or None


BOOKING_SLOT_ORDER = ("service", "datetime", "name")


def _is_blocked_slot_message(message_text: str) -> bool:
    return is_opt_out_message(message_text) or is_frustration_message(message_text)


def _is_noise_slot_message(message_text: str) -> bool:
    return (
        is_low_signal_message(message_text)
        or is_acknowledgement_message(message_text)
        or is_greeting_message(message_text)
        or is_thanks_message(message_text)
        or is_bot_status_question(message_text)
        or is_human_request_message(message_text)
    )


def _clean_name_candidate(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s-]", " ", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _validate_service_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    extracted = _extract_service_hint(message_text, client_slug)
    if extracted:
        return extracted
    return None


def _validate_datetime_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    extracted = _extract_datetime(message_text)
    if extracted:
        return extracted
    return None


def _validate_name_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    if _is_noise_slot_message(message_text):
        return None
    if _extract_service_hint(message_text, client_slug) or _extract_datetime(message_text):
        return None
    name_match = NAME_PATTERN.search(message_text)
    if name_match:
        candidate = name_match.group(1)
    elif not allow_freeform:
        return None
    else:
        candidate = message_text
    cleaned = _clean_name_candidate(candidate)
    if not cleaned:
        return None
    if any(char.isdigit() for char in cleaned):
        return None
    normalized = _normalize_text(cleaned)
    tokens = normalized.split()
    if not tokens or len(tokens) > 3:
        return None
    if any(len(token) < 2 for token in tokens):
        return None
    return cleaned


BOOKING_SLOT_VALIDATORS = {
    "service": _validate_service_slot,
    "datetime": _validate_datetime_slot,
    "name": _validate_name_slot,
}


def _is_booking_related_message(message_text: str, client_slug: str | None) -> bool:
    if not message_text:
        return False
    if _is_booking_request(message_text):
        return True
    refusal_flags = detect_refusal_flags(message_text)
    if refusal_flags.get("name") or refusal_flags.get("phone"):
        return True
    if _extract_service_hint(message_text, client_slug) or _extract_datetime(message_text):
        return True
    if _validate_name_slot(message_text, allow_freeform=True, client_slug=client_slug):
        return True
    return False


def _apply_booking_slot(
    booking: dict,
    slot_key: str,
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> dict:
    if booking.get(slot_key):
        return booking
    validator = BOOKING_SLOT_VALIDATORS.get(slot_key)
    if not validator:
        return booking
    value = validator(message_text, allow_freeform=allow_freeform, client_slug=client_slug)
    if value:
        booking[slot_key] = value
    return booking


BRANCH_SELECTION_KEY = "branch_selection"
BRANCH_CONTEXT_KEY = "branch_id"
MSG_BRANCH_SELECTED = "Отлично, выбрали филиал {branch_name}. Чем могу помочь?"


def _coerce_uuid(value) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _get_branch_selection(context: dict) -> dict | None:
    selection = context.get(BRANCH_SELECTION_KEY) if isinstance(context, dict) else None
    if isinstance(selection, dict):
        return dict(selection)
    return None


def _set_branch_selection(context: dict, selection: dict | None) -> dict:
    context = dict(context)
    if selection:
        context[BRANCH_SELECTION_KEY] = selection
    else:
        context.pop(BRANCH_SELECTION_KEY, None)
    return context


def _get_user_metadata(user: User) -> dict:
    metadata = user.user_metadata if isinstance(user.user_metadata, dict) else {}
    return dict(metadata)


def _get_user_branch_preference(user: User) -> UUID | None:
    metadata = _get_user_metadata(user)
    return _coerce_uuid(metadata.get(BRANCH_CONTEXT_KEY))


def _set_user_branch_preference(user: User, branch_id: UUID) -> None:
    metadata = _get_user_metadata(user)
    metadata[BRANCH_CONTEXT_KEY] = str(branch_id)
    user.user_metadata = metadata


def _get_active_branches(db: Session, client_id) -> list[Branch]:
    return (
        db.query(Branch)
        .filter(Branch.client_id == client_id, Branch.is_active == True)
        .order_by(Branch.name.asc())
        .all()
    )


def _build_branch_prompt(branches: list[Branch]) -> str:
    lines = ["Пожалуйста, выберите филиал:"]
    for idx, branch in enumerate(branches, start=1):
        label = branch.name or branch.slug or f"Филиал {idx}"
        lines.append(f"{idx}) {label}")
    lines.append("Ответьте номером или названием филиала.")
    return "\n".join(lines)


def _build_branch_selection(branches: list[Branch], now: datetime) -> dict:
    return {
        "options": [str(branch.id) for branch in branches],
        "asked_at": now.isoformat(),
    }


def _match_branch_choice(
    message_text: str,
    branches: list[Branch],
    selection: dict | None,
) -> tuple[Branch | None, bool]:
    normalized = _normalize_text(message_text)
    if not normalized:
        return None, False

    if normalized.isdigit():
        index = int(normalized)
        options = selection.get("options") if isinstance(selection, dict) else None
        if isinstance(options, list) and 1 <= index <= len(options):
            target_id = _coerce_uuid(options[index - 1])
            if target_id:
                for branch in branches:
                    if branch.id == target_id:
                        return branch, True
        if 1 <= index <= len(branches):
            return branches[index - 1], True

    for branch in branches:
        name_norm = _normalize_text(branch.name or "")
        slug_norm = _normalize_text(branch.slug or "")
        if name_norm and name_norm in normalized:
            return branch, False
        if slug_norm and slug_norm in normalized:
            return branch, False
    return None, False


def _is_branch_only_message(message_text: str, branch: Branch, selected_by_index: bool) -> bool:
    normalized = _normalize_text(message_text)
    if not normalized:
        return False
    if selected_by_index and normalized.isdigit():
        return True
    if branch.name and normalized == _normalize_text(branch.name):
        return True
    if branch.slug and normalized == _normalize_text(branch.slug):
        return True
    return False


def _apply_branch_selection(
    *,
    conversation: Conversation,
    user: User,
    branch: Branch,
    context: dict,
    remember_branch: bool,
) -> None:
    updated_context = dict(context)
    updated_context[BRANCH_CONTEXT_KEY] = str(branch.id)
    updated_context.pop(BRANCH_SELECTION_KEY, None)
    _set_conversation_context(conversation, updated_context)
    conversation.branch_id = branch.id
    if remember_branch:
        _set_user_branch_preference(user, branch.id)


def _update_booking_from_message(booking: dict, message_text: str, *, client_slug: str | None) -> dict:
    booking = dict(booking)
    last_question = booking.get("last_question")
    if _is_blocked_slot_message(message_text):
        return booking

    if last_question in BOOKING_SLOT_ORDER:
        booking = _apply_booking_slot(
            booking,
            last_question,
            message_text,
            allow_freeform=True,
            client_slug=client_slug,
        )

    for slot_key in BOOKING_SLOT_ORDER:
        booking = _apply_booking_slot(
            booking,
            slot_key,
            message_text,
            allow_freeform=False,
            client_slug=client_slug,
        )

    return booking


def _update_booking_from_messages(
    booking: dict,
    messages: list[str],
    *,
    client_slug: str | None,
) -> dict:
    updated = dict(booking)
    for message in messages:
        updated = _update_booking_from_message(updated, message, client_slug=client_slug)
    return updated


def _next_booking_prompt(booking: dict, *, refusal_flags: dict | None = None) -> tuple[dict, str | None]:
    booking = dict(booking)
    if not booking.get("service"):
        booking["last_question"] = "service"
        return booking, MSG_BOOKING_ASK_SERVICE
    if not booking.get("datetime"):
        booking["last_question"] = "datetime"
        return booking, MSG_BOOKING_ASK_DATETIME
    if not booking.get("name"):
        if _is_refusal_flag_active(refusal_flags, "name"):
            booking["last_question"] = None
            return booking, None
        booking["last_question"] = "name"
        return booking, MSG_BOOKING_ASK_NAME
    booking["last_question"] = None
    return booking, None


def _combine_sidecar(primary: str, sidecar: str | None) -> str:
    if not sidecar:
        return primary
    return f"{sidecar}\n\n{primary}"


MULTI_INTENT_LABELS = {
    "booking": "записи",
    "pricing": "цене",
    "duration": "длительности",
    "location": "адресу",
    "hours": "часам работы",
    "other": "другому вопросу",
}


def _format_multi_intent_followup(primary: str, secondary: list[str]) -> str | None:
    if not primary:
        return None
    labels = []
    for intent in secondary:
        label = MULTI_INTENT_LABELS.get(intent)
        if label:
            labels.append(label)
    if not labels:
        return "Есть ещё вопрос — уточните, пожалуйста."
    label_text = ", ".join(labels)
    if primary == "booking":
        return f"По {label_text} отвечу после записи."
    return f"Ещё был вопрос по {label_text}. Уточните, пожалуйста."


def _build_booking_summary(booking: dict, *, refusal_flags: dict | None = None) -> str:
    service = booking.get("service") or "не указано"
    datetime_pref = booking.get("datetime") or "не указано"
    name = booking.get("name")
    name_refused = _is_refusal_flag_active(refusal_flags, "name")
    if not name and name_refused:
        name_value = "отказ"
    else:
        name_value = name or "не указано"
    summary = f"Запись: услуга={service}; дата/время={datetime_pref}; имя={name_value}."
    if _is_refusal_flag_active(refusal_flags, "phone"):
        summary = f"{summary} Телефон: отказ."
    return summary


def _demo_salon_escalation_gate(messages: list[str]):
    for message in messages:
        decision = get_demo_salon_decision(message)
        if decision and decision.action == "escalate":
            return decision
    return None


def _demo_salon_price_sidecar(messages: list[str]) -> tuple[str | None, str | None]:
    for message in messages:
        price_reply = get_demo_salon_price_reply(message)
        if price_reply:
            return price_reply, get_demo_salon_price_item(message)
    return None, None


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


def _get_policy_type(client: Client | None) -> str | None:
    if not client or not isinstance(client.config, dict):
        return None
    policy = client.config.get("policy")
    if isinstance(policy, dict):
        policy_type = policy.get("type") or policy.get("policy_type")
        if isinstance(policy_type, str) and policy_type.strip():
            return policy_type.strip()
    legacy = client.config.get("policy_type")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    # Legacy fallback to preserve behavior until policy config is set.
    if client.name == "demo_salon":
        return "demo_salon"
    return None


def _get_policy_handler(client: Client | None) -> dict | None:
    policy_type = _get_policy_type(client)
    if not policy_type:
        return None
    return _POLICY_HANDLERS.get(policy_type)


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
        if handover.status == "active":
            conversation.state = ConversationState.MANAGER_ACTIVE.value
        else:
            conversation.state = ConversationState.PENDING.value
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


def _get_client_webhook_secret(settings: ClientSettings | None) -> str | None:
    if not settings:
        return None
    secret = getattr(settings, "webhook_secret", None)
    if not secret:
        return None
    cleaned = str(secret).strip()
    return cleaned or None


def _get_request_webhook_secret(request: Request) -> str | None:
    header_secret = request.headers.get("X-Webhook-Secret")
    if header_secret:
        return header_secret.strip()
    query_secret = request.query_params.get("webhook_secret")
    if query_secret:
        return query_secret.strip()
    return None


async def _process_outbox_rows(
    db: Session,
    rows: list[dict],
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, int]:
    results = {"claimed": len(rows), "sent": 0, "failed": 0, "retry_scheduled": 0}
    if not rows:
        return results

    picked_at = datetime.now(timezone.utc)
    pick_info: dict[str, dict[str, object]] = {}
    for row in rows:
        outbox_id = row.get("id")
        if not outbox_id:
            continue
        payload_json = row.get("payload_json") or {}
        created_at = row.get("created_at")
        conversation_id = row.get("conversation_id")
        outbox_id_str = str(outbox_id)
        pick_info[outbox_id_str] = {
            "picked_at": picked_at,
            "created_at": created_at,
            "conversation_id": conversation_id,
            "client_slug": payload_json.get("client_slug"),
        }
        logger.info(
            "Outbox picked",
            extra={
                "context": {
                    "outbox_id": outbox_id_str,
                    "conversation_id": str(conversation_id) if conversation_id else None,
                    "client_slug": payload_json.get("client_slug"),
                    "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
                    "outbox_picked_at": picked_at.isoformat(),
                }
            },
        )

    def _log_outbox_done(outbox_id: str, *, error: str | None = None) -> None:
        info = pick_info.get(outbox_id, {})
        done_at = datetime.now(timezone.utc)
        created_at = info.get("created_at")
        picked_at_info = info.get("picked_at")
        wait_ms = None
        process_ms = None
        if isinstance(created_at, datetime) and isinstance(picked_at_info, datetime):
            wait_ms = (picked_at_info - created_at).total_seconds() * 1000
        if isinstance(picked_at_info, datetime):
            process_ms = (done_at - picked_at_info).total_seconds() * 1000
        context = {
            "outbox_id": outbox_id,
            "conversation_id": str(info.get("conversation_id")) if info.get("conversation_id") else None,
            "client_slug": info.get("client_slug"),
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
            "outbox_picked_at": picked_at_info.isoformat() if isinstance(picked_at_info, datetime) else picked_at_info,
            "outbox_done_at": done_at.isoformat(),
            "wait_ms": round(wait_ms, 2) if wait_ms is not None else None,
            "process_ms": round(process_ms, 2) if process_ms is not None else None,
        }
        if error:
            context["error"] = error
        logger.info("Outbox done", extra={"context": context})

    def _row_has_media(row: dict) -> bool:
        payload_json = row.get("payload_json") or {}
        try:
            payload = WebhookRequest.model_validate(payload_json)
        except Exception:
            return False
        message_type = (payload.body.messageType or "").strip().lower()
        return bool(payload.body.mediaData) or (message_type and message_type != "text")

    async def _process_single_row(row: dict, *, conversation_id: str) -> None:
        outbox_id = row.get("id")
        if not outbox_id:
            return
        payload_json = row.get("payload_json") or {}
        try:
            payload = WebhookRequest.model_validate(payload_json)
        except Exception as exc:
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="FAILED",
                last_error=f"invalid_payload:{exc}"[:500],
                next_attempt_at=None,
            )
            results["failed"] += 1
            return

        try:
            outbox_ids = [str(outbox_id)]
            timing_start = time.monotonic()
            response = await _handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=UUID(conversation_id),
                outbox_ids=outbox_ids,
                outbox_created_at=row.get("created_at"),
            )
            if not response.success:
                raise RuntimeError(response.message)
            logger.info(
                "Outbox timing",
                extra={
                    "context": {
                        "outbox_id": str(outbox_id),
                        "outbox_ids": outbox_ids,
                        "conversation_id": conversation_id,
                        "client_slug": payload.client_slug,
                        "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                    }
                },
            )
            _log_outbox_done(str(outbox_id))
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="SENT",
                last_error=None,
                next_attempt_at=None,
            )
            results["sent"] += 1
        except Exception as exc:
            try:
                db.rollback()
            except Exception as rollback_exc:
                logger.warning(
                    "Outbox rollback failed",
                    extra={"context": {"error": str(rollback_exc)}},
                )
            logger.info(
                "Outbox timing",
                extra={
                    "context": {
                        "outbox_id": str(outbox_id),
                        "outbox_ids": [str(outbox_id)],
                        "conversation_id": conversation_id,
                        "client_slug": payload.client_slug,
                        "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                        "error": str(exc),
                    }
                },
            )
            _log_outbox_done(str(outbox_id), error=str(exc))
            now = datetime.now(timezone.utc)
            attempts = int(row.get("attempts") or 0)
            if attempts >= max_attempts:
                mark_outbox_status(
                    db,
                    outbox_id=outbox_id,
                    status="FAILED",
                    last_error=str(exc)[:500],
                    next_attempt_at=None,
                )
                results["failed"] += 1
                return
            backoff = retry_backoff_seconds * (2 ** max(attempts - 1, 0))
            next_attempt_at = now + timedelta(seconds=backoff)
            mark_outbox_status(
                db,
                outbox_id=outbox_id,
                status="PENDING",
                last_error=str(exc)[:500],
                next_attempt_at=next_attempt_at,
            )
            results["retry_scheduled"] += 1

    batches: dict[str, list[dict]] = {}
    for row in rows:
        conversation_id = row.get("conversation_id")
        if not conversation_id:
            continue
        batches.setdefault(str(conversation_id), []).append(row)

    for conversation_id, batch in batches.items():
        batch_sorted = sorted(
            batch,
            key=lambda r: r.get("created_at")
            if isinstance(r.get("created_at"), datetime)
            else datetime.min.replace(tzinfo=timezone.utc),
        )
        if any(_row_has_media(row) for row in batch_sorted):
            for row in batch_sorted:
                await _process_single_row(row, conversation_id=str(conversation_id))
            logger.info(
                "Outbox processed (media rows)",
                extra={"context": {"conversation_id": conversation_id, "count": len(batch_sorted)}},
            )
            continue

        window_seconds = _get_outbox_window_merge_seconds()
        grouped_batches = _split_outbox_batches(batch_sorted, window_seconds)
        for group in grouped_batches:
            outbox_ids = [row.get("id") for row in group]
            message_texts = []
            forwarded_in_batch = False
            group_created_at = None
            for row in group:
                payload_json = row.get("payload_json") or {}
                try:
                    payload = WebhookRequest.model_validate(payload_json)
                except Exception:
                    continue
                created_at = _coerce_outbox_created_at(row.get("created_at"))
                if created_at and (group_created_at is None or created_at > group_created_at):
                    group_created_at = created_at
                if payload.body.metadata and payload.body.metadata.forwarded_to_telegram:
                    forwarded_in_batch = True
                text = payload.body.message or ""
                if text.strip():
                    message_texts.append(text.strip())

            base_payload = WebhookRequest.model_validate(group[-1].get("payload_json") or {})
            combined_text = " ".join(message_texts).strip()
            if combined_text:
                base_payload.body.message = combined_text
            if forwarded_in_batch and base_payload.body.metadata:
                base_payload.body.metadata.forwarded_to_telegram = True

            logger.info(
                "Outbox processing start",
                extra={
                    "context": {
                        "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                        "conversation_id": conversation_id,
                        "attempts": group[-1].get("attempts"),
                        "coalesced_count": len(group),
                        "window_merge_seconds": window_seconds,
                    }
                },
            )

            try:
                timing_start = time.monotonic()
                response = await _handle_webhook_payload(
                    base_payload,
                    db,
                    provided_secret=None,
                    enforce_secret=False,
                    skip_persist=True,
                    conversation_id=UUID(conversation_id),
                    batch_messages=message_texts,
                    outbox_ids=[str(oid) for oid in outbox_ids if oid],
                    outbox_created_at=group_created_at,
                )
                if not response.success:
                    raise RuntimeError(response.message)
                logger.info(
                    "Outbox timing",
                    extra={
                        "context": {
                            "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                            "conversation_id": conversation_id,
                            "client_slug": base_payload.client_slug,
                            "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                        }
                    },
                )
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _log_outbox_done(str(outbox_id))
                for outbox_id in outbox_ids:
                    if outbox_id:
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="SENT",
                            last_error=None,
                            next_attempt_at=None,
                        )
                results["sent"] += len(outbox_ids)
                logger.info(
                    "Outbox processed",
                    extra={"context": {"conversation_id": conversation_id, "coalesced_count": len(group)}},
                )
            except Exception as exc:
                try:
                    db.rollback()
                except Exception as rollback_exc:
                    logger.warning(
                        "Outbox rollback failed",
                        extra={"context": {"error": str(rollback_exc)}},
                    )
                logger.info(
                    "Outbox timing",
                    extra={
                        "context": {
                            "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                            "conversation_id": conversation_id,
                            "client_slug": base_payload.client_slug,
                            "outbox_total_ms": round((time.monotonic() - timing_start) * 1000, 2),
                            "error": str(exc),
                        }
                    },
                )
                for outbox_id in outbox_ids:
                    if outbox_id:
                        _log_outbox_done(str(outbox_id), error=str(exc))
                now = datetime.now(timezone.utc)
                for row in group:
                    outbox_id = row.get("id")
                    if not outbox_id:
                        continue
                    attempts = int(row.get("attempts") or 0)
                    if attempts >= max_attempts:
                        mark_outbox_status(
                            db,
                            outbox_id=outbox_id,
                            status="FAILED",
                            last_error=str(exc)[:500],
                            next_attempt_at=None,
                        )
                        results["failed"] += 1
                        continue
                    backoff = retry_backoff_seconds * (2 ** max(attempts - 1, 0))
                    next_attempt_at = now + timedelta(seconds=backoff)
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="PENDING",
                        last_error=str(exc)[:500],
                        next_attempt_at=next_attempt_at,
                    )
                    results["retry_scheduled"] += 1
                logger.error(
                    "Outbox processing failed",
                    extra={
                        "context": {
                            "conversation_id": conversation_id,
                            "error": str(exc),
                            "coalesced_count": len(group),
                        }
                    },
                )

    return results


@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    """Debug endpoint to see raw request."""
    body = await request.json()
    logger.debug(f"DEBUG webhook body: {body}")
    return {"received": body}


@router.post("/webhook/{client_slug}", response_model=WebhookResponse)
async def handle_webhook_direct(client_slug: str, request: Request, db: Session = Depends(get_db)):
    """Handle direct ChatFlow webhook without wrapper."""
    parsed = await _parse_webhook_request(request, client_slug=client_slug)
    if isinstance(parsed, WebhookResponse):
        return parsed

    provided_secret = _get_request_webhook_secret(request)
    client = db.query(Client).filter(Client.name == parsed.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{parsed.client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    expected_secret = _get_client_webhook_secret(settings)
    if expected_secret:
        if not provided_secret or provided_secret != expected_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
    elif not provided_secret:
        alert_warning("Webhook secret missing", {"client_slug": parsed.client_slug})

    return await _handle_webhook_payload(
        parsed,
        db,
        provided_secret=provided_secret,
        enforce_secret=False,
        enqueue_only=True,
    )


@router.get("/webhook/{client_slug}")
async def handle_webhook_probe(client_slug: str):
    """Health probe for ChatFlow UI checks; real webhooks must use POST."""
    return {"ok": True, "message": "Use POST with JSON payload", "client_slug": client_slug}


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(payload: WebhookRequest, http_request: Request, db: Session = Depends(get_db)):
    """Handle legacy webhook wrapper (same format as ChatFlow webhook)."""
    provided_secret = _get_request_webhook_secret(http_request)
    return await _handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=True,
        enqueue_only=True,
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

    # Get client by slug
    client = db.query(Client).filter(Client.name == payload.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{payload.client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    if enforce_secret:
        expected_secret = _get_client_webhook_secret(settings)
        if expected_secret:
            if not provided_secret or provided_secret != expected_secret:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
        elif not provided_secret:
            alert_warning("Webhook secret missing", {"client_slug": payload.client_slug})

    body = payload.body
    metadata = body.metadata

    if not metadata or not metadata.remoteJid:
        return WebhookResponse(success=False, message="Missing metadata.remoteJid")

    remote_jid = metadata.remoteJid
    message_text = body.message or ""
    media_info = _extract_media_info(body)
    if not message_text.strip() and media_info and media_info.caption:
        message_text = media_info.caption
    message_type = (body.messageType or "").strip()
    has_media = bool(body.mediaData) or (message_type and message_type.lower() != "text")
    is_media_without_text = has_media and not message_text.strip()
    message_id = metadata.messageId

    if not message_text and not is_media_without_text:
        return WebhookResponse(success=False, message="Empty message")
    if is_media_without_text:
        media_label = message_type.lower() if message_type else "media"
        message_text = f"[{media_label}]"

    batch_messages_provided = batch_messages is not None
    batch_messages = _coerce_batch_messages(message_text, batch_messages)

    timing_context: dict = {"client_slug": payload.client_slug, "remote_jid": remote_jid}
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

    if skip_persist:
        if not conversation_id:
            return WebhookResponse(success=False, message="Missing conversation_id")
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return WebhookResponse(success=False, message="Conversation not found")
        user = db.query(User).filter(User.id == conversation.user_id).first()
        if not user:
            return WebhookResponse(success=False, message="User not found")
        timing_context["conversation_id"] = str(conversation.id)
        if message_id:
            saved_message = _find_message_by_message_id(db, client.id, message_id)
        if not saved_message and outbox_created_at:
            saved_message = _find_message_by_conversation_created_at(
                db,
                conversation.id,
                outbox_created_at,
                message_text=message_text,
            )
        if media_info and saved_message:
            saved_media = saved_message.message_metadata.get("media") if isinstance(saved_message.message_metadata, dict) else None
            media_decision = _deserialize_media_decision(
                saved_media.get("decision") if isinstance(saved_media, dict) else None
            )
        if media_info and media_decision is None and media_policy:
            media_decision = await _evaluate_media_decision(
                media=media_info,
                client_id=client.id,
                remote_jid=remote_jid,
                policy=media_policy,
                redis_client=media_redis_client,
                count_rate_limit=count_rate_limit,
            )
    else:
        if await is_duplicate_message_id(db=db, client_id=client.id, message_id=message_id):
            logger.info(f"Duplicate message_id skipped: {message_id}")
            return WebhookResponse(success=True, message="Duplicate message_id", conversation_id=None, bot_response=None)
        if not message_id:
            message_id = build_inbound_message_id(
                None,
                remote_jid,
                metadata.timestamp if metadata else None,
                message_text,
            )
            if metadata:
                metadata.messageId = message_id

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

        if enqueue_only:
            if (
                conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]
                and conversation.telegram_topic_id
            ):
                bot_token, chat_id = get_telegram_credentials(db, client.id)
                if bot_token and chat_id:
                    already_forwarded = bool(metadata and metadata.forwarded_to_telegram)
                    if not already_forwarded:
                        telegram = TelegramService(bot_token)
                        forward_result = None
                        if media_info and media_decision and media_decision.allowed and (media_policy or {}).get("forward_to_telegram"):
                            storage_path = None
                            if media_policy and media_policy.get("store_media"):
                                if saved_message and isinstance(saved_message.message_metadata, dict):
                                    storage_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")
                                if not storage_path:
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
                            caption = _build_media_caption(message_text, media_info)
                            forward_result = _send_telegram_media(
                                telegram=telegram,
                                chat_id=chat_id,
                                topic_id=conversation.telegram_topic_id,
                                media=media_info,
                                caption=caption,
                                stored_path=storage_path,
                            )
                        else:
                            forward_result = telegram.send_message(
                                chat_id=chat_id,
                                text=f"👤 <b>Клиент:</b> {message_text}",
                                message_thread_id=conversation.telegram_topic_id,
                            )
                        if forward_result and forward_result.get("ok"):
                            if metadata:
                                metadata.forwarded_to_telegram = True
                            logger.info(
                                "Fast-forwarded inbound message to Telegram",
                                extra={
                                    "context": {
                                        "conversation_id": str(conversation.id),
                                        "state": conversation.state,
                                        "telegram_topic_id": conversation.telegram_topic_id,
                                    }
                                },
                            )
                        else:
                            logger.warning(
                                "Fast-forward to Telegram failed",
                                extra={
                                    "context": {
                                        "conversation_id": str(conversation.id),
                                        "state": conversation.state,
                                        "telegram_topic_id": conversation.telegram_topic_id,
                                        "error": forward_result.get("description") if forward_result else None,
                                    }
                                },
                            )
            inbound_message_id = build_inbound_message_id(
                message_id, remote_jid, metadata.timestamp if metadata else None, message_text
            )
            payload_json = payload.model_dump(exclude_none=True)
            enqueued = enqueue_outbox_message(
                db,
                client_id=client.id,
                conversation_id=conversation.id,
                inbound_message_id=inbound_message_id,
                payload_json=payload_json,
            )
            if enqueued:
                logger.info(
                    "Outbox enqueued",
                    extra={
                        "context": {
                            "client_slug": payload.client_slug,
                            "conversation_id": str(conversation.id),
                            "inbound_message_id": inbound_message_id,
                        }
                    },
                )
            else:
                logger.info(
                    "Outbox duplicate skipped",
                    extra={
                        "context": {
                            "client_slug": payload.client_slug,
                            "conversation_id": str(conversation.id),
                            "inbound_message_id": inbound_message_id,
                        }
                    },
                )
            db.commit()
            return WebhookResponse(success=True, message="Accepted", conversation_id=conversation.id, bot_response=None)

    routing = _get_routing_policy(conversation.state)

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
    previous_last_message_at = conversation.last_message_at
    conversation.last_message_at = now
    context = _get_conversation_context(conversation)
    context_manager = _get_context_manager(context)
    message_count = _increment_context_message_count(context_manager)
    context_manager, refusal_flags, refusal_events = _update_refusal_flags(
        context_manager,
        message_text=message_text,
        now=now,
        client_slug=payload.client_slug,
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
    if message_count == SUMMARY_MESSAGE_THRESHOLD:
        _update_compact_summary(
            conversation=conversation,
            saved_message=saved_message,
            reason="message_threshold",
            now=now,
        )
        context = _get_conversation_context(conversation)
    current_goal = context_manager.get("current_goal") if isinstance(context_manager, dict) else None

    # 4.5 Branch routing (instance_id -> branch, or ask user)
    branch_mode = (
        settings.branch_resolution_mode if settings and settings.branch_resolution_mode else "hybrid"
    )
    remember_branch = (
        settings.remember_branch_preference
        if settings and settings.remember_branch_preference is not None
        else True
    )
    context = _get_conversation_context(conversation)
    branch_id = conversation.branch_id or _coerce_uuid(context.get(BRANCH_CONTEXT_KEY))
    if not branch_id and remember_branch:
        branch_id = _get_user_branch_preference(user)

    if branch_id:
        if conversation.branch_id != branch_id:
            conversation.branch_id = branch_id
        if context.get(BRANCH_CONTEXT_KEY) != str(branch_id):
            context[BRANCH_CONTEXT_KEY] = str(branch_id)
            _set_conversation_context(conversation, context)
        if remember_branch and _get_user_branch_preference(user) != branch_id:
            _set_user_branch_preference(user, branch_id)
    else:
        instance_id = metadata.instanceId if metadata else None
        if branch_mode in {"by_instance", "hybrid"} and instance_id:
            branch = (
                db.query(Branch)
                .filter(
                    Branch.client_id == client.id,
                    Branch.instance_id == instance_id,
                    Branch.is_active == True,
                )
                .first()
            )
            if branch:
                _apply_branch_selection(
                    conversation=conversation,
                    user=user,
                    branch=branch,
                    context=context,
                    remember_branch=remember_branch,
                )

        if not conversation.branch_id and branch_mode in {"ask_user", "hybrid"}:
            branches = _get_active_branches(db, client.id)
            if len(branches) == 1:
                _apply_branch_selection(
                    conversation=conversation,
                    user=user,
                    branch=branches[0],
                    context=context,
                    remember_branch=remember_branch,
                )
            elif len(branches) > 1 and conversation.state == ConversationState.BOT_ACTIVE.value:
                selection = _get_branch_selection(context)
                if selection:
                    matched_branch, selected_by_index = _match_branch_choice(
                        message_text, branches, selection
                    )
                    if matched_branch:
                        _apply_branch_selection(
                            conversation=conversation,
                            user=user,
                            branch=matched_branch,
                            context=context,
                            remember_branch=remember_branch,
                        )
                        if _is_branch_only_message(message_text, matched_branch, selected_by_index):
                            bot_response = MSG_BRANCH_SELECTED.format(
                                branch_name=matched_branch.name
                                or matched_branch.slug
                                or "филиал"
                            )
                            save_message(
                                db, conversation.id, client.id, role="assistant", content=bot_response
                            )
                            sent = _send_response(bot_response)
                            result_message = (
                                "Branch selected (prompted)" if sent else "Branch selection response failed"
                            )
                            db.commit()
                            return WebhookResponse(
                                success=True,
                                message=result_message,
                                conversation_id=conversation.id,
                                bot_response=bot_response,
                            )
                    else:
                        prompt = _build_branch_prompt(branches)
                        context = _set_branch_selection(
                            context, _build_branch_selection(branches, now)
                        )
                        _set_conversation_context(conversation, context)
                        save_message(db, conversation.id, client.id, role="assistant", content=prompt)
                        sent = _send_response(prompt)
                        result_message = (
                            "Branch selection requested (retry)"
                            if sent
                            else "Branch selection prompt failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=prompt,
                        )
                else:
                    prompt = _build_branch_prompt(branches)
                    context = _set_branch_selection(context, _build_branch_selection(branches, now))
                    _set_conversation_context(conversation, context)
                    save_message(db, conversation.id, client.id, role="assistant", content=prompt)
                    sent = _send_response(prompt)
                    result_message = (
                        "Branch selection requested" if sent else "Branch selection prompt failed"
                    )
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=prompt,
                    )

    # 5. Check session timeout - reset mute if no messages for 24h+
    bot_response = None
    sent = False
    result_message = None
    intent = None

    # Reset mute if new session (no messages for 24h+)
    if previous_last_message_at:
        last_seen = previous_last_message_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        time_since_last = now - last_seen
        if time_since_last > timedelta(hours=SESSION_TIMEOUT_HOURS):
            # New session - reset mute
            conversation.bot_status = "active"
            conversation.bot_muted_until = None
            conversation.no_count = 0
            conversation.context = {}
            logger.info(f"Session reset: {time_since_last} since last message")

    # 6. Check if bot is muted - but still forward to topic
    is_muted = False
    if conversation.bot_status == "muted" or (conversation.bot_muted_until and conversation.bot_muted_until > now):
        is_muted = True

    forwarded_to_telegram = bool(metadata.forwarded_to_telegram) if metadata else False

    # 7. Forward to topic if pending/manager_active (always, even if muted)
    if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value] and not forwarded_to_telegram:
        if conversation.telegram_topic_id:
            bot_token, chat_id = get_telegram_credentials(db, client.id)
            if bot_token and chat_id:
                telegram = TelegramService(bot_token)
                forward_result = None
                caption = None
                if has_media and media_info and media_decision and media_decision.allowed and (media_policy or {}).get("forward_to_telegram"):
                    stored_path = None
                    if saved_message and isinstance(saved_message.message_metadata, dict):
                        stored_path = (saved_message.message_metadata.get("media") or {}).get("storage_path")
                    caption = _build_media_caption(message_text, media_info)
                    forward_result = _send_telegram_media(
                        telegram=telegram,
                        chat_id=chat_id,
                        topic_id=conversation.telegram_topic_id,
                        media=media_info,
                        caption=caption,
                        stored_path=stored_path,
                    )
                elif not has_media:
                    forward_result = telegram.send_message(
                        chat_id=chat_id,
                        text=f"👤 <b>Клиент:</b> {message_text}",
                        message_thread_id=conversation.telegram_topic_id,
                    )
                if forward_result and forward_result.get("ok"):
                    if metadata:
                        metadata.forwarded_to_telegram = True
                    if (
                        transcript
                        and caption
                        and _is_voice_note(media_info)
                        and saved_message
                        and transcript.strip() == caption.strip()
                    ):
                        _update_message_media_metadata(saved_message, {"transcript_forwarded": True})
                elif forward_result:
                    logger.warning(
                        "Forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") or forward_result.get("error"),
                            }
                        },
                    )

    if (
        transcript
        and media_info
        and _is_voice_note(media_info)
        and conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]
        and conversation.telegram_topic_id
    ):
        already_forwarded = False
        if saved_message and isinstance(saved_message.message_metadata, dict):
            media_meta = saved_message.message_metadata.get("media") or {}
            already_forwarded = bool(media_meta.get("transcript_forwarded"))
        if not already_forwarded:
            bot_token, chat_id = get_telegram_credentials(db, client.id)
            if bot_token and chat_id:
                telegram = TelegramService(bot_token)
                forward_result = telegram.send_message(
                    chat_id=chat_id,
                    text=f"📝 <b>Транскрипт:</b> {transcript}",
                    message_thread_id=conversation.telegram_topic_id,
                )
                if forward_result and forward_result.get("ok") and saved_message:
                    _update_message_media_metadata(saved_message, {"transcript_forwarded": True})
                elif forward_result:
                    logger.warning(
                        "Transcript forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") or forward_result.get("error"),
                            }
                        },
                    )

    # 8. Manager active → bot must stay silent (only forwarding above)
    if conversation.state == ConversationState.MANAGER_ACTIVE.value:
        _record_decision_trace(
            conversation,
            {
                "stage": "routing",
                "decision": "manager_active_silent",
                "state": conversation.state,
            },
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message="Manager active, message forwarded",
            conversation_id=conversation.id,
            bot_response=None,
        )

    # 8.1 Detect signals early for re-engage and mute decisions.
    batch_messages = _coerce_batch_messages(message_text, batch_messages)
    signal_messages = list(batch_messages)
    opt_out_in_batch = any(is_opt_out_message(msg) for msg in signal_messages)
    booking_signal, booking_block_meta = _evaluate_booking_signal(
        signal_messages,
        client_slug=payload.client_slug,
        message_text=message_text,
    )
    context = _get_conversation_context(conversation)
    booking_state = _get_booking_context(context)
    booking_active = bool(booking_state.get("active"))
    reengage_override = False

    if conversation.state == ConversationState.BOT_ACTIVE.value:
        reengage_confirmation = _get_reengage_confirmation(context)
        if reengage_confirmation:
            if not _is_reengage_confirmation_active(reengage_confirmation, now):
                context = _set_reengage_confirmation(context, None)
                _set_conversation_context(conversation, context)
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    context = _set_reengage_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    conversation.bot_status = "active"
                    conversation.bot_muted_until = None
                    conversation.no_count = 0
                    reengage_override = True
                    stored_messages = reengage_confirmation.get("booking_messages")
                    if isinstance(stored_messages, list) and stored_messages:
                        batch_messages = _coerce_batch_messages("", stored_messages)
                        signal_messages = list(batch_messages)
                        booking_signal, booking_block_meta = _evaluate_booking_signal(
                            signal_messages,
                            client_slug=payload.client_slug,
                            message_text=signal_messages[-1] if signal_messages else message_text,
                        )
                    _record_decision_trace(
                        conversation,
                        {
                            "decision": "reengage_confirmed",
                            "state": conversation.state,
                            "booking_signal": booking_signal,
                            "opt_out_in_batch": opt_out_in_batch,
                        },
                    )
                elif decision == "no":
                    context = _set_reengage_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    mute_first, mute_second = get_mute_settings(db, client.id)
                    if conversation.no_count == 0:
                        conversation.bot_muted_until = now + timedelta(minutes=mute_first)
                        conversation.no_count = 1
                    else:
                        conversation.bot_muted_until = now + timedelta(hours=mute_second)
                        conversation.no_count += 1
                    _record_decision_trace(
                        conversation,
                        {
                            "decision": "reengage_declined",
                            "state": conversation.state,
                            "booking_signal": booking_signal,
                            "opt_out_in_batch": opt_out_in_batch,
                        },
                    )
                    bot_response = MSG_REENGAGE_DECLINED
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
                    result_message = "Re-engage declined" if sent else "Re-engage decline send failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )
                else:
                    reengage_confirmation["asked_at"] = now.isoformat()
                    context = _set_reengage_confirmation(context, reengage_confirmation)
                    _set_conversation_context(conversation, context)
                    _record_decision_trace(
                        conversation,
                        {
                            "decision": "reengage_confirmation_repeat",
                            "state": conversation.state,
                            "booking_signal": booking_signal,
                            "opt_out_in_batch": opt_out_in_batch,
                        },
                    )
                    bot_response = MSG_REENGAGE_CONFIRM
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
                    result_message = "Re-engage confirmation requested" if sent else "Re-engage confirmation failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

    if conversation.state == ConversationState.BOT_ACTIVE.value and opt_out_in_batch and booking_signal:
        confirmation_payload = {
            "asked_at": now.isoformat(),
            "booking_messages": signal_messages,
        }
        context = _set_reengage_confirmation(context, confirmation_payload)
        if booking_active:
            booking_state["active"] = False
            context = _set_booking_context(context, booking_state)
        _set_conversation_context(conversation, context)
        _record_decision_trace(
            conversation,
            {
                "decision": "reengage_confirmation_requested",
                "state": conversation.state,
                "booking_signal": booking_signal,
                "opt_out_in_batch": opt_out_in_batch,
            },
        )
        bot_response = MSG_REENGAGE_CONFIRM
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
        result_message = "Re-engage confirmation requested" if sent else "Re-engage confirmation failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    # 9. If muted - don't respond unless booking flow should re-engage.
    is_muted = conversation.bot_status == "muted" or (conversation.bot_muted_until and conversation.bot_muted_until > now)
    if is_muted:
        if (booking_signal or booking_active) and not opt_out_in_batch:
            conversation.bot_status = "active"
            conversation.bot_muted_until = None
            conversation.no_count = 0
            is_muted = False
            _record_decision_trace(
                conversation,
                {
                    "decision": "mute_cleared_for_booking",
                    "state": conversation.state,
                    "booking_signal": booking_signal,
                    "booking_active": booking_active,
                    "opt_out_in_batch": opt_out_in_batch,
                },
            )
        else:
            _record_decision_trace(
                conversation,
                {
                    "decision": "muted_skip",
                    "state": conversation.state,
                    "booking_signal": booking_signal,
                    "booking_active": booking_active,
                    "opt_out_in_batch": opt_out_in_batch,
                },
            )
            db.commit()
            return WebhookResponse(
                success=True,
                message="Bot muted, forwarded to topic" if conversation.telegram_topic_id else "Bot muted",
                conversation_id=conversation.id,
                bot_response=None,
            )

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
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = _send_response(bot_response)
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
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = "ASR confirmation requested" if sent else "ASR confirmation send failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if conversation.state == ConversationState.PENDING.value:
        if is_opt_out_message(message_text):
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
            _record_message_decision_meta(
                saved_message,
                action="rejection",
                intent="opt_out",
                source="pending",
                fast_intent=False,
            )
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = "Pending opt-out handled" if sent else "Pending opt-out send failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

        bot_response = MSG_PENDING_WAIT
        _record_decision_trace(
            conversation,
            {
                "stage": "routing",
                "decision": "pending_wait",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="pending_wait",
            intent=None,
            source="pending",
            fast_intent=False,
        )
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
        result_message = "Pending wait response sent" if sent else "Pending wait response failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if has_media:
        if not media_info:
            bot_response = MSG_MEDIA_UNSUPPORTED
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = "Media response sent" if sent else "Media response failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    # 9.0 Debounce bursty inputs: only the latest message triggers bot logic.
    append_user_message = True
    if conversation.state in [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value] and not batch_messages_provided:
        # Persist user message + last_message_at before waiting.
        db.commit()

        debounce_enabled, _, ttl_seconds, redis_url, socket_timeout_seconds = _get_debounce_settings()
        buffer_enabled, max_buffer_messages = _get_message_buffer_settings()
        redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)

        if debounce_enabled and buffer_enabled and redis_client:
            await _buffer_user_message(
                redis_client=redis_client,
                client_id=str(client.id),
                remote_jid=remote_jid,
                message_text=message_text,
                ttl_seconds=ttl_seconds,
                max_messages=max_buffer_messages,
            )

        should_process = await should_process_debounced_message(
            client_id=str(client.id),
            remote_jid=remote_jid,
            message_id=message_id,
            redis_client=redis_client,
        )
        if not should_process:
            logger.info(
                "Debounced intermediate message",
                extra={"context": {"remote_jid": remote_jid, "message_id": message_id}},
            )
            return WebhookResponse(
                success=True,
                message="Debounced: skipped intermediate message",
                conversation_id=conversation.id,
                bot_response=None,
            )

        if debounce_enabled and buffer_enabled and redis_client:
            buffered_messages = await _drain_buffered_messages(
                redis_client=redis_client,
                client_id=str(client.id),
                remote_jid=remote_jid,
            )
            if buffered_messages:
                logger.info(
                    "Debounce buffer drained",
                    extra={
                        "context": {
                            "remote_jid": remote_jid,
                            "message_id": message_id,
                            "buffered_count": len(buffered_messages),
                        }
                    },
                )
                message_text = " ".join(buffered_messages)
                if not batch_messages_provided:
                    batch_messages = _coerce_batch_messages(message_text, buffered_messages)
                append_user_message = False

        # Re-check state after waiting: manager could take the request during debounce pause.
        db.refresh(conversation)
        now = datetime.now(timezone.utc)
        if conversation.state == ConversationState.MANAGER_ACTIVE.value:
            return WebhookResponse(
                success=True,
                message="Manager active (after debounce), message forwarded",
                conversation_id=conversation.id,
                bot_response=None,
            )
        if conversation.bot_status == "muted" or (conversation.bot_muted_until and conversation.bot_muted_until > now):
            signal_messages = _coerce_batch_messages(message_text, batch_messages)
            opt_out_in_batch = any(is_opt_out_message(msg) for msg in signal_messages)
            booking_signal, booking_block_meta = _evaluate_booking_signal(
                signal_messages,
                client_slug=payload.client_slug,
                message_text=message_text,
            )
            context = _get_conversation_context(conversation)
            booking_active = bool(_get_booking_context(context).get("active"))
            reengage_confirmation = _get_reengage_confirmation(context)
            if reengage_confirmation and _is_reengage_confirmation_active(reengage_confirmation, now):
                conversation.bot_status = "active"
                conversation.bot_muted_until = None
                conversation.no_count = 0
            elif (booking_signal or booking_active) and not opt_out_in_batch:
                conversation.bot_status = "active"
                conversation.bot_muted_until = None
                conversation.no_count = 0
            else:
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "routing",
                        "decision": "muted_skip_after_debounce",
                        "state": conversation.state,
                        "booking_signal": booking_signal,
                        "booking_active": booking_active,
                        "opt_out_in_batch": opt_out_in_batch,
                    },
                )
                return WebhookResponse(
                    success=True,
                    message="Bot muted (after debounce), forwarded to topic"
                    if conversation.telegram_topic_id
                    else "Bot muted (after debounce)",
                    conversation_id=conversation.id,
                    bot_response=None,
                )

    # 9.02 Pending handover confirmation before other flows.
    if conversation.state == ConversationState.BOT_ACTIVE.value:
        context = _get_conversation_context(conversation)
        confirmation = _get_handover_confirmation(context)
        if confirmation:
            if not _is_handover_confirmation_active(confirmation, now):
                context = _set_handover_confirmation(context, None)
                _set_conversation_context(conversation, context)
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    context = _set_handover_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    _reset_low_confidence_retry(conversation)

                    escalation_message = confirmation.get("user_message") or message_text
                    _, reused, telegram_sent = _reuse_active_handover(
                        db=db,
                        conversation=conversation,
                        user=user,
                        message=escalation_message,
                        source="handover_confirmation",
                        intent="low_confidence",
                    )

                    if reused:
                        bot_response = MSG_ESCALATED
                        result_message = (
                            f"Handover confirmed (reused), telegram={'sent' if telegram_sent else 'failed'}"
                        )
                    else:
                        esc_result = escalate_to_pending(
                            db=db,
                            conversation=conversation,
                            user_message=escalation_message,
                            trigger_type="intent",
                            trigger_value="low_confidence",
                        )

                        if esc_result.ok:
                            handover = esc_result.value
                            telegram_sent = send_telegram_notification(
                                db=db,
                                handover=handover,
                                conversation=conversation,
                                user=user,
                                message=escalation_message,
                            )
                            bot_response = MSG_ESCALATED
                            result_message = (
                                f"Handover confirmed, telegram={'sent' if telegram_sent else 'failed'}"
                            )
                        else:
                            bot_response = MSG_AI_ERROR
                            result_message = f"Handover confirm escalation failed: {esc_result.error}"

                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
                    if not sent:
                        result_message = f"{result_message}; response_send=failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

                if decision == "no":
                    context = _set_handover_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    _reset_low_confidence_retry(conversation)

                    bot_response = MSG_HANDOVER_DECLINED
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
                    result_message = "Handover declined, asked for salon details" if sent else "Handover decline send failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

                context = _set_handover_confirmation(context, None)
                _set_conversation_context(conversation, context)

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

    intent_decomp_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent} if intent_decomp_used else set()
    if intent_decomp_used:
        new_goal = _resolve_current_goal(intent_decomp_set, consult_intent)
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
            _update_compact_summary(
                conversation=conversation,
                saved_message=saved_message,
                reason="intent_change",
                now=now,
            )
            context = _get_conversation_context(conversation)
            current_goal = new_goal
    intent_decomp_has_booking = "booking" in intent_decomp_set
    intent_decomp_info = intent_decomp_set & BOOKING_INFO_QUESTION_TYPES
    if intent_decomp_has_booking:
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
            else:
                booking_block_meta = {
                    "booking_blocked_reason": "intent_decomp_missing" if not intent_decomp_used else "intent_decomp_no_booking",
                }
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

    policy_handler = _get_policy_handler(client)
    policy_type = policy_handler.get("policy_type") if policy_handler else None
    multi_intent_primary = None
    multi_intent_secondary: list[str] = []
    multi_intent_followup = None
    multi_intent_booking_followup = None
    multi_intent_other_followup = None

    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and opt_out_in_batch
        and not booking_signal
    ):
        mute_first, mute_second = get_mute_settings(db, client.id)
        if conversation.no_count == 0:
            conversation.bot_muted_until = now + timedelta(minutes=mute_first)
            conversation.no_count = 1
            bot_response = MSG_MUTED_TEMP
            trace_decision = "muted_first"
        else:
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
        _record_message_decision_meta(
            saved_message,
            action="rejection",
            intent="opt_out",
            source="opt_out",
            fast_intent=False,
        )
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
        result_message = f"Muted (opt-out #{conversation.no_count})" if sent else "Opt-out response failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    # 9.03 Policy escalation gate (hard signals).
    if not bypass_domain_flows and policy_handler and routing["allow_truth_gate_reply"]:
        policy_t0 = time.monotonic()
        escalation_gate = policy_handler.get("escalation_gate")
        decision = escalation_gate(booking_messages) if escalation_gate else None
        if decision:
            bot_response = decision.response
            bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
            _reset_low_confidence_retry(conversation)

            result_message = "Policy reply sent"
            if decision.action == "escalate":
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=message_text,
                    source="policy_gate",
                    intent=decision.intent,
                )
                if reused:
                    result_message = f"Policy reuse, telegram={'sent' if telegram_sent else 'failed'}"
                elif conversation.state == ConversationState.BOT_ACTIVE.value:
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
                        result_message = f"Policy escalation, telegram={'sent' if telegram_sent else 'failed'}"
                    else:
                        result_message = f"Policy escalation failed: {result.error}"
                else:
                    result_message = "Policy escalation skipped (already pending)"

            _record_decision_trace(
                conversation,
                {
                    "stage": "policy_gate",
                    "decision": decision.action,
                    "intent": decision.intent,
                    "state": conversation.state,
                    "booking_wants_flow": booking_wants_flow,
                    "policy_type": policy_type,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action=decision.action,
                intent=decision.intent,
                source="policy_gate",
                fast_intent=False,
            )
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            _log_timing(
                "policy_gate_ms",
                (time.monotonic() - policy_t0) * 1000,
                {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "escalation"},
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
            {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "escalation"},
        )

    early_domain_intent = DomainIntent.UNKNOWN
    early_domain_meta: dict = {}
    early_out_of_domain = False
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not bypass_domain_flows
        and message_text
    ):
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
            early_out_of_domain = bool(int(early_domain_meta.get("out_hits") or 0) > 0)

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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
        result_message = "Out-of-domain early response sent" if sent else "Out-of-domain early response failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    consult_decision = None
    if routing["allow_bot_reply"] and not bypass_domain_flows and message_text:
        consult_blocked = bool(booking_wants_flow or booking_active or booking_signal)
        if intent_decomp_set & {"booking", "pricing", "duration", "location", "hours"}:
            consult_blocked = True
        if not consult_blocked:
            consult_decision = build_consult_reply(
                message_text,
                client_slug=payload.client_slug,
                intent_decomp=intent_decomp_payload,
            )

    if consult_decision:
        consult_meta = consult_decision.meta if isinstance(consult_decision.meta, dict) else {}
        consult_meta = dict(consult_meta)
        if consult_decision.action == "reply":
            consult_questions = consult_meta.get("consult_questions")
            if isinstance(consult_questions, list) and consult_questions:
                context = _get_conversation_context(conversation)
                context_manager = _get_context_manager(context)
                if _should_escalate_for_clarify(context_manager, "consult"):
                    clarify_count, _ = _get_clarify_attempt_state(context_manager, "consult")
                    _record_context_manager_decision(
                        conversation,
                        saved_message,
                        decision="clarify_limit",
                        updates={
                            "clarify_attempt": {"intent": "consult", "count": clarify_count},
                            "clarify_reason": "consult",
                            "clarify_limit": True,
                        },
                    )
                    consult_meta["clarify_limit"] = True
                    consult_decision = DemoSalonDecision(
                        action="escalate",
                        response=MSG_ESCALATED,
                        intent="clarify_limit",
                        meta=consult_meta,
                    )
                else:
                    _register_clarify_attempt(
                        conversation=conversation,
                        saved_message=saved_message,
                        intent="consult",
                        now=now,
                        reason="consult",
                    )
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

            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
        _reset_low_confidence_retry(conversation)
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
    if (
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

        if booking_active and _is_booking_cancel(message_text):
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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

            if prompt:
                context_manager = _get_context_manager(context)
                if _should_escalate_for_clarify(context_manager, "booking"):
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
                    )
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
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
                    bot_response = multi_reply
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
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
                    if not sent:
                        result_message = f"{result_message}; response_send=failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

        service_matcher = policy_handler.get("service_matcher")
        service_decision = (
            service_matcher(
                message_text,
                client_slug=payload.client_slug,
                intent_decomp=intent_decomp_payload,
            )
            if service_matcher
            else None
        )
        if service_decision:
            bot_response = service_decision.response
            bot_response = _combine_sidecar(bot_response, multi_intent_other_followup)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

    if routing["allow_bot_reply"]:
        llm_primary_result = generate_bot_response(
            db,
            conversation,
            message_text,
            payload.client_slug,
            append_user_message=append_user_message,
            pending_hint=conversation.state == ConversationState.PENDING.value,
            timing_context=timing_context,
        )
        if not llm_primary_result.ok:
            llm_primary_failed = True
            llm_primary_reason = "ai_error"
        else:
            response_text, confidence = llm_primary_result.value
            if confidence == "bot_inactive":
                llm_primary_failed = True
                llm_primary_reason = "bot_inactive"
            elif response_text and confidence != "low_confidence":
                blocked_topics = _detect_llm_guard_topics(response_text)
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
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
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
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = _send_response(bot_response)
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
                if price_item:
                    context = _get_conversation_context(conversation)
                    context = _set_service_hint(context, price_item, now)
                    _set_conversation_context(conversation, context)
                else:
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
            bot_response = decision.response
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
    out_of_domain_signal = domain_out_hits > 0
    _log_timing(
        "intent_ms",
        (time.monotonic() - intent_t0) * 1000,
        {
            "intent": intent.value,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
        },
    )

    rag_confident = False

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
        },
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = (
                f"Escalation reused ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
            )
        else:
            # Escalate using state_service (atomic transition)
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
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = _send_response(bot_response)
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
                gen_result = generate_bot_response(
                    db,
                    conversation,
                    message_text,
                    payload.client_slug,
                    append_user_message=append_user_message,
                    pending_hint=conversation.state == ConversationState.PENDING.value,
                    timing_context=timing_context,
                )
                if gen_result.ok and gen_result.value[0]:
                    bot_response = gen_result.value[0]
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
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
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = f"Muted (rejection #{conversation.no_count})"

    elif decision.action == "ai_response":
        # Bot responds: normal mode OR pending (bot helps while waiting)
        llm_primary_used = False
        gen_result = llm_primary_result
        if gen_result is None:
            gen_result = generate_bot_response(
                db,
                conversation,
                message_text,
                payload.client_slug,
                append_user_message=append_user_message,
                pending_hint=conversation.state == ConversationState.PENDING.value,
                timing_context=timing_context,
            )

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
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
                    if not out_of_domain_signal:
                        semantic_result = semantic_service_match(message_text, payload.client_slug)
                        if not semantic_result:
                            rewrite_query = rewrite_for_service_match(message_text, payload.client_slug)
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
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = _send_response(bot_response)
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
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = _send_response(bot_response)
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
                            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                            sent = _send_response(bot_response)
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
                            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                            sent = _send_response(bot_response)
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
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = _send_response(bot_response)
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
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
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
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
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
