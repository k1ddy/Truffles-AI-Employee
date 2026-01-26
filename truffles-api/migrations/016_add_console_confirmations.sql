CREATE TABLE IF NOT EXISTS console_confirmations (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    branch_id UUID REFERENCES branches(id),
    actor_id UUID NOT NULL REFERENCES agents(id),
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_console_confirmations_client_id
    ON console_confirmations (client_id);

CREATE INDEX IF NOT EXISTS ix_console_confirmations_branch_id
    ON console_confirmations (branch_id);

CREATE INDEX IF NOT EXISTS ix_console_confirmations_expires_at
    ON console_confirmations (expires_at);
