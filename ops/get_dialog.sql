-- Get recent dialog for phone 77015705555 with truffles
SELECT 
  m.role,
  m.content,
  m.created_at,
  m.metadata
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN users u ON c.user_id = u.id
JOIN clients cl ON c.client_id = cl.id
WHERE u.phone = '77015705555' 
  AND cl.name = 'truffles'
ORDER BY m.created_at DESC
LIMIT 20;

-- Get handovers for this user
SELECT 
  h.id,
  h.user_message,
  h.escalation_reason,
  h.status,
  h.trigger_type,
  h.created_at,
  cl.name as client
FROM handovers h
JOIN clients cl ON h.client_id = cl.id
ORDER BY h.created_at DESC
LIMIT 10;
