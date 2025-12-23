-- Conversations
SELECT id, telegram_topic_id, bot_status, client_id 
FROM conversations 
WHERE client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0';

-- Handovers
SELECT id, status, conversation_id, created_at 
FROM handovers 
ORDER BY created_at DESC 
LIMIT 5;
