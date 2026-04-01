-- Add escalation tracking to conversations
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP DEFAULT NULL;

-- Add escalation settings to client_settings
ALTER TABLE client_settings
ADD COLUMN IF NOT EXISTS escalation_cooldown_minutes INTEGER DEFAULT 30;

-- Add column for allowing repeated human_request
ALTER TABLE client_settings
ADD COLUMN IF NOT EXISTS allow_repeated_human_request BOOLEAN DEFAULT TRUE;

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'conversations' AND column_name = 'escalated_at';

SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'client_settings' AND column_name LIKE 'escalation%';
