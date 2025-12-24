-- Миграция на multi-tenant архитектуру
-- 1. Обновить clients: name → slug, config → добавить нужные поля

UPDATE clients 
SET 
  name = 'truffles',
  config = jsonb_build_object(
    'folder_id', '1JC4FiDcazmFy0nCNcE901cBn9ev-DoXw',
    'whatsapp_instance_id', 'eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InRydWZmbGVzLWNoYXRib3QifQ==',
    'whatsapp_token', 'REDACTED_JWT',
    'escalation_telegram', '1969855532',
    'notify_whatsapp', '77759841926'
  ),
  updated_at = NOW()
WHERE id = '499e4744-5e7f-4a97-8466-56ff2cdcf587';

-- 2. Проверить результат
SELECT id, name, status, config FROM clients;
