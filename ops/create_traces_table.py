#!/usr/bin/env python3
"""Create message_traces table for observability"""
import subprocess

SQL = """
-- Таблица для полного trace каждого сообщения
-- Позволяет быстро найти: что написал клиент → что ответил бот → почему

CREATE TABLE IF NOT EXISTS message_traces (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Идентификация
    phone VARCHAR(20) NOT NULL,
    conversation_id UUID,
    execution_id VARCHAR(50),
    
    -- Входные данные
    message TEXT NOT NULL,
    
    -- Классификация
    intent VARCHAR(50),
    
    -- RAG
    rag_top_score FLOAT,
    rag_top_doc VARCHAR(100),
    rag_scores JSONB,  -- массив всех scores
    
    -- Ответ
    response TEXT,
    has_answer BOOLEAN,
    needs_escalation BOOLEAN,
    
    -- Метрики
    latency_ms INTEGER,
    
    -- Для поиска проблем
    error TEXT,
    
    -- Индексы для быстрого поиска
    CONSTRAINT idx_phone CHECK (phone IS NOT NULL)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_traces_phone ON message_traces(phone);
CREATE INDEX IF NOT EXISTS idx_traces_created ON message_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_intent ON message_traces(intent);
CREATE INDEX IF NOT EXISTS idx_traces_escalation ON message_traces(needs_escalation) WHERE needs_escalation = true;
CREATE INDEX IF NOT EXISTS idx_traces_low_score ON message_traces(rag_top_score) WHERE rag_top_score < 0.45;

-- Комментарий
COMMENT ON TABLE message_traces IS 'Полный trace каждого сообщения для быстрой диагностики проблем';
"""

cmd = f'docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "{SQL}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.returncode == 0:
    print("SUCCESS: message_traces table created")
    print(result.stdout)
else:
    print("ERROR:")
    print(result.stderr)
