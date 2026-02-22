ALTER TABLE marketing_campaigns
    ADD COLUMN IF NOT EXISTS status_v2 TEXT;

UPDATE marketing_campaigns
SET status_v2 = CASE LOWER(COALESCE(status, ''))
    WHEN 'draft' THEN 'draft'
    WHEN 'in_review' THEN 'in_review'
    WHEN 'approved' THEN 'approved'
    WHEN 'scheduled' THEN 'scheduled'
    WHEN 'running' THEN 'running'
    WHEN 'paused' THEN 'paused'
    WHEN 'completed' THEN 'completed'
    WHEN 'cancelled' THEN 'cancelled'
    WHEN 'failed' THEN 'failed'
    WHEN 'ready' THEN 'approved'
    WHEN 'executed' THEN 'completed'
    ELSE 'draft'
END
WHERE status_v2 IS NULL OR btrim(status_v2) = '';

ALTER TABLE marketing_campaigns
    ALTER COLUMN status_v2 SET DEFAULT 'draft';

UPDATE marketing_campaigns
SET status_v2 = 'draft'
WHERE status_v2 IS NULL;

ALTER TABLE marketing_campaigns
    ALTER COLUMN status_v2 SET NOT NULL;

ALTER TABLE marketing_campaigns
    DROP CONSTRAINT IF EXISTS check_marketing_campaign_status_v2;

ALTER TABLE marketing_campaigns
    ADD CONSTRAINT check_marketing_campaign_status_v2
    CHECK (
        status_v2 IN (
            'draft',
            'in_review',
            'approved',
            'scheduled',
            'running',
            'paused',
            'completed',
            'cancelled',
            'failed'
        )
    );

CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_status_v2_created
    ON marketing_campaigns(status_v2, created_at DESC);
