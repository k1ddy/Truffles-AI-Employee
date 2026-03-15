ALTER TABLE knowledge_activation_jobs
    ADD COLUMN IF NOT EXISTS current_stage TEXT;

UPDATE knowledge_activation_jobs
SET current_stage = CASE
    WHEN state = 'ready' THEN 'ready'
    WHEN state = 'failed' THEN 'failed'
    WHEN state = 'running' THEN 'syncing_branch_docs'
    ELSE 'queued'
END
WHERE current_stage IS NULL OR btrim(current_stage) = '';

ALTER TABLE knowledge_activation_jobs
    ALTER COLUMN current_stage SET DEFAULT 'queued';

ALTER TABLE knowledge_activation_jobs
    ALTER COLUMN current_stage SET NOT NULL;
