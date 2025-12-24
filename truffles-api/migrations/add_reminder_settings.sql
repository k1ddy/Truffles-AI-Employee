-- Migration: Add reminder and mute settings to client_settings
-- Run: psql -U $DB_USER -d chatbot -f add_reminder_settings.sql

-- Add new columns to client_settings
ALTER TABLE client_settings 
ADD COLUMN IF NOT EXISTS owner_telegram_id TEXT,
ADD COLUMN IF NOT EXISTS enable_reminders BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS enable_owner_escalation BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS mute_duration_first_minutes INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS mute_duration_second_hours INTEGER DEFAULT 24;

-- Verify
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'client_settings'
ORDER BY ordinal_position;
