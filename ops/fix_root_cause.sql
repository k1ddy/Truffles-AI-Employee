-- 1. Удалить handovers для undefined users
DELETE FROM handovers WHERE conversation_id IN (
  SELECT c.id FROM conversations c
  JOIN users u ON u.id = c.user_id
  WHERE u.phone IN ('undefined', 'unknown', '')
);

-- 2. Удалить messages
DELETE FROM messages WHERE conversation_id IN (
  SELECT c.id FROM conversations c
  JOIN users u ON u.id = c.user_id
  WHERE u.phone IN ('undefined', 'unknown', '')
);

-- 3. Удалить summaries
DELETE FROM conversation_summaries WHERE conversation_id IN (
  SELECT c.id FROM conversations c
  JOIN users u ON u.id = c.user_id
  WHERE u.phone IN ('undefined', 'unknown', '')
);

-- 4. Удалить conversations
DELETE FROM conversations WHERE user_id IN (
  SELECT id FROM users WHERE phone IN ('undefined', 'unknown', '')
);

-- 5. Удалить users
DELETE FROM users WHERE phone IN ('undefined', 'unknown', '');

-- 6. Сбросить handovers для теста
DELETE FROM handovers;

-- 7. Сбросить conversations
UPDATE conversations SET bot_status = 'active', bot_muted_until = NULL, no_count = 0;

-- Проверяем
SELECT 'users' as t, count(*) FROM users
UNION ALL SELECT 'conversations', count(*) FROM conversations
UNION ALL SELECT 'handovers', count(*) FROM handovers;

SELECT u.phone, c.id as conv_id, c.telegram_topic_id
FROM users u
JOIN conversations c ON c.user_id = u.id
WHERE c.client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0';
