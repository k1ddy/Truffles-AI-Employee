-- Migration: add learning consent + anonymization/retention + pack candidate metadata
-- Run: psql -U $DB_USER -d chatbot -f 018_add_learning_consent_pack_candidates.sql

ALTER TABLE client_settings
    ADD COLUMN IF NOT EXISTS learning_consent_status TEXT DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS learning_anonymization_mode TEXT DEFAULT 'redact',
    ADD COLUMN IF NOT EXISTS learning_retention_days INTEGER DEFAULT 180;

ALTER TABLE learned_responses
    ADD COLUMN IF NOT EXISTS consent_status TEXT,
    ADD COLUMN IF NOT EXISTS anonymization_mode TEXT,
    ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS candidate_type TEXT DEFAULT 'faq',
    ADD COLUMN IF NOT EXISTS candidate_payload JSONB,
    ADD COLUMN IF NOT EXISTS redaction_summary JSONB;

CREATE INDEX IF NOT EXISTS idx_learned_responses_status ON learned_responses(status);
CREATE INDEX IF NOT EXISTS idx_learned_responses_retention_expires_at ON learned_responses(retention_expires_at);
