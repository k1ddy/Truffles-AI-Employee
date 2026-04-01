-- Migration 017: knowledge backlog table for misses
-- Run: psql -U $DB_USER -d chatbot -f ops/migrations/017_add_knowledge_backlog.sql

CREATE TABLE IF NOT EXISTS knowledge_backlog (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  user_text TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'unknown',
  miss_type TEXT NOT NULL DEFAULT 'unknown',
  repeat_count INTEGER NOT NULL DEFAULT 1,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS knowledge_backlog_unique
  ON knowledge_backlog (client_id, language, miss_type, user_text);

CREATE INDEX IF NOT EXISTS knowledge_backlog_last_seen_idx
  ON knowledge_backlog (client_id, last_seen_at DESC);

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'knowledge_backlog'
ORDER BY ordinal_position;
