-- Domain catalog registry with capability templates for platform-admin governance.
-- Enables domain-level capability layer between global and client/branch overrides.

CREATE TABLE IF NOT EXISTS domain_capability_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    capability_template_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_domain_capability_templates_status CHECK (status IN ('active', 'disabled'))
);

CREATE INDEX IF NOT EXISTS idx_domain_capability_templates_status
    ON domain_capability_templates(status);

