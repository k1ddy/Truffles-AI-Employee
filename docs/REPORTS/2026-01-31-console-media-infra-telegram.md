# Report: Console media infra + Telegram touchpoints (2026-01-31)

## Scope
- Console media upload/send (photo/audio/document) and Telegram echo (topic).
- Outbox vs direct send path; signed URL and storage.

## Current flow (facts)
1) Console UI -> /api/proxy -> POST /console/v1/conversations/{id}/messages/media (multipart).
2) API validates case ownership + active; rejects video; idempotency key supported.
3) Upload stored at MEDIA_STORAGE_DIR/<client>/<conversation>/console/<uuid>.<ext>; sha256 computed.
4) Signed URL built via PUBLIC_BASE_URL + MEDIA_SIGNING_SECRET + MEDIA_URL_TTL_SECONDS.
5) Message saved with metadata.media (type, size_bytes, sha256, storage_path, public_url, expires_at).
6) Delivery:
   - OUTBOX_WORKER_ENABLED=1 -> enqueue outbox event whatsapp.send_media (payload includes media_url, media_type, caption, media_meta).
   - Otherwise -> send_whatsapp_media via ChatFlow.
7) Telegram echo (if conversation.telegram_topic_id): resolve telegram bot token + chat id; send_photo/audio/document using local file path if present, else signed URL; caption prefixed with manager label.

## Infra dependencies
- MEDIA_STORAGE_DIR must be mounted for API and readable for TelegramService local file sends.
- PUBLIC_BASE_URL + MEDIA_SIGNING_SECRET must be set so signed URLs are valid and reachable by WhatsApp provider and Telegram.
- OUTBOX_WORKER_ENABLED / OUTBOX_SERVICE_ENABLED for async send + retries.
- CHATFLOW_MEDIA_BASE_URL / CHATFLOW_TOKEN for direct send path.
- PROVIDER_GATEWAY_OUTBOUND_ENABLED + PROVIDER_GATEWAY_OUTBOUND_URL if gateway handles outbox send.

## Risks and observations
- Telegram echo uses local file path when available; if container lacks volume mount, it will fall back to signed URL (must be publicly reachable).
- MEDIA_CLEANUP_TTL_DAYS should be >= outbox retry window to avoid missing files on retries.
- Caption required by ChatFlow for image/doc; direct send adds placeholder; outbox path should keep caption when present.

## Recommendations
1) Keep OUTBOX_WORKER_ENABLED=1 in prod; direct send only for dev.
2) Ensure MEDIA_STORAGE_DIR is a shared volume for API containers and persists across restarts.
3) Validate PUBLIC_BASE_URL is reachable from ChatFlow and Telegram; if private, add reverse proxy/CDN or disable local file path use.
4) Align MEDIA_URL_TTL_SECONDS with outbox retry + Telegram fetch delays (>= OUTBOX_MAX_ATTEMPTS * backoff).
5) Monitor MEDIA_STORAGE_WARN_BYTES and cleanup job; alert before storage fills.
6) Keep video blocked in console and enforce allowlist at UI + API.

## Evidence and references
- TECH.md (env vars: MEDIA_* / OUTBOX_* / CHATFLOW_*).
- truffles-api/app/services/chatflow_service.py (signed URL + send_whatsapp_media).
- truffles-api/app/services/manager_message_service.py (console upload + outbox).
- truffles-api/app/services/telegram_service.py (media send).
- truffles-api/app/routers/console.py (console media endpoint + telegram echo).
