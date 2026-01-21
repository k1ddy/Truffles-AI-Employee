CREATE TABLE IF NOT EXISTS console_idempotency_keys (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    idempotency_key TEXT NOT NULL,
    scope TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_status INTEGER,
    response_body JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_console_idempotency_client_key_scope
    ON console_idempotency_keys (client_id, idempotency_key, scope);

CREATE INDEX IF NOT EXISTS ix_console_idempotency_created_at
    ON console_idempotency_keys (created_at);
