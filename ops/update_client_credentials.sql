-- Обновляем credentials в clients.config

-- Truffles
UPDATE clients 
SET config = config || '{
  "instance_id": "eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InRydWZmbGVzLWNoYXRib3QifQ==",
  "phone": "+77759841926"
}'::jsonb
WHERE name = 'truffles';

-- demo_salon
UPDATE clients 
SET config = config || '{
  "instance_id": "eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InNhbG9uZGVtbyJ9",
  "phone": "+77055740455"
}'::jsonb
WHERE name = 'demo_salon';

-- Проверка
SELECT name, 
       config->>'instance_id' as instance_id,
       config->>'phone' as phone
FROM clients;
