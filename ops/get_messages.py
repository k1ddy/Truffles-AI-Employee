#!/usr/bin/env python3
import subprocess
sql = """
SELECT role, LEFT(content, 100) as content, created_at 
FROM messages 
ORDER BY created_at DESC 
LIMIT 25;
"""
result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot', '-c', sql
], capture_output=True, text=True)
print(result.stdout)
