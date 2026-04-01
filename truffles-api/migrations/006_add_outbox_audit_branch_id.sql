-- Add branch scoping to audit/outbox for tenant isolation.
ALTER TABLE audit_events
ADD COLUMN IF NOT EXISTS branch_id UUID;

ALTER TABLE outbox_messages
ADD COLUMN IF NOT EXISTS branch_id UUID;

CREATE INDEX IF NOT EXISTS idx_audit_events_branch_id ON audit_events(branch_id);
CREATE INDEX IF NOT EXISTS idx_outbox_messages_branch_id ON outbox_messages(branch_id);

-- Backfill outbox branch_id from conversations.
UPDATE outbox_messages o
SET branch_id = c.branch_id
FROM conversations c
WHERE o.conversation_id = c.id
  AND o.branch_id IS NULL;

-- Backfill audit branch_id for conversation events.
UPDATE audit_events ae
SET branch_id = c.branch_id
FROM conversations c
WHERE ae.entity_type = 'conversation'
  AND ae.entity_id = c.id
  AND ae.branch_id IS NULL;

-- Backfill audit branch_id for handover events.
UPDATE audit_events ae
SET branch_id = c.branch_id
FROM handovers h
JOIN conversations c ON c.id = h.conversation_id
WHERE ae.entity_type = 'handover'
  AND ae.entity_id = h.id
  AND ae.branch_id IS NULL;
