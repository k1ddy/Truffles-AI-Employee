SELECT c.id, c.bot_status, c.no_count, c.bot_muted_until, u.phone 
FROM conversations c 
JOIN users u ON c.user_id = u.id 
ORDER BY c.last_message_at DESC 
LIMIT 5;
