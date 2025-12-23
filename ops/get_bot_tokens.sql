SELECT c.slug, cs.telegram_bot_token 
FROM clients c 
LEFT JOIN client_settings cs ON cs.client_id = c.id;
