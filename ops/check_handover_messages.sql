SELECT 
  h.id,
  h.status,
  h.messages,
  h.created_at
FROM handovers h
ORDER BY created_at DESC
LIMIT 3;
