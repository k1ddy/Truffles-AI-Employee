-- Add handover metadata snapshot and trigger message link.

ALTER TABLE handovers
  ADD COLUMN IF NOT EXISTS meta JSONB,
  ADD COLUMN IF NOT EXISTS trigger_message_id UUID;

ALTER TABLE handovers
  DROP CONSTRAINT IF EXISTS handovers_trigger_message_id_fkey;

ALTER TABLE handovers
  ADD CONSTRAINT handovers_trigger_message_id_fkey
  FOREIGN KEY (trigger_message_id) REFERENCES messages(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_handovers_trigger_message_id
  ON handovers(trigger_message_id);
