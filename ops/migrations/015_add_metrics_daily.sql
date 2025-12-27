-- Migration 015: daily metrics snapshot table
-- Run: psql -U $DB_USER -d chatbot -f ops/migrations/015_add_metrics_daily.sql

CREATE TABLE IF NOT EXISTS metrics_daily (
  metric_date DATE NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  outbox_latency_p50 NUMERIC(10, 2),
  outbox_latency_p90 NUMERIC(10, 2),
  llm_timeout_rate NUMERIC(6, 4),
  llm_used_rate NUMERIC(6, 4),
  escalation_rate NUMERIC(6, 4),
  fast_intent_rate NUMERIC(6, 4),
  total_user_messages INTEGER NOT NULL DEFAULT 0,
  total_outbox_sent INTEGER NOT NULL DEFAULT 0,
  total_outbox_failed INTEGER NOT NULL DEFAULT 0,
  total_llm_used INTEGER NOT NULL DEFAULT 0,
  total_llm_timeout INTEGER NOT NULL DEFAULT 0,
  total_handovers INTEGER NOT NULL DEFAULT 0,
  total_fast_intent INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (metric_date, client_id)
);

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'metrics_daily'
ORDER BY ordinal_position;
