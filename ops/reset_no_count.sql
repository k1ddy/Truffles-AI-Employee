UPDATE conversations SET no_count = 0 WHERE client_id = '<CLIENT_ID>';
SELECT id, no_count, bot_status FROM conversations WHERE client_id = '<CLIENT_ID>';
