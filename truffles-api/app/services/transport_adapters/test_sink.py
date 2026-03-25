from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.transport_adapter import (
    TransportAdapter,
    TransportSendRequest,
    TransportSendResult,
)


class TestSinkTransportAdapter(TransportAdapter):
    __test__ = False
    _events: list[dict[str, Any]] = []

    @classmethod
    def clear_events(cls) -> None:
        cls._events.clear()

    @classmethod
    def get_events(cls) -> list[dict[str, Any]]:
        return list(cls._events)

    def send_text(self, *, db: Session, request: TransportSendRequest) -> TransportSendResult:
        self._events.append(
            {
                "remote_jid": request.remote_jid,
                "text": request.text,
                "idempotency_key": request.idempotency_key,
                "instance_id": request.instance_id,
                "client_id": request.client_id,
                "client_slug": request.client_slug,
                "conversation_id": request.conversation_id,
                "branch_id": request.branch_id,
                "use_outbox_send": request.use_outbox_send,
                "simulation": request.simulation,
            }
        )
        return TransportSendResult(delivered=True, status="sent")
