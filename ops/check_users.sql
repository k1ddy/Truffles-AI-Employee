SELECT u.id, u.phone, u.name, c.id as conv_id, c.telegram_topic_id
FROM users u
JOIN conversations c ON c.user_id = u.id
WHERE c.client_id = '<CLIENT_ID>';
