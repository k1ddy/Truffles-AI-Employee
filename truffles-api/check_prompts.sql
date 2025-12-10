SELECT client_id, name, is_active, LEFT(text, 200) as text_preview FROM prompts WHERE name = 'system' AND is_active = true;
