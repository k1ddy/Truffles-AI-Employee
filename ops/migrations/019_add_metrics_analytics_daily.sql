-- Migration 019: daily analytics KPI snapshot table
-- Run: psql -U $DB_USER -d chatbot -f ops/migrations/019_add_metrics_analytics_daily.sql

CREATE TABLE IF NOT EXISTS metrics_analytics_daily (
  metric_date DATE NOT NULL,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  inbound_conversations_total INTEGER NOT NULL DEFAULT 0,
  bot_closed_sessions INTEGER NOT NULL DEFAULT 0,
  bot_closed_total_sessions INTEGER NOT NULL DEFAULT 0,
  bot_closed_incomplete_total INTEGER NOT NULL DEFAULT 0,
  bot_closed_rate NUMERIC(6, 4),
  manager_median_response_seconds NUMERIC(10, 2),
  manager_time_saved_seconds_estimate NUMERIC(12, 2),
  booking_total INTEGER NOT NULL DEFAULT 0,
  booking_attributed INTEGER NOT NULL DEFAULT 0,
  booking_missing_conversation_total INTEGER NOT NULL DEFAULT 0,
  booking_conversion_rate NUMERIC(6, 4),
  first_response_p50_seconds NUMERIC(10, 2),
  first_response_p90_seconds NUMERIC(10, 2),
  first_response_missing_total INTEGER NOT NULL DEFAULT 0,
  after_hours_total INTEGER NOT NULL DEFAULT 0,
  after_hours_covered INTEGER NOT NULL DEFAULT 0,
  after_hours_missing_total INTEGER NOT NULL DEFAULT 0,
  after_hours_coverage_rate NUMERIC(6, 4),
  escalation_total INTEGER NOT NULL DEFAULT 0,
  escalation_quality_total INTEGER NOT NULL DEFAULT 0,
  escalation_meta_missing_total INTEGER NOT NULL DEFAULT 0,
  escalation_quality_rate NUMERIC(6, 4),
  outbox_failed_total INTEGER NOT NULL DEFAULT 0,
  outbox_saved_total INTEGER NOT NULL DEFAULT 0,
  no_response_alert_total INTEGER NOT NULL DEFAULT 0,
  intent_missing_total INTEGER NOT NULL DEFAULT 0,
  top_intents JSONB,
  top_info_sections JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (metric_date, client_id)
);

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'metrics_analytics_daily'
ORDER BY ordinal_position;
