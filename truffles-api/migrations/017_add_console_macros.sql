CREATE TABLE IF NOT EXISTS console_macros (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    branch_id UUID NOT NULL REFERENCES branches(id),
    agent_id UUID REFERENCES agents(id),
    scope TEXT NOT NULL,
    label TEXT NOT NULL,
    body TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_console_macros_client_branch
    ON console_macros (client_id, branch_id);

CREATE INDEX IF NOT EXISTS idx_console_macros_agent
    ON console_macros (agent_id);

CREATE INDEX IF NOT EXISTS idx_console_macros_scope
    ON console_macros (scope);
