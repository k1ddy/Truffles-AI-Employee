from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class TransportSendRequest:
    remote_jid: str
    text: str
    idempotency_key: str
    instance_id: str | None
    client_id: str
    client_slug: str
    conversation_id: str | None = None
    branch_id: str | None = None
    use_outbox_send: bool = False
    simulation: bool = False


@dataclass(frozen=True)
class TransportSendResult:
    delivered: bool
    status: str
    reason: str | None = None
    provider_error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class TransportAdapter(Protocol):
    def send_text(self, *, db: Session, request: TransportSendRequest) -> TransportSendResult:
        ...


def _normalize_adapter_name(name: str | None) -> str:
    if not isinstance(name, str):
        return "chatflow"
    token = name.strip().casefold()
    return token or "chatflow"


def resolve_transport_adapter(name: str | None = None) -> TransportAdapter:
    adapter_name = _normalize_adapter_name(name or os.environ.get("TRANSPORT_ADAPTER"))
    if adapter_name == "test_sink":
        from app.services.transport_adapters.test_sink import TestSinkTransportAdapter

        return TestSinkTransportAdapter()

    from app.services.transport_adapters.chatflow import ChatflowTransportAdapter

    return ChatflowTransportAdapter()
