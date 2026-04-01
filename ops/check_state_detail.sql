-- Conversations
SELECT id, telegram_topic_id, bot_status, client_id 
FROM conversations 
WHERE client_id = '<CLIENT_ID>';

-- Handovers
SELECT id, status, conversation_id, created_at 
FROM handovers 
ORDER BY created_at DESC 
LIMIT 5;
