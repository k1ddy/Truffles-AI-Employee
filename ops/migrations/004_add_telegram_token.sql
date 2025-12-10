-- Add telegram_bot_token to client_settings
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS telegram_bot_token TEXT;

-- Update client settings with telegram data
-- truffles client
UPDATE client_settings cs
SET 
  telegram_chat_id = '-1003362579990',
  telegram_bot_token = '8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4'
FROM clients c
WHERE cs.client_id = c.id AND c.name = 'truffles';

-- demo_salon client  
UPDATE client_settings cs
SET 
  telegram_chat_id = '-1003362579990',
  telegram_bot_token = '8249719610:AAGdyGmYTM9xnD5NojlsrIA36tbDcZFnpNk'
FROM clients c
WHERE cs.client_id = c.id AND c.name = 'demo_salon';

-- Verify
SELECT c.name, cs.telegram_chat_id, cs.telegram_bot_token 
FROM client_settings cs 
JOIN clients c ON cs.client_id = c.id;
