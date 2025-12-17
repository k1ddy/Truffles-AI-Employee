UPDATE clients
SET config = jsonb_set(
    config,
    '{instance_id}',
    '"eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6InNhbG9uZGVtbyJ9"',
    true
)
WHERE name = 'demo_salon';
