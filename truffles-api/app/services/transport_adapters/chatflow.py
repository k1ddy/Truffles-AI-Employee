from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.adapters.chatflow import ChatFlowAdapter
from app.ports.messaging import MessageOptions
from app.services.outbox_service import enqueue_outbox_message
from app.services.transport_adapter import (
    TransportAdapter,
    TransportSendRequest,
    TransportSendResult,
)


class ChatflowTransportAdapter(TransportAdapter):
    def send_text(self, *, db: Session, request: TransportSendRequest) -> TransportSendResult:
        if request.simulation:
            return TransportSendResult(
                delivered=True,
                status="simulated",
            )

        if not request.instance_id:
            return TransportSendResult(
                delivered=False,
                status="failed",
                reason="instance_id_missing",
            )

        if request.use_outbox_send and request.conversation_id:
            outbox_payload = {
                "schema_version": "outbox.v1",
                "event_type": "whatsapp.send_text",
                "idempotency_key": request.idempotency_key,
                "client_id": request.client_id,
                "branch_id": request.branch_id,
                "tenant_context": {
                    "client_id": request.client_id,
                    "branch_id": request.branch_id,
                    "client_slug": request.client_slug,
                    "instance_id": request.instance_id,
                    "source": "system",
                },
                "conversation_id": request.conversation_id,
                "channel": "whatsapp",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "remote_jid": request.remote_jid,
                    "text": request.text,
                    "instance_id": request.instance_id,
                    "idempotency_key": request.idempotency_key,
                },
            }
            enqueued = enqueue_outbox_message(
                db,
                client_id=request.client_id,
                conversation_id=request.conversation_id,
                inbound_message_id=request.idempotency_key,
                payload_json=outbox_payload,
                branch_id=request.branch_id,
            )
            if enqueued:
                return TransportSendResult(
                    delivered=True,
                    status="enqueued",
                    details={"outbox_enqueued": True},
                )
            return TransportSendResult(
                delivered=True,
                status="duplicate",
                reason="outbox_duplicate",
                details={"outbox_enqueued": False},
            )

        adapter = ChatFlowAdapter()
        options = MessageOptions(
            instance_id=request.instance_id,
            idempotency_key=request.idempotency_key,
        )
        result = adapter.send_text(request.remote_jid, request.text, options)
        if result.is_ok():
            return TransportSendResult(
                delivered=True,
                status="sent",
                details={"provider": "chatflow"},
            )
        return TransportSendResult(
            delivered=False,
            status="failed",
            reason="provider_send_failed",
            provider_error=str(result.error),
            details={"provider": "chatflow"},
        )
