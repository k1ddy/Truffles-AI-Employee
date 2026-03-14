-- 059_add_knowledge_version_sync_status.sql
-- Durable publish/sync status for owner-facing knowledge flows.

ALTER TABLE knowledge_versions
    ADD COLUMN IF NOT EXISTS sync_status TEXT;

ALTER TABLE knowledge_versions
    ADD COLUMN IF NOT EXISTS sync_error TEXT;

ALTER TABLE knowledge_versions
    ADD COLUMN IF NOT EXISTS sync_completed_at TIMESTAMPTZ;

UPDATE knowledge_versions
SET
    sync_status = CASE
        WHEN status = 'draft' THEN 'pending'
        ELSE 'ready'
    END,
    sync_completed_at = CASE
        WHEN status = 'draft' THEN NULL
        ELSE COALESCE(published_at, created_at, NOW())
    END
WHERE sync_status IS NULL;

WITH latest_failed_branch_version AS (
    SELECT DISTINCT ON (kv.branch_id)
        kv.id,
        kv.branch_id,
        b.knowledge_safe_mode_reason,
        b.knowledge_safe_mode_at
    FROM knowledge_versions kv
    JOIN branches b ON b.id = kv.branch_id
    WHERE kv.status = 'published'
      AND b.knowledge_safe_mode = TRUE
    ORDER BY kv.branch_id, kv.published_at DESC NULLS LAST, kv.created_at DESC NULLS LAST
)
UPDATE knowledge_versions kv
SET
    sync_status = 'failed',
    sync_error = COALESCE(latest_failed_branch_version.knowledge_safe_mode_reason, kv.sync_error, 'sync_failed'),
    sync_completed_at = COALESCE(latest_failed_branch_version.knowledge_safe_mode_at, kv.sync_completed_at, NOW())
FROM latest_failed_branch_version
WHERE kv.id = latest_failed_branch_version.id;

ALTER TABLE knowledge_versions
    ALTER COLUMN sync_status SET NOT NULL;

ALTER TABLE knowledge_versions
    ALTER COLUMN sync_status SET DEFAULT 'pending';

CREATE INDEX IF NOT EXISTS knowledge_versions_branch_sync_status_idx
    ON knowledge_versions (branch_id, sync_status, published_at DESC NULLS LAST, created_at DESC NULLS LAST);
