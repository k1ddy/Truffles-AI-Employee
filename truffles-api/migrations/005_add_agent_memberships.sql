-- Create agent_memberships table for org-level tenancy/RBAC
CREATE TABLE IF NOT EXISTS agent_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    scope TEXT NOT NULL CHECK (scope IN ('company', 'client', 'branch')),
    company_id UUID REFERENCES companies(id),
    client_id UUID REFERENCES clients(id),
    branch_id UUID REFERENCES branches(id),
    role TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CHECK (
        (scope = 'company' AND company_id IS NOT NULL AND client_id IS NULL AND branch_id IS NULL) OR
        (scope = 'client' AND client_id IS NOT NULL AND branch_id IS NULL) OR
        (scope = 'branch' AND branch_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_agent_memberships_agent_id ON agent_memberships(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memberships_company_id ON agent_memberships(company_id);
CREATE INDEX IF NOT EXISTS idx_agent_memberships_client_id ON agent_memberships(client_id);
CREATE INDEX IF NOT EXISTS idx_agent_memberships_branch_id ON agent_memberships(branch_id);

-- Backfill legacy agents into memberships (idempotent)
INSERT INTO agent_memberships (
    id,
    agent_id,
    scope,
    company_id,
    client_id,
    branch_id,
    role,
    is_active,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    a.id,
    CASE WHEN a.branch_id IS NOT NULL THEN 'branch' ELSE 'client' END,
    NULL,
    CASE WHEN a.branch_id IS NULL THEN a.client_id ELSE NULL END,
    CASE WHEN a.branch_id IS NOT NULL THEN a.branch_id ELSE NULL END,
    a.role,
    a.is_active,
    now(),
    now()
FROM agents a
WHERE NOT EXISTS (
    SELECT 1
    FROM agent_memberships am
    WHERE am.agent_id = a.id
);
