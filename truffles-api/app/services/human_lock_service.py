from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, ConversationHumanLock, Handover, User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None or not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def normalize_remote_jid(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if "@" in text:
        return text.lower()
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"


def normalize_phone_to_jid(value: str | None) -> str | None:
    return normalize_remote_jid(value)


def resolve_conversation_remote_jid(db: Session, *, conversation: Conversation) -> str | None:
    user = db.query(User).filter(User.id == conversation.user_id).first()
    if user:
        remote_jid = normalize_remote_jid(user.remote_jid)
        if remote_jid:
            return remote_jid
        remote_jid = normalize_phone_to_jid(user.phone)
        if remote_jid:
            return remote_jid

    handover = (
        db.query(Handover)
        .filter(
            Handover.conversation_id == conversation.id,
            Handover.client_id == conversation.client_id,
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    if handover:
        return normalize_remote_jid(handover.channel_ref)
    return None


def get_active_human_lock(
    db: Session,
    *,
    client_id: UUID,
    remote_jid: str | None,
    now: datetime | None = None,
) -> ConversationHumanLock | None:
    normalized = normalize_remote_jid(remote_jid)
    if not normalized:
        return None

    now_utc = _coerce_utc(now) or _utc_now()
    lock = (
        db.query(ConversationHumanLock)
        .filter(
            ConversationHumanLock.client_id == client_id,
            ConversationHumanLock.remote_jid == normalized,
            ConversationHumanLock.active.is_(True),
        )
        .first()
    )
    if not lock or not isinstance(lock, ConversationHumanLock):
        return None

    lock_until = _coerce_utc(lock.lock_until)
    if not lock_until or lock_until <= now_utc:
        lock.active = False
        lock.released_at = now_utc
        lock.updated_at = now_utc
        db.flush()
        return None

    return lock


def upsert_human_lock(
    db: Session,
    *,
    client_id: UUID,
    remote_jid: str,
    lock_until: datetime,
    conversation_id: UUID | None = None,
    branch_id: UUID | None = None,
    locked_by_id: UUID | None = None,
    locked_by_name: str | None = None,
    source: str = "console",
    reason: str | None = None,
) -> ConversationHumanLock:
    normalized = normalize_remote_jid(remote_jid)
    if not normalized:
        raise ValueError("remote_jid_required")

    lock_until_utc = _coerce_utc(lock_until)
    if lock_until_utc is None:
        raise ValueError("lock_until_required")

    lock = (
        db.query(ConversationHumanLock)
        .filter(
            ConversationHumanLock.client_id == client_id,
            ConversationHumanLock.remote_jid == normalized,
        )
        .first()
    )

    now_utc = _utc_now()
    if not lock:
        lock = ConversationHumanLock(
            client_id=client_id,
            branch_id=branch_id,
            conversation_id=conversation_id,
            remote_jid=normalized,
            source=source,
            reason=reason,
            locked_by_id=locked_by_id,
            locked_by_name=locked_by_name,
            lock_until=lock_until_utc,
            active=True,
            released_at=None,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(lock)
        db.flush()
        return lock

    lock.branch_id = branch_id
    lock.conversation_id = conversation_id
    lock.source = source
    lock.reason = reason
    lock.locked_by_id = locked_by_id
    lock.locked_by_name = locked_by_name
    lock.lock_until = lock_until_utc
    lock.active = True
    lock.released_at = None
    lock.updated_at = now_utc
    db.flush()
    return lock


def release_human_lock(
    db: Session,
    *,
    client_id: UUID,
    remote_jid: str | None,
    now: datetime | None = None,
) -> ConversationHumanLock | None:
    normalized = normalize_remote_jid(remote_jid)
    if not normalized:
        return None

    lock = (
        db.query(ConversationHumanLock)
        .filter(
            ConversationHumanLock.client_id == client_id,
            ConversationHumanLock.remote_jid == normalized,
        )
        .first()
    )
    if not lock:
        return None

    now_utc = _coerce_utc(now) or _utc_now()
    lock.active = False
    lock.released_at = now_utc
    lock.lock_until = now_utc
    lock.updated_at = now_utc
    db.flush()
    return lock
