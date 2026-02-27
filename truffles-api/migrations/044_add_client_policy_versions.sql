-- Versioned policy registry for operational policy overrides (hard-law excluded).
-- Scope: client or branch with deterministic publish/rollback history.

CREATE TABLE IF NOT EXISTS client_policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'published',
    schema_version TEXT NOT NULL DEFAULT 'v1',
    version_number INTEGER NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT,
    source_version_id UUID REFERENCES client_policy_versions(id),
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_by UUID REFERENCES agents(id),
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_client_policy_versions_scope CHECK (scope IN ('client', 'branch')),
    CONSTRAINT check_client_policy_versions_status CHECK (status IN ('published', 'archived')),
    CONSTRAINT check_client_policy_versions_scope_branch CHECK (
        (scope = 'client' AND branch_id IS NULL) OR
        (scope = 'branch' AND branch_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_client_policy_versions_lookup
    ON client_policy_versions(client_id, scope, branch_id, status, published_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_client_policy_versions_source_version_id
    ON client_policy_versions(source_version_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_client_policy_versions_version_client
    ON client_policy_versions(client_id, version_number)
    WHERE scope = 'client' AND branch_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_client_policy_versions_version_branch
    ON client_policy_versions(client_id, branch_id, version_number)
    WHERE scope = 'branch' AND branch_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_client_policy_versions_active_client
    ON client_policy_versions(client_id)
    WHERE scope = 'client' AND branch_id IS NULL AND status = 'published';

CREATE UNIQUE INDEX IF NOT EXISTS idx_client_policy_versions_active_branch
    ON client_policy_versions(client_id, branch_id)
    WHERE scope = 'branch' AND branch_id IS NOT NULL AND status = 'published';
