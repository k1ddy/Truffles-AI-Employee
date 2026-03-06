-- Wave7 Part A: executable action-macro contract for inbox macros.

ALTER TABLE console_macros
    ADD COLUMN IF NOT EXISTS action_config JSONB;
