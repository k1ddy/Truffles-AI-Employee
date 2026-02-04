-- Create outbox status events for analytics and audit.

CREATE TABLE IF NOT EXISTS outbox_status_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outbox_id UUID NOT NULL REFERENCES outbox_messages(id) ON DELETE CASCADE,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  conversation_id UUID,
  branch_id UUID,
  status TEXT NOT NULL,
  last_error TEXT,
  attempts INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outbox_status_events_client_date
  ON outbox_status_events(client_id, created_at);

CREATE INDEX IF NOT EXISTS idx_outbox_status_events_outbox_id
  ON outbox_status_events(outbox_id);

CREATE INDEX IF NOT EXISTS idx_outbox_status_events_status
  ON outbox_status_events(status);
