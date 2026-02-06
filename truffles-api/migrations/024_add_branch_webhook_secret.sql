ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS webhook_secret TEXT;

