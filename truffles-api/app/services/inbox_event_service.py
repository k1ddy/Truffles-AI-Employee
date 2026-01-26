from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Client, InboxEvent
from app.schemas.outbox_payload import TenantContext
from app.schemas.provider_gateway import ProviderInbound


def _parse_received_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def record_inbox_event(
    db: Session,
    *,
    payload: ProviderInbound,
    raw_payload: dict,
    enforce_client_match: bool = True,
) -> tuple[bool, str]:
    tenant_context = payload.tenant_context
    if not tenant_context or not tenant_context.client_id:
        return False, "missing_client_id"

    client_id = tenant_context.client_id
    if isinstance(client_id, str):
        try:
            client_id = UUID(client_id)
        except ValueError:
            return False, "invalid_client_id"

    client_slug = tenant_context.client_slug
    if enforce_client_match and client_slug:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return False, "client_not_found"
        if client.name != client_slug:
            return False, "client_slug_mismatch"

    received_at = _parse_received_at(payload.received_at)
    if not received_at:
        return False, "invalid_received_at"

    tenant_context_payload = TenantContext.model_validate(tenant_context).model_dump(exclude_none=True)
    event_id = uuid4()
    stmt = (
        insert(InboxEvent)
        .values(
            id=event_id,
            client_id=client_id,
            branch_id=tenant_context.branch_id,
            provider=payload.provider,
            channel=payload.channel,
            provider_message_id=payload.provider_message_id,
            received_at=received_at,
            raw_ref=payload.raw_ref,
            dedupe_key=payload.dedupe_key,
            tenant_context=tenant_context_payload,
            payload_json=raw_payload,
            meta=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(
            index_elements=["client_id", "provider", "channel", "provider_message_id"]
        )
    )
    try:
        result = db.execute(stmt)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False, "db_error"
    if result.rowcount == 0:
        return False, "duplicate"
    return True, str(event_id)
