# Messaging Port v1

Purpose
- Provide a stable adapter interface for messaging providers (WhatsApp, Telegram).
- Keep core logic vendor-agnostic and idempotent.

Interface
- send_text(to: str, text: str, options: MessageOptions) -> Result[MessageSent]
- send_media(to: str, media_url: str, media_type: str, options: MessageOptions) -> Result[MessageSent]

MessageOptions
- instance_id: string | null
- idempotency_key: string | null (required for outbound dedup)
- caption: string | null
- extra: object (provider-specific data)

MessageSent
- remote_jid: string
- message_id: string | null
- provider_response: object

Rules
- Idempotency: when idempotency_key is provided, provider adapter must pass it to the vendor API.
- Timeouts: adapter should fail fast (short timeout) and return an error Result.
- Errors: adapter returns Result.fail(code, message, details) without throwing.
- Observability: adapter should attach trace_id and provider status into provider_response when available.

Notes
- This mirrors app/ports/messaging.py.
- Breaking changes require a new version file (messaging_port.v2.md).
