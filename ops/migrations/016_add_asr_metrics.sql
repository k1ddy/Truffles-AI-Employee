-- Migration 016: add ASR metrics to daily snapshot table
-- Run: psql -U $DB_USER -d chatbot -f ops/migrations/016_add_asr_metrics.sql

ALTER TABLE metrics_daily
  ADD COLUMN IF NOT EXISTS asr_fail_rate NUMERIC(6, 4),
  ADD COLUMN IF NOT EXISTS total_asr_used INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_asr_failed INTEGER NOT NULL DEFAULT 0;

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'metrics_daily'
ORDER BY ordinal_position;
