-- 060_add_knowledge_release_activation_jobs.sql
-- Split active live pointer from published artifact candidate and add activation job lifecycle.

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS active_knowledge_version_id UUID REFERENCES knowledge_versions(id);

WITH latest_published_branch_version AS (
    SELECT DISTINCT ON (kv.branch_id)
        kv.branch_id,
        kv.id
    FROM knowledge_versions kv
    WHERE kv.status = 'published'
    ORDER BY kv.branch_id, kv.published_at DESC NULLS LAST, kv.created_at DESC NULLS LAST
)
UPDATE branches b
SET active_knowledge_version_id = latest_published_branch_version.id
FROM latest_published_branch_version
WHERE b.id = latest_published_branch_version.branch_id
  AND b.active_knowledge_version_id IS NULL;

CREATE TABLE IF NOT EXISTS knowledge_activation_jobs (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    branch_id UUID NOT NULL REFERENCES branches(id),
    version_id UUID NOT NULL REFERENCES knowledge_versions(id),
    state TEXT NOT NULL DEFAULT 'queued',
    source TEXT NOT NULL DEFAULT 'knowledge_publish',
    attempt_count INTEGER NOT NULL DEFAULT 1,
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    last_error TEXT,
    error_code TEXT,
    triggered_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS branches_active_knowledge_version_idx
    ON branches (active_knowledge_version_id);

CREATE INDEX IF NOT EXISTS knowledge_activation_jobs_branch_queued_idx
    ON knowledge_activation_jobs (branch_id, queued_at DESC);

CREATE INDEX IF NOT EXISTS knowledge_activation_jobs_version_queued_idx
    ON knowledge_activation_jobs (version_id, queued_at DESC);

CREATE INDEX IF NOT EXISTS knowledge_activation_jobs_branch_state_idx
    ON knowledge_activation_jobs (branch_id, state, queued_at DESC);
