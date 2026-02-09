CREATE TABLE IF NOT EXISTS console_branch_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    actor_agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    draft_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    diff_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_payload JSONB,
    base_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_snapshot JSONB,
    rollback_snapshot JSONB,
    base_branch_updated_at TIMESTAMPTZ,
    publish_error TEXT,
    rollback_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    validated_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    published_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    rolled_back_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    CONSTRAINT check_console_branch_changes_status
        CHECK (status IN ('draft', 'validated', 'publish_failed', 'published', 'rolled_back'))
);

CREATE INDEX IF NOT EXISTS idx_console_branch_changes_client_created
    ON console_branch_changes(client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_console_branch_changes_branch_created
    ON console_branch_changes(branch_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_console_branch_changes_status_created
    ON console_branch_changes(status, created_at DESC);
