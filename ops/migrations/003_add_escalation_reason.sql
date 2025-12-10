-- Add escalation_reason to handovers
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS escalation_reason VARCHAR(50);

-- Values: human_request, frustration, escalation
