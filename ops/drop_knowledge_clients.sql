-- Удаляем старую таблицу knowledge_clients (больше не нужна)
-- Все данные теперь в clients.config

DROP TABLE IF EXISTS knowledge_clients CASCADE;

-- Проверяем что удалилась
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'knowledge_clients';
