-- Reset all muted conversations for testing
UPDATE conversations 
SET bot_status = 'active', no_count = 0, bot_muted_until = NULL;

-- Verify
SELECT c.id, c.bot_status, c.no_count, u.phone 
FROM conversations c 
JOIN users u ON c.user_id = u.id 
ORDER BY c.last_message_at DESC 
LIMIT 5;
