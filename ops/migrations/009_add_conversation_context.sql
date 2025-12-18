ALTER TABLE conversations
ADD COLUMN context JSONB NOT NULL DEFAULT '{}'::jsonb;
