#!/usr/bin/env python3
import subprocess
result = subprocess.run([
    'docker', 'exec', 'truffles_postgres_1', 
    'psql', '-U', 'n8n', '-d', 'chatbot', 
    '-c', "SELECT id, name, config->>'folder_id' as folder_id FROM clients WHERE status = 'active'"
], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
