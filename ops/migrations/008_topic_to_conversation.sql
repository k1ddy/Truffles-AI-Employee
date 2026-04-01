-- Переносим telegram_topic_id из users в conversations
-- Потому что один user может общаться с разными клиентами

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS telegram_topic_id BIGINT;

-- Сбрасываем старые topic_id в users (они были для неправильной группы)
UPDATE users SET telegram_topic_id = NULL;

-- Проверяем
SELECT 'conversations' as table_name, column_name 
FROM information_schema.columns 
WHERE table_name = 'conversations' AND column_name = 'telegram_topic_id';
