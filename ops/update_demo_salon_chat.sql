-- Обновляем telegram_chat_id для demo_salon
UPDATE client_settings 
SET telegram_chat_id = -1003412216010
WHERE client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0';

-- Проверяем
SELECT 
  c.name,
  cs.telegram_chat_id,
  cs.telegram_bot_token
FROM client_settings cs
JOIN clients c ON c.id = cs.client_id;
