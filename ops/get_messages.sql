SELECT role, LEFT(content, 150) as content, created_at 
FROM messages 
ORDER BY created_at DESC 
LIMIT 6;
