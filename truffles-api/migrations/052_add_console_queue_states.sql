CREATE TABLE IF NOT EXISTS console_queue_states (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    surface TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    selected_branch_id UUID REFERENCES branches(id),
    case_id UUID,
    conversation_id UUID,
    version INTEGER NOT NULL DEFAULT 1,
    query_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_console_queue_states_scope UNIQUE (client_id, agent_id, surface, scope_key)
);

CREATE INDEX IF NOT EXISTS ix_console_queue_states_updated_at
    ON console_queue_states (updated_at);
