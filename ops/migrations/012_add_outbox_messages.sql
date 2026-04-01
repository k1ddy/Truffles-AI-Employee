-- Durable outbox for inbound processing (ACK-first).
-- Safe to run once; table includes minimal dedup on (client_id, inbound_message_id).

CREATE TABLE IF NOT EXISTS outbox_messages (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    inbound_message_id TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempts INT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT outbox_messages_status_check CHECK (status IN ('PENDING','PROCESSING','SENT','FAILED'))
);

CREATE UNIQUE INDEX IF NOT EXISTS outbox_messages_dedup_idx
    ON outbox_messages (client_id, inbound_message_id);

CREATE INDEX IF NOT EXISTS outbox_messages_status_idx
    ON outbox_messages (status, next_attempt_at);
