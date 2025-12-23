-- Check and fix conversation_summaries table

-- Show current structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'conversation_summaries';

-- Add UNIQUE constraint on conversation_id
ALTER TABLE conversation_summaries 
ADD CONSTRAINT conversation_summaries_conversation_id_key 
UNIQUE (conversation_id);

-- Verify
SELECT conname FROM pg_constraint WHERE conrelid = 'conversation_summaries'::regclass;
