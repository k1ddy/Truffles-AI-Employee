-- Последние N сообщений (user + assistant)
-- Использование: изменить LIMIT на нужное количество

SELECT role, content, timestamp 
FROM messages 
WHERE role IN ('user', 'assistant') 
ORDER BY timestamp DESC 
LIMIT 20;

-- Сообщения конкретного пользователя
-- SELECT * FROM messages WHERE user_id = 'UUID' ORDER BY timestamp DESC;

-- Сообщения за период
-- SELECT * FROM messages WHERE timestamp > NOW() - INTERVAL '1 day' ORDER BY timestamp DESC;
