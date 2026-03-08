CREATE TABLE IF NOT EXISTS console_routing_profiles (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    branch_id UUID NULL REFERENCES branches(id),
    routing_status TEXT NOT NULL DEFAULT 'available',
    max_open_case_count INTEGER NULL,
    updated_by_agent_id UUID NULL REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_console_routing_profiles_client_id
    ON console_routing_profiles (client_id);

CREATE INDEX IF NOT EXISTS ix_console_routing_profiles_agent_id
    ON console_routing_profiles (agent_id);

CREATE INDEX IF NOT EXISTS ix_console_routing_profiles_branch_id
    ON console_routing_profiles (branch_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_console_routing_profiles_client_agent_default
    ON console_routing_profiles (client_id, agent_id)
    WHERE branch_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_console_routing_profiles_client_agent_branch
    ON console_routing_profiles (client_id, agent_id, branch_id)
    WHERE branch_id IS NOT NULL;
