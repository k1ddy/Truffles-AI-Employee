-- Add JSONB meta column for outbox timing/metadata.
-- Safe to run once.

ALTER TABLE outbox_messages
    ADD COLUMN IF NOT EXISTS meta JSONB;
