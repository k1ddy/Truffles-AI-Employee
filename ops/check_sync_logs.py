#!/usr/bin/env python3
import subprocess

sql = "SELECT client_slug, status, created_at FROM knowledge_sync_logs ORDER BY created_at DESC LIMIT 10"

result = subprocess.run([
    'docker', 'exec', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot', '-c', sql
], capture_output=True, text=True)
print(result.stdout)
