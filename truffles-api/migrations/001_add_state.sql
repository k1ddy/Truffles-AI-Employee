ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS state TEXT DEFAULT 'bot_active';

-- Add check constraint separately (IF NOT EXISTS not supported for constraints)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'conversations_state_check'
    ) THEN
        ALTER TABLE conversations 
        ADD CONSTRAINT conversations_state_check 
        CHECK (state IN ('bot_active', 'pending', 'manager_active'));
    END IF;
END $$;
