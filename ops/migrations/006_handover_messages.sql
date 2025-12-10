-- Расширение handovers для адаптеров и истории сообщений

-- История сообщений менеджер-клиент
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS messages JSONB DEFAULT '[]'::jsonb;

-- Канал через который работает эскалация
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'telegram';

-- Ссылка на объект в канале (topic_id для Telegram, ticket_id для CRM)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS channel_ref VARCHAR(255);

-- Telegram message_id эскалации (для reply matching)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS telegram_message_id BIGINT;

-- Добавляем telegram_topic_id в users для связи клиент-тема
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_topic_id BIGINT;

-- Индексы
CREATE INDEX IF NOT EXISTS idx_handovers_channel_ref ON handovers(channel_ref);
CREATE INDEX IF NOT EXISTS idx_users_telegram_topic ON users(telegram_topic_id);

-- Проверка
SELECT 
  column_name, 
  data_type 
FROM information_schema.columns 
WHERE table_name = 'handovers' 
  AND column_name IN ('messages', 'channel', 'channel_ref', 'telegram_message_id')
ORDER BY column_name;
