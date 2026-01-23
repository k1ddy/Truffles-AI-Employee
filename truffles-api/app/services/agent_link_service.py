import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Agent, AgentLinkToken

TOKEN_TTL_MINUTES = 15
TOKEN_BYTES = 4  # 8 hex chars


def hash_link_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_link_token() -> str:
    return secrets.token_hex(TOKEN_BYTES).upper()


def build_telegram_deep_link(bot_username: Optional[str], token: str) -> Optional[str]:
    if not bot_username:
        return None
    cleaned = bot_username.lstrip("@").strip()
    if not cleaned:
        return None
    return f"https://t.me/{cleaned}?start={token}"


def create_agent_link_token(
    db: Session,
    *,
    agent: Agent,
    created_by_id: Optional[UUID],
    channel: str = "telegram",
    ttl_minutes: int = TOKEN_TTL_MINUTES,
) -> tuple[str, AgentLinkToken]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=max(ttl_minutes, 5))

    db.query(AgentLinkToken).filter(
        AgentLinkToken.agent_id == agent.id,
        AgentLinkToken.channel == channel,
        AgentLinkToken.used_at.is_(None),
        AgentLinkToken.expires_at > now,
    ).update({"used_at": now})

    for _ in range(5):
        token = generate_link_token()
        token_hash = hash_link_token(token)
        exists = db.query(AgentLinkToken).filter(AgentLinkToken.token_hash == token_hash).first()
        if exists:
            continue
        record = AgentLinkToken(
            agent_id=agent.id,
            client_id=agent.client_id,
            channel=channel,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
            created_by_id=created_by_id,
        )
        db.add(record)
        db.flush()
        return token, record

    raise RuntimeError("Failed to generate unique link token")


def consume_link_token(db: Session, token: str, *, channel: str = "telegram") -> AgentLinkToken:
    token_hash = hash_link_token(token)
    record = (
        db.query(AgentLinkToken)
        .filter(AgentLinkToken.token_hash == token_hash, AgentLinkToken.channel == channel)
        .first()
    )
    if not record:
        raise ValueError("invalid")

    now = datetime.now(timezone.utc)
    if record.used_at:
        raise ValueError("used")
    if record.expires_at and record.expires_at < now:
        raise ValueError("expired")

    return record
