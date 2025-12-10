SELECT p.name, p.is_active, LEFT(p.text, 100) as text_preview 
FROM prompts p 
JOIN clients c ON p.client_id = c.id 
WHERE c.name = 'truffles';
