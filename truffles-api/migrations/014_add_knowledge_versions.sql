CREATE TABLE IF NOT EXISTS knowledge_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    pack_yaml TEXT,
    checksum TEXT,
    summary TEXT,
    source_version_id UUID REFERENCES knowledge_versions(id) ON DELETE SET NULL,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_by UUID REFERENCES agents(id),
    published_at TIMESTAMPTZ,
    CONSTRAINT check_knowledge_versions_status CHECK (status IN ('draft', 'published', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_versions_client_id ON knowledge_versions(client_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_versions_branch_id ON knowledge_versions(branch_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_versions_status ON knowledge_versions(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_versions_unique_draft
    ON knowledge_versions(branch_id)
    WHERE status = 'draft';
CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_versions_unique_published
    ON knowledge_versions(branch_id)
    WHERE status = 'published';

ALTER TABLE branches ADD COLUMN IF NOT EXISTS knowledge_safe_mode BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE branches ADD COLUMN IF NOT EXISTS knowledge_safe_mode_reason TEXT;
ALTER TABLE branches ADD COLUMN IF NOT EXISTS knowledge_safe_mode_at TIMESTAMPTZ;
