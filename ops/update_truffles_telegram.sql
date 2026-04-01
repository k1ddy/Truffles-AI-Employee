-- Update truffles client_settings with Telegram info
UPDATE client_settings 
SET telegram_chat_id = '-1003362579990', 
    telegram_bot_token = 'REDACTED_TELEGRAM_BOT_TOKEN' 
WHERE client_id = (SELECT id FROM clients WHERE name = 'truffles');

-- Verify
SELECT cs.client_id, cs.telegram_chat_id, cs.telegram_bot_token, c.name 
FROM client_settings cs 
JOIN clients c ON cs.client_id = c.id;
