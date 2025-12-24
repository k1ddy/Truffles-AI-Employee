-- Удалить мусорные handovers
DELETE FROM handovers WHERE conversation_id IN (
  SELECT c.id FROM conversations c
  JOIN users u ON u.id = c.user_id
  WHERE u.phone = 'undefined'
);

-- Удалить мусорные conversations
DELETE FROM conversations WHERE user_id IN (
  SELECT id FROM users WHERE phone = 'undefined'
);

-- Удалить мусорных users
DELETE FROM users WHERE phone = 'undefined';

-- Сбросить нормальные conversations
UPDATE conversations 
SET bot_status = 'active', 
    bot_muted_until = NULL, 
    no_count = 0;

-- Удалить все handovers
DELETE FROM handovers;

-- Проверяем
SELECT 'users' as t, count(*) as cnt FROM users
UNION ALL
SELECT 'conversations', count(*) FROM conversations
UNION ALL
SELECT 'handovers', count(*) FROM handovers;

-- Показать оставшиеся
SELECT u.phone, c.telegram_topic_id, c.bot_status
FROM users u
JOIN conversations c ON c.user_id = u.id
WHERE c.client_id = '<CLIENT_ID>';
