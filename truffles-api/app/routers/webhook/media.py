"""Media intake, validation, storage, ASR, and forwarding helpers."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx

from app.models import Client, Message
from app.schemas.webhook import WebhookBody
from app.services.ai_service import normalize_for_matching, transcribe_audio_with_fallback
from app.services.alert_service import alert_warning
from app.services.telegram_service import TelegramService


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
    from . import _legacy as legacy

    overrides = {}
    if client and isinstance(client.config, dict):
        overrides = client.config.get("media") if isinstance(client.config.get("media"), dict) else {}

    max_size_cfg = overrides.get("max_size_mb") if isinstance(overrides.get("max_size_mb"), dict) else {}
    rate_cfg = overrides.get("rate_limit") if isinstance(overrides.get("rate_limit"), dict) else {}

    max_sizes_mb = {
        "photo": _coerce_int(
            overrides.get("max_photo_mb", max_size_cfg.get("photo")),
            legacy.MEDIA_MAX_DEFAULT_MB["photo"],
            min_value=1,
        ),
        "audio": _coerce_int(
            overrides.get("max_audio_mb", max_size_cfg.get("audio")),
            legacy.MEDIA_MAX_DEFAULT_MB["audio"],
            min_value=1,
        ),
        "document": _coerce_int(
            overrides.get("max_document_mb", max_size_cfg.get("document")),
            legacy.MEDIA_MAX_DEFAULT_MB["document"],
            min_value=1,
        ),
    }

    rate_limit = {
        "count": _coerce_int(rate_cfg.get("count"), legacy.MEDIA_RATE_LIMIT_DEFAULTS["count"], min_value=1),
        "window_seconds": _coerce_int(
            rate_cfg.get("window_seconds"), legacy.MEDIA_RATE_LIMIT_DEFAULTS["window_seconds"], min_value=30
        ),
        "daily_count": _coerce_int(
            rate_cfg.get("daily_count"), legacy.MEDIA_RATE_LIMIT_DEFAULTS["daily_count"], min_value=1
        ),
        "bytes_mb": _coerce_int(rate_cfg.get("bytes_mb"), legacy.MEDIA_RATE_LIMIT_DEFAULTS["bytes_mb"], min_value=1),
        "block_seconds": _coerce_int(
            rate_cfg.get("block_seconds"), legacy.MEDIA_RATE_LIMIT_DEFAULTS["block_seconds"], min_value=60
        ),
    }

    storage_dir = overrides.get("storage_dir") or legacy.MEDIA_STORAGE_DEFAULT_DIR
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
    from . import _legacy as legacy

    raw = (raw_type or "").strip().lower()
    if raw in legacy.MEDIA_TYPE_ALIASES:
        return legacy.MEDIA_TYPE_ALIASES[raw]
    if mime:
        if mime.startswith("image/"):
            return "photo"
        if mime.startswith("audio/"):
            return "audio"
        if mime in {"application/pdf", "application/msword"} or mime.startswith("application/vnd"):
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
    from . import _legacy as legacy

    enabled = legacy._is_env_enabled(os.environ.get("AUDIO_TRANSCRIPTION_ENABLED"), default=False)
    raw_max_mb = os.environ.get("AUDIO_TRANSCRIPTION_MAX_MB", str(legacy.AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB))
    try:
        max_mb = float(raw_max_mb)
    except (TypeError, ValueError):
        max_mb = legacy.AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB
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
    from . import _legacy as legacy

    cleaned = (text or "").strip()
    compact = re.sub(r"\s+", "", cleaned)
    if len(compact) < legacy.ASR_LOW_CONFIDENCE_MIN_CHARS:
        return True
    words = _count_words(cleaned)
    if (
        duration_seconds is not None
        and duration_seconds > legacy.ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS
        and words < legacy.ASR_LOW_CONFIDENCE_MIN_WORDS
    ):
        return True
    if _non_letter_ratio(cleaned) >= legacy.ASR_LOW_CONFIDENCE_NON_LETTER_RATIO:
        return True
    return False


def _is_style_reference_request(text: str | None, *, has_media: bool) -> bool:
    from . import _legacy as legacy

    normalized = normalize_for_matching(text or "")
    if not normalized:
        return False
    if not has_media and not any(token in normalized for token in legacy.STYLE_REFERENCE_HINT_TOKENS):
        return False
    return any(pattern.search(normalized) for pattern in legacy.STYLE_REFERENCE_PATTERNS)


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
    (
        enabled,
        max_bytes,
        model,
        language,
        primary_provider,
        fallback_provider,
        timeout_seconds,
        min_chars,
    ) = _get_transcription_settings()
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
    from . import _legacy as legacy

    now_ts = time.time()
    _purge_media_rate_cache(now_ts)

    block_key = f"{key_base}:block"
    block_until = _media_rate_cache.get(block_key, {}).get("expires_at", 0)
    if block_until and block_until > now_ts:
        retry_after = int(block_until - now_ts)
        return MediaDecision(
            allowed=False,
            reason="rate_limited",
            response=legacy.MSG_MEDIA_RATE_LIMIT,
            retry_after=retry_after,
        )

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
        return MediaDecision(
            allowed=False,
            reason="rate_limited",
            response=legacy.MSG_MEDIA_RATE_LIMIT,
            retry_after=rate_limit["block_seconds"],
        )

    if window["bytes"] > rate_limit["bytes_mb"] * 1024 * 1024:
        _media_rate_cache[block_key] = {"expires_at": now_ts + rate_limit["block_seconds"]}
        return MediaDecision(
            allowed=False,
            reason="rate_limited",
            response=legacy.MSG_MEDIA_RATE_LIMIT,
            retry_after=rate_limit["block_seconds"],
        )

    if day["count"] > rate_limit["daily_count"]:
        _media_rate_cache[block_key] = {"expires_at": now_ts + rate_limit["block_seconds"]}
        return MediaDecision(
            allowed=False,
            reason="rate_limited",
            response=legacy.MSG_MEDIA_RATE_LIMIT,
            retry_after=rate_limit["block_seconds"],
        )

    return MediaDecision(allowed=True)


async def _check_media_rate_limit(
    *,
    redis_client,
    key_base: str,
    size_bytes: int,
    rate_limit: dict,
) -> MediaDecision:
    from . import _legacy as legacy

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
        legacy.logger.warning("Media rate limit redis check failed", extra={"context": {"error": str(exc)}})
        return _check_media_rate_limit_fallback(
            key_base=key_base,
            size_bytes=size_bytes,
            rate_limit=rate_limit,
        )

    if blocked:
        return MediaDecision(allowed=False, reason="rate_limited", response=legacy.MSG_MEDIA_RATE_LIMIT)

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
        legacy.logger.warning("Media rate limit redis update failed", extra={"context": {"error": str(exc)}})
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
            legacy.logger.warning("Media rate limit redis block failed", extra={"context": {"error": str(exc)}})
        return MediaDecision(
            allowed=False,
            reason="rate_limited",
            response=legacy.MSG_MEDIA_RATE_LIMIT,
            retry_after=rate_limit["block_seconds"],
        )

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
    from . import _legacy as legacy

    if not policy.get("enabled"):
        return MediaDecision(allowed=False, reason="disabled", response=legacy.MSG_MEDIA_UNSUPPORTED)

    allowed = {
        "photo": policy.get("allow_photo", True),
        "audio": policy.get("allow_audio", True),
        "document": policy.get("allow_document", True),
    }

    if media.media_type not in allowed or not allowed.get(media.media_type, False):
        return MediaDecision(allowed=False, reason="unsupported_type", response=legacy.MSG_MEDIA_UNSUPPORTED)

    max_mb = policy.get("max_size_mb", legacy.MEDIA_MAX_DEFAULT_MB).get(media.media_type, 8)
    max_bytes = max_mb * 1024 * 1024
    size_bytes = media.size_bytes
    if size_bytes is not None and size_bytes > max_bytes:
        return MediaDecision(allowed=False, reason="too_large", response=legacy.MSG_MEDIA_TOO_LARGE)

    if not count_rate_limit:
        return MediaDecision(allowed=True)

    size_for_limit = size_bytes or 0
    decision = await _check_media_rate_limit(
        redis_client=redis_client,
        key_base=f"media:{client_id}:{remote_jid}",
        size_bytes=size_for_limit,
        rate_limit=policy.get("rate_limit", legacy.MEDIA_RATE_LIMIT_DEFAULTS),
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
    from . import _legacy as legacy

    if not policy.get("store_media", True):
        return {"stored": False, "error": "store_disabled"}

    storage_dir = Path(str(policy.get("storage_dir") or legacy.MEDIA_STORAGE_DEFAULT_DIR))
    target_dir = storage_dir / client_slug / str(conversation_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    ext = _guess_extension(media.mime, media.file_name)
    file_id = _safe_media_id(message_id)
    target_path = target_dir / f"{file_id}{ext}"

    max_mb = policy.get("max_size_mb", legacy.MEDIA_MAX_DEFAULT_MB).get(media.media_type, 8)
    max_bytes = min(max_mb * 1024 * 1024, legacy.MEDIA_STORAGE_MAX_BYTES)

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


def _serialize_media_decision(decision: MediaDecision) -> dict:
    return {
        "allowed": bool(decision.allowed),
        "reason": decision.reason,
        "retry_after": decision.retry_after,
    }


def _media_response_for_reason(reason: str | None) -> str | None:
    from . import _legacy as legacy

    if reason == "too_large":
        return legacy.MSG_MEDIA_TOO_LARGE
    if reason == "rate_limited":
        return legacy.MSG_MEDIA_RATE_LIMIT
    if reason in {"unsupported_type", "disabled"}:
        return legacy.MSG_MEDIA_UNSUPPORTED
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
