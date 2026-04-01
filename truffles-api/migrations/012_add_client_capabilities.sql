CREATE TABLE IF NOT EXISTS client_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_client_capabilities_scope CHECK (scope IN ('client', 'branch')),
    CONSTRAINT check_client_capabilities_status CHECK (status IN ('active', 'disabled')),
    CONSTRAINT check_client_capabilities_branch_scope CHECK (
        (scope = 'client' AND branch_id IS NULL) OR
        (scope = 'branch' AND branch_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_client_capabilities_client_id ON client_capabilities(client_id);
CREATE INDEX IF NOT EXISTS idx_client_capabilities_branch_id ON client_capabilities(branch_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_capabilities_unique_client
    ON client_capabilities(client_id)
    WHERE scope = 'client' AND branch_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_capabilities_unique_branch
    ON client_capabilities(client_id, branch_id)
    WHERE scope = 'branch' AND branch_id IS NOT NULL;
