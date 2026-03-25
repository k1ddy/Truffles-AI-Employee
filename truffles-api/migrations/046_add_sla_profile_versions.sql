-- SLA/SLO profile registry with multi-scope layering.
-- Scope order for effective merge: global -> domain -> client -> branch.

CREATE TABLE IF NOT EXISTS sla_profile_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope TEXT NOT NULL,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    domain_key TEXT,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'published',
    schema_version TEXT NOT NULL DEFAULT 'v1',
    version_number INTEGER NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason TEXT,
    source_version_id UUID REFERENCES sla_profile_versions(id),
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_by UUID REFERENCES agents(id),
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_sla_profile_versions_scope
        CHECK (scope IN ('global', 'domain', 'client', 'branch')),
    CONSTRAINT check_sla_profile_versions_status
        CHECK (status IN ('published', 'archived')),
    CONSTRAINT check_sla_profile_versions_scope_target
        CHECK (
            (scope = 'global' AND company_id IS NULL AND domain_key IS NULL AND client_id IS NULL AND branch_id IS NULL) OR
            (scope = 'domain' AND company_id IS NULL AND domain_key IS NOT NULL AND client_id IS NULL AND branch_id IS NULL) OR
            (scope = 'client' AND company_id IS NOT NULL AND domain_key IS NULL AND client_id IS NOT NULL AND branch_id IS NULL) OR
            (scope = 'branch' AND company_id IS NOT NULL AND domain_key IS NULL AND client_id IS NOT NULL AND branch_id IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_sla_profile_versions_lookup
    ON sla_profile_versions(scope, company_id, domain_key, client_id, branch_id, status, published_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sla_profile_versions_source_version_id
    ON sla_profile_versions(source_version_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_version_global
    ON sla_profile_versions(scope, version_number)
    WHERE scope = 'global';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_version_domain
    ON sla_profile_versions(scope, domain_key, version_number)
    WHERE scope = 'domain';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_version_client
    ON sla_profile_versions(scope, company_id, client_id, version_number)
    WHERE scope = 'client';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_version_branch
    ON sla_profile_versions(scope, company_id, client_id, branch_id, version_number)
    WHERE scope = 'branch';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_active_global
    ON sla_profile_versions(scope)
    WHERE scope = 'global' AND status = 'published';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_active_domain
    ON sla_profile_versions(scope, domain_key)
    WHERE scope = 'domain' AND status = 'published';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_active_client
    ON sla_profile_versions(scope, company_id, client_id)
    WHERE scope = 'client' AND status = 'published';

CREATE UNIQUE INDEX IF NOT EXISTS idx_sla_profile_versions_active_branch
    ON sla_profile_versions(scope, company_id, client_id, branch_id)
    WHERE scope = 'branch' AND status = 'published';
