-- Create alert events for analytics and audit.

CREATE TABLE IF NOT EXISTS alert_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  branch_id UUID,
  conversation_id UUID,
  message_id UUID,
  alert_type TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_client_date
  ON alert_events(client_id, created_at);

CREATE INDEX IF NOT EXISTS idx_alert_events_type
  ON alert_events(alert_type);

CREATE INDEX IF NOT EXISTS idx_alert_events_conversation
  ON alert_events(conversation_id);
