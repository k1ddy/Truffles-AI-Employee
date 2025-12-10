SELECT id, name, config->>'instance_id' as instance_id FROM clients LIMIT 1;
