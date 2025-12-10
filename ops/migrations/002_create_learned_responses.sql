-- Создание learned_responses (исправлено: handover_id вместо escalation_id)

CREATE TABLE IF NOT EXISTS learned_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  handover_id UUID REFERENCES handovers(id) ON DELETE SET NULL,
  
  question_text TEXT NOT NULL,
  question_normalized TEXT,
  
  response_text TEXT NOT NULL,
  
  source TEXT DEFAULT 'manager',
  source_name TEXT,
  
  use_count INTEGER DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learned_client ON learned_responses(client_id);
CREATE INDEX IF NOT EXISTS idx_learned_active ON learned_responses(client_id, is_active);

COMMENT ON TABLE learned_responses IS 'Выученные ответы из эскалаций (для RAG)';
