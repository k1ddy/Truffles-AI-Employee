-- Insert client_settings for demo_salon
INSERT INTO client_settings (client_id, telegram_chat_id, telegram_bot_token)
SELECT id, '-1003362579990', '8249719610:AAGdyGmYTM9xnD5NojlsrIA36tbDcZFnpNk'
FROM clients WHERE name = 'demo_salon'
ON CONFLICT (client_id) DO UPDATE SET 
  telegram_chat_id = EXCLUDED.telegram_chat_id, 
  telegram_bot_token = EXCLUDED.telegram_bot_token;

-- Verify
SELECT c.name, cs.telegram_chat_id, LEFT(cs.telegram_bot_token, 20) as token_prefix
FROM client_settings cs 
JOIN clients c ON cs.client_id = c.id;
