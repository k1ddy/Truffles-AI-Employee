SELECT u.id, u.phone, u.name, c.id as conv_id, c.telegram_topic_id
FROM users u
JOIN conversations c ON c.user_id = u.id
WHERE c.client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0';
