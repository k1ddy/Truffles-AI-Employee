CREATE TABLE IF NOT EXISTS console_saved_views (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    surface TEXT NOT NULL,
    name TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    query_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ux_console_saved_views_name UNIQUE (client_id, agent_id, surface, name)
);

CREATE INDEX IF NOT EXISTS ix_console_saved_views_surface_updated_at
    ON console_saved_views (surface, updated_at);
