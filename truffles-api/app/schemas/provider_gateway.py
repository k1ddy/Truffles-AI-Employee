from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.outbox_payload import TenantContext


class ProviderParticipant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    phone: str | None = None
    jid: str | None = None
    display_name: str | None = None


class ProviderMessageMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: str
    url: str | None = None
    signed_url: str | None = None
    expires_at: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    mime_type: str | None = None
    filename: str | None = None
    caption: str | None = None


class ProviderMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., min_length=1)
    text: str | None = None
    media: ProviderMessageMedia | None = None
    payload: dict[str, Any] | None = None


class ProviderInbound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., min_length=1)
    channel: str = Field(..., min_length=1)
    provider_message_id: str = Field(..., min_length=1)
    tenant_context: TenantContext
    received_at: str = Field(..., min_length=1)
    sender: ProviderParticipant
    receiver: ProviderParticipant
    message: ProviderMessage
    raw_ref: str | None = None
    dedupe_key: str | None = None
    auth: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    extensions: dict[str, Any] | None = None
