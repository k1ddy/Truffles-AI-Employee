SELECT id, status, channel_ref, telegram_message_id 
FROM handovers 
ORDER BY created_at DESC 
LIMIT 5;
