SELECT id, telegram_topic_id, bot_status 
FROM conversations 
WHERE telegram_topic_id IS NOT NULL OR bot_status = 'muted';
