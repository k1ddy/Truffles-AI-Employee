#!/usr/bin/env python3
import subprocess

sql = """
INSERT INTO clients (name, status, config)
VALUES (
  'demo_salon',
  'active',
  '{
    "folder_id": "1SxeLyiBczLJ9D28eoXA79c6kB51Unhb7",
    "business_name": "Салон красоты Мира",
    "business_type": "beauty_salon"
  }'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
  config = EXCLUDED.config,
  status = 'active';

SELECT name, status, config->>'folder_id' as folder_id FROM clients;
"""

result = subprocess.run([
    'docker', 'exec', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot', '-c', sql
], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("Error:", result.stderr)
