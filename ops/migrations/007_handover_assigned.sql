-- Добавляем колонки для назначения менеджера
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(100);
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS assigned_to_name VARCHAR(255);
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;

-- Проверка
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'handovers' 
  AND column_name IN ('assigned_to', 'assigned_to_name', 'resolved_at');
