from typing import Any

from app.contracts import Err, ErrorCodes, IntegrationError, Ok, Result
from app.ports.messaging import MessageOptions, MessageSent, MessagingPort
from app.services import chatflow_service


class ChatFlowAdapter(MessagingPort):
    """Adapter for ChatFlow WhatsApp provider."""

    def send_text(self, to: str, text: str, options: MessageOptions) -> Result[MessageSent]:
        instance_id = options.instance_id
        if not instance_id:
            return Err(IntegrationError(
                code=ErrorCodes.CONFIG_MISSING,
                message="instance_id is required for ChatFlow",
                service="chatflow",
                context={"to": to}
            ))
        if options.extra.get("simulation_mode"):
            return Ok(MessageSent(
                remote_jid=to,
                message_id=options.idempotency_key,
                provider_response={"simulation": True},
            ))

        # Call the existing service function
        result = chatflow_service.send_message_safe(
            instance_id=instance_id,
            remote_jid=to,
            message=text,
            idempotency_key=options.idempotency_key,
            notify_on_failure=False,
            record_metrics=False,
        )

        if result.is_ok():
            # Map service result to port result
            # service returns: MessageSent(remote_jid, instance_id)
            # port expects: MessageSent(remote_jid, message_id, provider_response)
            service_val = result.unwrap()
            return Ok(MessageSent(
                remote_jid=service_val.remote_jid,
                message_id=options.idempotency_key, # ChatFlow doesn't return ID immediately in this API
                provider_response={"instance_id": service_val.instance_id}
            ))
        else:
            return Err(result.error)

    def send_media(self, to: str, media_url: str, media_type: str, options: MessageOptions) -> Result[MessageSent]:
        instance_id = options.instance_id
        if not instance_id:
            return Err(IntegrationError(
                code=ErrorCodes.CONFIG_MISSING,
                message="instance_id is required for ChatFlow",
                service="chatflow",
                context={"to": to}
            ))
        if options.extra.get("simulation_mode"):
            return Ok(MessageSent(
                remote_jid=to,
                provider_response={"simulation": True},
            ))

        # chatflow_service.send_whatsapp_media returns bool, not Result
        success = chatflow_service.send_whatsapp_media(
            instance_id=instance_id,
            remote_jid=to,
            media_type=media_type,
            media_url=media_url,
            caption=options.caption,
            notify_on_failure=False,
            record_metrics=False,
        )

        if success:
            return Ok(MessageSent(
                remote_jid=to,
                provider_response={"instance_id": instance_id, "media_type": media_type}
            ))
        else:
            return Err(IntegrationError(
                code=ErrorCodes.CHATFLOW_ERROR,
                message="Failed to send media",
                service="chatflow",
                context={"to": to, "media_type": media_type}
            ))
