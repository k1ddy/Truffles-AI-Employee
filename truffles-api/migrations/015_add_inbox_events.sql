CREATE TABLE IF NOT EXISTS inbox_events (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    branch_id UUID NULL REFERENCES branches(id),
    provider TEXT NOT NULL,
    channel TEXT NOT NULL,
    provider_message_id TEXT NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_ref TEXT NULL,
    dedupe_key TEXT NULL,
    status TEXT NULL,
    status_at TIMESTAMP WITH TIME ZONE NULL,
    tenant_context JSONB NULL,
    payload_json JSONB NOT NULL,
    meta JSONB NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS inbox_events_provider_dedupe
    ON inbox_events (client_id, provider, channel, provider_message_id);

CREATE INDEX IF NOT EXISTS inbox_events_client_created_at
    ON inbox_events (client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS inbox_events_branch_created_at
    ON inbox_events (branch_id, created_at DESC);
