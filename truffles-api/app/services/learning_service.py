import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client, ClientSettings, Handover, LearnedResponse
from app.services.alert_service import alert_error, alert_warning
from app.services.knowledge_service import (
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    get_embedding,
)
from app.services.runtime_mode_service import is_nonprod_eval_mode

logger = get_logger("learning_service")

MAX_KNOWLEDGE_TEXT_LENGTH = 2000
MIN_QUESTION_LENGTH = 5
MIN_ANSWER_LENGTH = 5
DEFAULT_LEARNING_RETENTION_DAYS = int(os.environ.get("LEARNING_RETENTION_DAYS", "180"))
DEFAULT_ANONYMIZATION_MODE = os.environ.get("LEARNING_ANONYMIZATION_MODE", "redact").strip().lower()
ALLOWED_CONSENT_STATUSES = {"granted", "declined", "unknown"}
ALLOWED_ANONYMIZATION_MODES = {"redact", "strict"}
REDACTION_PHONE_MIN_DIGITS = 9
LOW_VALUE_TEXTS = {
    "ок",
    "окей",
    "ok",
    "okay",
    "ага",
    "угу",
    "да",
    "нет",
    "неа",
    "спасибо",
    "спасибо большое",
    "благодарю",
    "понял",
    "поняла",
    "понятно",
    "ясно",
    "хорошо",
    "принято",
}
PLACEHOLDER_PATTERNS = (
    re.compile(r"^\[[^\]]+\]$"),
    re.compile(r"^клиент отправил", re.IGNORECASE),
    re.compile(r"^файл получил", re.IGNORECASE),
    re.compile(r"^документ получил", re.IGNORECASE),
    re.compile(r"^ошибка вызова вебхука", re.IGNORECASE),
    re.compile(r"^передал", re.IGNORECASE),
    re.compile(r"^передали", re.IGNORECASE),
)

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"\bhttps?://[^\s]+|\bwww\.[^\s]+", re.IGNORECASE)
HANDLE_PATTERN = re.compile(r"@[A-Za-z0-9_]{3,}", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")


@dataclass(frozen=True)
class LearningPolicy:
    consent_status: str
    anonymization_mode: str
    retention_days: int
    allowed: bool


def _normalize_learning_consent(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    normalized = value.strip().lower()
    return normalized if normalized in ALLOWED_CONSENT_STATUSES else "unknown"


def _normalize_anonymization_mode(value: Optional[str]) -> str:
    if not value:
        return DEFAULT_ANONYMIZATION_MODE
    normalized = value.strip().lower()
    if normalized in ALLOWED_ANONYMIZATION_MODES:
        return normalized
    return "off"


def _normalize_retention_days(value: Optional[int]) -> int:
    if value is None:
        return DEFAULT_LEARNING_RETENTION_DAYS
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_LEARNING_RETENTION_DAYS
    return parsed if parsed > 0 else 0


def get_learning_policy(db: Session, client_id: UUID) -> LearningPolicy:
    settings = (
        db.query(ClientSettings)
        .filter(ClientSettings.client_id == client_id)
        .first()
    )
    consent_status = _normalize_learning_consent(
        getattr(settings, "learning_consent_status", None)
    )
    anonymization_mode = _normalize_anonymization_mode(
        getattr(settings, "learning_anonymization_mode", None)
    )
    retention_days = _normalize_retention_days(
        getattr(settings, "learning_retention_days", None)
    )
    allowed = (
        consent_status == "granted"
        and anonymization_mode in ALLOWED_ANONYMIZATION_MODES
        and retention_days > 0
    )
    return LearningPolicy(
        consent_status=consent_status,
        anonymization_mode=anonymization_mode,
        retention_days=retention_days,
        allowed=allowed,
    )


def evaluate_candidate_eligibility(
    policy: LearningPolicy,
    *,
    retention_expires_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> tuple[bool, Optional[str]]:
    current = now or datetime.now(timezone.utc)
    if policy.consent_status != "granted":
        return False, "consent_not_granted"
    if policy.anonymization_mode not in ALLOWED_ANONYMIZATION_MODES:
        return False, "anonymization_disabled"
    if isinstance(retention_expires_at, datetime) and retention_expires_at <= current:
        return False, "retention_expired"
    return True, None


def _redact_phone(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) < REDACTION_PHONE_MIN_DIGITS:
        return match.group(0)
    return "[PHONE]"


def _redact_card(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) < 13 or len(digits) > 19:
        return match.group(0)
    return "[CARD]"


def redact_text(text: str, mode: str) -> tuple[str, dict[str, int]]:
    if not text:
        return "", {}
    if mode not in ALLOWED_ANONYMIZATION_MODES:
        return text, {}

    summary: dict[str, int] = {}
    redacted = text

    def _apply(pattern: re.Pattern, label: str, repl) -> None:
        nonlocal redacted

        def _replace(match: re.Match) -> str:
            replacement = repl(match) if callable(repl) else repl
            if replacement != match.group(0):
                summary[label] = summary.get(label, 0) + 1
            return replacement

        redacted = pattern.sub(_replace, redacted)

    _apply(EMAIL_PATTERN, "email", "[EMAIL]")
    _apply(URL_PATTERN, "url", "[URL]")
    _apply(HANDLE_PATTERN, "handle", "[HANDLE]")
    _apply(PHONE_PATTERN, "phone", _redact_phone)
    _apply(CARD_PATTERN, "card", _redact_card)

    redacted = re.sub(r"\s{2,}", " ", redacted).strip()
    return redacted, summary


def build_retention_expires_at(now: datetime, retention_days: int) -> Optional[datetime]:
    if retention_days <= 0:
        return None
    return now + timedelta(days=retention_days)


def _normalize_text(text: str) -> str:
    cleaned = (text or "").strip().casefold()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _has_letters(text: str) -> bool:
    return bool(re.search(r"[a-zа-я]", text))


def _is_low_value_text(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return True
    if not _has_letters(normalized):
        return True
    if normalized in LOW_VALUE_TEXTS:
        return True
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def _normalize_telegram_identifier(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lstrip("@")


def _split_owner_identifiers(raw_value: Optional[str]) -> list[str]:
    if not raw_value:
        return []
    parts = re.split(r"[\s,]+", raw_value.strip())
    normalized: list[str] = []
    for part in parts:
        if not part:
            continue
        token = _normalize_telegram_identifier(part)
        if token:
            normalized.append(token)
    return normalized


def is_owner_response(
    db: Session,
    client_id: UUID,
    manager_telegram_id: int,
    manager_username: Optional[str] = None,
) -> bool:
    """
    Check if manager is the owner of this client.

    owner_telegram_id в client_settings может быть:
    - "@username"
    - "123456789" (telegram user id)
    """
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if not settings or not settings.owner_telegram_id:
        return False

    owner_ids = _split_owner_identifiers(settings.owner_telegram_id)
    if not owner_ids:
        return False

    manager_id = str(manager_telegram_id) if manager_telegram_id else None
    normalized_username = _normalize_telegram_identifier(manager_username) if manager_username else None

    for owner_id in owner_ids:
        # Prefer numeric ID match when owner_telegram_id is a user/chat id.
        if owner_id.lstrip("-").isdigit():
            if manager_id and manager_id == owner_id:
                return True
            continue

        # Fall back to username match (case-insensitive).
        if normalized_username and normalized_username.lower() == owner_id.lower():
            return True

    if not manager_id and not normalized_username:
        logger.debug("Owner response check: missing manager id/username")
    else:
        logger.debug(
            "Owner response mismatch",
            extra={
                "context": {
                    "owner_ids": owner_ids,
                    "manager_id": manager_id,
                    "manager_username": normalized_username,
                }
            },
        )
    return False


def get_client_slug(db: Session, client_id: UUID) -> Optional[str]:
    """Get client slug (name) for Qdrant filtering."""
    client = db.query(Client).filter(Client.id == client_id).first()
    return client.name if client else None


def _trim_text(text: str) -> str:
    """Trim long text to keep Qdrant payloads bounded."""
    if text is None:
        return ""
    if len(text) <= MAX_KNOWLEDGE_TEXT_LENGTH:
        return text
    return text[:MAX_KNOWLEDGE_TEXT_LENGTH]


def add_to_knowledge(
    db: Session,
    handover: Handover,
    source: str = "learned",
) -> Optional[str]:
    """
    Add manager response to Qdrant knowledge base.

    Returns point_id if successful, None otherwise.
    """
    if not handover.user_message or not handover.manager_response:
        logger.warning("Cannot add to knowledge: missing user_message or manager_response")
        alert_warning(
            "Learning skipped: missing text",
            {"handover_id": str(getattr(handover, "id", None)), "client_id": str(handover.client_id)},
        )
        return None

    policy = get_learning_policy(db, handover.client_id)
    if not policy.allowed:
        logger.info(
            "Learning skipped: consent not granted",
            extra={
                "context": {
                    "handover_id": str(handover.id),
                    "client_id": str(handover.client_id),
                    "consent_status": policy.consent_status,
                    "anonymization_mode": policy.anonymization_mode,
                    "retention_days": policy.retention_days,
                }
            },
        )
        return None

    client_slug = get_client_slug(db, handover.client_id)
    if not client_slug:
        logger.warning(f"Cannot add to knowledge: client_slug not found for {handover.client_id}")
        alert_warning(
            "Learning skipped: client_slug not found",
            {"handover_id": str(getattr(handover, "id", None)), "client_id": str(handover.client_id)},
        )
        return None

    # Format content for indexing
    question_raw = _trim_text(handover.user_message.strip())
    answer_raw = _trim_text(handover.manager_response.strip())
    question, question_redactions = redact_text(question_raw, policy.anonymization_mode)
    answer, answer_redactions = redact_text(answer_raw, policy.anonymization_mode)
    if not question or not answer:
        logger.info(
            "Skipped learning: redaction removed content",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "question_redactions": question_redactions,
                    "answer_redactions": answer_redactions,
                }
            },
        )
        return None
    if len(question) < MIN_QUESTION_LENGTH or len(answer) < MIN_ANSWER_LENGTH:
        logger.info(
            "Skipped learning: text too short",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "question_len": len(question),
                    "answer_len": len(answer),
                }
            },
        )
        alert_warning(
            "Learning skipped: text too short",
            {
                "handover_id": str(handover.id),
                "client_slug": client_slug,
                "question_len": len(question),
                "answer_len": len(answer),
            },
        )
        return None

    if _is_low_value_text(question) or _is_low_value_text(answer):
        logger.info(
            "Skipped learning: low-value content",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "question_preview": question[:80],
                    "answer_preview": answer[:80],
                }
            },
        )
        return None

    if is_nonprod_eval_mode(os.environ) and not (QDRANT_COLLECTION or "").endswith("_ci"):
        logger.warning(
            "Learning blocked: non-prod eval requires _ci collection",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "qdrant_collection": QDRANT_COLLECTION,
                    "learning_mode": "blocked",
                }
            },
        )
        return None

    learning_mode = (os.environ.get("LEARNING_MODE") or "").strip().lower()
    if learning_mode in {"skip", "off", "disabled"}:
        logger.info(
            "Learning skipped by LEARNING_MODE",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "learning_mode": learning_mode,
                }
            },
        )
        return None

    if learning_mode in {"record-only", "record"}:
        point_id = str(uuid.uuid4())
        try:
            db.execute(
                text(
                    "UPDATE handovers "
                    "SET added_to_knowledge = TRUE, knowledge_doc_id = :doc_id "
                    "WHERE id = :handover_id"
                ),
                {"doc_id": point_id, "handover_id": str(handover.id)},
            )
            db.commit()
        except Exception as exc:
            logger.warning(
                "Learning record-only update failed",
                extra={
                    "context": {
                        "handover_id": str(handover.id),
                        "error": str(exc),
                    }
                },
            )
        logger.info(
            "Learning recorded (record-only mode)",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "point_id": point_id,
                    "learning_mode": learning_mode,
                }
            },
        )
        alert_warning(
            "Learning record-only",
            {
                "client_slug": client_slug,
                "handover_id": str(handover.id),
                "point_id": point_id,
                "learning_mode": learning_mode,
            },
        )
        return point_id

    content = f"Вопрос: {question}\nОтвет: {answer}"
    if len(handover.user_message.strip()) > len(question) or len(handover.manager_response.strip()) > len(answer):
        logger.info("Truncated knowledge sample to fit length limits")
    if question_redactions or answer_redactions:
        logger.info(
            "Learning content redacted",
            extra={
                "context": {
                    "handover_id": str(handover.id),
                    "question_redactions": question_redactions,
                    "answer_redactions": answer_redactions,
                }
            },
        )

    try:
        # Get embedding
        embedding = get_embedding(content)

        # Generate point ID
        point_id = str(uuid.uuid4())

        retention_expires_at = build_retention_expires_at(
            datetime.now(timezone.utc),
            policy.retention_days,
        )
        metadata = {
            "client_slug": client_slug,
            "source": source,
            "handover_id": str(handover.id),
            "question": question,
            "answer": answer,
            "learned_from": handover.assigned_to_name or "manager",
            "retention_expires_at": retention_expires_at.isoformat() if retention_expires_at else None,
        }
        if getattr(handover, "branch_id", None):
            metadata["branch_id"] = str(handover.branch_id)
        payload = {"content": content, "metadata": metadata}

        # Upsert to Qdrant
        with httpx.Client(timeout=30.0) as client:
            response = client.put(
                f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points",
                headers={"api-key": QDRANT_API_KEY},
                json={"points": [{"id": point_id, "vector": embedding, "payload": payload}]},
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Qdrant upsert error: {response.status_code} - {response.text}")
                alert_error("Failed to add to knowledge", {"handover_id": str(handover.id), "status": response.status_code})
                return None

            context = {
                "point_id": point_id,
                "client_slug": client_slug,
                "handover_id": str(handover.id),
                "question_len": len(question),
                "answer_len": len(answer),
                "source": source,
            }
            logger.info("Added to knowledge", extra={"context": context})
            alert_warning("Learning success", context)
            return point_id

    except Exception as e:
        logger.error(f"Error adding to knowledge: {e}", exc_info=True)
        alert_error("Learning service error", {"handover_id": str(handover.id), "error": str(e)})
        return None


def add_learned_response_to_knowledge(
    db: Session,
    learned_response: LearnedResponse,
    source: str = "learned",
) -> Optional[str]:
    """Add approved learned response to Qdrant knowledge base."""
    if not learned_response.question_text or not learned_response.response_text:
        logger.warning("Cannot add learned_response: missing text")
        return None

    policy = get_learning_policy(db, learned_response.client_id)
    allowed, reason = evaluate_candidate_eligibility(
        policy,
        retention_expires_at=learned_response.retention_expires_at,
    )
    if not allowed:
        logger.info(
            "Learning skipped: candidate not eligible",
            extra={
                "context": {
                    "learned_response_id": str(learned_response.id),
                    "client_id": str(learned_response.client_id),
                    "reason": reason,
                }
            },
        )
        return None

    client_slug = get_client_slug(db, learned_response.client_id)
    if not client_slug:
        logger.warning(
            "Cannot add learned_response: client_slug not found",
            extra={"context": {"learned_response_id": str(learned_response.id)}},
        )
        return None

    question_raw = _trim_text(learned_response.question_text.strip())
    answer_raw = _trim_text(learned_response.response_text.strip())
    question, question_redactions = redact_text(question_raw, policy.anonymization_mode)
    answer, answer_redactions = redact_text(answer_raw, policy.anonymization_mode)
    if not question or not answer:
        logger.info(
            "Skipped learned_response: redaction removed content",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "learned_response_id": str(learned_response.id),
                    "question_redactions": question_redactions,
                    "answer_redactions": answer_redactions,
                }
            },
        )
        return None
    if len(question) < MIN_QUESTION_LENGTH or len(answer) < MIN_ANSWER_LENGTH:
        logger.info(
            "Skipped learned_response: text too short",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "learned_response_id": str(learned_response.id),
                    "question_len": len(question),
                    "answer_len": len(answer),
                }
            },
        )
        return None

    if _is_low_value_text(question) or _is_low_value_text(answer):
        logger.info(
            "Skipped learned_response: low-value content",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "learned_response_id": str(learned_response.id),
                    "question_preview": question[:80],
                    "answer_preview": answer[:80],
                }
            },
        )
        return None

    if is_nonprod_eval_mode(os.environ) and not (QDRANT_COLLECTION or "").endswith("_ci"):
        logger.warning(
            "Learning blocked: non-prod eval requires _ci collection",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "learned_response_id": str(learned_response.id),
                    "qdrant_collection": QDRANT_COLLECTION,
                    "learning_mode": "blocked",
                }
            },
        )
        return None

    learning_mode = (os.environ.get("LEARNING_MODE") or "").strip().lower()
    if learning_mode in {"skip", "off", "disabled"}:
        logger.info(
            "Learning skipped by LEARNING_MODE",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "learned_response_id": str(learned_response.id),
                    "learning_mode": learning_mode,
                }
            },
        )
        return None

    if learning_mode in {"record-only", "record"}:
        point_id = str(uuid.uuid4())
        learned_response.qdrant_point_id = point_id
        logger.info(
            "Learning recorded (record-only mode)",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "learned_response_id": str(learned_response.id),
                    "point_id": point_id,
                    "learning_mode": learning_mode,
                }
            },
        )
        alert_warning(
            "Learning record-only",
            {
                "client_slug": client_slug,
                "learned_response_id": str(learned_response.id),
                "point_id": point_id,
                "learning_mode": learning_mode,
            },
        )
        return point_id

    content = f"Вопрос: {question}\nОтвет: {answer}"
    if len(learned_response.question_text.strip()) > len(question) or len(
        learned_response.response_text.strip()
    ) > len(answer):
        logger.info("Truncated learned_response sample to fit length limits")
    if question_redactions or answer_redactions:
        logger.info(
            "Learned response content redacted",
            extra={
                "context": {
                    "learned_response_id": str(learned_response.id),
                    "question_redactions": question_redactions,
                    "answer_redactions": answer_redactions,
                }
            },
        )

    try:
        embedding = get_embedding(content)
        point_id = str(uuid.uuid4())
        payload = {
            "content": content,
            "metadata": {
                "client_slug": client_slug,
                "source": source,
                "learned_id": str(learned_response.id),
                "question": question,
                "answer": answer,
                "learned_from": learned_response.source_name or "manager",
                "retention_expires_at": (
                    learned_response.retention_expires_at.isoformat()
                    if learned_response.retention_expires_at
                    else None
                ),
            },
        }
        if learned_response.branch_id:
            payload["metadata"]["branch_id"] = str(learned_response.branch_id)

        with httpx.Client(timeout=30.0) as client:
            response = client.put(
                f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points",
                headers={"api-key": QDRANT_API_KEY},
                json={"points": [{"id": point_id, "vector": embedding, "payload": payload}]},
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Qdrant upsert error: {response.status_code} - {response.text}")
                alert_error(
                    "Failed to add learned_response to knowledge",
                    {"learned_response_id": str(learned_response.id), "status": response.status_code},
                )
                return None

        learned_response.qdrant_point_id = point_id
        context = {
            "point_id": point_id,
            "client_slug": client_slug,
            "learned_response_id": str(learned_response.id),
            "question_len": len(question),
            "answer_len": len(answer),
            "source": source,
        }
        logger.info("Added learned_response to knowledge", extra={"context": context})
        alert_warning("Learning success", context)
        return point_id

    except Exception as exc:
        logger.error(f"Error adding learned_response to knowledge: {exc}", exc_info=True)
        alert_error(
            "Learning service error",
            {"learned_response_id": str(learned_response.id), "error": str(exc)},
        )
        return None
