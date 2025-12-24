-- Найти conversation с undefined user
SELECT c.id FROM conversations c
JOIN users u ON u.id = c.user_id
WHERE u.phone = 'undefined';

-- Удалить summaries
DELETE FROM conversation_summaries WHERE conversation_id IN (
  SELECT c.id FROM conversations c
  JOIN users u ON u.id = c.user_id
  WHERE u.phone = 'undefined'
);

-- Удалить messages
DELETE FROM messages WHERE conversation_id IN (
  SELECT c.id FROM conversations c
  JOIN users u ON u.id = c.user_id
  WHERE u.phone = 'undefined'
);

-- Удалить conversations
DELETE FROM conversations WHERE user_id IN (
  SELECT id FROM users WHERE phone = 'undefined'
);

-- Удалить users
DELETE FROM users WHERE phone = 'undefined';

-- Проверяем
SELECT u.phone, c.telegram_topic_id, c.bot_status
FROM users u
JOIN conversations c ON c.user_id = u.id
WHERE c.client_id = '<CLIENT_ID>';
