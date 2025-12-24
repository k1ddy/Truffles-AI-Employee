-- Обновляем telegram_chat_id для demo_salon
UPDATE client_settings 
SET telegram_chat_id = -1003412216010
WHERE client_id = '<CLIENT_ID>';

-- Проверяем
SELECT 
  c.name,
  cs.telegram_chat_id,
  cs.telegram_bot_token
FROM client_settings cs
JOIN clients c ON c.id = cs.client_id;
