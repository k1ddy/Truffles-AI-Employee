-- Полный сброс для чистого теста

-- Сбрасываем conversations (НЕ трогаем telegram_topic_id!)
UPDATE conversations 
SET bot_status = 'active', 
    bot_muted_until = NULL, 
    no_count = 0;

-- Удаляем все handovers (для чистого теста)
DELETE FROM handovers;

-- Проверяем
SELECT 'conversations' as t, count(*) as cnt FROM conversations
UNION ALL
SELECT 'handovers', count(*) FROM handovers;
