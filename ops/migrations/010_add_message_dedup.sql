-- Message deduplication table to enforce idempotency by message_id per client.
-- Safe to run multiple times.

CREATE TABLE IF NOT EXISTS message_dedup (
    client_id UUID NOT NULL,
    message_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (client_id, message_id)
);
